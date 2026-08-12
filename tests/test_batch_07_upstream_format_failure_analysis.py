"""Offline checks for the persisted Batch 07 upstream Format diagnosis."""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from examples import run_batch_07_upstream_format_failure_analysis as diagnostic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_07"
EXPECTED_SHA256 = "cafddc7533a80dc834abe96606ae770a458d462893086be16fcea95554c6c036"
EXPECTED_CASES = ("061", "062", "063", "065", "066", "068")


@pytest.fixture(scope="module")
def result() -> dict:
    return diagnostic.analyze()


def test_exactly_six_remaining_format_false_negatives_are_derived(result: dict) -> None:
    assert tuple(result["remaining_format_fn_cases"]) == EXPECTED_CASES
    assert result["remaining_format_fn_count"] == 6


def test_fn_selection_is_not_hard_coded() -> None:
    source = Path(diagnostic.__file__).read_text(encoding="utf-8")
    analyze_node = next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "analyze"
    )
    analyze_source = ast.get_source_segment(source, analyze_node)
    assert analyze_source is not None
    assert "remaining = [" in analyze_source
    assert not any(f'"{case_id}"' in analyze_source for case_id in EXPECTED_CASES)


def test_every_case_has_an_allowed_failure_stage(result: dict) -> None:
    assert all(
        trace["primary_failure_stage"] in diagnostic.FAILURE_STAGES
        for trace in result["case_traces"]
    )


def test_every_case_has_an_allowed_expected_format_reachability(result: dict) -> None:
    assert all(
        trace["expected_format_reachability"] in diagnostic.REACHABILITY
        for trace in result["case_traces"]
    )


def test_every_case_has_an_allowed_wrong_format_path(result: dict) -> None:
    assert all(
        trace["wrong_format_path"] in diagnostic.WRONG_PATHS
        for trace in result["case_traces"]
    )


def test_observed_confusion_pairs_are_exact(result: dict) -> None:
    assert result["expected_to_predicted_format_pairs"] == {
        "EXPLAINER->STANDARD_NEWS": 1,
        "RESULT_REPORT->STANDARD_NEWS": 1,
        "STANDARD_NEWS->BREAKING": 1,
        "STANDARD_NEWS->RESULT_REPORT": 2,
        "TREND_UPDATE->STANDARD_NEWS": 1,
    }


def test_reader_intent_dependency_is_measured(result: dict) -> None:
    assert result["direct_intent_failures"] == 0
    assert result["format_downstream_intent_failures"] == 7
    assert result["other_upstream_intent_failures"] == 0


def test_false_sufficient_assessments_are_audited(result: dict) -> None:
    assert {(item["id"], item["candidate"]) for item in result["false_sufficient_cases"]} == {
        ("063", "RESULT_REPORT"), ("066", "RESULT_REPORT")
    }
    assert all(item["concerns_format"] for item in result["false_sufficient_cases"])
    assert all(
        item["origin_relative_to_primary_failure"] == "AFTER_PRIMARY_FAILURE"
        for item in result["false_sufficient_cases"]
    )


def test_confidence_is_classified_as_an_upstream_symptom(result: dict) -> None:
    assert set(result["false_confidence_cases"]) == set(EXPECTED_CASES)
    assert all(
        trace["confidence_audit"] in {"FALSE_HIGH_CONFIDENCE", "FALSE_MEDIUM_CONFIDENCE"}
        and trace["confidence_role"] == "SYMPTOM_OF_UPSTREAM_REPRESENTATION"
        for trace in result["case_traces"]
    )


def test_provider_opportunity_is_classified_without_calling_provider(result: dict) -> None:
    assert result["provider_opportunity_counts"] == {"LIKELY_YES": 6}
    assert result["provider_calls"] == 0


def test_common_root_cause_calculation_is_deterministic(result: dict) -> None:
    assert result["shared_root_cause"] == "FORMAT_COMPONENTS_NOT_COMPOSED_INTO_RELATIONSHIPS"
    assert result["shared_root_cause_count"] == 4
    assert diagnostic.analyze() == result


def test_gate_budget_is_permanently_zero(result: dict) -> None:
    assert result["gate_refinement_budget_remaining"] == 0
    assert result["gate_tuning_closed"] is True
    assert result["maximum_future_bounded_format_implementations"] == 1


def test_diagnostic_imports_no_provider_or_network_modules() -> None:
    tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        term in module.casefold()
        for module in imported
        for term in ("openai", "provider", "requests", "httpx", "urllib")
    )


def test_diagnostic_paths_are_confined_to_outputs_and_persisted_inputs() -> None:
    assert diagnostic.INPUT_JSON == BATCH_ROOT / "post_gate_refinement_full_stack_evaluation.json"
    assert diagnostic.OUTPUT_JSON == BATCH_ROOT / "upstream_format_failure_analysis.json"
    assert diagnostic.OUTPUT_MD == BATCH_ROOT / "upstream_format_failure_analysis.md"
    assert "src" not in {part.casefold() for path in (diagnostic.OUTPUT_JSON, diagnostic.OUTPUT_MD) for part in path.parts}


def test_expected_labels_are_frozen() -> None:
    expected = BATCH_ROOT / "expected.json"
    assert hashlib.sha256(expected.read_bytes()).hexdigest() == EXPECTED_SHA256
    assert diagnostic.EXPECTED_SHA256 == EXPECTED_SHA256


def test_outputs_contain_no_source_body_or_raw_provider_payload(result: dict) -> None:
    serialized = json.dumps(result, ensure_ascii=False).casefold()
    sources = [
        (BATCH_ROOT / case_id / "source.md").read_text(encoding="utf-8")
        for case_id in EXPECTED_CASES
    ]
    assert not any(source in serialized for source in sources)
    assert not any(term in serialized for term in ("raw_prompt", "raw_response", "api_key"))


def test_decision_contract_remains_diagnostic_and_bounded(result: dict) -> None:
    assert result["fix_scope_classification"] == "BOUNDED_FORMAT_EVIDENCE_FIX"
    assert result["fix_value"] == "HIGH"
    assert result["overfitting_risk"] == "HIGH"
    assert result["resolver_readiness"] == "YES_LIMITED"
    assert result["final_recommendation"] == "IMPLEMENT_ONE_BOUNDED_UPSTREAM_FORMAT_FIX"
