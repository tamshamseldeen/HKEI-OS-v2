"""Tests for the offline cross-batch candidate sufficiency parity audit."""

import inspect
import json
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples import run_semantic_candidate_assessment_parity_audit as audit


@pytest.fixture(scope="module")
def result() -> dict:
    return audit.analyze()


def test_audit_is_offline_and_does_not_modify_production() -> None:
    source = inspect.getsource(audit)
    assert "OpenAI(" not in source
    assert "responses.create" not in source
    assert "src/" not in source.split("OUTPUT_JSON", 1)[0]


def test_provider_network_is_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "socket", Mock(side_effect=AssertionError("network")))
    assert audit.analyze()["provider_calls"] == 0


def test_expected_labels_are_joined_after_assessments(monkeypatch: pytest.MonkeyPatch) -> None:
    from examples import run_semantic_candidate_assessment_shadow as shadow
    events: list[str] = []
    original = shadow._expected
    monkeypatch.setattr(shadow, "_expected", lambda path: (events.append("truth") or original(path)))
    assessor = Mock()
    from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor
    real = DeterministicSemanticCandidateAssessor()
    assessor.assess.side_effect = lambda **kwargs: (events.append("assessment") or real.assess(**kwargs))
    shadow.analyze(assessor=assessor)
    assert events.index("truth") > max(i for i, value in enumerate(events) if value == "assessment")


def test_batch_status_and_global_counts(result: dict) -> None:
    assert result["cases_analyzed"] == 41
    assert result["assessments_analyzed"] == 109
    assert result["batch_metrics"]["batch_06"]["scientific_status"] == "DIAGNOSTIC_DEVELOPMENT_SET"
    assert result["batch_metrics"]["batch_05"]["scientific_status"] == "SEMANTIC_ADJUDICATION_DEVELOPMENT_CORPUS"
    assert all(result["batch_metrics"][batch]["scientific_status"] == "HISTORICAL_REGRESSION_CORPUS" for batch in ("batch_01", "batch_02", "batch_03"))


def test_sufficiency_selectivity_metrics(result: dict) -> None:
    assert result["true_sufficient_count"] == 8
    assert result["false_sufficient_count"] == 0
    assert result["false_sufficiency_rate"] == 0.0
    assert result["sufficient_precision"] == 100.0
    assert result["correct_sufficient_preservation_rate"] == pytest.approx(85.71428571428571)


def test_format_parity_and_topic_role_safety(result: dict) -> None:
    assert set(result["format_candidate_parity"]) == {"ANALYSIS", "GUIDE", "RESULT_REPORT", "SERVICE", "STANDARD_NEWS", "TREND_UPDATE"}
    assert result["format_candidate_parity"]["STANDARD_NEWS"]["sufficient_count"] == 2
    assert result["topic_role_safety"] == {"AUTHORITY": 0, "ACTOR": 0, "METHOD": 0}


def test_competition_duplicate_and_counterfactual_metrics(result: dict) -> None:
    assert result["competition_metrics"] == {
        "cases_with_competing_candidates": 21,
        "assessments_with_competitors": 42,
        "conflicted_assessments": 6,
        "cases_where_competition_prevented_sufficient": 21,
    }
    assert result["duplicate_evidence_metrics"]["cases_with_duplicate_evidence_discounting"] == 16
    assert result["duplicate_evidence_metrics"]["duplicate_only_sufficient"] == []
    assert result["counterfactual_gate_metrics"] == {
        "counterfactual_wrong_resolved_count": 0,
        "counterfactual_correct_resolved_count": 8,
        "counterfactual_unresolved_wrong_count": 49,
    }


def test_safety_utility_and_readiness_are_deterministic(result: dict) -> None:
    assert result["safety_utility_classification"] == "SAFE_AND_USEFUL"
    assert result["integration_readiness"] == "REFINE_ASSESSOR_BEFORE_INTEGRATION"
    assert result["historical_pathologies"] == []
    assert result["batch_07_required"] is True


def test_failure_provenance_is_restricted_and_parent_compared() -> None:
    result = audit.failure_provenance()
    assert result["current_failure_count"] == 9
    assert result["parent_failure_count"] == 10
    assert result["parent_comparable_failure_count"] == 9
    assert result["hkei_170_regression_count"] == 0
    assert result["suite_state"] == "KNOWN_PRE_EXISTING_FAILURES_ONLY"
    allowed = {
        "PRE_EXISTING_BASELINE_FAILURE", "HKEI_170_REGRESSION",
        "STALE_HISTORICAL_ASSERTION", "DIAGNOSTIC_ARTIFACT_DRIFT",
        "ENVIRONMENTAL_NONDETERMINISM", "UNKNOWN",
    }
    assert {item["classification"] for item in result["failure_records"]} <= allowed


def test_persisted_outputs_have_no_secret_or_source_payloads(result: dict) -> None:
    rendered = json.dumps(result, ensure_ascii=False)
    assert "OPENAI_API_KEY" not in rendered
    assert "matched_text" not in rendered
    for path in (audit.OUTPUT_JSON, audit.OUTPUT_MD, audit.FAILURE_JSON, audit.FAILURE_MD):
        assert Path(path).exists()
