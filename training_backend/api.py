"""Handler Lambda para integracao proxy do API Gateway REST (payload v1)."""
import base64
import binascii
import json
import logging
import os
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError
from psycopg import Error as DatabaseError
from pydantic import ValidationError

from training_backend import repository
from training_backend.models import Order, OrderEvent
from training_backend.resources import database, queue_url, sqs

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def response(status, body, **headers):
    return {"statusCode": status, "headers": {"Content-Type": "application/json", **headers},
            "body": json.dumps(body, default=str)}


def handler(event, context):
    method, path = event.get("httpMethod"), event.get("path", "")
    try:
        if method == "GET" and path == "/health":
            with database() as connection:
                connection.execute("SELECT 1")
            sqs().get_queue_attributes(QueueUrl=queue_url(), AttributeNames=["QueueArn"])
            return response(200, {"status": "ok"})
        if method == "POST" and path == "/orders":
            body = event.get("body") or ""
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body, validate=True).decode("utf-8")
            if len(body.encode("utf-8")) > 65536:
                return response(413, {"error": "payload_too_large"})
            order = Order.model_validate_json(body)
            if order.failure_mode != "none" and os.getenv("ENABLE_FAULTS") != "true":
                return response(400, {"error": "fault_injection_disabled"})
            message = OrderEvent(version=1, order=order)
            sqs().send_message(QueueUrl=queue_url(), MessageBody=message.model_dump_json())
            logger.info(json.dumps({"action": "accepted", "order_id": str(order.order_id)}))
            return response(202, {"order_id": str(order.order_id), "status": "ACCEPTED"},
                            Location=f"/orders/{order.order_id}")
        if method == "GET" and path.startswith("/orders/"):
            order_id = UUID(path.removeprefix("/orders/"))
            order = repository.find_order(order_id)
            return response(200, order) if order else response(404, {"error": "order_not_found"})
        return response(404, {"error": "route_not_found"})
    except (ValidationError, ValueError, UnicodeError, binascii.Error):
        return response(400, {"error": "invalid_request"})
    except (BotoCoreError, ClientError, DatabaseError):
        logger.exception("dependency_unavailable")
        return response(503, {"error": "dependency_unavailable"})

