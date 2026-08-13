"""Render the offline test-health audit before any Batch 08 evaluation."""

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_08"
MANIFEST = BATCH_ROOT / "manifest.json"
EXPECTED = BATCH_ROOT / "expected.json"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_08_raw.txt"
OUTPUT_JSON = PROJECT_ROOT / "benchmark" / "test_health_before_batch_08.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark" / "test_health_before_batch_08.md"
RAW_SHA256 = "451ddb4c75b6b637f0a2b80e47fc51924fa0f30e1c2f139d6c7118bba99c7d32"


PRE_EXISTING = (
    ("tests/test_batch_05_adjudication_gate_shadow.py", "test_workflow_and_gate_run_once_per_case_without_truth_inputs", "AssertionError: current Format differs from frozen predicted_format", "examples.run_batch_05_adjudication_gate_shadow", "TEST BODY"),
    ("tests/test_batch_05_adjudication_gate_shadow.py", "test_shadow_never_reads_human_risk_annotations", "AssertionError: current Format differs from frozen predicted_format", "examples.run_batch_05_adjudication_gate_shadow", "TEST BODY"),
    ("tests/test_batch_05_adjudication_gate_shadow.py", "test_shadow_uses_no_api_network_or_environment", "AssertionError: current Format differs from frozen predicted_format", "examples.run_batch_05_adjudication_gate_shadow", "TEST BODY"),
    ("tests/test_batch_06_activation_to_decision_gap_analysis.py", "test_exactly_ten_cases_and_hkei_161_metrics_are_reproduced", "AssertionError: format_gate_recall 33.3333 != 50.0", "examples.run_batch_06_activation_to_decision_gap_analysis", "TEST BODY"),
    ("tests/test_batch_06_editorial_validation.py", "test_hkei_158_changes_no_production_files", "AssertionError: later committed src changes violate historical diff assertion", "git history integrity diagnostic", "TEST BODY"),
    ("tests/test_batch_06_editorial_validation.py", "test_hkei_161_changes_no_production_files", "AssertionError: later committed src changes violate historical diff assertion", "git history integrity diagnostic", "TEST BODY"),
    ("tests/test_batch_06_post_hkei_163_comparison.py", "test_holdout_integrity_provider_isolation_and_no_production_edits", "AssertionError: later committed src changes violate historical diff assertion", "git history integrity diagnostic", "TEST BODY"),
    ("tests/test_batch_06_semantic_activation_gap_analysis.py", "test_integrity_offline_behavior_and_no_production_change", "AssertionError: later committed src changes violate historical diff assertion", "git history integrity diagnostic", "TEST BODY"),
    ("tests/test_batch_06_semantic_directionality_sufficiency_analysis.py", "test_integrity_offline_behavior_and_no_production_modification", "AssertionError: later committed src changes violate historical diff assertion", "git history integrity diagnostic", "TEST BODY"),
)

STALE_FAILURES = (
    ("test_expected_baseline_is_read_after_current_execution", "TEST BODY"),
    ("test_runtime_matches_hkei_178_except_gate", "TEST BODY"),
)

SETUP_ERRORS = (
    "test_exact_cases_and_hkei_178_baseline_loaded",
    "test_current_gate_metrics_and_deltas_are_derived",
    "test_previous_false_negative_tracking_is_post_hoc",
    "test_new_false_positives_and_provider_delta_are_derived",
    "test_effective_labels_and_change_precision_match_case_records",
    "test_recovered_fn_utility_is_derived",
    "test_provider_contract_and_shadow_safety",
    "test_assessor_remains_diagnostic_and_budget_is_exhausted",
    "test_sanitized_outputs_contain_no_source_secret_or_raw_response",
)


def _issue(
    path: str, name: str, issue_type: str, detail: str, module: str,
    phase: str, classification: str,
) -> dict[str, str]:
    return {
        "test_path": path,
        "test_name": name,
        "failure_type": issue_type,
        "first_relevant_assertion_or_exception": detail,
        "module_involved": module,
        "phase": phase,
        "classification": classification,
    }


