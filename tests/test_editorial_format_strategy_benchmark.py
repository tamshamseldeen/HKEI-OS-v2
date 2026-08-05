"""Tests for the deterministic editorial format strategy benchmark."""

from dataclasses import replace
import os

import pytest

from examples.run_editorial_format_strategy_benchmark import (
    STRATEGY_BENCHMARK_CASES,
    _matches_expected,
    _source_fields,
    run_benchmark,
)
from src.strategy.editorial_format_strategy_adapter import (
    EditorialFormatStrategyAdapter,
)
from src.strategy.editorial_strategy import EditorialStrategy
from src.workflows.editorial_format_result import EditorialFormatResult
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_strategy_result import EditorialStrategyResult
from src.workflows.editorial_strategy_workflow import EditorialStrategyWorkflow


def _run_case(
    case_index: int,
) -> tuple[EditorialStrategyResult, EditorialFormatResult, EditorialStrategy]:
    """Run real workflows and adaptation for one indexed benchmark case."""
    benchmark_case = STRATEGY_BENCHMARK_CASES[case_index]
    fields = _source_fields(benchmark_case.source_case)
    strategy_result = EditorialStrategyWorkflow().process(**fields)
    format_result = EditorialFormatWorkflow().process(**fields)
    ingestion = strategy_result.intent_result.classification_result.ingestion
    adapted = EditorialFormatStrategyAdapter().adapt(
        strategy=strategy_result.strategy,
        format_classification=format_result.format_classification,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
    )
    return strategy_result, format_result, adapted


def test_exactly_four_strategy_benchmark_cases_exist() -> None:
    """Reuse exactly four source cases in their deterministic order."""
    assert tuple(
        case.source_case.name for case in STRATEGY_BENCHMARK_CASES
    ) == (
        "traffic_service",
        "sports_feature",
        "sports_guide",
        "sports_result",
    )


@pytest.mark.parametrize("case_index", range(4))
def test_adapted_strategy_and_required_reason_match(case_index: int) -> None:
    """Match every specified strategy field and required adapter reason."""
    _, format_result, adapted = _run_case(case_index)
    expected = STRATEGY_BENCHMARK_CASES[case_index].expected

    assert _matches_expected(
        strategy=adapted,
        editorial_format=format_result.format_classification.editorial_format,
        expected=expected,
    )
    assert expected.required_reason_code in adapted.reason_codes


def test_base_strategy_remains_unchanged() -> None:
    """Leave the real base strategy unchanged after additive adaptation."""
    benchmark_case = STRATEGY_BENCHMARK_CASES[0]
    fields = _source_fields(benchmark_case.source_case)
    strategy_result = EditorialStrategyWorkflow().process(**fields)
    format_result = EditorialFormatWorkflow().process(**fields)
    ingestion = strategy_result.intent_result.classification_result.ingestion
    base_strategy = strategy_result.strategy
    snapshot = replace(base_strategy)

    EditorialFormatStrategyAdapter().adapt(
        strategy=base_strategy,
        format_classification=format_result.format_classification,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
    )

    assert base_strategy == snapshot


def test_success_summary_exit_code_and_output_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report four matches, full accuracy, success, and deterministic order."""
    status = run_benchmark()
    output = capsys.readouterr().out

    assert status == 0
    assert "Total Cases:\n4" in output
    assert "Matched:\n4" in output
    assert "Mismatched:\n0" in output
    assert "Accuracy:\n100.00%" in output
    positions = [
        output.index(f"=== {case.source_case.name} ===")
        for case in STRATEGY_BENCHMARK_CASES
    ]
    assert positions == sorted(positions)
    assert positions[-1] < output.index("=== SUMMARY ===")


def test_forced_expected_mismatch_returns_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return failure when one expectation is intentionally made incorrect."""
    first = STRATEGY_BENCHMARK_CASES[0]
    wrong_expected = replace(first.expected, target_word_count=451)
    cases = (
        replace(first, expected=wrong_expected),
        *STRATEGY_BENCHMARK_CASES[1:],
    )

    status = run_benchmark(cases=cases)
    output = capsys.readouterr().out

    assert status == 1
    assert "Expected Match:\nNO" in output
    assert "Matched:\n3" in output
    assert "Mismatched:\n1" in output
    assert "Accuracy:\n75.00%" in output


def test_benchmark_does_not_access_environment_or_apis(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run entirely locally without reading environment configuration."""
    def fail_environment_access(*args: object, **kwargs: object) -> str:
        raise AssertionError("environment access is forbidden")

    monkeypatch.setattr(os, "getenv", fail_environment_access)

    assert run_benchmark() == 0
    capsys.readouterr()
