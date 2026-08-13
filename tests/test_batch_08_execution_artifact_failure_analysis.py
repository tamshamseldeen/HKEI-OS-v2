"""Offline tests for the Batch 08 artifact observation-race diagnosis."""

import inspect

import examples.run_batch_08_execution_artifact_failure_analysis as diagnostic


def test_provider_call_reconstruction_is_deterministic() -> None:
    result = diagnostic.analyze()
    assert result["provider_call_reconstruction"] == "CONFIRMED_6"
    assert result["provider_call_cases"] == ["071", "073", "075", "077", "079", "080"]


def test_failure_stage_and_root_cause_are_valid() -> None:
    result = diagnostic.analyze()
    assert result["failure_stage"] in diagnostic.FAILURE_STAGES
    assert result["failure_stage"] == "POST_WRITE_VALIDATION_FAILURE"
    assert result["artifact_failure_root_cause"] == "POST_RUN_VALIDATION_BUG"


def test_all_execution_stages_and_complete_cases_are_confirmed() -> None:
    result = diagnostic.analyze()
    assert result["live_runner_started"] is True
    assert result["classifier_execution"] == "CONFIRMED_10_CASES"
    assert result["semantic_execution"] == "CONFIRMED_10_CASES"
    assert result["gate_execution"] == "CONFIRMED_10_CASES"
    assert result["provider_execution"] == "CONFIRMED"
    assert result["partial_cases_processed"] == 10
    assert result["complete_sanitized_results_found"] is True


def test_untracked_file_safety_inspection_is_sanitized() -> None:
    files = diagnostic.analyze()["untracked_diagnostic_files"]
    assert len(files) == 4
    assert all(item["safe_to_preserve"] for item in files)
    assert not any(item["contains_source_body"] for item in files)
    assert not any(item["contains_secret"] for item in files)
    assert not any(item["contains_raw_prompt"] for item in files)
    assert not any(item["contains_raw_provider_response"] for item in files)


def test_status_and_retry_recommendations_are_deterministic() -> None:
    result = diagnostic.analyze()
    assert result["batch_08_recommended_scientific_status"] == "EVALUATED_PREREGISTERED_HOLDOUT"
    assert result["retry_safety"] == "DO_NOT_RETRY_BATCH_08"
    assert result["required_fix_scope"] == "DIAGNOSTIC_FIX_ONLY"
    assert result["retry_executed"] is False


def test_diagnostic_has_no_provider_or_network_path() -> None:
    source = inspect.getsource(diagnostic)
    assert "OpenAI(" not in source
    assert ".adjudicate(" not in source
    assert "requests." not in source
    assert diagnostic.analyze()["provider_calls_during_diagnostic"] == 0


def test_diagnostic_modifies_no_production_contract() -> None:
    assert not any(
        item["path"].startswith("src/")
        for item in diagnostic.analyze()["untracked_diagnostic_files"]
    )
