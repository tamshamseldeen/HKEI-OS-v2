"""Offline integration parity tests for limited Topic authority modes."""

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_decision import SemanticAdjudicationDecision
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage
from src.resolution import (
    EditorialResolutionSource,
    LimitedEditorialResolver,
    LimitedTopicAuthorityApplicator,
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityBlockReason,
)
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)
from src.workflows.limited_editorial_resolver_shadow_workflow import (
    LimitedEditorialResolverShadowWorkflow,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLE = {
    "title": "إعلان علمي جديد",
    "body": "أعلنت المؤسسة نتيجة دراسة جديدة. وأوضحت أن العمل يشرح آلية القياس وخطواته.",
    "source_name": "صحيفة تجريبية",
    "language": "ar",
}


class CountingTopicGate:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, **_kwargs):
        self.calls += 1
        return SemanticAdjudicationDecision(
            scope=AdjudicationScope.TOPIC_REQUIRED,
            trigger_signals=("PARITY_FIXTURE",),
            topic_required=True,
            format_required=False,
            reason_codes=("PARITY_FIXTURE",),
            warnings=(),
        )


class CountingResolver(LimitedEditorialResolver):
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, inputs):
        self.calls += 1
        return super().resolve(inputs)


class ParityFakeProvider(SemanticAdjudicationProvider):
    def __init__(
        self,
        *,
        same_label: bool = False,
        confidence: AdjudicationConfidence = AdjudicationConfidence.HIGH,
        ambiguity: bool = False,
    ) -> None:
        self.calls = 0
        self.same_label = same_label
        self.confidence = confidence
        self.ambiguity = ambiguity

    @property
    def provider_name(self):
        return "parity-fake"

    @property
    def model_name(self):
        return "offline-fixture"

    def adjudicate(self, request):
        self.calls += 1
        if self.same_label:
            topic = request.deterministic_topic
        else:
            topic = next(
                candidate for candidate in request.candidate_topics
                if candidate != request.deterministic_topic
            )
        return SemanticAdjudicationResponse(
            adjudicated_topic=topic,
            adjudicated_format=request.deterministic_format,
            topic_confidence=self.confidence,
            format_confidence=AdjudicationConfidence.MEDIUM,
            topic_reason="دليل تجريبي محدود",
            format_reason="المعالجة الحتمية محفوظة",
            topic_evidence_refs=("TITLE",),
            format_evidence_refs=("LEAD",),
            ambiguity_remaining=self.ambiguity,
            warnings=(),
            provider="parity-fake",
            model="offline-fixture",
            request_schema_version="1.0",
            response_schema_version="1.1",
            input_fingerprint=request.input_fingerprint,
            usage=SemanticAdjudicationUsage(10, 5, 0),
        )


def _workflow_result(
    *,
    same_label=False,
    confidence=AdjudicationConfidence.HIGH,
    ambiguity=False,
):
    provider = ParityFakeProvider(
        same_label=same_label, confidence=confidence, ambiguity=ambiguity,
    )
    gate = CountingTopicGate()
    resolver = CountingResolver()
    adjudication = ExperimentalSemanticAdjudicationShadowWorkflow(
        provider=provider,
        adjudication_gate=gate,
    )
    workflow = LimitedEditorialResolverShadowWorkflow(
        provider=provider,
        adjudication_workflow=adjudication,
        resolver=resolver,
    )
    return workflow.analyze(**ARTICLE), provider, gate, resolver


def _config(mode):
    return LimitedTopicAuthorityConfig(authority_mode=mode)


