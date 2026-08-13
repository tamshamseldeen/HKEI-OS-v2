"""Integrity tests for the post-HKEI-192 offline Format V2 audit."""

import inspect
import json

import pytest

import examples.run_editorial_format_v2_post_feature_refinement_audit as audit
from examples.run_benchmark_batch_02_validation import parse_source
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature


@pytest.fixture(scope="module")
def result() -> dict:
    return audit.analyze()


def test_hkei_191_baseline_is_loaded_exactly() -> None:
    baseline = audit._load_baseline()
    assert baseline["cases_evaluated"] == 60
    assert baseline["v1_accuracy"] == pytest.approx(55.0)
    assert baseline["v2_accuracy"] == pytest.approx(41.6666666667)
    assert (baseline["v2_improvements"], baseline["v2_regressions"], baseline["wrong_to_wrong_changes"]) == (12, 20, 12)
    assert baseline["failure_ownership_counts"]["FEATURE_EXTRACTION"] == 35


def test_same_evaluable_case_set_and_metrics_are_deterministic(result: dict) -> None:
    baseline = audit._load_baseline()
    old_keys = sorted(f"{case['batch']}:{case['id']}" for case in baseline["cases"])
    assert result["case_keys"] == old_keys
    assert result == audit.analyze()


def test_aggregate_and_delta_metrics_are_derived(result: dict) -> None:
    assert result["v2_delta_vs_previous"] == pytest.approx(result["current_v2_accuracy"] - result["previous_v2_accuracy"])
    assert result["v2_delta_vs_v1"] == pytest.approx(result["current_v2_accuracy"] - result["v1_accuracy"])
    assert result["net_case_gain"] == result["newly_correct_cases_after_hkei_192"] - result["newly_wrong_cases_after_hkei_192"]


def test_batch_and_format_deltas_are_complete_and_correct(result: dict) -> None:
    assert sum(item["case_count"] for item in result["batch_metrics"].values()) == 60
    assert tuple(result["format_metrics"]) == tuple(label.value for label in EditorialFormat)
    assert sum(item["support"] for item in result["format_metrics"].values()) == 60
    for item in result["batch_metrics"].values():
        assert item["delta_vs_previous_v2"] == pytest.approx(item["current_v2_accuracy"] - item["previous_v2_accuracy"])
    for item in result["format_metrics"].values():
        assert item["delta_vs_previous_v2"] == pytest.approx(
            item["current_v2_accuracy"] - item["previous_v2_correct"] / item["support"] * 100 if item["support"] else 0
        )


def test_completeness_and_feature_coverage_deltas_are_complete(result: dict) -> None:
    assert result["expected_profile_complete_rate_after"] + result["expected_profile_partial_rate"] + result["expected_profile_incomplete_rate_after"] == pytest.approx(100.0)
    assert sum(item["count"] for item in result["selected_completeness_distribution"].values()) == 60
    assert set(result["feature_coverage_deltas"]) == {feature.value for feature in EditorialTreatmentFeature}
    for item in result["feature_coverage_deltas"].values():
        assert item["delta"] == item["current_cases_detected"] - item["previous_cases_detected"]


def test_analysis_and_failure_ownership_metrics_are_consistent(result: dict) -> None:
    assert result["analysis_predictions"] == result["correct_analysis_predictions"] + result["false_analysis_predictions"]
    assert sum(result["false_analysis_by_expected_format"].values()) == result["false_analysis_predictions"]
    errors = 60 - round(result["current_v2_accuracy"] * 60 / 100)
    assert sum(result["failure_ownership_after"].values()) == errors


def test_expected_labels_are_isolated_until_predictions_complete(monkeypatch) -> None:
    observed = {}
    original = audit.baseline_runner._join_truth

    def guarded(cases, labels):
        observed["count"] = len(cases)
        assert all("expected_format" not in case for case in cases)
        assert all(len(case["candidate_assessments"]) == 12 for case in cases)
        return original(cases, labels)

    monkeypatch.setattr(audit.baseline_runner, "_join_truth", guarded)
    assert audit.analyze()["cases_evaluated"] == observed["count"] == 60


def test_no_provider_production_mutation_or_source_body_persistence(result: dict) -> None:
    assert result["provider_calls"] == 0
    assert result["v1_format_mutated"] is False
    assert result["reader_intent_mutated"] is False
    assert result["gate_mutated"] is False
    audit._verify_frozen_production()
    source_code = inspect.getsource(audit)
    assert "OpenAI(" not in source_code and ".adjudicate(" not in source_code
    serialized = json.dumps(result, ensure_ascii=False)
    for batch_id in audit.baseline_runner.BATCH_IDS[1:]:
        root = audit.PROJECT_ROOT / "benchmark" / batch_id
        for item in audit.baseline_runner.read_manifest(root):
            assert parse_source(root / item["source_file"]).body not in serialized
