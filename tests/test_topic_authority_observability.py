"""Offline contracts for Topic authority observations and metrics."""

from dataclasses import FrozenInstanceError, asdict, fields

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.resolution import (
    EditorialResolutionSource,
    EditorialResolutionStatus,
    EditorialResolutionWarning,
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityAuditRecord,
    TopicAuthorityAuditStatus,
    TopicAuthorityBlockReason,
    TopicAuthorityContractValidator,
    TopicAuthorityContractViolation,
    TopicAuthorityDecision,
    TopicAuthorityMetrics,
    TopicAuthorityMetricsAggregator,
    TopicAuthorityObservationBuilder,
    TopicAuthorityProviderFailureCategory,
)
from src.topic.topic import Topic


def _decision(**changes):
    values = dict(
        deterministic_topic=Topic.SCIENCE,
        resolved_topic=Topic.HEALTH,
        authoritative_topic=Topic.HEALTH,
        authority_applied=True,
        authority_source=EditorialResolutionSource.ADJUDICATION,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_confidence=AdjudicationConfidence.HIGH,
        ambiguity_remaining=False,
        review_required=False,
        warnings=(),
        input_fingerprint="sha256:decision-1",
        block_reasons=(),
    )
    values.update(changes)
    return TopicAuthorityDecision(**values)


def _blocked(reason=TopicAuthorityBlockReason.MODE_SHADOW, **changes):
    return _decision(
        authoritative_topic=Topic.SCIENCE,
        authority_applied=False,
        authority_source=EditorialResolutionSource.DETERMINISTIC_V1,
        block_reasons=(reason,),
        **changes,
    )


def _observation(
    decision=None,
    mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
    **metadata,
):
    values = dict(
        topic_adjudication_requested=True,
        provider_called=True,
        provider_valid=True,
        candidate_compliant=True,
        fingerprint_valid=True,
        provider_failure_category=None,
    )
    values.update(metadata)
    return TopicAuthorityObservationBuilder().build(
        decision or _decision(), mode, **values,
    )


def test_shadow_observation_is_sanitized_and_non_authoritative() -> None:
    observation = _observation(
        _blocked(), ResolverAuthorityMode.SHADOW,
    )
    assert observation.authority_mode is ResolverAuthorityMode.SHADOW
    assert observation.authority_applied is False
    assert observation.block_reasons == (TopicAuthorityBlockReason.MODE_SHADOW,)


def test_limited_applied_observation_preserves_decision() -> None:
    decision = _decision()
    observation = _observation(decision)
    assert observation.authority_applied is True
    assert observation.authority_source is EditorialResolutionSource.ADJUDICATION
    assert observation.provider_confidence is AdjudicationConfidence.HIGH
    assert observation.decision_fingerprint == decision.input_fingerprint


def test_no_topic_change_observation_is_valid_noop() -> None:
    observation = _observation(
        _blocked(
            TopicAuthorityBlockReason.NO_TOPIC_CHANGE,
            resolved_topic=Topic.SCIENCE,
        )
    )
    assert observation.provider_valid is True
    assert observation.block_reasons == (TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)


@pytest.mark.parametrize(
    "reason",
    [
        TopicAuthorityBlockReason.REVIEW_REQUIRED,
        TopicAuthorityBlockReason.AMBIGUITY_REMAINS,
        TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW,
    ],
)
def test_policy_blocked_observations_preserve_reason(reason) -> None:
    assert _observation(_blocked(reason)).block_reasons == (reason,)


def test_provider_failure_uses_only_symbolic_category() -> None:
    observation = _observation(
        _blocked(TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE),
        provider_valid=False,
        provider_failure_category=TopicAuthorityProviderFailureCategory.TIMEOUT,
    )
    assert observation.provider_failure_category is TopicAuthorityProviderFailureCategory.TIMEOUT
    assert observation.provider_used is False


@pytest.mark.parametrize(
    ("metadata", "reason"),
    [
        ({"candidate_compliant": False}, TopicAuthorityBlockReason.CANDIDATE_INVALID),
        ({"fingerprint_valid": False}, TopicAuthorityBlockReason.FINGERPRINT_INVALID),
    ],
)
def test_invalid_trust_observations_are_explicit(metadata, reason) -> None:
    observation = _observation(_blocked(reason), **metadata)
    assert reason in observation.block_reasons
    assert not getattr(observation, next(iter(metadata)))


