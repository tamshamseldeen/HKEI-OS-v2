"""Tests for provider-neutral semantic adjudication usage telemetry."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage


def test_usage_has_exact_field_order_and_is_frozen() -> None:
    usage = SemanticAdjudicationUsage(10, 5, None)
    assert tuple(field.name for field in fields(usage)) == (
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
    )
    with pytest.raises(FrozenInstanceError):
        usage.input_tokens = 11


@pytest.mark.parametrize("reasoning_tokens", (None, 0, 3))
def test_valid_reasoning_token_values_are_preserved(
    reasoning_tokens: int | None,
) -> None:
    usage = SemanticAdjudicationUsage(10, 5, reasoning_tokens)
    assert usage.reasoning_tokens == reasoning_tokens


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens", "reasoning_tokens", "message"),
    (
        (-1, 0, None, "input_tokens must be a non-negative integer"),
        (0, -1, None, "output_tokens must be a non-negative integer"),
        (0, 1, -1, "reasoning_tokens must be a non-negative integer"),
        (0, 1, 2, "reasoning_tokens must not exceed output_tokens"),
        (True, 1, None, "input_tokens must be a non-negative integer"),
    ),
)
def test_invalid_usage_is_rejected(
    input_tokens: object,
    output_tokens: object,
    reasoning_tokens: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        SemanticAdjudicationUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
        )
