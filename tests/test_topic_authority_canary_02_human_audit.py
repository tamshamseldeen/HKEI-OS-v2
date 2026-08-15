"""Integrity contract for the HKEI-219/HKEI-220 human-audit packet."""

import json
from pathlib import Path

from src.topic.topic import Topic


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "benchmark/internal_canary/topic_authority_canary_02_human_audit.json"
CANARY = ROOT / "benchmark/internal_canary/topic_authority_canary_02.json"
SOURCE = ROOT / "canary_sources/topic_authority_canary_02.txt"
HUMAN_FIELDS = (
    "human_correctness", "human_expected_topic", "reviewer_notes", "review_timestamp"
)


def packet(): return json.loads(AUDIT.read_text(encoding="utf-8"))
def run_cases(): return json.loads(CANARY.read_text(encoding="utf-8"))["cases"]
def consumed(): return tuple(item for item in run_cases() if item["authority_consumed"])
def records_by_id(): return {item["canary_id"]: item for item in packet()["records"]}


def test_exactly_two_records(): assert len(packet()["records"]) == 2
def test_only_authority_consumed_cases_included(): assert set(records_by_id()) == {item["canary_id"] for item in consumed()}
def test_blocked_cases_excluded(): assert not {item["canary_id"] for item in run_cases() if item["block_reasons"]}.intersection(records_by_id())
def test_no_topic_change_cases_excluded(): assert not {item["canary_id"] for item in run_cases() if "NO_TOPIC_CHANGE" in item["block_reasons"]}.intersection(records_by_id())
def test_audit_identities_unique():
    identities = [item["audit_identity"] for item in packet()["records"]]
    assert len(identities) == len(set(identities)) == 2
def test_audit_identities_match_queue_exactly():
    queue = json.loads(CANARY.read_text(encoding="utf-8"))["audit_queue"]
    assert {item["audit_identity"] for item in packet()["records"]} == {item["decision_fingerprint"] for item in queue}
def test_deterministic_topics_preserved(): assert {key:value["deterministic_topic"] for key,value in records_by_id().items()} == {item["canary_id"]:item["deterministic_topic"] for item in consumed()}
def test_authoritative_topics_preserved(): assert {key:value["authoritative_topic"] for key,value in records_by_id().items()} == {item["canary_id"]:item["authoritative_topic"] for item in consumed()}
def test_human_fields_recorded_from_independent_review():
    assert {key:value["human_correctness"] for key,value in records_by_id().items()} == {"CANARY2-001":"CORRECT_OVERRIDE", "CANARY2-002":"UNSURE"}
    assert records_by_id()["CANARY2-001"]["human_expected_topic"] in packet()["legal_topic_values"]
    assert records_by_id()["CANARY2-002"]["human_expected_topic"] == "UNREVIEWED"
    assert all(record["reviewer_notes"] != "UNREVIEWED" and record["review_timestamp"] != "UNREVIEWED" for record in packet()["records"])
def test_legal_topic_contract_exact(): assert set(packet()["legal_topic_values"]) == {item.value for item in Topic}
def test_article_context_available_and_faithful():
    source = SOURCE.read_text(encoding="utf-8")
    assert all(item["human_review_context"]["title"] in source and item["human_review_context"]["faithful_excerpt"] in source for item in packet()["records"])
def test_no_provider_prompt_field(): assert all("provider_prompt" not in item and "raw_prompt" not in item for item in packet()["records"])
def test_no_raw_provider_response_field(): assert all("provider_response" not in item and "raw_response" not in item for item in packet()["records"])
def test_no_provider_reasoning_field(): assert all("provider_reasoning" not in item and "reasoning" not in item for item in packet()["records"])
def test_no_chain_of_thought_field(): assert all("chain_of_thought" not in item for item in packet()["records"])
def test_no_automatic_correctness_inference(): assert packet()["judgment_source"] == "INDEPENDENT_HUMAN_REVIEW"
def test_provider_calls_zero(): assert packet()["metrics"]["provider_calls"] == 0
def test_pilot_remains_shadow(): assert packet()["pilot_effective_mode"] == "SHADOW"
def test_canary_continuation_paused(): assert packet()["canary_continuation"] == "PAUSED_FOR_HUMAN_AUDIT"
def test_independence_statement_complete():
    statement = packet()["independence_statement"]
    assert "must not assume either deterministic_topic or authoritative_topic is correct" in statement
    assert "Provider output is not ground truth" in statement
def test_metrics_before_review_exact():
    assert packet()["metrics"] == {"audit_records_prepared":2,"reviewed":2,"correct":1,"incorrect":0,"unsure":1,"provider_calls":0}
