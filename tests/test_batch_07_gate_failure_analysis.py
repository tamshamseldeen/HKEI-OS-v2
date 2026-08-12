"""Offline tests for the persisted Batch 07 Gate failure diagnosis."""

import ast
import hashlib
import json
from pathlib import Path

import pytest

import examples.run_batch_07_gate_failure_analysis as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source


@pytest.fixture(scope="module")
def result():
    return diagnostic.analyze()


def test_hkei_178_gate_metrics_are_reproduced(result) -> None:
    assert result["hkei_178_topic_gate"] == {
        "tp": 6, "fp": 2, "tn": 1, "fn": 1,
        "precision": 75.0, "recall": pytest.approx(85.71428571428571),
    }
    assert result["hkei_178_format_gate"] == {
        "tp": 1, "fp": 1, "tn": 1, "fn": 7,
        "precision": 50.0, "recall": 12.5,
    }


def test_false_negative_ids_are_derived_not_hard_coded(result) -> None:
    source = Path(diagnostic.__file__).read_text(encoding="utf-8")
    derived_ids = {
        item["id"] for key in ("topic_gate_false_negatives", "format_gate_false_negatives")
        for item in result[key]
    }
    assert derived_ids
    assert all(f'"{case_id}"' not in source and f"'{case_id}'" not in source for case_id in derived_ids)


def test_exact_false_negative_counts(result) -> None:
    assert result["topic_fn_count"] == 1
    assert result["format_fn_count"] == 7


def test_all_failure_classes_are_allowed(result) -> None:
    traces = result["topic_gate_false_negatives"] + result["format_gate_false_negatives"]
    assert all(trace["failure_class"] in diagnostic.FAILURE_CLASSES for trace in traces)


def test_existing_and_missing_format_signals_are_deterministic(result) -> None:
    traces = result["format_gate_false_negatives"]
    existing = [trace for trace in traces if trace["existing_unresolved_format_signal"]]
    missing = [trace for trace in traces if not trace["existing_unresolved_format_signal"]]
    assert len(existing) == result["format_fn_with_existing_unresolved_signal"] == 5
    assert len(missing) == result["format_fn_without_existing_unresolved_signal"] == 2
    assert all(trace["existing_signal_gate_failed_to_consume"] for trace in existing)
    assert all(trace["upstream_missing_representation"] for trace in missing)


def test_false_sufficiency_is_audited_without_gate_causation(result) -> None:
    false_sufficient = result["false_sufficient_assessments"]
    assert len(false_sufficient) == 2
    assert all(item["sufficiency"] == "SUFFICIENT" for item in false_sufficient)
    assert all(item["candidate"] != item["expected"] for item in false_sufficient)
    assert result["false_sufficient_contributing_to_gate_fn"] == []


def test_counterfactual_is_bounded_to_existing_signals(result) -> None:
    assert result["counterfactual_existing_signals_only"] is True
    assert result["counterfactual_topic_fn_captured"] == 1
    assert result["counterfactual_format_fn_captured"] == 5
    assert result["counterfactual_additional_provider_calls"] == 2
    assert result["counterfactual_new_false_positives"] == 1


def test_stop_rule_and_diagnostic_classification(result) -> None:
    assert result["gate_only_fix_viability"] == "HIGH"
    assert result["dominant_root_cause"] == "MIXED_GATE_AND_UPSTREAM_GAP"
    assert result["recommended_next_step"] == "IMPLEMENT_ONE_BOUNDED_GATE_REFINEMENT"
    assert result["one_gate_refinement_budget"] == 1


def test_no_provider_import_or_call(result) -> None:
    assert result["provider_calls"] == 0
    tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
    imports = [
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert not any("provider" in module.casefold() or "openai" in module.casefold() for module in imports)


def test_expected_labels_remain_frozen() -> None:
    assert hashlib.sha256(diagnostic.EXPECTED_JSON.read_bytes()).hexdigest() == diagnostic.EXPECTED_SHA256


def test_persisted_analysis_contains_no_source_bodies(tmp_path) -> None:
    result = diagnostic.analyze()
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    persisted = path.read_text(encoding="utf-8")
    for case_id in (f"{value:03d}" for value in range(61, 71)):
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in persisted


def test_no_production_files_are_modified_by_scope() -> None:
    assert diagnostic.OUTPUT_JSON.parent == diagnostic.BATCH_ROOT
    assert diagnostic.OUTPUT_MD.parent == diagnostic.BATCH_ROOT
