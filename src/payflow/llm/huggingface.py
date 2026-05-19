import json
import logging
import os
import re
from typing import TypeVar

from huggingface_hub import AsyncInferenceClient
from pydantic import BaseModel

from payflow.llm.base import LLMProviderError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class HuggingFaceProvider:
    """LLM provider backed by Hugging Face Inference API, using JSON mode for structured output."""

    def __init__(
        self,
        model: str = "Qwen/Qwen2.5-72B-Instruct",
        timeout: float = 30.0,
        max_tokens: int = 512,
    ) -> None:
        self._client = AsyncInferenceClient(
            api_key=os.environ["HF_API_KEY"],
            timeout=timeout,
        )
        self._model = model
        self._max_tokens = max_tokens

    async def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        schema = json.dumps(response_model.model_json_schema(), indent=2)
        system_with_schema = f"{system}\n\nRespond with a JSON object that strictly follows this schema:\n{schema}"
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_with_schema},
                    {"role": "user", "content": user},
                ],
                max_tokens=self._max_tokens,
                temperature=0,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or ""
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise LLMProviderError(f"No JSON object found in response: {text!r}")
            logger.debug(
                "huggingface_completion_ok",
                extra={
                    "model": self._model,
                    "input_tokens": response.usage.prompt_tokens if response.usage else None,
                    "output_tokens": response.usage.completion_tokens if response.usage else None,
                },
            )
            return response_model.model_validate_json(match.group())
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(str(exc)) from exc
