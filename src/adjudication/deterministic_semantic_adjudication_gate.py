"""Deterministic gate for deciding whether editorial adjudication is needed."""

from src.evidence.contextual_evidence import ContextualEvidence
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.semantics.semantic_component import SemanticComponent
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence

from .adjudication_scope import AdjudicationScope
from .semantic_adjudication_decision import SemanticAdjudicationDecision


_TOPIC_PREFIX = "TOPIC_"
_PRIMARY_DOMAIN_PREFIX = "PRIMARY_DOMAIN_"
_FORMAT_PREFIX = "FORMAT_"


class DeterministicSemanticAdjudicationGate:
    """Evaluate existing structured evidence without selecting new labels."""

    def evaluate(
        self,
        *,
        topic_classification: TopicClassification,
        format_classification: EditorialFormatClassification,
        contextual_evidence: ContextualEvidence,
        semantic_evidence: CompositionalSemanticEvidence,
    ) -> SemanticAdjudicationDecision:
        """Return the deterministic scope required by existing evidence."""
        contextual_items = contextual_evidence.all_items
        contextual_supports = tuple(
            support for item in contextual_items for support in item.supports
        )
        semantic_supports = semantic_evidence.all_supports
        semantic_suppressions = semantic_evidence.all_suppressions

        topic_low_confidence = (
            topic_classification.confidence is TopicConfidence.LOW
        )
        topic_general_fallback = (
            topic_classification.topic is Topic.GENERAL
            and self._indicates_general_fallback(topic_classification)
        )
        no_primary_domain = not semantic_evidence.primary_domain_candidates
        context_without_relationship = bool(contextual_items) and not (
            semantic_evidence.relationships
        )
        method_subject_ambiguity = self._has_method_subject_ambiguity(
            contextual_supports=contextual_supports,
            semantic_evidence=semantic_evidence,
        )
        semantic_domain_conflict = self._has_semantic_domain_conflict(
            semantic_evidence
        )
        multiple_topic_signals = self._has_multiple_competing_topic_signals(
            contextual_supports=contextual_supports,
            semantic_supports=semantic_supports,
            primary_domain_candidates=semantic_evidence.primary_domain_candidates,
        )

        format_low_confidence = (
            format_classification.confidence is EditorialFormatConfidence.LOW
        )
        contextual_format_targets = self._format_targets(contextual_supports)
        semantic_format_targets = self._format_targets(
            semantic_evidence.format_support
        )
        final_format = format_classification.editorial_format.value
        analytical_news_fallback = (
            "ANALYSIS" in contextual_format_targets
            and format_classification.editorial_format
            is EditorialFormat.STANDARD_NEWS
            and format_classification.confidence
            is not EditorialFormatConfidence.HIGH
        )
        explainer_unresolved = (
            "EXPLAINER"
            in contextual_format_targets | semantic_format_targets
            and format_classification.editorial_format
            is not EditorialFormat.EXPLAINER
        )
        contextual_format_not_promoted = any(
            target != final_format for target in contextual_format_targets
        )
        format_conflict = self._has_format_conflict(semantic_evidence)

        trigger_signals: list[str] = []
        for present, signal in (
            (topic_low_confidence, "TOPIC_LOW_CONFIDENCE"),
            (topic_general_fallback, "TOPIC_GENERAL_FALLBACK"),
            (no_primary_domain, "NO_PRIMARY_SEMANTIC_DOMAIN"),
            (
                context_without_relationship,
                "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP",
            ),
            (method_subject_ambiguity, "METHOD_SUBJECT_AMBIGUITY"),
            (semantic_domain_conflict, "SEMANTIC_DOMAIN_CONFLICT"),
            (multiple_topic_signals, "MULTIPLE_COMPETING_TOPIC_SIGNALS"),
            (format_low_confidence, "FORMAT_LOW_CONFIDENCE"),
            (
                analytical_news_fallback,
                "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK",
            ),
            (explainer_unresolved, "EXPLAINER_STRUCTURE_UNRESOLVED"),
            (
                contextual_format_not_promoted,
                "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED",
            ),
            (format_conflict, "FORMAT_CONFLICT"),
        ):
            if present and signal not in trigger_signals:
                trigger_signals.append(signal)

        topic_required = (
            (topic_general_fallback and topic_low_confidence)
            or (
                topic_low_confidence
                and no_primary_domain
                and (
                    context_without_relationship
                    or multiple_topic_signals
                    or method_subject_ambiguity
                )
            )
            or semantic_domain_conflict
            or (
                method_subject_ambiguity
                and topic_classification.confidence is not TopicConfidence.HIGH
            )
        )
        format_required = (
            format_conflict
            or (
                contextual_format_not_promoted
                and format_classification.confidence
                is not EditorialFormatConfidence.HIGH
            )
            or analytical_news_fallback
            or (
                explainer_unresolved
                and format_classification.confidence
                is not EditorialFormatConfidence.HIGH
            )
        )
        scope, reason_codes = self._resolve_scope(
            topic_required=topic_required,
            format_required=format_required,
        )
        return SemanticAdjudicationDecision(
            scope=scope,
            trigger_signals=tuple(trigger_signals),
            topic_required=topic_required,
            format_required=format_required,
            reason_codes=reason_codes,
            warnings=(),
        )

    @staticmethod
    def _indicates_general_fallback(
        classification: TopicClassification,
    ) -> bool:
        indicators = (
            *classification.reason_codes,
            *classification.supporting_signals,
            *classification.warnings,
        )
        return any(
            token in indicator
            for indicator in indicators
            for token in ("FALLBACK", "INSUFFICIENT", "DEFAULT_GENERAL")
        )

    @staticmethod
    def _primary_domains(values: tuple[str, ...]) -> set[str]:
        return {
            value.removeprefix(_PRIMARY_DOMAIN_PREFIX)
            for value in values
            if value.startswith(_PRIMARY_DOMAIN_PREFIX)
        }

    @staticmethod
    def _contextual_topics(values: tuple[str, ...]) -> set[str]:
        return {
            value.removeprefix(_TOPIC_PREFIX)
            for value in values
            if value.startswith(_TOPIC_PREFIX)
        }

    def _has_method_subject_ambiguity(
        self,
        *,
        contextual_supports: tuple[str, ...],
        semantic_evidence: CompositionalSemanticEvidence,
    ) -> bool:
        has_method_relationship = any(
            relationship.subject_component
            in (SemanticComponent.METHOD, SemanticComponent.TOOL)
            or relationship.object_component
            in (SemanticComponent.METHOD, SemanticComponent.TOOL)
            for relationship in semantic_evidence.relationships
        )
        contextual_topics = self._contextual_topics(contextual_supports)
        semantic_domains = self._primary_domains(semantic_evidence.all_supports)
        return (
            has_method_relationship
            and bool(contextual_topics)
            and bool(semantic_domains)
            and len(contextual_topics | semantic_domains) > 1
        )

    def _has_semantic_domain_conflict(
        self,
        evidence: CompositionalSemanticEvidence,
    ) -> bool:
        candidates = set(evidence.primary_domain_candidates)
        supported = self._primary_domains(evidence.all_supports)
        suppressed = self._primary_domains(evidence.all_suppressions)
        return (
            len(candidates) > 1
            or bool(supported & suppressed)
            or (not candidates and len(supported) > 1)
        )

    def _has_multiple_competing_topic_signals(
        self,
        *,
        contextual_supports: tuple[str, ...],
        semantic_supports: tuple[str, ...],
        primary_domain_candidates: tuple[str, ...],
    ) -> bool:
        topics = self._contextual_topics(contextual_supports)
        domains = self._primary_domains(semantic_supports)
        distinct_candidates = set(primary_domain_candidates)
        return len(topics | domains) > 1 and len(distinct_candidates) != 1

    @staticmethod
    def _format_targets(values: tuple[str, ...]) -> set[str]:
        return {
            value.removeprefix(_FORMAT_PREFIX)
            for value in values
            if value.startswith(_FORMAT_PREFIX)
        }

    def _has_format_conflict(
        self,
        evidence: CompositionalSemanticEvidence,
    ) -> bool:
        supported = self._format_targets(evidence.format_support)
        suppressed = self._format_targets(evidence.format_suppression)
        return len(supported) > 1 or bool(supported & suppressed)

    @staticmethod
    def _resolve_scope(
        *,
        topic_required: bool,
        format_required: bool,
    ) -> tuple[AdjudicationScope, tuple[str, ...]]:
        if topic_required and format_required:
            return (
                AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
                ("TOPIC_AND_FORMAT_ADJUDICATION_REQUIRED",),
            )
        if topic_required:
            return (
                AdjudicationScope.TOPIC_REQUIRED,
                ("TOPIC_ADJUDICATION_REQUIRED",),
            )
        if format_required:
            return (
                AdjudicationScope.FORMAT_REQUIRED,
                ("FORMAT_ADJUDICATION_REQUIRED",),
            )
        return (
            AdjudicationScope.NOT_REQUIRED,
            ("DETERMINISTIC_RESULT_SUFFICIENT",),
        )
