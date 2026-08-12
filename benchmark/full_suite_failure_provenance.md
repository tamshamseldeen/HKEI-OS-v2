# Full-Suite Failure Provenance

```json
{
  "current_failure_count": 9,
  "parent_failure_count": 10,
  "parent_comparable_failure_count": 9,
  "parent_environment_specific_extra": "batch_06 manifest absolute raw_source_path differs in isolated /tmp worktree",
  "failure_records": [
    {
      "test_path": "tests/test_batch_05_adjudication_gate_shadow.py",
      "test_name": "test_workflow_and_gate_run_once_per_case_without_truth_inputs",
      "assertion_summary": "frozen predicted_format mismatch",
      "first_failing_assertion": "workflow format equals frozen predicted_format",
      "production_modules_involved": [
        "editorial workflow/classifiers"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_05_adjudication_gate_shadow.py",
      "test_name": "test_shadow_never_reads_human_risk_annotations",
      "assertion_summary": "frozen predicted_format mismatch",
      "first_failing_assertion": "workflow format equals frozen predicted_format",
      "production_modules_involved": [
        "editorial workflow/classifiers"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_05_adjudication_gate_shadow.py",
      "test_name": "test_shadow_uses_no_api_network_or_environment",
      "assertion_summary": "frozen predicted_format mismatch",
      "first_failing_assertion": "workflow format equals frozen predicted_format",
      "production_modules_involved": [
        "editorial workflow/classifiers"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_06_activation_to_decision_gap_analysis.py",
      "test_name": "test_exactly_ten_cases_and_hkei_161_metrics_are_reproduced",
      "assertion_summary": "format_gate_recall 33.33 != frozen 50.0",
      "first_failing_assertion": "hkei_161_metrics equality",
      "production_modules_involved": [
        "historical diagnostic scripts"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "DIAGNOSTIC_ARTIFACT_DRIFT"
    },
    {
      "test_path": "tests/test_batch_06_editorial_validation.py",
      "test_name": "test_hkei_158_changes_no_production_files",
      "assertion_summary": "later committed production files violate historical allowlist",
      "first_failing_assertion": "no unauthorized src path since historical commit",
      "production_modules_involved": [
        "historical diagnostic scripts"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_06_editorial_validation.py",
      "test_name": "test_hkei_161_changes_no_production_files",
      "assertion_summary": "later committed production files violate historical assertion",
      "first_failing_assertion": "no src path changed since historical commit",
      "production_modules_involved": [
        "historical diagnostic scripts"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_06_post_hkei_163_comparison.py",
      "test_name": "test_holdout_integrity_provider_isolation_and_no_production_edits",
      "assertion_summary": "later committed production files violate historical assertion",
      "first_failing_assertion": "no src path changed since historical commit",
      "production_modules_involved": [
        "historical diagnostic scripts"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_06_semantic_activation_gap_analysis.py",
      "test_name": "test_integrity_offline_behavior_and_no_production_change",
      "assertion_summary": "later committed production files violate historical allowlist",
      "first_failing_assertion": "no unauthorized src path since historical commit",
      "production_modules_involved": [
        "historical diagnostic scripts"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    },
    {
      "test_path": "tests/test_batch_06_semantic_directionality_sufficiency_analysis.py",
      "test_name": "test_integrity_offline_behavior_and_no_production_modification",
      "assertion_summary": "later committed production files violate historical assertion",
      "first_failing_assertion": "no src path changed since historical commit",
      "production_modules_involved": [
        "historical diagnostic scripts"
      ],
      "related_to_hkei_170_files": false,
      "parent_result": "FAILED",
      "current_result": "FAILED",
      "classification": "STALE_HISTORICAL_ASSERTION"
    }
  ],
  "classification_counts": {
    "STALE_HISTORICAL_ASSERTION": 8,
    "DIAGNOSTIC_ARTIFACT_DRIFT": 1
  },
  "suite_state": "KNOWN_PRE_EXISTING_FAILURES_ONLY",
  "hkei_170_regression_count": 0
}
```
