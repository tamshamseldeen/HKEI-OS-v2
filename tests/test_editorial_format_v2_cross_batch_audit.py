"""Offline integrity tests for the cross-batch Format V2 shadow audit."""

import inspect
import json
from pathlib import Path

import pytest

import examples.run_editorial_format_v2_cross_batch_audit as audit
from examples.run_benchmark_batch_02_validation import parse_source
from src.formatting.editorial_format import EditorialFormat


@pytest.fixture(scope="module")
def result() -> dict:
    return audit.analyze()


def test_expected_labels_are_joined_only_after_every_prediction(monkeypatch) -> None:
    original = audit._join_truth
    observed = {}

    def guarded(cases, labels):
        observed["count"] = len(cases)
        assert len(cases) == 60
        assert all("expected_format" not in case for case in cases)
        assert all(len(case["candidate_assessments"]) == 12 for case in cases)
        return original(cases, labels)

    monkeypatch.setattr(audit, "_join_truth", guarded)
    value = audit.analyze()
    assert observed["count"] == value["cases_evaluated"] == 60


def test_case_inventory_and_batch_metrics_are_derived(result: dict) -> None:
    assert result["excluded_batches_without_valid_expected_format"] == ["batch_01"]
    assert sum(item["case_count"] for item in result["batch_metrics"].values()) == 60
    for batch, item in result["batch_metrics"].items():
        cases = [case for case in result["cases"] if case["batch"] == batch]
        assert item["case_count"] == len(cases)
        assert item["improvements"] == sum(not case["v1_correct"] and case["v2_correct"] for case in cases)
        assert item["regressions"] == sum(case["v1_correct"] and not case["v2_correct"] for case in cases)


def test_aggregate_transition_metrics_are_derived(result: dict) -> None:
    cases = result["cases"]
    assert result["v2_improvements"] == sum(not case["v1_correct"] and case["v2_correct"] for case in cases)
    assert result["v2_regressions"] == sum(case["v1_correct"] and not case["v2_correct"] for case in cases)
    assert result["v1_accuracy"] == pytest.approx(sum(case["v1_correct"] for case in cases) / 60 * 100)
    assert result["v2_accuracy"] == pytest.approx(sum(case["v2_correct"] for case in cases) / 60 * 100)


def test_per_format_support_and_accuracy_include_all_labels(result: dict) -> None:
    assert tuple(result["format_metrics"]) == tuple(item.value for item in EditorialFormat)
    assert sum(item["support"] for item in result["format_metrics"].values()) == 60
    for label, metrics in result["format_metrics"].items():
        cases = [case for case in result["cases"] if case["expected_format"] == label]
        assert metrics["support"] == len(cases)
        assert metrics["v2_correct"] == sum(case["v2_correct"] for case in cases)


def test_confusion_matrix_and_frequent_pairs_are_derived(result: dict) -> None:
    assert sum(sum(row.values()) for row in result["v2_confusion_matrix"].values()) == 60
    assert all(item["expected"] != item["predicted"] for item in result["most_frequent_v2_confusion_pairs"])


@pytest.mark.parametrize(
    ("key", "values"),
    [
        ("ambiguity_distribution", ("CLEAR", "COMPETING", "INSUFFICIENT_EVIDENCE", "CONTRADICTORY")),
        ("confidence_distribution", ("HIGH", "MEDIUM", "LOW")),
        ("selected_completeness_distribution", ("COMPLETE", "PARTIAL", "INCOMPLETE")),
    ],
)
def test_diagnostic_distributions_are_complete(result: dict, key: str, values) -> None:
    assert tuple(result[key]) == values
    assert sum(item["count"] for item in result[key].values()) == 60
    assert all(0 <= item["accuracy"] <= 100 for item in result[key].values())


def test_competition_failure_ownership_and_reachability_are_valid(result: dict) -> None:
    assert set(result["failure_ownership_counts"]) == audit.FAILURE_OWNERS
    assert sum(result["failure_ownership_counts"].values()) == sum(not case["v2_correct"] for case in result["cases"])
    assert result["expected_profile_complete_rate"] + result["expected_profile_partial_rate"] + result["expected_profile_incomplete_rate"] == pytest.approx(100.0)


def test_v1_shadow_safety_and_no_provider_path(result: dict) -> None:
    assert result["v1_format_mutated"] is False
    assert result["reader_intent_mutated"] is False
    assert result["gate_mutated"] is False
    assert result["provider_calls"] == 0
    source = inspect.getsource(audit)
    assert "OpenAI(" not in source
    assert ".adjudicate(" not in source


def test_persisted_outputs_are_sanitized_and_contain_no_source_bodies() -> None:
    persisted = audit.OUTPUT_JSON.read_text(encoding="utf-8") + audit.OUTPUT_MD.read_text(encoding="utf-8")
    assert not any(term in persisted for term in ("OPENAI_API_KEY", "sk-", "raw_prompt", "raw_response"))
    for batch in audit.BATCH_IDS[1:]:
        root = audit.PROJECT_ROOT / "benchmark" / batch
        for item in audit.read_manifest(root):
            assert parse_source(root / item["source_file"]).body not in persisted


def test_audit_does_not_encode_benchmark_specific_classifier_tuning() -> None:
    classifier_source = (audit.PROJECT_ROOT / "src/formatting/editorial_format_v2_classifier.py").read_text(encoding="utf-8")
    extractor_source = (audit.PROJECT_ROOT / "src/formatting/editorial_treatment_feature_extractor.py").read_text(encoding="utf-8")
    assert "batch_" not in classifier_source.casefold()
    assert "batch_" not in extractor_source.casefold()
