"""Immutable provider-agnostic semantic adjudication response contract."""

from dataclasses import dataclass

from .adjudication_confidence import AdjudicationConfidence
from .semantic_adjudication_usage import SemanticAdjudicationUsage


@dataclass(frozen=True)
class SemanticAdjudicationResponse:
    """Store structured adjudication output and provider audit metadata."""

    adjudicated_topic: str
    adjudicated_format: str

    topic_confidence: AdjudicationConfidence
    format_confidence: AdjudicationConfidence

    topic_reason: str
    format_reason: str

    topic_evidence_refs: tuple[str, ...]
    format_evidence_refs: tuple[str, ...]

    ambiguity_remaining: bool

    warnings: tuple[str, ...]

    provider: str
    model: str

    request_schema_version: str
    response_schema_version: str

    input_fingerprint: str

    usage: SemanticAdjudicationUsage
