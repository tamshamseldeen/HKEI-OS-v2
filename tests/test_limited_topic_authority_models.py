"""Contracts for limited Topic authority pilot configuration and models."""

from dataclasses import FrozenInstanceError, fields
from pathlib import Path

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
    TopicAuthorityDecision,
    TopicAuthorityMetrics,
    TopicAuthorityObservation,
    TopicAuthoritySafetyMetrics,
)
from src.topic.topic import Topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _decision(**overrides) -> TopicAuthorityDecision:
    values = {
        "deterministic_topic": Topic.SCIENCE,
        "resolved_topic": Topic.HEALTH,
        "authoritative_topic": Topic.SCIENCE,
        "authority_applied": False,
        "authority_source": EditorialResolutionSource.DETERMINISTIC_V1,
        "resolution_status": EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
        "provider_confidence": None,
        "ambiguity_remaining": False,
        "review_required": False,
        "warnings": (),
        "input_fingerprint": "sha256:fixture",
        "block_reasons": (TopicAuthorityBlockReason.MODE_SHADOW,),
    }
    values.update(overrides)
    return TopicAuthorityDecision(**values)


def _observation(**overrides) -> TopicAuthorityObservation:
    values = {
        "authority_mode": ResolverAuthorityMode.SHADOW,
        "authority_applied": False,
        "authority_source": EditorialResolutionSource.DETERMINISTIC_V1,
        "resolution_status": EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
        "provider_used": False,
        "provider_confidence": None,
        "ambiguity_remaining": False,
        "review_required": False,
        "block_reasons": (TopicAuthorityBlockReason.MODE_SHADOW,),
        "warnings": (),
        "candidate_compliant": True,
        "fingerprint_valid": True,
    }
    values.update(overrides)
    return TopicAuthorityObservation(**values)


def test_authority_mode_has_exact_values() -> None:
    assert tuple(item.value for item in ResolverAuthorityMode) == (
        "SHADOW", "LIMITED_TOPIC_AUTHORITY",
    )


def test_default_mode_is_shadow() -> None:
    assert LimitedTopicAuthorityConfig().authority_mode is ResolverAuthorityMode.SHADOW


def test_config_is_frozen() -> None:
    config = LimitedTopicAuthorityConfig()
    with pytest.raises(FrozenInstanceError):
        config.regression_budget = 1


def test_config_has_canonical_defaults() -> None:
    assert LimitedTopicAuthorityConfig() == LimitedTopicAuthorityConfig(
        authority_mode=ResolverAuthorityMode.SHADOW,
        minimum_provider_confidence=AdjudicationConfidence.MEDIUM,
        block_on_review_required=True,
        block_on_ambiguity=True,
        regression_budget=0,
        minimum_audited_override_sample=30,
    )


@pytest.mark.parametrize("mode", ["SHADOW", "UNKNOWN", None])
def test_invalid_or_raw_string_mode_is_rejected(mode) -> None:
    with pytest.raises(ValueError, match="ResolverAuthorityMode"):
        LimitedTopicAuthorityConfig(authority_mode=mode)


@pytest.mark.parametrize("confidence", ["MEDIUM", None, 2])
def test_confidence_enum_is_required(confidence) -> None:
    with pytest.raises(ValueError, match="AdjudicationConfidence"):
        LimitedTopicAuthorityConfig(minimum_provider_confidence=confidence)


def test_low_minimum_confidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="LOW"):
        LimitedTopicAuthorityConfig(minimum_provider_confidence=AdjudicationConfidence.LOW)


@pytest.mark.parametrize("confidence", [AdjudicationConfidence.MEDIUM, AdjudicationConfidence.HIGH])
def test_medium_and_high_minimum_confidence_are_supported(confidence) -> None:
    assert LimitedTopicAuthorityConfig(minimum_provider_confidence=confidence).minimum_provider_confidence is confidence


def test_negative_regression_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        LimitedTopicAuthorityConfig(regression_budget=-1)


@pytest.mark.parametrize("value", [True, 1.5, "0"])
def test_regression_budget_requires_integer(value) -> None:
    with pytest.raises(ValueError, match="integer"):
        LimitedTopicAuthorityConfig(regression_budget=value)


def test_minimum_sample_default_is_thirty() -> None:
    assert LimitedTopicAuthorityConfig().minimum_audited_override_sample == 30


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_minimum_sample_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        LimitedTopicAuthorityConfig(minimum_audited_override_sample=value)


def test_policy_flags_require_booleans() -> None:
    with pytest.raises(ValueError, match="boolean"):
        LimitedTopicAuthorityConfig(block_on_review_required=1)
    with pytest.raises(ValueError, match="boolean"):
        LimitedTopicAuthorityConfig(block_on_ambiguity="yes")


