"""Immutable source risk assessment model."""

from dataclasses import dataclass

from .risk_level import RiskLevel
from .source_status import SourceStatus
from .verification_status import VerificationStatus


@dataclass(frozen=True)
class SourceRiskAssessment:
    """Represent the source and risk assessment result.

    Attributes:
        source_status: Attribution availability of the source.
        verification_status: Verification state of the source material.
        risk_level: Editorial risk level of the source material.
        risk_topics: High-risk topics associated with the source material.
        warnings: Machine-readable assessment warnings.
        requires_official_source: Whether an official source is required.
        requires_human_review: Whether human review is required.
        generation_allowed: Whether generation may continue.
        reason_codes: Stable codes explaining assessment decisions.
    """

    source_status: SourceStatus
    verification_status: VerificationStatus
    risk_level: RiskLevel
    risk_topics: tuple[str, ...]
    warnings: tuple[str, ...]
    requires_official_source: bool
    requires_human_review: bool
    generation_allowed: bool
    reason_codes: tuple[str, ...]
