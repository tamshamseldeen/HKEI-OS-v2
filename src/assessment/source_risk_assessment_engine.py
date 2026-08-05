"""Deterministic source risk assessment engine."""

from src.intake.normalized_source import NormalizedSource

from .risk_level import RiskLevel
from .risk_rule_engine import RiskRuleEngine
from .source_risk_assessment import SourceRiskAssessment
from .source_status import SourceStatus
from .verification_status import VerificationStatus


_RISK_PRIORITY = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


class SourceRiskAssessmentEngine:
    """Assess normalized sources using deterministic MVP rules."""

    def __init__(self, risk_rule_engine: RiskRuleEngine | None = None) -> None:
        """Initialize the assessment engine.

        Args:
            risk_rule_engine: Rule engine to use, or None to create the default.
        """
        self.risk_rule_engine = (
            risk_rule_engine if risk_rule_engine is not None else RiskRuleEngine()
        )

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

        matched_rules = self.risk_rule_engine.evaluate(source)
        risk_level = max(
            (rule.risk_level for rule in matched_rules),
            key=_RISK_PRIORITY.__getitem__,
            default=RiskLevel.LOW,
        )

        risk_topics: list[str] = []
        for rule in matched_rules:
            for topic in rule.topics:
                if topic not in risk_topics:
                    risk_topics.append(topic)

        warnings: list[str] = []
        if source.source_url is None:
            warnings.append("SOURCE_URL_MISSING")
        if source_status is SourceStatus.UNIDENTIFIED:
            warnings.append("SOURCE_UNIDENTIFIED")
        if verification_status is VerificationStatus.UNVERIFIED:
            warnings.append("CONTENT_UNVERIFIED")
        for rule in matched_rules:
            for warning in rule.warnings:
                if warning not in warnings:
                    warnings.append(warning)

        valid_source_content = bool(source.title and source.body)
        generation_allowed = (
            valid_source_content and risk_level is not RiskLevel.CRITICAL
        )
        source_is_complete = (
            source_status is SourceStatus.IDENTIFIED and valid_source_content
        )
        reason_codes: list[str] = [
            "SOURCE_OK" if source_is_complete else "SOURCE_INCOMPLETE"
        ]
        for rule in matched_rules:
            if rule.code not in reason_codes:
                reason_codes.append(rule.code)

        return SourceRiskAssessment(
            source_status=source_status,
            verification_status=verification_status,
            risk_level=risk_level,
            risk_topics=tuple(risk_topics),
            warnings=tuple(warnings),
            requires_official_source=any(
                rule.requires_official_source for rule in matched_rules
            ),
            requires_human_review=(
                risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                or any(rule.requires_human_review for rule in matched_rules)
            ),
            generation_allowed=generation_allowed,
            reason_codes=tuple(reason_codes),
        )
