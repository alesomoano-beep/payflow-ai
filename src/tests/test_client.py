import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from payflow.client import (
    BankClient,
    BankNetworkError,
    BankResponseError,
    BankTimeoutError,
)
from payflow.schemas.domain import CardNetwork, Currency


API_KEY = "test_api_key"
MERCHANT_ID = "merchant_001"


def make_mock_response(approved: bool, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {
        "reference": "test-ref-123",
        "approved": approved,
        "auth_code": "X7K2P9" if approved else None,
        "decline_code": None if approved else "insufficient_funds",
    }
    mock.raise_for_status = MagicMock()
    return mock


class TestBankClient:
    @pytest.mark.asyncio
    async def test_context_manager_opens_and_closes(self) -> None:
        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            assert bank._client is not None
        assert bank._client.is_closed

    @pytest.mark.asyncio
    async def test_client_without_context_manager_raises(self) -> None:
        bank = BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID)
        with pytest.raises(RuntimeError, match="context manager"):
            _ = bank.client

    @pytest.mark.asyncio
    async def test_successful_authorization(self) -> None:
        mock_response = make_mock_response(approved=True)
        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            with patch.object(bank._client, "post", new_callable=AsyncMock, return_value=mock_response):
                result = await bank.authorize(
                    amount=Decimal("150.75"),
                    currency=Currency.EUR,
                    card_last4="1234",
                    card_network=CardNetwork.VISA,
                    merchant_id=MERCHANT_ID,
                    reference="test-ref-123",
                )
        assert result.approved is True
        assert result.auth_code == "X7K2P9"

    @pytest.mark.asyncio
    async def test_declined_authorization(self) -> None:
        mock_response = make_mock_response(approved=False)
        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            with patch.object(bank._client, "post", new_callable=AsyncMock, return_value=mock_response):
                result = await bank.authorize(
                    amount=Decimal("150.75"),
                    currency=Currency.EUR,
                    card_last4="1234",
                    card_network=CardNetwork.VISA,
                    merchant_id=MERCHANT_ID,
                    reference="test-ref-123",
                )
        assert result.approved is False
        assert result.decline_code == "insufficient_funds"

    @pytest.mark.asyncio
    async def test_timeout_raises_bank_timeout_error(self) -> None:
        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            with patch.object(
                bank._client, "post",
                new_callable=AsyncMock,
                side_effect=httpx.TimeoutException("timeout"),
            ):
                with pytest.raises(BankTimeoutError):
                    await bank.authorize(
                        amount=Decimal("150.75"),
                        currency=Currency.EUR,
                        card_last4="1234",
                        card_network=CardNetwork.VISA,
                        merchant_id=MERCHANT_ID,
                        reference="test-ref-123",
                    )

    @pytest.mark.asyncio
    async def test_http_error_raises_bank_response_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            with patch.object(bank._client, "post", new_callable=AsyncMock, return_value=mock_response):
                with pytest.raises(BankResponseError) as exc_info:
                    await bank.authorize(
                        amount=Decimal("150.75"),
                        currency=Currency.EUR,
                        card_last4="1234",
                        card_network=CardNetwork.VISA,
                        merchant_id=MERCHANT_ID,
                        reference="test-ref-123",
                    )
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_network_error_raises_bank_network_error(self) -> None:
        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            with patch.object(
                bank._client, "post",
                new_callable=AsyncMock,
                side_effect=httpx.RequestError("network error"),
            ):
                with pytest.raises(BankNetworkError):
                    await bank.authorize(
                        amount=Decimal("150.75"),
                        currency=Currency.EUR,
                        card_last4="1234",
                        card_network=CardNetwork.VISA,
                        merchant_id=MERCHANT_ID,
                        reference="test-ref-123",
                    )

    @pytest.mark.asyncio
    async def test_amount_converted_to_cents(self) -> None:
        payload = None
        mock_response = make_mock_response(approved=True)

        async with BankClient(api_key=API_KEY, merchant_id=MERCHANT_ID) as bank:
            async def capture_post(url, **kwargs):
                nonlocal payload
                payload = kwargs.get("json", {})
                return mock_response

            with patch.object(bank._client, "post", side_effect=capture_post):
                await bank.authorize(
                    amount=Decimal("150.75"),
                    currency=Currency.EUR,
                    card_last4="1234",
                    card_network=CardNetwork.VISA,
                    merchant_id=MERCHANT_ID,
                    reference="test-ref-123",
                )

        assert payload["amount_cents"] == 15075
