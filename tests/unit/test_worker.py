import json
from unittest.mock import Mock

import pytest

from training_backend import worker

pytestmark = pytest.mark.unit


def record(order, message_id="message-1", count=1):
    return {"messageId": message_id, "body": json.dumps({"version": 1, "order": order}),
            "attributes": {"ApproximateReceiveCount": str(count)}}


@pytest.fixture
def save(monkeypatch):
    save = Mock(return_value="created")
    monkeypatch.setattr(worker, "save_order", save)
    monkeypatch.setenv("ENABLE_FAULTS", "true")
    return save


def test_mixed_batch_retries_only_bad_record(save, order_data):
    bad = {"messageId": "bad", "body": "not-json"}
    result = worker.handler({"Records": [record(order_data, "good"), bad]}, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "bad"}]}
    assert save.call_count == 1


def test_transient_fault_succeeds_on_next_receive(save, order_data):
    order_data["failure_mode"] = "once"
    assert worker.handler({"Records": [record(order_data)]}, None)["batchItemFailures"]
    save.assert_not_called()
    assert worker.handler({"Records": [record(order_data, count=2)]}, None) == {"batchItemFailures": []}
    assert save.call_args.args[1] == 2


@pytest.mark.parametrize("count", [1, 2, 3])
def test_permanent_fault_always_returns_failure(save, order_data, count):
    order_data["failure_mode"] = "permanent"
    assert worker.handler({"Records": [record(order_data, count=count)]}, None)["batchItemFailures"]
    save.assert_not_called()


def test_commit_failure_keeps_message_for_retry(save, order_data):
    save.side_effect = RuntimeError("commit failed")
    assert worker.handler({"Records": [record(order_data)]}, None) == {
        "batchItemFailures": [{"itemIdentifier": "message-1"}]}


def test_duplicate_is_successfully_acknowledged(save, order_data):
    save.return_value = "duplicate"
    assert worker.handler({"Records": [record(order_data)]}, None) == {"batchItemFailures": []}

