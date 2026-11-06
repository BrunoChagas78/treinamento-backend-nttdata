import os
from functools import lru_cache

import boto3
import psycopg
from botocore.config import Config
from psycopg.rows import dict_row


@lru_cache
def sqs():
    # AWS_ENDPOINT_URL aponta ao LocalStack; sem ela, boto3 usa a AWS.
    return boto3.client(
        "sqs", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        config=Config(connect_timeout=2, read_timeout=5, retries={"max_attempts": 1}),
    )


def database():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3, row_factory=dict_row)


def queue_url():
    return os.environ["ORDERS_QUEUE_URL"]

