"""Tests for the Batch 03 semantic-aware topic diagnostic."""

import copy
from hashlib import sha256
import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_03_semantic_topic_diagnostic import (
    BATCH_ROOT,
    DIAGNOSTIC_EXPECTATIONS,
    analyze_diagnostic,
    diagnostic_status,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.workflows.editorial_semantic_topic_workflow import (
    EditorialSemanticTopicWorkflow,
)


INPUT_DIGEST = "6fc29192f5bbb7cfd56f3645f01b71780d03ecdca601521d044c1b9766dbfe99"
CASE_KEYS = {
    "id",
    "expected_topic",
    "predicted_topic",
    "confidence",
    "match",
    "contextual_support_labels",
    "semantic_primary_domain_candidates",
    "semantic_secondary_domain_candidates",
    "semantic_suppressions",
    "reason_codes",
    "supporting_signals",
    "warnings",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Return the real diagnostic over persisted Batch 03 sources."""
    return analyze_diagnostic()


def _input_digest() -> str:
    """Hash the frozen manifest, expectations, and registered sources."""
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


def test_exact_three_registered_cases_and_expectations(
    analysis: dict[str, object],
) -> None:
    """Load only 024, 025, and 029 with their fixed expected topics."""
    assert DIAGNOSTIC_EXPECTATIONS == (
        ("024", "HEALTH"),
        ("025", "HEALTH"),
        ("029", "EDUCATION"),
    )
    assert tuple(
        (case["id"], case["expected_topic"])
        for case in analysis["cases"]
    ) == DIAGNOSTIC_EXPECTATIONS


def test_workflow_receives_exact_category_free_fields() -> None:
    """Pass persisted source data and required empty metadata unchanged."""
    workflow = Mock(wraps=EditorialSemanticTopicWorkflow())

    analyze_diagnostic(workflow=workflow)

    assert workflow.process.call_count == 3
    manifest = {case["id"]: case for case in read_manifest(BATCH_ROOT)}
    for workflow_call, (case_id, _) in zip(
        workflow.process.call_args_list,
        DIAGNOSTIC_EXPECTATIONS,
    ):
        source = parse_source(BATCH_ROOT / manifest[case_id]["source_file"])
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


def test_case_schema_semantics_and_matches_are_exact(
    analysis: dict[str, object],
) -> None:
    """Record each required evidence collection and calculate exact matches."""
    for case in analysis["cases"]:
        assert set(case) == CASE_KEYS
        assert case["semantic_primary_domain_candidates"]
        assert isinstance(case["semantic_secondary_domain_candidates"], list)
        assert isinstance(case["semantic_suppressions"], list)
        assert case["match"] is (
            case["expected_topic"] == case["predicted_topic"]
        )
    matched = sum(case["match"] for case in analysis["cases"])
    assert analysis["matched"] == matched
    assert analysis["mismatched"] == 3 - matched
    assert analysis["accuracy"] == matched / 3 * 100.0


def test_required_cases_match_semantic_topics(
    analysis: dict[str, object],
) -> None:
    """Resolve both health cases and the education case correctly."""
    assert tuple(case["predicted_topic"] for case in analysis["cases"]) == (
        "HEALTH",
        "HEALTH",
        "EDUCATION",
    )
    assert diagnostic_status(analysis) == "PASSED"


def test_status_fails_when_any_case_mismatches(
    analysis: dict[str, object],
) -> None:
    """Require all three diagnostic matches for PASSED status."""
    changed = copy.deepcopy(analysis)
    changed["matched"] = 2
    changed["mismatched"] = 1

    assert diagnostic_status(changed) == "FAILED"


def test_json_excludes_full_source_bodies(
    analysis: dict[str, object],
) -> None:
    """Serialize required fields without source body material."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert set(parsed) == {"cases", "matched", "mismatched", "accuracy"}
    assert all("body" not in case for case in parsed["cases"])
    for case_id, _ in DIAGNOSTIC_EXPECTATIONS:
        assert parse_source(BATCH_ROOT / case_id / "source.md").body not in output


def test_markdown_console_and_reports_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Keep checked-in JSON, Markdown, and console output byte-stable."""
    markdown = render_markdown(analysis)
    assert len(
        [line for line in markdown.splitlines() if line.startswith("| 0")]
    ) == 3
    assert (BATCH_ROOT / "semantic_topic_diagnostic.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "semantic_topic_diagnostic.md").read_text(
        encoding="utf-8"
    ) == markdown
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_frozen_batch_inputs_are_unchanged() -> None:
    """Protect registered sources and expected labels from diagnostics."""
    assert _input_digest() == INPUT_DIGEST


def test_diagnostic_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run all cases with network and environment access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_diagnostic()["matched"] == 3
