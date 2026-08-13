"""Pure validator for applied limited Topic authority decisions."""

from src.adjudication.adjudication_confidence import AdjudicationConfidence

from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .limited_topic_authority_config import LimitedTopicAuthorityConfig
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_contract_violation import TopicAuthorityContractViolation
from .topic_authority_decision import TopicAuthorityDecision


class TopicAuthorityContractValidator:
    """Report unsafe applied authority without changing the decision."""

    _CONFIDENCE_RANK = {
        AdjudicationConfidence.LOW: 0,
        AdjudicationConfidence.MEDIUM: 1,
        AdjudicationConfidence.HIGH: 2,
    }

    def validate(
        self,
        decision: TopicAuthorityDecision,
        config: LimitedTopicAuthorityConfig,
        candidate_compliant: bool,
        fingerprint_valid: bool,
        response_valid: bool,
        provider_available: bool,
        format_authority_applied: bool = False,
        reader_intent_authority_applied: bool = False,
    ) -> tuple[TopicAuthorityContractViolation, ...]:
        if not isinstance(decision, TopicAuthorityDecision):
            raise ValueError("decision must be a TopicAuthorityDecision")
        if not isinstance(config, LimitedTopicAuthorityConfig):
            raise ValueError("config must be a LimitedTopicAuthorityConfig")
        flags = {
            "candidate_compliant": candidate_compliant,
            "fingerprint_valid": fingerprint_valid,
            "response_valid": response_valid,
            "provider_available": provider_available,
            "format_authority_applied": format_authority_applied,
            "reader_intent_authority_applied": reader_intent_authority_applied,
        }
        for name, value in flags.items():
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")

        violations: list[TopicAuthorityContractViolation] = []
        if decision.authority_applied:
            if config.authority_mode is ResolverAuthorityMode.SHADOW:
                violations.append(TopicAuthorityContractViolation.AUTHORITY_APPLIED_IN_SHADOW_MODE)
            if (
                decision.resolution_status is not EditorialResolutionStatus.ADJUDICATED_ACCEPTED
                or decision.authority_source is not EditorialResolutionSource.ADJUDICATION
            ):
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITHOUT_ADJUDICATION
                )
            if decision.review_required:
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_REVIEW_REQUIRED
                )
            if decision.ambiguity_remaining:
                violations.append(TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_AMBIGUITY)
            if (
                decision.provider_confidence is None
                or self._CONFIDENCE_RANK[decision.provider_confidence]
                < self._CONFIDENCE_RANK[config.minimum_provider_confidence]
            ):
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_LOW_CONFIDENCE
                )
            if not response_valid:
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_RESPONSE
                )
            if not candidate_compliant:
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_CANDIDATE
                )
            if not fingerprint_valid:
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_FINGERPRINT
                )
            if not provider_available:
                violations.append(
                    TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_PROVIDER_UNAVAILABLE
                )
        if format_authority_applied:
            violations.append(TopicAuthorityContractViolation.FORMAT_AUTHORITY_VIOLATION)
        if reader_intent_authority_applied:
            violations.append(TopicAuthorityContractViolation.READER_INTENT_AUTHORITY_VIOLATION)
        present = set(violations)
        return tuple(item for item in TopicAuthorityContractViolation if item in present)
