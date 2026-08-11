"""Immutable provider-agnostic semantic adjudication request contract."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticAdjudicationRequest:
    """Store minimal text and structured deterministic adjudication evidence."""

    request_id: str

    title: str
    lead: str
    body_excerpt: str

    deterministic_topic: str
    topic_confidence: str

    deterministic_format: str
    format_confidence: str

    content_type: str

    contextual_support_labels: tuple[str, ...]
    contextual_suppressions: tuple[str, ...]

    semantic_relationship_summary: tuple[str, ...]

    primary_domain_candidates: tuple[str, ...]
    secondary_domain_candidates: tuple[str, ...]

    semantic_format_support: tuple[str, ...]
    semantic_format_suppression: tuple[str, ...]

    topic_reason_codes: tuple[str, ...]
    topic_warnings: tuple[str, ...]

    format_reason_codes: tuple[str, ...]
    format_warnings: tuple[str, ...]

    candidate_topics: tuple[str, ...]
    candidate_formats: tuple[str, ...]

    input_fingerprint: str
