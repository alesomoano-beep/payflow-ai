from decimal import Decimal
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from payflow.main import app
from payflow.schemas.domain import (
    TransactionResult,
    TransactionStatus,
    Currency,
    BatchResult,
)
from payflow.client import BankTimeoutError, BankResponseError


client = TestClient(app)


def make_result(**kwargs) -> TransactionResult:
    defaults = dict(
        status=TransactionStatus.APPROVED,
        amount=Decimal("150.75"),
        currency=Currency.EUR,
        merchant_id="merchant_001",
        authorization_code="X7K2P9",
        decline_reason=None,
    )
    defaults.update(kwargs)
    return TransactionResult(**defaults)


VALID_PAYLOAD = {
    "amount": "150.75",
    "currency": "EUR",
    "card": {
        "number_last4": "1234",
        "network": "VISA",
        "holder_name": "Ana Garcia",
    },
    "merchant_id": "merchant_001",
}


class TestAuthorizeEndpoint:
    def test_successful_authorization(self) -> None:
        mock_result = make_result()
        with patch("payflow.router.process_transaction", new_callable=AsyncMock, return_value=mock_result):
            response = client.post("/payments/authorize", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["authorization_code"] == "X7K2P9"

    def test_declined_transaction(self) -> None:
        mock_result = make_result(
            status=TransactionStatus.DECLINED,
            authorization_code=None,
            decline_reason="fondos insuficientes",
        )
        with patch("payflow.router.process_transaction", new_callable=AsyncMock, return_value=mock_result):
            response = client.post("/payments/authorize", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "declined"
        assert data["decline_reason"] == "fondos insuficientes"

    def test_invalid_amount_returns_422(self) -> None:
        payload = {**VALID_PAYLOAD, "amount": "-50"}
        response = client.post("/payments/authorize", json=payload)
        assert response.status_code == 422

    def test_amount_exceeds_limit_returns_422(self) -> None:
        payload = {**VALID_PAYLOAD, "amount": "999999"}
        response = client.post("/payments/authorize", json=payload)
        assert response.status_code == 422

    def test_invalid_currency_returns_422(self) -> None:
        payload = {**VALID_PAYLOAD, "currency": "INVALID"}
        response = client.post("/payments/authorize", json=payload)
        assert response.status_code == 422

    def test_missing_field_returns_422(self) -> None:
        payload = {**VALID_PAYLOAD}
        del payload["merchant_id"]
        response = client.post("/payments/authorize", json=payload)
        assert response.status_code == 422

    def test_bank_timeout_returns_504(self) -> None:
        with patch(
            "payflow.router.process_transaction",
            new_callable=AsyncMock,
            side_effect=BankTimeoutError(reference="test-ref"),
        ):
            response = client.post("/payments/authorize", json=VALID_PAYLOAD)
        assert response.status_code == 504

    def test_bank_error_returns_502(self) -> None:
        with patch(
            "payflow.router.process_transaction",
            new_callable=AsyncMock,
            side_effect=BankResponseError(status_code=500, reference="test-ref"),
        ):
            response = client.post("/payments/authorize", json=VALID_PAYLOAD)
        assert response.status_code == 502


class TestBatchEndpoint:
    def test_successful_batch(self) -> None:
        mock_batch = BatchResult(
            total=2,
            approved=2,
            declined=0,
            failed=0,
            results=[make_result(), make_result()],
        )
        with patch("payflow.router.process_batch", new_callable=AsyncMock, return_value=mock_batch):
            response = client.post("/payments/batch", json=[VALID_PAYLOAD, VALID_PAYLOAD])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["approved"] == 2

    def test_empty_batch_returns_422(self) -> None:
        response = client.post("/payments/batch", json=[])
        assert response.status_code == 422

    def test_batch_exceeds_limit_returns_422(self) -> None:
        response = client.post("/payments/batch", json=[VALID_PAYLOAD] * 51)
        assert response.status_code == 422


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestGetTransactionEndpoint:
    def test_returns_404(self) -> None:
        response = client.get("/payments/transaction/3fa85f64-5717-4562-b3fc-2c963f66afa6")
        assert response.status_code == 404

    def test_invalid_uuid_returns_422(self) -> None:
        response = client.get("/payments/transaction/esto-no-es-uuid")
        assert response.status_code == 422