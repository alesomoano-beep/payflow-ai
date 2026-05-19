import hashlib
import json
import logging
import time
from decimal import Decimal
from typing import cast

from cachetools import LRUCache
from pydantic import BaseModel

from payflow.llm import HuggingFaceProvider, LLMProvider, LLMProviderError
from payflow.schemas.domain import CardNetwork, TransactionRequest

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    approved: bool
    confidence: float
    reason: str
    flags: list[str]


class LLMAnalysis(BaseModel):
    approved: bool
    reason: str
    flags: list[str]


_cache: LRUCache[str, LLMAnalysis] = LRUCache(maxsize=1000)
_default_provider: LLMProvider = HuggingFaceProvider()


SYSTEM_PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """
You are a payment validation agent specialized in detecting
inconsistencies in transaction data.

Some deterministic flags have already been computed and will be provided to you.
Your job is to detect additional fuzzy patterns:
- Suspicious merchant IDs
- Unusual amount patterns (too round, too specific)
- Inconsistencies between holder name and card data
- Any other red flags not covered by the pre-computed flags

Respond ONLY with a JSON object, no markdown, no explanation:
{
  "approved": true or false,
  "reason": "brief explanation",
  "flags": ["flag1", "flag2"]
}
"""


# --- 1. Deterministic validation ---


def run_rules(request: TransactionRequest) -> list[str]:
    """Evaluates deterministic rules in code. Fast, auditable, no LLM needed."""
    flags: list[str] = []

    if request.card.network == CardNetwork.AMEX and request.amount > Decimal("10000"):
        flags.append("high_amount_amex")

    if request.amount > Decimal("5000") and request.amount % 1000 == 0:
        flags.append("suspicious_round_amount")

    if len(request.merchant_id) < 5:
        flags.append("short_merchant_id")

    return flags


# --- 2. AI anomaly detection ---


def _build_prompt(request: TransactionRequest, rule_flags: list[str]) -> str:
    transaction_data = json.dumps(
        {
            "amount": str(request.amount),
            "currency": request.currency,
            "network": request.card.network,
            "last4": request.card.number_last4,
            "holder_name": request.card.holder_name,
            "merchant_id": request.merchant_id,
        },
        ensure_ascii=True,
    )
    flags_section = ", ".join(rule_flags) if rule_flags else "none"
    return f"""
<transaction>
{transaction_data}
</transaction>

Pre-computed flags: {flags_section}

Detect any additional fuzzy patterns not already flagged above.
Respond with the JSON object only.
"""


def _cache_key(request: TransactionRequest, rule_flags: list[str]) -> str:
    payload = (
        f"{request.amount}:{request.currency}:{request.card.network}"
        f":{request.merchant_id}:{sorted(rule_flags)}:{SYSTEM_PROMPT_VERSION}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()


async def run_llm_analysis(
    request: TransactionRequest,
    rule_flags: list[str],
    provider: LLMProvider | None = None,
) -> LLMAnalysis:
    """Calls the LLM provider to detect fuzzy anomalies not covered by deterministic rules."""
    key = _cache_key(request, rule_flags)
    if key in _cache:
        logger.info("llm_analysis_cache_hit", extra={"merchant_id": request.merchant_id})
        return cast(LLMAnalysis, _cache[key])

    llm = provider or _default_provider
    t0 = time.monotonic()
    try:
        result = await llm.complete_structured(
            system=SYSTEM_PROMPT,
            user=_build_prompt(request, rule_flags),
            response_model=LLMAnalysis,
        )
        _cache[key] = result
        logger.info(
            "llm_analysis_ok",
            extra={
                "merchant_id": request.merchant_id,
                "amount": str(request.amount),
                "currency": request.currency,
                "rule_flags": rule_flags,
                "llm_flags": result.flags,
                "approved": result.approved,
                "prompt_version": SYSTEM_PROMPT_VERSION,
                "latency_ms": round((time.monotonic() - t0) * 1000),
            },
        )
        return result
    except LLMProviderError as exc:
        logger.warning("llm_analysis_failed: %s", exc)
        logger.warning(
            "llm_analysis_failed",
            extra={
                "merchant_id": request.merchant_id,
                "error": str(exc),
                "latency_ms": round((time.monotonic() - t0) * 1000),
            },
        )
        return LLMAnalysis(
            approved=False,
            reason="LLM analysis unavailable, defaulting to reject",
            flags=["llm_unavailable"],
        )


# --- 3. Final decision engine ---


def combine_results(rule_flags: list[str], llm: LLMAnalysis) -> ValidationResult:
    """Merges deterministic flags with LLM analysis into a final decision."""
    all_flags = list(set(rule_flags + llm.flags))
    approved = llm.approved and not rule_flags
    confidence = max(0.0, round(1.0 - len(all_flags) * 0.2, 2))
    return ValidationResult(
        approved=approved,
        confidence=confidence,
        reason=llm.reason,
        flags=all_flags,
    )


# --- Entrypoint ---


async def run_validator(
    request: TransactionRequest,
    provider: LLMProvider | None = None,
) -> ValidationResult:
    """Orchestrates rules, LLM analysis, and final decision."""
    rule_flags = run_rules(request)
    llm = await run_llm_analysis(request, rule_flags, provider=provider)
    return combine_results(rule_flags, llm)
