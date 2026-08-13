"""Focused offline tests for the pure limited editorial Resolver."""

from dataclasses import replace
import inspect
from pathlib import Path

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_ambiguity import EditorialFormatAmbiguity
from src.formatting.editorial_format_completeness import EditorialFormatCompleteness
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.resolution import (
    EditorialFormatV2TrustSignal,
    EditorialResolutionSource,
    EditorialResolutionStatus,
    EditorialResolutionWarning as W,
    EditorialResolverProviderStatus as ProviderStatus,
    LimitedEditorialResolver,
    LimitedEditorialResolverInput,
)
from src.topic.topic import Topic
from src.topic.topic_confidence import TopicConfidence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _response(
    topic="HEALTH", editorial_format="EXPLAINER", fingerprint="fingerprint-1",
    ambiguity=False, topic_confidence=AdjudicationConfidence.MEDIUM,
    format_confidence=AdjudicationConfidence.HIGH,
) -> SemanticAdjudicationResponse:
    return SemanticAdjudicationResponse(
        adjudicated_topic=topic,
        adjudicated_format=editorial_format,
        topic_confidence=topic_confidence,
        format_confidence=format_confidence,
        topic_reason="validated",
        format_reason="validated",
        topic_evidence_refs=("TITLE",),
        format_evidence_refs=("LEAD",),
        ambiguity_remaining=ambiguity,
        warnings=(),
        provider="fake",
        model="fake-model",
        request_schema_version="1.0",
        response_schema_version="1.1",
        input_fingerprint=fingerprint,
        usage=SemanticAdjudicationUsage(10, 5, 2),
    )


def _inputs(**changes) -> LimitedEditorialResolverInput:
    values = dict(
        deterministic_topic=Topic.SCIENCE,
        deterministic_topic_confidence=TopicConfidence.HIGH,
        deterministic_topic_ambiguity=False,
        deterministic_format=EditorialFormat.STANDARD_NEWS,
        deterministic_format_confidence=EditorialFormatConfidence.MEDIUM,
        deterministic_format_ambiguity=False,
        deterministic_reader_intent=ReaderIntent.GET_UPDATE,
        deterministic_reader_intent_confidence=ReaderIntentConfidence.HIGH,
        scope=AdjudicationScope.NOT_REQUIRED,
        provider_status=ProviderStatus.NOT_CALLED,
        validated_adjudication_response=None,
        legal_topic_candidates=(Topic.SCIENCE, Topic.HEALTH),
        legal_format_candidates=(EditorialFormat.STANDARD_NEWS, EditorialFormat.EXPLAINER),
        expected_input_fingerprint="fingerprint-1",
        format_v2_trust_signal=None,
    )
    values.update(changes)
    return LimitedEditorialResolverInput(**values)


def _resolve(**changes):
    return LimitedEditorialResolver().resolve(_inputs(**changes))


def test_no_adjudication_accepts_all_deterministic_values() -> None:
    result = _resolve()
    assert result.deterministic_topic is Topic.SCIENCE
    assert result.topic_resolution.value is Topic.SCIENCE
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert result.reader_intent_resolution.value is ReaderIntent.GET_UPDATE
    assert result.topic_resolution.status is EditorialResolutionStatus.DETERMINISTIC_ACCEPTED
    assert result.format_resolution.status is EditorialResolutionStatus.DETERMINISTIC_ACCEPTED
    assert result.provider_used is False
    assert result.warnings == ()


def test_topic_only_valid_adjudication_overrides_topic() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(),
    )
    assert result.deterministic_topic is Topic.SCIENCE
    assert result.topic_resolution.value is Topic.HEALTH
    assert result.topic_resolution.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert result.topic_resolution.source is EditorialResolutionSource.ADJUDICATION
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert result.provider_used is True


def test_format_only_valid_adjudication_overrides_format() -> None:
    result = _resolve(
        scope=AdjudicationScope.FORMAT_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(),
    )
    assert result.deterministic_topic is Topic.SCIENCE
    assert result.topic_resolution.value is Topic.SCIENCE
    assert result.format_resolution.value is EditorialFormat.EXPLAINER
    assert result.format_resolution.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert result.provider_used is True


def test_topic_and_format_valid_adjudication_accepts_both() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(),
    )
    assert result.topic_resolution.value is Topic.HEALTH
    assert result.format_resolution.value is EditorialFormat.EXPLAINER
    assert result.provider_used is True


