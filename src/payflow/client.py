from decimal import Decimal

import httpx

from payflow.schemas.bank import BankTransactionPayload, BankTransactionResponse
from payflow.schemas.domain import CardNetwork, Currency


class BankClientError(Exception):
    def __init__(self, reference: str = "") -> None:
        self.reference = reference
        super().__init__(reference)


class BankTimeoutError(BankClientError):
    pass


class BankNetworkError(BankClientError):
    pass


class BankResponseError(BankClientError):
    def __init__(self, status_code: int, reference: str = "") -> None:
        self.status_code = status_code
        super().__init__(reference)


class BankClient:
    def __init__(
        self,
        api_key: str,
        merchant_id: str,
        base_url: str = "https://bank.example.com",
    ) -> None:
        self._api_key = api_key
        self._merchant_id = merchant_id
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BankClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("BankClient must be used as a context manager")
        return self._client

    async def authorize(
        self,
        amount: Decimal,
        currency: Currency,
        card_last4: str,
        card_network: CardNetwork,
        merchant_id: str,
        reference: str,
    ) -> BankTransactionResponse:
        payload = BankTransactionPayload(
            amount_cents=int(amount * 100),
            currency=str(currency),
            card_last4=card_last4,
            card_network=str(card_network),
            merchant_id=merchant_id,
            reference=reference,
        )
        try:
            response = await self._client.post("/authorize", json=payload.model_dump())
            response.raise_for_status()
            return BankTransactionResponse(**response.json())
        except httpx.TimeoutException:
            raise BankTimeoutError(reference=reference)
        except httpx.HTTPStatusError as e:
            raise BankResponseError(status_code=e.response.status_code, reference=reference)
        except httpx.RequestError:
            raise BankNetworkError(reference=reference)
