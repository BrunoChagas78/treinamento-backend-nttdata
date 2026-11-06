"""O event source mapping remove apenas os registros processados com sucesso."""
import json
import logging
import os

from training_backend.models import OrderEvent
from training_backend.repository import save_order

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    failures = []
    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            message = OrderEvent.model_validate_json(record["body"])
            attempts = int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))
            mode = message.order.failure_mode
            if mode != "none" and os.getenv("ENABLE_FAULTS") != "true":
                raise ValueError("fault_injection_disabled")
            if mode == "permanent" or (mode == "once" and attempts == 1):
                raise RuntimeError(f"injected_failure:{mode}")
            result = save_order(message.order, attempts, message_id)
            logger.info(json.dumps({"action": result, "message_id": message_id,
                                    "order_id": str(message.order.order_id), "attempt": attempts}))
        except Exception:
            # Isolar por registro evita repetir os sucessos de um lote misto.
            logger.exception("processing_failed message_id=%s", message_id)
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}

