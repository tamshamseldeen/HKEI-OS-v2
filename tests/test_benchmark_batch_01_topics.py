"""Tests for the deterministic Batch 01 topic benchmark report."""

import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_benchmark_batch_01_analysis import BATCH_ROOT, parse_source, read_manifest
from examples.run_benchmark_batch_01_topics import (
    EXPECTED_TOPICS,
    _summary,
    analyze_topics,
    render_console,
    render_json,
    render_markdown,
    run_benchmark,
)
from src.topic.topic_confidence import TopicConfidence
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


CASE_KEYS = {
    "id",
    "benchmark_category",
    "expected_topic",
    "predicted_topic",
    "confidence",
    "match",
    "reason_codes",
    "supporting_signals",
    "warnings",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real deterministic topic benchmark analysis."""
    return analyze_topics()


def test_exact_cases_order_and_expected_topics(
    analysis: dict[str, object],
) -> None:
    """Load exactly ten ordered cases with exact benchmark-only labels."""
    cases = analysis["cases"]
    manifest_ids = tuple(case["id"] for case in read_manifest())

    assert analysis["case_count"] == 10
    assert len(cases) == 10
    assert tuple(case["id"] for case in cases) == manifest_ids
    assert EXPECTED_TOPICS == (
        ("001", "ECONOMY"),
        ("002", "ECONOMY"),
        ("003", "TECHNOLOGY"),
        ("004", "WEATHER"),
        ("005", "GOVERNMENT"),
        ("006", "ECONOMY"),
        ("007", "ECONOMY"),
        ("008", "CULTURE"),
        ("009", "SPORTS"),
        ("010", "ECONOMY"),
    )
    assert tuple(case["expected_topic"] for case in cases) == tuple(
        expected for _, expected in EXPECTED_TOPICS
    )


def test_editorial_topic_workflow_receives_exact_metadata() -> None:
    """Use the additive workflow with exact source and missing metadata mapping."""
    workflow = Mock(wraps=EditorialTopicWorkflow())

    analyze_topics(workflow=workflow)

    assert workflow.process.call_count == 10
    for workflow_call, manifest_case in zip(
        workflow.process.call_args_list,
        read_manifest(),
    ):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert workflow_call.kwargs == {
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


def test_each_case_records_exact_topic_output_fields(
    analysis: dict[str, object],
) -> None:
    """Record prediction, confidence, explanations, warnings, and correct match."""
    for case in analysis["cases"]:
        assert set(case) == CASE_KEYS
        assert case["predicted_topic"]
        assert case["confidence"] in tuple(
            confidence.value for confidence in TopicConfidence
        )
        assert isinstance(case["reason_codes"], list)
        assert isinstance(case["supporting_signals"], list)
        assert isinstance(case["warnings"], list)
        assert case["match"] is (
            case["predicted_topic"] == case["expected_topic"]
        )


def test_json_is_safe_and_accuracy_is_numeric(
    analysis: dict[str, object],
) -> None:
    """Exclude source bodies, prompts, generation, and API metadata from JSON."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert isinstance(parsed["accuracy"], float)
    assert parsed["accuracy"] == 100.0
    for prohibited in ("prompt", "generation", "api_metadata"):
        assert prohibited not in output.lower()
    for manifest_case in read_manifest():
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_markdown_rows_and_summary_match_case_data(
    analysis: dict[str, object],
) -> None:
    """Render ten rows with consistent totals and confidence distribution."""
    markdown = render_markdown(analysis)
    rows = [line for line in markdown.splitlines() if line.startswith("| 0")]
    summary = _summary(analysis)

    assert len(rows) == 10
    assert f"Total Cases:\n{analysis['case_count']}" in markdown
    assert f"Matched:\n{analysis['matched']}" in markdown
    assert f"Mismatched:\n{analysis['mismatched']}" in markdown
    assert f"Accuracy:\n{analysis['accuracy']:.2f}%" in markdown
    assert sum(summary["confidence_distribution"].values()) == 10
    assert summary["conflict_warnings"] == sum(
        bool(
            {"CATEGORY_TOPIC_CONFLICT", "CONFLICTING_TOPIC_SIGNALS"}.intersection(
                case["warnings"]
            )
        )
        for case in analysis["cases"]
    )
    assert summary["low_confidence"] == sum(
        case["confidence"] == "LOW" for case in analysis["cases"]
    )


def test_topic_distribution_uses_prediction_first_occurrence_order(
    analysis: dict[str, object],
) -> None:
    """Summarize predictions in deterministic first-occurrence order."""
    summary = _summary(analysis)
    predicted_order = tuple(
        dict.fromkeys(case["predicted_topic"] for case in analysis["cases"])
    )

    assert tuple(summary["topic_distribution"]) == predicted_order
    markdown = render_markdown(analysis)
    positions = [
        markdown.index(f"{topic}: {summary['topic_distribution'][topic]}")
        for topic in predicted_order
    ]
    assert positions == sorted(positions)


def test_success_exit_code_and_console_order(
    analysis: dict[str, object],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return success and print every matched case in manifest order."""
    status = run_benchmark(analysis)
    output = capsys.readouterr().out

    assert status == 0
    assert "Matched:\n10" in output
    assert "Mismatched:\n0" in output
    assert "Accuracy:\n100.00%" in output
    positions = [output.index(f"{case_id} |") for case_id, _ in EXPECTED_TOPICS]
    assert positions == sorted(positions)
    assert "=== MISMATCHES ===" not in output


def test_forced_expected_mismatch_returns_failure_with_details(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Return failure and exact details when one benchmark expectation differs."""
    forced_expectations = (
        ("001", "SPORTS"),
        *EXPECTED_TOPICS[1:],
    )
    mismatch_analysis = analyze_topics(expected_topics=forced_expectations)

    status = run_benchmark(mismatch_analysis)
    output = capsys.readouterr().out

    assert status == 1
    assert mismatch_analysis["matched"] == 9
    assert mismatch_analysis["mismatched"] == 1
    assert mismatch_analysis["accuracy"] == 90.0
    assert "=== MISMATCHES ===" in output
    assert "Case:\n001" in output
    assert "Category:\neconomy" in output
    assert "Expected:\nSPORTS" in output
    assert "Predicted:\nECONOMY" in output
    assert "Reason Codes:\n- " in output
    assert "Supporting Signals:\n- " in output
    assert "Warnings:\nNone" in output


def test_checked_in_outputs_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Keep persisted JSON and Markdown byte-identical to stable rendering."""
    expected_json = render_json(analysis)
    expected_markdown = render_markdown(analysis)

    assert (BATCH_ROOT / "topic_analysis.json").read_text(
        encoding="utf-8"
    ) == expected_json
    assert (BATCH_ROOT / "topic_analysis.md").read_text(
        encoding="utf-8"
    ) == expected_markdown
    assert render_json(analysis) == expected_json
    assert render_markdown(analysis) == expected_markdown
    assert render_console(analysis) == render_console(analysis)


def test_benchmark_requires_no_network_api_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run all persisted sources with external and environment access disabled."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    result = analyze_topics()
    assert result["case_count"] == 10
