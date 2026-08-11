"""Offline tests for the bounded five-case OpenAI shadow evaluation."""

import json
from pathlib import Path
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import examples.run_batch_05_openai_live_shadow_5case as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.adjudication.semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


class FakeSecretResolver(SemanticAdjudicationSecretResolver):
    def resolve(self, secret_name: str) -> str:
        assert secret_name == "OPENAI_API_KEY"
        return "test-only-secret"


class FakeResponses:
    def __init__(self, incomplete_call: int | None = None) -> None:
        self.incomplete_call = incomplete_call
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        call_number = len(self.calls)
        if call_number == self.incomplete_call:
            return SimpleNamespace(
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            )
        schema = kwargs["text"]["format"]["schema"]
        topics = schema["properties"]["adjudicated_topic"]["enum"]
        formats = schema["properties"]["adjudicated_format"]["enum"]
        payload = {
            "adjudicated_topic": topics[-1],
            "adjudicated_format": formats[-1],
            "topic_confidence": "MEDIUM",
            "format_confidence": "HIGH",
            "topic_reason": "bounded fake rationale",
            "format_reason": "bounded fake rationale",
            "topic_evidence_refs": ["HEADLINE"],
            "format_evidence_refs": ["LEAD"],
            "ambiguity_remaining": call_number % 2 == 0,
            "warnings": [],
        }
        return SimpleNamespace(
            status="completed",
            output=(),
            output_text=json.dumps(payload),
            model="fake-gpt-5-mini",
            usage=SimpleNamespace(
                input_tokens=700 + call_number,
                output_tokens=400 + call_number,
                output_tokens_details=SimpleNamespace(
                    reasoning_tokens=100 + call_number,
                    reasoning_summary="never persist reasoning text",
                ),
            ),
        )


class FakeClient:
    def __init__(self, incomplete_call: int | None = None) -> None:
        self.responses = FakeResponses(incomplete_call)


def run_fake(
    tmp_path: Path,
    *,
    incomplete_call: int | None = None,
    gate: object = None,
) -> tuple[dict[str, object], FakeClient, Path, Path]:
    client = FakeClient(incomplete_call)
    json_path = tmp_path / "result.json"
    md_path = tmp_path / "result.md"
    times = iter(float(value) for value in range(20))
    summary = diagnostic.run_evaluation(
        model="gpt-5-mini",
        output_json=json_path,
        output_md=md_path,
        secret_resolver=FakeSecretResolver(),
        client_factory=lambda context: client,
        adjudication_gate=gate,
        monotonic=lambda: next(times),
    )
    return summary, client, json_path, md_path


def test_selected_cases_calls_runtime_and_sanitized_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *args, **kwargs: pytest.fail("network access attempted"),
    )
    summary, client, json_path, md_path = run_fake(tmp_path)
    assert diagnostic.CASE_IDS == ("044", "045", "046", "048", "050")
    assert summary["cases_selected"] == list(diagnostic.CASE_IDS)
    assert [case["id"] for case in summary["cases"]] == list(diagnostic.CASE_IDS)
    assert summary["provider_calls"] == len(client.responses.calls) == 5
    assert summary["valid_responses"] == 5
    assert all(call["model"] == "gpt-5-mini" for call in client.responses.calls)
    assert all(call["reasoning"] == {"effort": "low"} for call in client.responses.calls)
    assert all("temperature" not in call for call in client.responses.calls)
    assert all(call["max_output_tokens"] == 1200 for call in client.responses.calls)
    assert all(call["store"] is False and call["tools"] == [] for call in client.responses.calls)
    persisted = json_path.read_text(encoding="utf-8")
    assert json.loads(persisted)["cases_selected"] == list(diagnostic.CASE_IDS)
    assert "test-only-secret" not in persisted
    assert "never persist reasoning text" not in persisted
    assert "SOURCE_CONTENT_UNTRUSTED" not in persisted
    assert md_path.exists()
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in persisted


def test_expected_labels_are_loaded_only_after_all_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient()
    original = diagnostic.read_expectations

    def guarded(batch_root: Path):
        assert len(client.responses.calls) == 5
        return original(batch_root)

    monkeypatch.setattr(diagnostic, "read_expectations", guarded)
    times = iter(float(value) for value in range(20))
    diagnostic.run_evaluation(
        model="gpt-5-mini",
        output_json=tmp_path / "result.json",
        output_md=tmp_path / "result.md",
        secret_resolver=FakeSecretResolver(),
        client_factory=lambda context: client,
        monotonic=lambda: next(times),
    )


def test_summary_metrics_are_derived_from_case_records(tmp_path: Path) -> None:
    summary, _, _, _ = run_fake(tmp_path)
    cases = summary["cases"]
    topic_cases = [case for case in cases if case["topic_required"]]
    format_cases = [case for case in cases if case["format_required"]]
    assert summary["topic_correct"] == sum(
        case["topic_match_expected"] is True for case in topic_cases
    )
    assert summary["format_correct"] == sum(
        case["format_match_expected"] is True for case in format_cases
    )
    assert summary["ambiguity_true_cases"] == 2
    assert summary["average_input_tokens"] == 703
    assert summary["average_output_tokens"] == 403
    assert summary["average_reasoning_tokens"] == 103
    assert summary["median_reasoning_tokens"] == 103
    assert summary["average_non_reasoning_output_tokens"] == 300
    assert summary["average_latency_ms"] == 1000
    assert summary["median_latency_ms"] == 1000
    assert summary["max_latency_ms"] == 1000
    assert summary["candidate_compliance_rate"] == 100.0
    assert summary["fingerprint_integrity_rate"] == 100.0
    assert summary["shadow_topic_mutations"] == 0
    assert summary["shadow_format_mutations"] == 0
    assert summary["shadow_intent_mutations"] == 0


def test_failure_is_recorded_once_and_later_cases_continue(tmp_path: Path) -> None:
    summary, client, _, _ = run_fake(tmp_path, incomplete_call=2)
    assert len(client.responses.calls) == 5
    assert summary["valid_responses"] == 4
    assert summary["failed_responses"] == 1
    failed = summary["cases"][1]
    assert failed["response_valid"] is False
    assert failed["provider_error_category"] == (
        "SemanticAdjudicationProviderInvalidResponseError"
    )
    assert failed["provider_error_message_sanitized"] == (
        "OpenAI response is incomplete. reason=max_output_tokens"
    )


def test_not_required_gate_forces_no_calls(tmp_path: Path) -> None:
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    gate.evaluate.return_value = SemanticAdjudicationDecision(
        scope=AdjudicationScope.NOT_REQUIRED,
        trigger_signals=(),
        topic_required=False,
        format_required=False,
        reason_codes=("TEST_SKIP",),
        warnings=(),
    )
    summary, client, _, _ = run_fake(tmp_path, gate=gate)
    assert summary["provider_calls"] == 0
    assert client.responses.calls == []
    assert all(not case["provider_called"] for case in summary["cases"])


def test_call_guard_rejects_sixth_attempt() -> None:
    responses = FakeResponses()
    limited = diagnostic._LimitedResponses(responses)
    for _ in range(5):
        with pytest.raises(Exception):
            limited.create()
    assert limited.call_count == 5
    with pytest.raises(RuntimeError, match="at most five calls"):
        limited.create()
