import base64
import json
from unittest.mock import Mock
from uuid import uuid4

import pytest
from botocore.exceptions import EndpointConnectionError
from psycopg import OperationalError

from training_backend import api

pytestmark = pytest.mark.unit


@pytest.fixture
def queue(monkeypatch):
    queue = Mock()
    monkeypatch.setattr(api, "sqs", lambda: queue)
    monkeypatch.setattr(api, "queue_url", lambda: "http://localstack/queue")
    monkeypatch.delenv("ENABLE_FAULTS", raising=False)
    return queue


def invoke(method, path, body=None, **extra):
    result = api.handler({"httpMethod": method, "path": path, "body": body, **extra}, None)
    return result["statusCode"], json.loads(result["body"]), result["headers"]


def test_acceptance_means_queued_not_processed(queue, order_data):
    status, body, headers = invoke("POST", "/orders", json.dumps(order_data))
    assert status == 202
    assert body == {"order_id": order_data["order_id"], "status": "ACCEPTED"}
    assert headers["Location"] == "/orders/" + order_data["order_id"]
    event = json.loads(queue.send_message.call_args.kwargs["MessageBody"])
    assert event["version"] == 1
    assert event["order"]["order_id"] == order_data["order_id"]


@pytest.mark.parametrize("body", ["{", "null", "[]", "", "{}"])
def test_invalid_body_never_enqueues(queue, body):
    assert invoke("POST", "/orders", body)[0] == 400
    queue.send_message.assert_not_called()


def test_handles_gateway_base64_payload(queue, order_data):
    encoded = base64.b64encode(json.dumps(order_data).encode()).decode()
    assert invoke("POST", "/orders", encoded, isBase64Encoded=True)[0] == 202


def test_oversized_request_never_enqueues(queue):
    assert invoke("POST", "/orders", "x" * 65537)[0] == 413
    queue.send_message.assert_not_called()


def test_queue_outage_does_not_claim_acceptance(queue, order_data):
    queue.send_message.side_effect = EndpointConnectionError(endpoint_url="local")
    assert invoke("POST", "/orders", json.dumps(order_data))[0] == 503


def test_faults_are_opt_in(queue, order_data):
    order_data["failure_mode"] = "permanent"
    assert invoke("POST", "/orders", json.dumps(order_data))[0] == 400
    queue.send_message.assert_not_called()


def test_database_outage_returns_unavailable(monkeypatch):
    monkeypatch.setattr(api.repository, "find_order", Mock(side_effect=OperationalError("offline")))
    assert invoke("GET", f"/orders/{uuid4()}")[0] == 503


def test_pending_or_unknown_order_returns_404(monkeypatch):
    monkeypatch.setattr(api.repository, "find_order", lambda order_id: None)
    assert invoke("GET", f"/orders/{uuid4()}")[:2] == (404, {"error": "order_not_found"})


def test_invalid_uuid_returns_400():
    assert invoke("GET", "/orders/not-a-uuid")[0] == 400

