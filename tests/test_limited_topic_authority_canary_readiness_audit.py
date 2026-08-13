"""Tests for the controlled Topic authority readiness audit."""

import ast
from pathlib import Path

import pytest

from examples.run_limited_topic_authority_canary_readiness_audit import run_audit
from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.resolution import (
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityPilotStopEvaluator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def audit():
    return run_audit(persist=False)


def test_default_shadow_verified(audit) -> None:
    assert LimitedTopicAuthorityConfig().authority_mode is ResolverAuthorityMode.SHADOW
    assert audit["default_off_safe"] is True


def test_explicit_limited_requirement_verified(audit) -> None:
    assert audit["explicit_enablement_required"] is True


def test_kill_switch_contract_and_operational_gap_are_distinguished(audit) -> None:
    assert audit["kill_switch_ready_at_authority_layer"] is True
    assert audit["kill_switch_operationally_reachable"] is False


def test_rollback_contract_and_operational_gap_are_distinguished(audit) -> None:
    assert audit["rollback_ready_at_contract_layer"] is True
    assert audit["rollback_operationally_wired"] is False


def test_eligibility_and_same_label_contracts_are_complete(audit) -> None:
    assert audit["authority_eligibility_complete"] is True
    assert audit["same_label_safe"] is True


def test_format_and_reader_intent_have_zero_authority_paths(audit) -> None:
    assert audit["format_authority_paths"] == 0
    assert audit["reader_intent_authority_paths"] == 0


def test_gate_resolver_and_provider_are_isolated(audit) -> None:
    assert audit["gate_isolated"] is True
    assert audit["resolver_isolated"] is True
    assert audit["provider_isolated"] is True


def test_stop_evaluator_visibility_and_no_automatic_mutation(audit) -> None:
    assert audit["stop_evaluator_visible_in_runtime_result"] is True
    assert audit["stop_recommendation"] == "SHADOW"
    assert audit["automatic_mode_mutation"] is False


def test_fail_closed_behavior_verified(audit) -> None:
    assert audit["fail_closed"] is True


def test_observation_coverage_is_complete(audit) -> None:
    assert audit["observation_coverage_complete"] is True
    assert audit["observation_sensitive_direct_fields"] == []


def test_sensitive_runtime_result_gap_is_reported(audit) -> None:
    assert audit["runtime_result_sensitive_direct_fields"] == []
    assert audit["runtime_result_embeds_full_shadow_result"] is True
    assert audit["sensitive_data_safe_for_operational_sink"] is False
    assert "SANITIZED_RUNTIME_RESULT_BOUNDARY_MISSING" in audit["enablement_gaps"]


def test_metrics_and_safety_metrics_are_complete(audit) -> None:
    assert audit["operational_metrics_complete"] is True
    assert audit["safety_metrics_complete"] is True


def test_human_audit_is_independent_and_duplicate_safe(audit) -> None:
    assert audit["human_audit_independent"] is True
    assert audit["duplicate_audit_protected"] is True


def test_exact_threshold_contract(audit) -> None:
    assert audit["minimum_provider_confidence"] == AdjudicationConfidence.MEDIUM.value
    assert audit["block_on_review_required"] is True
    assert audit["block_on_ambiguity"] is True
    assert audit["regression_budget"] == 0
    assert audit["minimum_audited_override_sample"] == 30
    assert audit["override_precision_threshold"] == 0.90


def test_regression_stop_recommends_shadow(audit) -> None:
    assert audit["first_incorrect_override_stops"] is True
    assert audit["first_incorrect_override_recommended_mode"] == "SHADOW"


def test_precision_threshold_timing(audit) -> None:
    assert audit["precision_stop_below_minimum"] is False
    assert audit["precision_stop_at_minimum_below_threshold"] is True


def test_provider_failure_contract(audit) -> None:
    assert audit["provider_failure_fail_closed"] is True
    assert audit["provider_failure_is_not_incorrect_override"] is True


def test_no_shared_mutable_state_and_request_local_concurrency(audit) -> None:
    assert audit["shared_mutable_state"] is False
    assert audit["request_local_concurrency_contract"] is True
    assert audit["idempotent"] is True


def test_runtime_available_but_not_globally_enabled(audit) -> None:
    assert audit["canary_runtime_available"] is True
    assert audit["canary_globally_enabled"] is False


def test_existing_consumers_do_not_read_authoritative_topic(audit) -> None:
    assert audit["existing_consumer_reads_authoritative_topic"] is False


@pytest.mark.parametrize(
    "gap",
    [
        "CONFIG_SOURCE_MISSING",
        "AUTHORITY_MODE_NOT_RUNTIME_CONFIGURABLE",
        "OBSERVATION_SINK_MISSING",
        "STOP_SIGNAL_NOT_OPERATIONALLY_VISIBLE",
        "KILL_SWITCH_NOT_OPERATIONALLY_REACHABLE",
        "CONSUMER_ROUTING_GAP",
    ],
)
def test_each_operational_enablement_gap_is_reported(audit, gap) -> None:
    assert gap in audit["enablement_gaps"]


def test_required_before_enablement_is_explicit(audit) -> None:
    assert len(audit["required_before_enablement"]) == 7
    assert any("SHADOW fail-safe" in item for item in audit["required_before_enablement"])
    assert any("sanitized" in item for item in audit["required_before_enablement"])


def test_recommended_scope_is_internal_single_path(audit) -> None:
    assert audit["recommended_first_canary_scope"] == "INTERNAL_SINGLE_PATH"


def test_readiness_and_safety_classifications(audit) -> None:
    assert audit["canary_safety_classification"] == "SAFE_WITH_OPERATIONAL_GAPS"
    assert audit["readiness_classification"] == "NOT_READY_FOR_CANARY_ENABLEMENT"


def test_audit_makes_zero_provider_calls_and_no_mutation(audit) -> None:
    assert audit["provider_calls"] == 0
    assert audit["production_mutation"] is False


def test_audit_script_has_no_openai_import() -> None:
    path = PROJECT_ROOT / "examples" / "run_limited_topic_authority_canary_readiness_audit.py"
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "openai" not in imported


def test_audit_is_deterministic() -> None:
    assert run_audit(persist=False) == run_audit(persist=False)


def test_production_files_are_not_modified_by_audit_contract() -> None:
    assert TopicAuthorityPilotStopEvaluator.OVERRIDE_PRECISION_THRESHOLD == 0.90
