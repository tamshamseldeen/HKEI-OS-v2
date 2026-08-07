"""Experimental orchestration of semantic-aware topic classification."""

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier

from .editorial_classification_workflow import EditorialClassificationWorkflow
from .editorial_semantic_topic_result import EditorialSemanticTopicResult


class EditorialSemanticTopicWorkflow:
    """Coordinate classification, evidence composition, and topic analysis."""

    def __init__(
        self,
        classification_workflow: EditorialClassificationWorkflow | None = None,
        evidence_engine: DeterministicContextualEvidenceEngine | None = None,
        semantic_engine: DeterministicCompositionalSemanticEngine | None = None,
        topic_classifier: DeterministicTopicClassifier | None = None,
    ) -> None:
        """Initialize supplied dependencies or deterministic defaults.

        Args:
            classification_workflow: Existing classification workflow or default.
            evidence_engine: Contextual evidence engine or default.
            semantic_engine: Compositional semantic engine or default.
            topic_classifier: Semantic-aware topic classifier or default.
        """
        self.classification_workflow = (
            classification_workflow
            if classification_workflow is not None
            else EditorialClassificationWorkflow()
        )
        self.evidence_engine = (
            evidence_engine
            if evidence_engine is not None
            else DeterministicContextualEvidenceEngine()
        )
        self.semantic_engine = (
            semantic_engine
            if semantic_engine is not None
            else DeterministicCompositionalSemanticEngine()
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
    ) -> EditorialSemanticTopicResult:
        """Run the additive semantic-aware topic analysis sequence.

        Args:
            title: Raw source title.
            body: Raw source body.
            source_name: Raw source name.
            source_url: Optional source URL.
            published_at: Optional publication timestamp.
            language: Optional source language.
            country: Optional source country.
            author: Optional source author.
            images: Source image references.
            attachments: Source attachment references.
            category: Optional source category.
            tags: Source tags.
            user_instruction: Optional editorial instruction.

        Returns:
            Upstream classification, both evidence layers, and topic result.
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
        contextual_evidence = self.evidence_engine.analyze(
            source=ingestion.source,
            user_instruction=user_instruction,
        )
        semantic_evidence = self.semantic_engine.compose(
            source=ingestion.source,
            contextual_evidence=contextual_evidence,
        )
        topic_classification = self.topic_classifier.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification_result.classification,
            user_instruction=user_instruction,
            contextual_evidence=contextual_evidence,
            semantic_evidence=semantic_evidence,
        )
        return EditorialSemanticTopicResult(
            classification_result=classification_result,
            contextual_evidence=contextual_evidence,
            semantic_evidence=semantic_evidence,
            topic_classification=topic_classification,
        )
