"""Offline tests for Topic authority pilot stop and rollback recommendations."""

from dataclasses import FrozenInstanceError

import pytest

from src.resolution import (
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityMetrics,
    TopicAuthorityPilotStopEvaluator,
    TopicAuthorityPilotStopReason,
    TopicAuthoritySafetyMetrics,
)


def _operational(**changes):
    values = dict(
        articles_processed=0,
        topic_adjudication_requested=0,
        provider_calls=0,
        valid_adjudications=0,
        resolver_adjudicated_accepted=0,
        authoritative_topic_overrides=0,
        deterministic_topic_preserved=0,
        fallbacks=0,
        review_required_decisions=0,
        authority_blocked_by_policy=0,
        provider_failures=0,
        candidate_violations=0,
        fingerprint_failures=0,
        provider_validation_failures=0,
        max_consecutive_provider_validation_failures=0,
    )
    values.update(changes)
    return TopicAuthorityMetrics(**values)


def _safety(**changes):
    values = dict(
        audited_override_count=0,
        audited_correct_override_count=0,
        audited_incorrect_override_count=0,
        override_precision=None,
        rollback_count=0,
        authority_contract_violation_count=0,
        accepted_candidate_violation_count=0,
        accepted_fingerprint_violation_count=0,
        format_authority_violation_count=0,
        reader_intent_authority_violation_count=0,
    )
    values.update(changes)
    return TopicAuthoritySafetyMetrics(**values)


def _evaluate(operational=None, safety=None, config=None):
    return TopicAuthorityPilotStopEvaluator().evaluate(
        operational or _operational(),
        safety or _safety(),
        config or LimitedTopicAuthorityConfig(),
    )


def test_zero_violations_does_not_stop() -> None:
    decision = _evaluate()
    assert decision.should_stop is False
    assert decision.reasons == ()
    assert decision.recommended_mode is None


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"authority_contract_violation_count": 1}, TopicAuthorityPilotStopReason.AUTHORITY_CONTRACT_VIOLATION),
        ({"audited_override_count": 1, "audited_incorrect_override_count": 1, "override_precision": 0.0}, TopicAuthorityPilotStopReason.REGRESSION_BUDGET_EXCEEDED),
        ({"authority_contract_violation_count": 1, "accepted_candidate_violation_count": 1}, TopicAuthorityPilotStopReason.ACCEPTED_CANDIDATE_VIOLATION),
        ({"authority_contract_violation_count": 1, "accepted_fingerprint_violation_count": 1}, TopicAuthorityPilotStopReason.ACCEPTED_FINGERPRINT_VIOLATION),
        ({"authority_contract_violation_count": 1, "format_authority_violation_count": 1}, TopicAuthorityPilotStopReason.FORMAT_AUTHORITY_VIOLATION),
        ({"authority_contract_violation_count": 1, "reader_intent_authority_violation_count": 1}, TopicAuthorityPilotStopReason.READER_INTENT_AUTHORITY_VIOLATION),
    ],
)
def test_each_mandatory_safety_condition_stops(changes, reason) -> None:
    decision = _evaluate(safety=_safety(**changes))
    assert decision.should_stop is True
    assert reason in decision.reasons
    assert decision.recommended_mode is ResolverAuthorityMode.SHADOW


def test_first_incorrect_override_exceeds_zero_regression_budget() -> None:
    decision = _evaluate(
        safety=_safety(
            audited_override_count=1,
            audited_incorrect_override_count=1,
            override_precision=0.0,
        )
    )
    assert TopicAuthorityPilotStopReason.REGRESSION_BUDGET_EXCEEDED in decision.reasons


def test_configured_regression_budget_is_respected_as_metadata() -> None:
    config = LimitedTopicAuthorityConfig(regression_budget=1)
    decision = _evaluate(
        safety=_safety(
            audited_override_count=1,
            audited_incorrect_override_count=1,
            override_precision=0.0,
        ),
        config=config,
    )
    assert TopicAuthorityPilotStopReason.REGRESSION_BUDGET_EXCEEDED not in decision.reasons


def test_low_precision_below_minimum_sample_does_not_trigger_precision_stop() -> None:
    decision = _evaluate(
        safety=_safety(
            audited_override_count=29,
            audited_correct_override_count=25,
            audited_incorrect_override_count=4,
            override_precision=25 / 29,
        ),
        config=LimitedTopicAuthorityConfig(regression_budget=10),
    )
    assert TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD not in decision.reasons


