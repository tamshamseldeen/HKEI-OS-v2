"""Experimental orchestration of format-aware editorial strategy."""

from src.strategy.editorial_format_strategy_adapter import (
    EditorialFormatStrategyAdapter,
)

from .editorial_format_workflow import EditorialFormatWorkflow
from .editorial_strategy_workflow import EditorialStrategyWorkflow
from .experimental_editorial_strategy_result import (
    ExperimentalEditorialStrategyResult,
)


class ExperimentalEditorialStrategyWorkflow:
    """Combine existing strategy and format analysis without replacing either."""

    def __init__(
        self,
        strategy_workflow: EditorialStrategyWorkflow | None = None,
        format_workflow: EditorialFormatWorkflow | None = None,
        strategy_adapter: EditorialFormatStrategyAdapter | None = None,
    ) -> None:
        """Initialize the experimental workflow with supplied or default parts.

        Args:
            strategy_workflow: Existing editorial strategy workflow or default.
            format_workflow: Additive editorial format workflow or default.
            strategy_adapter: Format-aware strategy adapter or default.
        """
        self.strategy_workflow = (
            strategy_workflow
            if strategy_workflow is not None
            else EditorialStrategyWorkflow()
        )
        self.format_workflow = (
            format_workflow
            if format_workflow is not None
            else EditorialFormatWorkflow()
        )
        self.strategy_adapter = (
            strategy_adapter
            if strategy_adapter is not None
            else EditorialFormatStrategyAdapter()
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
    ) -> ExperimentalEditorialStrategyResult:
        """Run parallel analysis, validate compatibility, and adapt strategy.

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
            Both unchanged workflow results and a separate adapted strategy.

        Raises:
            ValueError: If parallel workflow results are incompatible.
        """
        fields = {
            "title": title,
            "body": body,
            "source_name": source_name,
            "source_url": source_url,
            "published_at": published_at,
            "language": language,
            "country": country,
            "author": author,
            "images": images,
            "attachments": attachments,
            "category": category,
            "tags": tags,
            "user_instruction": user_instruction,
        }
        strategy_result = self.strategy_workflow.process(**fields)
        format_result = self.format_workflow.process(**fields)

        classification_result = strategy_result.intent_result.classification_result
        ingestion = classification_result.ingestion
        format_classification_result = format_result.classification_result
        format_ingestion = format_classification_result.ingestion
        if (
            ingestion.source != format_ingestion.source
            or ingestion.assessment != format_ingestion.assessment
            or ingestion.facts != format_ingestion.facts
            or classification_result.classification
            != format_classification_result.classification
        ):
            raise ValueError("EXPERIMENTAL_WORKFLOW_RESULT_MISMATCH")

        adapted_strategy = self.strategy_adapter.adapt(
            strategy=strategy_result.strategy,
            format_classification=format_result.format_classification,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
        )
        return ExperimentalEditorialStrategyResult(
            strategy_result=strategy_result,
            format_result=format_result,
            adapted_strategy=adapted_strategy,
        )
