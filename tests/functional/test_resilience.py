import json
from uuid import uuid4

import pytest

from scripts.common import client, local_endpoint, rebase, wait_until
from scripts.lab import find_dlq_message, redrive

pytestmark = pytest.mark.resilience


def test_duplicate_delivery_keeps_one_row(http, order_data, processed, sql):
    # Enviar novamente apos confirmar o primeiro processamento prova a redelivery.
    assert http("POST", "/orders", order_data)[0] == 202
    processed(order_data["order_id"])
    for _ in range(3):
        assert http("POST", "/orders", order_data)[0] == 202
    # Standard nao garante ordem: observar os recibos do proprio pedido.
    def all_delivered():
        rows = sql("SELECT outcome FROM order_receipts WHERE order_id = %s", (order_data["order_id"],))
        return rows if len(rows) == 4 else None
    receipts = wait_until(all_delivered, timeout=60, description="quatro entregas do mesmo pedido")
    assert sorted(row["outcome"] for row in receipts) == ["created", "duplicate", "duplicate", "duplicate"]
    assert sql("SELECT count(*) AS n FROM orders WHERE order_id = %s", (order_data["order_id"],))[0]["n"] == 1


def test_transient_failure_retries_then_persists(http, order_data, processed, sql):
    order_data["failure_mode"] = "once"
    assert http("POST", "/orders", order_data)[0] == 202
    processed(order_data["order_id"], timeout=150)
    row = sql("SELECT receive_count FROM orders WHERE order_id = %s", (order_data["order_id"],))[0]
    assert row["receive_count"] >= 2


def test_poison_message_reaches_dlq_then_recovers(infrastructure, http, order_data, processed, sql):
    order_data["failure_mode"] = "permanent"
    assert http("POST", "/orders", order_data)[0] == 202
    # Um pedido valido deve progredir apesar do pedido defeituoso.
    healthy = {**order_data, "order_id": str(uuid4()), "failure_mode": "none"}
    assert http("POST", "/orders", healthy)[0] == 202
    processed(healthy["order_id"])
    sqs = client("sqs")
    dlq, queue = [rebase(infrastructure[k], local_endpoint()) for k in ("dlq_url", "queue_url")]
    message = wait_until(lambda: find_dlq_message(sqs, dlq, order_data["order_id"]),
                         timeout=300, description="mensagem especifica na DLQ apos 3 tentativas")
    assert json.loads(message["Body"])["order"]["order_id"] == order_data["order_id"]
    assert sql("SELECT * FROM orders WHERE order_id = %s", (order_data["order_id"],)) == []
    # O teste remove a mensagem somente depois de confirmar o novo envio.
    assert redrive(sqs, dlq, queue, message) == order_data["order_id"]
    processed(order_data["order_id"])
    assert sql("SELECT count(*) AS n FROM orders WHERE order_id = %s", (order_data["order_id"],))[0]["n"] == 1

