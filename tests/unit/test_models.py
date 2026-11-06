from decimal import Decimal

import pytest
from pydantic import ValidationError

from training_backend.models import Order, OrderEvent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("field,value", [
    ("amount", "0"), ("amount", "-1"), ("amount", "1.001"), ("amount", "NaN"),
    ("amount", "Infinity"), ("amount", "10000000000.00"), ("order_id", "invalido"),
    ("customer_id", ""), ("customer_id", "   "), ("customer_id", "x" * 101),
    ("currency", "USD"), ("failure_mode", "unknown"), ("campo_extra", "valor"),
])
def test_rejects_invalid_order(order_data, field, value):
    order_data[field] = value
    with pytest.raises(ValidationError):
        Order.model_validate(order_data)


def test_money_is_decimal_and_normalized(order_data):
    order_data["amount"] = "42.5"
    order = Order.model_validate(order_data)
    assert order.amount == Decimal("42.50")
    assert order.business_data()["amount"] == "42.50"
    assert "failure_mode" not in order.business_data()


def test_event_version_is_checked(order_data):
    with pytest.raises(ValidationError):
        OrderEvent(version=2, order=order_data)