@pytest.mark.parametrize(
    ("status", "warning"),
    [
        (ProviderStatus.UNAVAILABLE, W.PROVIDER_UNAVAILABLE),
        (ProviderStatus.CONFIGURATION_ERROR, W.PROVIDER_CONFIGURATION_ERROR),
        (ProviderStatus.AUTHENTICATION_ERROR, W.PROVIDER_AUTHENTICATION_ERROR),
        (ProviderStatus.PERMISSION_ERROR, W.PROVIDER_PERMISSION_ERROR),
        (ProviderStatus.RATE_LIMITED, W.PROVIDER_RATE_LIMITED),
        (ProviderStatus.TIMEOUT, W.PROVIDER_TIMEOUT),
        (ProviderStatus.INVALID_RESPONSE, W.INVALID_ADJUDICATION_RESPONSE),
        (ProviderStatus.INCOMPLETE_RESPONSE, W.INCOMPLETE_ADJUDICATION_RESPONSE),
    ],
)
def test_topic_provider_failures_preserve_deterministic_fallback(status, warning) -> None:
    result = _resolve(scope=AdjudicationScope.TOPIC_REQUIRED, provider_status=status)
    assert result.deterministic_topic is Topic.SCIENCE
    assert result.topic_resolution.value is Topic.SCIENCE
    assert result.topic_resolution.status is EditorialResolutionStatus.FALLBACK_ACCEPTED
    assert result.topic_resolution.source is EditorialResolutionSource.FALLBACK
    assert warning in result.topic_resolution.warnings
    assert result.review_required is True
    assert result.provider_used is False


@pytest.mark.parametrize(
    ("status", "warning"),
    [
        (ProviderStatus.UNAVAILABLE, W.PROVIDER_UNAVAILABLE),
        (ProviderStatus.CONFIGURATION_ERROR, W.PROVIDER_CONFIGURATION_ERROR),
        (ProviderStatus.AUTHENTICATION_ERROR, W.PROVIDER_AUTHENTICATION_ERROR),
        (ProviderStatus.PERMISSION_ERROR, W.PROVIDER_PERMISSION_ERROR),
        (ProviderStatus.RATE_LIMITED, W.PROVIDER_RATE_LIMITED),
        (ProviderStatus.TIMEOUT, W.PROVIDER_TIMEOUT),
        (ProviderStatus.INVALID_RESPONSE, W.INVALID_ADJUDICATION_RESPONSE),
        (ProviderStatus.INCOMPLETE_RESPONSE, W.INCOMPLETE_ADJUDICATION_RESPONSE),
    ],
)
def test_format_provider_failures_preserve_v1_with_two_warnings(status, warning) -> None:
    result = _resolve(scope=AdjudicationScope.FORMAT_REQUIRED, provider_status=status)
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert result.format_resolution.status is EditorialResolutionStatus.FALLBACK_ACCEPTED
    assert warning in result.format_resolution.warnings
    assert W.FORMAT_FALLBACK_USED in result.format_resolution.warnings
    assert result.provider_used is False


def test_both_dimensions_fallback_on_provider_failure() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider_status=ProviderStatus.UNAVAILABLE,
    )
    assert result.topic_resolution.status is EditorialResolutionStatus.FALLBACK_ACCEPTED
    assert result.format_resolution.status is EditorialResolutionStatus.FALLBACK_ACCEPTED
    assert result.warnings == (W.FORMAT_FALLBACK_USED, W.PROVIDER_UNAVAILABLE)


def test_success_without_validated_response_is_invalid_fallback() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
    )
    assert W.INVALID_ADJUDICATION_RESPONSE in result.warnings
    assert result.provider_used is False


def test_globally_legal_but_request_illegal_topic_is_rejected() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(topic="HEALTH"),
        legal_topic_candidates=(Topic.SCIENCE,),
    )
    assert result.topic_resolution.value is Topic.SCIENCE
    assert W.ILLEGAL_ADJUDICATED_CANDIDATE in result.warnings
    assert result.provider_used is False


def test_globally_legal_but_request_illegal_format_is_rejected() -> None:
    result = _resolve(
        scope=AdjudicationScope.FORMAT_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(editorial_format="EXPLAINER"),
        legal_format_candidates=(EditorialFormat.STANDARD_NEWS,),
    )
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert W.ILLEGAL_ADJUDICATED_CANDIDATE in result.warnings
    assert W.FORMAT_FALLBACK_USED in result.warnings


@pytest.mark.parametrize(
    ("scope", "field", "value"),
    [
        (AdjudicationScope.TOPIC_REQUIRED, "adjudicated_topic", "NOT_A_TOPIC"),
        (AdjudicationScope.FORMAT_REQUIRED, "adjudicated_format", "NOT_A_FORMAT"),
    ],
)
def test_non_enum_adjudicated_candidate_is_rejected(scope, field, value) -> None:
    response = replace(_response(), **{field: value})
    result = _resolve(scope=scope, provider_status=ProviderStatus.SUCCESS, validated_adjudication_response=response)
    assert W.ILLEGAL_ADJUDICATED_CANDIDATE in result.warnings
    assert result.provider_used is False


