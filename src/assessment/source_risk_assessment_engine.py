"""Deterministic source risk assessment engine."""

from src.intake.normalized_source import NormalizedSource

from .risk_level import RiskLevel
from .source_risk_assessment import SourceRiskAssessment
from .source_status import SourceStatus
from .verification_status import VerificationStatus


class SourceRiskAssessmentEngine:
    """Assess normalized sources using deterministic MVP rules."""

    def assess(self, source: NormalizedSource) -> SourceRiskAssessment:
        """Assess source attribution, verification, and generation eligibility.

        Args:
            source: Normalized source to assess.

        Returns:
            The deterministic source risk assessment.
        """
        if source.source_name and source.source_url:
            source_status = SourceStatus.IDENTIFIED
        elif source.source_name and source.source_url is None:
            source_status = SourceStatus.PARTIALLY_IDENTIFIED
        else:
            source_status = SourceStatus.UNIDENTIFIED

        if source.source_url is None:
            verification_status = VerificationStatus.UNVERIFIED
        else:
            verification_status = VerificationStatus.SOURCE_PROVIDED

        warnings: list[str] = []
        if source.source_url is None:
            warnings.append("SOURCE_URL_MISSING")
        if source_status is SourceStatus.UNIDENTIFIED:
            warnings.append("SOURCE_UNIDENTIFIED")
        if verification_status is VerificationStatus.UNVERIFIED:
            warnings.append("CONTENT_UNVERIFIED")

        generation_allowed = bool(source.title and source.body)
        source_is_complete = (
            source_status is SourceStatus.IDENTIFIED and generation_allowed
        )
        reason_codes = ("SOURCE_OK" if source_is_complete else "SOURCE_INCOMPLETE",)

        return SourceRiskAssessment(
            source_status=source_status,
            verification_status=verification_status,
            risk_level=RiskLevel.LOW,
            risk_topics=(),
            warnings=tuple(warnings),
            requires_official_source=False,
            requires_human_review=False,
            generation_allowed=generation_allowed,
            reason_codes=reason_codes,
        )
