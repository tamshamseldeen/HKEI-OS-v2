"""HKEI-220 audited metrics and mandatory stop-policy tests."""

import json
from pathlib import Path

from examples.run_topic_authority_canary_02_human_audit_result import (
    CANARY, HISTORICAL_CANARY_SHA256, OUTPUT_JSON, build_result,
)
from hashlib import sha256


def result(): return build_result()
def by_id(): return {item["canary_id"]:item for item in result()["records"]}


def test_exactly_two_reviewed_records(): assert len(result()["records"]) == result()["reviewed_count"] == 2
def test_canary_001_correct(): assert by_id()["CANARY2-001"]["human_correctness"] == "CORRECT_OVERRIDE"
def test_canary_001_expected_world(): assert by_id()["CANARY2-001"]["human_expected_topic"] == "WORLD"
def test_canary_002_unsure(): assert by_id()["CANARY2-002"]["human_correctness"] == "UNSURE"
def test_canary_002_expected_topic_unreviewed(): assert by_id()["CANARY2-002"]["human_expected_topic"] == "UNREVIEWED"
def test_canary_002_ontology_boundary(): assert by_id()["CANARY2-002"]["override_transition"] == "ONTOLOGY_BOUNDARY_UNCERTAIN"
def test_audit_identities_unchanged(): assert {item["audit_identity"] for item in result()["records"]} == {"105cb08f0553979ac022501fc8a9e16b9cf5aa9b73575b3d34a6383b9cd1116c", "218688620285f5c799caff2c31a5c88f4d5886b143e288ff2dbad7cb12272b9f"}
def test_no_duplicate_audits(): assert len({item["audit_identity"] for item in result()["records"]}) == 2
def test_blocked_cases_excluded(): assert set(by_id()) == {"CANARY2-001", "CANARY2-002"}
def test_no_topic_change_excluded(): assert set(by_id()) == {"CANARY2-001", "CANARY2-002"}
def test_reviewed_count(): assert result()["reviewed_count"] == 2
def test_correct_count(): assert result()["correct_count"] == 1
def test_incorrect_count(): assert result()["incorrect_count"] == 0
def test_unsure_count(): assert result()["unsure_count"] == 1
def test_precision_one(): assert result()["override_precision"] == 1.0
def test_minimum_precision_sample(): assert result()["minimum_precision_sample"] == 30
def test_precision_not_evaluable(): assert result()["precision_threshold_evaluable"] is False
def test_precision_stop_not_triggered(): assert result()["precision_stop_triggered"] is False
def test_regression_budget_zero(): assert result()["regression_budget"] == 0
def test_regression_count_zero(): assert result()["regression_count"] == 0
def test_regression_budget_not_exceeded_for_canary_02(): assert result()["regression_budget_exceeded"] is False
def test_wrong_to_wrong_count_zero(): assert result()["wrong_to_wrong_override_count"] == 0
def test_stop_evaluator_executed(): assert result()["stop_evaluator_executed"] is True
def test_should_stop(): assert result()["stop_decision"]["should_stop"] is True
def test_stop_reason_is_regression_budget(): assert result()["stop_decision"]["reasons"] == ["REGRESSION_BUDGET_EXCEEDED"]
def test_recommended_mode_shadow(): assert result()["stop_decision"]["recommended_mode"] == "SHADOW"
def test_canary_continuation_false(): assert result()["canary_continuation_allowed"] is False
def test_incorrect_override_not_contract_violation(): assert result()["authority_contract_violations"] == 0
def test_historical_canary_unchanged(): assert sha256(CANARY.read_bytes()).hexdigest() == HISTORICAL_CANARY_SHA256
def test_canary_01_history_unchanged():
    cumulative = result()["cumulative_pilot_audit"]
    assert cumulative["audited_override_count"] - result()["audited_override_count"] == 3
    assert cumulative["audited_correct_override_count"] - result()["correct_count"] == 2
    assert cumulative["audited_incorrect_override_count"] == 1
def test_cumulative_audited_count(): assert result()["cumulative_pilot_audit"]["audited_override_count"] == 4
def test_cumulative_correct_count(): assert result()["cumulative_pilot_audit"]["audited_correct_override_count"] == 3
def test_cumulative_incorrect_count(): assert result()["cumulative_pilot_audit"]["audited_incorrect_override_count"] == 1
def test_cumulative_unsure_count(): assert result()["cumulative_pilot_audit"]["unsure_override_count"] == 1
def test_cumulative_precision(): assert result()["cumulative_pilot_audit"]["override_precision"] == 0.75
def test_cumulative_regression_budget_exceeded(): assert result()["cumulative_pilot_audit"]["regression_budget_exceeded"] is True
def test_hkei_216_signal_preserved():
    diagnostic = result()["hkei_216_diagnostic"]
    assert diagnostic["consequence_only_primary_sufficiency_count"] == 0
    assert diagnostic["generalization_signal"] == "NO_NEW_CONSEQUENCE_SUBJECT_REGRESSION_OBSERVED"
def test_amendment_provenance_preserved():
    amendment = by_id()["CANARY2-002"]["audit_amendment"]
    assert amendment["previous_human_correctness"] == "INCORRECT_OVERRIDE"
    assert amendment["previous_human_expected_topic"] == "WORLD"
    assert amendment["original_review_timestamp"] != amendment["amendment_timestamp"]
def test_post_stop_shadow_blocks_authority(): assert not result()["post_stop_authority_consumed"] and result()["post_stop_consumer_topic"] == result()["post_stop_deterministic_topic"]
def test_internal_route_not_globally_enabled(): assert result()["internal_route_state_after_stop"] == "DISABLED_DEFAULT"
def test_provider_calls_zero(): assert result()["provider_calls"] == 0
def test_no_raw_provider_response(): assert "raw_response" not in json.dumps(result()).lower()
def test_no_provider_prompt_or_reasoning():
    rendered = json.dumps(result()).lower()
    assert "provider_prompt" not in rendered and "provider_response" not in rendered and "provider_reasoning" not in rendered
def test_no_chain_of_thought(): assert "chain-of-thought" not in json.dumps(result()).lower()
def test_persisted_result_matches_if_present():
    if OUTPUT_JSON.exists(): assert json.loads(OUTPUT_JSON.read_text()) == result()
