"""Integrity tests for the historical offline Resolver shadow evaluation."""

import json

import pytest

import examples.run_limited_resolver_historical_shadow_evaluation as audit
from examples.run_benchmark_batch_02_validation import parse_source
from src.resolution import EditorialResolutionSource, EditorialResolutionStatus


@pytest.fixture(scope="module")
def result():
    return audit.analyze()


def test_expected_labels_are_joined_only_after_resolution(monkeypatch) -> None:
    original = audit._join_truth
    observed = {}
    def guarded(cases, paths):
        observed["count"] = len(cases)
        assert all("expected_topic" not in case for case in cases)
        assert all("resolved_topic" in case and "resolved_format" in case for case in cases)
        return original(cases, paths)
    monkeypatch.setattr(audit, "_join_truth", guarded)
    assert audit.analyze()["cases_evaluated"] == observed["count"] == 60


def test_result_is_deterministic(result) -> None:
    assert result == audit.analyze()


@pytest.mark.parametrize("dimension", ("topic", "format", "reader_intent"))
def test_dimension_metrics_are_derived(result, dimension) -> None:
    cases = result["cases"]
    metrics = result[dimension]
    assert metrics["deterministic_accuracy"] == pytest.approx(sum(case[f"deterministic_{dimension}_correct"] for case in cases) / 60 * 100)
    assert metrics["resolved_accuracy"] == pytest.approx(sum(case[f"resolved_{dimension}_correct"] for case in cases) / 60 * 100)
    assert metrics["improvements"] == sum(not case[f"deterministic_{dimension}_correct"] and case[f"resolved_{dimension}_correct"] for case in cases)
    assert metrics["regressions"] == sum(case[f"deterministic_{dimension}_correct"] and not case[f"resolved_{dimension}_correct"] for case in cases)


def test_reader_intent_is_unchanged(result) -> None:
    assert result["reader_intent"]["delta"] == 0
    assert result["reader_intent"]["regressions"] == 0
    assert all(case["deterministic_reader_intent"] == case["resolved_reader_intent"] for case in result["cases"])


def test_full_accuracy_is_derived(result) -> None:
    cases = result["cases"]
    assert result["deterministic_full_accuracy"] == pytest.approx(sum(case["deterministic_full_correct"] for case in cases) / 60 * 100)
    assert result["resolved_full_accuracy"] == pytest.approx(sum(case["resolved_full_correct"] for case in cases) / 60 * 100)


@pytest.mark.parametrize("dimension", ("topic", "format", "reader_intent"))
def test_status_and_source_distributions_are_complete(result, dimension) -> None:
    statuses = result["resolution_status_distribution"][dimension]
    sources = result["resolution_source_distribution"][dimension]
    assert set(statuses) == {item.value for item in EditorialResolutionStatus}
    assert set(sources) == {item.value for item in EditorialResolutionSource}
    assert sum(statuses.values()) == sum(sources.values()) == 60


def test_review_and_provider_used_metrics_are_derived(result) -> None:
    cases = result["cases"]
    assert result["cases_review_required"] == sum(case["review_required"] for case in cases)
    assert result["provider_used_count"] == sum(case["provider_used"] for case in cases)
    assert all(case["provider_used"] == ("ADJUDICATION" in (case["topic_source"], case["format_source"])) for case in cases)


@pytest.mark.parametrize("dimension", ("topic", "format"))
def test_override_precision_is_derived(result, dimension) -> None:
    cases = [case for case in result["cases"] if case[f"{dimension}_resolution_status"] == "ADJUDICATED_ACCEPTED" and case[f"deterministic_{dimension}"] != case[f"resolved_{dimension}"]]
    assert result[dimension]["adjudicated_overrides"] == len(cases)
    assert result[dimension]["correct_overrides"] == sum(case[f"resolved_{dimension}_correct"] for case in cases)


def test_fallback_never_mutates_baseline(result) -> None:
    assert result["fallback_mutation_count"] == 0
    for case in result["cases"]:
        if case["topic_resolution_status"] == "FALLBACK_ACCEPTED":
            assert case["resolved_topic"] == case["deterministic_topic"]
        if case["format_resolution_status"] == "FALLBACK_ACCEPTED":
            assert case["resolved_format"] == case["deterministic_format"]


def test_invalid_authority_safety_counters_are_zero(result) -> None:
    assert result["invalid_response_accepted_count"] == 0
    assert result["illegal_candidate_accepted_count"] == 0
    assert result["fingerprint_mismatch_accepted_count"] == 0
    assert result["missing_dimension_accepted_count"] == 0
    assert result["unexpected_dimension_authority_count"] == 0


def test_ambiguity_contract_is_preserved(result) -> None:
    ambiguous = [case for case in result["cases"] if case["ambiguity_remaining"] and case["provider_used"]]
    assert all(case["review_required"] for case in ambiguous)
    assert all("ADJUDICATION_AMBIGUITY_REMAINS" in case["warnings"] for case in ambiguous)


def test_format_v2_never_has_direct_authority(result) -> None:
    assert result["v2_direct_override_count"] == 0
    assert all(case["format_source"] != "FORMAT_V2_SHADOW" for case in result["cases"])
    assert result["v1_v2_disagreement_count"] == sum(case["v1_v2_disagreement"] for case in result["cases"])


def test_batch_metrics_cover_exact_historical_inventory(result) -> None:
    assert tuple(result["batch_metrics"]) == audit.BATCH_IDS
    assert all(item["case_count"] == 10 for item in result["batch_metrics"].values())
    assert sum(item["case_count"] for item in result["batch_metrics"].values()) == 60


def test_historical_availability_is_explicit(result) -> None:
    allowed = {"PERSISTED_VALIDATED", "FAKE_DETERMINISTIC", "PROVIDER_UNAVAILABLE", "NOT_REQUIRED"}
    assert set(result["adjudication_source_distribution"]) <= allowed
    assert sum(result["adjudication_source_distribution"].values()) == 60


def test_no_live_provider_or_production_mutation(result) -> None:
    assert result["real_provider_calls"] == 0
    assert result["production_topic_mutated"] is False
    assert result["production_format_mutated"] is False
    assert result["production_reader_intent_mutated"] is False
    assert result["gate_mutated"] is False and result["format_v2_mutated"] is False


def test_persisted_outputs_contain_no_source_bodies_or_secrets() -> None:
    persisted = audit.OUTPUT_JSON.read_text(encoding="utf-8") + audit.OUTPUT_MD.read_text(encoding="utf-8")
    assert not any(value in persisted for value in ("OPENAI_API_KEY", "sk-", "raw_prompt", "raw_response"))
    for batch in audit.BATCH_IDS:
        root = audit.PROJECT_ROOT / "benchmark" / batch
        for item in audit.read_manifest(root):
            assert parse_source(root / item["source_file"]).body not in persisted


def test_output_cases_have_required_contract_without_source_body(result) -> None:
    required = {
        "deterministic_topic", "resolved_topic", "deterministic_format", "resolved_format",
        "deterministic_reader_intent", "resolved_reader_intent", "topic_resolution_status",
        "format_resolution_status", "reader_intent_resolution_status", "topic_source",
        "format_source", "reader_intent_source", "review_required", "warnings", "provider_used",
    }
    assert all(required <= set(case) for case in result["cases"])
    assert all("body" not in case and "source_body" not in case for case in result["cases"])
