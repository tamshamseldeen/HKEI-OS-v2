"""Tests for the offline Batch 06 directionality/sufficiency diagnosis."""

import hashlib
from pathlib import Path
import subprocess

import examples.run_batch_06_semantic_directionality_sufficiency_analysis as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIRECTIONS = {
    "CORRECT_DIRECTION", "WRONG_DIRECTION", "OVERGENERALIZED_DIRECTION",
    "AMBIGUOUS_DIRECTION", "IRRELEVANT_DIRECTION",
}
ALLOWED_FAILURES = {
    "DOMAIN_MAPPING_MISSING", "DOMAIN_SIGNAL_WRONG_ROLE", "SUBJECT_NOT_IDENTIFIED",
    "OBJECT_NOT_DOMAIN_BEARING", "AUTHORITY_OVERWEIGHTED", "ACTOR_OVERWEIGHTED",
    "COMPETING_DOMAIN_PRECEDENCE", "RELATIONSHIP_TOO_WEAK",
    "PROMOTION_THRESHOLD_TOO_HIGH", "WRONG_DOMAIN_RELATIONSHIP", "ONTOLOGY_BOUNDARY",
}


def test_exact_cases_current_metrics_and_scientific_status() -> None:
    result = diagnostic.analyze()
    assert result["cases_analyzed"] == list(diagnostic.CASE_IDS)
    assert result["batch_scientific_status"] == "DIAGNOSTIC_DEVELOPMENT_SET"
    assert result["final_generalization_claims_allowed"] is False
    assert result["current_hkei_164_metrics"] == {
        "topic_accuracy": 40.0, "format_accuracy": 40.0,
        "reader_intent_accuracy": 40.0, "full_case_accuracy": 0.0,
        "topic_gate_recall": 83.33333333333334,
        "format_gate_recall": 33.33333333333333,
    }


def test_direction_and_domain_failure_classes_are_restricted() -> None:
    result = diagnostic.analyze()
    assert all(
        entry["direction"] in ALLOWED_DIRECTIONS
        for entries in result["semantic_directionality_by_case"].values()
        for entry in entries
    )
    assert set(result["expected_domain_failure_reasons"].values()) <= ALLOWED_FAILURES


def test_gate_false_negatives_case_055_and_confidence_are_reproduced() -> None:
    result = diagnostic.analyze()
    assert result["format_gate_safety_analysis"]["false_negative_cases"] == ["054", "056", "058", "059"]
    case = result["case_055_gate_safety_analysis"]
    assert case["trigger_signals"] == []
    assert case["safety_break"] == "PARTIAL_SEMANTICS_MARKED_RESOLVED"
    assert all(
        item["classification"] in {
            "JUSTIFIED", "OVERSTATED", "SEMANTICALLY_INFLATED",
            "DETERMINISTICALLY_INFLATED", "MIXED_INFLATION",
        }
        for item in result["confidence_contribution_analysis"].values()
    )


def test_direction_metrics_match_relationship_support_inventory() -> None:
    result = diagnostic.analyze()
    metrics = result["semantic_evidence_direction_metrics"]
    assert metrics == {
        "aligned_with_expected": 7,
        "aligned_with_wrong_prediction": 6,
        "neutral_or_irrelevant": 1,
        "total_directional_items": 14,
        "direction_accuracy": 50.0,
    }
    assert result["primary_domain_sufficiency_counts"] == {
        "STRONG_SUFFICIENCY": 2, "FALSE_SUFFICIENCY": 1,
    }


def test_integrity_offline_behavior_and_no_production_modification() -> None:
    result = diagnostic.analyze()
    assert result["provider_calls"] == 0
    assert result["expected_labels_sha256"] == diagnostic.EXPECTED_SHA256
    assert hashlib.sha256((diagnostic.BATCH_ROOT / "expected.json").read_bytes()).hexdigest() == diagnostic.EXPECTED_SHA256
    assert result["raw_source_integrity"] is True
    changed = subprocess.run(
        ["git", "diff", "--name-only", "0aa21313ce50c5a277fc1b4763c575997dec97c4"],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    assert not any(path.startswith("src/") for path in changed)


def test_rendered_outputs_contain_no_source_bodies() -> None:
    result = diagnostic.analyze()
    rendered = diagnostic.render_json(result) + diagnostic.render_markdown(result)
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in rendered
