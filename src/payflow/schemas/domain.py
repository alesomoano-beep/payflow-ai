from datetime import datetime, UTC
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Currency(StrEnum):
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    FAILED = "failed"


class CardNetwork(StrEnum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMEX = "AMEX"


class CardInfo(BaseModel):
    number_last4: str = Field(..., min_length=4, max_length=4)
    network: CardNetwork
    holder_name: str = Field(..., min_length=2, max_length=100)

    @field_validator("number_last4")
    @classmethod
    def must_be_digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Los últimos 4 dígitos deben ser numéricos")
        return value


class TransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"), le=Decimal("50000"))
    currency: Currency
    card: CardInfo
    merchant_id: str = Field(..., min_length=3, max_length=50)
    idempotency_key: UUID = Field(default_factory=uuid4)

    @model_validator(mode="after")
    def amex_limit(self) -> "TransactionRequest":
        if self.card.network == CardNetwork.AMEX and self.amount > Decimal("10000"):
            raise ValueError("AMEX: límite de 10.000 por transacción")
        return self


class TransactionResult(BaseModel):
    transaction_id: UUID = Field(default_factory=uuid4)
    status: TransactionStatus
    amount: Decimal
    currency: Currency
    merchant_id: str
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authorization_code: str | None = None
    decline_reason: str | None = None

    model_config = {"frozen": True}


class BatchResult(BaseModel):
    total: int
    approved: int
    declined: int
    failed: int
    results: list[TransactionResult]

    @property
    def approval_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.approved / self.total * 100, 2)
