from pathlib import Path

import pytest

from examples import run_semantic_sufficiency_shadow_consumption as diagnostic


def assessment(candidate, sufficiency, group="TOPIC_LIKE"):
    return {"candidate": candidate, "sufficiency": sufficiency, "candidate_group": group}


@pytest.fixture(scope="module")
def result():
    return diagnostic.analyze()


def decide(items, *, current="CURRENT", dimension="TOPIC", group="TOPIC_LIKE"):
    return diagnostic.shadow_decision(
        dimension=dimension, current_candidate=current,
        assessments=items, candidate_group=group,
    )


def test_topic_consumer_is_shadow_only():
    decision = decide([assessment("ALTERNATIVE", "SUFFICIENT")])
    assert decision["current_candidate"] == "CURRENT"
    assert decision["shadow_candidate"] == "ALTERNATIVE"


def test_format_consumer_is_independent_and_shadow_only():
    decision = decide(
        [assessment("FORMAT_ALT", "SUFFICIENT", "FORMAT_LIKE")],
        dimension="FORMAT", group="FORMAT_LIKE",
    )
    assert decision["current_candidate"] == "CURRENT"
    assert decision["shadow_candidate"] == "FORMAT_ALT"


def test_sufficient_alternative_overrides():
    assert decide([assessment("ALT", "SUFFICIENT")])["decision_reason"] == "SUFFICIENT_ALTERNATIVE_OVERRIDE"


@pytest.mark.parametrize("state", ["PARTIAL", "INSUFFICIENT", "CONFLICTED"])
def test_non_sufficient_alternative_cannot_override(state):
    decision = decide([assessment("ALT", state)])
    assert decision["changed"] is False
    assert decision["decision_reason"] == "ALTERNATIVE_NOT_STRONG_ENOUGH"


def test_multiple_sufficient_candidates_preserve_current():
    decision = decide([assessment("A", "SUFFICIENT"), assessment("B", "SUFFICIENT")])
    assert decision["shadow_candidate"] == "CURRENT"
    assert decision["decision_reason"] == "MULTIPLE_SUFFICIENT_CONFLICT"


def test_current_sufficient_is_preserved():
    decision = decide([assessment("CURRENT", "SUFFICIENT"), assessment("ALT", "PARTIAL")])
    assert decision["shadow_candidate"] == "CURRENT"
    assert decision["decision_reason"] == "CURRENT_ALREADY_SUFFICIENT"


def test_no_assessments_preserves_current():
    assert decide([])["decision_reason"] == "NO_ASSESSMENTS"


def test_expected_labels_are_loaded_after_all_shadow_decisions(monkeypatch):
    events = []
    original_decision = diagnostic.shadow_decision
    original_expectations = diagnostic._expectations

    def tracked_decision(**kwargs):
        events.append("decision")
        return original_decision(**kwargs)

    def tracked_expectations(root):
        events.append("expected")
        return original_expectations(root)

    monkeypatch.setattr(diagnostic, "shadow_decision", tracked_decision)
    monkeypatch.setattr(diagnostic, "_expectations", tracked_expectations)
    diagnostic.analyze()
    assert events.count("decision") == 100
    assert events.index("expected") == 100


def test_topic_metrics_are_complete(result):
    metrics = result["topic_metrics"]
    assert metrics["evaluable_cases"] == 50
    assert metrics["current_topic_correct"] + metrics["topic_unchanged_wrong"] == 50


def test_format_metrics_are_complete(result):
    metrics = result["format_metrics"]
    assert metrics["evaluable_cases"] == 40
    assert metrics["current_format_correct"] + metrics["format_unchanged_wrong"] == 40


def test_override_precision_and_wrong_to_wrong_metrics():
    cases = [
        {"batch": "x", "id": "1", "current_topic": "A", "shadow_topic": "B", "expected_topic": "B"},
        {"batch": "x", "id": "2", "current_topic": "A", "shadow_topic": "B", "expected_topic": "C"},
    ]
    metrics = diagnostic._dimension_metrics(cases, "topic")
    assert metrics["topic_override_precision"] == 50.0
    assert metrics["topic_wrong_to_wrong_overrides"] == 1


def test_no_actual_classification_or_confidence_mutation(result):
    assert result["mutation_audit"] == {
        "actual_topic_mutated": False,
        "actual_format_mutated": False,
        "actual_reader_intent_mutated": False,
        "actual_confidence_mutated": False,
        "gate_mutated": False,
    }


def test_no_provider_calls(result):
    assert result["provider_calls"] == 0


def test_batch_statuses_are_explicit(result):
    assert result["batch_metrics"]["batch_01"]["scientific_status"] == "HISTORICAL_REGRESSION_CORPUS"
    assert result["batch_metrics"]["batch_05"]["scientific_status"] == "SEMANTIC_ADJUDICATION_DEVELOPMENT_CORPUS"
    assert result["batch_metrics"]["batch_06"]["scientific_status"] == "DIAGNOSTIC_DEVELOPMENT_SET"


def test_batch_07_remains_required(result):
    assert result["batch_07_required"] is True


def test_no_source_bodies_are_persisted(result):
    forbidden = {"source", "source_body", "body", "text", "raw_source"}
    assert all(not forbidden.intersection(case) for case in result["case_inventory"])


def test_only_expected_output_paths_are_declared():
    assert diagnostic.OUTPUT_JSON == diagnostic.BENCHMARK_ROOT / "semantic_sufficiency_shadow_consumption.json"
    assert diagnostic.OUTPUT_MD == diagnostic.BENCHMARK_ROOT / "semantic_sufficiency_shadow_consumption.md"


def test_suppression_counts_cases_not_assessments(result):
    suppression = result["override_suppression"]
    assert all(isinstance(value, int) and 0 <= value <= 50 for value in suppression.values())


def test_decision_reasons_do_not_include_correctness():
    source = Path(diagnostic.__file__).read_text(encoding="utf-8")
    policy = source[source.index("def shadow_decision"):source.index("def _expectations")]
    assert "expected" not in policy.lower()

