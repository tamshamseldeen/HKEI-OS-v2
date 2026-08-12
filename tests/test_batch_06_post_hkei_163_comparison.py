"""Offline integrity tests for the post-HKEI-163 Batch 06 comparison."""

import hashlib
import json
from pathlib import Path
import subprocess

from examples.run_batch_06_editorial_validation import (
    BATCH_ROOT, CASE_IDS, POST_HKEI_160_JSON, RAW_SHA256,
    analyze_validation, build_post_hkei_163_comparison,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "336e5f4f49f8e75c55751599b679b29501e3713af1f8d5514ec0a46168f6a4d8"


def _comparison() -> dict:
    checkpoint = json.loads(POST_HKEI_160_JSON.read_text(encoding="utf-8"))
    return build_post_hkei_163_comparison(
        checkpoint["baselines"]["HKEI-155"],
        checkpoint["baselines"]["HKEI-158"],
        analyze_validation(),
    )


def test_exact_cases_and_preserved_baselines() -> None:
    comparison = _comparison()
    assert comparison["case_count"] == 10
    assert comparison["current"]["case_ids"] == list(CASE_IDS)
    baseline = comparison["baselines"]["HKEI-161"]
    assert baseline["topic_accuracy"] == baseline["format_accuracy"] == 40.0
    assert baseline["reader_intent_accuracy"] == 40.0
    assert baseline["full_case_accuracy"] == 0.0


def test_reachability_primary_quality_and_format_alignment_are_complete() -> None:
    comparison = _comparison()
    assert set(comparison["expected_domain_reachability"]) == set(comparison["current_topic_mismatches"])
    assert set(comparison["expected_domain_reachability"].values()) <= {
        "NO_SIGNAL", "COMPONENT_ONLY", "RELATIONSHIP_SUPPORT", "SECONDARY_DOMAIN", "PRIMARY_DOMAIN",
    }
    assert all("aligned_with_expected_topic" in value for value in comparison["primary_domain_quality"].values())
    assert set(comparison["format_support_alignment_counts"]) <= {
        "ALIGNED_WITH_EXPECTED", "ALIGNED_WITH_WRONG_PREDICTION", "MIXED", "IRRELEVANT",
    }


def test_confidence_gate_and_tracked_cases_are_consistent() -> None:
    comparison = _comparison()
    current = comparison["current"]
    assert len(comparison["current_false_semantic_confidence_cases"]) <= 10
    assert sum(current[f"topic_gate_{key}"] for key in ("tp", "fp", "tn", "fn")) == 10
    assert sum(current[f"format_gate_{key}"] for key in ("tp", "fp", "tn", "fn")) == 10
    assert comparison["case_055_gate_status"]["expected_topic"] == "WORLD"
    assert set(comparison["previous_fn_tracking"]) == {"054", "056", "059"}


def test_holdout_integrity_provider_isolation_and_no_production_edits() -> None:
    comparison = _comparison()
    assert comparison["provider_calls"] == 0
    assert hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest() == EXPECTED_SHA256
    assert comparison["expected_labels_unchanged"] is True
    raw = PROJECT_ROOT.parent / "benchmark_sources" / "batch_06_raw.txt"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == RAW_SHA256
    assert comparison["raw_source_integrity"] is True
    changed = subprocess.run(
        ["git", "diff", "--name-only", "98346f7f007e70a08d21a8949cdd0ceb066ab9b3"],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    assert not any(path.startswith("src/") for path in changed)
