"""Offline safety tests for the single-request OpenAI live canary runner."""

import inspect
import json
import os
from pathlib import Path
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from openai import (
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)
import pytest

import examples.run_openai_semantic_adjudication_live_canary as canary
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.adjudication.semantic_adjudication_provider_config_validator import (
    SemanticAdjudicationProviderConfigValidator,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
)
from src.adjudication.semantic_adjudication_reasoning_effort import (
    SemanticAdjudicationReasoningEffort,
)
from src.adjudication.semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


class FakeSecretResolver(SemanticAdjudicationSecretResolver):
    def __init__(self, secret: object = "test-secret") -> None:
        self.secret = secret
        self.calls: list[str] = []

    def resolve(self, secret_name: str) -> str:
        self.calls.append(secret_name)
        if isinstance(self.secret, Exception):
            raise self.secret
        return self.secret


class FakeResponses:
    def __init__(self, mode: str = "valid") -> None:
        self.mode = mode
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        status_errors = {
            "authentication": (AuthenticationError, 401, None),
            "permission": (PermissionDeniedError, 403, None),
            "bad_request": (
                BadRequestError,
                400,
                {"code": "unsupported_value", "param": "temperature"},
            ),
            "rate_limit": (RateLimitError, 429, None),
        }
        if self.mode in status_errors:
            error_type, status_code, body = status_errors[self.mode]
            raise error_type(
                "raw sk-test-secret message with Bounded source body.",
                response=httpx.Response(
                    status_code,
                    request=httpx.Request("POST", "https://example.invalid"),
                ),
                body=body,
            )
        if self.mode == "timeout":
            raise APITimeoutError(
                request=httpx.Request("POST", "https://example.invalid")
            )
        if self.mode == "malformed":
            return SimpleNamespace(
                status="completed",
                output=(),
                output_text="{bad-json",
                model="fake-live-model",
                usage=None,
            )
        schema = kwargs["text"]["format"]["schema"]
        topics = schema["properties"]["adjudicated_topic"]["enum"]
        formats = schema["properties"]["adjudicated_format"]["enum"]
        payload = {
            "adjudicated_topic": topics[-1],
            "adjudicated_format": formats[-1],
            "topic_confidence": "HIGH",
            "format_confidence": "MEDIUM",
            "topic_reason": "live canary contract topic selection",
            "format_reason": "live canary contract format selection",
            "topic_evidence_refs": ["HEADLINE"],
            "format_evidence_refs": ["LEAD"],
            "ambiguity_remaining": False,
            "warnings": [],
        }
        return SimpleNamespace(
            status="completed",
            output=(),
            output_text=json.dumps(payload),
            model="fake-live-model",
            usage=SimpleNamespace(
                input_tokens=87,
                output_tokens=29,
                output_tokens_details=SimpleNamespace(
                    reasoning_tokens=11,
                    reasoning_summary="never expose this reasoning text",
                ),
            ),
        )


class FakeOpenAIClient:
    def __init__(self, mode: str = "valid") -> None:
        self.responses = FakeResponses(mode)


def client_factory(client: FakeOpenAIClient, calls: list[object]):
    def create(context: object) -> FakeOpenAIClient:
        calls.append(context)
        return client
    return create


def not_required_gate() -> Mock:
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    gate.evaluate.return_value = SemanticAdjudicationDecision(
        scope=AdjudicationScope.NOT_REQUIRED,
        trigger_signals=(),
        topic_required=False,
        format_required=False,
        reason_codes=("TEST_SKIP",),
        warnings=(),
    )
    return gate


def run(
    *,
    mode: str = "valid",
    resolver: SemanticAdjudicationSecretResolver | None = None,
    gate: object = None,
    validator: SemanticAdjudicationProviderConfigValidator | None = None,
) -> tuple[canary.CanaryReport, FakeOpenAIClient, list[object]]:
    client = FakeOpenAIClient(mode)
    factory_calls: list[object] = []
    times = iter((10.0, 10.125))
    report = canary.run_canary(
        model="gpt-5-mini",
        config_validator=validator,
        secret_resolver=resolver or FakeSecretResolver(),
        client_factory=client_factory(client, factory_calls),
        adjudication_gate=gate,
        monotonic=lambda: next(times),
    )
    return report, client, factory_calls


