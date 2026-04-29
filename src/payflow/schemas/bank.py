from typing import Any

from pydantic import BaseModel, Field


class BankTransactionPayload(BaseModel):
    """What we send to the bank. Their API, their format."""
    amount_cents: int          # banks work in cents, no decimals
    currency: str
    card_last4: str
    card_network: str
    merchant_id: str
    reference: str             # our idempotency_key


class BankTransactionResponse(BaseModel):
    """What the bank returns to us."""
    reference: str
    approved: bool
    auth_code: str | None = None
    decline_code: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
