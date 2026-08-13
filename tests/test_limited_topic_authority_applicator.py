"""Focused offline tests for the pure limited Topic authority applicator."""

from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.resolution import (
    EditorialDimensionResolution,
    EditorialResolutionDimension,
    EditorialResolutionResult,
    EditorialResolutionSource,
    EditorialResolutionStatus,
    EditorialResolutionWarning,
    LimitedTopicAuthorityApplicator,
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityBlockReason,
)
from src.topic.topic import Topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _dimension(dimension, value):
    return EditorialDimensionResolution(
        dimension=dimension,
        value=value,
        status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
        source=EditorialResolutionSource.DETERMINISTIC_V1,
        confidence="HIGH",
        confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
        ambiguity=False,
        review_required=False,
        warnings=(),
    )


def _result(
    *,
    deterministic_topic=Topic.SCIENCE,
    resolved_topic=Topic.HEALTH,
    status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
    source=EditorialResolutionSource.ADJUDICATION,
    confidence="MEDIUM",
    confidence_source=EditorialResolutionSource.ADJUDICATION,
    ambiguity=False,
    review_required=False,
    warnings=(),
    fingerprint="sha256:canonical",
):
    topic = EditorialDimensionResolution(
        dimension=EditorialResolutionDimension.TOPIC,
        value=resolved_topic,
        status=status,
        source=source,
        confidence=confidence,
        confidence_source=confidence_source,
        ambiguity=ambiguity,
        review_required=review_required,
        warnings=warnings,
    )
    return EditorialResolutionResult(
        deterministic_topic=deterministic_topic,
        topic_resolution=topic,
        format_resolution=_dimension(
            EditorialResolutionDimension.FORMAT, EditorialFormat.STANDARD_NEWS,
        ),
        reader_intent_resolution=_dimension(
            EditorialResolutionDimension.READER_INTENT, ReaderIntent.GET_UPDATE,
        ),
        review_required=review_required,
        warnings=warnings,
        provider_used=status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        input_fingerprint=fingerprint,
    )


def _unresolved_result():
    return _result(
        resolved_topic=None,
        status=EditorialResolutionStatus.UNRESOLVED,
        source=EditorialResolutionSource.NONE,
        confidence=None,
        confidence_source=EditorialResolutionSource.NONE,
        review_required=True,
        warnings=(EditorialResolutionWarning.TOPIC_UNRESOLVED,),
    )


def _apply(result=None, config=None, **trust):
    flags = dict(
        candidate_compliant=True,
        fingerprint_valid=True,
        response_valid=True,
        provider_available=True,
    )
    flags.update(trust)
    return LimitedTopicAuthorityApplicator().apply(
        result or _result(), config or LimitedTopicAuthorityConfig(), **flags,
    )


def _enabled(minimum=AdjudicationConfidence.MEDIUM):
    return LimitedTopicAuthorityConfig(
        authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        minimum_provider_confidence=minimum,
    )


def test_default_shadow_blocks_authority() -> None:
    assert _apply().authority_applied is False


def test_valid_adjudication_is_still_blocked_in_shadow() -> None:
    decision = _apply()
    assert decision.resolution_status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert TopicAuthorityBlockReason.MODE_SHADOW in decision.block_reasons


def test_shadow_keeps_deterministic_topic_authoritative() -> None:
    assert _apply().authoritative_topic is Topic.SCIENCE


def test_shadow_uses_deterministic_authority_source() -> None:
    assert _apply().authority_source is EditorialResolutionSource.DETERMINISTIC_V1


def test_shadow_aggregates_other_blockers_in_enum_order() -> None:
    decision = _apply(
        _result(confidence="LOW", ambiguity=True, review_required=True),
        fingerprint_valid=False,
    )
    assert decision.block_reasons == (
        TopicAuthorityBlockReason.MODE_SHADOW,
        TopicAuthorityBlockReason.REVIEW_REQUIRED,
        TopicAuthorityBlockReason.AMBIGUITY_REMAINS,
        TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW,
        TopicAuthorityBlockReason.FINGERPRINT_INVALID,
    )


@pytest.mark.parametrize("confidence", ["MEDIUM", "HIGH"])
def test_enabled_medium_and_high_confidence_apply(confidence) -> None:
    decision = _apply(_result(confidence=confidence), _enabled())
    assert decision.authority_applied is True
    assert decision.authoritative_topic is Topic.HEALTH
    assert decision.authority_source is EditorialResolutionSource.ADJUDICATION
    assert decision.block_reasons == ()


def test_low_confidence_is_blocked() -> None:
    decision = _apply(_result(confidence="LOW"), _enabled())
    assert decision.block_reasons == (TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW,)


def test_high_minimum_blocks_medium() -> None:
    decision = _apply(_result(confidence="MEDIUM"), _enabled(AdjudicationConfidence.HIGH))
    assert decision.block_reasons == (TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW,)


