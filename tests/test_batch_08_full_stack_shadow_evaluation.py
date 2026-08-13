"""Offline contract tests for the Batch 08 full-stack shadow evaluation."""

from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import examples.run_batch_08_full_stack_shadow_evaluation as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_decision import SemanticAdjudicationDecision
from tests.test_batch_07_full_stack_shadow_evaluation import FakeProvider, CountingAssessor


def run_fake(tmp_path: Path, **kwargs):
    provider = kwargs.pop("provider", FakeProvider())
    times = iter(float(value) for value in range(40))
    summary = diagnostic.run_evaluation(
        model="gpt-5-mini", provider=provider,
        output_json=tmp_path / "evaluation.json",
        output_md=tmp_path / "evaluation.md",
        monotonic=lambda: next(times),
        now=lambda: datetime(2026, 8, 13, tzinfo=timezone.utc),
        **kwargs,
    )
    return summary, provider


def test_exact_holdout_registration_and_integrity() -> None:
    diagnostic._verify_registration()
    assert diagnostic.CASE_IDS == tuple(f"{value:03d}" for value in range(71, 81))
    assert diagnostic.RAW_SHA256 == "451ddb4c75b6b637f0a2b80e47fc51924fa0f30e1c2f139d6c7118bba99c7d32"


def test_expected_and_risk_metadata_are_isolated_until_predictions_finish(
    tmp_path, monkeypatch,
) -> None:
    assessor = CountingAssessor()
    original = diagnostic.base._score_cases

    def guarded(cases):
        assert assessor.calls == 10
        assert len(cases) == 10
        assert all("expected_topic" not in case for case in cases)
        return original(cases)

    monkeypatch.setattr(diagnostic.base, "_score_cases", guarded)
    run_fake(tmp_path, assessor=assessor)


def test_provider_calls_only_for_open_gate_with_hard_limit(tmp_path) -> None:
    summary, provider = run_fake(tmp_path)
    expected_calls = sum(case["gate_scope"] != "NOT_REQUIRED" for case in summary["cases"])
    assert summary["provider_calls"] == len(provider.calls) == expected_calls
    assert summary["provider_calls"] <= 10
    assert summary["retry_attempts"] == 0


def test_closed_gate_never_calls_provider(tmp_path) -> None:
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    gate.evaluate.return_value = SemanticAdjudicationDecision(
        scope=AdjudicationScope.NOT_REQUIRED, trigger_signals=(),
        topic_required=False, format_required=False,
        reason_codes=("TEST_NOT_REQUIRED",), warnings=(),
    )
    summary, provider = run_fake(tmp_path, adjudication_gate=gate)
    assert summary["provider_calls"] == 0
    assert provider.calls == []


def test_runtime_contract_is_fixed() -> None:
    config = diagnostic.base._configuration("gpt-5-mini")
    assert config.model == "gpt-5-mini"
    assert config.reasoning_effort.value == "LOW"
    assert config.max_output_tokens == 1200
    assert config.max_retries == 0
    assert config.timeout_seconds == 30.0


