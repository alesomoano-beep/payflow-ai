import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from payflow.client import BankClientError, BankTimeoutError
from payflow.schemas.domain import BatchResult, TransactionRequest, TransactionResult
from payflow.service import process_batch, process_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


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
    try:
        return await process_transaction(request)

    except BankTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Bank did not respond in time, please retry",
        )
    except BankClientError as e:
        logger.error("Bank error for ref=%s: %s", request.idempotency_key, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bank returned an unexpected error",
        )


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

    try:
        return await process_batch(requests)

    except BankTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Bank did not respond in time, please retry",
        )
    except BankClientError as e:
        logger.error("Bank error during batch: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bank returned an unexpected error",
        )


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