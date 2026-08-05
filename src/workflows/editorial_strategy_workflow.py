"""End-to-end orchestration of deterministic editorial strategy."""

from src.strategy.deterministic_editorial_strategy_engine import (
    DeterministicEditorialStrategyEngine,
)

from .editorial_intent_workflow import EditorialIntentWorkflow
from .editorial_strategy_result import EditorialStrategyResult


class EditorialStrategyWorkflow:
    """Coordinate editorial intent analysis and strategy selection."""

    def __init__(
        self,
        intent_workflow: EditorialIntentWorkflow | None = None,
        strategy_engine: DeterministicEditorialStrategyEngine | None = None,
    ) -> None:
        """Initialize the editorial strategy workflow.

        Args:
            intent_workflow: Intent workflow, or None to create the default.
            strategy_engine: Strategy engine, or None to create the default.
        """
        self.intent_workflow = (
            intent_workflow
            if intent_workflow is not None
            else EditorialIntentWorkflow()
        )
        self.strategy_engine = (
            strategy_engine
            if strategy_engine is not None
            else DeterministicEditorialStrategyEngine()
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
    ) -> EditorialStrategyResult:
        """Analyze raw source fields and select an editorial strategy.

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
            The editorial intent result and deterministic strategy.
        """
        intent_result = self.intent_workflow.process(
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
        classification_result = intent_result.classification_result
        ingestion = classification_result.ingestion
        classification = classification_result.classification
        reader_intent = intent_result.reader_intent
        strategy = self.strategy_engine.decide(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification,
            reader_intent=reader_intent,
            user_instruction=user_instruction,
        )
        return EditorialStrategyResult(
            intent_result=intent_result,
            strategy=strategy,
        )
