"""Tests for blind Batch 06 pre-provider generalization validation."""

import hashlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

import examples.run_batch_06_editorial_validation as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


EXPECTED_SHA256 = "336e5f4f49f8e75c55751599b679b29501e3713af1f8d5514ec0a46168f6a4d8"


@pytest.fixture(scope="module")
def analysis() -> dict:
    return diagnostic.analyze_validation()


@pytest.fixture(scope="module")
def comparison(analysis: dict) -> dict:
    previous = (
        json.loads(diagnostic.COMPARISON_JSON.read_text(encoding="utf-8"))[
            "baseline_snapshot"
        ]
        if diagnostic.COMPARISON_JSON.exists()
        else json.loads(diagnostic.OUTPUT_JSON.read_text(encoding="utf-8"))
    )
    return diagnostic.build_comparison(previous, analysis)


def test_exact_cases_integrity_and_no_provider(analysis: dict) -> None:
    assert analysis["validation_status"] == "PASSED"
    assert analysis["case_count"] == 10
    assert analysis["case_ids"] == list(diagnostic.CASE_IDS)
    assert diagnostic.CASE_IDS == tuple(f"{value:03d}" for value in range(51, 61))
    assert analysis["raw_source_sha256"] == diagnostic.RAW_SHA256
    assert analysis["source_integrity"] is True
    assert analysis["provider_calls"] == 0
    assert analysis["expected_labels_sha256"] == EXPECTED_SHA256
    assert hashlib.sha256((diagnostic.BATCH_ROOT / "expected.json").read_bytes()).hexdigest() == EXPECTED_SHA256


def test_editorial_metrics_are_derived_from_frozen_cases(analysis: dict) -> None:
    cases = analysis["cases"]
    assert analysis["topic_matches"] == sum(case["topic_match"] for case in cases)
    assert analysis["topic_mismatches"] == sum(not case["topic_match"] for case in cases)
    assert analysis["topic_accuracy"] == analysis["topic_matches"] / 10 * 100
    assert analysis["format_matches"] == sum(case["format_match"] for case in cases)
    assert analysis["format_mismatches"] == sum(not case["format_match"] for case in cases)
    assert analysis["format_accuracy"] == analysis["format_matches"] / 10 * 100
    assert analysis["reader_intent_matches"] == sum(case["intent_match"] for case in cases)
    assert analysis["reader_intent_mismatches"] == sum(not case["intent_match"] for case in cases)
    assert analysis["reader_intent_accuracy"] == analysis["reader_intent_matches"] / 10 * 100
    assert analysis["fully_matched_cases"] == sum(case["full_match"] for case in cases)
    assert analysis["full_case_accuracy"] == analysis["fully_matched_cases"] / 10 * 100


def test_gate_confusion_matrices_and_projection_are_derived(analysis: dict) -> None:
    cases = analysis["cases"]
    for dimension in ("topic", "format"):
        tp = sum(not case[f"{dimension}_match"] and case[f"{dimension}_required"] for case in cases)
        fp = sum(case[f"{dimension}_match"] and case[f"{dimension}_required"] for case in cases)
        tn = sum(case[f"{dimension}_match"] and not case[f"{dimension}_required"] for case in cases)
        fn = sum(not case[f"{dimension}_match"] and not case[f"{dimension}_required"] for case in cases)
        assert analysis[f"{dimension}_gate_tp"] == tp
        assert analysis[f"{dimension}_gate_fp"] == fp
        assert analysis[f"{dimension}_gate_tn"] == tn
        assert analysis[f"{dimension}_gate_fn"] == fn
        assert tp + fp + tn + fn == 10
    projected = sum(case["gate_scope"] != "NOT_REQUIRED" for case in cases)
    assert analysis["projected_provider_call_cases"] == projected
    assert analysis["projected_provider_call_rate"] == projected * 10.0
    assert sum(analysis["scope_distribution"].values()) == 10


def test_expected_and_risk_data_are_read_only_after_predictions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CountingWorkflow:
        def __init__(self) -> None:
            self.delegate = ExperimentalSemanticEditorialAnalysisWorkflow()
            self.calls = 0

        def process(self, **kwargs):
            self.calls += 1
            return self.delegate.process(**kwargs)

    workflow = CountingWorkflow()
    expected_reader = diagnostic.read_expectations
    risk_reader = diagnostic._read_risk_annotations

    def guarded_expected(batch_root: Path):
        assert workflow.calls == 10
        return expected_reader(batch_root)

    def guarded_risk(batch_root: Path):
        assert workflow.calls == 10
        return risk_reader(batch_root)

    monkeypatch.setattr(diagnostic, "read_expectations", guarded_expected)
    monkeypatch.setattr(diagnostic, "_read_risk_annotations", guarded_risk)
    result = diagnostic.analyze_validation(workflow=workflow)
    assert result["risk_annotations_isolated"] is True


