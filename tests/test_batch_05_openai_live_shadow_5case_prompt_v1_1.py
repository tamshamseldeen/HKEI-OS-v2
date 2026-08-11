"""Offline tests for the bounded Prompt v1.1 five-case A/B comparison."""

import hashlib
import inspect
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

import examples.run_batch_05_openai_live_shadow_5case_prompt_v1_1 as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from src.adjudication.semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


class FakeSecretResolver(SemanticAdjudicationSecretResolver):
    def resolve(self, secret_name: str) -> str:
        assert secret_name == "OPENAI_API_KEY"
        return "test-only-secret"


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        call_number = len(self.calls)
        schema = kwargs["text"]["format"]["schema"]
        topics = schema["properties"]["adjudicated_topic"]["enum"]
        formats = schema["properties"]["adjudicated_format"]["enum"]
        payload = {
            "adjudicated_topic": topics[-1],
            "adjudicated_format": formats[-1],
            "topic_confidence": "HIGH",
            "format_confidence": "MEDIUM",
            "topic_reason": "fake concise rationale that must not persist",
            "format_reason": "fake concise rationale that must not persist",
            "topic_evidence_refs": ["TITLE"],
            "format_evidence_refs": ["BODY"],
            "ambiguity_remaining": call_number % 2 == 0,
            "warnings": [],
        }
        return SimpleNamespace(
            status="completed",
            output=(),
            output_text=json.dumps(payload),
            model="fake-gpt-5-mini",
            usage=SimpleNamespace(
                input_tokens=1000 + call_number,
                output_tokens=300 + call_number,
                output_tokens_details=SimpleNamespace(
                    reasoning_tokens=100 + call_number,
                    reasoning_summary="hidden fake reasoning that must not persist",
                ),
            ),
        )


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def run_fake(tmp_path: Path) -> tuple[dict, dict, FakeClient, list[Path]]:
    client = FakeClient()
    paths = [
        tmp_path / "b.json", tmp_path / "b.md",
        tmp_path / "comparison.json", tmp_path / "comparison.md",
    ]
    times = iter(float(value) for value in range(20))
    b_side, comparison = diagnostic.run_comparison(
        model="gpt-5-mini",
        output_json=paths[0],
        output_md=paths[1],
        comparison_json=paths[2],
        comparison_md=paths[3],
        secret_resolver=FakeSecretResolver(),
        client_factory=lambda context: client,
        monotonic=lambda: next(times),
    )
    return b_side, comparison, client, paths


def test_exact_cases_runtime_parity_prompt_version_and_five_call_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("network"))
    b_side, comparison, client, _ = run_fake(tmp_path)
    assert diagnostic.CASE_IDS == ("044", "045", "046", "048", "050")
    assert diagnostic.PROMPT_VERSION == "1.1"
    assert diagnostic.MAX_CALLS == 5
    assert b_side["cases_selected"] == list(diagnostic.CASE_IDS)
    assert comparison["cases"] == list(diagnostic.CASE_IDS)
    assert len(client.responses.calls) == b_side["provider_calls"] == 5
    for call in client.responses.calls:
        assert call["model"] == "gpt-5-mini"
        assert call["reasoning"] == {"effort": "low"}
        assert call["max_output_tokens"] == 1200
        assert call["timeout"] == 30.0
        assert call["store"] is False and call["tools"] == []
        assert "temperature" not in call


def test_runtime_or_prompt_mismatch_stops_before_client_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = diagnostic._read(diagnostic.BASELINE_JSON)
    with pytest.raises(diagnostic.ABRuntimeMismatchError, match="A_B_RUNTIME_MISMATCH"):
        diagnostic.verify_experiment("gpt-4o-mini", baseline)
    monkeypatch.setattr(diagnostic, "OPENAI_ADJUDICATION_PROMPT_VERSION", "1.2")
    with pytest.raises(diagnostic.ABRuntimeMismatchError, match="A_B_RUNTIME_MISMATCH"):
        diagnostic.verify_experiment("gpt-5-mini", baseline)


def test_baseline_is_read_only_and_expected_labels_load_after_all_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = hashlib.sha256(diagnostic.BASELINE_JSON.read_bytes()).hexdigest()
    client = FakeClient()
    original = diagnostic.live_runner.read_expectations

    def guarded(batch_root: Path):
        assert len(client.responses.calls) == 5
        return original(batch_root)

    monkeypatch.setattr(diagnostic.live_runner, "read_expectations", guarded)
    paths = [tmp_path / name for name in ("b.json", "b.md", "ab.json", "ab.md")]
    times = iter(float(value) for value in range(20))
    diagnostic.run_comparison(
        model="gpt-5-mini",
        output_json=paths[0], output_md=paths[1],
        comparison_json=paths[2], comparison_md=paths[3],
        secret_resolver=FakeSecretResolver(),
        client_factory=lambda context: client,
        monotonic=lambda: next(times),
    )
    assert hashlib.sha256(diagnostic.BASELINE_JSON.read_bytes()).hexdigest() == before


def test_ab_accuracy_anchoring_ambiguity_efficiency_and_integrity(tmp_path: Path) -> None:
    b_side, result, _, _ = run_fake(tmp_path)
    assert result["a_topic_accuracy"] == 60.0
    assert result["a_format_accuracy"] == 0.0
    assert result["a_fully_correct_cases"] == 2
    assert result["a_format_anchoring_rate"] == 100.0
    assert result["a_wrong_format_with_deterministic_preserved"] == 3
    assert result["topic_accuracy_delta_percentage_points"] == (
        result["b_topic_accuracy"] - result["a_topic_accuracy"]
    )
    assert result["format_accuracy_delta_percentage_points"] == (
        result["b_format_accuracy"] - result["a_format_accuracy"]
    )
    assert result["format_anchoring_rate_delta_percentage_points"] == (
        result["b_format_anchoring_rate"] - result["a_format_anchoring_rate"]
    )
    assert result["average_input_token_delta"] == b_side["average_input_tokens"] - 955.4
    assert result["average_output_token_delta"] == b_side["average_output_tokens"] - 505.6
    assert result["average_reasoning_token_delta"] == b_side["average_reasoning_tokens"] - 153.6
    assert result["b_side"]["candidate_compliance_rate"] == 100.0
    assert result["b_side"]["fingerprint_integrity_rate"] == 100.0
    assert result["b_side"]["shadow_mutations"] == 0
    assert all(case["candidate_compliant"] is True for case in b_side["cases"])
    assert all(case["fingerprint_valid"] is True for case in b_side["cases"])


def test_persisted_outputs_are_sanitized_metrics_and_labels_only(tmp_path: Path) -> None:
    _, _, _, paths = run_fake(tmp_path)
    combined = "".join(path.read_text(encoding="utf-8") for path in paths)
    assert "test-only-secret" not in combined
    assert "fake concise rationale" not in combined
    assert "hidden fake reasoning" not in combined
    assert "SOURCE_CONTENT_UNTRUSTED" not in combined
    assert "chain-of-thought" not in combined
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in combined


def test_module_has_no_retry_fallback_or_direct_expected_label_prompting() -> None:
    source = inspect.getsource(diagnostic)
    assert "MAX_CALLS = 5" in source
    assert "retry" not in source.casefold()
    assert "fallback" not in source.casefold()
    assert "responses.create" not in source
    assert "read_expectations" not in source
