"""Infraestrutura como codigo via APIs AWS, restrita ao LocalStack."""
import io
import json
import os
import zipfile
from pathlib import Path

from scripts.common import client, rebase, wait_until

PREFIX = "training-orders"
REGION = "us-east-1"


def role(iam, name, statements):
    trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
             "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
    try:
        arn = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust))["Role"]["Arn"]
    except iam.exceptions.EntityAlreadyExistsException:
        arn = iam.get_role(RoleName=name)["Role"]["Arn"]
    iam.put_role_policy(RoleName=name, PolicyName="lab-permissions", PolicyDocument=json.dumps({
        "Version": "2012-10-17", "Statement": statements,
    }))
    return arn


def package():
    directory = Path("/opt/function")
    if not directory.is_dir():
        raise RuntimeError("Execute o provisionamento pelo Docker Compose: dependencias Linux necessarias")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in directory.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(directory))
    return buffer.getvalue()


def function(lambdas, name, handler, role_arn, environment, code):
    config = dict(FunctionName=name, Role=role_arn, Runtime="python3.13", Handler=handler,
                  Timeout=10, MemorySize=256, Environment={"Variables": environment})
    try:
        lambdas.get_function(FunctionName=name)
    except lambdas.exceptions.ResourceNotFoundException:
        lambdas.create_function(**config, Code={"ZipFile": code}, Architectures=["x86_64"])
    else:
        lambdas.update_function_code(FunctionName=name, ZipFile=code)
        lambdas.get_waiter("function_updated_v2").wait(FunctionName=name)
        lambdas.update_function_configuration(**config)
        lambdas.get_waiter("function_updated_v2").wait(FunctionName=name)
    lambdas.get_waiter("function_active_v2").wait(FunctionName=name)
    return lambdas.get_function_configuration(FunctionName=name)["FunctionArn"]


def provision():
    sqs, iam, lambdas, gateway = [client(s) for s in ("sqs", "iam", "lambda", "apigateway")]
    account = client("sts").get_caller_identity()["Account"]
    if account != "000000000000":
        raise RuntimeError("Conta inesperada; use credenciais locais test/test")
    dlq = sqs.create_queue(QueueName=f"{PREFIX}-dlq", Attributes={
        "MessageRetentionPeriod": "1209600", "VisibilityTimeout": "30",
    })["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    attributes = {"VisibilityTimeout": "60", "MessageRetentionPeriod": "345600",
                  "ReceiveMessageWaitTimeSeconds": "1",
                  "RedrivePolicy": json.dumps({"deadLetterTargetArn": dlq_arn, "maxReceiveCount": 3})}
    # create_queue exige atributos identicos se a fila ja existir.
    try:
        queue = sqs.get_queue_url(QueueName=PREFIX)["QueueUrl"]
        sqs.set_queue_attributes(QueueUrl=queue, Attributes=attributes)
    except sqs.exceptions.QueueDoesNotExist:
        queue = sqs.create_queue(QueueName=PREFIX, Attributes=attributes)["QueueUrl"]
    queue_arn = sqs.get_queue_attributes(QueueUrl=queue, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    logs_policy = {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                   "logs:PutLogEvents"], "Resource": f"arn:aws:logs:{REGION}:{account}:log-group:/aws/lambda/{PREFIX}*"}
    api_role = role(iam, f"{PREFIX}-api-role", [logs_policy, {"Effect": "Allow",
        "Action": ["sqs:SendMessage", "sqs:GetQueueAttributes"], "Resource": queue_arn}])
    worker_role = role(iam, f"{PREFIX}-worker-role", [logs_policy, {"Effect": "Allow",
        "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes",
                   "sqs:ChangeMessageVisibility"], "Resource": queue_arn}])
    lambda_endpoint = os.getenv("LAMBDA_AWS_ENDPOINT_URL", "http://localstack:4566")
    environment = {"DATABASE_URL": os.environ["DATABASE_URL"], "ENABLE_FAULTS": "true",
                   "AWS_ENDPOINT_URL": lambda_endpoint,
                   "ORDERS_QUEUE_URL": rebase(queue, lambda_endpoint)}
    code = package()
    api_arn = function(lambdas, f"{PREFIX}-api", "training_backend.api.handler", api_role, environment, code)
    worker_name = f"{PREFIX}-worker"
    worker_arn = function(lambdas, worker_name, "training_backend.worker.handler", worker_role, environment, code)
    mappings = lambdas.list_event_source_mappings(FunctionName=worker_name, EventSourceArn=queue_arn)["EventSourceMappings"]
    mapping_args = dict(BatchSize=5, MaximumBatchingWindowInSeconds=0,
                        FunctionResponseTypes=["ReportBatchItemFailures"], Enabled=True)
    if mappings:
        mapping = lambdas.update_event_source_mapping(UUID=mappings[0]["UUID"], **mapping_args)
    else:
        mapping = lambdas.create_event_source_mapping(FunctionName=worker_arn, EventSourceArn=queue_arn, **mapping_args)
    mapping_id = mapping["UUID"]
    wait_until(lambda: lambdas.get_event_source_mapping(UUID=mapping_id)["State"] == "Enabled",
               description="event source mapping habilitado")

    apis = [a for a in gateway.get_rest_apis(limit=500)["items"] if a["name"] == PREFIX]
    api = apis[0] if apis else gateway.create_rest_api(name=PREFIX, endpointConfiguration={"types": ["REGIONAL"]})
    api_id = api["id"]
    resources = gateway.get_resources(restApiId=api_id, limit=500)["items"]
    root = next(r for r in resources if r["path"] == "/")
    proxy = next((r for r in resources if r["path"] == "/{proxy+}"), None)
    if proxy is None:
        proxy = gateway.create_resource(restApiId=api_id, parentId=root["id"], pathPart="{proxy+}")
    # put_method nao atualiza um metodo ja existente.
    try:
        gateway.get_method(restApiId=api_id, resourceId=proxy["id"], httpMethod="ANY")
    except gateway.exceptions.NotFoundException:
        gateway.put_method(restApiId=api_id, resourceId=proxy["id"], httpMethod="ANY", authorizationType="NONE")
    gateway.put_integration(restApiId=api_id, resourceId=proxy["id"], httpMethod="ANY", type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{api_arn}/invocations")
    try:
        lambdas.add_permission(FunctionName=f"{PREFIX}-api", StatementId="api-gateway",
            Action="lambda:InvokeFunction", Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{REGION}:{account}:{api_id}/*/*/*")
    except lambdas.exceptions.ResourceConflictException:
        pass
    gateway.create_deployment(restApiId=api_id, stageName="local")
    output = Path(os.getenv("LAB_OUTPUT_DIR", ".local"))
    output.mkdir(parents=True, exist_ok=True)
    public = os.getenv("LOCALSTACK_PUBLIC_URL", "http://localhost:4566")
    internal = os.getenv("LOCALSTACK_INTERNAL_URL", "http://localstack:4566")
    path = f"/_aws/execute-api/{api_id}/local"
    result = {"api_id": api_id, "base_url": public + path, "internal_base_url": internal + path,
              "queue_url": queue, "dlq_url": dlq, "mapping_id": mapping_id,
              "api_function": f"{PREFIX}-api", "worker_function": worker_name,
              "visibility_timeout": 60, "max_receive_count": 3}
    (output / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    postman = {"name": "Treinamento local", "values": [
        {"key": "base_url", "value": result["base_url"], "enabled": True},
        {"key": "customer_id", "value": "aluno-01", "enabled": True},
    ], "_postman_variable_scope": "environment"}
    (output / "postman.local.json").write_text(json.dumps(postman, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    provision()

