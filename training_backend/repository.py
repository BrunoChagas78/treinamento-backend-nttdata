from psycopg.types.json import Jsonb

from training_backend.resources import database


def find_order(order_id):
    with database() as connection:
        return connection.execute(
            "SELECT order_id, customer_id, amount, currency, status, receive_count, processed_at "
            "FROM orders WHERE order_id = %s", (str(order_id),),
        ).fetchone()


def save_order(order, receive_count, message_id):
    """PK + transacao protegem contra entrega duplicada, inclusive concorrente."""
    payload = order.business_data()
    with database() as connection:
        inserted = connection.execute(
            "INSERT INTO orders (order_id, customer_id, amount, currency, payload, receive_count) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (order_id) DO NOTHING "
            "RETURNING order_id",
            (str(order.order_id), order.customer_id, order.amount, order.currency,
             Jsonb(payload), receive_count),
        ).fetchone()
        outcome = "created" if inserted else "duplicate"
        if not inserted:
            existing = connection.execute(
                "SELECT payload FROM orders WHERE order_id = %s", (str(order.order_id),),
            ).fetchone()
            if existing["payload"] != payload:
                raise ValueError("order_id reutilizado com dados diferentes")
        connection.execute(
            "INSERT INTO order_receipts (message_id, order_id, outcome, receive_count) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (message_id) DO NOTHING",
            (message_id, str(order.order_id), outcome, receive_count),
        )
        return outcome

