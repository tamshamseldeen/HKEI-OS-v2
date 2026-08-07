"""Experimental orchestration of semantic-aware editorial analysis."""

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier

from .editorial_classification_workflow import EditorialClassificationWorkflow
from .experimental_semantic_editorial_analysis_result import (
    ExperimentalSemanticEditorialAnalysisResult,
)


class ExperimentalSemanticEditorialAnalysisWorkflow:
    """Coordinate semantic-aware topic, format, and intent analysis."""

    def __init__(
        self,
        classification_workflow: EditorialClassificationWorkflow | None = None,
        evidence_engine: DeterministicContextualEvidenceEngine | None = None,
        semantic_engine: DeterministicCompositionalSemanticEngine | None = None,
        topic_classifier: DeterministicTopicClassifier | None = None,
        format_classifier: DeterministicEditorialFormatClassifier | None = None,
        intent_classifier: DeterministicReaderIntentClassifierV2 | None = None,
    ) -> None:
        """Initialize injected dependencies or deterministic defaults."""
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
    ) -> ExperimentalSemanticEditorialAnalysisResult:
        """Run semantic evidence before topic, format, and intent analysis."""
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
        format_classification = self.format_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification_result.classification,
            user_instruction=user_instruction,
            contextual_evidence=contextual_evidence,
            semantic_evidence=semantic_evidence,
        )
        reader_intent_classification = self.intent_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            topic_classification=topic_classification,
            format_classification=format_classification,
            user_instruction=user_instruction,
        )
        return ExperimentalSemanticEditorialAnalysisResult(
            classification_result=classification_result,
            contextual_evidence=contextual_evidence,
            semantic_evidence=semantic_evidence,
            topic_classification=topic_classification,
            format_classification=format_classification,
            reader_intent_classification=reader_intent_classification,
        )
