"""Tests for the experimental semantic adjudication shadow workflow."""

from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.adjudication.semantic_adjudication_provider import (
    SemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderUnavailableError,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_request_builder import (
    SemanticAdjudicationRequestBuilder,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage
from src.adjudication.semantic_adjudication_response_validator import (
    SemanticAdjudicationResponseValidator,
)
from src.workflows.experimental_semantic_adjudication_shadow_result import (
    ExperimentalSemanticAdjudicationShadowResult,
)
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


INPUT = {
    "title": "عنوان تجريبي",
    "body": "هذه مقدمة تجريبية. وهذه جملة ثانية للتحليل.",
    "source_name": "مصدر تجريبي",
    "source_url": "https://example.test/article",
    "language": "ar",
}


class ValidFakeProvider(SemanticAdjudicationProvider):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        self.calls += 1
        return valid_response(request)


class InvalidFakeProvider(ValidFakeProvider):
    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        self.calls += 1
        response = valid_response(request)
        return SemanticAdjudicationResponse(
            **{
                **response.__dict__,
                "input_fingerprint": "invalid-fingerprint",
            }
        )


class ErrorFakeProvider(ValidFakeProvider):
    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        self.calls += 1
        raise SemanticAdjudicationProviderUnavailableError("sensitive detail")


class CountingFakeProvider(ValidFakeProvider):
    pass


class UnexpectedErrorProvider(ValidFakeProvider):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        self.calls += 1
        raise self.error


def valid_response(
    request: SemanticAdjudicationRequest,
) -> SemanticAdjudicationResponse:
    return SemanticAdjudicationResponse(
        adjudicated_topic=request.candidate_topics[0],
        adjudicated_format=request.candidate_formats[0],
        topic_confidence=AdjudicationConfidence.HIGH,
        format_confidence=AdjudicationConfidence.MEDIUM,
        topic_reason="Concise Topic rationale.",
        format_reason="Concise Format rationale.",
        topic_evidence_refs=("TITLE",),
        format_evidence_refs=("BODY_SENTENCE_0",),
        ambiguity_remaining=False,
        warnings=(),
        provider="fake",
        model="fake-model",
        request_schema_version="1.0",
        response_schema_version="1.0",
        input_fingerprint=request.input_fingerprint,
        usage=SemanticAdjudicationUsage(0, 0, None),
    )


def gate_decision(scope: AdjudicationScope) -> SemanticAdjudicationDecision:
    return SemanticAdjudicationDecision(
        scope=scope,
        trigger_signals=(),
        topic_required=scope in (
            AdjudicationScope.TOPIC_REQUIRED,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        ),
        format_required=scope in (
            AdjudicationScope.FORMAT_REQUIRED,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        ),
        reason_codes=("TEST_SCOPE",),
        warnings=(),
    )


def dependencies(
    *,
    scope: AdjudicationScope,
    provider: SemanticAdjudicationProvider,
) -> tuple[
    ExperimentalSemanticAdjudicationShadowWorkflow,
    Mock,
    Mock,
    Mock,
    Mock,
]:
    editorial = Mock(spec=ExperimentalSemanticEditorialAnalysisWorkflow)
    editorial.process.return_value = (
        ExperimentalSemanticEditorialAnalysisWorkflow().process(**INPUT)
    )
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    gate.evaluate.return_value = gate_decision(scope)
    builder = Mock(wraps=SemanticAdjudicationRequestBuilder())
    validator = Mock(wraps=SemanticAdjudicationResponseValidator())
    workflow = ExperimentalSemanticAdjudicationShadowWorkflow(
        provider=provider,
        editorial_workflow=editorial,
        adjudication_gate=gate,
        request_builder=builder,
        response_validator=validator,
    )
    return workflow, editorial, gate, builder, validator


def test_shadow_result_is_frozen_and_has_exact_fields() -> None:
    assert tuple(field.name for field in fields(
        ExperimentalSemanticAdjudicationShadowResult
    )) == (
        "editorial_result",
        "adjudication_decision",
        "request",
        "provider_response",
        "validated_response",
        "provider_called",
        "response_valid",
        "provider_error",
    )
    workflow, *_ = dependencies(
        scope=AdjudicationScope.NOT_REQUIRED,
        provider=CountingFakeProvider(),
    )
    result = workflow.analyze(**INPUT)
    with pytest.raises(FrozenInstanceError):
        result.provider_called = True


def test_not_required_skips_builder_provider_and_validator() -> None:
    provider = CountingFakeProvider()
    workflow, editorial, gate, builder, validator = dependencies(
        scope=AdjudicationScope.NOT_REQUIRED,
        provider=provider,
    )
    result = workflow.analyze(**INPUT)
    assert editorial.process.call_count == gate.evaluate.call_count == 1
    assert builder.build.call_count == provider.calls == validator.validate.call_count == 0
    assert result.request is None
    assert result.provider_response is None
    assert result.validated_response is None
    assert result.provider_called is result.response_valid is False
    assert result.provider_error is None


def test_required_success_uses_every_dependency_once_and_preserves_state() -> None:
    provider = ValidFakeProvider()
    workflow, editorial, gate, builder, validator = dependencies(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        provider=provider,
    )
    result = workflow.analyze(**INPUT)
    assert editorial.process.call_count == gate.evaluate.call_count == 1
    assert builder.build.call_count == provider.calls == validator.validate.call_count == 1
    assert result.request is not None
    assert result.provider_response is not None
    assert result.validated_response is result.provider_response
    assert result.provider_called is result.response_valid is True
    assert result.provider_error is None
    editorial_result = editorial.process.return_value
    assert result.editorial_result is editorial_result
    assert result.editorial_result.topic_classification is editorial_result.topic_classification
    assert result.editorial_result.format_classification is editorial_result.format_classification
    assert result.editorial_result.reader_intent_classification is (
        editorial_result.reader_intent_classification
    )


def test_invalid_response_is_retained_but_not_validated() -> None:
    provider = InvalidFakeProvider()
    workflow, _, _, builder, validator = dependencies(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider=provider,
    )
    result = workflow.analyze(**INPUT)
    assert builder.build.call_count == provider.calls == validator.validate.call_count == 1
    assert result.provider_called is True
    assert result.response_valid is False
    assert result.provider_response is not None
    assert result.validated_response is None
    assert result.provider_error == "input fingerprint mismatch"


def test_provider_error_is_recorded_without_message_or_validation() -> None:
    provider = ErrorFakeProvider()
    workflow, _, _, builder, validator = dependencies(
        scope=AdjudicationScope.FORMAT_REQUIRED,
        provider=provider,
    )
    result = workflow.analyze(**INPUT)
    assert builder.build.call_count == provider.calls == 1
    assert validator.validate.call_count == 0
    assert result.request is not None
    assert result.provider_response is result.validated_response is None
    assert result.provider_called is True
    assert result.response_valid is False
    assert result.provider_error == "SemanticAdjudicationProviderUnavailableError"
    assert "sensitive detail" not in result.provider_error


@pytest.mark.parametrize("error", (ValueError("bug"), TypeError("bug"), RuntimeError("bug")))
def test_unexpected_provider_errors_propagate(error: Exception) -> None:
    provider = UnexpectedErrorProvider(error)
    workflow, *_ = dependencies(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider=provider,
    )
    with pytest.raises(type(error), match="bug"):
        workflow.analyze(**INPUT)
    assert provider.calls == 1


def test_request_id_is_deterministic_and_not_benchmark_aware() -> None:
    first_provider = ValidFakeProvider()
    first, *_ = dependencies(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider=first_provider,
    )
    second, *_ = dependencies(
        scope=AdjudicationScope.TOPIC_REQUIRED,
        provider=ValidFakeProvider(),
    )
    first_result = first.analyze(**INPUT)
    second_result = second.analyze(**INPUT)
    assert first_result.request.request_id == second_result.request.request_id
    assert first_result.request.request_id.startswith("semantic-adjudication-")
    assert len(first_result.request.request_id) == len("semantic-adjudication-") + 64


def test_workflow_has_no_resolver_retry_cache_vendor_or_risk_integration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.workflows.experimental_semantic_adjudication_shadow_workflow as module

    source = inspect.getsource(module).casefold()
    imports = "\n".join(
        line for line in source.splitlines()
        if line.startswith(("from ", "import "))
    )
    forbidden_imports = (
        "openai",
        "anthropic",
        "gemini",
        "resolver",
        "reader_intent",
        "risk",
        "benchmark",
    )
    assert not any(value in imports for value in forbidden_imports)
    assert not any(value in source for value in ("uuid", "retry", "cache"))
    result_fields = {
        field.name for field in fields(ExperimentalSemanticAdjudicationShadowResult)
    }
    assert not any(name.startswith("resolved_") for name in result_fields)
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *args, **kwargs: pytest.fail("network access attempted"),
    )
    workflow, *_ = dependencies(
        scope=AdjudicationScope.NOT_REQUIRED,
        provider=CountingFakeProvider(),
    )
    assert workflow.analyze(**INPUT).provider_called is False
