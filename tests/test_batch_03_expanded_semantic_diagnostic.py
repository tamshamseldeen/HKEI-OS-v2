"""Tests for the Batch 03 expanded semantic diagnostic."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_03_expanded_semantic_diagnostic import (
    BATCH_ROOT,
    DIAGNOSTIC_CASE_IDS,
    analyze_diagnostic,
    diagnostic_status,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
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
    """Return one real expanded diagnostic over persisted inputs."""
    return analyze_diagnostic()


def _case(analysis: dict[str, object], case_id: str) -> dict[str, object]:
    """Return one serialized diagnostic case."""
    return next(case for case in analysis["cases"] if case["id"] == case_id)


def _input_digest() -> str:
    """Hash only the frozen Batch 03 inputs and expectations."""
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


def test_exact_five_cases_are_analyzed_in_order(
    analysis: dict[str, object],
) -> None:
    """Analyze only 021, 022, 023, 026, and 028 in fixed order."""
    assert DIAGNOSTIC_CASE_IDS == ("021", "022", "023", "026", "028")
    assert analysis["case_count"] == 5
    assert tuple(case["id"] for case in analysis["cases"]) == DIAGNOSTIC_CASE_IDS


def test_contextual_and_semantic_engines_receive_same_exact_sources() -> None:
    """Use both engines once per category-free persisted source."""
    contextual = Mock(wraps=DeterministicContextualEvidenceEngine())
    semantic = Mock(wraps=DeterministicCompositionalSemanticEngine())

    analyze_diagnostic(contextual_engine=contextual, semantic_engine=semantic)

    assert contextual.analyze.call_count == semantic.compose.call_count == 5
    manifest = {case["id"]: case for case in read_manifest(BATCH_ROOT)}
    for contextual_call, semantic_call, case_id in zip(
        contextual.analyze.call_args_list,
        semantic.compose.call_args_list,
        DIAGNOSTIC_CASE_IDS,
    ):
        source = contextual_call.kwargs["source"]
        persisted = parse_source(BATCH_ROOT / manifest[case_id]["source_file"])
        assert source == NormalizedSource(
            title=persisted.title,
            body=persisted.body,
            source_name=persisted.source_name,
            source_url=persisted.source_url,
            published_at=None,
            language="ar",
            country=None,
            author=None,
            images=(),
            attachments=(),
            category=None,
            tags=(),
        )
        assert semantic_call.kwargs["source"] is source


def test_runner_has_no_classifier_dependencies() -> None:
    """Keep topic, format, and intent classifiers outside the diagnostic."""
    runner = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "run_batch_03_expanded_semantic_diagnostic.py"
    ).read_text(encoding="utf-8")

    assert "TopicClassifier" not in runner
    assert "FormatClassifier" not in runner
    assert "ReaderIntentClassifier" not in runner


@pytest.mark.parametrize(
    ("case_id", "primary", "relationship", "reason"),
    (
        (
            "021",
            "PRIMARY_DOMAIN_GOVERNMENT",
            "INSTITUTION_BELONGS_TO_DOMAIN",
            "PUBLIC_INFRASTRUCTURE_DOMAIN_COMPOSITION",
        ),
        (
            "022",
            "PRIMARY_DOMAIN_ECONOMY",
            "INDICATOR_DESCRIBES_DOMAIN",
            "ECONOMIC_INDICATOR_DOMAIN_COMPOSITION",
        ),
        (
            "023",
            "PRIMARY_DOMAIN_POLITICS",
            "ACTOR_PERFORMS_ACTION",
            "INTERNATIONAL_NEGOTIATION_DOMAIN_COMPOSITION",
        ),
        (
            "026",
            "PRIMARY_DOMAIN_TECHNOLOGY",
            "RECOMMENDATION_TARGETS_AUDIENCE",
            "RECOMMENDED_ACTION_AUDIENCE_COMPOSITION",
        ),
        (
            "028",
            "PRIMARY_DOMAIN_WEATHER",
            "EVENT_HAS_OUTCOME",
            "WEATHER_EVENT_DOMAIN_COMPOSITION",
        ),
    ),
)
def test_required_primary_and_relationship_outputs(
    analysis: dict[str, object],
    case_id: str,
    primary: str,
    relationship: str,
    reason: str,
) -> None:
    """Expose the expected primary and architecture-driven relationship."""
    case = _case(analysis, case_id)

    assert primary in case["primary_domain_candidates"]
    assert any(
        item["relationship_type"] == relationship
        and item["reason_code"] == reason
        for item in case["relationships"]
    )
    assert case["required_relationship_present"] is True
    assert case["required_primary_domain_present"] is True
    assert case["unexpected_primary_domain_present"] is False


def test_negotiation_secondary_is_recorded_but_nonblocking(
    analysis: dict[str, object],
) -> None:
    """Record current secondary economy support as informative evidence."""
    case = _case(analysis, "023")

    assert "SECONDARY_DOMAIN_ECONOMY" in case["secondary_domain_candidates"]
    assert case["required_secondary_domain_present"] is True
    changed = copy.deepcopy(analysis)
    changed["required_secondary_domains_passed"] = 0
    assert diagnostic_status(changed) == "PASSED"


def test_recommendation_format_and_intent_support_are_required(
    analysis: dict[str, object],
) -> None:
    """Require SERVICE and KNOW_ACTION only for case 026."""
    case = _case(analysis, "026")

    assert case["format_support"] == ["FORMAT_SERVICE"]
    assert case["intent_support"] == ["INTENT_KNOW_ACTION"]
    assert case["required_format_support_present"] is True
    assert case["required_intent_support_present"] is True
    assert all(
        item["required_format_support_present"] is None
        and item["required_intent_support_present"] is None
        for item in analysis["cases"]
        if item["id"] != "026"
    )


def test_relationship_schema_and_provenance_are_valid(
    analysis: dict[str, object],
) -> None:
    """Validate exact records, index bounds, and local section compatibility."""
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


def test_json_excludes_complete_source_bodies(
    analysis: dict[str, object],
) -> None:
    """Store semantic evidence without a separate full body field."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert all("body" not in case for case in parsed["cases"])
    for case_id in DIAGNOSTIC_CASE_IDS:
        assert parse_source(BATCH_ROOT / case_id / "source.md").body not in output


def test_status_requires_all_blocking_quality_conditions(
    analysis: dict[str, object],
) -> None:
    """Pass clean metrics and fail every required blocking regression."""
    assert diagnostic_status(analysis) == "PASSED"
    for key in (
        "required_relationships_passed",
        "required_primary_domains_passed",
        "required_format_support_passed",
        "required_intent_support_passed",
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
    assert (BATCH_ROOT / "expanded_semantic_diagnostic.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "expanded_semantic_diagnostic.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_sources_and_expected_labels_remain_unchanged() -> None:
    """Protect every registered source and expected label from diagnostics."""
    assert _input_digest() == INPUT_DIGEST


def test_diagnostic_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run all five cases with external access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_diagnostic()["case_count"] == 5
