"""Tests for the deterministic Batch 01 reader-intent migration benchmark."""

import copy
import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_01_reader_intent_v2 import (
    EXPECTED_READER_INTENTS,
    analyze_reader_intents,
    benchmark_status,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_01_analysis import (
    BATCH_ROOT,
    parse_source,
    read_manifest,
)
from src.intent.deterministic_reader_intent_classifier import (
    DeterministicReaderIntentClassifier,
)
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


CASE_KEYS = {
    "id",
    "benchmark_category",
    "legacy_content_type",
    "topic",
    "editorial_format",
    "risk_level",
    "expected_reader_intent",
    "legacy_reader_intent",
    "legacy_confidence",
    "v2_reader_intent",
    "v2_confidence",
    "legacy_match",
    "v2_match",
    "intent_changed",
    "v2_reason_codes",
    "v2_supporting_signals",
    "v2_warnings",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real deterministic V1-versus-V2 analysis."""
    return analyze_reader_intents()


def test_exact_cases_and_expected_reader_intents(
    analysis: dict[str, object],
) -> None:
    """Load exactly ten cases with the exact benchmark-only expectations."""
    cases = analysis["cases"]

    assert analysis["case_count"] == 10
    assert len(cases) == 10
    assert EXPECTED_READER_INTENTS == (
        ("001", "GET_UPDATE"),
        ("002", "GET_UPDATE"),
        ("003", "GET_UPDATE"),
        ("004", "GET_UPDATE"),
        ("005", "GET_UPDATE"),
        ("006", "GET_UPDATE"),
        ("007", "VERIFY_REQUIREMENTS"),
        ("008", "GET_UPDATE"),
        ("009", "FIND_RESULT"),
        ("010", "GET_UPDATE"),
    )
    assert tuple(case["id"] for case in cases) == tuple(
        case["id"] for case in read_manifest()
    )
    assert tuple(case["expected_reader_intent"] for case in cases) == tuple(
        expected for _, expected in EXPECTED_READER_INTENTS
    )


def test_required_workflows_and_classifiers_are_used() -> None:
    """Call each required workflow and classifier exactly once per case."""
    classification = Mock(wraps=EditorialClassificationWorkflow())
    topic = Mock(wraps=EditorialTopicWorkflow())
    format_workflow = Mock(wraps=EditorialFormatWorkflow())
    legacy = Mock(wraps=DeterministicReaderIntentClassifier())
    v2 = Mock(wraps=DeterministicReaderIntentClassifierV2())

    analyze_reader_intents(
        classification_workflow=classification,
        topic_workflow=topic,
        format_workflow=format_workflow,
        legacy_classifier=legacy,
        v2_classifier=v2,
    )

    assert classification.process.call_count == 10
    assert topic.process.call_count == 10
    assert format_workflow.process.call_count == 10
    assert legacy.classify.call_count == 10
    assert v2.classify.call_count == 10
    for legacy_call, v2_call in zip(
        legacy.classify.call_args_list,
        v2.classify.call_args_list,
    ):
        assert legacy_call.kwargs["source"] is v2_call.kwargs["source"]
        assert legacy_call.kwargs["assessment"] is v2_call.kwargs["assessment"]
        assert legacy_call.kwargs["facts"] is v2_call.kwargs["facts"]
        assert legacy_call.kwargs["user_instruction"] is None
        assert v2_call.kwargs["user_instruction"] is None
        assert "content_classification" in legacy_call.kwargs
        assert "topic_classification" in v2_call.kwargs
        assert "format_classification" in v2_call.kwargs


def test_case_records_and_boolean_calculations(
    analysis: dict[str, object],
) -> None:
    """Record all classifications and calculate comparison booleans exactly."""
    cases = analysis["cases"]

    for case in cases:
        assert set(case) == CASE_KEYS
        assert case["legacy_content_type"]
        assert case["topic"]
        assert case["editorial_format"]
        assert case["risk_level"]
        assert case["legacy_match"] is (
            case["legacy_reader_intent"] == case["expected_reader_intent"]
        )
        assert case["v2_match"] is (
            case["v2_reader_intent"] == case["expected_reader_intent"]
        )
        assert case["intent_changed"] is (
            case["legacy_reader_intent"] != case["v2_reader_intent"]
        )


def test_summary_calculations_are_exact(analysis: dict[str, object]) -> None:
    """Calculate matches, changes, improvements, regressions, and accuracy."""
    cases = analysis["cases"]
    legacy_matched = sum(case["legacy_match"] for case in cases)
    v2_matched = sum(case["v2_match"] for case in cases)

    assert analysis["legacy_matched"] == legacy_matched
    assert analysis["legacy_accuracy"] == legacy_matched / 10 * 100.0
    assert analysis["v2_matched"] == v2_matched
    assert analysis["v2_accuracy"] == v2_matched / 10 * 100.0
    assert analysis["intent_changed"] == sum(
        case["legacy_reader_intent"] != case["v2_reader_intent"]
        for case in cases
    )
    assert analysis["improvements"] == sum(
        not case["legacy_match"] and case["v2_match"] for case in cases
    )
    assert analysis["regressions"] == sum(
        case["legacy_match"] and not case["v2_match"] for case in cases
    )


def test_json_is_safe_and_has_numeric_accuracies(
    analysis: dict[str, object],
) -> None:
    """Exclude source bodies and prompts while preserving numeric percentages."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert isinstance(parsed["legacy_accuracy"], float)
    assert isinstance(parsed["v2_accuracy"], float)
    assert "prompt" not in output.lower()
    for manifest_case in read_manifest():
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_markdown_has_exact_rows_and_change_sections(
    analysis: dict[str, object],
) -> None:
    """Render ten case rows and exact improvement and regression sections."""
    markdown = render_markdown(analysis)
    rows = [line for line in markdown.splitlines() if line.startswith("| 0")]
    improved = [
        case
        for case in analysis["cases"]
        if not case["legacy_match"] and case["v2_match"]
    ]
    regressed = [
        case
        for case in analysis["cases"]
        if case["legacy_match"] and not case["v2_match"]
    ]

    assert len(rows) == 10
    assert markdown.count("## Improvements") == 1
    assert markdown.count("## Regressions") == 1
    for case in improved:
        assert (
            f"{case['id']}: {case['legacy_reader_intent']} → "
            f"{case['v2_reader_intent']}"
        ) in markdown
    regression_section = markdown.split("## Regressions\n\n", 1)[1]
    if regressed:
        for case in regressed:
            assert f"{case['id']}:" in regression_section
    else:
        assert regression_section == "None\n"


@pytest.mark.parametrize(
    ("legacy_accuracy", "v2_accuracy", "regressions", "expected"),
    (
        (30.0, 100.0, 0, "PASSED"),
        (100.0, 100.0, 0, "FAILED"),
        (30.0, 90.0, 0, "FAILED"),
        (30.0, 100.0, 1, "FAILED"),
    ),
)
def test_passed_requires_all_success_criteria(
    legacy_accuracy: float,
    v2_accuracy: float,
    regressions: int,
    expected: str,
) -> None:
    """Require V2 improvement, perfect V2 accuracy, and zero regressions."""
    data = {
        "legacy_accuracy": legacy_accuracy,
        "v2_accuracy": v2_accuracy,
        "regressions": regressions,
    }

    assert benchmark_status(data) == expected


def test_checked_in_outputs_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Keep persisted JSON and Markdown byte-identical to stable rendering."""
    assert (BATCH_ROOT / "reader_intent_v2_analysis.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "reader_intent_v2_analysis.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_no_external_or_environment_access_and_inputs_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analyze without API, network, environment, or persisted-input mutation."""
    input_paths = [BATCH_ROOT / "manifest.json"] + [
        BATCH_ROOT / case["source_file"] for case in read_manifest()
    ]
    before = {path: path.read_bytes() for path in input_paths}

    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    result = analyze_reader_intents()

    assert result["case_count"] == 10
    assert {path: path.read_bytes() for path in input_paths} == before


def test_v2_mismatch_console_includes_full_details(
    analysis: dict[str, object],
) -> None:
    """Print full diagnostic details for a forced V2 mismatch."""
    forced = copy.deepcopy(analysis)
    forced_case = forced["cases"][0]
    forced_case["expected_reader_intent"] = "COMPARE_OPTIONS"
    forced_case["v2_match"] = False
    output = render_console(forced)

    assert "=== V2 MISMATCH DETAILS ===" in output
    assert "Case:\n001" in output
    assert "Category:\n" in output
    assert "Expected:\nCOMPARE_OPTIONS" in output
    assert "Legacy:\n" in output
    assert "V2:\n" in output
    assert "V2 Confidence:\n" in output
    assert "Reason Codes:\n" in output
    assert "Supporting Signals:\n" in output
    assert "Warnings:\n" in output
