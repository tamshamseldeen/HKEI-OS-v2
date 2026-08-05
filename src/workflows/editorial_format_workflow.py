"""Additive orchestration of deterministic editorial format analysis."""

from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)

from .editorial_classification_workflow import EditorialClassificationWorkflow
from .editorial_format_result import EditorialFormatResult


class EditorialFormatWorkflow:
    """Coordinate existing content and additional format classification."""

    def __init__(
        self,
        classification_workflow: EditorialClassificationWorkflow | None = None,
        format_classifier: DeterministicEditorialFormatClassifier | None = None,
    ) -> None:
        """Initialize the additive editorial format workflow.

        Args:
            classification_workflow: Content classification workflow or default.
            format_classifier: Editorial format classifier or default.
        """
        self.classification_workflow = (
            classification_workflow
            if classification_workflow is not None
            else EditorialClassificationWorkflow()
        )
        self.format_classifier = (
            format_classifier
            if format_classifier is not None
            else DeterministicEditorialFormatClassifier()
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
    ) -> EditorialFormatResult:
        """Classify source content and its independent editorial format.

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
            Existing classification and additional editorial format analysis.
        """
        classification_result = self.classification_workflow.process(
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
        ingestion = classification_result.ingestion
        content_classification = classification_result.classification
        format_classification = self.format_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=content_classification,
            user_instruction=user_instruction,
        )
        return EditorialFormatResult(
            classification_result=classification_result,
            format_classification=format_classification,
        )
