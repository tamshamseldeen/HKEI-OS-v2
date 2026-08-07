"""Tests for the deterministic Batch 02 unseen validation benchmark."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_benchmark_batch_02_validation import (
    BATCH_ROOT,
    VALIDATION_THRESHOLD,
    analyze_validation,
    parse_source,
    read_expectations,
    read_manifest,
    render_console,
    render_json,
    render_markdown,
    validation_status,
)
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


CASE_KEYS = {
    "id",
    "source_name",
    "expected_topic",
    "predicted_topic",
    "topic_confidence",
    "topic_match",
    "topic_reason_codes",
    "topic_warnings",
    "expected_format",
    "predicted_format",
    "format_confidence",
    "format_match",
    "format_reason_codes",
    "format_warnings",
    "expected_reader_intent",
    "predicted_reader_intent",
    "reader_intent_confidence",
    "reader_intent_match",
    "reader_intent_reason_codes",
    "reader_intent_warnings",
    "case_match",
}
INPUT_DIGEST = "d6480ad14f4640a4c3dcf29268accbd848455fd01177416ba092aacb4189a755"
BATCH_01_DIGEST = "a6aec12744fbf240633b6056a86b4ca5cea611d5c1de44237a8063431ea72208"


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real unseen validation result."""
    return analyze_validation()


def _digest(paths: list[Path], root: Path) -> str:
    """Calculate a deterministic path-sensitive digest."""
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _input_paths() -> list[Path]:
    """Return frozen Batch 02 input paths in registration order."""
    return [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[
            BATCH_ROOT / manifest_case["source_file"]
            for manifest_case in read_manifest()
        ],
    ]


def test_loads_exact_cases_and_registered_expectations(
    analysis: dict[str, object],
) -> None:
    """Read all ten manifest cases and the exact pre-registered labels."""
    expectations = read_expectations()

    assert analysis["case_count"] == 10
    assert len(analysis["cases"]) == len(expectations) == 10
    assert tuple(case["id"] for case in analysis["cases"]) == tuple(
        case["id"] for case in expectations
    )
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


def test_workflows_and_v2_classifier_receive_exact_inputs() -> None:
    """Use required analyzers with category absent and no inferred metadata."""
    topic = Mock(wraps=EditorialTopicWorkflow())
    format_workflow = Mock(wraps=EditorialFormatWorkflow())
    intent = Mock(wraps=DeterministicReaderIntentClassifierV2())

    analyze_validation(
        topic_workflow=topic,
        format_workflow=format_workflow,
        reader_intent_classifier=intent,
    )

    assert topic.process.call_count == 10
    assert format_workflow.process.call_count == 10
    assert intent.classify.call_count == 10
    for topic_call, format_call, intent_call, manifest_case in zip(
        topic.process.call_args_list,
        format_workflow.process.call_args_list,
        intent.classify.call_args_list,
        read_manifest(),
    ):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        for workflow_call in (topic_call, format_call):
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
        assert intent_call.kwargs["user_instruction"] is None
        assert "topic_classification" in intent_call.kwargs
        assert "format_classification" in intent_call.kwargs


def test_case_fields_and_matches_are_calculated_exactly(
    analysis: dict[str, object],
) -> None:
    """Record every required output and derive all four match flags."""
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
        assert case["case_match"] is (
            case["topic_match"]
            and case["format_match"]
            and case["reader_intent_match"]
        )


def test_summary_counts_and_accuracies_are_calculated_exactly(
    analysis: dict[str, object],
) -> None:
    """Calculate dimensional and full-case metrics from raw case booleans."""
    cases = analysis["cases"]
    mappings = (
        ("topic_match", "topic_matched", "topic_accuracy", "topic_mismatches"),
        ("format_match", "format_matched", "format_accuracy", "format_mismatches"),
        (
            "reader_intent_match",
            "reader_intent_matched",
            "reader_intent_accuracy",
            "reader_intent_mismatches",
        ),
    )
    for match_key, matched_key, accuracy_key, mismatch_key in mappings:
        matched = sum(case[match_key] for case in cases)
        assert analysis[matched_key] == matched
        assert analysis[accuracy_key] == matched / 10 * 100.0
        assert analysis[mismatch_key] == 10 - matched
    fully_matched = sum(case["case_match"] for case in cases)
    assert analysis["fully_matched_cases"] == fully_matched
    assert analysis["full_case_accuracy"] == fully_matched / 10 * 100.0


@pytest.mark.parametrize(
    ("topic", "format_accuracy", "intent", "expected"),
    (
        (80.0, 80.0, 80.0, "PASSED"),
        (79.999, 80.0, 80.0, "FAILED"),
        (80.0, 79.999, 80.0, "FAILED"),
        (80.0, 80.0, 79.999, "FAILED"),
    ),
)
def test_validation_status_uses_inclusive_eighty_percent_threshold(
    topic: float,
    format_accuracy: float,
    intent: float,
    expected: str,
) -> None:
    """Pass only when each independent classification metric reaches 80%."""
    assert VALIDATION_THRESHOLD == 80.0
    assert validation_status(
        {
            "topic_accuracy": topic,
            "format_accuracy": format_accuracy,
            "reader_intent_accuracy": intent,
        }
    ) == expected


def test_json_is_safe_and_contains_no_source_or_prompt(
    analysis: dict[str, object],
) -> None:
    """Exclude source bodies and prompts from the machine-readable report."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert parsed["batch"] == "batch_02"
    assert "prompt" not in output.lower()
    for manifest_case in read_manifest():
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_markdown_has_ten_rows_summary_and_exact_mismatch_sections(
    analysis: dict[str, object],
) -> None:
    """Render all cases plus complete details for every raw mismatch."""
    markdown = render_markdown(analysis)
    rows = [line for line in markdown.splitlines() if line.startswith("| 0")]

    assert len(rows) == 10
    assert "## Topic Mismatches" in markdown
    assert "## Editorial Format Mismatches" in markdown
    assert "## Reader Intent Mismatches" in markdown
    for prefix, title in (
        ("topic", "Topic Mismatches"),
        ("format", "Editorial Format Mismatches"),
        ("reader_intent", "Reader Intent Mismatches"),
    ):
        section = markdown.split(f"## {title}\n\n", 1)[1]
        for later_title in (
            "Editorial Format Mismatches",
            "Reader Intent Mismatches",
        ):
            section = section.split(f"## {later_title}", 1)[0]
        mismatches = [case for case in analysis["cases"] if not case[f"{prefix}_match"]]
        for case in mismatches:
            assert f"ID:\n{case['id']}" in section
        if not mismatches:
            assert section.strip() == "None"


def test_outputs_are_deterministic_and_match_checked_in_reports(
    analysis: dict[str, object],
) -> None:
    """Keep JSON, Markdown, and console rendering byte-stable."""
    assert (BATCH_ROOT / "validation.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "validation.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_frozen_inputs_and_batch_01_remain_unchanged() -> None:
    """Protect registered Batch 02 inputs and all prior Batch 01 artifacts."""
    assert _digest(_input_paths(), BATCH_ROOT) == INPUT_DIGEST
    batch_01_root = BATCH_ROOT.parent / "batch_01"
    batch_01_paths = sorted(
        path for path in batch_01_root.rglob("*") if path.is_file()
    )
    assert _digest(batch_01_paths, batch_01_root) == BATCH_01_DIGEST


def test_validation_requires_no_api_network_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run validation with network sockets and environment reads forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    result = analyze_validation()
    assert result["case_count"] == 10
