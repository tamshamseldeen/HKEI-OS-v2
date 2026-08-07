"""Additive orchestration of deterministic editorial topic analysis."""

from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier

from .editorial_classification_workflow import EditorialClassificationWorkflow
from .editorial_topic_result import EditorialTopicResult


class EditorialTopicWorkflow:
    """Coordinate existing content and additional topic classification."""

    def __init__(
        self,
        classification_workflow: EditorialClassificationWorkflow | None = None,
        topic_classifier: DeterministicTopicClassifier | None = None,
    ) -> None:
        """Initialize the additive topic workflow.

        Args:
            classification_workflow: Existing content workflow or default.
            topic_classifier: Deterministic topic classifier or default.
        """
        self.classification_workflow = (
            classification_workflow
            if classification_workflow is not None
            else EditorialClassificationWorkflow()
        )
        self.topic_classifier = (
            topic_classifier
            if topic_classifier is not None
            else DeterministicTopicClassifier()
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
    ) -> EditorialTopicResult:
        """Classify source content and its independent primary topic.

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
            Existing classification and additional topic analysis.
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
        topic_classification = self.topic_classifier.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification_result.classification,
            user_instruction=user_instruction,
        )
        return EditorialTopicResult(
            classification_result=classification_result,
            topic_classification=topic_classification,
        )