def test_import_is_inert_and_client_construction_is_live_path_only() -> None:
    source = inspect.getsource(canary)
    module_prefix = source.split('if __name__ == "__main__":')[0]
    assert "OpenAI(" in inspect.getsource(canary._create_openai_client)
    assert module_prefix.count("OpenAI(") == 1
    assert "run_canary(" not in module_prefix.split("def main", 1)[0].split(
        "def run_canary", 1
    )[0]
    assert not hasattr(canary, "client")


def test_success_runs_one_synthetic_source_and_one_openai_call(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report, client, factory_calls = run()
    assert report.status == "SUCCESS"
    assert report.exit_code == canary.EXIT_SUCCESS
    assert report.provider_called is report.response_valid is True
    assert len(factory_calls) == 1
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "gpt-5-mini"
    assert call["max_output_tokens"] == 1200
    assert call["timeout"] == 30.0
    assert call["store"] is False
    assert call["tools"] == []
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["reasoning"] == {"effort": "low"}
    assert "reasoning_effort" not in call
    assert "effort" not in call
    assert report.gate_scope != AdjudicationScope.NOT_REQUIRED.value
    assert report.shadow_topic_mutated is False
    assert report.shadow_format_mutated is False
    assert report.shadow_intent_mutated is False
    assert report.input_tokens == 87
    assert report.output_tokens == 29
    assert report.reasoning_tokens == 11
    assert report.non_reasoning_output_tokens == 18
    assert report.output_token_headroom == 1171
    assert report.output_token_headroom_ratio == 1171 / 1200
    assert report.returned_model == "fake-live-model"
    assert report.topic_confidence == "HIGH"
    assert report.format_confidence == "MEDIUM"
    assert report.latency_milliseconds == 125
    assert len(report.input_fingerprint) == 64
    canary.print_summary(report)
    output = capsys.readouterr().out
    assert "Status:\nSUCCESS" in output
    assert "Input Tokens:\n87" in output
    assert "Output Tokens:\n29" in output
    assert "Reasoning Tokens:\n11" in output
    assert "Non-Reasoning Output Tokens:\n18" in output
    assert "Output Token Headroom:\n1171" in output
    assert f"Output Token Headroom Ratio:\n{1171 / 1200}" in output
    assert "Returned Model:\nfake-live-model" in output
    assert "Topic Confidence:\nHIGH" in output
    assert "Format Confidence:\nMEDIUM" in output
    assert "never expose this reasoning text" not in output
    assert report.input_fingerprint in output
    assert "Sanitized Provider Error:\nNONE" in output


def test_config_validation_resolution_and_runtime_builder_are_used() -> None:
    real_validator = SemanticAdjudicationProviderConfigValidator()
    validator = Mock(wraps=real_validator)
    resolver = FakeSecretResolver()
    report, _, factory_calls = run(validator=validator, resolver=resolver)
    assert report.status == "SUCCESS"
    assert validator.validate.call_count == 1
    config = validator.validate.call_args.args[0]
    assert config.model == "gpt-5-mini"
    assert config.max_retries == 0
    assert config.max_output_tokens == 1200
    assert config.temperature == 0.0
    assert config.reasoning_effort is SemanticAdjudicationReasoningEffort.LOW
    assert resolver.calls == [canary.API_KEY_ENV_VAR]
    context = factory_calls[0]
    assert context.api_key == "test-secret"
    assert context.max_retries == 0
    assert context.max_output_tokens == 1200
    assert context.reasoning_effort is SemanticAdjudicationReasoningEffort.LOW


def test_gate_skip_creates_client_but_makes_zero_provider_calls() -> None:
    gate = not_required_gate()
    report, client, factory_calls = run(gate=gate)
    assert report.status == "SKIPPED"
    assert report.error_category == "CANARY_SKIPPED_NOT_REQUIRED"
    assert report.exit_code == canary.EXIT_SUCCESS
    assert report.provider_called is report.response_valid is False
    assert len(factory_calls) == 1
    assert client.responses.calls == []
    assert gate.evaluate.call_count == 1
    assert report.input_fingerprint is None
    assert report.returned_model is None
    assert report.topic_confidence is None
    assert report.format_confidence is None
    assert report.reasoning_tokens is None
    assert report.non_reasoning_output_tokens is None
    assert report.output_token_headroom is None
    assert report.output_token_headroom_ratio is None


def test_configuration_error_stops_before_client_or_provider_call(
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_error = SemanticAdjudicationProviderConfigurationError(
        "missing test secret"
    )
    resolver = FakeSecretResolver(secret_error)
    report, client, factory_calls = run(resolver=resolver)
    assert report.status == "CONFIGURATION_ERROR"
    assert report.exit_code == canary.EXIT_CONFIGURATION_ERROR
    assert report.provider_called is False
    assert factory_calls == []
    assert client.responses.calls == []
    canary.print_summary(report)
    output = capsys.readouterr().out
    assert "missing test secret" not in output
    assert "test-secret" not in output


@pytest.mark.parametrize(
    ("mode", "status", "exit_code"),
    (
        ("timeout", "PROVIDER_ERROR", canary.EXIT_PROVIDER_ERROR),
        ("malformed", "INVALID_RESPONSE", canary.EXIT_INVALID_RESPONSE),
    ),
)
def test_provider_failures_are_fail_open_and_single_attempt(
    mode: str,
    status: str,
    exit_code: int,
) -> None:
    report, client, _ = run(mode=mode)
    assert report.status == status
    assert report.exit_code == exit_code
    assert report.provider_called is True
    assert report.response_valid is False
    assert len(client.responses.calls) == 1
    assert report.shadow_topic_mutated is False
    assert report.shadow_format_mutated is False
    assert report.shadow_intent_mutated is False
    assert report.adjudicated_topic is report.adjudicated_format is None


@pytest.mark.parametrize(
    ("mode", "status", "message"),
    (
        (
            "authentication",
            "CONFIGURATION_ERROR",
            "OpenAI authentication failed.",
        ),
        ("permission", "CONFIGURATION_ERROR", "OpenAI permission denied."),
        (
            "bad_request",
            "CONFIGURATION_ERROR",
            "OpenAI request configuration was rejected. "
            "code=unsupported_value; param=temperature",
        ),
        ("rate_limit", "PROVIDER_ERROR", "OpenAI rate limit reached."),
    ),
)
def test_summary_preserves_exact_sanitized_provider_error(
    mode: str,
    status: str,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report, client, _ = run(mode=mode)
    assert report.status == status
    assert report.sanitized_provider_error == message
    assert len(client.responses.calls) == 1
    canary.print_summary(report)
    output = capsys.readouterr().out
    assert f"Sanitized Provider Error:\n{message}" in output
    assert "raw sk-test-secret message" not in output
    assert "sk-test-secret" not in output
    assert "Bounded source body." not in output


def test_summary_and_call_never_expose_secret_or_forbidden_content(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report, client, _ = run()
    canary.print_summary(report)
    output = capsys.readouterr().out
    call = client.responses.calls[0]
    serialized_call = json.dumps(call, ensure_ascii=False)
    assert "test-secret" not in output
    assert "test-secret" not in serialized_call
    assert "test-secret" not in report.input_fingerprint
    assert canary.CANARY_SOURCE["body"] not in output
    assert "raw response" not in output.casefold()
    assert "chain-of-thought" not in output.casefold()
    assert "correct" not in output.casefold()
    assert "accuracy" not in output.casefold()
    assert call["store"] is False
    assert call["tools"] == []


def test_runner_uses_no_benchmark_labels_loops_retries_or_persistence() -> None:
    source = inspect.getsource(canary)
    casefolded = source.casefold()
    forbidden = (
        "benchmark/batch_",
        "expected_topic",
        "expected_format",
        "oracle",
        "accuracy",
        "write_text",
        "open(\"",
        "git ",
        "for case",
        "while ",
    )
    assert not any(value in casefolded for value in forbidden)
    assert "max_retries=0" in source
    assert "ExperimentalSemanticAdjudicationShadowWorkflow" in source
    assert "OpenAISemanticAdjudicationProvider" in source
    assert "EnvironmentSemanticAdjudicationSecretResolver" in source
    assert "SemanticAdjudicationRuntimeContextBuilder" in source
    assert "resolved_topic" not in source
    assert "resolved_format" not in source
    assert "resolved_reader_intent" not in source


def test_tests_require_no_environment_key_network_or_output_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access attempted")

    monkeypatch.delenv(canary.API_KEY_ENV_VAR, raising=False)
    monkeypatch.setattr(os, "getenv", fail)
    monkeypatch.setattr(socket, "socket", fail)
    before = set(tmp_path.iterdir())
    report, client, _ = run()
    after = set(tmp_path.iterdir())
    assert report.status == "SUCCESS"
    assert len(client.responses.calls) == 1
    assert before == after
