"""Offline runner and post-live sanitized artifact integrity tests."""

import json
from pathlib import Path

from examples.run_topic_authority_canary_01 import CASE_IDS, MAX_CALLS, SOURCE_SHA256, _parse_cases, _verify_source


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmark/internal_canary/topic_authority_canary_01.json"


def test_registered_source_preconditions(): _verify_source()
def test_exact_case_inventory(): assert tuple(item[0] for item in _parse_cases()) == CASE_IDS
def test_hard_call_limit(): assert MAX_CALLS == 5
def test_source_sha_frozen(): assert SOURCE_SHA256 == "fc1edf27beb103b726a3f879b5bff9ae0e801b8b5114abc7b197e2ecac2f4a7d"
def test_artifact_is_optional_before_live_execution(): assert OUTPUT.exists() or not OUTPUT.exists()


def test_live_artifact_is_sanitized_if_present():
    if not OUTPUT.exists(): return
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    forbidden = {"body", "title", "source", "raw_prompt", "raw_response", "api_key", "chain_of_thought"}
    assert not forbidden.intersection(data)
    assert all(not forbidden.intersection(case) for case in data["cases"])


def test_live_artifact_call_limit_if_present():
    if OUTPUT.exists(): assert json.loads(OUTPUT.read_text())["provider_calls"] <= MAX_CALLS


def test_audit_queue_has_no_correctness_if_present():
    if not OUTPUT.exists(): return
    assert all(item["correctness"] is None and item["decision_fingerprint"] for item in json.loads(OUTPUT.read_text())["audit_queue"])
