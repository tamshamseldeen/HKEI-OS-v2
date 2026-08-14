"""Regression contract for the HKEI-210 final audit rerun."""

import json
from pathlib import Path

from examples.run_limited_topic_authority_final_pre_canary_audit_rerun import build_rerun_audit


ROOT = Path(__file__).resolve().parents[1]


def test_previous_failure_evidence_preserved():
    previous = build_rerun_audit()["previous_audit"]
    assert previous["stop_signal_audit"] == "FAIL"
    assert previous["stop_observability"] == "FAIL"
    assert previous["final_safety_classification"] == "PRE_CANARY_BLOCKED"


def test_stop_visibility_fix_commit_recorded(): assert build_rerun_audit()["fix_commit"] == "7d39db7"


def test_previous_blocker_now_fully_passes():
    assert set(build_rerun_audit()["previous_blocker_verification"].values()) == {"PASS"}


def test_complete_audit_has_no_failed_checks():
    assert set(build_rerun_audit()["current_checks"].values()) == {"PASS"}


def test_pilot_thresholds_unchanged():
    audit = build_rerun_audit()
    assert (audit["regression_budget"], audit["precision_threshold"], audit["minimum_audited_overrides"]) == (0, 0.90, 30)


def test_format_and_intent_authority_remain_zero():
    audit = build_rerun_audit()
    assert audit["format_authority_paths"] == audit["reader_intent_authority_paths"] == 0


def test_default_and_rollout_remain_safe():
    audit = build_rerun_audit()
    assert audit["default_mode"] == "SHADOW"
    assert audit["global_authority_enabled"] is False
    assert audit["percentage_rollout"] is False


def test_final_classification_is_safe_and_ready():
    audit = build_rerun_audit()
    assert audit["final_safety_classification"] == "PRE_CANARY_SAFE"
    assert audit["final_readiness_decision"] == "READY_TO_RUN_INTERNAL_SINGLE_PATH_CANARY"


def test_first_scope_remains_internal_single_path():
    assert build_rerun_audit()["first_real_canary_scope"] == "INTERNAL_SINGLE_PATH"


def test_no_provider_or_production_mutation():
    audit = build_rerun_audit()
    assert audit["real_provider_calls"] == 0
    assert audit["production_mutation"] is False


def test_persisted_rerun_matches_builder():
    persisted = json.loads((ROOT / "benchmark/limited_topic_authority_final_pre_canary_audit_rerun.json").read_text())
    assert persisted == build_rerun_audit()
