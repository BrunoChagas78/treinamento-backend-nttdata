from uuid import uuid4

import pytest

pytestmark = pytest.mark.contract


def test_acceptance_contract(http, order_data):
    status, body, headers = http("POST", "/orders", order_data)
    assert status == 202
    assert body == {"order_id": order_data["order_id"], "status": "ACCEPTED"}
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Location"].endswith(order_data["order_id"])


@pytest.mark.parametrize("field,value", [("amount", "0"), ("amount", "1.001"), ("currency", "USD"),
                                       ("customer_id", ""), ("order_id", "invalid")])
def test_negative_contract(http, order_data, field, value):
    order_data[field] = value
    status, body, _ = http("POST", "/orders", order_data)
    assert (status, body) == (400, {"error": "invalid_request"})


def test_malformed_json(http):
    assert http("POST", "/orders", raw=b"{")[0] == 400


def test_unknown_order(http):
    assert http("GET", f"/orders/{uuid4()}")[0] == 404

