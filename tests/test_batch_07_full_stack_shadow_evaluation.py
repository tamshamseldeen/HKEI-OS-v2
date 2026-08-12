"""Offline tests for the preregistered Batch 07 full-stack evaluation."""

from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import examples.run_batch_07_full_stack_shadow_evaluation as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import DeterministicSemanticAdjudicationGate
from src.adjudication.semantic_adjudication_decision import SemanticAdjudicationDecision
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor


class FakeProvider(SemanticAdjudicationProvider):
    def __init__(self) -> None:
        self.calls = []

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "gpt-5-mini"

    def adjudicate(self, request):
        self.calls.append(request)
        return SemanticAdjudicationResponse(
            adjudicated_topic=request.deterministic_topic,
            adjudicated_format=request.deterministic_format,
            topic_confidence=AdjudicationConfidence.HIGH,
            format_confidence=AdjudicationConfidence.MEDIUM,
            topic_reason="safe fake rationale",
            format_reason="safe fake rationale",
            topic_evidence_refs=("HEADLINE",),
            format_evidence_refs=("LEAD",),
            ambiguity_remaining=False,
            warnings=(),
            provider="fake",
            model="fake-gpt-5-mini",
            request_schema_version="1.0",
            response_schema_version="1.1",
            input_fingerprint=request.input_fingerprint,
            usage=SemanticAdjudicationUsage(
                input_tokens=600, output_tokens=300, reasoning_tokens=100,
            ),
        )


class CountingAssessor:
    def __init__(self) -> None:
        self.inner = DeterministicSemanticCandidateAssessor()
        self.calls = 0

    def assess(self, **kwargs):
        self.calls += 1
        return self.inner.assess(**kwargs)


def run_fake(tmp_path: Path, **kwargs):
    provider = kwargs.pop("provider", FakeProvider())
    times = iter(float(value) for value in range(40))
    summary = diagnostic.run_evaluation(
        model="gpt-5-mini",
        provider=provider,
        output_json=tmp_path / "evaluation.json",
        output_md=tmp_path / "evaluation.md",
        monotonic=lambda: next(times),
        now=lambda: datetime(2026, 8, 12, tzinfo=timezone.utc),
        **kwargs,
    )
    return summary, provider


def test_exact_holdout_integrity_and_frozen_registration() -> None:
    diagnostic._verify_registration()
    assert diagnostic.CASE_IDS == tuple(f"{value:03d}" for value in range(61, 71))
    assert diagnostic.RAW_SHA256 == "7a8ab6b9155276eeabbb4459590fa9c10528cfd3c9a5fc517f8d0abed5d39be3"


def test_expected_and_risk_metadata_are_joined_only_after_all_predictions(tmp_path, monkeypatch) -> None:
    assessor = CountingAssessor()
    original = diagnostic._score_cases

    def guarded(cases):
        assert assessor.calls == 10
        assert len(cases) == 10
        assert all("expected_topic" not in case for case in cases)
        return original(cases)

    monkeypatch.setattr(diagnostic, "_score_cases", guarded)
    run_fake(tmp_path, assessor=assessor)


def test_provider_called_only_when_gate_requires_and_never_more_than_ten(tmp_path) -> None:
    summary, provider = run_fake(tmp_path)
    required = sum(case["gate_scope"] != "NOT_REQUIRED" for case in summary["cases"])
    assert summary["provider_calls"] == len(provider.calls) == required
    assert summary["provider_calls"] <= 10
    assert all(case["provider_called"] == (case["gate_scope"] != "NOT_REQUIRED") for case in summary["cases"])


def test_not_required_gate_makes_no_provider_calls(tmp_path) -> None:
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    gate.evaluate.return_value = SemanticAdjudicationDecision(
        scope=AdjudicationScope.NOT_REQUIRED,
        trigger_signals=(), topic_required=False, format_required=False,
        reason_codes=("TEST_NOT_REQUIRED",), warnings=(),
    )
    summary, provider = run_fake(tmp_path, adjudication_gate=gate)
    assert summary["provider_calls"] == 0
    assert provider.calls == []


def test_call_guard_rejects_eleventh_request() -> None:
    limited = diagnostic._LimitedProvider(FakeProvider())
    request = Mock()
    for _ in range(10):
        limited.adjudicate(request)
    with pytest.raises(RuntimeError, match="at most ten calls"):
        limited.adjudicate(request)
    assert limited.call_count == 10


