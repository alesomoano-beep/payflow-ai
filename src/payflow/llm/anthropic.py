import logging
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from payflow.llm.base import LLMProviderError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AnthropicProvider:
    """LLM provider backed by Anthropic Claude, using tool_use for structured output."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        timeout: float = 10.0,
        max_tokens: int = 300,
    ) -> None:
        self._client = AsyncAnthropic(timeout=timeout)
        self._model = model
        self._max_tokens = max_tokens

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=0,
                system=system,
                tools=[
                    {
                        "name": "submit_result",
                        "description": "Submit the structured result",
                        "input_schema": response_model.model_json_schema(),
                    }
                ],
                tool_choice={"type": "tool", "name": "submit_result"},
                messages=[{"role": "user", "content": user}],
            )
            tool_use = next(b for b in response.content if b.type == "tool_use")
            logger.debug(
                "anthropic_completion_ok",
                extra={
                    "model": self._model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )
            return response_model(**tool_use.input)
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc
