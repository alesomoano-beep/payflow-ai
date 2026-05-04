import logging
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from payflow.client import BankClientError, BankTimeoutError
from payflow.service import process_batch, process_transaction
from payflow.schemas.domain import BatchResult, TransactionRequest, TransactionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@contextmanager
def _handle_bank_errors(log_context: str):
    try:
        yield
    except BankTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Bank did not respond in time, please retry",
        )
    except BankClientError as e:
        logger.error("Bank error %s: %s", log_context, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bank returned an unexpected error",
        )


@router.post(
    "/authorize",
    response_model=TransactionResult,
    status_code=status.HTTP_200_OK,
    summary="Authorize a single transaction",
)
async def authorize(request: TransactionRequest) -> TransactionResult:
    """
    Authorizes a single payment transaction.
    - Validates card, amount and currency automatically via Pydantic
    - Returns the result with authorization code or decline reason
    """
    with _handle_bank_errors(f"ref={request.idempotency_key}"):
        return await process_transaction(request)


@router.post(
    "/batch",
    response_model=BatchResult,
    status_code=status.HTTP_200_OK,
    summary="Process a batch of transactions in parallel",
)
async def authorize_batch(requests: list[TransactionRequest]) -> BatchResult:
    """
    Processes up to 50 transactions in parallel.

    - All transactions run concurrently via asyncio.gather
    - Returns aggregated results with approval rate
    """
    if len(requests) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Batch size cannot exceed 50 transactions",
        )

    if not requests:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Batch cannot be empty",
        )

    with _handle_bank_errors("batch"):
        return await process_batch(requests)


@router.get(
    "/transaction/{transaction_id}",
    response_model=TransactionResult,
    summary="Get transaction by ID",
)
async def get_transaction(transaction_id: UUID) -> TransactionResult:
    """
    Retrieves a transaction by its ID.
    In phase 3 this will query a real database.
    """
    # Placeholder until we add persistence in phase 3
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Transaction {transaction_id} not found",
    )