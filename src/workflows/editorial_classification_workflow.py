"""End-to-end orchestration of editorial content classification."""

from src.classification.deterministic_content_type_classifier import (
    DeterministicContentTypeClassifier,
)

from .editorial_classification_result import EditorialClassificationResult
from .editorial_ingestion_workflow import EditorialIngestionWorkflow


class EditorialClassificationWorkflow:
    """Coordinate editorial ingestion and deterministic classification."""

    def __init__(
        self,
        ingestion_workflow: EditorialIngestionWorkflow | None = None,
        classifier: DeterministicContentTypeClassifier | None = None,
    ) -> None:
        """Initialize the editorial classification workflow.

        Args:
            ingestion_workflow: Ingestion workflow, or None for the default.
            classifier: Content type classifier, or None for the default.
        """
        self.ingestion_workflow = (
            ingestion_workflow
            if ingestion_workflow is not None
            else EditorialIngestionWorkflow()
        )
        self.classifier = (
            classifier
            if classifier is not None
            else DeterministicContentTypeClassifier()
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
    ) -> EditorialClassificationResult:
        """Ingest raw source fields and classify the resulting content.

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
            The ingestion result and its content type classification.
        """
        ingestion = self.ingestion_workflow.process(
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
        )
        classification = self.classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            user_instruction=user_instruction,
        )
        return EditorialClassificationResult(
            ingestion=ingestion,
            classification=classification,
        )