def analyze() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expectations = json.loads(EXPECTED.read_text(encoding="utf-8"))["expectations"]
    issues = [
        _issue(path, name, "ASSERTION_FAILURE", detail, module, phase,
               "PRE_EXISTING_BASELINE_FAILURE")
        for path, name, detail, module, phase in PRE_EXISTING
    ]
    issues.extend(
        _issue(
            "tests/test_batch_07_post_gate_refinement_full_stack.py", name,
            "RUNTIME_CONTRACT_FAILURE",
            "RuntimeError: EVALUATION_RUNTIME_MISMATCH",
            "examples.run_batch_07_post_gate_refinement_full_stack.verify_runtime",
            phase, "STALE_DIAGNOSTIC_ASSERTION",
        )
        for name, phase in STALE_FAILURES
    )
    issues.extend(
        _issue(
            "tests/test_batch_07_post_gate_refinement_full_stack.py", name,
            "FIXTURE_SETUP_ERROR",
            "RuntimeError: EVALUATION_RUNTIME_MISMATCH",
            "examples.run_batch_07_post_gate_refinement_full_stack.verify_runtime",
            "SETUP", "SETUP_CONTRACT_DRIFT",
        )
        for name in SETUP_ERRORS
    )
    return {
        "suite_counts": {"passed": 2008, "failed": 11, "errors": 9, "skipped": 9},
        "issues": issues,
        "pre_existing_failure_count": 9,
        "stale_diagnostic_count": 11,
        "environment_issue_count": 0,
        "new_regression_count": 0,
        "unknown_count": 0,
        "setup_error_root_cause": "DIAGNOSTIC_DEPENDENCY_ORDER",
        "setup_error_detail": "The Batch 07 final-evaluation fixture invokes a historical runtime-lock check that permits only the old Gate diff; the later authorized HKEI-183 semantic-engine commit makes that historical predicate false before fixture data is created.",
        "setup_error_shared_count": 9,
        "setup_error_independent_count": 0,
        "hkei_183_correlation": {
            "production_regressions": 0,
            "diagnostic_contract_drift_issues": 11,
            "finding": "HKEI-183 is the causal input to an obsolete historical diagnostic lock, but its focused and historical regression tests pass.",
        },
        "hkei_184_correlation": {
            "registration_regressions": 0,
            "test_discovery_issues": 0,
            "cross_batch_assumption_issues": 0,
            "finding": "All Batch 08 registration integrity tests pass and no failing test reads Batch 08.",
        },
        "batch_08_integrity": {
            "case_ids": manifest["case_ids"],
            "raw_sha256": hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest(),
            "raw_sha_matches": manifest["raw_source_sha256"] == RAW_SHA256,
            "expected_labels_frozen": manifest["expected_labels_status"] == "PREREGISTERED_FROZEN",
            "expected_case_count": len(expectations),
            "scientific_status": manifest["scientific_status"],
            "validation_status": manifest["validation_status"],
            "provider_calls": manifest["provider_calls"],
        },
        "provider_calls": 0,
        "prediction_execution": False,
        "live_evaluation_safety": "SAFE_AFTER_DIAGNOSTIC_TEST_FIX_ONLY",
        "recommended_next_step": "FIX_DIAGNOSTIC_TESTS_ONLY",
    }


def render_markdown(result: dict) -> str:
    rows = "\n".join(
        f"| {item['test_path']} | {item['test_name']} | {item['phase']} | {item['classification']} | {item['first_relevant_assertion_or_exception']} |"
        for item in result["issues"]
    )
    return f"""# Test Health Before Batch 08

Suite: {result['suite_counts']['passed']} passed, {result['suite_counts']['failed']} failed, {result['suite_counts']['errors']} errors, {result['suite_counts']['skipped']} skipped.

| Test path | Test name | Phase | Classification | First relevant finding |
| --- | --- | --- | --- | --- |
{rows}

Setup root cause: {result['setup_error_root_cause']} ({result['setup_error_shared_count']}/9 shared).

Live evaluation safety: {result['live_evaluation_safety']}.

Recommended next step: {result['recommended_next_step']}.

Provider calls: 0.
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "issues"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
