"""Tests for the post-HKEI-173 integration-readiness audit."""

import inspect
import json
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples import run_semantic_assessor_integration_readiness_audit as audit


@pytest.fixture(scope="module")
def result() -> dict:
    return audit.analyze()


def test_current_hkei_173_metrics_reproduced(result: dict) -> None:
    assert result["current_safety_metrics"] == {
        "true_sufficient_count": 8, "false_sufficient_count": 0,
        "sufficient_precision": 100.0, "false_resolution_rate": 0.0,
        "counterfactual_wrong_resolved_count": 0,
        "counterfactual_correct_resolved_count": 8,
        "authority_dominated_sufficient": 0, "actor_dominated_sufficient": 0,
        "method_dominated_sufficient": 0, "critical_wrong_format_sufficient": 0,
    }


def test_pre_hkei_173_metrics_reproduced_from_git(result: dict) -> None:
    comparison = result["before_after"]
    assert comparison["before_commit"] == audit.BEFORE_COMMIT
    assert comparison["true_sufficient"]["before"] == 13
    assert comparison["false_sufficient"]["before"] == 1
    assert comparison["sufficient_precision"]["before"] == pytest.approx(92.85714285714286)


def test_lost_sufficient_assessments_are_deterministic(result: dict) -> None:
    assert len(result["lost_sufficient_assessments"]) == 6
    assert result["lost_sufficient_counts"] == {
        "true_sufficient": 5, "false_sufficient": 1,
        "unevaluable_sufficient": 0,
    }
    assert all(item["before_sufficiency"] == "SUFFICIENT" and item["after_sufficiency"] != "SUFFICIENT" for item in result["lost_sufficient_assessments"])


def test_downgrade_alignment_and_overcorrection_are_separated(result: dict) -> None:
    alignments = [item["expected_label_alignment"] for item in result["lost_sufficient_assessments"]]
    assert alignments.count("TRUE_SUFFICIENT") == 5
    assert alignments.count("FALSE_SUFFICIENT") == 1
    assert result["overcorrection_findings"]["POSSIBLE_OVERCORRECTION"] == 5
    assert result["overcorrection_findings"]["CLEAR_OVERCORRECTION"] == 0


def test_denominator_differences_are_explicit(result: dict) -> None:
    comparison = result["before_after"]
    assert comparison["true_sufficient"]["denominator"] != comparison["correct_sufficient_preservation"]["denominator"]
    assert comparison["correct_sufficient_preservation"]["before"] == comparison["correct_sufficient_preservation"]["after"]
    assert "fixed older control cohort" in comparison["denominator_explanation"]


def test_readiness_rule_trace_has_one_exact_failure(result: dict) -> None:
    failures = [item for item in result["readiness_decision_trace"] if item["status"] == "FAIL"]
    assert failures == [{
        "condition_name": "READINESS_DERIVED_FROM_OBSERVED_METRICS",
        "required_value": True, "observed_value": False, "status": "FAIL",
    }]


def test_exact_blocker_and_classification(result: dict) -> None:
    assert result["integration_readiness_blocker"] == "RULE_NOT_UPDATED_FOR_NEW_METRICS"
    assert result["blocker_class"] == "DIAGNOSTIC_RULE_DRIFT"
    assert result["persisted_integration_readiness"] == "REFINE_ASSESSOR_BEFORE_INTEGRATION"


def test_safe_and_useful_consistency_is_evaluated(result: dict) -> None:
    assert result["safe_and_useful_consistency"]["classification"] == "INCONSISTENT"
    assert "unconditional literal" in result["safe_and_useful_consistency"]["explanation"]


def test_shadow_and_production_readiness_are_separate(result: dict) -> None:
    assert "NO_OUTPUT_MUTATION" in result["shadow_readiness_requirements"]
    assert "NO_GATE_MUTATION" in result["shadow_readiness_requirements"]
    production = result["production_readiness_requirements"]
    assert set(production) == {"classifier_consumption", "confidence_influence", "gate_consumption", "resolver_usage"}
    assert all(production.values())


def test_shadow_risk_value_and_recommendation(result: dict) -> None:
    assert result["shadow_consumption_risk"]["classification"] == "LOW"
    assert result["shadow_consumption_value"]["classification"] == "HIGH_VALUE"
    assert result["final_recommendation"] == "FIX_READINESS_RULE_DRIFT"


def test_stop_refinement_and_batch_status_are_deterministic(result: dict) -> None:
    assert result["stop_assessor_refinement_now"] == "YES"
    assert result["batch_06_status"] == "DIAGNOSTIC_DEVELOPMENT_SET"
    assert result["batch_07_required"] is True


def test_no_provider_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "socket", Mock(side_effect=AssertionError("network")))
    assert audit.analyze()["provider_calls"] == 0
    source = inspect.getsource(audit)
    assert "OpenAI(" not in source
    assert "responses.create" not in source


def test_no_production_modification_path_in_audit() -> None:
    source = inspect.getsource(audit)
    assert "write_text" in source
    assert "src/" not in source


def test_outputs_persist_no_source_bodies_or_secrets(result: dict) -> None:
    rendered = json.dumps(result, ensure_ascii=False)
    assert "OPENAI_API_KEY" not in rendered
    assert "matched_text" not in rendered
    assert "source_body" not in rendered
    assert Path(audit.OUTPUT_JSON).exists()
    assert Path(audit.OUTPUT_MD).exists()


def test_lost_records_store_only_symbolic_provenance(result: dict) -> None:
    allowed = {
        "batch", "case", "candidate", "candidate_group", "expected_label",
        "expected_label_alignment", "before_sufficiency", "after_sufficiency",
        "reason_for_downgrade", "warning_changes", "competitor_changes",
        "duplicate_evidence_changes", "overcorrection_classification",
    }
    assert all(set(item) == allowed for item in result["lost_sufficient_assessments"])