def test_rendered_outputs_have_complete_fields_without_source_bodies(analysis: dict) -> None:
    rendered = diagnostic.render_json(analysis) + diagnostic.render_markdown(analysis)
    required = {
        "id", "expected_topic", "predicted_topic", "topic_match",
        "expected_format", "predicted_format", "format_match",
        "expected_reader_intent", "predicted_reader_intent", "intent_match",
        "full_match", "topic_confidence", "format_confidence",
        "contextual_support_labels", "contextual_suppressions",
        "semantic_relationship_count", "primary_semantic_domains",
        "secondary_semantic_domains", "semantic_format_support",
        "semantic_format_suppression", "gate_scope", "topic_required",
        "format_required", "trigger_signals",
    }
    assert all(required <= set(case) for case in analysis["cases"])
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in rendered
    assert "OPENAI_API_KEY" not in rendered
    assert "raw_prompt" not in rendered


def test_module_has_no_provider_prompt_or_benchmark_specific_production_change() -> None:
    source = inspect.getsource(diagnostic)
    forbidden = (
        "OpenAI(", "responses.create", "OpenAISemanticAdjudicationProvider",
        "SemanticAdjudicationRequestBuilder", "_provider_input", "provider.adjudicate",
    )
    assert not any(value in source for value in forbidden)
    assert diagnostic.OUTPUT_JSON.parent == diagnostic.BATCH_ROOT
    assert diagnostic.OUTPUT_MD.parent == diagnostic.BATCH_ROOT


def test_post_change_comparison_loads_registered_baseline(comparison: dict) -> None:
    assert comparison["case_count"] == 10
    assert comparison["baseline"] == "HKEI-155"
    assert comparison["previous_topic_accuracy"] == 40.0
    assert comparison["previous_format_accuracy"] == 40.0
    assert comparison["previous_reader_intent_accuracy"] == 40.0
    assert comparison["previous_full_case_accuracy"] == 0.0
    assert comparison["previous_semantic_relationships"] == 3
    assert comparison["previous_primary_domains"] == 1
    assert comparison["previous_format_supports"] == 0


def test_current_metrics_and_deltas_are_exact(
    analysis: dict, comparison: dict,
) -> None:
    for field in (
        "topic_accuracy", "format_accuracy", "reader_intent_accuracy",
        "full_case_accuracy",
    ):
        assert comparison[f"current_{field}"] == analysis[field]
        assert comparison[f"{field}_delta"] == (
            analysis[field] - comparison[f"previous_{field}"]
        )
    assert comparison["fully_matched_cases"] == [
        case["id"] for case in analysis["cases"] if case["full_match"]
    ]


def test_mismatch_deltas_are_set_differences(comparison: dict) -> None:
    for dimension in ("topic", "format", "reader_intent"):
        previous = {
            case["id"] for case in comparison["baseline_snapshot"]["cases"]
            if not case["intent_match" if dimension == "reader_intent" else f"{dimension}_match"]
        }
        current = set(comparison[f"current_{dimension}_mismatches"])
        assert comparison[f"resolved_{dimension}_mismatches"] == sorted(previous - current)
        assert comparison[f"new_{dimension}_mismatches"] == sorted(current - previous)
        assert comparison[f"unchanged_{dimension}_mismatches"] == sorted(current & previous)


def test_evidence_funnel_and_conversion_deltas_are_derived(
    analysis: dict, comparison: dict,
) -> None:
    funnel = comparison["evidence_funnel"]
    assert funnel["cases_with_semantic_relationships"] == analysis["cases_with_semantic_relationships"]
    assert comparison["semantic_relationship_count_delta"] == analysis["cases_with_semantic_relationships"] - 3
    assert comparison["primary_domain_count_delta"] == analysis["cases_with_primary_semantic_domains"] - 1
    assert comparison["format_support_count_delta"] == analysis["cases_with_semantic_format_support"]
    assert comparison["conversion_metrics"]["semantic_format_support_rate"] == analysis["cases_with_semantic_format_support"] * 10.0


def test_comparison_gate_matrices_and_previous_false_negatives(
    analysis: dict, comparison: dict,
) -> None:
    assert comparison["previous_topic_gate"]["recall"] == 100.0
    assert comparison["previous_format_gate"]["recall"] == 50.0
    assert comparison["previous_format_fn_cases"] == ["054", "056", "059"]
    assert set(comparison["previous_fn_tracking"]) == {"054", "056", "059"}
    for dimension in ("topic", "format"):
        for key in ("tp", "fp", "tn", "fn", "precision", "recall"):
            assert comparison[f"current_{dimension}_gate"][key] == analysis[f"{dimension}_gate_{key}"]


def test_comparison_preserves_integrity_and_has_no_provider_call(
    comparison: dict,
) -> None:
    assert comparison["provider_calls"] == 0
    assert comparison["expected_labels_unchanged"] is True
    assert comparison["raw_source_integrity"] is True
    assert comparison["regression_controls_preserved"] is True


def test_hkei_158_changes_no_production_files() -> None:
    root = Path(__file__).resolve().parents[1]
    changed = subprocess.run(
        ["git", "diff", "--name-only", "61b2669"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    authorized_later_evidence_work = {
        "src/evidence/evidence_role.py",
        "src/evidence/deterministic_contextual_evidence_engine.py",
        "src/semantics/deterministic_compositional_semantic_engine.py",
    }
    assert not any(
        path.startswith("src/") and path not in authorized_later_evidence_work
        for path in changed
    )
