"""Tests for the deterministic limited Topic authority offline canary."""

import ast
from pathlib import Path

import pytest

from examples.run_limited_topic_authority_offline_canary import run_simulation
from src.resolution import ResolverAuthorityMode, TopicAuthorityPilotStopReason


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def simulation():
    return run_simulation(persist=False)


def test_simulation_has_at_least_sixty_cases(simulation) -> None:
    assert simulation["simulation_cases"] == 75


@pytest.mark.parametrize(
    ("kind", "minimum"),
    [
        ("eligible_changed", 20),
        ("same_label", 10),
        ("deterministic", 10),
        ("low_confidence", 5),
        ("review_required", 5),
        ("ambiguity", 3),
        ("provider_failure", 2),
        ("fingerprint_failure", 2),
        ("candidate_failure", 2),
        ("invalid_response", 1),
    ],
)
def test_required_scenario_distribution(simulation, kind, minimum) -> None:
    assert simulation["scenario_distribution"][kind] >= minimum


def test_clean_pilot_does_not_stop(simulation) -> None:
    assert simulation["clean"]["stop"].should_stop is False


def test_clean_pilot_has_thirty_independent_correct_audits(simulation) -> None:
    safety = simulation["clean"]["safety"]
    assert safety.audited_override_count == 30
    assert safety.audited_correct_override_count == 30
    assert safety.audited_incorrect_override_count == 0
    assert safety.override_precision == 1.0


def test_single_regression_stops_immediately(simulation) -> None:
    stop = simulation["single_regression"]["stop"]
    assert stop.should_stop is True
    assert TopicAuthorityPilotStopReason.REGRESSION_BUDGET_EXCEEDED in stop.reasons
    assert stop.recommended_mode is ResolverAuthorityMode.SHADOW


def test_precision_below_ninety_at_thirty_stops(simulation) -> None:
    stop = simulation["precision_failure"]["stop"]
    assert stop.should_stop is True
    assert TopicAuthorityPilotStopReason.OVERRIDE_PRECISION_BELOW_THRESHOLD in stop.reasons


def test_precision_below_ninety_at_twenty_nine_does_not_stop(simulation) -> None:
    assert simulation["precision_before_minimum"]["safety"].audited_override_count == 29
    assert simulation["precision_before_minimum"]["stop"].should_stop is False


def test_thirtieth_audit_activates_precision_check(simulation) -> None:
    assert simulation["precision_failure"]["safety"].audited_override_count == 30
    assert simulation["precision_failure"]["stop"].should_stop is True


@pytest.mark.parametrize(
    "cohort",
    [
        "contract_violation", "candidate_violation", "fingerprint_violation",
        "format_violation", "reader_intent_violation",
    ],
)
def test_every_contract_or_boundary_violation_stops(simulation, cohort) -> None:
    stop = simulation[cohort]["stop"]
    assert stop.should_stop is True
    assert stop.recommended_mode is ResolverAuthorityMode.SHADOW


def test_candidate_violation_has_specific_safety_count(simulation) -> None:
    assert simulation["candidate_violation"]["safety"].accepted_candidate_violation_count == 1


def test_fingerprint_violation_has_specific_safety_count(simulation) -> None:
    assert simulation["fingerprint_violation"]["safety"].accepted_fingerprint_violation_count == 1


def test_format_and_reader_intent_violations_are_detection_only(simulation) -> None:
    assert simulation["format_violation"]["safety"].format_authority_violation_count == 1
    assert simulation["reader_intent_violation"]["safety"].reader_intent_authority_violation_count == 1
    assert simulation["production_mutation"] is False


def test_provider_failure_blocks_and_preserves_deterministic_topic(simulation) -> None:
    metrics = simulation["provider_failure_only"]["operational"]
    assert metrics.authoritative_topic_overrides == 0
    assert metrics.deterministic_topic_preserved == 1
    assert metrics.provider_failures == 1
    assert metrics.fallbacks == 1


