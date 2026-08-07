"""Tests for deterministic editorial analysis of benchmark batch 01."""

import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_benchmark_batch_01_analysis import (
    BATCH_ROOT,
    _summary,
    _unique_warnings,
    analyze_batch,
    parse_source,
    read_manifest,
    render_console,
    render_json,
    render_markdown,
)
from src.assessment.risk_level import RiskLevel
from src.workflows.experimental_editorial_strategy_workflow import (
    ExperimentalEditorialStrategyWorkflow,
)


CASE_KEYS = {
    "id",
    "source_name",
    "benchmark_category",
    "risk_level",
    "risk_topics",
    "risk_warnings",
    "generation_allowed",
    "content_type",
    "content_confidence",
    "content_warnings",
    "editorial_format",
    "format_confidence",
    "format_warnings",
    "reader_intent",
    "reader_intent_confidence",
    "reader_intent_warnings",
    "base_strategy",
    "adapted_strategy",
}
STRATEGY_KEYS = {
    "article_length",
    "article_depth",
    "writing_mode",
    "target_word_count",
    "warnings",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real deterministic analysis for report assertions."""
    return analyze_batch()


def test_exactly_ten_cases_preserve_manifest_order(
    analysis: dict[str, object],
) -> None:
    """Analyze all ten cases in unchanged manifest order."""
    cases = analysis["cases"]

    assert analysis["batch"] == "batch_01"
    assert analysis["case_count"] == 10
    assert len(cases) == 10
    assert tuple(case["id"] for case in cases) == tuple(
        entry["id"] for entry in read_manifest()
    )


def test_source_files_are_read_without_rewriting() -> None:
    """Read exact non-empty source fields and metadata from each local file."""
    for entry in read_manifest():
        source = parse_source(BATCH_ROOT / entry["source_file"])
        assert source.case_id == entry["id"]
        assert source.source_name == entry["source_name"]
        assert source.benchmark_category == entry["benchmark_category"]
        assert source.title
        assert source.body
        assert source.source_url.startswith("https://")


def test_workflow_receives_exact_metadata_mapping() -> None:
    """Pass Arabic and supplied category while leaving missing metadata empty."""
    workflow = Mock(wraps=ExperimentalEditorialStrategyWorkflow())

    analyze_batch(workflow=workflow)

    assert workflow.process.call_count == 10
    for call_args, entry in zip(workflow.process.call_args_list, read_manifest()):
        source = parse_source(BATCH_ROOT / entry["source_file"])
        assert call_args.kwargs == {
            "title": source.title,
            "body": source.body,
            "source_name": source.source_name,
            "source_url": source.source_url,
            "published_at": None,
            "language": "ar",
            "country": None,
            "author": None,
            "images": (),
            "attachments": (),
            "category": source.benchmark_category,
            "tags": (),
            "user_instruction": None,
        }


def test_case_records_contain_exact_analysis_fields(
    analysis: dict[str, object],
) -> None:
    """Record every required risk, classification, intent, and strategy value."""
    public = json.loads(render_json(analysis))

    for case in public["cases"]:
        assert set(case) == CASE_KEYS
        assert case["risk_level"] in tuple(level.value for level in RiskLevel)
        assert case["content_type"]
        assert case["content_confidence"]
        assert case["editorial_format"]
        assert case["format_confidence"]
        assert case["reader_intent"]
        assert case["reader_intent_confidence"]
        assert set(case["base_strategy"]) == STRATEGY_KEYS
        assert set(case["adapted_strategy"]) == STRATEGY_KEYS
        assert case["base_strategy"]["article_length"]
        assert case["adapted_strategy"]["writing_mode"]


def test_json_excludes_articles_prompts_and_internal_fields(
    analysis: dict[str, object],
) -> None:
    """Exclude full source bodies, prompts, and internal calculation metadata."""
    output = render_json(analysis)
    public = json.loads(output)

    assert "body" not in output.lower()
    assert "prompt" not in output.lower()
    assert "_strategy_changed" not in output
    assert all(set(case) == CASE_KEYS for case in public["cases"])
    for entry in read_manifest():
        source = parse_source(BATCH_ROOT / entry["source_file"])
        assert source.body not in output


def test_markdown_has_exactly_ten_rows_and_unique_warnings(
    analysis: dict[str, object],
) -> None:
    """Render one row per case and deduplicate warning codes in every row."""
    output = render_markdown(analysis)
    rows = [line for line in output.splitlines() if line.startswith("| 0")]

    assert len(rows) == 10
    for row, case in zip(rows, analysis["cases"]):
        warning_cell = row.strip("| ").split(" | ")[-1]
        warnings = () if warning_cell == "None" else tuple(
            warning_cell.split(", ")
        )
        assert warnings == _unique_warnings(case)
        assert len(warnings) == len(set(warnings))


def test_summary_counts_equal_case_data(analysis: dict[str, object]) -> None:
    """Derive risk, blocking, and strategy-change totals from case data."""
    summary = _summary(analysis)
    cases = analysis["cases"]
    risk_distribution = summary["risk_distribution"]

    assert sum(risk_distribution.values()) == 10
    assert summary["generation_blocked"] == sum(
        not case["generation_allowed"] for case in cases
    )
    assert summary["strategy_changed"] + summary["strategy_unchanged"] == 10
    markdown = render_markdown(analysis)
    assert f"Generation Blocked:\n{summary['generation_blocked']}" in markdown
    assert f"Format Strategy Changed:\n{summary['strategy_changed']}" in markdown
    assert f"Format Strategy Unchanged:\n{summary['strategy_unchanged']}" in markdown


def test_checked_in_reports_match_deterministic_rendering(
    analysis: dict[str, object],
) -> None:
    """Keep both persisted reports byte-identical to deterministic rendering."""
    expected_json = render_json(analysis)
    expected_markdown = render_markdown(analysis)

    assert (BATCH_ROOT / "analysis.json").read_text(
        encoding="utf-8"
    ) == expected_json
    assert (BATCH_ROOT / "analysis.md").read_text(
        encoding="utf-8"
    ) == expected_markdown
    assert render_json(analysis) == expected_json
    assert render_markdown(analysis) == expected_markdown
    assert render_console(analysis) == render_console(analysis)


def test_analysis_requires_no_network_api_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analyze all cases with sockets and environment reads disabled."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    result = analyze_batch()
    assert result["case_count"] == 10
