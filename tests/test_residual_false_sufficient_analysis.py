"""Tests for the offline residual false-sufficiency forensic analysis."""

import inspect
import json
from pathlib import Path
import socket

import pytest

from examples import run_residual_false_sufficient_analysis as diagnostic


@pytest.fixture(scope="module")
def result() -> dict:
    return diagnostic.analyze()


def test_exactly_one_target_is_derived_from_persisted_assessments(result: dict) -> None:
    assert result["false_sufficient_count"] == 1
    persisted = json.loads(diagnostic.SHADOW_PATH.read_text(encoding="utf-8"))
    target = result["target_assessment"]
    assert any(
        case["batch"] == target["batch"] and case["id"] == target["case_id"]
        and any(item["candidate"] == target["candidate"] for item in case["assessments"])
        for case in persisted["case_inventory"]
    )
    assert target["expected_label"] != target["candidate"]
    assert target["sufficiency"] == "SUFFICIENT"


def test_target_identifier_is_not_hard_coded() -> None:
    source = inspect.getsource(diagnostic)
    result = diagnostic.analyze()
    assert f'"{result["target_assessment"]["case_id"]}"' not in source


def test_evidence_independence_and_direction_classes_are_valid(result: dict) -> None:
    independence = {"INDEPENDENT", "DERIVED_FROM_SAME_SIGNAL", "SEMANTIC_DUPLICATE", "HIERARCHICAL_DUPLICATE", "UNKNOWN"}
    assert {item["classification"] for item in result["evidence_independence_analysis"]["pair_classifications"]} <= independence
    direction = {"CORRECT_SUPPORT", "OVERGENERALIZED_SUPPORT", "MISDIRECTED_SUPPORT", "NEUTRAL_MISREAD_AS_SUPPORT", "SHOULD_BE_SUPPRESSION"}
    assert {item["classification"] for item in result["directionality_analysis"]} <= direction


def test_competition_and_structural_findings_are_restricted(result: dict) -> None:
    assert result["competition_analysis"]["classification"] in {
        "COMPETITION_CORRECT", "COMPETITOR_NOT_DETECTED",
        "COMPETITOR_DETECTED_BUT_UNDERWEIGHTED", "EXPECTED_CANDIDATE_MISSING",
    }
    assert result["structural_completeness"]["classification"] in {
        "STRUCTURE_COMPLETE", "STRUCTURE_PARTIAL", "STRUCTURE_INCOMPLETE", "STRUCTURE_MISIDENTIFIED",
    }


def test_sufficiency_prerequisite_audit_is_complete(result: dict) -> None:
    assert set(result["sufficiency_prerequisite_audit"]) == {
        "SUPPORT_DIRECTION", "STRONG_STRENGTH", "STRUCTURAL_COMPLETENESS",
        "CENTRAL_ROLE", "NO_MATERIAL_SUPPRESSION", "NO_MEANINGFUL_COMPETITOR",
        "INDEPENDENT_EVIDENCE", "COHERENT_EVIDENCE",
    }
    assert set(result["sufficiency_prerequisite_audit"].values()) <= {"PASS", "FAIL", "NOT_APPLICABLE"}
    assert "FAIL" in result["sufficiency_prerequisite_audit"].values()


def test_expected_label_is_read_only_and_controls_are_deterministic(result: dict) -> None:
    expected_path = diagnostic.PROJECT_ROOT / "benchmark" / result["target_assessment"]["batch"] / "expected.json"
    before = expected_path.read_bytes()
    repeated = diagnostic.analyze()
    assert expected_path.read_bytes() == before
    assert result["true_sufficient_controls"] == repeated["true_sufficient_controls"]
    assert len(result["true_sufficient_controls"]) == 3


def test_root_cause_and_fix_classes_are_restricted(result: dict) -> None:
    assert result["primary_failure_class"] in {
        "DUPLICATE_INDEPENDENCE_FAILURE", "ROLE_BASIS_OVERCLAIM",
        "DIRECTIONAL_MAPPING_OVERGENERALIZATION", "MISSING_SUPPRESSION",
        "MISSING_COMPETITOR", "STRUCTURAL_COMPLETENESS_FALSE_POSITIVE",
        "STRENGTH_CALIBRATION_ERROR", "SUFFICIENCY_RULE_ERROR",
        "ONTOLOGY_BOUNDARY_AMBIGUITY", "EXPECTED_LABEL_AMBIGUITY", "UNKNOWN",
    }
    assert result["generic_counterfactual_fix"] in {
        "TIGHTEN_EVIDENCE_INDEPENDENCE", "TIGHTEN_ROLE_BASIS_REQUIREMENT",
        "TIGHTEN_DIRECTIONAL_MAPPING", "REQUIRE_STRONGER_STRUCTURAL_COMPLETENESS",
        "PROPAGATE_SUPPRESSION", "STRENGTHEN_COMPETITOR_DETECTION",
        "TIGHTEN_SUFFICIENCY_FINAL_CHECK", "REFINE_ONTOLOGY_BOUNDARY",
        "NO_SAFE_GENERIC_FIX_IDENTIFIED",
    }


def test_no_provider_network_or_production_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network")))
    assert diagnostic.analyze()["provider_calls"] == 0
    assert "src/" not in inspect.getsource(diagnostic).split("PARITY_PATH", 1)[0]
    assert "OpenAI(" not in inspect.getsource(diagnostic)


def test_outputs_persist_no_source_body_or_secrets(result: dict) -> None:
    rendered = json.dumps(result, ensure_ascii=False)
    assert "OPENAI_API_KEY" not in rendered
    assert "subject_text" not in rendered
    assert "object_text" not in rendered
    assert result["assessment_path"]["normalized_evidence"]["raw_text_persisted"] is False
    assert Path(diagnostic.OUTPUT_JSON).exists()
    assert Path(diagnostic.OUTPUT_MD).exists()
