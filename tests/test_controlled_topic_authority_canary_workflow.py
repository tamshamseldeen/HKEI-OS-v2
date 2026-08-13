"""Offline integration tests for controlled Topic authority runtime wiring."""

from dataclasses import FrozenInstanceError, fields, replace
import ast
from pathlib import Path

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_decision import SemanticAdjudicationDecision
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderUnavailableError,
)
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage
from src.resolution import (
    EditorialResolutionSource,
    LimitedTopicAuthorityApplicator,
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityBlockReason,
    TopicAuthorityContractViolation,
    TopicAuthorityDecision,
    TopicAuthorityMetrics,
    TopicAuthorityProviderFailureCategory,
    TopicAuthoritySafetyMetrics,
)
from src.topic.topic import Topic
from src.workflows.controlled_topic_authority_canary_result import (
    ControlledTopicAuthorityCanaryResult,
)
from src.workflows.controlled_topic_authority_canary_workflow import (
    ControlledTopicAuthorityCanaryWorkflow,
)
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)
from src.workflows.limited_editorial_resolver_shadow_workflow import (
    LimitedEditorialResolverShadowWorkflow,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLE = dict(
    title="إعلان علمي جديد",
    body="أعلنت المؤسسة نتيجة دراسة جديدة. وأوضحت أن العمل يشرح آلية القياس وخطواته.",
    source_name="صحيفة تجريبية",
    language="ar",
)


class FixedGate:
    def __init__(self, scope=AdjudicationScope.TOPIC_REQUIRED):
        self.scope = scope
        self.calls = 0

    def evaluate(self, **_kwargs):
        self.calls += 1
        return SemanticAdjudicationDecision(
            scope=self.scope,
            trigger_signals=("CANARY_FIXTURE",) if self.scope is not AdjudicationScope.NOT_REQUIRED else (),
            topic_required=self.scope in (AdjudicationScope.TOPIC_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED),
            format_required=self.scope in (AdjudicationScope.FORMAT_REQUIRED, AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED),
            reason_codes=("CANARY_FIXTURE",),
            warnings=(),
        )


class FakeProvider(SemanticAdjudicationProvider):
    def __init__(self, *, same=False, confidence=AdjudicationConfidence.HIGH, ambiguity=False, error=None):
        self.calls = 0
        self.same = same
        self.confidence = confidence
        self.ambiguity = ambiguity
        self.error = error

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return "offline"

    def adjudicate(self, request):
        self.calls += 1
        if self.error:
            raise self.error("safe fake failure")
        topic = request.deterministic_topic if self.same else next(
            item for item in request.candidate_topics if item != request.deterministic_topic
        )
        return SemanticAdjudicationResponse(
            adjudicated_topic=topic,
            adjudicated_format=request.candidate_formats[-1],
            topic_confidence=self.confidence,
            format_confidence=AdjudicationConfidence.HIGH,
            topic_reason="دليل محدود",
            format_reason="دليل محدود",
            topic_evidence_refs=("TITLE",),
            format_evidence_refs=("LEAD",),
            ambiguity_remaining=self.ambiguity,
            warnings=(),
            provider="fake",
            model="offline",
            request_schema_version="1.0",
            response_schema_version="1.1",
            input_fingerprint=request.input_fingerprint,
            usage=SemanticAdjudicationUsage(10, 5, 0),
        )


def _workflow(*, mode=None, scope=AdjudicationScope.TOPIC_REQUIRED, provider=None, applicator=None):
    provider = provider or FakeProvider()
    gate = FixedGate(scope)
    shadow = LimitedEditorialResolverShadowWorkflow(
        provider=provider,
        adjudication_workflow=ExperimentalSemanticAdjudicationShadowWorkflow(
            provider=provider, adjudication_gate=gate,
        ),
    )
    config = None if mode is None else LimitedTopicAuthorityConfig(authority_mode=mode)
    workflow = ControlledTopicAuthorityCanaryWorkflow(
        provider=provider, config=config, shadow_workflow=shadow, applicator=applicator,
    )
    return workflow, provider, gate


def _run(**kwargs):
    workflow, provider, gate = _workflow(**kwargs)
    return workflow.analyze(**ARTICLE), workflow, provider, gate


def test_default_workflow_is_shadow() -> None:
    result, workflow, _, _ = _run()
    assert workflow.config.authority_mode is ResolverAuthorityMode.SHADOW
    assert result.authority_applied is False
    assert result.authoritative_topic is result.deterministic_topic


def test_explicit_limited_mode_applies_changed_topic() -> None:
    result, _, _, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    assert result.authority_applied is True
    assert result.authoritative_topic is result.resolved_topic
    assert result.authoritative_topic is not result.deterministic_topic


@pytest.mark.parametrize(
    ("scope", "calls", "topic_requested"),
    [
        (AdjudicationScope.NOT_REQUIRED, 0, False),
        (AdjudicationScope.TOPIC_REQUIRED, 1, True),
        (AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED, 1, True),
    ],
)
def test_gate_paths_preserve_expected_fake_provider_calls(scope, calls, topic_requested) -> None:
    result, _, provider, gate = _run(scope=scope)
    assert provider.calls == calls
    assert gate.calls == 1
    assert result.authority_observation.topic_adjudication_requested is topic_requested


def test_not_required_stays_deterministic_in_limited_mode() -> None:
    result, _, _, _ = _run(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        scope=AdjudicationScope.NOT_REQUIRED,
    )
    assert result.authority_applied is False
    assert TopicAuthorityBlockReason.RESOLUTION_NOT_ADJUDICATED in result.authority_decision.block_reasons


@pytest.mark.parametrize("confidence", [AdjudicationConfidence.MEDIUM, AdjudicationConfidence.HIGH])
def test_medium_and_high_confidence_are_eligible(confidence) -> None:
    result, _, _, _ = _run(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        provider=FakeProvider(confidence=confidence),
    )
    assert result.authority_applied is True


def test_low_confidence_is_blocked() -> None:
    result, _, _, _ = _run(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        provider=FakeProvider(confidence=AdjudicationConfidence.LOW),
    )
    assert not result.authority_applied
    assert TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW in result.authority_decision.block_reasons


def test_same_label_is_no_topic_change() -> None:
    result, _, _, _ = _run(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        provider=FakeProvider(same=True),
    )
    assert not result.authority_applied
    assert result.authority_decision.block_reasons == (TopicAuthorityBlockReason.NO_TOPIC_CHANGE,)


def test_ambiguity_and_review_required_are_blocked() -> None:
    result, _, _, _ = _run(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        provider=FakeProvider(ambiguity=True),
    )
    assert not result.authority_applied
    assert TopicAuthorityBlockReason.REVIEW_REQUIRED in result.authority_decision.block_reasons
    assert TopicAuthorityBlockReason.AMBIGUITY_REMAINS in result.authority_decision.block_reasons


@pytest.mark.parametrize(
    ("metadata", "reason"),
    [
        ({"response_valid": False}, TopicAuthorityBlockReason.RESPONSE_INVALID),
        ({"candidate_compliant": False}, TopicAuthorityBlockReason.CANDIDATE_INVALID),
        ({"fingerprint_valid": False}, TopicAuthorityBlockReason.FINGERPRINT_INVALID),
        ({"provider_available": False}, TopicAuthorityBlockReason.PROVIDER_UNAVAILABLE),
    ],
)
def test_explicit_trust_failures_block_authority(metadata, reason) -> None:
    workflow, _, _ = _workflow(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    result = workflow.analyze(**ARTICLE, **metadata)
    assert not result.authority_applied
    assert result.authoritative_topic is result.deterministic_topic
    assert reason in result.authority_decision.block_reasons


def test_provider_failure_uses_existing_resolver_fallback() -> None:
    provider = FakeProvider(error=SemanticAdjudicationProviderUnavailableError)
    workflow, provider, _ = _workflow(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY, provider=provider,
    )
    result = workflow.analyze(
        **ARTICLE,
        provider_available=False,
        provider_failure_category=TopicAuthorityProviderFailureCategory.UNAVAILABLE,
    )
    assert provider.calls == 1
    assert not result.authority_applied
    assert result.authoritative_topic is result.deterministic_topic
    assert result.authority_observation.provider_failure_category is TopicAuthorityProviderFailureCategory.UNAVAILABLE


def test_observation_is_always_generated_in_both_modes() -> None:
    shadow, _, _, _ = _run()
    limited, _, _, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    assert shadow.authority_observation.authority_mode is ResolverAuthorityMode.SHADOW
    assert limited.authority_observation.authority_mode is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY


def test_dual_topic_provenance_is_exposed() -> None:
    result, _, _, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    assert result.deterministic_topic is result.resolution_result.deterministic_topic
    assert result.resolved_topic is result.resolution_result.topic_resolution.value
    assert result.authoritative_topic is result.authority_decision.authoritative_topic


def test_result_model_is_frozen() -> None:
    result, _, _, _ = _run()
    with pytest.raises(FrozenInstanceError):
        result.authority_applied = True


def test_invalid_config_is_rejected_before_runtime() -> None:
    provider = FakeProvider()
    with pytest.raises(ValueError, match="config"):
        ControlledTopicAuthorityCanaryWorkflow(provider=provider, config="LIMITED_TOPIC_AUTHORITY")
    assert provider.calls == 0


def test_kill_switch_round_trip_uses_same_resolution_without_upstream_calls() -> None:
    result, _, provider, gate = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    resolution = result.resolution_result
    calls = (provider.calls, gate.calls)
    limited, _, _ = _workflow(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    shadow, _, _ = _workflow(mode=ResolverAuthorityMode.SHADOW)
    first = limited.apply_to_resolution(
        resolution, candidate_compliant=True, fingerprint_valid=True,
        response_valid=True, provider_available=True,
    )
    middle = shadow.apply_to_resolution(
        resolution, candidate_compliant=True, fingerprint_valid=True,
        response_valid=True, provider_available=True,
    )
    last = limited.apply_to_resolution(
        resolution, candidate_compliant=True, fingerprint_valid=True,
        response_valid=True, provider_available=True,
    )
    assert first == last and first.authority_applied
    assert not middle.authority_applied and middle.authoritative_topic is resolution.deterministic_topic
    assert (provider.calls, gate.calls) == calls


def test_stop_recommendation_is_exposed_without_mode_mutation() -> None:
    workflow, _, _ = _workflow(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    result = workflow.analyze(
        **ARTICLE,
        operational_metrics=TopicAuthorityMetrics(),
        safety_metrics=TopicAuthoritySafetyMetrics(authority_contract_violation_count=1),
    )
    assert result.stop_decision.should_stop is True
    assert result.stop_decision.recommended_mode is ResolverAuthorityMode.SHADOW
    assert workflow.config.authority_mode is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY


class UnsafeApplicator(LimitedTopicAuthorityApplicator):
    def apply(self, resolution, config, *flags):
        normal = super().apply(
            resolution,
            LimitedTopicAuthorityConfig(
                authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
            ),
            True, True, True, True,
        )
        return replace(normal, review_required=True)


def test_contract_violation_is_visible_and_fails_closed() -> None:
    result, _, _, _ = _run(
        mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        applicator=UnsafeApplicator(),
    )
    assert TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_REVIEW_REQUIRED in result.contract_violations
    assert result.authority_applied is False
    assert result.authoritative_topic is result.deterministic_topic
    assert result.authority_source is EditorialResolutionSource.DETERMINISTIC_V1


@pytest.mark.parametrize(
    "attribute",
    [
        "deterministic_topic", "topic_resolution", "format_resolution",
        "reader_intent_resolution", "warnings", "input_fingerprint",
    ],
)
def test_authority_layer_does_not_mutate_resolution(attribute) -> None:
    result, _, _, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    before = getattr(result.resolution_result, attribute)
    assert getattr(result.shadow_workflow_result.resolution_result, attribute) == before


def test_format_has_no_authority_field_and_remains_resolver_output() -> None:
    result, _, _, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    names = {item.name for item in fields(ControlledTopicAuthorityCanaryResult)}
    assert "authoritative_format" not in names
    assert result.resolution_result.format_resolution is result.shadow_workflow_result.resolution_result.format_resolution


def test_reader_intent_has_no_authority_field_and_remains_resolver_output() -> None:
    result, _, _, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    names = {item.name for item in fields(ControlledTopicAuthorityCanaryResult)}
    assert "authoritative_reader_intent" not in names
    assert result.resolution_result.reader_intent_resolution is result.shadow_workflow_result.resolution_result.reader_intent_resolution


def test_provider_request_and_response_match_runtime_result() -> None:
    result, _, provider, _ = _run(mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    assert provider.calls == 1
    assert result.shadow_workflow_result.request.input_fingerprint == result.resolution_result.input_fingerprint
    assert result.shadow_workflow_result.validated_response.input_fingerprint == result.resolution_result.input_fingerprint


def test_mode_is_downstream_and_adds_no_provider_calls() -> None:
    result, _, provider, gate = _run()
    calls = (provider.calls, gate.calls)
    resolution = result.resolution_result
    for mode in (ResolverAuthorityMode.SHADOW, ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY):
        workflow, _, _ = _workflow(mode=mode)
        workflow.apply_to_resolution(
            resolution, candidate_compliant=True, fingerprint_valid=True,
            response_valid=True, provider_available=True,
        )
    assert (provider.calls, gate.calls) == calls


def test_runtime_models_exclude_sensitive_payload_fields() -> None:
    names = {
        item.name
        for model in (ControlledTopicAuthorityCanaryResult,)
        for item in fields(model)
    }
    assert names.isdisjoint({
        "article_body", "raw_prompt", "raw_response", "api_key",
        "authorization_header", "chain_of_thought",
    })


def test_workflow_has_no_openai_import_or_global_metrics() -> None:
    path = PROJECT_ROOT / "src" / "workflows" / "controlled_topic_authority_canary_workflow.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "openai" not in imported
    assert not any(
        isinstance(node, (ast.Assign, ast.AnnAssign)) for node in tree.body
    )


@pytest.mark.parametrize("run_number", range(5))
def test_independent_workflow_instances_do_not_share_state(run_number) -> None:
    result, workflow, provider, gate = _run()
    assert result.authority_applied is False
    assert workflow.config.authority_mode is ResolverAuthorityMode.SHADOW
    assert provider.calls == 1 and gate.calls == 1


def test_real_provider_calls_are_zero_by_construction() -> None:
    result, _, provider, _ = _run()
    assert provider.provider_name == "fake"
    assert result.shadow_workflow_result.provider_called is True


def test_runtime_does_not_wait_for_or_contain_human_audit_truth() -> None:
    signature = fields(ControlledTopicAuthorityCanaryResult)
    names = {item.name for item in signature}
    assert names.isdisjoint({"audit_record", "human_correct", "expected_topic"})
