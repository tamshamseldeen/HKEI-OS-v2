"""Post-run integrity checks for the frozen Canary 03 evaluation."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "canary_sources/topic_authority_canary_03.txt"
MANIFEST = ROOT / "canary_sources/topic_authority_canary_03_manifest.json"
RESULT = ROOT / "benchmark/internal_canary/topic_authority_canary_03.json"
EXPECTED_SHA = "fb711ba1d0c3a4a8cd32d9f8ea2729f64754d0f38db4560a099ee23ffe9ca531"
EXPECTED_IDS = [f"CANARY3-{number:03d}" for number in range(1, 6)]


def data(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_frozen_source_hash_is_unchanged():
    assert sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA


def test_exact_five_cases_completed_once():
    result = data(RESULT)
    assert result["cases_attempted"] == result["cases_completed"] == 5
    assert [case["canary_id"] for case in result["cases"]] == EXPECTED_IDS


def test_provider_scope_was_respected():
    result = data(RESULT)
    assert result["provider_calls"] == 4 <= 5
    assert result["valid_responses"] == 4
    assert result["invalid_responses"] == result["provider_errors"] == 0
    assert result["retry_attempts"] == 0
    assert result["model"] == "gpt-5-mini"


def test_global_shadow_and_disabled_route_preserved():
    result = data(RESULT)
    assert result["global_mode_before_run"] == result["global_mode_after_run"] == "SHADOW"
    assert result["internal_route_state_after_run"] == "DISABLED_DEFAULT"
    assert result["production_wide_authority_enabled"] is False


def test_operational_contract_is_clean():
    result = data(RESULT)
    assert result["classification"] == "THIRD_CANARY_OPERATIONALLY_CLEAN"
    assert result["contract_violations"] == []
    assert result["candidate_violations"] == 0
    assert result["fingerprint_violations"] == 0
    assert result["observation_failures"] == 0
    assert result["canary_stopped_early"] is False


def test_consumed_state_is_recorded_without_truth_claims():
    manifest = data(MANIFEST)
    result = data(RESULT)
    assert manifest["freshness_status"] == "CONSUMED_FOR_EVALUATION"
    assert manifest["evaluation_status"] == "COMPLETED_AWAITING_HUMAN_AUDIT"
    assert manifest["provider_calls"] == result["provider_calls"] == 4
    assert result["human_correctness_judgments_made"] == 0
    assert all(item["correctness"] is None for item in result["audit_queue"])


def test_only_sanitized_result_fields_are_persisted():
    text = RESULT.read_text(encoding="utf-8").lower()
    forbidden = ("api_key", "authorization", "raw_prompt", "raw_response", "chain_of_thought")
    assert not any(field in text for field in forbidden)