def test_provider_failure_is_not_incorrect_override_or_immediate_stop(simulation) -> None:
    cohort = simulation["provider_failure_only"]
    assert cohort["safety"].audited_incorrect_override_count == 0
    assert cohort["stop"].should_stop is False


def test_no_topic_change_excluded_from_override_count(simulation) -> None:
    metrics = simulation["distribution"]["operational"]
    assert simulation["scenario_distribution"]["same_label"] == 10
    assert metrics.authoritative_topic_overrides == 35


def test_no_topic_change_excluded_from_audit_sample(simulation) -> None:
    assert simulation["clean"]["safety"].audited_override_count == 30
    assert simulation["duplicate_audit_rejected"] is True


def test_shadow_override_count_is_zero(simulation) -> None:
    metrics = simulation["shadow"]["operational"]
    assert metrics.authoritative_topic_overrides == 0
    assert metrics.resolver_adjudicated_accepted == 20


def test_limited_mode_applies_only_eligible_changed_topics(simulation) -> None:
    metrics = simulation["distribution"]["operational"]
    assert metrics.authoritative_topic_overrides == 35
    assert metrics.deterministic_topic_preserved == 40


@pytest.mark.parametrize(
    "kind",
    ["low_confidence", "review_required", "ambiguity", "invalid_response"],
)
def test_policy_and_response_scenarios_are_present_and_blocked(simulation, kind) -> None:
    assert simulation["scenario_distribution"][kind] > 0
    assert simulation["distribution"]["operational"].deterministic_topic_preserved >= 1


def test_kill_switch_recommendation_is_shadow(simulation) -> None:
    assert simulation["rollback"]["at_stop"]["stop"].recommended_mode is ResolverAuthorityMode.SHADOW


def test_rollback_is_explicit_configuration_only(simulation) -> None:
    rollback = simulation["rollback"]
    assert rollback["before"]["operational"].authoritative_topic_overrides == 5
    assert rollback["future_deterministic_topics_preserved"] is True


def test_post_rollback_has_no_new_authoritative_overrides(simulation) -> None:
    assert simulation["rollback"]["post_rollback_authoritative_overrides"] == 0


def test_historical_authority_metrics_are_preserved(simulation) -> None:
    assert simulation["rollback"]["historical_authoritative_overrides"] == 5


def test_duplicate_audit_protection_is_active(simulation) -> None:
    assert simulation["duplicate_audit_rejected"] is True


def test_human_audit_outcomes_are_explicit_not_provider_generated(simulation) -> None:
    assert simulation["single_regression"]["safety"].audited_incorrect_override_count == 1
    assert simulation["clean"]["safety"].audited_incorrect_override_count == 0


def test_deterministic_replay_is_exact() -> None:
    assert run_simulation(persist=False) == run_simulation(persist=False)


def test_independent_cohorts_do_not_leak_metrics(simulation) -> None:
    assert simulation["clean"]["operational"].articles_processed == 35
    assert simulation["single_regression"]["operational"].articles_processed == 1
    assert simulation["shadow"]["operational"].articles_processed == 20


def test_no_real_provider_calls(simulation) -> None:
    assert simulation["real_provider_calls"] == 0


def test_no_production_mutation(simulation) -> None:
    assert simulation["production_mutation"] is False


def test_canary_classification_and_next_step(simulation) -> None:
    assert simulation["offline_canary_classification"] == "CANARY_SAFE"
    assert simulation["next_step_decision"] == "READY_FOR_CONTROLLED_TOPIC_AUTHORITY_CANARY_IMPLEMENTATION"


def test_script_has_no_openai_or_benchmark_batch_dependency() -> None:
    source = (
        PROJECT_ROOT / "examples" / "run_limited_topic_authority_offline_canary.py"
    ).read_text(encoding="utf-8")
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "openai" not in imported
    lowered = source.lower()
    assert all("batch_" + suffix not in lowered for suffix in ("07", "08", "09"))
