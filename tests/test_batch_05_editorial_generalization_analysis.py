"""Tests for the frozen Batch 05 editorial generalization analysis."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket

import pytest

from examples.run_batch_05_editorial_generalization_analysis import (
    BATCH_ROOT,
    CASE_IDS,
    FAILURE_CLASSES,
    TRIGGERS,
    analyze_generalization,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest


VALIDATION_DIGESTS = {
    "editorial_validation.json": (
        "a8b210cb8ece13d77cb3f594a3048cac1d306148d9de30fcedc1abd0ae5c9fe3"
    ),
    "editorial_validation.md": (
        "120046742a0466d1666f9684e5582fd85505f72066d6d905b2745b06582fa3ad"
    ),
}
EXPECTED_TRIGGER_COUNTS = {
    "TOPIC_LOW_CONFIDENCE": (7, 0, 7, 1.0),
    "TOPIC_GENERAL_FALLBACK": (6, 0, 6, 1.0),
    "NO_PRIMARY_SEMANTIC_DOMAIN": (9, 0, 9, 1.0),
    "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP": (6, 0, 6, 1.0),
    "MULTIPLE_COMPETING_TOPIC_SIGNALS": (1, 0, 1, 1.0),
    "METHOD_SUBJECT_AMBIGUITY": (2, 0, 2, 1.0),
    "SEMANTIC_DOMAIN_CONFLICT": (0, 0, 0, None),
    "FORMAT_LOW_CONFIDENCE": (3, 1, 2, 2 / 3),
    "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK": (2, 1, 1, 0.5),
    "EXPLAINER_STRUCTURE_UNRESOLVED": (0, 0, 0, None),
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    return analyze_generalization()


def _case(analysis: dict[str, object], case_id: str) -> dict[str, object]:
    return next(case for case in analysis["cases"] if case["id"] == case_id)


def test_exactly_cases_041_through_050_are_analyzed(
    analysis: dict[str, object],
) -> None:
    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in analysis["cases"]) == CASE_IDS


def test_first_holdout_results_are_preserved_and_used(
    analysis: dict[str, object],
) -> None:
    validation = json.loads(
        (BATCH_ROOT / "editorial_validation.json").read_text(encoding="utf-8")
    )
    assert analysis["topic_failure_count"] == 9
    assert analysis["format_failure_count"] == 4
    assert analysis["intent_failure_count"] == 4
    for case, prior in zip(analysis["cases"], validation["cases"]):
        assert (
            case["expected_topic"], case["predicted_topic"],
            case["expected_format"], case["predicted_format"],
            case["expected_intent"], case["predicted_intent"],
        ) == (
            prior["expected_topic"], prior["predicted_topic"],
            prior["expected_format"], prior["predicted_format"],
            prior["expected_reader_intent"], prior["predicted_reader_intent"],
        )
    for filename, digest in VALIDATION_DIGESTS.items():
        assert sha256((BATCH_ROOT / filename).read_bytes()).hexdigest() == digest


def test_failure_classes_are_exact_and_deterministic(
    analysis: dict[str, object],
) -> None:
    assert {
        case["id"]: tuple(case["failure_classes"])
        for case in analysis["cases"]
    } == FAILURE_CLASSES
    counts: dict[str, int] = {}
    for failures in FAILURE_CLASSES.values():
        for failure in failures:
            counts[failure] = counts.get(failure, 0) + 1
    assert analysis["failure_class_counts"] == dict(sorted(counts.items()))


def test_case_046_diagnoses_domain_and_analysis_promotion(
    analysis: dict[str, object],
) -> None:
    case = _case(analysis, "046")
    assert "METHOD_SUBJECT_CONFUSION" in case["failure_classes"]
    assert "SCIENCE_BIOLOGICAL_DOMAIN_GAP" in case["failure_classes"]
    assert "SEMANTIC_RELATIONSHIP_WITHOUT_DOMAIN" in case["failure_classes"]
    assert "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED" in case["failure_classes"]
    assert "FORMAT_ANALYSIS_STRUCTURE_GAP" in case["failure_classes"]


def test_case_048_is_format_negative_control(
    analysis: dict[str, object],
) -> None:
    case = _case(analysis, "048")
    assert case["expected_format"] == case["predicted_format"] == "STANDARD_NEWS"
    assert case["deterministic_format_sufficient"] is True
    assert case["semantic_adjudication_format_candidate"] is False
    assert "CONTEXTUAL_FORMAT_OVERTRIGGER" in case["failure_classes"]
    trigger = analysis["trigger_analysis"][
        "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK"
    ]
    assert trigger["matched_cases_triggered"] == 1


def test_case_049_is_matched_deterministic_control(
    analysis: dict[str, object],
) -> None:
    case = _case(analysis, "049")
    assert case["failure_classes"] == []
    assert case["deterministic_topic_sufficient"] is True
    assert case["deterministic_format_sufficient"] is True
    assert case["semantic_adjudication_topic_candidate"] is False
    assert case["semantic_adjudication_format_candidate"] is False
    assert analysis["deterministically_sufficient_cases"] == ["049"]


def test_intent_failures_are_deterministically_downstream(
    analysis: dict[str, object],
) -> None:
    assert analysis["direct_intent_failure_count"] == 0
    assert analysis["downstream_intent_failure_count"] == 4
    intent_mismatches = [
        case for case in analysis["cases"]
        if case["expected_intent"] != case["predicted_intent"]
    ]
    assert [case["id"] for case in intent_mismatches] == [
        "044", "045", "046", "047"
    ]
    assert all(
        case["expected_format"] != case["predicted_format"]
        and "DOWNSTREAM_INTENT_FROM_WRONG_FORMAT" in case["failure_classes"]
        for case in intent_mismatches
    )


def test_adjudication_candidates_match_only_failed_dimensions(
    analysis: dict[str, object],
) -> None:
    assert analysis["semantic_adjudication_topic_candidates"] == [
        "041", "042", "043", "044", "045", "046", "047", "048", "050"
    ]
    assert analysis["semantic_adjudication_format_candidates"] == [
        "044", "045", "046", "047"
    ]


def test_candidate_triggers_and_precision_use_frozen_outputs(
    analysis: dict[str, object],
) -> None:
    assert tuple(analysis["trigger_analysis"]) == TRIGGERS
    for trigger, expected in EXPECTED_TRIGGER_COUNTS.items():
        metrics = analysis["trigger_analysis"][trigger]
        assert (
            metrics["cases_triggered"],
            metrics["matched_cases_triggered"],
            metrics["mismatched_cases_triggered"],
            metrics["precision_for_mismatch"],
        ) == expected
        if metrics["cases_triggered"]:
            assert metrics["precision_for_mismatch"] == (
                metrics["mismatched_cases_triggered"]
                / metrics["cases_triggered"]
            )


def test_analysis_does_not_recommend_benchmark_specific_keywords(
    analysis: dict[str, object],
) -> None:
    markdown = render_markdown(analysis)
    architecture = markdown.split("## Deterministic vs Adjudication Boundary", 1)[1]
    assert "add citizenship" not in architecture.casefold()
    assert "add nato" not in architecture.casefold()
    assert "add drones" not in architecture.casefold()
    assert "add virus" not in architecture.casefold()
    assert "case-specific phrases would constitute overfitting" in architecture


def test_json_excludes_full_source_bodies(
    analysis: dict[str, object],
) -> None:
    output = render_json(analysis)
    assert all("body" not in case for case in json.loads(output)["cases"])
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_outputs_are_deterministic_and_match_reports(
    analysis: dict[str, object],
) -> None:
    assert (BATCH_ROOT / "editorial_generalization_analysis.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "editorial_generalization_analysis.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_analysis_never_reads_human_risk_annotations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "human_risk_annotations.json":
            raise AssertionError("risk annotations must not be read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    assert analyze_generalization()["case_count"] == 10


def test_analysis_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert analyze_generalization()["case_count"] == 10
