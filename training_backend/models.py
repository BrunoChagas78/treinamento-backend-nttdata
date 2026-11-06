"""Contrato do pedido compartilhado pela API e pelo consumidor."""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: UUID
    customer_id: str = Field(min_length=1, max_length=100, pattern=r"\S")
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["BRL"] = "BRL"
    # Injetores didaticos, habilitados apenas no laboratorio.
    failure_mode: Literal["none", "once", "permanent"] = "none"

    def business_data(self):
        data = self.model_dump(mode="json", exclude={"failure_mode"})
        data["amount"] = format(self.amount, ".2f")
        return data


class OrderEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    order: Order

