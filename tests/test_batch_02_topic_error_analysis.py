"""Tests for the analysis-only Batch 02 topic mismatch diagnostics."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_02_topic_error_analysis import (
    HUMAN_ADJUDICATION_IDS,
    analyze_topic_errors,
    matched_topic_terms,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import (
    BATCH_ROOT,
    _source_fields,
    parse_source,
    read_expectations,
    read_manifest,
)
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


MISMATCH_IDS = ("011", "013", "014", "015", "017", "018", "019", "020")
INPUT_DIGEST = "d6480ad14f4640a4c3dcf29268accbd848455fd01177416ba092aacb4189a755"


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real deterministic topic error analysis."""
    return analyze_topic_errors()


def _input_paths() -> list[Path]:
    """Return frozen expectation, manifest, and source inputs."""
    return [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[
            BATCH_ROOT / case["source_file"] for case in read_manifest()
        ],
    ]


def _input_digest() -> str:
    """Calculate the same path-sensitive frozen-input digest as registration."""
    digest = sha256()
    for path in _input_paths():
        digest.update(path.relative_to(BATCH_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_analyzes_exactly_the_eight_topic_mismatches(
    analysis: dict[str, object],
) -> None:
    """Include every raw topic mismatch and no matched validation case."""
    ids = tuple(case["id"] for case in analysis["mismatches"])

    assert analysis["topic_mismatches"] == 8
    assert ids == MISMATCH_IDS
    assert "012" not in ids
    assert "016" not in ids


def test_exact_title_body_and_tag_matches_are_reported(
    analysis: dict[str, object],
) -> None:
    """Expose production terms and exact local contexts for every topic."""
    for case in analysis["mismatches"]:
        for location in ("title_topic_signals", "body_topic_signals"):
            signals = case[location]
            assert len(signals) == 14
            for matches in signals.values():
                for match in matches:
                    assert match["matched_term"]
                    assert match["matched_term"] in match["matched_text_context"].lower()
                    assert isinstance(match["inside_larger_token"], bool)
        assert all(not matches for matches in case["tag_topic_signals"].values())
        assert case["expected_topic_title_matches"] == case[
            "title_topic_signals"
        ][case["expected_topic"]]
        assert case["expected_topic_body_matches"] == case[
            "body_topic_signals"
        ][case["expected_topic"]]


def test_records_every_current_deterministic_influence(
    analysis: dict[str, object],
) -> None:
    """Record legacy, risk, entity, structure, and final classifier evidence."""
    for case in analysis["mismatches"]:
        assert case["legacy_content_type"]
        assert case["legacy_content_confidence"]
        assert case["legacy_support_applied"] is (
            case["legacy_implied_topic"] is not None
        )
        assert isinstance(case["risk_topics"], list)
        assert isinstance(case["government_entity_evidence"], bool)
        assert isinstance(case["structured_economic_evidence"], bool)
        assert isinstance(case["final_reason_codes"], list)
        assert isinstance(case["final_supporting_signals"], list)
        assert isinstance(case["final_warnings"], list)


def test_substring_collision_uses_unicode_token_boundaries() -> None:
    """Distinguish a standalone sports term from one inside a larger token."""
    signals = matched_topic_terms("دوري تستهدف")
    sports_matches = signals["SPORTS"]
    standalone = next(
        match for match in sports_matches if match["matched_term"] == "دوري"
    )
    collision = next(
        match for match in sports_matches if match["matched_term"] == "هدف"
    )

    assert standalone["inside_larger_token"] is False
    assert collision["inside_larger_token"] is True


def test_diagnostics_do_not_change_current_classification(
    analysis: dict[str, object],
) -> None:
    """Keep classification output identical while adding diagnostic flags."""
    manifest = {case["id"]: case for case in read_manifest()}
    workflow = EditorialTopicWorkflow()
    for case in analysis["mismatches"]:
        source = parse_source(BATCH_ROOT / manifest[case["id"]]["source_file"])
        before_flags = tuple(case["diagnostic_flags"])
        fresh = workflow.process(**_source_fields(source)).topic_classification

        assert fresh.topic.value == case["predicted_topic"]
        assert fresh.confidence.value == case["predicted_confidence"]
        assert tuple(case["diagnostic_flags"]) == before_flags


def test_workflow_is_used_only_for_mismatched_topic_cases() -> None:
    """Reproduce deterministic inputs for exactly the eight mismatches."""
    workflow = Mock(wraps=EditorialTopicWorkflow())

    analyze_topic_errors(topic_workflow=workflow)

    assert workflow.process.call_count == 8
    processed_titles = tuple(
        call.kwargs["title"] for call in workflow.process.call_args_list
    )
    manifest = {case["id"]: case for case in read_manifest()}
    assert processed_titles == tuple(
        parse_source(BATCH_ROOT / manifest[case_id]["source_file"]).title
        for case_id in MISMATCH_IDS
    )


def test_expected_labels_and_source_inputs_remain_unchanged() -> None:
    """Protect the pre-registered labels and supplied source text byte-for-byte."""
    expected_before = read_expectations()

    analyze_topic_errors()

    assert read_expectations() == expected_before
    assert _input_digest() == INPUT_DIGEST


def test_human_adjudication_queue_is_exact(
    analysis: dict[str, object],
) -> None:
    """Pre-register exactly the five specified cases without deciding labels."""
    queue = analysis["human_adjudication_queue"]

    assert HUMAN_ADJUDICATION_IDS == ("011", "013", "014", "016", "020")
    assert tuple(case["id"] for case in queue) == HUMAN_ADJUDICATION_IDS
    assert all(case["title"] for case in queue)
    assert all(len(case["possible_competing_topics"]) >= 2 for case in queue)


def test_json_excludes_every_full_source_body(
    analysis: dict[str, object],
) -> None:
    """Persist exact matched contexts without copying complete source bodies."""
    output = render_json(analysis)

    for manifest_case in read_manifest():
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_markdown_has_required_sections_and_failure_class_groups(
    analysis: dict[str, object],
) -> None:
    """Render all diagnostics, adjudication cases, and grouped failure classes."""
    markdown = render_markdown(analysis)

    assert markdown.startswith("# Batch 02 Topic Error Analysis\n")
    assert "## Summary" in markdown
    assert "## Mismatch Diagnostics" in markdown
    assert "## Human Adjudication Queue" in markdown
    assert "## Candidate Failure Classes" in markdown
    for case_id in MISMATCH_IDS:
        assert f"### Case {case_id}" in markdown
    for failure_class in (
        "Legacy dependency",
        "Substring matching",
        "Vocabulary coverage",
        "Topic scoring / precedence",
        "Human-label ambiguity",
    ):
        assert f"### {failure_class}" in markdown


def test_outputs_are_deterministic_and_match_checked_in_files(
    analysis: dict[str, object],
) -> None:
    """Keep both reports and compact console output byte-stable."""
    assert (BATCH_ROOT / "topic_error_analysis.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "topic_error_analysis.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_analysis_requires_no_api_network_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run diagnostics with external and environment access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_topic_errors()["topic_mismatches"] == 8
