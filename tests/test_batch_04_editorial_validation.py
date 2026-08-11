"""Tests for the Batch 04 advanced holdout editorial validation."""

import copy
from hashlib import sha256
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_04_editorial_validation import (
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
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


FROZEN_INPUT_DIGEST = (
    "20c08c974d31c3bb762437e6a3970a2b31dd16431cf43084cd7470f791f38224"
)
RISK_ANNOTATION_DIGEST = (
    "aa3d0b9616368d449e4bb60d1f71cbf923556da089553468b42d3797969b4ad6"
)
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
    "topic_reason_codes",
    "topic_supporting_signals",
    "topic_warnings",
    "format_reason_codes",
    "format_supporting_signals",
    "format_warnings",
    "intent_reason_codes",
    "intent_supporting_signals",
    "intent_warnings",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Run the real workflow once for deterministic assertions."""
    return analyze_validation()


def _digest(paths: list[Path]) -> str:
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(BATCH_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_loads_exact_registered_cases_and_expectations(
    analysis: dict[str, object],
) -> None:
    """Load 031–040 and use the frozen editorial expectations."""
    expectations = read_expectations(BATCH_ROOT)
    assert analysis["case_count"] == len(expectations) == 10
    assert tuple(case["id"] for case in analysis["cases"]) == tuple(
        f"{case_id:03d}" for case_id in range(31, 41)
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


def test_required_workflow_receives_exact_category_free_sources() -> None:
    """Use only the semantic workflow with the prescribed empty metadata."""
    workflow = Mock(wraps=ExperimentalSemanticEditorialAnalysisWorkflow())
    analyze_validation(workflow=workflow)
    assert workflow.process.call_count == 10
    for call, manifest_case in zip(
        workflow.process.call_args_list, read_manifest(BATCH_ROOT)
    ):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert call.kwargs == {
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


def test_case_schema_evidence_and_comparisons_are_exact(
    analysis: dict[str, object],
) -> None:
    """Record all requested evidence and derive matches independently."""
    list_fields = CASE_KEYS - {
        "id", "expected_topic", "predicted_topic", "topic_confidence",
        "topic_match", "expected_format", "predicted_format", "format_confidence",
        "format_match", "expected_reader_intent", "predicted_reader_intent",
        "reader_intent_confidence", "reader_intent_match", "full_match",
    }
    for case in analysis["cases"]:
        assert set(case) == CASE_KEYS
        assert all(isinstance(case[field], list) for field in list_fields)
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


def test_summary_metrics_and_semantic_usage_are_exact(
    analysis: dict[str, object],
) -> None:
    """Calculate every summary metric from the per-case records."""
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


def test_status_thresholds_are_exact() -> None:
    """Apply EXCELLENT, PASSED, and FAILED thresholds as preregistered."""
    assert validation_status(
        {"topic_accuracy": 100.0, "format_accuracy": 100.0,
         "reader_intent_accuracy": 100.0, "full_case_accuracy": 100.0}
    ) == "EXCELLENT"
    assert validation_status(
        {"topic_accuracy": 80.0, "format_accuracy": 80.0,
         "reader_intent_accuracy": 80.0, "full_case_accuracy": 20.0}
    ) == "PASSED"
    assert validation_status(
        {"topic_accuracy": 70.0, "format_accuracy": 100.0,
         "reader_intent_accuracy": 100.0, "full_case_accuracy": 70.0}
    ) == "FAILED"


def test_reports_are_deterministic_and_exclude_source_and_risk_data(
    analysis: dict[str, object],
) -> None:
    """Persist byte-stable reports without bodies or risk annotation fields."""
    json_output = render_json(analysis)
    forbidden = (
        "expected_risk_band",
        "attribution_required",
        "uncertainty_present",
        "sensitive_context",
    )
    assert not any(field in json_output for field in forbidden)
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in json_output
    assert (BATCH_ROOT / "editorial_validation.json").read_text(
        encoding="utf-8"
    ) == json_output
    assert (BATCH_ROOT / "editorial_validation.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_markdown_contains_required_mismatch_sections(
    analysis: dict[str, object],
) -> None:
    """Report raw mismatch evidence with explicit empty-value rendering."""
    markdown = render_markdown(analysis)
    assert markdown.startswith("# Batch 04 Advanced Holdout Editorial Validation\n")
    assert "## Topic Mismatches" in markdown
    assert "## Format Mismatches" in markdown
    assert "## Reader Intent Mismatches" in markdown
    assert "None" in markdown


def test_validation_never_reads_human_risk_annotations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail explicitly if the benchmark-only risk metadata is opened."""
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "human_risk_annotations.json":
            raise AssertionError("risk annotations must not be read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    assert analyze_validation()["case_count"] == 10


def test_validation_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run locally while network and environment access are forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert analyze_validation()["case_count"] == 10


def test_frozen_batch_04_inputs_and_risk_annotations_are_unchanged() -> None:
    """Protect labels, sources, manifest, and benchmark-only risk metadata."""
    frozen_paths = [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[
            BATCH_ROOT / case["source_file"]
            for case in read_manifest(BATCH_ROOT)
        ],
    ]
    assert _digest(frozen_paths) == FROZEN_INPUT_DIGEST
    assert sha256(
        (BATCH_ROOT / "human_risk_annotations.json").read_bytes()
    ).hexdigest() == RISK_ANNOTATION_DIGEST
