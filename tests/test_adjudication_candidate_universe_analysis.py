"""Tests for the semantic adjudication candidate-universe diagnostic."""

import inspect
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

import examples.run_adjudication_candidate_universe_analysis as diagnostic
from examples.run_adjudication_candidate_universe_analysis import (
    CURRENT,
    FULL,
    NO_DOMAIN,
    OUTPUT_JSON,
    OUTPUT_MD,
    THIN,
    analyze_candidate_universes,
    construct_strategies,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.adjudication.semantic_adjudication_request_builder import (
    SemanticAdjudicationRequestBuilder,
)
from src.formatting.editorial_format import EditorialFormat
from src.topic.topic import Topic


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    return json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))


def test_fifty_cases_and_only_gate_required_requests_are_analyzed(
    analysis: dict[str, object],
) -> None:
    assert analysis["cases_analyzed"] == 50
    assert analysis["requests_analyzed"] == 26
    assert sum(case["strategies"] is not None for case in analysis["cases"]) == 26
    assert all(
        case["strategies"] is None
        for case in analysis["cases"]
        if case["gate_scope"] == "NOT_REQUIRED"
    )


def test_current_strategy_reproduces_batch_05_shadow_exactly(
    analysis: dict[str, object],
) -> None:
    shadow = json.loads(
        (diagnostic.BENCHMARK_ROOT / "batch_05" / "adjudication_request_shadow.json")
        .read_text(encoding="utf-8")
    )
    shadow_by_id = {case["id"]: case for case in shadow["cases"]}
    for case in analysis["cases"]:
        if case["batch"] != "batch_05" or case["strategies"] is None:
            continue
        current = case["strategies"][CURRENT]
        assert current["candidate_topics"] == shadow_by_id[case["id"]][
            "candidate_topics"
        ]
        assert current["candidate_formats"] == shadow_by_id[case["id"]][
            "candidate_formats"
        ]


def test_full_enum_order_is_deterministic_evidence_first_and_enum_bounded() -> None:
    values = construct_strategies(
        deterministic_topic="HEALTH",
        deterministic_format="ANALYSIS",
        structured_topics=("HEALTH", "SCIENCE", "HEALTH", "GENERAL"),
        structured_formats=("ANALYSIS", "EXPLAINER", "ANALYSIS"),
        topic_required=True,
        format_required=True,
        primary_domain_candidates=(),
    )[FULL]
    assert values["candidate_topics"][:3] == ("HEALTH", "SCIENCE", "GENERAL")
    assert values["candidate_formats"][:2] == ("ANALYSIS", "EXPLAINER")
    assert set(values["candidate_topics"]) == {item.value for item in Topic}
    assert set(values["candidate_formats"]) == {
        item.value for item in EditorialFormat
    }
    assert len(values["candidate_topics"]) == len(set(values["candidate_topics"]))
    assert len(values["candidate_formats"]) == len(set(values["candidate_formats"]))


def test_scope_isolation_is_preserved_by_every_strategy() -> None:
    topic_only = construct_strategies(
        deterministic_topic="GENERAL",
        deterministic_format="STANDARD_NEWS",
        structured_topics=("GENERAL",),
        structured_formats=("STANDARD_NEWS",),
        topic_required=True,
        format_required=False,
        primary_domain_candidates=(),
    )
    format_only = construct_strategies(
        deterministic_topic="ECONOMY",
        deterministic_format="STANDARD_NEWS",
        structured_topics=("ECONOMY",),
        structured_formats=("STANDARD_NEWS",),
        topic_required=False,
        format_required=True,
        primary_domain_candidates=("PRIMARY_DOMAIN_ECONOMY",),
    )
    assert all(
        values["candidate_formats"] == ("STANDARD_NEWS",)
        for values in topic_only.values()
    )
    assert all(
        values["candidate_topics"] == ("ECONOMY",)
        for values in format_only.values()
    )


def test_hybrid_activation_uses_only_candidate_count_and_domain_evidence() -> None:
    signature = inspect.signature(construct_strategies)
    assert not any("expected" in name for name in signature.parameters)
    thin = construct_strategies(
        deterministic_topic="GENERAL",
        deterministic_format="STANDARD_NEWS",
        structured_topics=("GENERAL", "WORLD"),
        structured_formats=("STANDARD_NEWS", "ANALYSIS"),
        topic_required=True,
        format_required=True,
        primary_domain_candidates=("PRIMARY_DOMAIN_WORLD",),
    )
    assert len(thin[THIN]["candidate_topics"]) == len(Topic)
    assert len(thin[THIN]["candidate_formats"]) == len(EditorialFormat)
    assert thin[NO_DOMAIN]["candidate_topics"] == ("GENERAL", "WORLD")


