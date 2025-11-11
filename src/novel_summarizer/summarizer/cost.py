from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

# (input per 1K tokens, output per 1K tokens)
pricing = {
    "gpt-4o-mini": (0.15, 0.60),  # https://platform.openai.com/docs/models/gpt-4o-mini
    "gpt-4o-2024-08-06": (
        2.50,
        10.00,
    ),  # https://platform.openai.com/docs/models/gpt-4o
    "gpt-5": (1.25, 10),  # hhttps://platform.openai.com/docs/models/gpt-5
    "gpt-5-mini": (0.25, 2),  # https://platform.openai.com/docs/models/gpt-5-mini
    "gpt-5-nano": (0.05, 0.4),  # https://platform.openai.com/docs/models/gpt-5-nano
    "gpt-5-pro": (15, 120),  # https://platform.openai.com/docs/models/gpt-5-pro
    "gpt-4.1": (2, 8),  # https://platform.openai.com/docs/models/gpt-4.1
}


class Cost(BaseModel):
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    input_characters: int = Field(default=0)
    output_characters: int = Field(default=0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def total_characters(self) -> int:
        return self.input_characters + self.output_characters

    def price(self, model: str) -> float:
        (input_price, output_price) = pricing[model]
        input_cost = self.input_tokens / (1000 * 1000) * input_price
        output_cost = self.output_tokens / (1000 * 1000) * output_price
        return input_cost + output_cost

    def __add__(self, other: "Cost") -> "Cost":
        return Cost(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            input_characters=self.input_characters + other.input_characters,
            output_characters=self.output_characters + other.output_characters,
        )

    def tokens_per_character(self) -> float | None:
        total_characters = self.total_characters
        if total_characters == 0:
            return None
        return self.total_tokens / total_characters


def cost_from_usage(usage: Any) -> Cost:
    """Create a Cost instance from an OpenAI usage payload (dict or object)."""

    def _extract(primary: str, secondary: str | None = None) -> int:
        candidates = [primary]
        if secondary is not None:
            candidates.append(secondary)

        for key in candidates:
            value: Any
            if isinstance(usage, Mapping):
                value = usage.get(key)  # type: ignore[assignment]
            else:
                value = getattr(usage, key, None)

            if value is not None:
                return int(value)

        return 0

    if usage is None:
        return Cost()

    return Cost(
        input_tokens=_extract("input_tokens", "prompt_tokens"),
        output_tokens=_extract("output_tokens", "completion_tokens"),
        input_characters=_extract("input_characters"),
        output_characters=_extract("output_characters"),
    )
