import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from scripts.common import manifest, wait_until


@pytest.fixture
def order_data():
    return {"order_id": str(uuid4()), "customer_id": "aluno-testes", "amount": "42.50", "currency": "BRL"}


@pytest.fixture(scope="session")
def infrastructure():
    # Falhar com diagnostico claro, em vez de ignorar testes de infra nao executados.
    try:
        return manifest()
    except FileNotFoundError:
        pytest.fail("Infra nao provisionada. Execute docker compose up --build -d e aguarde provision.")


@pytest.fixture(scope="session")
def http(infrastructure):
    base_url = os.getenv("BASE_URL", infrastructure["internal_base_url"] if os.getenv("LAB_MANIFEST")
                         else infrastructure["base_url"])

    def request(method, path, body=None, raw=None):
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        request = Request(base_url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            result = urlopen(request, timeout=20)
        except HTTPError as exc:
            result = exc
        with result:
            return result.status, json.loads(result.read()), result.headers

    status, body, _ = request("GET", "/health")
    assert status == 200, f"API indisponivel: {status} {body}"
    return request


@pytest.fixture
def sql():
    dsn = os.getenv("DATABASE_URL", "postgresql://training:training@localhost:5433/orders")

    def query(statement, parameters=()):
        with psycopg.connect(dsn, connect_timeout=3, row_factory=dict_row) as connection:
            return connection.execute(statement, parameters).fetchall()

    return query


@pytest.fixture
def processed(http):
    def poll(order_id, timeout=60):
        def check():
            status, body, _ = http("GET", f"/orders/{order_id}")
            assert status in (200, 404), (status, body)
            return body if status == 200 else None
        return wait_until(check, timeout=timeout, description=f"pedido {order_id} persistido")
    return poll

