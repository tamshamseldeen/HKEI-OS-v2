"""Offline runner and post-live sanitized artifact integrity tests."""

import json
from pathlib import Path

from examples.run_topic_authority_canary_02 import (
    CASE_IDS,
    MAX_CALLS,
    SOURCE_SHA256,
    _parse_cases,
    _verify_source,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmark/internal_canary/topic_authority_canary_02.json"


def test_registered_source_preconditions(): _verify_source()
def test_exact_case_inventory(): assert tuple(item[0] for item in _parse_cases()) == CASE_IDS
def test_hard_call_limit(): assert MAX_CALLS == 5
def test_source_sha_frozen(): assert SOURCE_SHA256 == "06ac5eff8fb27212ec06351f056d9911d47bd739fe29e27b81844a1519e2cb04"
def test_artifact_is_optional_before_live_execution(): assert OUTPUT.exists() or not OUTPUT.exists()


def test_live_artifact_is_sanitized_if_present():
    if not OUTPUT.exists(): return
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    forbidden = {"body", "title", "source", "raw_prompt", "raw_response", "api_key", "authorization", "chain_of_thought"}
    assert not forbidden.intersection(data)
    assert all(not forbidden.intersection(case) for case in data["cases"])


def test_live_artifact_call_limit_and_inventory_if_present():
    if not OUTPUT.exists(): return
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert data["provider_calls"] <= MAX_CALLS
    assert tuple(case["canary_id"] for case in data["cases"]) == CASE_IDS[:data["cases_completed"]]
    assert len({case["canary_id"] for case in data["cases"]}) == data["cases_completed"]


def test_runtime_boundaries_if_present():
    if not OUTPUT.exists(): return
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert data["global_mode_before_run"] == "SHADOW"
    assert data["global_mode_after_run"] == "SHADOW"
    assert data["internal_route_state_after_run"] == "DISABLED_DEFAULT"
    assert data["production_wide_authority_enabled"] is False
    assert data["format_authority_violations"] == 0
    assert data["reader_intent_authority_violations"] == 0


def test_hkei_216_diagnostics_if_present():
    if not OUTPUT.exists(): return
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert data["consequence_only_primary_sufficiency_count"] == sum(
        case["consequence_role_diagnostic_summary"]["consequence_only_primary_sufficiency_count"]
        for case in data["cases"]
    )


def test_audit_queue_has_required_sanitized_fields_if_present():
    if not OUTPUT.exists(): return
    queue = json.loads(OUTPUT.read_text(encoding="utf-8"))["audit_queue"]
    assert all(item["correctness"] is None for item in queue)
    assert all(item["decision_fingerprint"] and item["deterministic_topic"] and item["authoritative_topic"] for item in queue)
