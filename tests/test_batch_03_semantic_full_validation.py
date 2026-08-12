"""Tests for Batch 03 semantic-aware full editorial validation."""

import copy
from hashlib import sha256
import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_03_semantic_full_validation import (
    BATCH_ROOT,
    PREVIOUS_ACCURACIES,
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
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


INPUT_DIGEST = "6fc29192f5bbb7cfd56f3645f01b71780d03ecdca601521d044c1b9766dbfe99"
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
    "semantic_primary_domain_candidates",
    "semantic_secondary_domain_candidates",
    "semantic_format_support",
    "semantic_format_suppression",
    "semantic_intent_support",
    "semantic_suppressions",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Return one real semantic-aware Batch 03 validation."""
    return analyze_validation()


def _input_digest() -> str:
    """Hash the frozen manifest, expectations, and sources."""
    paths = [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[
            BATCH_ROOT / case["source_file"]
            for case in read_manifest(BATCH_ROOT)
        ],
    ]
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(BATCH_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_loads_exact_ten_cases_and_registered_expectations(
    analysis: dict[str, object],
) -> None:
    """Load 021–030 and compare only against frozen expected labels."""
    expectations = read_expectations(BATCH_ROOT)

    assert analysis["case_count"] == len(expectations) == 10
    assert tuple(case["id"] for case in analysis["cases"]) == tuple(
        f"{value:03d}" for value in range(21, 31)
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


def test_workflow_receives_exact_category_free_sources() -> None:
    """Forward exact persisted source fields without category inference."""
    workflow = Mock(wraps=ExperimentalSemanticEditorialAnalysisWorkflow())

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
    """Record every required semantic field and calculate all matches."""
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
        for key in (
            "semantic_primary_domain_candidates",
            "semantic_secondary_domain_candidates",
            "semantic_format_support",
            "semantic_format_suppression",
            "semantic_intent_support",
            "semantic_suppressions",
        ):
            assert isinstance(case[key], list)


def test_metrics_and_semantic_usage_counts_are_exact(
    analysis: dict[str, object],
) -> None:
    """Derive every accuracy and semantic usage metric from case records."""
    for dimension in ("topic", "format", "reader_intent"):
        matched = sum(case[f"{dimension}_match"] for case in analysis["cases"])
        assert analysis[f"{dimension}_matched"] == matched
        assert analysis[f"{dimension}_accuracy"] == matched / 10 * 100.0
    full = sum(case["full_match"] for case in analysis["cases"])
    assert analysis["fully_matched_cases"] == full
    assert analysis["full_case_accuracy"] == full / 10 * 100.0
    assert analysis["semantic_evidence_used"] == sum(
        bool(
            case["semantic_primary_domain_candidates"]
            or case["semantic_secondary_domain_candidates"]
            or case["semantic_format_support"]
            or case["semantic_intent_support"]
        )
        for case in analysis["cases"]
    )
    assert analysis["semantic_suppression_used"] == sum(
        bool(case["semantic_format_suppression"] or case["semantic_suppressions"])
        for case in analysis["cases"]
    )


def test_status_thresholds_and_previous_baseline_are_fixed() -> None:
    """Apply exact status thresholds and retain the registered baseline."""
    assert PREVIOUS_ACCURACIES == {
        "topic": 20.0,
        "format": 80.0,
        "reader_intent": 80.0,
        "full": 20.0,
    }
    assert validation_status(
        {
            "topic_accuracy": 100.0,
            "format_accuracy": 100.0,
            "reader_intent_accuracy": 100.0,
            "full_case_accuracy": 100.0,
        }
    ) == "EXCELLENT"
    assert validation_status(
        {
            "topic_accuracy": 80.0,
            "format_accuracy": 80.0,
            "reader_intent_accuracy": 80.0,
            "full_case_accuracy": 20.0,
        }
    ) == "PASSED"


def test_real_validation_is_excellent_without_remaining_mismatches(
    analysis: dict[str, object],
) -> None:
    """Report the full improvement produced by negative format evidence."""
    assert validation_status(analysis) == "EXCELLENT"
    assert analysis["topic_accuracy"] == 100.0
    assert analysis["format_accuracy"] == 100.0
    assert analysis["reader_intent_accuracy"] == 100.0
    assert analysis["full_case_accuracy"] == 100.0
    mismatches = [case for case in analysis["cases"] if not case["full_match"]]
    assert mismatches == []


def test_json_has_no_source_body_and_outputs_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Exclude bodies and keep JSON, Markdown, and console byte-stable."""
    output = render_json(analysis)
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output
    assert output == render_json(analyze_validation())
    assert render_markdown(analysis) == render_markdown(analyze_validation())
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_expected_labels_and_sources_remain_unchanged() -> None:
    """Protect all frozen Batch 03 inputs from validation."""
    assert _input_digest() == INPUT_DIGEST


def test_validation_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run locally with environment and network access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_validation()["case_count"] == 10
