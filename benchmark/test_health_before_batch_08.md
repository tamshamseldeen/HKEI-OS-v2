# Test Health Before Batch 08

Suite: 2008 passed, 11 failed, 9 errors, 9 skipped.

| Test path | Test name | Phase | Classification | First relevant finding |
| --- | --- | --- | --- | --- |
| tests/test_batch_05_adjudication_gate_shadow.py | test_workflow_and_gate_run_once_per_case_without_truth_inputs | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: current Format differs from frozen predicted_format |
| tests/test_batch_05_adjudication_gate_shadow.py | test_shadow_never_reads_human_risk_annotations | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: current Format differs from frozen predicted_format |
| tests/test_batch_05_adjudication_gate_shadow.py | test_shadow_uses_no_api_network_or_environment | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: current Format differs from frozen predicted_format |
| tests/test_batch_06_activation_to_decision_gap_analysis.py | test_exactly_ten_cases_and_hkei_161_metrics_are_reproduced | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: format_gate_recall 33.3333 != 50.0 |
| tests/test_batch_06_editorial_validation.py | test_hkei_158_changes_no_production_files | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: later committed src changes violate historical diff assertion |
| tests/test_batch_06_editorial_validation.py | test_hkei_161_changes_no_production_files | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: later committed src changes violate historical diff assertion |
| tests/test_batch_06_post_hkei_163_comparison.py | test_holdout_integrity_provider_isolation_and_no_production_edits | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: later committed src changes violate historical diff assertion |
| tests/test_batch_06_semantic_activation_gap_analysis.py | test_integrity_offline_behavior_and_no_production_change | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: later committed src changes violate historical diff assertion |
| tests/test_batch_06_semantic_directionality_sufficiency_analysis.py | test_integrity_offline_behavior_and_no_production_modification | TEST BODY | PRE_EXISTING_BASELINE_FAILURE | AssertionError: later committed src changes violate historical diff assertion |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_expected_baseline_is_read_after_current_execution | TEST BODY | STALE_DIAGNOSTIC_ASSERTION | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_runtime_matches_hkei_178_except_gate | TEST BODY | STALE_DIAGNOSTIC_ASSERTION | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_exact_cases_and_hkei_178_baseline_loaded | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_current_gate_metrics_and_deltas_are_derived | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_previous_false_negative_tracking_is_post_hoc | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_new_false_positives_and_provider_delta_are_derived | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_effective_labels_and_change_precision_match_case_records | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_recovered_fn_utility_is_derived | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_provider_contract_and_shadow_safety | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_assessor_remains_diagnostic_and_budget_is_exhausted | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |
| tests/test_batch_07_post_gate_refinement_full_stack.py | test_sanitized_outputs_contain_no_source_secret_or_raw_response | SETUP | SETUP_CONTRACT_DRIFT | RuntimeError: EVALUATION_RUNTIME_MISMATCH |

Setup root cause: DIAGNOSTIC_DEPENDENCY_ORDER (9/9 shared).

Live evaluation safety: SAFE_AFTER_DIAGNOSTIC_TEST_FIX_ONLY.

Recommended next step: FIX_DIAGNOSTIC_TESTS_ONLY.

Provider calls: 0.