def test_confidence_order_is_explicit_not_lexical() -> None:
    assert LimitedTopicAuthorityApplicator._CONFIDENCE_RANK == {
        AdjudicationConfidence.LOW: 0,
        AdjudicationConfidence.MEDIUM: 1,
        AdjudicationConfidence.HIGH: 2,
    }


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"review_required": True}, (TopicAuthorityBlockReason.REVIEW_REQUIRED,)),
        ({"ambiguity": True}, (TopicAuthorityBlockReason.AMBIGUITY_REMAINS,)),
        (
            {"review_required": True, "ambiguity": True},
            (
                TopicAuthorityBlockReason.REVIEW_REQUIRED,
                TopicAuthorityBlockReason.AMBIGUITY_REMAINS,
            ),
        ),
    ],
)
def test_review_and_ambiguity_policy_blocks(changes, expected) -> None:
    assert _apply(_result(**changes), _enabled()).block_reasons == expected


def test_clean_adjudication_has_no_policy_block() -> None:
    assert _apply(_result(), _enabled()).block_reasons == ()


@pytest.mark.parametrize(
    ("flag", "reason"),
    [
        ("response_valid", TopicAuthorityBlockReason.RESPONSE_INVALID),
        ("candidate_compliant", TopicAuthorityBlockReason.CANDIDATE_INVALID),
        ("fingerprint_valid", TopicAuthorityBlockReason.FINGERPRINT_INVALID),
        ("provider_available", TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE),
    ],
)
def test_each_explicit_trust_failure_blocks(flag, reason) -> None:
    decision = _apply(_result(), _enabled(), **{flag: False})
    assert decision.block_reasons == (reason,)
    assert decision.authoritative_topic is Topic.SCIENCE


def test_multiple_trust_failures_aggregate_stably() -> None:
    decision = _apply(
        _result(), _enabled(), candidate_compliant=False, fingerprint_valid=False,
        response_valid=False, provider_available=False,
    )
    assert decision.block_reasons == (
        TopicAuthorityBlockReason.FINGERPRINT_INVALID,
        TopicAuthorityBlockReason.CANDIDATE_INVALID,
        TopicAuthorityBlockReason.RESPONSE_INVALID,
        TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE,
    )


@pytest.mark.parametrize(
    "status",
    [
        EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
        EditorialResolutionStatus.FALLBACK_ACCEPTED,
        EditorialResolutionStatus.REVIEW_REQUIRED,
    ],
)
def test_non_adjudicated_resolution_statuses_block(status) -> None:
    source = {
        EditorialResolutionStatus.DETERMINISTIC_ACCEPTED: EditorialResolutionSource.DETERMINISTIC_V1,
        EditorialResolutionStatus.FALLBACK_ACCEPTED: EditorialResolutionSource.FALLBACK,
        EditorialResolutionStatus.REVIEW_REQUIRED: EditorialResolutionSource.DETERMINISTIC_V1,
    }[status]
    decision = _apply(
        _result(
            resolved_topic=Topic.SCIENCE,
            status=status,
            source=source,
            confidence="HIGH",
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            review_required=status is EditorialResolutionStatus.REVIEW_REQUIRED,
        ),
        _enabled(),
    )
    assert TopicAuthorityBlockReason.RESOLUTION_NOT_ADJUDICATED in decision.block_reasons
    assert TopicAuthorityBlockReason.SOURCE_NOT_ADJUDICATION in decision.block_reasons


def test_unresolved_status_blocks_and_preserves_none_resolved_topic() -> None:
    decision = _apply(_unresolved_result(), _enabled())
    assert decision.resolved_topic is None
    assert decision.authoritative_topic is Topic.SCIENCE
    assert TopicAuthorityBlockReason.RESOLUTION_NOT_ADJUDICATED in decision.block_reasons


def test_non_adjudication_source_blocks_fail_safe() -> None:
    decision = _apply(
        _result(
            resolved_topic=Topic.SCIENCE,
            status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
            source=EditorialResolutionSource.DETERMINISTIC_V1,
            confidence="HIGH",
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
        ),
        _enabled(),
    )
    assert TopicAuthorityBlockReason.SOURCE_NOT_ADJUDICATION in decision.block_reasons


def test_valid_same_label_returns_only_no_topic_change() -> None:
    decision = _apply(_result(resolved_topic=Topic.SCIENCE), _enabled())
    assert decision.authority_applied is False
    assert decision.authoritative_topic is Topic.SCIENCE
    assert decision.authority_source is EditorialResolutionSource.DETERMINISTIC_V1
    assert decision.block_reasons == (TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)


def test_no_topic_change_is_not_fallback_or_error_semantics() -> None:
    decision = _apply(_result(resolved_topic=Topic.SCIENCE), _enabled())
    assert decision.resolution_status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert decision.provider_confidence is AdjudicationConfidence.MEDIUM
    assert decision.block_reasons != (TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE,)


