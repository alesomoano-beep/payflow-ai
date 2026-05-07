from decimal import Decimal

import pytest
from payflow.schemas.domain import (
    CardInfo,
    CardNetwork,
    Currency,
    TransactionRequest,
    TransactionResult,
    TransactionStatus,
)


class TestCardInfo:
    def test_valid_card(self) -> None:
        card = CardInfo(
            number_last4="1234",
            network=CardNetwork.VISA,
            holder_name="Ana Garcia",
        )
        assert card.number_last4 == "1234"
        assert card.network == CardNetwork.VISA

    def test_last4_must_be_digits(self) -> None:
        with pytest.raises(ValueError, match="numéricos"):
            CardInfo(
                number_last4="AB34",
                network=CardNetwork.VISA,
                holder_name="Ana Garcia",
            )

    def test_last4_must_be_4_chars(self) -> None:
        with pytest.raises(ValueError):
            CardInfo(
                number_last4="123",
                network=CardNetwork.VISA,
                holder_name="Ana Garcia",
            )


class TestTransactionRequest:
    def test_valid_request(self, basic_request: TransactionRequest) -> None:
        assert basic_request.amount == Decimal("150.75")
        assert basic_request.currency == Currency.EUR

    def test_amount_must_be_positive(self, visa_card: CardInfo) -> None:
        with pytest.raises(ValueError):
            TransactionRequest(
                amount=Decimal("-10"),
                currency=Currency.EUR,
                card=visa_card,
                merchant_id="merchant_001",
            )

    def test_amount_cannot_exceed_limit(self, visa_card: CardInfo) -> None:
        with pytest.raises(ValueError):
            TransactionRequest(
                amount=Decimal("100000"),
                currency=Currency.EUR,
                card=visa_card,
                merchant_id="merchant_001",
            )

    def test_amex_limit(self, amex_card: CardInfo) -> None:
        with pytest.raises(ValueError, match="AMEX"):
            TransactionRequest(
                amount=Decimal("15000"),
                currency=Currency.EUR,
                card=amex_card,
                merchant_id="merchant_001",
            )

    def test_idempotency_key_auto_generated(self, basic_request: TransactionRequest) -> None:
        assert basic_request.idempotency_key is not None

    def test_two_requests_have_different_keys(self, visa_card: CardInfo) -> None:
        req1 = TransactionRequest(amount=Decimal("100"), currency=Currency.EUR, card=visa_card, merchant_id="mer1")
        req2 = TransactionRequest(amount=Decimal("100"), currency=Currency.EUR, card=visa_card, merchant_id="mer1")
        assert req1.idempotency_key != req2.idempotency_key


class TestTransactionResult:
    def test_result_is_immutable(self, basic_request: TransactionRequest) -> None:
        result = TransactionResult(
            status=TransactionStatus.APPROVED,
            amount=basic_request.amount,
            currency=basic_request.currency,
            merchant_id=basic_request.merchant_id,
            authorization_code="X7K2P9",
        )
        with pytest.raises(Exception):
            result.status = TransactionStatus.DECLINED
