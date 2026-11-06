from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


def test_rest_to_sql_preserves_business_values(http, order_data, processed, sql):
    assert http("POST", "/orders", order_data)[0] == 202
    result = processed(order_data["order_id"])
    rows = sql("SELECT * FROM orders WHERE order_id = %s", (order_data["order_id"],))
    assert len(rows) == 1
    assert rows[0]["amount"] == Decimal("42.50")
    assert rows[0]["customer_id"] == order_data["customer_id"]
    assert rows[0]["currency"] == "BRL"
    assert rows[0]["status"] == result["status"] == "PROCESSED"
    assert rows[0]["processed_at"] is not None


def test_customer_text_is_data_not_sql(http, order_data, processed, sql):
    order_data["customer_id"] = "aluno'; DROP TABLE orders; --"
    assert http("POST", "/orders", order_data)[0] == 202
    processed(order_data["order_id"])
    rows = sql("SELECT customer_id FROM orders WHERE order_id = %s", (order_data["order_id"],))
    assert rows[0]["customer_id"] == order_data["customer_id"]

