"""Tests for Batch 03 compositional context failure analysis."""

import copy
import json
import os
import socket

import pytest

from examples.run_batch_03_compositional_context_analysis import (
    BATCH_ROOT,
    FAILED_CASE_IDS,
    FAILURE_TAXONOMY,
    analyze_failures,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Return one real diagnostic analysis of persisted failures."""
    return analyze_failures()


def test_analyzes_exactly_eight_failed_cases(
    analysis: dict[str, object],
) -> None:
    """Include only the registered failed cases and no matched cases."""
    validation = json.loads(
        (BATCH_ROOT / "contextual_full_validation.json").read_text(encoding="utf-8")
    )
    failed_ids = tuple(case["id"] for case in validation["cases"] if not case["full_match"])

    assert analysis["cases_analyzed"] == 8
    assert tuple(case["id"] for case in analysis["cases"]) == FAILED_CASE_IDS
    assert FAILED_CASE_IDS == failed_ids


def test_failure_taxonomy_and_counts_are_stable(
    analysis: dict[str, object],
) -> None:
    """Count every stable taxonomy class from raw per-case assignments."""
    assert tuple(analysis["failure_class_counts"]) == FAILURE_TAXONOMY
    for failure_class in FAILURE_TAXONOMY:
        assert analysis["failure_class_counts"][failure_class] == sum(
            failure_class in case["failure_classes"] for case in analysis["cases"]
        )


@pytest.mark.parametrize(
    ("case_id", "failure_class"),
    (
        ("024", "METHOD_SUBJECT_CONFUSION"),
        ("025", "AUTHORITY_SUBJECT_CONFUSION"),
        ("029", "AUTHORITY_SUBJECT_CONFUSION"),
        ("026", "ACTION_STRUCTURE_MISSING"),
        ("028", "EVENT_DOMAIN_MAPPING_MISSING"),
    ),
)
def test_required_case_failure_classes(
    analysis: dict[str, object],
    case_id: str,
    failure_class: str,
) -> None:
    """Assign every required critical compositional failure class."""
    case = next(case for case in analysis["cases"] if case["id"] == case_id)

    assert failure_class in case["failure_classes"]


def test_general_fixes_are_architectural_without_case_exceptions(
    analysis: dict[str, object],
) -> None:
    """Recommend relationship architecture instead of benchmark vocabulary."""
    fixes = [
        fix for case in analysis["cases"] for fix in case["general_fix_candidates"]
    ]
    combined = " ".join(fixes).lower()

    assert fixes
    assert not any(case_id in combined for case_id in FAILED_CASE_IDS)
    assert "add monorail keyword" not in combined
    assert "add imf keyword" not in combined
    assert "add flood keyword" not in combined
    assert all(
        any(
            concept in fix.lower()
            for concept in (
                "domain",
                "subject",
                "composition",
                "relationship",
                "format evidence",
                "contextual competition",
            )
        )
        for fix in fixes
    )


def test_json_excludes_full_source_bodies(analysis: dict[str, object]) -> None:
    """Keep machine-readable diagnostics free of complete source bodies."""
    output = render_json(analysis)

    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_outputs_are_deterministic_and_match_reports(
    analysis: dict[str, object],
) -> None:
    """Keep JSON, Markdown, and console diagnostics byte-stable."""
    markdown = render_markdown(analysis)
    assert "## Cross-Case Architectural Findings" in markdown
    assert "## Proposed Next Architecture" in markdown
    assert (
        "Compositional Semantic Evidence should consume relationships between"
        in markdown
    )
    assert (BATCH_ROOT / "compositional_context_analysis.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "compositional_context_analysis.md").read_text(
        encoding="utf-8"
    ) == markdown
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_analysis_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run analysis with external and environment access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_failures()["cases_analyzed"] == 8
