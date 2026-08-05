"""End-to-end orchestration of editorial reader intent analysis."""

from src.intent.deterministic_reader_intent_classifier import (
    DeterministicReaderIntentClassifier,
)

from .editorial_classification_workflow import EditorialClassificationWorkflow
from .editorial_intent_result import EditorialIntentResult


class EditorialIntentWorkflow:
    """Coordinate editorial classification and reader intent analysis."""

    def __init__(
        self,
        classification_workflow: EditorialClassificationWorkflow | None = None,
        reader_intent_classifier: DeterministicReaderIntentClassifier
        | None = None,
    ) -> None:
        """Initialize the editorial intent workflow.

        Args:
            classification_workflow: Classification workflow, or the default.
            reader_intent_classifier: Intent classifier, or the default.
        """
        self.classification_workflow = (
            classification_workflow
            if classification_workflow is not None
            else EditorialClassificationWorkflow()
        )
        self.reader_intent_classifier = (
            reader_intent_classifier
            if reader_intent_classifier is not None
            else DeterministicReaderIntentClassifier()
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
    ) -> EditorialIntentResult:
        """Classify raw source content and its primary reader intent.

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
            The editorial classification and reader intent results.
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
        classification = classification_result.classification
        reader_intent = self.reader_intent_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification,
            user_instruction=user_instruction,
        )
        return EditorialIntentResult(
            classification_result=classification_result,
            reader_intent=reader_intent,
        )