@pytest.mark.parametrize(
    ("scope", "field"),
    [
        (AdjudicationScope.TOPIC_REQUIRED, "adjudicated_topic"),
        (AdjudicationScope.FORMAT_REQUIRED, "adjudicated_format"),
    ],
)
def test_missing_requested_dimension_falls_back(scope, field) -> None:
    response = replace(_response(), **{field: ""})
    result = _resolve(scope=scope, provider_status=ProviderStatus.SUCCESS, validated_adjudication_response=response)
    assert W.INVALID_ADJUDICATION_RESPONSE in result.warnings
    assert result.review_required is True


@pytest.mark.parametrize(
    "scope", (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED),
)
def test_fingerprint_mismatch_rejects_requested_authority(scope) -> None:
    result = _resolve(
        scope=scope,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(fingerprint="wrong"),
    )
    assert W.FINGERPRINT_MISMATCH in result.warnings
    assert result.input_fingerprint == "fingerprint-1"
    assert result.provider_used is False


def test_matching_fingerprint_accepts_authority() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(fingerprint="fingerprint-1"),
    )
    assert result.topic_resolution.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert result.input_fingerprint == "fingerprint-1"


def test_absent_expected_fingerprint_does_not_fabricate_a_match() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(fingerprint="provider-value"),
        expected_input_fingerprint=None,
    )
    assert result.topic_resolution.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert result.input_fingerprint is None


@pytest.mark.parametrize("scope", (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.FORMAT_REQUIRED))
def test_accepted_ambiguity_preserves_value_and_requires_review(scope) -> None:
    result = _resolve(
        scope=scope,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(ambiguity=True),
    )
    selected = result.topic_resolution if scope is AdjudicationScope.TOPIC_REQUIRED else result.format_resolution
    assert selected.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert selected.ambiguity is True
    assert selected.review_required is True
    assert W.ADJUDICATION_AMBIGUITY_REMAINS in selected.warnings
    assert result.provider_used is True


def test_provider_confidence_is_preserved_only_for_accepted_topic() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(topic_confidence=AdjudicationConfidence.LOW),
    )
    assert result.topic_resolution.confidence == "LOW"
    assert result.topic_resolution.confidence_source is EditorialResolutionSource.ADJUDICATION


def test_fallback_preserves_deterministic_confidence_provenance() -> None:
    result = _resolve(scope=AdjudicationScope.TOPIC_REQUIRED, provider_status=ProviderStatus.TIMEOUT)
    assert result.topic_resolution.confidence == "HIGH"
    assert result.topic_resolution.confidence_source is EditorialResolutionSource.DETERMINISTIC_V1


def test_unrequested_response_dimension_never_gets_authority() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(editorial_format="EXPLAINER"),
    )
    assert result.topic_resolution.value is Topic.HEALTH
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert result.format_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1


def test_format_v2_disagreement_warns_but_cannot_override_v1() -> None:
    signal = EditorialFormatV2TrustSignal(
        EditorialFormat.ANALYSIS,
        EditorialFormatConfidence.HIGH,
        EditorialFormatAmbiguity.CLEAR,
        EditorialFormatCompleteness.COMPLETE,
    )
    result = _resolve(format_v2_trust_signal=signal)
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert result.format_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1
    assert W.FORMAT_V1_V2_DISAGREEMENT in result.warnings
    assert result.review_required is True


@pytest.mark.parametrize(
    ("ambiguity", "completeness", "competition", "contradiction"),
    [
        (EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE, EditorialFormatCompleteness.COMPLETE, False, False),
        (EditorialFormatAmbiguity.CLEAR, EditorialFormatCompleteness.INCOMPLETE, False, False),
        (EditorialFormatAmbiguity.CLEAR, EditorialFormatCompleteness.PARTIAL, False, False),
        (EditorialFormatAmbiguity.CLEAR, EditorialFormatCompleteness.COMPLETE, True, False),
        (EditorialFormatAmbiguity.CONTRADICTORY, EditorialFormatCompleteness.COMPLETE, False, True),
    ],
)
def test_format_v2_uncertainty_is_review_only(ambiguity, completeness, competition, contradiction) -> None:
    signal = EditorialFormatV2TrustSignal(
        EditorialFormat.STANDARD_NEWS,
        EditorialFormatConfidence.LOW,
        ambiguity,
        completeness,
        competition,
        contradiction,
    )
    result = _resolve(format_v2_trust_signal=signal)
    assert result.format_resolution.value is EditorialFormat.STANDARD_NEWS
    assert W.FORMAT_STRUCTURE_INCOMPLETE in result.warnings
    assert result.review_required is True