def test_observation_serialization_excludes_sensitive_payload_fields() -> None:
    serialized = asdict(_observation())
    forbidden = {
        "article_body", "source_text", "raw_prompt", "raw_response", "api_key",
        "authorization", "chain_of_thought",
    }
    assert set(serialized).isdisjoint(forbidden)
    assert all(not any(token in key.lower() for token in forbidden) for key in serialized)


def test_observation_is_frozen() -> None:
    observation = _observation()
    with pytest.raises(FrozenInstanceError):
        observation.provider_called = False


def test_operational_metrics_count_required_events() -> None:
    observations = (
        _observation(),
        _observation(_blocked(), ResolverAuthorityMode.SHADOW),
        _observation(
            _blocked(
                TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE,
                resolution_status=EditorialResolutionStatus.FALLBACK_ACCEPTED,
                provider_confidence=None,
            ),
            provider_valid=False,
            provider_failure_category=TopicAuthorityProviderFailureCategory.UNAVAILABLE,
        ),
    )
    metrics = TopicAuthorityMetricsAggregator().aggregate_operational(observations)
    assert metrics.articles_processed == 3
    assert metrics.topic_adjudication_requested == 3
    assert metrics.provider_calls == 3
    assert metrics.valid_adjudications == 2
    assert metrics.resolver_adjudicated_accepted == 2
    assert metrics.authoritative_topic_overrides == 1
    assert metrics.deterministic_topic_preserved == 2
    assert metrics.authority_blocked_by_policy == 1
    assert metrics.provider_failures == 1


def test_fallback_candidate_and_fingerprint_metrics() -> None:
    fallback = _blocked(
        TopicAuthorityBlockReason.CANDIDATE_INVALID,
        resolution_status=EditorialResolutionStatus.FALLBACK_ACCEPTED,
        provider_confidence=None,
    )
    observations = (
        _observation(fallback, candidate_compliant=False),
        _observation(_blocked(TopicAuthorityBlockReason.FINGERPRINT_INVALID), fingerprint_valid=False),
    )
    metrics = TopicAuthorityMetricsAggregator().aggregate_operational(observations)
    assert metrics.fallbacks == 1
    assert metrics.candidate_violations == 1
    assert metrics.fingerprint_failures == 1


def test_no_topic_change_metrics_are_valid_without_override_or_failure() -> None:
    observation = _observation(
        _blocked(TopicAuthorityBlockReason.NO_TOPIC_CHANGE, resolved_topic=Topic.SCIENCE)
    )
    metrics = TopicAuthorityMetricsAggregator().aggregate_operational((observation,))
    assert metrics.valid_adjudications == 1
    assert metrics.resolver_adjudicated_accepted == 1
    assert metrics.deterministic_topic_preserved == 1
    assert metrics.authoritative_topic_overrides == 0
    assert metrics.fallbacks == 0
    assert metrics.provider_failures == 0


def test_shadow_never_counts_authoritative_override() -> None:
    unsafe_claim = _observation(_decision(), ResolverAuthorityMode.SHADOW)
    metrics = TopicAuthorityMetricsAggregator().aggregate_operational((unsafe_claim,))
    assert metrics.authoritative_topic_overrides == 0


def test_metrics_are_immutable_and_order_independent_for_valid_events() -> None:
    first = _observation()
    second = _observation(_blocked(), ResolverAuthorityMode.SHADOW)
    aggregator = TopicAuthorityMetricsAggregator()
    left = aggregator.aggregate_operational((first, second))
    right = aggregator.aggregate_operational((second, first))
    assert left == right
    with pytest.raises(FrozenInstanceError):
        left.provider_calls = 9


def _audit(fingerprint, correct, status=TopicAuthorityAuditStatus.COMPLETED):
    return TopicAuthorityAuditRecord(
        decision_fingerprint=fingerprint,
        authoritative_topic=Topic.HEALTH,
        review_status=status,
        human_reviewed_correctness=correct,
    )