def _paired(result, **trust):
    flags = {
        "candidate_compliant": True,
        "fingerprint_valid": True,
        "response_valid": True,
        "provider_available": True,
    }
    flags.update(trust)
    applicator = LimitedTopicAuthorityApplicator()
    shadow = applicator.apply(
        result.resolution_result, _config(ResolverAuthorityMode.SHADOW), **flags,
    )
    limited = applicator.apply(
        result.resolution_result,
        _config(ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        **flags,
    )
    return shadow, limited


@pytest.fixture(scope="module")
def changed_stack():
    return _workflow_result()


@pytest.fixture(scope="module")
def same_stack():
    return _workflow_result(same_label=True)


def test_eligible_changed_topic_has_expected_mode_difference(changed_stack) -> None:
    result, _, _, _ = changed_stack
    shadow, limited = _paired(result)
    assert shadow.authoritative_topic is result.resolution_result.deterministic_topic
    assert shadow.authority_applied is False
    assert limited.authoritative_topic is result.resolution_result.topic_resolution.value
    assert limited.authority_applied is True


def test_eligible_changed_topic_sources_differ_only_at_authority_layer(changed_stack) -> None:
    result, _, _, _ = changed_stack
    shadow, limited = _paired(result)
    assert shadow.authority_source is EditorialResolutionSource.DETERMINISTIC_V1
    assert limited.authority_source is EditorialResolutionSource.ADJUDICATION


def test_eligible_changed_topic_block_reasons_are_mode_specific(changed_stack) -> None:
    result, _, _, _ = changed_stack
    shadow, limited = _paired(result)
    assert shadow.block_reasons == (TopicAuthorityBlockReason.MODE_SHADOW,)
    assert limited.block_reasons == ()


@pytest.mark.parametrize(
    "attribute",
    [
        "deterministic_topic", "topic_resolution", "format_resolution",
        "reader_intent_resolution", "warnings", "input_fingerprint",
    ],
)
def test_resolver_result_fields_are_identical_between_modes(changed_stack, attribute) -> None:
    result, _, _, _ = changed_stack
    before = getattr(result.resolution_result, attribute)
    _paired(result)
    assert getattr(result.resolution_result, attribute) == before


@pytest.mark.parametrize(
    "attribute",
    ["adjudication_decision", "request", "validated_response", "response_valid"],
)
def test_upstream_adjudication_fields_are_identical_between_modes(changed_stack, attribute) -> None:
    result, _, _, _ = changed_stack
    before = getattr(result, attribute)
    _paired(result)
    assert getattr(result, attribute) == before


def test_candidate_universe_is_identical_between_modes(changed_stack) -> None:
    result, _, _, _ = changed_stack
    candidates = (result.request.candidate_topics, result.request.candidate_formats)
    _paired(result)
    assert (result.request.candidate_topics, result.request.candidate_formats) == candidates


def test_same_label_shadow_and_limited_parity(same_stack) -> None:
    result, _, _, _ = same_stack
    shadow, limited = _paired(result)
    deterministic = result.resolution_result.deterministic_topic
    assert shadow.authoritative_topic is deterministic
    assert limited.authoritative_topic is deterministic
    assert shadow.block_reasons == (TopicAuthorityBlockReason.MODE_SHADOW,)
    assert limited.block_reasons == (TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)


def test_same_label_never_counts_as_conceptual_override(same_stack) -> None:
    result, _, _, _ = same_stack
    assert all(not decision.authority_applied for decision in _paired(result))


def test_low_confidence_blocks_both_modes() -> None:
    result, _, _, _ = _workflow_result(confidence=AdjudicationConfidence.LOW)
    shadow, limited = _paired(result)
    assert not shadow.authority_applied and not limited.authority_applied
    assert TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW in limited.block_reasons
    assert shadow.authoritative_topic is limited.authoritative_topic


def test_review_required_blocks_both_modes() -> None:
    result, _, _, _ = _workflow_result(ambiguity=True)
    shadow, limited = _paired(result)
    assert not shadow.authority_applied and not limited.authority_applied
    assert TopicAuthorityBlockReason.REVIEW_REQUIRED in limited.block_reasons


def test_ambiguity_blocks_both_modes() -> None:
    result, _, _, _ = _workflow_result(ambiguity=True)
    shadow, limited = _paired(result)
    assert not shadow.authority_applied and not limited.authority_applied
    assert TopicAuthorityBlockReason.AMBIGUITY_REMAINS in limited.block_reasons


@pytest.mark.parametrize(
    ("trust", "reason"),
    [
        ({"response_valid": False}, TopicAuthorityBlockReason.RESPONSE_INVALID),
        ({"candidate_compliant": False}, TopicAuthorityBlockReason.CANDIDATE_INVALID),
        ({"fingerprint_valid": False}, TopicAuthorityBlockReason.FINGERPRINT_INVALID),
        ({"provider_available": False}, TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE),
    ],
)
def test_trust_failure_parity(changed_stack, trust, reason) -> None:
    result, _, _, _ = changed_stack
    shadow, limited = _paired(result, **trust)
    assert not shadow.authority_applied and not limited.authority_applied
    assert shadow.authoritative_topic is limited.authoritative_topic
    assert reason in shadow.block_reasons and reason in limited.block_reasons


def test_kill_switch_round_trip_is_immediate_and_stable(changed_stack) -> None:
    result, provider, gate, resolver = changed_stack
    calls = (provider.calls, gate.calls, resolver.calls)
    applicator = LimitedTopicAuthorityApplicator()
    flags = (True, True, True, True)
    enabled = applicator.apply(
        result.resolution_result,
        _config(ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        *flags,
    )
    shadow = applicator.apply(
        result.resolution_result, _config(ResolverAuthorityMode.SHADOW), *flags,
    )
    reenabled = applicator.apply(
        result.resolution_result,
        _config(ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        *flags,
    )
    assert enabled == reenabled
    assert shadow.authoritative_topic is result.resolution_result.deterministic_topic
    assert (provider.calls, gate.calls, resolver.calls) == calls


def test_default_config_is_shadow_and_non_authoritative(changed_stack) -> None:
    result, _, _, _ = changed_stack
    decision = LimitedTopicAuthorityApplicator().apply(
        result.resolution_result, LimitedTopicAuthorityConfig(), True, True, True, True,
    )
    assert LimitedTopicAuthorityConfig().authority_mode is ResolverAuthorityMode.SHADOW
    assert decision.authority_applied is False


def test_mode_switch_adds_zero_gate_resolver_or_provider_calls(changed_stack) -> None:
    result, provider, gate, resolver = changed_stack
    before = (provider.calls, gate.calls, resolver.calls)
    _paired(result)
    assert (provider.calls, gate.calls, resolver.calls) == before


def test_full_topic_resolution_parity(changed_stack) -> None:
    result, _, _, _ = changed_stack
    topic = result.resolution_result.topic_resolution
    snapshot = (
        result.resolution_result.deterministic_topic, topic.value, topic.status,
        topic.source, topic.confidence, topic.ambiguity, topic.warnings,
    )
    _paired(result)
    assert snapshot == (
        result.resolution_result.deterministic_topic, topic.value, topic.status,
        topic.source, topic.confidence, topic.ambiguity, topic.warnings,
    )


def test_full_format_parity(changed_stack) -> None:
    result, _, _, _ = changed_stack
    before = result.resolution_result.format_resolution
    _paired(result)
    assert result.resolution_result.format_resolution == before


def test_full_reader_intent_parity(changed_stack) -> None:
    result, _, _, _ = changed_stack
    before = result.resolution_result.reader_intent_resolution
    _paired(result)
    assert result.resolution_result.reader_intent_resolution == before


def test_fingerprint_and_resolver_warning_parity(changed_stack) -> None:
    result, _, _, _ = changed_stack
    before = (result.resolution_result.input_fingerprint, result.resolution_result.warnings)
    _paired(result)
    assert (result.resolution_result.input_fingerprint, result.resolution_result.warnings) == before


def test_authority_block_reasons_never_flow_back_to_resolver_warnings(changed_stack) -> None:
    result, _, _, _ = changed_stack
    warnings = result.resolution_result.warnings
    shadow, _ = _paired(result)
    assert TopicAuthorityBlockReason.MODE_SHADOW in shadow.block_reasons
    assert result.resolution_result.warnings == warnings


def test_decisions_are_deterministic_in_both_modes(changed_stack) -> None:
    result, _, _, _ = changed_stack
    assert _paired(result) == _paired(result)


def test_multiple_applicators_have_no_shared_state(changed_stack, same_stack) -> None:
    changed, _, _, _ = changed_stack
    same, _, _, _ = same_stack
    first = LimitedTopicAuthorityApplicator().apply(
        changed.resolution_result,
        _config(ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        True, True, True, True,
    )
    second = LimitedTopicAuthorityApplicator().apply(
        same.resolution_result,
        _config(ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        True, True, True, True,
    )
    assert first.authority_applied is True
    assert second.block_reasons == (TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)


def test_independent_results_and_configs_do_not_leak() -> None:
    changed, _, _, _ = _workflow_result()
    low, _, _, _ = _workflow_result(confidence=AdjudicationConfidence.LOW)
    changed_decision = _paired(changed)[1]
    low_decision = _paired(low)[1]
    assert changed_decision.authority_applied is True
    assert low_decision.authority_applied is False


def test_authority_decision_contains_no_format_or_reader_intent_authority(changed_stack) -> None:
    result, _, _, _ = changed_stack
    names = {item.name for item in fields(type(_paired(result)[1]))}
    assert "authoritative_format" not in names
    assert "authoritative_reader_intent" not in names


def test_parity_suite_uses_no_openai_or_network() -> None:
    source = (PROJECT_ROOT / "tests" / "test_limited_topic_authority_parity.py").read_text(
        encoding="utf-8"
    )
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"openai", "requests", "httpx"})