def test_authority_decision_is_frozen() -> None:
    decision = _decision()
    with pytest.raises(FrozenInstanceError):
        decision.authority_applied = True


def test_authority_applied_requires_empty_block_reasons() -> None:
    with pytest.raises(ValueError, match="empty block_reasons"):
        _decision(
            authority_applied=True,
            authority_source=EditorialResolutionSource.ADJUDICATION,
            authoritative_topic=Topic.HEALTH,
        )


def test_authority_applied_requires_adjudication_source() -> None:
    with pytest.raises(ValueError, match="ADJUDICATION source"):
        _decision(authority_applied=True, authoritative_topic=Topic.HEALTH, block_reasons=())


def test_authority_applied_uses_resolved_topic() -> None:
    decision = _decision(
        authority_applied=True,
        authority_source=EditorialResolutionSource.ADJUDICATION,
        authoritative_topic=Topic.HEALTH,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_confidence=AdjudicationConfidence.HIGH,
        block_reasons=(),
    )
    assert decision.authoritative_topic is decision.resolved_topic


def test_blocked_decision_supports_multiple_immutable_reasons() -> None:
    reasons = (
        TopicAuthorityBlockReason.REVIEW_REQUIRED,
        TopicAuthorityBlockReason.AMBIGUITY_REMAINS,
    )
    assert _decision(block_reasons=reasons).block_reasons == reasons


def test_mutable_block_reasons_are_rejected() -> None:
    with pytest.raises(ValueError, match="tuple"):
        _decision(block_reasons=[TopicAuthorityBlockReason.MODE_SHADOW])


def test_block_reason_enum_contains_specification_contract() -> None:
    required = {
        "MODE_SHADOW", "RESOLUTION_NOT_ADJUDICATED", "SOURCE_NOT_ADJUDICATION",
        "REVIEW_REQUIRED", "AMBIGUITY_REMAINS", "PROVIDER_CONFIDENCE_TOO_LOW",
        "FINGERPRINT_INVALID", "CANDIDATE_INVALID", "RESPONSE_INVALID",
        "PROVIDER_UNAVAILABLE",
    }
    assert required <= {item.value for item in TopicAuthorityBlockReason}


def test_no_topic_change_has_exact_symbolic_value() -> None:
    assert TopicAuthorityBlockReason.NO_TOPIC_CHANGE.value == "NO_TOPIC_CHANGE"


def test_existing_block_reasons_are_preserved_with_no_duplicates() -> None:
    existing = {
        "MODE_SHADOW", "TOPIC_ADJUDICATION_NOT_REQUESTED",
        "RESOLUTION_NOT_ADJUDICATED", "SOURCE_NOT_ADJUDICATION",
        "REVIEW_REQUIRED", "AMBIGUITY_REMAINS", "PROVIDER_CONFIDENCE_TOO_LOW",
        "FINGERPRINT_INVALID", "CANDIDATE_INVALID", "RESPONSE_INVALID",
        "PROVIDER_UNAVAILABLE",
    }
    values = tuple(item.value for item in TopicAuthorityBlockReason)
    assert existing <= set(values)
    assert len(values) == 12
    assert len(values) == len(set(values))


def test_valid_same_label_adjudication_is_a_non_error_no_override_decision() -> None:
    decision = _decision(
        resolved_topic=Topic.SCIENCE,
        authoritative_topic=Topic.SCIENCE,
        authority_applied=False,
        authority_source=EditorialResolutionSource.DETERMINISTIC_V1,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_confidence=AdjudicationConfidence.HIGH,
        block_reasons=(TopicAuthorityBlockReason.NO_TOPIC_CHANGE,),
    )
    assert decision.authoritative_topic is decision.deterministic_topic
    assert decision.authority_applied is False
    assert decision.authority_source is EditorialResolutionSource.DETERMINISTIC_V1
    assert decision.block_reasons == (TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)


def test_no_topic_change_has_no_failure_metric_implication() -> None:
    metric_fields = {item.name for item in fields(TopicAuthorityMetrics)}
    safety_fields = {item.name for item in fields(TopicAuthoritySafetyMetrics)}
    assert "valid_adjudications" in metric_fields
    assert "resolver_adjudicated_accepted" in metric_fields
    assert "authoritative_topic_overrides" in metric_fields
    assert "provider_failures" in metric_fields
    assert "audited_incorrect_override_count" in safety_fields
    assert "authority_contract_violation_count" in safety_fields
    assert TopicAuthorityBlockReason.NO_TOPIC_CHANGE not in {
        TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE,
        TopicAuthorityBlockReason.RESPONSE_INVALID,
    }


def test_specification_documents_no_topic_change_contract() -> None:
    specification = (
        PROJECT_ROOT / "docs" / "LIMITED_TOPIC_AUTHORITY_PILOT_SPECIFICATION.md"
    ).read_text(encoding="utf-8")
    assert "agrees with the deterministic Topic" in specification
    assert "`NO_TOPIC_CHANGE`" in specification


