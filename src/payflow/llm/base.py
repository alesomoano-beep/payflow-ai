from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    """Raised when an LLM provider call fails."""


class LLMProvider(Protocol):
    """Provider-agnostic interface for structured LLM completions."""

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T: ...