def test_independent_correct_and_incorrect_audits_compute_precision() -> None:
    observations = (
        _observation(_decision(input_fingerprint="sha256:a")),
        _observation(_decision(input_fingerprint="sha256:b")),
    )
    safety = TopicAuthorityMetricsAggregator().aggregate_safety(
        observations, (_audit("sha256:a", True), _audit("sha256:b", False)),
    )
    assert safety.audited_override_count == 2
    assert safety.audited_correct_override_count == 1
    assert safety.audited_incorrect_override_count == 1
    assert safety.override_precision == 0.5


def test_duplicate_audit_identity_is_rejected() -> None:
    observations = (_observation(_decision(input_fingerprint="sha256:a")),)
    with pytest.raises(ValueError, match="duplicate"):
        TopicAuthorityMetricsAggregator().aggregate_safety(
            observations, (_audit("sha256:a", True), _audit("sha256:a", True)),
        )


def test_no_topic_change_cannot_enter_authoritative_audit_sample() -> None:
    observation = _observation(
        _blocked(
            TopicAuthorityBlockReason.NO_TOPIC_CHANGE,
            resolved_topic=Topic.SCIENCE,
            input_fingerprint="sha256:no-change",
        )
    )
    with pytest.raises(ValueError, match="authority-applied"):
        TopicAuthorityMetricsAggregator().aggregate_safety(
            (observation,), (_audit("sha256:no-change", True),),
        )


def test_provider_output_cannot_auto_create_human_correctness() -> None:
    safety = TopicAuthorityMetricsAggregator().aggregate_safety((_observation(),))
    assert safety.audited_override_count == 0
    assert safety.override_precision is None


def test_contract_validator_accepts_valid_applied_authority() -> None:
    assert TopicAuthorityContractValidator().validate(
        _decision(), LimitedTopicAuthorityConfig(
            authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
        ), True, True, True, True,
    ) == ()


def test_contract_validator_flags_shadow_applied_authority() -> None:
    violations = TopicAuthorityContractValidator().validate(
        _decision(), LimitedTopicAuthorityConfig(), True, True, True, True,
    )
    assert violations == (TopicAuthorityContractViolation.AUTHORITY_APPLIED_IN_SHADOW_MODE,)


@pytest.mark.parametrize(
    ("decision_changes", "trust", "violation"),
    [
        ({"review_required": True}, {}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_REVIEW_REQUIRED),
        ({"ambiguity_remaining": True}, {}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_AMBIGUITY),
        ({"provider_confidence": AdjudicationConfidence.LOW}, {}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_LOW_CONFIDENCE),
        ({}, {"response_valid": False}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_RESPONSE),
        ({}, {"candidate_compliant": False}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_CANDIDATE),
        ({}, {"fingerprint_valid": False}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_FINGERPRINT),
        ({}, {"provider_available": False}, TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_PROVIDER_UNAVAILABLE),
    ],
)
def test_contract_validator_flags_each_applied_trust_violation(decision_changes, trust, violation) -> None:
    flags = dict(candidate_compliant=True, fingerprint_valid=True, response_valid=True, provider_available=True)
    flags.update(trust)
    violations = TopicAuthorityContractValidator().validate(
        _decision(**decision_changes),
        LimitedTopicAuthorityConfig(authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        **flags,
    )
    assert violation in violations


def test_format_and_reader_intent_violation_detection_is_observational_only() -> None:
    violations = TopicAuthorityContractValidator().validate(
        _blocked(), LimitedTopicAuthorityConfig(), True, True, True, True,
        format_authority_applied=True, reader_intent_authority_applied=True,
    )
    assert violations == (
        TopicAuthorityContractViolation.FORMAT_AUTHORITY_VIOLATION,
        TopicAuthorityContractViolation.READER_INTENT_AUTHORITY_VIOLATION,
    )


def test_metrics_models_enforce_consistency() -> None:
    with pytest.raises(ValueError, match="overrides"):
        TopicAuthorityMetrics(
            articles_processed=1, provider_calls=1, valid_adjudications=1,
            resolver_adjudicated_accepted=0, authoritative_topic_overrides=1,
        )


def test_observation_fields_contain_no_format_or_reader_intent_authority() -> None:
    names = {item.name for item in fields(type(_observation()))}
    assert "authoritative_format" not in names
    assert "authoritative_reader_intent" not in names
