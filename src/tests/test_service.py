import pytest
from unittest.mock import patch

from payflow.schemas.domain import (
    TransactionStatus,
    TransactionRequest,
)
from payflow.service import process_transaction, process_batch


class TestProcessTransaction:
    @pytest.mark.asyncio
    async def test_returns_transaction_result(self, basic_request: TransactionRequest) -> None:
        result = await process_transaction(basic_request)
        assert result.amount == basic_request.amount
        assert result.currency == basic_request.currency
        assert result.merchant_id == basic_request.merchant_id
        assert result.transaction_id is not None
        assert result.processed_at is not None

    @pytest.mark.asyncio
    async def test_result_is_approved_or_declined(self, basic_request: TransactionRequest) -> None:
        result = await process_transaction(basic_request)
        assert result.status in (TransactionStatus.APPROVED, TransactionStatus.DECLINED)

    @pytest.mark.asyncio
    async def test_approved_has_auth_code(self, basic_request: TransactionRequest) -> None:
        with patch("payflow.service.random.random", return_value=0.0):
            result = await process_transaction(basic_request)
        assert result.status == TransactionStatus.APPROVED
        assert result.authorization_code is not None
        assert result.decline_reason is None

    @pytest.mark.asyncio
    async def test_declined_has_reason(self, basic_request: TransactionRequest) -> None:
        with patch("payflow.service.random.random", return_value=1.0):
            result = await process_transaction(basic_request)
        assert result.status == TransactionStatus.DECLINED
        assert result.decline_reason is not None
        assert result.authorization_code is None


class TestProcessBatch:
    @pytest.mark.asyncio
    async def test_empty_batch(self) -> None:
        result = await process_batch([])
        assert result.total == 0
        assert result.approved == 0
        assert result.declined == 0

    @pytest.mark.asyncio
    async def test_batch_counts_match(self, basic_request: TransactionRequest) -> None:
        requests = [basic_request] * 5
        result = await process_batch(requests)
        assert result.total == 5
        assert result.approved + result.declined + result.failed == result.total

    @pytest.mark.asyncio
    async def test_batch_runs_in_parallel(self, basic_request: TransactionRequest) -> None:
        import time
        requests = [basic_request] * 10
        start = time.time()
        await process_batch(requests)
        elapsed = time.time() - start
        # 10 transactions × 200 ms max = 2 s sequentially
        # in parallel it should finish in under 1 s
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_approval_rate_calculation(self, basic_request: TransactionRequest) -> None:
        with patch("payflow.service.random.random", return_value=0.0):
            result = await process_batch([basic_request] * 4)
        assert result.approved == 4
        assert result.approval_rate == 100.0