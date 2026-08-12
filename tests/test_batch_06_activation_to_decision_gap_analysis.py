"""Tests for the offline Batch 06 activation-to-decision diagnosis."""

import hashlib
import json
from pathlib import Path

from examples.run_batch_06_activation_to_decision_gap_analysis import (
    EXPECTED_SHA256,
    analyze,
    render_json,
    render_markdown,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_06"
ALLOWED_REACHABILITY = {
    "EXPECTED_DOMAIN_NOT_EXTRACTED",
    "EXPECTED_DOMAIN_EXTRACTED_AS_COMPONENT",
    "EXPECTED_DOMAIN_PRESENT_IN_RELATIONSHIP",
    "EXPECTED_DOMAIN_SECONDARY_ONLY",
    "EXPECTED_DOMAIN_PRIMARY_CANDIDATE",
    "EXPECTED_DOMAIN_PRIMARY_BUT_CLASSIFIER_IGNORED",
    "EXPECTED_DOMAIN_BLOCKED_BY_PRECEDENCE",
    "ONTOLOGY_BOUNDARY",
}
ALLOWED_PROMOTION_FAILURES = {
    "RELATIONSHIP_TOO_WEAK", "SUBJECT_ROLE_UNRESOLVED", "ACTOR_DOMINANCE",
    "AUTHORITY_DOMINANCE", "METHOD_DOMINANCE", "COMPETING_DOMAIN_PRECEDENCE",
    "DOMAIN_MAPPING_MISSING", "PROMOTION_THRESHOLD_BLOCK", "OTHER",
}


def _result() -> dict:
    return analyze()


def test_exactly_ten_cases_and_hkei_161_metrics_are_reproduced() -> None:
    result = _result()
    assert result["cases_analyzed"] == [f"{value:03d}" for value in range(51, 61)]
    assert result["hkei_161_metrics"] == {
        "topic_accuracy": 40.0,
        "format_accuracy": 40.0,
        "reader_intent_accuracy": 40.0,
        "full_case_accuracy": 0.0,
        "cases_reaching_semantic_components": 10,
        "cases_with_semantic_relationships": 6,
        "cases_with_primary_semantic_domains": 3,
        "cases_with_semantic_format_support": 3,
        "cases_with_semantic_format_suppression": 3,
        "topic_gate_recall": 83.33333333333334,
        "format_gate_recall": 50.0,
    }


def test_topic_gate_regression_and_topic_funnel_are_identified() -> None:
    result = _result()
    assert set(result["topic_mismatch_analysis"]) == {"051", "053", "054", "055", "056", "060"}
    regression = result["topic_gate_recall_regression"]
    assert regression["case_id"] == "055"
    assert regression["cause"] == "FALSE_PRIMARY_DOMAIN_SUFFICIENCY"
    assert regression["previous_topic_required"] is True
    assert regression["current_topic_required"] is False
    assert set(result["expected_domain_reachability"].values()) <= ALLOWED_REACHABILITY
    assert result["expected_domain_reachability"]["056"] == "EXPECTED_DOMAIN_PRESENT_IN_RELATIONSHIP"
    assert set(result["domain_promotion_failures"].values()) <= ALLOWED_PROMOTION_FAILURES


def test_format_utility_and_false_confidence_are_classified() -> None:
    result = _result()
    assert set(result["format_mismatch_analysis"]) == {"052", "054", "056", "057", "058", "059"}
    assert set(result["semantic_format_support_utility"]) == {"054", "056", "058"}
    assert set(result["semantic_format_support_utility"].values()) <= {
        "A_SUPPORT_TARGETS_EXPECTED_FORMAT", "B_SUPPORT_TARGETS_WRONG_PREDICTED_FORMAT",
        "C_SUPPORT_EXISTS_BUT_CLASSIFIER_IGNORES_IT", "D_SUPPORT_TOO_WEAK",
        "E_SUPPORT_IS_CONTRADICTORY",
    }
    assert result["format_classifier_consumption_findings"]["expected_support_emitted"] == []
    assert result["false_semantic_confidence_count"] == 6
    assert result["false_semantic_confidence_cases"] == ["052", "054", "055", "056", "058", "059"]


def test_intent_dependency_and_provider_isolation() -> None:
    result = _result()
    assert result["reader_intent_dependency"]["direct_intent_failures"] == 0
    assert result["reader_intent_dependency"]["downstream_intent_failures"] == 6
    assert result["provider_calls"] == 0


def test_rendered_artifacts_contain_no_source_bodies_or_provider_payloads() -> None:
    result = _result()
    rendered = render_json(result) + render_markdown(result)
    for case_id in result["cases_analyzed"]:
        source = (BATCH_ROOT / case_id / "source.md").read_text(encoding="utf-8")
        body = source.split("\n# Body\n", 1)[1].split("\n# Metadata\n", 1)[0].strip()
        assert body not in rendered
    forbidden = ("OPENAI_API_KEY", "authorization", "raw_response", "raw_prompt")
    assert not any(term.casefold() in rendered.casefold() for term in forbidden)


def test_expected_labels_and_production_tree_are_unchanged() -> None:
    expected = BATCH_ROOT / "expected.json"
    assert hashlib.sha256(expected.read_bytes()).hexdigest() == EXPECTED_SHA256
    result = _result()
    assert result["expected_labels_sha256"] == EXPECTED_SHA256
    assert result["raw_source_integrity"] is True
    runner = (PROJECT_ROOT / "examples" / "run_batch_06_activation_to_decision_gap_analysis.py").read_text(encoding="utf-8")
    assert "openai" not in runner.casefold()
    assert "src.adjudication" not in runner
    assert "src/" not in runner
