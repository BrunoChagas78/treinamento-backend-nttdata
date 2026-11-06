"""Ferramentas para observar filas e corrigir uma mensagem especifica da DLQ."""
import argparse
import json
from uuid import UUID, uuid4

from scripts.common import client, local_endpoint, manifest, rebase, wait_until
from training_backend.models import Order, OrderEvent


def find_dlq_message(sqs, url, order_id):
    held, found = [], None
    try:
        # Manter os lotes anteriores invisiveis durante a busca evita ler
        # sempre os mesmos dez registros e nunca alcancar o pedido procurado.
        for _ in range(20):
            messages = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10,
                WaitTimeSeconds=0, VisibilityTimeout=30).get("Messages", [])
            if not messages:
                break
            held.extend(messages)
            for message in messages:
                try:
                    candidate = json.loads(message["Body"])["order"]["order_id"]
                except (ValueError, KeyError, TypeError):
                    candidate = None
                if candidate == order_id:
                    found = message
                    break
            if found:
                break
        return found
    finally:
        # Nao descartar mensagens de outros cenarios.
        for message in held:
            if found is None or message["MessageId"] != found["MessageId"]:
                sqs.change_message_visibility(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"], VisibilityTimeout=0)


def redrive(sqs, dlq, queue, message):
    event = OrderEvent.model_validate_json(message["Body"])
    event.order.failure_mode = "none"
    sqs.send_message(QueueUrl=queue, MessageBody=event.model_dump_json())
    # Se o envio falhar, a mensagem permanece na DLQ.
    sqs.delete_message(QueueUrl=dlq, ReceiptHandle=message["ReceiptHandle"])
    return str(event.order.order_id)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("pause")
    sub.add_parser("resume")
    logs = sub.add_parser("logs")
    logs.add_argument("--function", choices=["api", "worker"], default="worker")
    send = sub.add_parser("send")
    send.add_argument("--failure", choices=["none", "once", "permanent"], default="none")
    send.add_argument("--order-id", type=UUID, default=None)
    send.add_argument("--customer", default="instrutor")
    repair = sub.add_parser("redrive")
    repair.add_argument("order_id", type=UUID)
    args = parser.parse_args()
    data, sqs = manifest(), client("sqs")
    queue, dlq = [rebase(data[k], local_endpoint()) for k in ("queue_url", "dlq_url")]
    if args.action == "status":
        for name, url in (("orders", queue), ("dlq", dlq)):
            print(name, json.dumps(sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"], indent=2))
        print("worker", client("lambda").get_event_source_mapping(UUID=data["mapping_id"])["State"])
    elif args.action in {"pause", "resume"}:
        desired = "Enabled" if args.action == "resume" else "Disabled"
        lambdas = client("lambda")
        lambdas.update_event_source_mapping(UUID=data["mapping_id"], Enabled=args.action == "resume")
        wait_until(lambda: lambdas.get_event_source_mapping(UUID=data["mapping_id"])["State"] == desired,
                   description=f"worker {desired}")
        print(f"Worker {desired}. Invocacoes em andamento podem terminar.")
    elif args.action == "send":
        order = Order(order_id=args.order_id or uuid4(), customer_id=args.customer,
                      amount="42.50", failure_mode=args.failure)
        event = OrderEvent(version=1, order=order)
        result = sqs.send_message(QueueUrl=queue, MessageBody=event.model_dump_json())
        print(json.dumps({"order_id": str(order.order_id), "message_id": result["MessageId"]}))
    elif args.action == "logs":
        group = "/aws/lambda/" + data[f"{args.function}_function"]
        result = client("logs").filter_log_events(logGroupName=group, limit=100)
        for event in result["events"]:
            print(event["message"].rstrip())
    elif args.action == "redrive":
        message = wait_until(lambda: find_dlq_message(sqs, dlq, str(args.order_id)), timeout=20,
                             description="pedido especifico na DLQ")
        print("Reenviado:", redrive(sqs, dlq, queue, message))


if __name__ == "__main__":
    main()

