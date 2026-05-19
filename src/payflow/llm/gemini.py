import logging
import os
import re
from typing import TypeVar, cast

from google import genai
from google.genai import types
from pydantic import BaseModel

from payflow.llm.base import LLMProviderError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider:
    """LLM provider backed by Google Gemini, using response_schema for structured output."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        timeout: float = 10.0,
        max_tokens: int = 512,
    ) -> None:
        self._client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )
        self._model = model
        self._max_tokens = max_tokens

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0,
                    max_output_tokens=self._max_tokens,
                    response_mime_type="application/json",
                    response_schema=response_model,
                ),
            )
            logger.debug(
                "gemini_completion_ok",
                extra={
                    "model": self._model,
                    "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                    "output_tokens": response.usage_metadata.candidates_token_count
                    if response.usage_metadata
                    else None,
                },
            )
            parsed = response.parsed
            if parsed is not None:
                return cast(T, parsed)
            text = response.text or ""
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise LLMProviderError(f"No JSON object found in response: {text!r}")
            return response_model.model_validate_json(match.group())
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc
