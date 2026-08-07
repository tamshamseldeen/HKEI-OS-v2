"""Tests for the pure unseen Batch 03 context-aware validation."""

import copy
import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_03_contextual_full_validation import (
    BATCH_ROOT,
    analyze_validation,
    render_console,
    render_json,
    render_markdown,
    validation_status,
)
from examples.run_benchmark_batch_02_validation import (
    parse_source,
    read_expectations,
    read_manifest,
)
from src.workflows.experimental_contextual_editorial_analysis_workflow import (
    ExperimentalContextualEditorialAnalysisWorkflow,
)


EXPECTED_IDS = tuple(f"{case_id:03d}" for case_id in range(21, 31))
CASE_KEYS = {
    "id",
    "expected_topic",
    "predicted_topic",
    "topic_confidence",
    "topic_match",
    "expected_format",
    "predicted_format",
    "format_confidence",
    "format_match",
    "expected_reader_intent",
    "predicted_reader_intent",
    "reader_intent_confidence",
    "reader_intent_match",
    "full_match",
    "contextual_support_labels",
    "contextual_suppression_labels",
}
SUMMARY_KEYS = {
    "batch",
    "case_count",
    "topic_matched",
    "topic_accuracy",
    "format_matched",
    "format_accuracy",
    "reader_intent_matched",
    "reader_intent_accuracy",
    "fully_matched_cases",
    "full_case_accuracy",
    "contextual_evidence_used",
    "contextual_suppression_used",
    "cases",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Return one real unseen Batch 03 validation result."""
    return analyze_validation()


def test_loads_exact_cases_and_registered_expectations(
    analysis: dict[str, object],
) -> None:
    """Read cases 021–030 and all expected labels from expected.json."""
    expectations = read_expectations(BATCH_ROOT)

    assert analysis["case_count"] == len(expectations) == 10
    assert tuple(case["id"] for case in analysis["cases"]) == EXPECTED_IDS
    assert tuple(
        (
            case["expected_topic"],
            case["expected_format"],
            case["expected_reader_intent"],
        )
        for case in analysis["cases"]
    ) == tuple(
        (item["topic"], item["editorial_format"], item["reader_intent"])
        for item in expectations
    )


def test_experimental_workflow_receives_exact_category_free_input() -> None:
    """Use only the required workflow without inferred category or metadata."""
    workflow = Mock(wraps=ExperimentalContextualEditorialAnalysisWorkflow())

    analyze_validation(workflow=workflow)

    assert workflow.process.call_count == 10
    for workflow_call, manifest_case in zip(
        workflow.process.call_args_list,
        read_manifest(BATCH_ROOT),
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
            "category": None,
            "tags": (),
            "user_instruction": None,
        }


def test_case_schema_comparisons_and_full_match_are_exact(
    analysis: dict[str, object],
) -> None:
    """Record exact fields and compare all three dimensions independently."""
    assert set(analysis) == SUMMARY_KEYS
    for case in analysis["cases"]:
        assert set(case) == CASE_KEYS
        assert case["topic_match"] is (
            case["expected_topic"] == case["predicted_topic"]
        )
        assert case["format_match"] is (
            case["expected_format"] == case["predicted_format"]
        )
        assert case["reader_intent_match"] is (
            case["expected_reader_intent"] == case["predicted_reader_intent"]
        )
        assert case["full_match"] is (
            case["topic_match"]
            and case["format_match"]
            and case["reader_intent_match"]
        )
        assert isinstance(case["contextual_support_labels"], list)
        assert isinstance(case["contextual_suppression_labels"], list)


def test_summary_accuracies_and_context_counts_are_exact(
    analysis: dict[str, object],
) -> None:
    """Derive every reported metric directly from the raw case outcomes."""
    for dimension in ("topic", "format", "reader_intent"):
        matched = sum(
            case[f"{dimension}_match"] for case in analysis["cases"]
        )
        assert analysis[f"{dimension}_matched"] == matched
        assert analysis[f"{dimension}_accuracy"] == matched / 10 * 100.0
    fully_matched = sum(case["full_match"] for case in analysis["cases"])
    assert analysis["fully_matched_cases"] == fully_matched
    assert analysis["full_case_accuracy"] == fully_matched / 10 * 100.0
    assert analysis["contextual_evidence_used"] == sum(
        bool(case["contextual_support_labels"]) for case in analysis["cases"]
    )
    assert analysis["contextual_suppression_used"] == sum(
        bool(case["contextual_suppression_labels"])
        for case in analysis["cases"]
    )


@pytest.mark.parametrize(
    ("topic", "editorial_format", "intent", "full", "expected"),
    (
        (100.0, 100.0, 100.0, 100.0, "EXCELLENT"),
        (80.0, 80.0, 80.0, 20.0, "PASSED"),
        (79.99, 100.0, 100.0, 100.0, "FAILED"),
        (100.0, 79.99, 100.0, 100.0, "FAILED"),
        (100.0, 100.0, 79.99, 100.0, "FAILED"),
    ),
)
def test_status_uses_registered_thresholds(
    topic: float,
    editorial_format: float,
    intent: float,
    full: float,
    expected: str,
) -> None:
    """Return excellent, passed, or failed without requiring perfection."""
    assert validation_status(
        {
            "topic_accuracy": topic,
            "format_accuracy": editorial_format,
            "reader_intent_accuracy": intent,
            "full_case_accuracy": full,
        }
    ) == expected


def test_json_contains_no_body_or_prompt(analysis: dict[str, object]) -> None:
    """Exclude full source bodies and prompts from machine-readable output."""
    output = render_json(analysis)

    assert "prompt" not in output.lower()
    assert json.loads(output)["batch"] == "batch_03"
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_markdown_console_and_reports_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Keep both persisted reports and console output byte-stable."""
    markdown = render_markdown(analysis)
    assert len(
        [line for line in markdown.splitlines() if line.startswith("| 0")]
    ) == 10
    for heading in (
        "## Topic Mismatches",
        "## Format Mismatches",
        "## Reader Intent Mismatches",
    ):
        assert heading in markdown
    assert (BATCH_ROOT / "contextual_full_validation.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "contextual_full_validation.md").read_text(
        encoding="utf-8"
    ) == markdown
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_validation_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run unseen validation with external and environment access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_validation()["case_count"] == 10
