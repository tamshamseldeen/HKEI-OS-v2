"""HKEI-214 audited metrics and mandatory stop-policy tests."""

import json
from pathlib import Path

from examples.run_topic_authority_canary_01_human_audit_result import (
    CANARY, HISTORICAL_CANARY_SHA256, OUTPUT_JSON, build_result,
)
from hashlib import sha256


def result(): return build_result()
def by_id(): return {item["canary_id"]:item for item in result()["records"]}


def test_exactly_three_reviewed_records(): assert len(result()["records"]) == result()["reviewed_count"] == 3
def test_canary_002_correct(): assert by_id()["CANARY-002"]["human_correctness"] == "CORRECT_OVERRIDE"
def test_canary_003_incorrect(): assert by_id()["CANARY-003"]["human_correctness"] == "INCORRECT_OVERRIDE"
def test_canary_005_correct(): assert by_id()["CANARY-005"]["human_correctness"] == "CORRECT_OVERRIDE"
def test_expected_topics_exact(): assert {key:value["human_expected_topic"] for key,value in by_id().items()} == {"CANARY-002":"POLITICS", "CANARY-003":"CRIME", "CANARY-005":"EDUCATION"}
def test_audit_identities_unchanged(): assert len({item["audit_identity"] for item in result()["records"]}) == 3
def test_no_duplicate_audits(): assert result()["audited_override_count"] == 3
def test_no_topic_change_excluded(): assert not {"CANARY-001", "CANARY-004"}.intersection(by_id())
def test_reviewed_count(): assert result()["reviewed_count"] == 3
def test_correct_count(): assert result()["correct_count"] == 2
def test_incorrect_count(): assert result()["incorrect_count"] == 1
def test_unsure_count(): assert result()["unsure_count"] == 0
def test_precision_two_thirds(): assert result()["override_precision"] == 2/3
def test_minimum_precision_sample(): assert result()["minimum_precision_sample"] == 30
def test_precision_not_evaluable(): assert result()["precision_threshold_evaluable"] is False
def test_precision_stop_not_triggered(): assert result()["precision_stop_triggered"] is False
def test_regression_budget_zero(): assert result()["regression_budget"] == 0
def test_regression_count_one(): assert result()["regression_count"] == 1
def test_regression_budget_exceeded(): assert result()["regression_budget_exceeded"] is True
def test_stop_evaluator_executed(): assert result()["stop_evaluator_executed"] is True
def test_should_stop(): assert result()["stop_decision"]["should_stop"] is True
def test_stop_reason_is_regression_budget(): assert result()["stop_decision"]["reasons"] == ["REGRESSION_BUDGET_EXCEEDED"]
def test_recommended_mode_shadow(): assert result()["stop_decision"]["recommended_mode"] == "SHADOW"
def test_canary_continuation_false(): assert result()["canary_continuation_allowed"] is False
def test_incorrect_override_not_contract_violation(): assert result()["authority_contract_violations"] == 0
def test_historical_canary_unchanged(): assert sha256(CANARY.read_bytes()).hexdigest() == HISTORICAL_CANARY_SHA256
def test_post_stop_shadow_blocks_authority(): assert not result()["post_stop_authority_consumed"] and result()["post_stop_consumer_topic"] == result()["post_stop_deterministic_topic"]
def test_internal_route_not_globally_enabled(): assert result()["internal_route_state_after_stop"] == "DISABLED_DEFAULT"
def test_provider_calls_zero(): assert result()["provider_calls"] == 0
def test_no_raw_provider_response(): assert "raw_response" not in json.dumps(result()).lower()
def test_no_chain_of_thought(): assert "chain-of-thought" not in json.dumps(result()).lower()
def test_persisted_result_matches_if_present():
    if OUTPUT_JSON.exists(): assert json.loads(OUTPUT_JSON.read_text()) == result()