def test_clear_complete_agreeing_v2_signal_does_not_require_review() -> None:
    signal = EditorialFormatV2TrustSignal(
        EditorialFormat.STANDARD_NEWS,
        EditorialFormatConfidence.HIGH,
        EditorialFormatAmbiguity.CLEAR,
        EditorialFormatCompleteness.COMPLETE,
    )
    result = _resolve(format_v2_trust_signal=signal)
    assert result.review_required is False
    assert result.warnings == ()


@pytest.mark.parametrize("scope", tuple(AdjudicationScope))
def test_reader_intent_is_always_deterministic_for_every_scope(scope) -> None:
    provider_status = ProviderStatus.NOT_CALLED if scope is AdjudicationScope.NOT_REQUIRED else ProviderStatus.SUCCESS
    response = None if scope is AdjudicationScope.NOT_REQUIRED else _response()
    result = _resolve(scope=scope, provider_status=provider_status, validated_adjudication_response=response)
    assert result.reader_intent_resolution.value is ReaderIntent.GET_UPDATE
    assert result.reader_intent_resolution.status is EditorialResolutionStatus.DETERMINISTIC_ACCEPTED
    assert result.reader_intent_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1


@pytest.mark.parametrize(
    ("scope", "topic_adjudicated", "format_adjudicated"),
    [
        (AdjudicationScope.NOT_REQUIRED, False, False),
        (AdjudicationScope.TOPIC_REQUIRED, True, False),
        (AdjudicationScope.FORMAT_REQUIRED, False, True),
        (AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED, True, True),
    ],
)
def test_scope_modes_apply_authority_independently(scope, topic_adjudicated, format_adjudicated) -> None:
    status = ProviderStatus.NOT_CALLED if scope is AdjudicationScope.NOT_REQUIRED else ProviderStatus.SUCCESS
    response = None if scope is AdjudicationScope.NOT_REQUIRED else _response()
    result = _resolve(scope=scope, provider_status=status, validated_adjudication_response=response)
    assert (result.topic_resolution.source is EditorialResolutionSource.ADJUDICATION) is topic_adjudicated
    assert (result.format_resolution.source is EditorialResolutionSource.ADJUDICATION) is format_adjudicated


def test_one_of_two_dimensions_accepted_still_marks_provider_used() -> None:
    response = _response(topic="HEALTH", editorial_format="ANALYSIS")
    result = _resolve(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=response,
    )
    assert result.topic_resolution.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
    assert result.format_resolution.status is EditorialResolutionStatus.FALLBACK_ACCEPTED
    assert result.provider_used is True


def test_top_level_review_is_union_of_dimension_review_flags() -> None:
    result = _resolve(scope=AdjudicationScope.FORMAT_REQUIRED, provider_status=ProviderStatus.TIMEOUT)
    assert result.topic_resolution.review_required is False
    assert result.format_resolution.review_required is True
    assert result.review_required is True


def test_warning_union_is_deduplicated_in_enum_order() -> None:
    result = _resolve(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider_status=ProviderStatus.TIMEOUT,
    )
    assert result.warnings == (W.FORMAT_FALLBACK_USED, W.PROVIDER_TIMEOUT)
    assert len(result.warnings) == len(set(result.warnings))


def test_resolution_is_idempotent() -> None:
    inputs = _inputs(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(ambiguity=True),
    )
    resolver = LimitedEditorialResolver()
    assert resolver.resolve(inputs) == resolver.resolve(inputs)


def test_resolver_does_not_mutate_any_input() -> None:
    inputs = _inputs(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider_status=ProviderStatus.SUCCESS,
        validated_adjudication_response=_response(),
    )
    snapshot = replace(inputs)
    response_snapshot = replace(inputs.validated_adjudication_response)
    LimitedEditorialResolver().resolve(inputs)
    assert inputs == snapshot
    assert inputs.validated_adjudication_response == response_snapshot


def test_resolver_has_no_network_provider_gate_raw_response_or_benchmark_dependency() -> None:
    source = inspect.getsource(__import__(
        "src.resolution.limited_editorial_resolver", fromlist=["LimitedEditorialResolver"]
    ))
    forbidden = (
        "import openai", "from openai", "DeterministicSemanticAdjudicationGate",
        ".adjudicate(", "responses.create", "raw_response", "benchmark/", "source_body",
    )
    assert not any(term.casefold() in source.casefold() for term in forbidden)


def test_resolver_input_contains_no_article_or_provider_secret_fields() -> None:
    parameters = inspect.signature(LimitedEditorialResolverInput).parameters
    forbidden = {"title", "lead", "body", "source", "api_key", "provider_config", "raw_response"}
    assert forbidden.isdisjoint(parameters)


def test_invalid_input_type_is_rejected_without_side_effects() -> None:
    with pytest.raises(ValueError, match="LimitedEditorialResolverInput"):
        LimitedEditorialResolver().resolve(object())
