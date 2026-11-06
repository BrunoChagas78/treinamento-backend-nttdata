import json
from unittest.mock import Mock

import pytest

from scripts.common import local_endpoint
from scripts.lab import find_dlq_message, redrive

pytestmark = pytest.mark.unit


def test_redrive_sends_corrected_message_before_deleting(order_data):
    order_data["failure_mode"] = "permanent"
    sqs = Mock()
    message = {"Body": json.dumps({"version": 1, "order": order_data}), "ReceiptHandle": "receipt"}
    redrive(sqs, "dlq", "queue", message)
    assert [call[0] for call in sqs.mock_calls] == ["send_message", "delete_message"]
    assert json.loads(sqs.send_message.call_args.kwargs["MessageBody"])["order"]["failure_mode"] == "none"


def test_failed_redrive_never_deletes_original(order_data):
    sqs = Mock()
    sqs.send_message.side_effect = RuntimeError("offline")
    with pytest.raises(RuntimeError):
        redrive(sqs, "dlq", "queue", {"Body": json.dumps({"version": 1, "order": order_data}), "ReceiptHandle": "r"})
    sqs.delete_message.assert_not_called()


def test_tools_reject_real_aws_endpoint(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://sqs.us-east-1.amazonaws.com")
    with pytest.raises(ValueError, match="somente endpoints locais"):
        local_endpoint()


def test_dlq_search_reaches_later_batches_without_hiding_other_orders(order_data):
    unrelated = {"MessageId": "other", "ReceiptHandle": "other-receipt", "Body": "not-json"}
    wanted = {"MessageId": "wanted", "ReceiptHandle": "wanted-receipt",
              "Body": json.dumps({"version": 1, "order": order_data})}
    sqs = Mock()
    sqs.receive_message.side_effect = [{"Messages": [unrelated]}, {"Messages": [wanted]}]
    assert find_dlq_message(sqs, "dlq", order_data["order_id"]) == wanted
    assert [call[0] for call in sqs.mock_calls] == ["receive_message", "receive_message", "change_message_visibility"]
    sqs.change_message_visibility.assert_called_once_with(QueueUrl="dlq", ReceiptHandle="other-receipt", VisibilityTimeout=0)

