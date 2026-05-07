from decimal import Decimal

import pytest

from payflow.schemas.domain import (
    CardInfo,
    CardNetwork,
    Currency,
    TransactionRequest,
)


@pytest.fixture
def visa_card() -> CardInfo:
    return CardInfo(
        number_last4="1234",
        network=CardNetwork.VISA,
        holder_name="Ana Garcia",
    )


@pytest.fixture
def amex_card() -> CardInfo:
    return CardInfo(
        number_last4="9999",
        network=CardNetwork.AMEX,
        holder_name="Carlos Lopez",
    )


@pytest.fixture
def basic_request(visa_card: CardInfo) -> TransactionRequest:
    return TransactionRequest(
        amount=Decimal("150.75"),
        currency=Currency.EUR,
        card=visa_card,
        merchant_id="merchant_001",
    )


@pytest.fixture
def high_value_request(visa_card: CardInfo) -> TransactionRequest:
    return TransactionRequest(
        amount=Decimal("25000.00"),
        currency=Currency.EUR,
        card=visa_card,
        merchant_id="merchant_001",
    )
