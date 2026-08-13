"""Pure sanitized observation builder for the Topic authority pilot."""

from .editorial_resolution_status import EditorialResolutionStatus
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_decision import TopicAuthorityDecision
from .topic_authority_observation import TopicAuthorityObservation
from .topic_authority_provider_failure_category import TopicAuthorityProviderFailureCategory


class TopicAuthorityObservationBuilder:
    """Build immutable telemetry without source or provider payloads."""

    def build(
        self,
        decision: TopicAuthorityDecision,
        authority_mode: ResolverAuthorityMode,
        topic_adjudication_requested: bool,
        provider_called: bool,
        provider_valid: bool,
        candidate_compliant: bool,
        fingerprint_valid: bool,
        provider_failure_category: TopicAuthorityProviderFailureCategory | None = None,
    ) -> TopicAuthorityObservation:
        if not isinstance(decision, TopicAuthorityDecision):
            raise ValueError("decision must be a TopicAuthorityDecision")
        if not isinstance(authority_mode, ResolverAuthorityMode):
            raise ValueError("authority_mode must be a ResolverAuthorityMode")
        flags = {
            "topic_adjudication_requested": topic_adjudication_requested,
            "provider_called": provider_called,
            "provider_valid": provider_valid,
            "candidate_compliant": candidate_compliant,
            "fingerprint_valid": fingerprint_valid,
        }
        for name, value in flags.items():
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")
        if provider_failure_category is not None and not isinstance(
            provider_failure_category, TopicAuthorityProviderFailureCategory
        ):
            raise ValueError(
                "provider_failure_category must be a TopicAuthorityProviderFailureCategory or None"
            )
        return TopicAuthorityObservation(
            authority_mode=authority_mode,
            authority_applied=decision.authority_applied,
            authority_source=decision.authority_source,
            resolution_status=decision.resolution_status,
            provider_used=(
                decision.resolution_status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
                and provider_valid
            ),
            provider_called=provider_called,
            provider_valid=provider_valid,
            topic_adjudication_requested=topic_adjudication_requested,
            provider_failure_category=provider_failure_category,
            provider_confidence=decision.provider_confidence,
            ambiguity_remaining=decision.ambiguity_remaining,
            review_required=decision.review_required,
            block_reasons=decision.block_reasons,
            warnings=decision.warnings,
            candidate_compliant=candidate_compliant,
            fingerprint_valid=fingerprint_valid,
            decision_fingerprint=decision.input_fingerprint,
        )
