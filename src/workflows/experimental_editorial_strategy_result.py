"""Immutable result for experimental format-aware strategy adaptation."""

from dataclasses import dataclass

from src.strategy.editorial_strategy import EditorialStrategy

from .editorial_format_result import EditorialFormatResult
from .editorial_strategy_result import EditorialStrategyResult


@dataclass(frozen=True)
class ExperimentalEditorialStrategyResult:
    """Represent parallel strategy, format, and adapted strategy results.

    Attributes:
        strategy_result: Unchanged result from the existing strategy workflow.
        format_result: Unchanged result from the additive format workflow.
        adapted_strategy: Separately adapted experimental editorial strategy.
    """

    strategy_result: EditorialStrategyResult
    format_result: EditorialFormatResult
    adapted_strategy: EditorialStrategy
