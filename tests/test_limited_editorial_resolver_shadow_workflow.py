"""Fake-provider full-stack tests for the limited Resolver shadow workflow."""

from dataclasses import replace
import inspect

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_decision import SemanticAdjudicationDecision
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
    SemanticAdjudicationProviderTimeoutError,
    SemanticAdjudicationProviderUnavailableError,
)
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage
from src.adjudication.semantic_adjudication_request_builder import SemanticAdjudicationRequestBuilder
from src.formatting.editorial_format import EditorialFormat
from src.resolution import EditorialResolutionSource, EditorialResolutionStatus
from src.resolution.editorial_resolution_warning import EditorialResolutionWarning as W
from src.topic.topic import Topic
from src.workflows.experimental_semantic_adjudication_shadow_workflow import ExperimentalSemanticAdjudicationShadowWorkflow
from src.workflows.limited_editorial_resolver_shadow_workflow import LimitedEditorialResolverShadowWorkflow


ARTICLE = dict(
    title="إعلان علمي جديد",
    body="أعلنت المؤسسة نتيجة دراسة جديدة. وأوضحت أن العمل يشرح آلية القياس وخطواته.",
    source_name="صحيفة تجريبية",
    language="ar",
)


class FixedGate:
    def __init__(self, scope: AdjudicationScope):
        self.scope = scope
        self.calls = 0

    def evaluate(self, **_kwargs):
        self.calls += 1
        return SemanticAdjudicationDecision(
            scope=self.scope,
            trigger_signals=("GENERIC_TEST_TRIGGER",) if self.scope is not AdjudicationScope.NOT_REQUIRED else (),
            topic_required=self.scope in {AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED},
            format_required=self.scope in {AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED},
            reason_codes=("GENERIC_TEST_SCOPE",),
            warnings=(),
        )


class SemanticAdjudicationProviderRateLimitError(SemanticAdjudicationProviderConfigurationError):
    pass


class FakeProvider(SemanticAdjudicationProvider):
    def __init__(self, *, error=None, mutate=None, topic_index=-1, format_index=-1, ambiguity=False):
        self.calls = 0
        self.error = error
        self.mutate = mutate
        self.topic_index = topic_index
        self.format_index = format_index
        self.ambiguity = ambiguity

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake-model"

    def adjudicate(self, request):
        self.calls += 1
        if self.error:
            raise self.error("safe fake failure")
        response = SemanticAdjudicationResponse(
            adjudicated_topic=request.candidate_topics[self.topic_index],
            adjudicated_format=request.candidate_formats[self.format_index],
            topic_confidence=AdjudicationConfidence.HIGH,
            format_confidence=AdjudicationConfidence.MEDIUM,
            topic_reason="دليل من العنوان",
            format_reason="دليل من المعالجة",
            topic_evidence_refs=("TITLE",),
            format_evidence_refs=("LEAD",),
            ambiguity_remaining=self.ambiguity,
            warnings=(),
            provider="fake",
            model="fake-model",
            request_schema_version="1.0",
            response_schema_version="1.1",
            input_fingerprint=request.input_fingerprint,
            usage=SemanticAdjudicationUsage(10, 5, 1),
        )
        return self.mutate(response, request) if self.mutate else response


class NarrowRequestBuilder(SemanticAdjudicationRequestBuilder):
    def __init__(self, *, exclude_topic=None, exclude_format=None):
        self.exclude_topic = exclude_topic
        self.exclude_format = exclude_format

    def build(self, **kwargs):
        request = super().build(**kwargs)
        return replace(
            request,
            candidate_topics=tuple(value for value in request.candidate_topics if value != self.exclude_topic),
            candidate_formats=tuple(value for value in request.candidate_formats if value != self.exclude_format),
        )


def _run(scope, provider=None, request_builder=None):
    provider = provider or FakeProvider()
    gate = FixedGate(scope)
    adjudication = ExperimentalSemanticAdjudicationShadowWorkflow(
        provider=provider,
        adjudication_gate=gate,
        request_builder=request_builder,
    )
    result = LimitedEditorialResolverShadowWorkflow(provider=provider, adjudication_workflow=adjudication).analyze(**ARTICLE)
    return result, provider, gate


