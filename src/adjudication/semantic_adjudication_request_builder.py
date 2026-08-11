"""Build minimal provider-agnostic semantic adjudication requests."""

from hashlib import sha256
import json
import re
from typing import Iterable

from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.intake.normalized_source import NormalizedSource
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification

from .adjudication_scope import AdjudicationScope
from .semantic_adjudication_decision import SemanticAdjudicationDecision
from .semantic_adjudication_request import SemanticAdjudicationRequest


SEMANTIC_ADJUDICATION_REQUEST_SCHEMA_VERSION = "1.0"
_LEAD_LIMIT = 500
_BODY_EXCERPT_LIMIT = 1800
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?؟])\s+|\n+")


class SemanticAdjudicationNotRequiredError(ValueError):
    """Raised when a request is attempted for a sufficient gate decision."""


def _deduplicate(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _sentences(body: str) -> tuple[str, ...]:
    return tuple(
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY.split(body.strip())
        if sentence.strip()
    )


def _label_value(label: str, prefix: str, valid: set[str]) -> str | None:
    value = label[len(prefix):] if label.startswith(prefix) else label
    return value if value in valid else None


class SemanticAdjudicationRequestBuilder:
    """Convert deterministic editorial state into a bounded request payload."""

    def build(
        self,
        *,
        request_id: str,
        source: NormalizedSource,
        content_classification: ContentTypeClassification,
        topic_classification: TopicClassification,
        format_classification: EditorialFormatClassification,
        contextual_evidence: ContextualEvidence,
        semantic_evidence: CompositionalSemanticEvidence,
        decision: SemanticAdjudicationDecision,
    ) -> SemanticAdjudicationRequest:
        """Build one immutable request without mutating deterministic inputs."""
        if decision.scope is AdjudicationScope.NOT_REQUIRED:
            raise SemanticAdjudicationNotRequiredError(
                "semantic adjudication is not required"
            )

        title = (source.title or "").strip()
        lead = self._lead(source.body)
        body_excerpt = self._body_excerpt(
            source.body,
            contextual_evidence=contextual_evidence,
            semantic_evidence=semantic_evidence,
            decision=decision,
        )
        contextual_supports = _deduplicate(
            support
            for item in contextual_evidence.all_items
            for support in item.supports
        )
        contextual_suppressions = _deduplicate(
            suppression
            for item in contextual_evidence.all_items
            for suppression in item.suppresses
        )
        relationship_summary = tuple(
            "|".join(
                (
                    relationship.relationship_type.value,
                    relationship.subject_component.value,
                    relationship.object_component.value,
                    relationship.strength.value,
                    relationship.reason_code,
                )
            )
            for relationship in semantic_evidence.relationships
        )
        primary_candidates = _deduplicate(
            semantic_evidence.primary_domain_candidates
        )
        secondary_candidates = _deduplicate(
            semantic_evidence.secondary_domain_candidates
        )
        semantic_format_support = _deduplicate(semantic_evidence.format_support)
        semantic_format_suppression = _deduplicate(
            semantic_evidence.format_suppression
        )
        candidate_topics = self._candidate_topics(
            deterministic=topic_classification.topic.value,
            required=decision.topic_required,
            primary=primary_candidates,
            secondary=secondary_candidates,
            contextual=contextual_supports,
        )
        candidate_formats = self._candidate_formats(
            deterministic=format_classification.editorial_format.value,
            required=decision.format_required,
            semantic_support=semantic_format_support,
            semantic_suppression=semantic_format_suppression,
            contextual=contextual_supports,
            relationships=semantic_evidence.relationships,
        )

        payload = {
            "schema_identifier": SEMANTIC_ADJUDICATION_REQUEST_SCHEMA_VERSION,
            "request_id": request_id,
            "title": title,
            "lead": lead,
            "body_excerpt": body_excerpt,
            "deterministic_topic": topic_classification.topic.value,
            "topic_confidence": topic_classification.confidence.value,
            "deterministic_format": (
                format_classification.editorial_format.value
            ),
            "format_confidence": format_classification.confidence.value,
            "content_type": content_classification.content_type.value,
            "contextual_support_labels": contextual_supports,
            "contextual_suppressions": contextual_suppressions,
            "semantic_relationship_summary": relationship_summary,
            "primary_domain_candidates": primary_candidates,
            "secondary_domain_candidates": secondary_candidates,
            "semantic_format_support": semantic_format_support,
            "semantic_format_suppression": semantic_format_suppression,
            "topic_reason_codes": topic_classification.reason_codes,
            "topic_warnings": topic_classification.warnings,
            "format_reason_codes": format_classification.reason_codes,
            "format_warnings": format_classification.warnings,
            "candidate_topics": candidate_topics,
            "candidate_formats": candidate_formats,
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = sha256(serialized.encode("utf-8")).hexdigest()
        payload.pop("schema_identifier")
        return SemanticAdjudicationRequest(
            **payload,
            input_fingerprint=fingerprint,
        )

    @staticmethod
    def _lead(body: str) -> str:
        paragraphs = tuple(
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", body)
            if paragraph.strip()
        )
        if paragraphs:
            return paragraphs[0][:_LEAD_LIMIT]
        sentences = _sentences(body)
        return (sentences[0] if sentences else "")[:_LEAD_LIMIT]

    def _body_excerpt(
        self,
        body: str,
        *,
        contextual_evidence: ContextualEvidence,
        semantic_evidence: CompositionalSemanticEvidence,
        decision: SemanticAdjudicationDecision,
    ) -> str:
        sentences = _sentences(body)
        if not sentences:
            return ""

        relationship_indexes = [
            relationship.sentence_index
            for relationship in semantic_evidence.relationships
            if relationship.strength is EvidenceStrength.STRONG
            and relationship.source_section in (SourceSection.LEAD, SourceSection.BODY)
        ]
        ambiguity_indexes: list[int] = []
        trigger_indexes: list[int] = []
        triggers = set(decision.trigger_signals)
        for item in contextual_evidence.all_items:
            if item.source_section not in (SourceSection.LEAD, SourceSection.BODY):
                continue
            labels = (*item.supports, *item.suppresses)
            if any(
                label.startswith(("ADJUDICATION_", "TOPIC_", "FORMAT_"))
                or "AMBIGU" in label
                for label in labels
            ):
                ambiguity_indexes.append(item.sentence_index)
            if (
                item.reason_code in triggers
                or any(label in triggers for label in labels)
            ):
                trigger_indexes.append(item.sentence_index)

        selected: list[int] = []
        for index in (*relationship_indexes, *ambiguity_indexes, *trigger_indexes):
            if 0 <= index < len(sentences) and index not in selected:
                selected.append(index)
        if selected:
            bounded: set[int] = set()
            for index in selected:
                proposed = sorted((*bounded, index))
                proposed_length = sum(
                    len(sentences[item]) for item in proposed
                ) + max(0, len(proposed) - 1)
                if proposed_length <= _BODY_EXCERPT_LIMIT or not bounded:
                    bounded.add(index)
            for index in selected:
                for candidate_index in (index - 1, index + 1):
                    if not 0 <= candidate_index < len(sentences):
                        continue
                    if candidate_index in bounded:
                        continue
                    proposed = sorted((*bounded, candidate_index))
                    proposed_length = sum(
                        len(sentences[item]) for item in proposed
                    ) + max(0, len(proposed) - 1)
                    if proposed_length <= _BODY_EXCERPT_LIMIT or not bounded:
                        bounded.add(candidate_index)
            ordered = sorted(bounded)
        else:
            ordered = list(range(len(sentences)))

        excerpt = ""
        included_sentences: set[str] = set()
        for index in ordered:
            addition = sentences[index]
            if addition in included_sentences:
                continue
            candidate = f"{excerpt} {addition}".strip()
            if len(candidate) > _BODY_EXCERPT_LIMIT:
                if not excerpt:
                    excerpt = addition[:_BODY_EXCERPT_LIMIT]
                break
            excerpt = candidate
            included_sentences.add(addition)
        return excerpt

    @staticmethod
    def _candidate_topics(
        *,
        deterministic: str,
        required: bool,
        primary: tuple[str, ...],
        secondary: tuple[str, ...],
        contextual: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not required:
            return (deterministic,)
        valid = {topic.value for topic in Topic}
        candidates: list[str] = [deterministic]
        for label in (*primary, *secondary):
            value = _label_value(label, "PRIMARY_DOMAIN_", valid)
            if value is None:
                value = _label_value(label, "SECONDARY_DOMAIN_", valid)
            if value is not None:
                candidates.append(value)
        for label in contextual:
            value = _label_value(label, "TOPIC_", valid)
            if value is not None and label.startswith("TOPIC_"):
                candidates.append(value)
        candidates.append(Topic.GENERAL.value)
        return _deduplicate(candidates)

    @staticmethod
    def _candidate_formats(
        *,
        deterministic: str,
        required: bool,
        semantic_support: tuple[str, ...],
        semantic_suppression: tuple[str, ...],
        contextual: tuple[str, ...],
        relationships: tuple[object, ...],
    ) -> tuple[str, ...]:
        if not required:
            return (deterministic,)
        valid = {editorial_format.value for editorial_format in EditorialFormat}
        suppressed = {
            value
            for label in semantic_suppression
            if (value := _label_value(label, "FORMAT_", valid)) is not None
        }
        for relationship in relationships:
            if relationship.strength is EvidenceStrength.STRONG:
                suppressed.update(
                    value
                    for label in relationship.suppresses
                    if (value := _label_value(label, "FORMAT_", valid)) is not None
                )
        candidates: list[str] = [deterministic]
        for label in (*semantic_support, *contextual):
            value = _label_value(label, "FORMAT_", valid)
            if (
                value is not None
                and (label.startswith("FORMAT_") or label in valid)
                and (value == deterministic or value not in suppressed)
            ):
                candidates.append(value)
        return _deduplicate(candidates)
