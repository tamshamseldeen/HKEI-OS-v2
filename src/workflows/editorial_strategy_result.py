"""Immutable result of the editorial strategy workflow."""

from dataclasses import dataclass

from src.strategy.editorial_strategy import EditorialStrategy

from .editorial_intent_result import EditorialIntentResult


@dataclass(frozen=True)
class EditorialStrategyResult:
    """Represent editorial intent analysis and its strategy.

    Attributes:
        intent_result: Complete editorial intent result.
        strategy: Deterministic strategy for the editorial result.
    """

    intent_result: EditorialIntentResult
    strategy: EditorialStrategy