def test_not_required_routes_without_provider_or_request() -> None:
    result, provider, gate = _run(AdjudicationScope.NOT_REQUIRED)
    assert provider.calls == 0 and result.provider_called is False and result.request is None
    assert result.resolution_result.topic_resolution.status is EditorialResolutionStatus.DETERMINISTIC_ACCEPTED
    assert result.resolution_result.format_resolution.status is EditorialResolutionStatus.DETERMINISTIC_ACCEPTED
    assert gate.calls == 1


@pytest.mark.parametrize(
    ("scope", "topic", "editorial_format", "calls"),
    [
        (AdjudicationScope.TOPIC_REQUIRED, True, False, 1),
        (AdjudicationScope.FORMAT_REQUIRED, False, True, 1),
        (AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED, True, True, 1),
    ],
)
def test_required_scopes_accept_only_requested_dimensions(scope, topic, editorial_format, calls) -> None:
    result, provider, _ = _run(scope)
    assert provider.calls == calls
    assert (result.resolution_result.topic_resolution.source is EditorialResolutionSource.ADJUDICATION) is topic
    assert (result.resolution_result.format_resolution.source is EditorialResolutionSource.ADJUDICATION) is editorial_format


@pytest.mark.parametrize(
    ("error", "warning"),
    [
        (SemanticAdjudicationProviderConfigurationError, W.PROVIDER_CONFIGURATION_ERROR),
        (SemanticAdjudicationProviderUnavailableError, W.PROVIDER_UNAVAILABLE),
        (SemanticAdjudicationProviderRateLimitError, W.PROVIDER_RATE_LIMITED),
        (SemanticAdjudicationProviderTimeoutError, W.PROVIDER_TIMEOUT),
    ],
)
@pytest.mark.parametrize("scope", (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED))
def test_normalized_provider_failures_fallback_without_crash(scope, error, warning) -> None:
    result, provider, _ = _run(scope, FakeProvider(error=error))
    assert provider.calls == 1 and result.resolution_result.provider_used is False
    assert result.resolution_result.review_required is True
    assert warning in result.resolution_result.warnings


@pytest.mark.parametrize("scope", (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED))
def test_structurally_invalid_response_is_rejected_by_validator(scope) -> None:
    def invalid(response, _request):
        return replace(response, provider="")
    result, provider, _ = _run(scope, FakeProvider(mutate=invalid))
    assert provider.calls == 1 and result.response_valid is False
    assert result.validated_response is None
    assert W.INVALID_ADJUDICATION_RESPONSE in result.resolution_result.warnings
    assert result.resolution_result.provider_used is False


@pytest.mark.parametrize(
    ("scope", "field", "global_value"),
    [
        (AdjudicationScope.TOPIC_REQUIRED, "adjudicated_topic", Topic.CRIME.value),
        (AdjudicationScope.FORMAT_REQUIRED, "adjudicated_format", EditorialFormat.INTERVIEW.value),
    ],
)
def test_request_illegal_global_candidate_is_rejected(scope, field, global_value) -> None:
    def illegal(response, _request):
        return replace(response, **{field: global_value})
    builder = NarrowRequestBuilder(
        exclude_topic=global_value if field == "adjudicated_topic" else None,
        exclude_format=global_value if field == "adjudicated_format" else None,
    )
    result, _, _ = _run(scope, FakeProvider(mutate=illegal), builder)
    assert result.validated_response is None
    assert W.INVALID_ADJUDICATION_RESPONSE in result.resolution_result.warnings
    assert result.resolution_result.provider_used is False


@pytest.mark.parametrize("scope", (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED))
def test_fingerprint_mismatch_is_rejected(scope) -> None:
    def mismatch(response, _request):
        return replace(response, input_fingerprint="wrong-fingerprint")
    result, _, _ = _run(scope, FakeProvider(mutate=mismatch))
    assert result.response_valid is False
    assert result.resolution_result.review_required is True
    assert result.resolution_result.input_fingerprint == result.request.input_fingerprint
    assert W.INVALID_ADJUDICATION_RESPONSE in result.resolution_result.warnings


