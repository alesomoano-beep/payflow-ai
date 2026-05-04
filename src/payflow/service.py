import asyncio
import random
import string
from decimal import Decimal

from payflow.schemas.domain import (
    BatchResult,
    CardNetwork,
    TransactionRequest,
    TransactionResult,
    TransactionStatus,
)


def _generate_auth_code() -> str:
    """Generates a 6-character alphanumeric authorization code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _simulate_bank_decision(request: TransactionRequest) -> tuple[TransactionStatus, str | None, str | None]:
    """
    Simulates the bank’s decision. In phase 3 this will be a real AI agent.
    Returns: status, authorization_code, decline_reason
    """
    approval_rate = 0.7 if request.card.network == CardNetwork.AMEX else 0.9

    # Large transactions have more friction
    if request.amount > Decimal("10000"):
        approval_rate -= 0.2

    if random.random() < approval_rate:
        return TransactionStatus.APPROVED, _generate_auth_code(), None
    else:
        reasons = [
            "fondos insuficientes",
            "límite diario excedido",
            "tarjeta bloqueada",
        ]
        return TransactionStatus.DECLINED, None, random.choice(reasons)


async def process_transaction(request: TransactionRequest) -> TransactionResult:
    """
    Processes a single transaction asynchronously.
    The await simulates latency of calling an external bank.
    """
    await asyncio.sleep(random.uniform(0.05, 0.2))

    status, auth_code, decline_reason = _simulate_bank_decision(request)

    return TransactionResult(
        status=status,
        amount=request.amount,
        currency=request.currency,
        merchant_id=request.merchant_id,
        authorization_code=auth_code,
        decline_reason=decline_reason,
    )


def _build_batch_result(results: list[TransactionResult]) -> BatchResult:
    approved = sum(1 for r in results if r.status == TransactionStatus.APPROVED)
    declined = sum(1 for r in results if r.status == TransactionStatus.DECLINED)
    failed = sum(1 for r in results if r.status == TransactionStatus.FAILED)
    return BatchResult(
        total=len(results),
        approved=approved,
        declined=declined,
        failed=failed,
        results=list(results),
    )


async def process_batch(requests: list[TransactionRequest]) -> BatchResult:
    """
    Processes multiple transactions in parallel using asyncio.gather.
    If they were sequential: 10 transactions × 150 ms = ~1.5 seconds.
    In parallel: 10 transactions × 150 ms = ~150 ms (10× faster).
    """
    if not requests:
        return BatchResult(total=0, approved=0, declined=0, failed=0, results=[])

    # Aquí está la magia: todas las transacciones vuelan a la vez
    results: list[TransactionResult] = await asyncio.gather(
        *[process_transaction(req) for req in requests],
        return_exceptions=False,
    )

    return _build_batch_result(results)


async def process_batch_with_limit(
    requests: list[TransactionRequest],
    concurrency: int = 5,
) -> BatchResult:
    """
    Advanced version: limits how many transactions run in parallel at the same time.
    Useful when the external bank has a request-per-second limit.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _guarded(req: TransactionRequest) -> TransactionResult:
        async with semaphore:
            return await process_transaction(req)

    results: list[TransactionResult] = await asyncio.gather(
        *[_guarded(req) for req in requests]
    )

    return _build_batch_result(results)