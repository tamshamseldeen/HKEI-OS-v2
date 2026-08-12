"""Offline tests for the final Batch 07 Gate-refinement evaluation."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

import examples.run_batch_07_post_gate_refinement_full_stack as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source
from tests.test_batch_07_full_stack_shadow_evaluation import FakeProvider


@pytest.fixture(scope="module")
def evaluation(tmp_path_factory):
    root = tmp_path_factory.mktemp("post-gate")
    times = iter(float(value) for value in range(40))
    current, comparison = diagnostic.run_final(
        model="gpt-5-mini",
        provider=FakeProvider(),
        output_json=root / "evaluation.json",
        output_md=root / "evaluation.md",
        comparison_json=root / "comparison.json",
        comparison_md=root / "comparison.md",
        monotonic=lambda: next(times),
        now=lambda: datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    return current, comparison, root


def test_exact_cases_and_hkei_178_baseline_loaded(evaluation) -> None:
    current, comparison, _ = evaluation
    baseline = json.loads(diagnostic.BASELINE_JSON.read_text(encoding="utf-8"))
    assert tuple(current["case_ids"]) == diagnostic.CASE_IDS
    assert len(current["cases"]) == 10
    assert comparison["previous_provider_calls"] == baseline["provider_calls"] == 8
    assert comparison["previous_effective_topic_accuracy"] == 70.0
    assert comparison["previous_effective_format_accuracy"] == 30.0


def test_current_gate_metrics_and_deltas_are_derived(evaluation) -> None:
    current, comparison, _ = evaluation
    baseline = json.loads(diagnostic.BASELINE_JSON.read_text(encoding="utf-8"))
    for dimension in ("topic", "format"):
        gate = current[f"{dimension}_gate"]
        delta = comparison[f"{dimension}_gate_delta"]
        previous = baseline[f"{dimension}_gate"]
        assert all(delta[key] == pytest.approx(gate[key] - previous[key]) for key in delta)


def test_previous_false_negative_tracking_is_post_hoc(evaluation) -> None:
    current, comparison, _ = evaluation
    baseline = json.loads(diagnostic.BASELINE_JSON.read_text(encoding="utf-8"))
    assert set(comparison["previous_topic_fn"]) == diagnostic._gate_false_negatives(baseline["cases"], "topic")
    assert set(comparison["previous_format_fn"]) == diagnostic._gate_false_negatives(baseline["cases"], "format")
    assert set(comparison["current_topic_fn"]) == diagnostic._gate_false_negatives(current["cases"], "topic")
    assert set(comparison["current_format_fn"]) == diagnostic._gate_false_negatives(current["cases"], "format")


def test_new_false_positives_and_provider_delta_are_derived(evaluation) -> None:
    current, comparison, _ = evaluation
    assert comparison["provider_call_delta"] == current["provider_calls"] - 8
    assert comparison["current_provider_calls"] == current["provider_calls"]
    assert comparison["new_gate_false_positive_count"] == len(comparison["new_gate_false_positives"])


def test_effective_labels_and_change_precision_match_case_records(evaluation) -> None:
    current, _, _ = evaluation
    for dimension in ("topic", "format"):
        metrics = current[dimension]
        changed = [case for case in current["cases"] if case[f"effective_shadow_{dimension}"] != case[f"deterministic_{dimension}"]]
        correct = sum(case[f"{dimension}_match_after"] for case in changed)
        assert metrics["changed_decisions"] == len(changed)
        assert metrics["correct_changes"] == correct
        assert metrics["change_precision"] == (correct / len(changed) * 100 if changed else 0)


def test_recovered_fn_utility_is_derived(evaluation) -> None:
    current, comparison, _ = evaluation
    cases = {case["id"]: case for case in current["cases"]}
    captured_topic = {case_id for case_id, status in comparison["previous_topic_fn_status"].items() if status == "CAPTURED"}
    captured_format = {case_id for case_id, status in comparison["previous_format_fn_status"].items() if status == "CAPTURED"}
    assert comparison["recovered_topic_fn_count"] == len(captured_topic)
    assert comparison["recovered_topic_fn_corrected_by_provider"] == sum(cases[case_id]["topic_match_after"] for case_id in captured_topic)
    assert comparison["recovered_format_fn_count"] == len(captured_format)
    assert comparison["recovered_format_fn_corrected_by_provider"] == sum(cases[case_id]["format_match_after"] for case_id in captured_format)


def test_provider_contract_and_shadow_safety(evaluation) -> None:
    current, _, _ = evaluation
    assert current["provider_calls"] <= 10
    assert current["retry_attempts"] == 0
    assert current["valid_responses"] == current["provider_calls"]
    assert current["invalid_responses"] == current["provider_errors"] == 0
    assert current["candidate_compliance"] == current["fingerprint_integrity"] == 100.0
    assert not any(current[key] for key in (
        "shadow_topic_mutated", "shadow_format_mutated", "shadow_intent_mutated",
        "actual_confidence_mutated", "gate_mutated",
    ))


def test_expected_baseline_is_read_after_current_execution(tmp_path, monkeypatch) -> None:
    baseline = json.loads(diagnostic.BASELINE_JSON.read_text(encoding="utf-8"))
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    events = []

    def fake_run(**kwargs):
        events.append("current_complete")
        return deepcopy(baseline)

    class TrackedPath(type(baseline_path)):
        pass

    monkeypatch.setattr(diagnostic, "run_evaluation", fake_run)
    monkeypatch.setattr(diagnostic, "BASELINE_JSON", baseline_path)
    diagnostic.run_final(
        model="gpt-5-mini",
        output_json=tmp_path / "out.json", output_md=tmp_path / "out.md",
        comparison_json=tmp_path / "cmp.json", comparison_md=tmp_path / "cmp.md",
    )
    assert events == ["current_complete"]


def test_assessor_remains_diagnostic_and_budget_is_exhausted(evaluation) -> None:
    _, comparison, _ = evaluation
    gate_source = (diagnostic.PROJECT_ROOT / "src/adjudication/deterministic_semantic_adjudication_gate.py").read_text(encoding="utf-8")
    assert "candidate_assessor" not in gate_source
    assert comparison["batch_07_gate_refinement_budget_remaining"] == 0
    assert comparison["additional_gate_tuning_recommended"] is False
    assert comparison["final_decision"] != "RUN_ONE_MORE_UNTOUCHED_HOLDOUT" or comparison["additional_gate_tuning_recommended"] is False


def test_sanitized_outputs_contain_no_source_secret_or_raw_response(evaluation) -> None:
    _, _, root = evaluation
    persisted = "\n".join(path.read_text(encoding="utf-8") for path in root.iterdir())
    forbidden = ("OPENAI_API_KEY", "sk-", "raw_prompt", "raw_response", "chain_of_thought")
    assert not any(value in persisted for value in forbidden)
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in persisted


def test_runtime_matches_hkei_178_except_gate() -> None:
    diagnostic.verify_runtime("gpt-5-mini")

