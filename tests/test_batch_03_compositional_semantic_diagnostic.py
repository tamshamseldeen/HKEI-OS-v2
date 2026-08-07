"""Tests for the Batch 03 compositional semantic diagnostic."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_03_compositional_semantic_diagnostic import (
    BATCH_ROOT,
    DIAGNOSTIC_CASE_IDS,
    analyze_diagnostic,
    diagnostic_status,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.normalized_source import NormalizedSource
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)


INPUT_DIGEST = "6fc29192f5bbb7cfd56f3645f01b71780d03ecdca601521d044c1b9766dbfe99"
RELATIONSHIP_KEYS = {
    "source_section",
    "sentence_index",
    "relationship_type",
    "subject_component",
    "subject_text",
    "object_component",
    "object_text",
    "strength",
    "reason_code",
    "evidence_indexes",
    "supports",
    "suppresses",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Return the real deterministic diagnostic for persisted sources."""
    return analyze_diagnostic()


def _case(analysis: dict[str, object], case_id: str) -> dict[str, object]:
    """Return one serialized diagnostic case by ID."""
    return next(case for case in analysis["cases"] if case["id"] == case_id)


def _input_digest() -> str:
    """Hash only the frozen Batch 03 manifest, expectations, and sources."""
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


def test_exact_three_cases_are_analyzed_in_order(
    analysis: dict[str, object],
) -> None:
    """Analyze exactly cases 024, 025, and 029 in fixed order."""
    assert DIAGNOSTIC_CASE_IDS == ("024", "025", "029")
    assert analysis["case_count"] == 3
    assert tuple(case["id"] for case in analysis["cases"]) == DIAGNOSTIC_CASE_IDS


def test_both_engines_receive_exact_persisted_sources() -> None:
    """Use both engines once per source without supplying a category."""
    contextual = Mock(wraps=DeterministicContextualEvidenceEngine())
    semantic = Mock(wraps=DeterministicCompositionalSemanticEngine())

    analyze_diagnostic(contextual_engine=contextual, semantic_engine=semantic)

    assert contextual.analyze.call_count == 3
    assert semantic.compose.call_count == 3
    for contextual_call, semantic_call, case_id in zip(
        contextual.analyze.call_args_list,
        semantic.compose.call_args_list,
        DIAGNOSTIC_CASE_IDS,
    ):
        source = contextual_call.kwargs["source"]
        persisted = parse_source(BATCH_ROOT / case_id / "source.md")
        assert source.title == persisted.title
        assert source.body == persisted.body
        assert source.source_name == persisted.source_name
        assert source.source_url == persisted.source_url
        assert source.category is None
        assert semantic_call.kwargs["source"] is source
        assert isinstance(
            semantic_call.kwargs["contextual_evidence"],
            ContextualEvidence,
        )


def test_diagnostic_has_no_classifier_dependencies() -> None:
    """Exclude topic, format, and reader-intent classifiers from the runner."""
    runner = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "run_batch_03_compositional_semantic_diagnostic.py"
    ).read_text(encoding="utf-8")

    assert "TopicClassifier" not in runner
    assert "FormatClassifier" not in runner
    assert "ReaderIntentClassifier" not in runner