def test_effective_labels_intent_and_change_metrics_are_derived(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    assert all(
        case["effective_shadow_reader_intent"] == case["deterministic_reader_intent"]
        for case in summary["cases"]
    )
    for dimension in ("topic", "format"):
        changed = [
            case for case in summary["cases"]
            if case[f"effective_shadow_{dimension}"] != case[f"deterministic_{dimension}"]
        ]
        assert summary[dimension]["changed_decisions"] == len(changed)
        assert summary[dimension]["improvements"] == sum(
            case[f"{dimension}_improvement"] for case in summary["cases"]
        )
        assert summary[dimension]["regressions"] == sum(
            case[f"{dimension}_regression"] for case in summary["cases"]
        )


def test_gate_confusion_metrics_are_post_hoc_and_derived(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    for dimension in ("topic", "format"):
        assert summary[f"{dimension}_gate"] == diagnostic.base._confusion(
            summary["cases"], dimension,
        )


def test_format_reachability_and_conversion_diagnostics_are_derived(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    assert set(summary["format_reachability"].values()) <= diagnostic.REACHABILITY
    assert set(summary["format_reachability"]) == set(summary["format_mismatch_cases"])
    relationships = sum(
        case["semantic_format_relationship_present"] for case in summary["cases"]
    )
    assert summary["cases_with_semantic_format_relationships"] == relationships
    assert 0 <= summary["format_component_to_relationship_conversion"] <= 100
    assert 0 <= summary["format_relationship_to_support_conversion"] <= 100
    assert 0 <= summary["expected_format_semantic_reachability_rate"] <= 100


def test_candidate_assessments_remain_diagnostic_and_safety_holds(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    assert any(case["candidate_assessment_summary"] for case in summary["cases"])
    assert not any(summary[key] for key in (
        "shadow_topic_mutated", "shadow_format_mutated", "shadow_intent_mutated",
        "actual_confidence_mutated", "gate_mutated", "resolver_used",
    ))


def test_provider_telemetry_and_confidence_are_trusted(tmp_path) -> None:
    summary, provider = run_fake(tmp_path)
    assert summary["valid_responses"] == len(provider.calls)
    assert summary["invalid_responses"] == summary["provider_errors"] == 0
    assert summary["candidate_compliance"] == summary["fingerprint_integrity"] == 100.0
    assert summary["average_input_tokens"] == 600
    assert summary["average_output_tokens"] == 300
    assert summary["average_reasoning_tokens"] == 100
    assert set(summary["confidence_calibration"]) == {
        f"{correctness}_{level}"
        for correctness in ("correct", "wrong")
        for level in ("HIGH", "MEDIUM", "LOW")
    }


def test_outputs_are_sanitized_and_registration_artifacts_unchanged(tmp_path) -> None:
    frozen = {
        name: (diagnostic.BATCH_ROOT / name).read_bytes()
        for name in ("manifest.json", "expected.json", "human_risk_annotations.json")
    }
    run_fake(tmp_path)
    persisted = (tmp_path / "evaluation.json").read_text(encoding="utf-8")
    assert not any(term in persisted for term in (
        "OPENAI_API_KEY", "sk-", "raw_prompt", "raw_response", "chain-of-thought",
    ))
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in persisted
    assert frozen == {name: (diagnostic.BATCH_ROOT / name).read_bytes() for name in frozen}


def test_classification_and_decisions_use_closed_enums(tmp_path) -> None:
    summary, _ = run_fake(tmp_path)
    assert summary["evaluation_status"] in {"EXCELLENT", "STRONG", "MIXED", "WEAK", "FAILED"}
    assert summary["format_generalization_decision"] in {
        "FORMAT_FIX_GENERALIZED", "FORMAT_FIX_PARTIALLY_GENERALIZED",
        "FORMAT_FIX_DID_NOT_GENERALIZE",
        "FORMAT_EVIDENCE_IMPROVED_BUT_FINAL_CLASSIFICATION_DID_NOT",
        "INSUFFICIENT_EVIDENCE_TO_JUDGE",
    }
    assert summary["product_decision"] in {
        "READY_TO_DESIGN_RESOLVER",
        "BEGIN_LIMITED_RESOLVER_DESIGN_WITH_FORMAT_GUARDRAILS",
        "ANALYZE_BATCH_08_FULL_STACK_FAILURES_ONCE",
        "REDESIGN_FORMAT_SUBSYSTEM", "NOT_READY_FOR_RESOLVER",
    }


def test_recovered_post_run_artifacts_are_complete_and_safe() -> None:
    summary = diagnostic.validate_persisted_evaluation()
    assert summary["cases_evaluated"] == 10
    assert summary["case_ids"] == list(diagnostic.CASE_IDS)
    assert summary["provider_calls"] == diagnostic.RECOVERED_PROVIDER_CALLS == 6
    assert summary["retry_attempts"] == 0
    assert summary["candidate_compliance"] == 100.0
    assert summary["fingerprint_integrity"] == 100.0
    assert summary["scientific_status_after"] == "EVALUATED_PREREGISTERED_HOLDOUT"
