"""End-to-end orchestration of deterministic article planning."""

from src.planning.deterministic_article_planner import (
    DeterministicArticlePlanner,
)

from .editorial_planning_result import EditorialPlanningResult
from .editorial_strategy_workflow import EditorialStrategyWorkflow


class EditorialPlanningWorkflow:
    """Coordinate editorial strategy analysis and article planning."""

    def __init__(
        self,
        strategy_workflow: EditorialStrategyWorkflow | None = None,
        article_planner: DeterministicArticlePlanner | None = None,
    ) -> None:
        """Initialize the editorial planning workflow.

        Args:
            strategy_workflow: Strategy workflow, or None for the default.
            article_planner: Article planner, or None for the default.
        """
        self.strategy_workflow = (
            strategy_workflow
            if strategy_workflow is not None
            else EditorialStrategyWorkflow()
        )
        self.article_planner = (
            article_planner
            if article_planner is not None
            else DeterministicArticlePlanner()
        )

    def process(
        self,
        *,
        title: str | None,
        body: str | None,
        source_name: str | None,
        source_url: str | None = None,
        published_at: str | None = None,
        language: str | None = None,
        country: str | None = None,
        author: str | None = None,
        images: tuple[str, ...] = (),
        attachments: tuple[str, ...] = (),
        category: str | None = None,
        tags: tuple[str, ...] = (),
        user_instruction: str | None = None,
    ) -> EditorialPlanningResult:
        """Analyze raw source fields and create an article plan.

        Args:
            title: Raw source title.
            body: Raw source body.
            source_name: Raw source name.
            source_url: Optional raw source URL.
            published_at: Optional publication timestamp.
            language: Optional source language code.
            country: Optional country associated with the source.
            author: Optional source author.
            images: Image references associated with the source.
            attachments: Attachment references associated with the source.
            category: Optional source category.
            tags: Tags associated with the source.
            user_instruction: Optional explicit editorial instruction.

        Returns:
            The editorial strategy result and deterministic article plan.
        """
        strategy_result = self.strategy_workflow.process(
            title=title,
            body=body,
            source_name=source_name,
            source_url=source_url,
            published_at=published_at,
            language=language,
            country=country,
            author=author,
            images=images,
            attachments=attachments,
            category=category,
            tags=tags,
            user_instruction=user_instruction,
        )
        intent_result = strategy_result.intent_result
        classification_result = intent_result.classification_result
        ingestion = classification_result.ingestion
        classification = classification_result.classification
        reader_intent = intent_result.reader_intent
        strategy = strategy_result.strategy
        article_plan = self.article_planner.plan(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification,
            reader_intent=reader_intent,
            strategy=strategy,
            user_instruction=user_instruction,
        )
        return EditorialPlanningResult(
            strategy_result=strategy_result,
            article_plan=article_plan,
        )