@pytest.mark.parametrize("scope", (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED))
def test_ambiguity_is_accepted_and_preserved(scope) -> None:
    result, _, _ = _run(scope, FakeProvider(ambiguity=True))
    assert result.response_valid is True and result.resolution_result.provider_used is True
    assert result.resolution_result.review_required is True
    assert W.ADJUDICATION_AMBIGUITY_REMAINS in result.resolution_result.warnings


@pytest.mark.parametrize(
    ("scope", "field"),
    [
        (AdjudicationScope.TOPIC_REQUIRED, "adjudicated_topic"),
        (AdjudicationScope.FORMAT_REQUIRED, "adjudicated_format"),
    ],
)
def test_missing_requested_dimension_is_invalid_and_falls_back(scope, field) -> None:
    def missing(response, _request):
        return replace(response, **{field: ""})
    result, _, _ = _run(scope, FakeProvider(mutate=missing))
    assert result.validated_response is None
    assert result.resolution_result.review_required is True
    assert result.resolution_result.provider_used is False


def test_unexpected_format_in_topic_only_response_never_gains_authority() -> None:
    result, _, _ = _run(AdjudicationScope.TOPIC_REQUIRED)
    deterministic = result.editorial_result.format_classification.editorial_format
    assert result.resolution_result.format_resolution.value is deterministic
    assert result.resolution_result.format_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1


def test_unexpected_topic_in_format_only_response_never_gains_authority() -> None:
    result, _, _ = _run(AdjudicationScope.FORMAT_REQUIRED)
    deterministic = result.editorial_result.topic_classification.topic
    assert result.resolution_result.topic_resolution.value is deterministic
    assert result.resolution_result.topic_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1


def test_format_v2_disagreement_may_warn_but_never_overrides_v1_when_not_requested() -> None:
    result, _, _ = _run(AdjudicationScope.NOT_REQUIRED)
    deterministic = result.editorial_result.format_classification.editorial_format
    assert result.resolution_result.format_resolution.value is deterministic
    assert result.resolution_result.format_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1
    if result.format_v2_result.selected_format is not deterministic:
        assert W.FORMAT_V1_V2_DISAGREEMENT in result.resolution_result.warnings


@pytest.mark.parametrize("scope", tuple(AdjudicationScope))
def test_reader_intent_and_all_inputs_remain_unmutated(scope) -> None:
    result, _, _ = _run(scope)
    deterministic = result.editorial_result.reader_intent_classification.reader_intent
    assert result.resolution_result.reader_intent_resolution.value is deterministic
    assert result.resolution_result.reader_intent_resolution.source is EditorialResolutionSource.DETERMINISTIC_V1
    assert not result.topic_mutated and not result.format_mutated
    assert not result.reader_intent_mutated and not result.gate_mutated and not result.format_v2_mutated


def test_request_candidates_and_fingerprint_flow_unchanged_to_resolution() -> None:
    result, _, _ = _run(AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED)
    assert result.validated_response.input_fingerprint == result.request.input_fingerprint
    assert result.resolution_result.input_fingerprint == result.request.input_fingerprint
    assert result.validated_response.adjudicated_topic in result.request.candidate_topics
    assert result.validated_response.adjudicated_format in result.request.candidate_formats


def test_shadow_result_does_not_expose_raw_provider_response_or_source_body_field() -> None:
    parameters = inspect.signature(type(_run(AdjudicationScope.NOT_REQUIRED)[0])).parameters
    assert "provider_response" not in parameters and "source_body" not in parameters


def test_workflow_depends_on_provider_interface_and_has_no_openai_or_network_dependency() -> None:
    source = inspect.getsource(__import__(
        "src.workflows.limited_editorial_resolver_shadow_workflow",
        fromlist=["LimitedEditorialResolverShadowWorkflow"],
    ))
    assert "SemanticAdjudicationProvider" in source
    assert "OpenAI" not in source and "responses.create" not in source


def test_exactly_one_fake_call_per_required_execution_without_retry() -> None:
    for scope in (
        AdjudicationScope.TOPIC_REQUIRED,
        AdjudicationScope.FORMAT_REQUIRED,
        AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
    ):
        result, provider, _ = _run(scope)
        assert provider.calls == 1 and result.provider_called is True
