"""Tests for the offline pre-Batch-08 test-health audit."""

import ast
import hashlib
import json
from pathlib import Path

from examples import run_test_health_before_batch_08 as audit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = tuple(f"{value:03d}" for value in range(71, 81))


def _result() -> dict:
    return audit.analyze()


def test_current_suite_problem_count_is_reproduced() -> None:
    assert _result()["suite_counts"] == {"passed": 2008, "failed": 11, "errors": 9, "skipped": 9}


def test_all_failures_and_setup_errors_are_classified() -> None:
    issues = _result()["issues"]
    assert len(issues) == 20
    assert sum(item["phase"] == "SETUP" for item in issues) == 9
    assert all(item["classification"] for item in issues)


def test_shared_setup_root_cause_is_computed() -> None:
    result = _result()
    assert result["setup_error_root_cause"] == "DIAGNOSTIC_DEPENDENCY_ORDER"
    assert result["setup_error_shared_count"] == 9
    assert result["setup_error_independent_count"] == 0


def test_regression_counts_are_deterministic() -> None:
    result = _result()
    assert result["pre_existing_failure_count"] == 9
    assert result["stale_diagnostic_count"] == 11
    assert result["environment_issue_count"] == 0
    assert result["new_regression_count"] == 0
    assert result["unknown_count"] == 0


def test_hkei_183_and_hkei_184_correlations_are_audited() -> None:
    result = _result()
    assert result["hkei_183_correlation"]["production_regressions"] == 0
    assert result["hkei_183_correlation"]["diagnostic_contract_drift_issues"] == 11
    assert result["hkei_184_correlation"]["registration_regressions"] == 0
    assert result["hkei_184_correlation"]["test_discovery_issues"] == 0


def test_batch_08_integrity_is_unchanged() -> None:
    integrity = _result()["batch_08_integrity"]
    assert tuple(integrity["case_ids"]) == EXPECTED_IDS
    assert integrity["raw_sha256"] == audit.RAW_SHA256
    assert integrity["raw_sha_matches"] is True
    assert integrity["expected_labels_frozen"] is True
    assert integrity["expected_case_count"] == 10
    assert integrity["scientific_status"] == "UNTOUCHED_PREREGISTERED_HOLDOUT"
    assert integrity["validation_status"] == "NOT_RUN"
    assert integrity["provider_calls"] == 0


def test_no_provider_or_prediction_execution_modules_are_imported() -> None:
    tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    forbidden = ("openai", "provider", "classifier", "semantic_engine", "assessor", "gate", "workflow")
    assert not any(term in name.casefold() for name in imports for term in forbidden)
    assert _result()["prediction_execution"] is False
    assert _result()["provider_calls"] == 0


def test_audit_writes_no_production_paths() -> None:
    assert audit.OUTPUT_JSON.parent == PROJECT_ROOT / "benchmark"
    assert audit.OUTPUT_MD.parent == PROJECT_ROOT / "benchmark"
    source = Path(audit.__file__).read_text(encoding="utf-8")
    assert "src/" not in source


def test_no_source_bodies_are_persisted() -> None:
    serialized = json.dumps(_result(), ensure_ascii=False)
    for case_id in EXPECTED_IDS:
        source = (audit.BATCH_ROOT / case_id / "source.md").read_text(encoding="utf-8")
        body = source.split("\n# Body\n", 1)[1].split("\n# Metadata\n", 1)[0].strip()
        assert body not in serialized


def test_safety_and_recommendation_are_bounded_to_diagnostic_fixes() -> None:
    result = _result()
    assert result["live_evaluation_safety"] == "SAFE_AFTER_DIAGNOSTIC_TEST_FIX_ONLY"
    assert result["recommended_next_step"] == "FIX_DIAGNOSTIC_TESTS_ONLY"
    assert hashlib.sha256(audit.RAW_SOURCE.read_bytes()).hexdigest() == audit.RAW_SHA256
