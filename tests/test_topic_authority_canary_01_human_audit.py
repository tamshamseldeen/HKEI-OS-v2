"""Integrity tests for the independent HKEI-213 human-review packet."""

import json
from pathlib import Path

from src.topic.topic import Topic


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "benchmark/internal_canary/topic_authority_canary_01_human_audit.json"
CANARY = ROOT / "benchmark/internal_canary/topic_authority_canary_01.json"
SOURCE = ROOT / "canary_sources/topic_authority_canary_01.txt"


def packet(): return json.loads(AUDIT.read_text(encoding="utf-8"))
def consumed(): return tuple(item for item in json.loads(CANARY.read_text(encoding="utf-8"))["cases"] if item["authority_consumed"])


def test_exactly_three_records(): assert len(packet()["records"]) == 3
def test_only_consumed_cases_included(): assert {item["canary_id"] for item in packet()["records"]} == {item["canary_id"] for item in consumed()}
def test_no_topic_change_cases_excluded(): assert not {"CANARY-001", "CANARY-004"}.intersection(item["canary_id"] for item in packet()["records"])
def test_audit_identities_unique():
    identities = [item["audit_identity"] for item in packet()["records"]]; assert len(identities) == len(set(identities)) == 3
def test_audit_identities_match_queue(): assert {item["audit_identity"] for item in packet()["records"]} == {item["decision_fingerprint"] for item in json.loads(CANARY.read_text())["audit_queue"]}
def test_deterministic_topics_preserved(): assert {item["canary_id"]:item["deterministic_topic"] for item in packet()["records"]} == {item["canary_id"]:item["deterministic_topic"] for item in consumed()}
def test_authoritative_topics_preserved(): assert {item["canary_id"]:item["authoritative_topic"] for item in packet()["records"]} == {item["canary_id"]:item["authoritative_topic"] for item in consumed()}
def test_article_context_available_and_faithful():
    source = SOURCE.read_text(encoding="utf-8"); assert all(item["human_review_context"]["title"] in source and item["human_review_context"]["faithful_excerpt"] in source for item in packet()["records"])
def test_no_provider_raw_response(): assert "raw_response" not in AUDIT.read_text(encoding="utf-8").lower()
def test_no_provider_prompt(): assert "raw_prompt" not in AUDIT.read_text(encoding="utf-8").lower()
def test_no_chain_of_thought(): assert "chain-of-thought" not in AUDIT.read_text(encoding="utf-8").lower()
def test_human_judgments_recorded_exactly(): assert {item["canary_id"]:item["human_correctness"] for item in packet()["records"]} == {"CANARY-002":"CORRECT_OVERRIDE", "CANARY-003":"INCORRECT_OVERRIDE", "CANARY-005":"CORRECT_OVERRIDE"}
def test_legal_topic_contract_exact(): assert set(packet()["legal_topic_values"]) == {item.value for item in Topic}
def test_independent_human_source(): assert packet()["judgment_source"] == "INDEPENDENT_HUMAN_REVIEW"
def test_recorded_metrics(): assert packet()["metrics"] == {"audit_records_prepared":3,"reviewed":3,"correct":2,"incorrect":1,"unsure":0,"provider_calls":0}
def test_provider_calls_zero(): assert packet()["metrics"]["provider_calls"] == 0
