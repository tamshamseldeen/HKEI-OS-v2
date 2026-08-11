"""Tests for the Batch 04 semantic coverage failure analysis."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_04_semantic_coverage_analysis import (
    BATCH_ROOT,
    CASE_IDS,
    INSPECTED_ROLES,
    analyze_coverage,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)


FROZEN_INPUT_DIGEST = (
    "20c08c974d31c3bb762437e6a3970a2b31dd16431cf43084cd7470f791f38224"
)
RISK_ANNOTATION_DIGEST = (
    "aa3d0b9616368d449e4bb60d1f71cbf923556da089553468b42d3797969b4ad6"
)
EXPECTED_FAILURE_COUNTS = {
    "CONTEXTUAL_EVIDENCE_MISSING": 3,
    "CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED": 6,
    "SEMANTIC_RELATIONSHIP_PRESENT_WITHOUT_DOMAIN": 1,
    "SEMANTIC_DOMAIN_PRESENT_BUT_NOT_RECORDED_AS_USED": 0,
    "DOMAIN_MODEL_COVERAGE_GAP": 10,
    "FORMAT_SEMANTIC_COVERAGE_GAP": 4,
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    return analyze_coverage()


def _digest(paths: list[Path]) -> str:
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(BATCH_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_exactly_cases_031_through_040_are_analyzed(
    analysis: dict[str, object],
) -> None:
    assert CASE_IDS == tuple(f"{case_id:03d}" for case_id in range(31, 41))
    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in analysis["cases"]) == CASE_IDS
    assert {"039", "040"} <= {case["id"] for case in analysis["cases"]}


def test_pipeline_layers_receive_each_persisted_source_independently() -> None:
    classification = Mock(wraps=EditorialClassificationWorkflow())
    contextual = Mock(wraps=DeterministicContextualEvidenceEngine())
    semantic = Mock(wraps=DeterministicCompositionalSemanticEngine())

    analyze_coverage(
        classification_workflow=classification,
        contextual_engine=contextual,
        semantic_engine=semantic,
    )

    assert classification.process.call_count == 10
    assert contextual.analyze.call_count == 10
    assert semantic.compose.call_count == 10
    for case_id, classification_call, contextual_call, semantic_call in zip(
        CASE_IDS,
        classification.process.call_args_list,
        contextual.analyze.call_args_list,
        semantic.compose.call_args_list,
    ):
        persisted = parse_source(BATCH_ROOT / case_id / "source.md")
        assert classification_call.kwargs["title"] == persisted.title
        assert classification_call.kwargs["body"] == persisted.body
        assert classification_call.kwargs["category"] is None
        source = contextual_call.kwargs["source"]
        assert source.title == persisted.title
        assert source.body == persisted.body
        assert semantic_call.kwargs["source"] is source
        assert (
            semantic_call.kwargs["contextual_evidence"]
            is contextual.return_value.analyze.return_value
            or semantic_call.kwargs["contextual_evidence"] is not None
        )


def test_diagnostic_runner_has_no_topic_format_or_intent_classifier() -> None:
    runner = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "run_batch_04_semantic_coverage_analysis.py"
    ).read_text(encoding="utf-8")
    assert "DeterministicTopicClassifier" not in runner
    assert "DeterministicEditorialFormatClassifier" not in runner
    assert "DeterministicReaderIntentClassifierV2" not in runner


def test_observed_counts_and_summary_lists_are_exact(
    analysis: dict[str, object],
) -> None:
    assert analysis["cases_with_contextual_evidence"] == 7
    assert analysis["cases_with_semantic_relationships"] == 1
    assert analysis["cases_with_primary_domain_candidates"] == 0
    assert analysis["cases_with_secondary_domain_candidates"] == 0
    assert analysis["cases_with_semantic_format_support"] == 0
    assert analysis["contextual_missing_cases"] == ["033", "037", "039"]
    assert analysis["uncomposed_context_cases"] == [
        "031", "032", "034", "035", "036", "040"
    ]
    assert analysis["relationship_without_domain_cases"] == ["038"]
    assert analysis["semantic_domain_cases"] == []


def test_per_case_counts_match_recorded_evidence(
    analysis: dict[str, object],
) -> None:
    for case in analysis["cases"]:
        assert case["contextual_item_count"] == sum(
            case["contextual_role_counts"].values()
        )
        assert tuple(case["contextual_role_counts"]) == INSPECTED_ROLES
        assert case["contextual_item_count"] == sum(
            len(items) for items in case["contextual_evidence_by_role"].values()
        )
        assert case["semantic_relationship_count"] == len(
            case["semantic_relationships"]
        )
        assert case["semantic_relationship_types"] == list(
            dict.fromkeys(
                item["relationship_type"]
                for item in case["semantic_relationships"]
            )
        )


def test_failure_classes_are_deterministic(
    analysis: dict[str, object],
) -> None:
    assert analysis["failure_class_counts"] == EXPECTED_FAILURE_COUNTS
    assert {
        case["id"]: case["failure_classes"] for case in analysis["cases"]
    } == {
        "031": ["CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED", "DOMAIN_MODEL_COVERAGE_GAP"],
        "032": ["CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED", "DOMAIN_MODEL_COVERAGE_GAP"],
        "033": ["CONTEXTUAL_EVIDENCE_MISSING", "DOMAIN_MODEL_COVERAGE_GAP", "FORMAT_SEMANTIC_COVERAGE_GAP"],
        "034": ["CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED", "DOMAIN_MODEL_COVERAGE_GAP"],
        "035": ["CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED", "DOMAIN_MODEL_COVERAGE_GAP", "FORMAT_SEMANTIC_COVERAGE_GAP"],
        "036": ["CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED", "DOMAIN_MODEL_COVERAGE_GAP", "FORMAT_SEMANTIC_COVERAGE_GAP"],
        "037": ["CONTEXTUAL_EVIDENCE_MISSING", "DOMAIN_MODEL_COVERAGE_GAP"],
        "038": ["SEMANTIC_RELATIONSHIP_PRESENT_WITHOUT_DOMAIN", "DOMAIN_MODEL_COVERAGE_GAP", "FORMAT_SEMANTIC_COVERAGE_GAP"],
        "039": ["CONTEXTUAL_EVIDENCE_MISSING", "DOMAIN_MODEL_COVERAGE_GAP"],
        "040": ["CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED", "DOMAIN_MODEL_COVERAGE_GAP"],
    }


def test_json_excludes_full_bodies_and_risk_annotations(
    analysis: dict[str, object],
) -> None:
    output = render_json(analysis)
    assert "expected_risk_band" not in output
    assert "attribution_required" not in output
    for case_id in CASE_IDS:
        assert parse_source(BATCH_ROOT / case_id / "source.md").body not in output


def test_outputs_are_deterministic_and_match_reports(
    analysis: dict[str, object],
) -> None:
    assert (BATCH_ROOT / "semantic_coverage_analysis.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "semantic_coverage_analysis.md").read_text(
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
    assert analyze_coverage()["case_count"] == 10


def test_analysis_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert analyze_coverage()["case_count"] == 10


def test_frozen_sources_labels_and_risk_annotations_are_unchanged() -> None:
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
