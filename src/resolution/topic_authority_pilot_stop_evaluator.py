"""Pure stop-condition evaluator for the limited Topic authority pilot."""

from .limited_topic_authority_config import LimitedTopicAuthorityConfig
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_metrics import TopicAuthorityMetrics, TopicAuthoritySafetyMetrics
from .topic_authority_pilot_stop_decision import (
    TopicAuthorityPilotStopDecision,
    TopicAuthorityPilotStopReason,
)


class TopicAuthorityPilotStopEvaluator:
    """Evaluate preregistered safety thresholds without mutating config."""

    OVERRIDE_PRECISION_THRESHOLD = 0.90
    PROVIDER_FAILURE_RATE_THRESHOLD = 0.05
    PROVIDER_FAILURE_RATE_MINIMUM_CALLS = 20
    CONSECUTIVE_PROVIDER_FAILURE_LIMIT = 3

    def evaluate(
        self,
        operational: TopicAuthorityMetrics,
        safety: TopicAuthoritySafetyMetrics,
        config: LimitedTopicAuthorityConfig,
    ) -> TopicAuthorityPilotStopDecision:
        if not isinstance(operational, TopicAuthorityMetrics):
            raise ValueError("operational must be TopicAuthorityMetrics")
        if not isinstance(safety, TopicAuthoritySafetyMetrics):
            raise ValueError("safety must be TopicAuthoritySafetyMetrics")
        if not isinstance(config, LimitedTopicAuthorityConfig):
            raise ValueError("config must be LimitedTopicAuthorityConfig")
        reasons: list[TopicAuthorityPilotStopReason] = []
        if safety.authority_contract_violation_count > 0:
            reasons.append(TopicAuthorityPilotStopReason.AUTHORITY_CONTRACT_VIOLATION)
        if safety.audited_incorrect_override_count > config.regression_budget:
            reasons.append(TopicAuthorityPilotStopReason.REGRESSION_BUDGET_EXCEEDED)
        if safety.accepted_candidate_violation_count > 0:
            reasons.append(TopicAuthorityPilotStopReason.ACCEPTED_CANDIDATE_VIOLATION)
        if safety.accepted_fingerprint_violation_count > 0:
            reasons.append(TopicAuthorityPilotStopReason.ACCEPTED_FINGERPRINT_VIOLATION)
        if safety.format_authority_violation_count > 0:
            reasons.append(TopicAuthorityPilotStopReason.FORMAT_AUTHORITY_VIOLATION)
        if safety.reader_intent_authority_violation_count > 0:
            reasons.append(TopicAuthorityPilotStopReason.READER_INTENT_AUTHORITY_VIOLATION)
        if (
            safety.audited_override_count >= config.minimum_audited_override_sample
            and safety.override_precision is not None
            and safety.override_precision < self.OVERRIDE_PRECISION_THRESHOLD
        ):
            reasons.append(TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD)
        if (
            operational.max_consecutive_provider_validation_failures
            >= self.CONSECUTIVE_PROVIDER_FAILURE_LIMIT
        ):
            reasons.append(TopicAuthorityPilotStopReason.CONSECUTIVE_PROVIDER_VALIDATION_FAILURES)
        if (
            operational.provider_calls >= self.PROVIDER_FAILURE_RATE_MINIMUM_CALLS
            and operational.provider_validation_failures / operational.provider_calls
            > self.PROVIDER_FAILURE_RATE_THRESHOLD
        ):
            reasons.append(TopicAuthorityPilotStopReason.PROVIDER_VALIDATION_FAILURE_RATE_EXCEEDED)
        stop_reasons = tuple(reasons)
        return TopicAuthorityPilotStopDecision(
            should_stop=bool(stop_reasons),
            reasons=stop_reasons,
            recommended_mode=(ResolverAuthorityMode.SHADOW if stop_reasons else None),
        )
