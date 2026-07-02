"""Configurable model pricing and cost calculation."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


DEFAULT_PRICING_USD_PER_MILLION: dict[str, ModelPricing] = {
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00),
    "claude-sonnet-5": ModelPricing(3.00, 15.00),
    "claude-opus-4-8": ModelPricing(15.00, 75.00),
    "claude-haiku-4-5-20251001": ModelPricing(1.00, 5.00),
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.00),
    "llama-3.3-70b-versatile": ModelPricing(0.59, 0.79),
    "llama-3.1-8b-instant": ModelPricing(0.05, 0.08),
    "gpt-4.1": ModelPricing(2.00, 8.00),
    "gpt-4.1-mini": ModelPricing(0.40, 1.60),
    "gemini-1.5-pro": ModelPricing(1.25, 5.00),
    "gemini-1.5-flash": ModelPricing(0.075, 0.30),
    "gemini-2.0-flash": ModelPricing(0.10, 0.40),
    "gemini-2.0-flash-lite": ModelPricing(0.075, 0.30),
    "deepseek-chat": ModelPricing(0.27, 1.10),
    "deepseek-reasoner": ModelPricing(0.55, 2.19),
}


def _parse_overrides(raw: str) -> dict[str, ModelPricing]:
    if not raw.strip():
        return {}
    parsed = json.loads(raw)
    overrides: dict[str, ModelPricing] = {}
    for model, value in parsed.items():
        if not isinstance(value, dict):
            continue
        input_price = float(value.get("input_per_million", 0))
        output_price = float(value.get("output_per_million", 0))
        if input_price >= 0 and output_price >= 0:
            overrides[str(model)] = ModelPricing(input_price, output_price)
    return overrides


def pricing_config() -> dict[str, ModelPricing]:
    pricing = dict(DEFAULT_PRICING_USD_PER_MILLION)
    try:
        pricing.update(_parse_overrides(settings.LLM_PRICING_OVERRIDES_JSON))
    except (TypeError, ValueError, json.JSONDecodeError):
        # Invalid pricing overrides must not break investigation execution.
        pass
    return pricing


def estimate_cost_usd(
    model: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    pricing: dict[str, ModelPricing] | None = None,
) -> float:
    price = (pricing or pricing_config()).get(model)
    if not price:
        return 0.0
    input_cost = (max(prompt_tokens, 0) / 1_000_000) * price.input_per_million
    output_cost = (max(completion_tokens, 0) / 1_000_000) * price.output_per_million
    return round(input_cost + output_cost, 8)
