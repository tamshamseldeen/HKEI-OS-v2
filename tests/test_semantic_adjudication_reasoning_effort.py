"""Tests for provider-neutral semantic adjudication reasoning effort."""

from src.adjudication.semantic_adjudication_reasoning_effort import (
    SemanticAdjudicationReasoningEffort,
)


def test_reasoning_effort_has_exact_portable_values() -> None:
    assert tuple(effort.value for effort in SemanticAdjudicationReasoningEffort) == (
        "MINIMAL",
        "LOW",
        "MEDIUM",
        "HIGH",
    )
