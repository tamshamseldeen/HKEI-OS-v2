"""Tests for the offline Batch 06 semantic activation-gap diagnostic."""

import inspect
import json
from pathlib import Path
import subprocess

import pytest

import examples.run_batch_06_semantic_activation_gap_analysis as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source


@pytest.fixture(scope="module")
def analysis() -> dict:
    return diagnostic.analyze()


def test_exact_cases_and_zero_delta_are_reproduced(analysis: dict) -> None:
    assert analysis["cases_analyzed"] == list(diagnostic.CASE_IDS)
    assert len(analysis["cases"]) == 10
    assert analysis["zero_delta_reproduced"] == {
        "semantic_relationships": [3, 3],
        "primary_domains": [1, 1],
        "semantic_format_support": [0, 0],
    }


def test_activation_stages_and_component_inventory_are_bounded(
    analysis: dict,
) -> None:
    assert set(analysis["activation_stage_by_case"].values()) <= set(diagnostic.STAGES)
    assert sum(analysis["activation_stage_counts"].values()) == 10
    assert set(analysis["component_role_coverage_by_case"]) == set(diagnostic.CASE_IDS)
    assert all(
        item["present_roles"] and item["missing_roles_needed_for_expected_composition"]
        for item in analysis["component_role_coverage_by_case"].values()
    )


def test_relationship_candidates_locality_and_format_zero_are_classified(
    analysis: dict,
) -> None:
    assert set(analysis["relationship_candidate_findings"]) == set(diagnostic.CASE_IDS)
    assert all(
        finding["classification"] in diagnostic.LOCALITIES
        for finding in analysis["locality_findings"].values()
    )
    assert set(analysis["semantic_format_support_zero_causes"]) == set(diagnostic.CASE_IDS)
    assert all(analysis["semantic_format_support_zero_causes"].values())


def test_previous_false_negatives_receive_deep_audit(analysis: dict) -> None:
    assert set(analysis["format_gate_fn_activation_breaks"]) == {"054", "056", "059"}
    assert all(
        not finding["semantic_format_support_emitted"]
        and not finding["format_confidence_changed"]
        and not finding["new_gate_signal_received"]
        for finding in analysis["format_gate_fn_activation_breaks"].values()
    )


def test_synthetic_realism_metrics_use_end_to_end_raw_text(analysis: dict) -> None:
    metrics = analysis["test_realism_metrics"]
    assert metrics == {
        "synthetic_tests_using_raw_text": 25,
        "synthetic_tests_using_prebuilt_components": 0,
        "synthetic_tests_using_prebuilt_contextual_evidence": 0,
        "synthetic_tests_directly_calling_semantic_relationship_logic": 0,
        "synthetic_tests_bypassing_extraction": 0,
        "path_classification": "SAME_PATH",
        "finding": "End-to-end path was exercised, but synthetic vocabulary matched exact generic regex forms more directly than Arabic corpus expression.",
    }
    assert analysis["dominant_root_cause"] == "B_REAL_TEXT_COMPONENT_EXTRACTION_GAP"
    assert analysis["recommended_next_step"] == "IMPROVE_GENERIC_COMPONENT_EXTRACTION"


def test_integrity_offline_behavior_and_no_production_change(analysis: dict) -> None:
    assert analysis["provider_calls"] == 0
    assert analysis["expected_labels_sha256"] == diagnostic.EXPECTED_SHA256
    assert analysis["raw_source_integrity"] is True
    changed = subprocess.run(
        ["git", "diff", "--name-only", "e6a1324"],
        cwd=diagnostic.PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert not any(path.startswith("src/") for path in changed)
    module = inspect.getsource(diagnostic)
    assert "OpenAI(" not in module
    assert "responses.create" not in module
    assert "provider.adjudicate" not in module


def test_outputs_do_not_persist_source_bodies(analysis: dict) -> None:
    rendered = diagnostic.render_json(analysis) + diagnostic.render_markdown(analysis)
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in rendered
    assert all(
        "matched_text" not in item
        for case in analysis["cases"]
        for item in case["contextual_evidence_inventory"]
    )


def test_persisted_outputs_are_deterministic_when_present(analysis: dict) -> None:
    if diagnostic.OUTPUT_JSON.exists():
        assert json.loads(diagnostic.OUTPUT_JSON.read_text(encoding="utf-8")) == analysis
        assert diagnostic.OUTPUT_MD.read_text(encoding="utf-8") == diagnostic.render_markdown(analysis)
