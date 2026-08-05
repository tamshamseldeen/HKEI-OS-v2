"""Immutable result of the editorial planning workflow."""

from dataclasses import dataclass

from src.planning.article_plan import ArticlePlan

from .editorial_strategy_result import EditorialStrategyResult


@dataclass(frozen=True)
class EditorialPlanningResult:
    """Represent editorial strategy analysis and its article plan.

    Attributes:
        strategy_result: Complete editorial strategy result.
        article_plan: Deterministic internal article plan.
    """

    strategy_result: EditorialStrategyResult
    article_plan: ArticlePlan