@pytest.mark.parametrize(
    ("case_id", "relationship", "primary", "secondary", "suppression"),
    (
        (
            "024",
            "METHOD_APPLIED_TO_SUBJECT",
            "PRIMARY_DOMAIN_HEALTH",
            "SECONDARY_DOMAIN_TECHNOLOGY",
            "PRIMARY_DOMAIN_TECHNOLOGY",
        ),
        (
            "025",
            "AUTHORITY_ACTS_ON_SUBJECT",
            "PRIMARY_DOMAIN_HEALTH",
            None,
            "PRIMARY_DOMAIN_GOVERNMENT",
        ),
        (
            "029",
            "AUTHORITY_ACTS_ON_SUBJECT",
            "PRIMARY_DOMAIN_EDUCATION",
            None,
            "PRIMARY_DOMAIN_GOVERNMENT",
        ),
    ),
)
def test_required_semantic_outputs(
    analysis: dict[str, object],
    case_id: str,
    relationship: str,
    primary: str,
    secondary: str | None,
    suppression: str,
) -> None:
    """Expose each required relationship, candidate, and suppression."""
    case = _case(analysis, case_id)
    relationships = case["relationships"]

    assert relationship in {item["relationship_type"] for item in relationships}
    assert primary in case["primary_domain_candidates"]
    if secondary is not None:
        assert secondary in case["secondary_domain_candidates"]
    assert suppression in {
        value for item in relationships for value in item["suppresses"]
    }
    assert case["required_relationship_present"] is True
    assert case["required_primary_domain_present"] is True
    assert case["required_secondary_domain_present"] is (
        True if secondary is not None else None
    )
    assert case["required_suppression_present"] is True
    assert case["unexpected_primary_domain_present"] is False


def test_relationship_schema_and_provenance_are_exact(
    analysis: dict[str, object],
) -> None:
    """Validate index bounds and local section/sentence correspondence."""
    manifest = {case["id"]: case for case in read_manifest(BATCH_ROOT)}
    contextual = DeterministicContextualEvidenceEngine()
    semantic = DeterministicCompositionalSemanticEngine()
    for case in analysis["cases"]:
        persisted = parse_source(BATCH_ROOT / manifest[case["id"]]["source_file"])
        source = NormalizedSource(
            title=persisted.title,
            body=persisted.body,
            source_name=persisted.source_name,
            source_url=persisted.source_url,
            language="ar",
        )
        contextual_evidence = contextual.analyze(source=source, user_instruction=None)
        relationships = semantic.compose(
            source=source,
            contextual_evidence=contextual_evidence,
        ).relationships

        assert case["contextual_item_count"] == len(contextual_evidence.all_items)
        assert case["semantic_relationship_count"] == len(relationships)
        assert all(set(item) == RELATIONSHIP_KEYS for item in case["relationships"])
        for relationship in relationships:
            for index in relationship.evidence_indexes:
                assert 0 <= index < len(contextual_evidence.all_items)
                item = contextual_evidence.all_items[index]
                assert item.source_section is relationship.source_section
                assert item.sentence_index == relationship.sentence_index
        assert case["provenance_valid"] is True


def test_json_excludes_full_article_bodies(
    analysis: dict[str, object],
) -> None:
    """Do not store a body field or complete source body in JSON."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert all("body" not in case for case in parsed["cases"])
    for case_id in DIAGNOSTIC_CASE_IDS:
        assert parse_source(BATCH_ROOT / case_id / "source.md").body not in output


def test_status_requires_every_quality_condition(
    analysis: dict[str, object],
) -> None:
    """Pass complete results and fail each regressed status metric."""
    assert diagnostic_status(analysis) == "PASSED"
    for key in (
        "required_relationships_passed",
        "required_primary_domains_passed",
        "required_secondary_domains_passed",
        "required_suppressions_passed",
        "provenance_valid_cases",
    ):
        changed = copy.deepcopy(analysis)
        changed[key] -= 1
        assert diagnostic_status(changed) == "FAILED"
    changed = copy.deepcopy(analysis)
    changed["unexpected_primary_domains"] = 1
    assert diagnostic_status(changed) == "FAILED"


def test_outputs_are_deterministic_and_match_reports(
    analysis: dict[str, object],
) -> None:
    """Keep JSON, Markdown, and console output byte-stable."""
    assert (BATCH_ROOT / "compositional_semantic_diagnostic.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "compositional_semantic_diagnostic.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_frozen_sources_and_expectations_are_unchanged() -> None:
    """Protect every registered Batch 03 source and expected label."""
    assert _input_digest() == INPUT_DIGEST


def test_diagnostic_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run locally with environment and network access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_diagnostic()["case_count"] == 3