def test_approved_runtime_is_fixed_and_retry_free() -> None:
    config = diagnostic._configuration("gpt-5-mini")
    assert config.model == "gpt-5-mini"
    assert config.max_output_tokens == 1200
    assert config.max_retries == 0
    assert config.timeout_seconds == 30.0
    assert config.reasoning_effort.value == "LOW"


def test_effective_labels_and_reader_intent_rules() -> None:
    case = {
        "deterministic_topic": "A", "deterministic_format": "B",
        "deterministic_reader_intent": "GET_UPDATE", "topic_required": True,
        "format_required": False, "response_valid": True,
        "adjudicated_topic": "C", "adjudicated_format": "D",
    }
    assert diagnostic._effective_label(case, "topic") == "C"
    assert diagnostic._effective_label(case, "format") == "B"
    assert case["deterministic_reader_intent"] == "GET_UPDATE"


def _metric_cases():
    return [
        {"id": "1", "deterministic_topic": "A", "effective_shadow_topic": "B", "expected_topic": "B", "topic_match_before": False, "topic_match_after": True, "topic_improvement": True, "topic_regression": False},
        {"id": "2", "deterministic_topic": "A", "effective_shadow_topic": "C", "expected_topic": "B", "topic_match_before": False, "topic_match_after": False, "topic_improvement": False, "topic_regression": False},
        {"id": "3", "deterministic_topic": "A", "effective_shadow_topic": "C", "expected_topic": "A", "topic_match_before": True, "topic_match_after": False, "topic_improvement": False, "topic_regression": True},
    ]


def test_improvement_regression_wrong_to_wrong_and_override_precision() -> None:
    metrics = diagnostic._dimension_metrics(_metric_cases(), "topic")
    assert metrics["improvements"] == 1
    assert metrics["regressions"] == 1
    assert metrics["wrong_to_wrong_changes"] == 1
    assert metrics["changed_decisions"] == 3
    assert metrics["correct_changes"] == 1
    assert metrics["change_precision"] == pytest.approx(100 / 3)


def test_gate_confusion_matrix() -> None:
    cases = [
        {"topic_required": True, "topic_match_before": False},
        {"topic_required": True, "topic_match_before": True},
        {"topic_required": False, "topic_match_before": True},
        {"topic_required": False, "topic_match_before": False},
    ]
    assert diagnostic._confusion(cases, "topic") == {
        "tp": 1, "fp": 1, "tn": 1, "fn": 1,
        "precision": 50.0, "recall": 50.0,
    }


def test_summary_metrics_and_diagnostics_are_derived(tmp_path) -> None:
    summary, provider = run_fake(tmp_path)
    assert summary["cases_evaluated"] == 10
    assert summary["retry_attempts"] == 0
    assert summary["valid_responses"] == len(provider.calls)
    assert summary["invalid_responses"] == 0
    assert summary["provider_errors"] == 0
    assert summary["candidate_compliance"] == 100.0
    assert summary["fingerprint_integrity"] == 100.0
    assert summary["average_input_tokens"] == 600
    assert summary["average_output_tokens"] == 300
    assert summary["average_reasoning_tokens"] == 100
    assert summary["average_non_reasoning_output_tokens"] == 200


def test_candidate_assessments_are_diagnostic_only_and_no_mutations(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    assert any(case["candidate_assessment_summary"] for case in summary["cases"])
    assert summary["shadow_topic_mutated"] is False
    assert summary["shadow_format_mutated"] is False
    assert summary["shadow_intent_mutated"] is False
    assert summary["actual_confidence_mutated"] is False
    assert summary["gate_mutated"] is False
    assert summary["resolver_used"] is False


def test_sanitized_artifacts_exclude_secrets_sources_and_raw_responses(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    persisted = (tmp_path / "evaluation.json").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in persisted
    assert "sk-" not in persisted
    assert "raw_response" not in persisted
    assert "chain-of-thought" not in persisted
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in persisted
    assert json.loads(persisted)["cases_evaluated"] == summary["cases_evaluated"]


def test_registration_artifacts_remain_untouched_by_fake_run(tmp_path) -> None:
    before = {
        name: (diagnostic.BATCH_ROOT / name).read_bytes()
        for name in ("manifest.json", "expected.json", "human_risk_annotations.json")
    }
    run_fake(tmp_path)
    assert before == {name: (diagnostic.BATCH_ROOT / name).read_bytes() for name in before}
