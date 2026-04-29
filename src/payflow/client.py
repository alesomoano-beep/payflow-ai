import logging
from decimal import Decimal
from typing import Any

import httpx

from payflow.schemas.bank import BankTransactionPayload, BankTransactionResponse
from payflow.schemas.domain import CardNetwork, Currency, TransactionStatus

logger = logging.getLogger(__name__)


# --- Client ---

class BankClient:
    """
    Async HTTP client toward the external bank.
    Uses httpx.AsyncClient with timeout, retries and error handling.
    """

    BASE_URL = "https://sandbox.fakebank.internal/v1"
    TIMEOUT = httpx.Timeout(connect=2.0, read=10.0, write=5.0, pool=2.0)

    def __init__(self, api_key: str, merchant_id: str) -> None:
        self._api_key = api_key
        self._merchant_id = merchant_id
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BankClient":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.TIMEOUT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-Merchant-ID": self._merchant_id,
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("BankClient must be used as async context manager")
        return self._client

    def _to_payload(
        self,
        amount: Decimal,
        currency: Currency,
        card_last4: str,
        card_network: CardNetwork,
        merchant_id: str,
        reference: str,
    ) -> BankTransactionPayload:
        """Converts our models into the format the bank expects."""
        amount_cents = int(amount * 100)  # 150.75 EUR → 15075
        return BankTransactionPayload(
            amount_cents=amount_cents,
            currency=currency.value,
            card_last4=card_last4,
            card_network=card_network.value,
            merchant_id=merchant_id,
            reference=reference,
        )

    async def authorize(
        self,
        amount: Decimal,
        currency: Currency,
        card_last4: str,
        card_network: CardNetwork,
        merchant_id: str,
        reference: str,
    ) -> BankTransactionResponse:
        """
        Calls the bank's authorization endpoint.
        Handles network errors, timeouts and unexpected responses.
        """
        payload = self._to_payload(
            amount, currency, card_last4, card_network, merchant_id, reference
        )

        try:
            logger.info("Authorizing transaction ref=%s amount=%s%s", reference, amount, currency)

            response = await self.client.post(
                "/authorize",
                json=payload.model_dump(),
            )
            response.raise_for_status()

            raw = response.json()
            return BankTransactionResponse(
                reference=raw["reference"],
                approved=raw["approved"],
                auth_code=raw.get("auth_code"),
                decline_code=raw.get("decline_code"),
                raw_response=raw,
            )

        except httpx.TimeoutException:
            logger.error("Timeout calling bank for ref=%s", reference)
            raise BankTimeoutError(reference=reference)

        except httpx.HTTPStatusError as e:
            logger.error("Bank returned HTTP %s for ref=%s", e.response.status_code, reference)
            raise BankResponseError(status_code=e.response.status_code, reference=reference)

        except httpx.RequestError as e:
            logger.error("Network error calling bank for ref=%s: %s", reference, e)
            raise BankNetworkError(reference=reference)


# --- Client-specific exceptions ---

class BankClientError(Exception):
    """Base class for all bank client errors."""
    def __init__(self, reference: str, message: str) -> None:
        self.reference = reference
        super().__init__(message)


class BankTimeoutError(BankClientError):
    def __init__(self, reference: str) -> None:
        super().__init__(reference, f"Bank timeout for transaction {reference}")


class BankResponseError(BankClientError):
    def __init__(self, status_code: int, reference: str) -> None:
        self.status_code = status_code
        super().__init__(reference, f"Bank returned {status_code} for transaction {reference}")


class BankNetworkError(BankClientError):
    def __init__(self, reference: str) -> None:
        super().__init__(reference, f"Network error for trans