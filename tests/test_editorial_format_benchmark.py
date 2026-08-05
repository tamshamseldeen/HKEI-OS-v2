"""Tests for the deterministic editorial format benchmark example."""

from dataclasses import replace
import os
from unittest.mock import Mock

import pytest

from examples.run_editorial_format_benchmark import (
    BENCHMARK_CASES,
    run_benchmark,
)
from src.formatting.editorial_format import EditorialFormat
from src.workflows.editorial_format_result import EditorialFormatResult
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow


EXPECTED_FORMATS = (
    EditorialFormat.SERVICE,
    EditorialFormat.FEATURE,
    EditorialFormat.GUIDE,
    EditorialFormat.RESULT_REPORT,
)


def test_exactly_four_cases_with_expected_formats() -> None:
    """Define exactly the four specified cases in deterministic order."""
    assert tuple(case.name for case in BENCHMARK_CASES) == (
        "traffic_service",
        "sports_feature",
        "sports_guide",
        "sports_result",
    )
    assert tuple(case.expected_format for case in BENCHMARK_CASES) == (
        EXPECTED_FORMATS
    )


@pytest.mark.parametrize(
    ("case_index", "expected"),
    tuple(enumerate(EXPECTED_FORMATS)),
)
def test_each_benchmark_case_matches(
    case_index: int,
    expected: EditorialFormat,
) -> None:
    """Match each representative case using the real deterministic workflow."""
    case = BENCHMARK_CASES[case_index]

    result = EditorialFormatWorkflow().process(
        title=case.title,
        body=case.body,
        source_name=case.source_name,
        source_url=case.source_url,
        category=case.category,
        tags=case.tags,
        user_instruction=case.user_instruction,
    )

    assert result.format_classification.editorial_format is expected


def test_success_output_summary_and_order(capsys: pytest.CaptureFixture[str]) -> None:
    """Print ordered cases and a fully matched summary with success status."""
    status = run_benchmark()
    output = capsys.readouterr().out

    assert status == 0
    assert "Total Cases:\n4" in output
    assert "Matched:\n4" in output
    assert "Mismatched:\n0" in output
    assert "Accuracy:\n100.00%" in output
    positions = [output.index(f"=== {case.name} ===") for case in BENCHMARK_CASES]
    assert positions == sorted(positions)
    assert positions[-1] < output.index("=== SUMMARY ===")


def test_forced_mismatch_returns_failure(capsys: pytest.CaptureFixture[str]) -> None:
    """Return failure and accurate totals when one prediction is forced to differ."""
    real_workflow = EditorialFormatWorkflow()
    results: list[EditorialFormatResult] = []
    for case in BENCHMARK_CASES:
        results.append(
            real_workflow.process(
                title=case.title,
                body=case.body,
                source_name=case.source_name,
                source_url=case.source_url,
                category=case.category,
                tags=case.tags,
                user_instruction=case.user_instruction,
            )
        )
    first = results[0]
    wrong_classification = replace(
        first.format_classification,
        editorial_format=EditorialFormat.ANALYSIS,
    )
    results[0] = replace(first, format_classification=wrong_classification)
    workflow = Mock(spec=EditorialFormatWorkflow)
    workflow.process.side_effect = results

    status = run_benchmark(workflow=workflow)
    output = capsys.readouterr().out

    assert status == 1
    assert "Match:\nNO" in output
    assert "Matched:\n3" in output
    assert "Mismatched:\n1" in output
    assert "Accuracy:\n75.00%" in output
    assert workflow.process.call_count == 4


def test_benchmark_does_not_access_environment_or_apis(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Complete locally without reading environment variables or API clients."""
    def fail_environment_access(*args: object, **kwargs: object) -> str:
        raise AssertionError("environment access is forbidden")

    monkeypatch.setattr(os, "getenv", fail_environment_access)

    assert run_benchmark() == 0
    capsys.readouterr()
