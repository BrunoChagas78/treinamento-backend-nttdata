import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

import boto3
from botocore.config import Config


def local_endpoint():
    endpoint = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    host = urlsplit(endpoint).hostname
    if host not in {"localhost", "127.0.0.1", "localstack", "host.docker.internal"}:
        raise ValueError("Este laboratorio aceita somente endpoints locais do LocalStack")
    return endpoint.rstrip("/")


def client(service):
    return boto3.client(service, endpoint_url=local_endpoint(), region_name="us-east-1",
                        aws_access_key_id="test", aws_secret_access_key="test",
                        config=Config(connect_timeout=3, read_timeout=120,
                                      retries={"max_attempts": 2}))


def rebase(url, origin):
    return origin.rstrip("/") + urlsplit(url).path


def manifest():
    return json.loads(Path(os.getenv("LAB_MANIFEST", ".local/manifest.json")).read_text())


def wait_until(check, timeout=240, interval=1, description="condicao"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(interval)
    raise TimeoutError(f"Tempo esgotado ({timeout}s): {description}")
