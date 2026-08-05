"""Token cost calculator — Anthropic and OpenAI pricing as of Aug 2026."""
from __future__ import annotations
from typing import Optional

# Prices in USD per million tokens (input, output)
_ANTHROPIC_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-20251101":      (15.00, 75.00),
    "claude-sonnet-5-20251101":     (3.00,  15.00),
    "claude-sonnet-4-6":            (3.00,  15.00),
    "claude-sonnet-4-5":            (3.00,  15.00),
    "claude-haiku-4-5-20251001":    (0.80,   4.00),
    "claude-opus-4-5":             (15.00,  75.00),
    "claude-haiku-3-5":             (0.80,   4.00),
    "claude-3-5-sonnet-20241022":   (3.00,  15.00),
    "claude-3-5-haiku-20241022":    (0.80,   4.00),
    "claude-3-opus-20240229":      (15.00,  75.00),
}

_OPENAI_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o":              (2.50,  10.00),
    "gpt-4o-mini":         (0.15,   0.60),
    "gpt-4-turbo":        (10.00,  30.00),
    "gpt-4":              (30.00,  60.00),
    "gpt-3.5-turbo":       (0.50,   1.50),
    "o1":                 (15.00,  60.00),
    "o1-mini":             (3.00,  12.00),
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    provider: str = "anthropic",
) -> Optional[float]:
    """Return cost in USD, or None if model is unknown."""
    table = _ANTHROPIC_PRICES if provider == "anthropic" else _OPENAI_PRICES
    # Exact match first, then prefix match
    prices = table.get(model)
    if prices is None:
        for key, val in table.items():
            if model.startswith(key) or key.startswith(model):
                prices = val
                break
    if prices is None:
        return None
    input_cost  = (input_tokens  / 1_000_000) * prices[0]
    output_cost = (output_tokens / 1_000_000) * prices[1]
    return round(input_cost + output_cost, 6)


def format_cost(usd: Optional[float]) -> str:
    if usd is None:
        return "—"
    if usd < 0.001:
        return f"${usd * 1000:.4f}m"
    return f"${usd:.4f}"
