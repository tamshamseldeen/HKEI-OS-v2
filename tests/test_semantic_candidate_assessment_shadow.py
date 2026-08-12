"""Tests for shadow-only semantic candidate assessment diagnostics."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import examples.run_semantic_candidate_assessment_shadow as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from src.semantics.deterministic_semantic_candidate_assessor import (
    DeterministicSemanticCandidateAssessor,
)


@pytest.fixture(scope="module")
def analysis() -> dict:
    return diagnostic.analyze()


def test_assessor_is_shadow_only_and_mutates_no_pipeline_decisions(analysis: dict) -> None:
    persisted = json.loads(
        (diagnostic.BENCHMARK_ROOT / "batch_06/editorial_validation.json").read_text(encoding="utf-8")
    )
    current = {case["id"]: case for case in persisted["cases"]}
    shadow = {
        case["id"]: case for case in analysis["case_inventory"]
        if case["batch"] == "batch_06"
    }
    for case_id, case in shadow.items():
        assert case["topic"] == current[case_id]["predicted_topic"]
        assert case["format"] == current[case_id]["predicted_format"]
        assert case["intent"] == current[case_id]["predicted_reader_intent"]
        assert case["gate_scope"] == current[case_id]["gate_scope"]
    assert analysis["provider_calls"] == 0


def test_expected_labels_are_loaded_only_after_all_assessments(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    real = DeterministicSemanticCandidateAssessor()
    assessor = Mock(wraps=real)
    assessor.assess.side_effect = lambda **kwargs: (
        events.append("assess") or real.assess(**kwargs)
    )
    original = diagnostic._expected
    monkeypatch.setattr(
        diagnostic, "_expected",
        lambda path: (events.append("truth") or original(path)),
    )
    diagnostic.analyze(assessor=assessor)
    assert events.count("assess") == 50
    assert events.index("truth") > max(
        index for index, event in enumerate(events) if event == "assess"
    )


def test_distributions_are_exact_and_batches_are_included(analysis: dict) -> None:
    assert analysis["cases_analyzed"] == 41
    assert analysis["sufficiency_distribution"] == {
        "INSUFFICIENT": 59, "PARTIAL": 28, "SUFFICIENT": 18, "CONFLICTED": 6,
    }
    assert analysis["strength_distribution"] == {
        "WEAK": 59, "MODERATE": 29, "STRONG": 23,
    }
    assert analysis["direction_distribution"] == {
        "SUPPORT": 77, "SUPPRESS": 28, "NEUTRAL": 0, "CONFLICTING": 6,
    }
    assert set(analysis["batch_distribution"]) == set(diagnostic.BATCHES)


def test_false_sufficiency_quality_metrics_are_exact(analysis: dict) -> None:
    assert analysis["sufficiency_quality_metrics"] == {
        "true_sufficient_count": 1,
        "false_sufficient_count": 2,
        "safe_wrong_partial_count": 17,
        "expected_candidate_sufficient_count": 0,
        "expected_candidate_partial_count": 1,
        "expected_candidate_missing_count": 7,
        "false_sufficiency_rate": 66.66666666666666,
    }
    assert analysis["diagnostic_quality"] == "WEAK"
    assert analysis["recommended_next_step"] == "REFINE_FORMAT_DIRECTIONAL_ASSESSMENT"


def test_case_055_and_topic_counterfactual_are_deterministic(analysis: dict) -> None:
    case = analysis["case_055_safety"]
    assert case["wrong_semantic_candidate"] == "BUSINESS"
    assert case["wrong_candidate_sufficiency"] == "INSUFFICIENT"
    assert case["expected_sufficiency"] == "NONE"
    assert case["counterfactual_unresolved"] is True
    assert analysis["counterfactual_topic_unresolved"]["055"] is True


def test_critical_format_safety_and_counterfactual_are_exact(analysis: dict) -> None:
    critical = analysis["critical_format_case_safety"]
    assert critical["054"]["predicted_sufficiency"] == "PARTIAL"
    assert critical["056"]["predicted_sufficiency"] == "SUFFICIENT"
    assert critical["058"]["predicted_sufficiency"] == "SUFFICIENT"
    assert critical["059"]["expected_sufficiency"] == "NONE"
    assert analysis["counterfactual_format_unresolved"] == {
        "054": True, "056": False, "058": False, "059": True,
    }


def test_confidence_duplicate_role_and_competition_audits(analysis: dict) -> None:
    assert analysis["confidence_sufficiency_divergence"] == ["054:FORMAT"]
    assert analysis["duplicate_evidence_findings"] == [
        "batch_01:001", "batch_01:003", "batch_02:013", "batch_02:014",
        "batch_02:015", "batch_02:018", "batch_03:029", "batch_05:049",
    ]
    dominated = analysis["authority_actor_method_findings"]["dominated_sufficient"]
    assert dominated == {"AUTHORITY": [], "ACTOR": [], "METHOD": []}
    competition = analysis["competition_findings"]
    assert len(competition["cases_with_competing_candidates"]) == 20
    assert len(competition["conflicted_assessments"]) == 6


def test_historical_corpora_are_included_without_dominated_sufficiency(analysis: dict) -> None:
    safety = analysis["historical_corpus_safety"]
    assert safety["cases"] == 32
    assert safety["assessments"] == 81
    assert safety["dominated_sufficient_count"] == 0
    assert safety["conflicted_count"] < safety["assessments"]
    assert safety["insufficient_count"] < safety["assessments"]


def test_outputs_persist_no_source_bodies(analysis: dict) -> None:
    rendered = diagnostic.render_json(analysis) + diagnostic.render_markdown(analysis)
    for batch in diagnostic.BATCHES:
        root = diagnostic.BENCHMARK_ROOT / batch
        for item in diagnostic.read_manifest(root):
            if batch == "batch_01":
                source = diagnostic.parse_batch_01_source(root / item["source_file"])
            else:
                source = parse_source(root / item["source_file"])
            assert source.body not in rendered
    assert "matched_text" not in rendered