def test_no_topic_change_does_not_represent_an_override() -> None:
    decision = _apply(_result(resolved_topic=Topic.SCIENCE), _enabled())
    assert decision.authority_applied is False
    assert decision.authoritative_topic is decision.deterministic_topic


@pytest.mark.parametrize(
    ("result", "trust", "reason"),
    [
        (_result(resolved_topic=Topic.SCIENCE), {"fingerprint_valid": False}, TopicAuthorityBlockReason.FINGERPRINT_INVALID),
        (_result(resolved_topic=Topic.SCIENCE, review_required=True), {}, TopicAuthorityBlockReason.REVIEW_REQUIRED),
        (_result(resolved_topic=Topic.SCIENCE, confidence="LOW"), {}, TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW),
    ],
)
def test_no_topic_change_never_masks_other_blockers(result, trust, reason) -> None:
    decision = _apply(result, _enabled(), **trust)
    assert reason in decision.block_reasons
    assert TopicAuthorityBlockReason.NO_TOPIC_CHANGE not in decision.block_reasons


def test_kill_switch_immediately_restores_deterministic_authority() -> None:
    result = _result()
    enabled = _apply(result, _enabled())
    shadow = _apply(result, LimitedTopicAuthorityConfig())
    assert enabled.authority_applied is True
    assert shadow.authority_applied is False
    assert shadow.authoritative_topic is Topic.SCIENCE
    assert TopicAuthorityBlockReason.MODE_SHADOW in shadow.block_reasons


def test_no_persistent_authority_state_after_kill_switch() -> None:
    applicator = LimitedTopicAuthorityApplicator()
    result = _result()
    first = applicator.apply(result, _enabled(), True, True, True, True)
    second = applicator.apply(result, LimitedTopicAuthorityConfig(), True, True, True, True)
    third = applicator.apply(result, _enabled(), True, True, True, True)
    assert first == third
    assert second != first


def test_default_config_always_preserves_deterministic_topic() -> None:
    assert _apply(_result(confidence="HIGH")).authoritative_topic is Topic.SCIENCE


def test_decision_is_idempotent() -> None:
    result = _result()
    config = _enabled()
    assert _apply(result, config) == _apply(result, config)


def test_inputs_and_warnings_are_not_mutated() -> None:
    warnings = (EditorialResolutionWarning.ADJUDICATION_AMBIGUITY_REMAINS,)
    result = _result(ambiguity=True, review_required=True, warnings=warnings)
    config = _enabled()
    before = (result, config, result.warnings, result.topic_resolution.warnings)
    decision = _apply(result, config)
    assert before == (result, config, result.warnings, result.topic_resolution.warnings)
    assert decision.warnings == warnings


def test_canonical_fingerprint_is_preserved_including_none() -> None:
    assert _apply(_result(fingerprint="sha256:canonical"), _enabled()).input_fingerprint == "sha256:canonical"
    assert _apply(_result(fingerprint=None), _enabled()).input_fingerprint is None


@pytest.mark.parametrize("flag", ["candidate_compliant", "fingerprint_valid", "response_valid", "provider_available"])
def test_trust_inputs_require_real_booleans(flag) -> None:
    with pytest.raises(ValueError, match=flag):
        _apply(_result(), _enabled(), **{flag: 1})


def test_decision_remains_frozen() -> None:
    decision = _apply(_result(), _enabled())
    with pytest.raises(FrozenInstanceError):
        decision.authority_applied = False


def test_no_format_or_reader_intent_authority_fields_exist() -> None:
    names = {item.name for item in fields(type(_apply()))}
    assert "authoritative_format" not in names
    assert "authoritative_reader_intent" not in names


def test_applicator_has_no_gate_provider_or_network_dependencies() -> None:
    source = (
        PROJECT_ROOT / "src" / "resolution" / "limited_topic_authority_applicator.py"
    ).read_text(encoding="utf-8").lower()
    forbidden = ("openai", "http", "semanticadjudicationgate", "provider_config", "api_key")
    assert all(item not in source for item in forbidden)


def test_applicator_does_not_import_or_modify_resolver() -> None:
    source = inspect.getsource(LimitedTopicAuthorityApplicator)
    assert "LimitedEditorialResolver" not in source


def test_block_reason_output_has_no_duplicates() -> None:
    decision = _apply(
        _result(ambiguity=True, review_required=True, confidence="LOW"),
        LimitedTopicAuthorityConfig(),
        candidate_compliant=False,
        fingerprint_valid=False,
        response_valid=False,
        provider_available=False,
    )
    assert len(decision.block_reasons) == len(set(decision.block_reasons))


def test_applied_changed_topic_is_conceptually_the_only_override_state() -> None:
    changed = _apply(_result(), _enabled())
    same = _apply(_result(resolved_topic=Topic.SCIENCE), _enabled())
    shadow = _apply(_result(), LimitedTopicAuthorityConfig())
    assert changed.authority_applied and changed.authoritative_topic is not changed.deterministic_topic
    assert not same.authority_applied and not shadow.authority_applied
