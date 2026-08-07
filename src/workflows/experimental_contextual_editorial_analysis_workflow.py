"""Experimental orchestration of context-aware editorial analysis."""

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier

from .editorial_classification_workflow import EditorialClassificationWorkflow
from .experimental_contextual_editorial_analysis_result import (
    ExperimentalContextualEditorialAnalysisResult,
)


class ExperimentalContextualEditorialAnalysisWorkflow:
    """Coordinate additive context-aware topic, format, and intent analysis."""

    def __init__(
        self,
        classification_workflow: EditorialClassificationWorkflow | None = None,
        evidence_engine: DeterministicContextualEvidenceEngine | None = None,
        topic_classifier: DeterministicTopicClassifier | None = None,
        format_classifier: DeterministicEditorialFormatClassifier | None = None,
        intent_classifier: DeterministicReaderIntentClassifierV2 | None = None,
    ) -> None:
        """Initialize injected dependencies or deterministic defaults.

        Args:
            classification_workflow: Existing classification workflow or default.
            evidence_engine: Contextual evidence engine or default.
            topic_classifier: Context-aware topic classifier or default.
            format_classifier: Context-aware format classifier or default.
            intent_classifier: Topic-and-format-aware intent classifier or default.
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
        self.topic_classifier = (
            topic_classifier
            if topic_classifier is not None
            else DeterministicTopicClassifier()
        )
        self.format_classifier = (
            format_classifier
            if format_classifier is not None
            else DeterministicEditorialFormatClassifier()
        )
        self.intent_classifier = (
            intent_classifier
            if intent_classifier is not None
            else DeterministicReaderIntentClassifierV2()
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
    ) -> ExperimentalContextualEditorialAnalysisResult:
        """Run contextual topic and format analysis before reader intent.

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
            Complete experimental contextual editorial analysis result.
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
        topic_classification = self.topic_classifier.classify(
            source=ingestion.source,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
            content_classification=classification_result.classification,
            user_instruction=user_instruction,
            contextual_evidence=contextual_evidence,
        )
        format_classification = self.format_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification_result.classification,
            user_instruction=user_instruction,
            contextual_evidence=contextual_evidence,
        )
        reader_intent_classification = self.intent_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            topic_classification=topic_classification,
            format_classification=format_classification,
            user_instruction=user_instruction,
        )
        return ExperimentalContextualEditorialAnalysisResult(
            classification_result=classification_result,
            contextual_evidence=contextual_evidence,
            topic_classification=topic_classification,
            format_classification=format_classification,
            reader_intent_classification=reader_intent_classification,
        )
