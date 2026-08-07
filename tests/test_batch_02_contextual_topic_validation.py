"""Tests for Batch 02 experimental context-aware topic validation."""

import copy
import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_02_contextual_topic_validation import (
    BATCH_ROOT,
    VALIDATION_THRESHOLD,
    analyze_validation,
    contextual_selection_count,
    contextual_suppression_count,
    render_console,
    render_json,
    render_markdown,
    validation_status,
)
from examples.run_benchmark_batch_01_topics import analyze_topics
from examples.run_benchmark_batch_02_validation import (
    parse_source,
    read_expectations,
    read_manifest,
)
from src.workflows.editorial_contextual_topic_workflow import (
    EditorialContextualTopicWorkflow,
)


CASE_KEYS = {
    "id",
    "expected_topic",
    "predicted_topic",
    "confidence",
    "match",
    "reason_codes",
    "supporting_signals",
    "warnings",
    "contextual_support_labels",
    "contextual_suppression_labels",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Return one real context-aware Batch 02 validation result."""
    return analyze_validation()


def test_loads_exact_cases_and_expected_topics(
    analysis: dict[str, object],
) -> None:
    """Use all ten manifest cases and expected.json topic labels in order."""
    expectations = read_expectations()

    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in analysis["cases"]) == tuple(
        item["id"] for item in expectations
    )
    assert tuple(case["expected_topic"] for case in analysis["cases"]) == tuple(
        item["topic"] for item in expectations
    )


def test_context_workflow_receives_exact_category_free_inputs() -> None:
    """Call only the context-aware workflow with the required raw fields."""
    workflow = Mock(wraps=EditorialContextualTopicWorkflow())

    analyze_validation(workflow=workflow)

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
            "category": None,
            "tags": (),
            "user_instruction": None,
        }


def test_case_fields_labels_and_matches_are_exact(
    analysis: dict[str, object],
) -> None:
    """Record required fields, topic labels, suppression labels, and comparisons."""
    for case in analysis["cases"]:
        assert set(case) == CASE_KEYS
        assert case["match"] is (
            case["expected_topic"] == case["predicted_topic"]
        )
        assert all(
            label.startswith("TOPIC_")
            for label in case["contextual_support_labels"]
        )
        assert all(
            label.startswith("TOPIC_")
            for label in case["contextual_suppression_labels"]
        )


def test_summary_accuracy_and_context_counts_are_derived(
    analysis: dict[str, object],
) -> None:
    """Calculate summary and contextual-use counts from raw case records."""
    matched = sum(case["match"] for case in analysis["cases"])

    assert analysis["matched"] == matched
    assert analysis["mismatched"] == 10 - matched
    assert analysis["accuracy"] == matched / 10 * 100.0
    assert contextual_selection_count(analysis) == sum(
        "CONTEXTUAL_TOPIC_EVIDENCE" in case["reason_codes"]
        for case in analysis["cases"]
    )
    assert contextual_suppression_count(analysis) == sum(
        "CONTEXTUAL_TOPIC_SUPPRESSION" in case["reason_codes"]
        for case in analysis["cases"]
    )


@pytest.mark.parametrize(
    ("accuracy", "expected"),
    ((89.999, "FAILED"), (90.0, "PASSED"), (100.0, "PASSED")),
)
def test_status_uses_inclusive_ninety_percent_threshold(
    accuracy: float,
    expected: str,
) -> None:
    """Apply the preregistered scientific threshold without requiring perfection."""
    assert VALIDATION_THRESHOLD == 90.0
    assert validation_status({"accuracy": accuracy}) == expected


def test_json_contains_no_source_body(analysis: dict[str, object]) -> None:
    """Serialize the exact safe schema without embedding source content."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert set(parsed) == {
        "batch",
        "case_count",
        "matched",
        "mismatched",
        "accuracy",
        "cases",
    }
    for manifest_case in read_manifest():
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_markdown_console_and_reports_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Keep both reports and console output byte-stable."""
    markdown = render_markdown(analysis)
    assert len(
        [line for line in markdown.splitlines() if line.startswith("| 0")]
    ) == 10
    assert "## Summary" in markdown
    assert "## Mismatches" in markdown
    assert (BATCH_ROOT / "contextual_topic_validation.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "contextual_topic_validation.md").read_text(
        encoding="utf-8"
    ) == markdown
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_validation_uses_no_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run real validation while external and environment access is forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_validation()["case_count"] == 10


def test_batch_01_topic_benchmark_remains_unchanged() -> None:
    """Preserve the prior ten-of-ten Batch 01 topic result."""
    batch_01 = analyze_topics()

    assert batch_01["matched"] == 10
    assert batch_01["accuracy"] == 100.0