def test_low_precision_at_thirty_triggers_stop() -> None:
    decision = _evaluate(
        safety=_safety(
            audited_override_count=30,
            audited_correct_override_count=26,
            audited_incorrect_override_count=4,
            override_precision=26 / 30,
        ),
        config=LimitedTopicAuthorityConfig(regression_budget=10),
    )
    assert TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD in decision.reasons


@pytest.mark.parametrize(("correct", "precision"), [(27, 0.9), (30, 1.0)])
def test_acceptable_precision_at_thirty_does_not_trigger_precision_stop(correct, precision) -> None:
    decision = _evaluate(
        safety=_safety(
            audited_override_count=30,
            audited_correct_override_count=correct,
            audited_incorrect_override_count=30 - correct,
            override_precision=precision,
        ),
        config=LimitedTopicAuthorityConfig(regression_budget=30),
    )
    assert TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD not in decision.reasons


def test_precision_minimum_uses_configured_thirty_sample_default() -> None:
    assert LimitedTopicAuthorityConfig().minimum_audited_override_sample == 30
    assert TopicAuthorityPilotStopEvaluator.OVERRIDE_PRECISION_THRESHOLD == 0.90


def test_three_consecutive_provider_validation_failures_stop() -> None:
    decision = _evaluate(
        operational=_operational(
            articles_processed=3,
            provider_calls=3,
            provider_validation_failures=3,
            max_consecutive_provider_validation_failures=3,
        )
    )
    assert TopicAuthorityPilotStopReason.CONSECUTIVE_PROVIDER_VALIDATION_FAILURES in decision.reasons


def test_provider_failure_rate_not_evaluated_before_twenty_calls() -> None:
    decision = _evaluate(
        operational=_operational(
            articles_processed=19,
            provider_calls=19,
            valid_adjudications=17,
            provider_validation_failures=2,
            max_consecutive_provider_validation_failures=1,
        )
    )
    assert TopicAuthorityPilotStopReason.PROVIDER_VALIDATION_FAILURE_RATE_EXCEEDED not in decision.reasons


def test_provider_failure_rate_above_five_percent_at_twenty_calls_stops() -> None:
    decision = _evaluate(
        operational=_operational(
            articles_processed=20,
            provider_calls=20,
            valid_adjudications=18,
            provider_validation_failures=2,
            max_consecutive_provider_validation_failures=1,
        )
    )
    assert TopicAuthorityPilotStopReason.PROVIDER_VALIDATION_FAILURE_RATE_EXCEEDED in decision.reasons


def test_exact_five_percent_does_not_stop() -> None:
    decision = _evaluate(
        operational=_operational(
            articles_processed=20,
            provider_calls=20,
            valid_adjudications=19,
            provider_validation_failures=1,
            max_consecutive_provider_validation_failures=1,
        )
    )
    assert TopicAuthorityPilotStopReason.PROVIDER_VALIDATION_FAILURE_RATE_EXCEEDED not in decision.reasons


def test_stop_evaluator_does_not_mutate_inputs_or_mode() -> None:
    operational = _operational()
    safety = _safety(authority_contract_violation_count=1)
    config = LimitedTopicAuthorityConfig(
        authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
    )
    before = (operational, safety, config)
    decision = _evaluate(operational, safety, config)
    assert (operational, safety, config) == before
    assert config.authority_mode is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
    assert decision.recommended_mode is ResolverAuthorityMode.SHADOW


def test_stop_decision_is_frozen() -> None:
    decision = _evaluate(safety=_safety(authority_contract_violation_count=1))
    with pytest.raises(FrozenInstanceError):
        decision.should_stop = False


def test_rollback_count_is_observed_but_not_mutated_or_a_stop_condition() -> None:
    safety = _safety(rollback_count=2)
    decision = _evaluate(safety=safety)
    assert safety.rollback_count == 2
    assert decision.should_stop is False


def test_multiple_stop_reasons_are_stably_aggregated() -> None:
    decision = _evaluate(
        safety=_safety(
            authority_contract_violation_count=2,
            accepted_candidate_violation_count=1,
            format_authority_violation_count=1,
        )
    )
    assert decision.reasons == (
        TopicAuthorityPilotStopReason.AUTHORITY_CONTRACT_VIOLATION,
        TopicAuthorityPilotStopReason.ACCEPTED_CANDIDATE_VIOLATION,
        TopicAuthorityPilotStopReason.FORMAT_AUTHORITY_VIOLATION,
    )