def test_observation_is_frozen() -> None:
    observation = _observation()
    with pytest.raises(FrozenInstanceError):
        observation.provider_used = True


def test_observation_rejects_mutable_collections() -> None:
    with pytest.raises(ValueError, match="tuple"):
        _observation(block_reasons=[])
    with pytest.raises(ValueError, match="tuple"):
        _observation(warnings=[EditorialResolutionWarning.PROVIDER_UNAVAILABLE])


def test_operational_metrics_snapshot_is_frozen_and_defaults_to_zero() -> None:
    metrics = TopicAuthorityMetrics()
    assert all(getattr(metrics, item.name) == 0 for item in fields(metrics))
    with pytest.raises(FrozenInstanceError):
        metrics.provider_calls = 1


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_operational_metrics_reject_invalid_counts(value) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        TopicAuthorityMetrics(provider_calls=value)


def test_safety_metrics_are_separate_and_frozen() -> None:
    metrics = TopicAuthoritySafetyMetrics(override_precision=1.0)
    with pytest.raises(FrozenInstanceError):
        metrics.rollback_count = 1


@pytest.mark.parametrize("value", [-0.1, 1.1, True, "1"])
def test_safety_metrics_reject_invalid_precision(value) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        TopicAuthoritySafetyMetrics(override_precision=value)


def test_pending_audit_record_is_frozen_and_sanitized() -> None:
    record = TopicAuthorityAuditRecord(
        decision_fingerprint="sha256:decision",
        authoritative_topic=Topic.SCIENCE,
        review_status=TopicAuthorityAuditStatus.PENDING,
        human_reviewed_correctness=None,
    )
    with pytest.raises(FrozenInstanceError):
        record.review_status = TopicAuthorityAuditStatus.COMPLETED


def test_completed_audit_requires_correctness() -> None:
    with pytest.raises(ValueError, match="require reviewed correctness"):
        TopicAuthorityAuditRecord(
            "sha256:decision", Topic.SCIENCE, TopicAuthorityAuditStatus.COMPLETED, None
        )


def test_pending_audit_rejects_premature_correctness() -> None:
    with pytest.raises(ValueError, match="pending audits"):
        TopicAuthorityAuditRecord(
            "sha256:decision", Topic.SCIENCE, TopicAuthorityAuditStatus.PENDING, True
        )


def test_models_exclude_format_and_reader_intent_authority() -> None:
    names = {
        item.name
        for model in (TopicAuthorityDecision, TopicAuthorityObservation, TopicAuthorityAuditRecord)
        for item in fields(model)
    }
    assert "authoritative_format" not in names
    assert "authoritative_reader_intent" not in names


def test_models_exclude_sensitive_payload_fields() -> None:
    names = {
        item.name
        for model in (
            LimitedTopicAuthorityConfig, TopicAuthorityDecision,
            TopicAuthorityObservation, TopicAuthorityAuditRecord,
        )
        for item in fields(model)
    }
    forbidden = {
        "article", "article_body", "source", "source_body", "raw_prompt",
        "raw_response", "api_key", "secret", "authorization_header", "chain_of_thought",
    }
    assert names.isdisjoint(forbidden)


def test_kill_switch_has_one_source_of_truth() -> None:
    names = {item.name for item in fields(LimitedTopicAuthorityConfig)}
    assert "authority_mode" in names
    assert names.isdisjoint({"enabled", "kill_switch", "authority_enabled"})


def test_specification_contract_file_and_canonical_values_are_aligned() -> None:
    specification = PROJECT_ROOT / "docs" / "LIMITED_TOPIC_AUTHORITY_PILOT_SPECIFICATION.md"
    assert specification.is_file()
    config = LimitedTopicAuthorityConfig()
    assert (
        config.authority_mode,
        config.minimum_provider_confidence,
        config.block_on_review_required,
        config.block_on_ambiguity,
        config.regression_budget,
        config.minimum_audited_override_sample,
    ) == (
        ResolverAuthorityMode.SHADOW,
        AdjudicationConfidence.MEDIUM,
        True,
        True,
        0,
        30,
    )


def test_new_models_have_no_gate_or_provider_dependency() -> None:
    paths = [
        PROJECT_ROOT / "src" / "resolution" / name
        for name in (
            "resolver_authority_mode.py", "limited_topic_authority_config.py",
            "topic_authority_block_reason.py", "topic_authority_decision.py",
            "topic_authority_observation.py", "topic_authority_metrics.py",
            "topic_authority_audit_record.py",
        )
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "openai" not in source.lower()
    assert "semantic_adjudication_gate" not in source
    assert "LimitedEditorialResolver" not in source
