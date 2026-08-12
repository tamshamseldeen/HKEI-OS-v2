"""Tests for offline Batch 06 generalization failure analysis."""

import hashlib
import inspect
import json
from pathlib import Path

import pytest

import examples.run_batch_06_generalization_failure_analysis as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source


@pytest.fixture(scope="module")
def analysis() -> dict:
    return json.loads(diagnostic.OUTPUT_JSON.read_text(encoding="utf-8"))


def test_exact_cases_and_hkei_155_metrics_are_reproduced(analysis: dict) -> None:
    assert analysis["cases_analyzed"] == list(diagnostic.CASE_IDS)
    assert len(analysis["cases"]) == 10
    assert analysis["hkei_155_metrics"] == {
        "topic_accuracy": 40.0,
        "format_accuracy": 40.0,
        "reader_intent_accuracy": 40.0,
        "full_case_accuracy": 0.0,
        "topic_gate_recall": 100.0,
        "format_gate_recall": 50.0,
        "projected_provider_call_rate": 90.0,
    }
    assert analysis["provider_calls"] == 0


def test_failure_ids_gate_false_negatives_and_intent_dependency(analysis: dict) -> None:
    cases = analysis["cases"]
    assert [case["id"] for case in cases if not case["topic_match"]] == [
        "051", "053", "054", "055", "056", "060"
    ]
    assert [case["id"] for case in cases if not case["format_match"]] == [
        "052", "054", "056", "057", "058", "059"
    ]
    assert analysis["topic_gate_false_negatives"] == 0
    assert analysis["topic_gate_false_positive_case"] == "058"
    assert analysis["format_gate_false_negative_cases"] == ["054", "056", "059"]
    assert analysis["format_gate_true_positive_cases"] == ["052", "057", "058"]
    assert analysis["direct_intent_failures"] == 0
    assert analysis["downstream_intent_failures"] == 6
    assert analysis["mixed_intent_failures"] == 0


def test_evidence_funnel_and_conversion_metrics(analysis: dict) -> None:
    assert analysis["evidence_stage_counts"] == {
        "NO_CONTEXT": 1,
        "CONTEXT_ONLY": 6,
        "RELATIONSHIP": 2,
        "DOMAIN": 1,
        "FORMAT_SEMANTIC_SUPPORT": 0,
    }
    assert analysis["context_only_cases"] == 6
    assert analysis["semantic_relationship_cases"] == 3
    assert analysis["primary_domain_cases"] == 1
    assert analysis["semantic_format_support_cases"] == 0
    assert analysis["context_to_relationship_conversion_rate"] == pytest.approx(100 / 3)
    assert analysis["relationship_to_primary_domain_conversion_rate"] == pytest.approx(100 / 3)
    assert analysis["context_to_primary_domain_conversion_rate"] == pytest.approx(100 / 9)
    assert analysis["format_semantic_support_rate"] == 0.0
    assert analysis["dominant_failure_category"] == "COMPOSITION_DOMINANT"


def test_annotations_are_loaded_only_after_machine_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    machine_complete = False
    original_machine = diagnostic._machine_analysis
    original_read = diagnostic._read

    def tracked_machine(validation: dict):
        nonlocal machine_complete
        result = original_machine(validation)
        machine_complete = True
        return result

    def guarded_read(path: Path):
        if path.name == "human_risk_annotations.json":
            assert machine_complete
        return original_read(path)

    monkeypatch.setattr(diagnostic, "_machine_analysis", tracked_machine)
    monkeypatch.setattr(diagnostic, "_read", guarded_read)
    result = diagnostic.analyze()
    assert all(case["human_risk_alignment"] != "NOT_YET_READ" for case in result["cases"])


def test_expected_labels_classes_and_owners_are_immutable_and_bounded(analysis: dict) -> None:
    assert hashlib.sha256(diagnostic.EXPECTED_JSON.read_bytes()).hexdigest() == diagnostic.EXPECTED_SHA256
    assert analysis["expected_labels_sha256"] == diagnostic.EXPECTED_SHA256
    for case in analysis["cases"]:
        assert set(case["topic_failure_classes"]) <= diagnostic.TOPIC_CLASSES
        assert set(case["format_failure_classes"]) <= diagnostic.FORMAT_CLASSES
        assert case["primary_architectural_owner"] in diagnostic.OWNERS
        assert case["expected_label_clarity"] in {
            "EXPECTED_LABEL_CLEAR",
            "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
            "EXPECTED_LABEL_REQUIRES_REVIEW",
        }
    assert analysis["expected_label_review_cases"] == 0


def test_outputs_are_source_free_and_module_is_offline(analysis: dict) -> None:
    combined = diagnostic.render_json(analysis) + diagnostic.render_markdown(analysis)
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in combined
    source = inspect.getsource(diagnostic)
    forbidden = (
        "OpenAI(", "responses.create", "provider.adjudicate",
        "ExperimentalSemanticEditorialAnalysisWorkflow",
        "DeterministicSemanticAdjudicationGate",
    )
    assert not any(value in source for value in forbidden)