def test_expected_labels_are_loaded_after_candidate_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    real_builder = SemanticAdjudicationRequestBuilder()
    builder = Mock(wraps=real_builder)

    def tracked_build(**kwargs: object) -> object:
        events.append("build")
        assert not any("expected" in key for key in kwargs)
        return real_builder.build(**kwargs)

    builder.build.side_effect = tracked_build
    original_topics = diagnostic._expected_topics

    def tracked_topics(path: Path) -> dict[str, str]:
        events.append("truth")
        return original_topics(path)

    monkeypatch.setattr(diagnostic, "_expected_topics", tracked_topics)
    analyze_candidate_universes(builder=builder)
    assert events.count("build") == 26
    assert events.index("truth") > max(
        index for index, event in enumerate(events) if event == "build"
    )


def test_coverage_counts_sizes_quality_and_recommendation_are_exact(
    analysis: dict[str, object],
) -> None:
    expected = {
        CURRENT: (52.0, 42.857142857142854, 2.0, 1.5714285714285714, 4, 2, "POOR"),
        FULL: (100.0, 100.0, 15.0, 12.0, 15, 12, "EXCELLENT"),
        THIN: (96.0, 100.0, 11.68, 12.0, 15, 12, "ACCEPTABLE"),
        NO_DOMAIN: (100.0, 42.857142857142854, 14.56, 1.5714285714285714, 15, 2, "POOR"),
    }
    for name, values in expected.items():
        metrics = analysis["strategies"][name]
        assert (
            metrics["topic_candidate_coverage"],
            metrics["format_candidate_coverage"],
            metrics["average_topic_candidate_count"],
            metrics["average_format_candidate_count"],
            metrics["max_topic_candidate_count"],
            metrics["max_format_candidate_count"],
            metrics["quality"],
        ) == values
        assert metrics["average_candidate_payload_chars"] > 0
        assert metrics["max_candidate_payload_chars"] >= (
            metrics["average_candidate_payload_chars"]
        )
        assert metrics["scope_violations"] == []
    assert analysis["recommendation"] == "USE_FULL_ENUM_FOR_REQUIRED_SCOPE"


def test_batch_05_coverage_matches_registered_baseline_and_counterfactuals(
    analysis: dict[str, object],
) -> None:
    expected = {
        CURRENT: (0.0, 25.0),
        FULL: (100.0, 100.0),
        THIN: (88.88888888888889, 100.0),
        NO_DOMAIN: (100.0, 25.0),
    }
    for name, coverage in expected.items():
        batch = analysis["strategies"][name]["coverage_by_batch"]["batch_05"]
        assert (
            batch["topic_candidate_coverage"],
            batch["format_candidate_coverage"],
        ) == coverage


def test_persisted_outputs_are_deterministic_and_body_free(
    analysis: dict[str, object],
) -> None:
    assert OUTPUT_JSON.read_text(encoding="utf-8") == render_json(analysis)
    assert OUTPUT_MD.read_text(encoding="utf-8") == render_markdown(analysis)
    rendered = render_json(analysis)
    for batch in diagnostic.BATCHES:
        root = diagnostic.BENCHMARK_ROOT / batch
        for manifest_case in read_manifest(root):
            path = root / manifest_case["source_file"]
            source = (
                diagnostic.parse_batch_01_source(path)
                if batch == "batch_01"
                else parse_source(path)
            )
            assert source.body not in rendered


def test_runner_reads_no_risk_annotations_and_has_no_external_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[str] = []
    original_read = Path.read_text

    def tracked_read(path: Path, *args: object, **kwargs: object) -> str:
        reads.append(path.name)
        return original_read(path, *args, **kwargs)

    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(Path, "read_text", tracked_read)
    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(os, "getenv", fail)
    result = analyze_candidate_universes()
    assert result["cases_analyzed"] == 50
    assert "human_risk_annotations.json" not in reads
    assert not any("risk" in name.casefold() for name in reads)
