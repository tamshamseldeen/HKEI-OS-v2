"""Tests for the Batch 05 semantic request-builder shadow diagnostic."""

import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

import examples.run_batch_05_adjudication_request_shadow as diagnostic
from examples.run_batch_05_adjudication_request_shadow import (
    BATCH_ROOT,
    CASE_IDS,
    OUTPUT_JSON,
    OUTPUT_MD,
    analyze_request_shadow,
    diagnostic_status,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_request_builder import (
    SemanticAdjudicationRequestBuilder,
)
from src.formatting.editorial_format import EditorialFormat
from src.topic.topic import Topic
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    return json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))


def test_exactly_ten_cases_are_analyzed(analysis: dict[str, object]) -> None:
    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in analysis["cases"]) == CASE_IDS


def test_gate_runs_for_all_cases_and_builder_only_for_required_cases() -> None:
    workflow = Mock(wraps=ExperimentalSemanticEditorialAnalysisWorkflow())
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    builder = Mock(wraps=SemanticAdjudicationRequestBuilder())
    result = analyze_request_shadow(workflow=workflow, gate=gate, builder=builder)
    assert workflow.process.call_count == 10
    assert gate.evaluate.call_count == 10
    assert builder.build.call_count == 18  # Each of nine requests is rebuilt once.
    request_ids = [call.kwargs["request_id"] for call in builder.build.call_args_list]
    assert set(request_ids) == {
        f"batch_05_{case_id}" for case_id in CASE_IDS if case_id != "049"
    }
    assert request_ids.count("batch_05_049") == 0
    assert result["requests_created"] == 9
    assert result["requests_avoided"] == 1


def test_not_required_control_has_no_request(analysis: dict[str, object]) -> None:
    control = next(case for case in analysis["cases"] if case["id"] == "049")
    assert control["gate_scope"] == AdjudicationScope.NOT_REQUIRED.value
    assert control["request_created"] is False
    assert control["request_id"] is None
    assert control["candidate_topics"] == []
    assert control["candidate_formats"] == []


def test_limits_fingerprints_candidates_and_scope_are_valid(
    analysis: dict[str, object],
) -> None:
    valid_topics = {topic.value for topic in Topic}
    valid_formats = {editorial_format.value for editorial_format in EditorialFormat}
    for case in analysis["cases"]:
        if not case["request_created"]:
            continue
        assert case["lead_length"] <= 500
        assert case["body_excerpt_length"] <= 1800
        assert len(case["input_fingerprint"]) == 64
        assert set(case["input_fingerprint"]) <= set("0123456789abcdef")
        assert case["fingerprint_stable"] is True
        assert set(case["candidate_topics"]) <= valid_topics
        assert set(case["candidate_formats"]) <= valid_formats
        assert case["candidate_topics"]
        assert case["candidate_formats"]
        if not case["topic_required"]:
            assert len(case["candidate_topics"]) == 1
        if not case["format_required"]:
            assert len(case["candidate_formats"]) == 1
        assert case["request_valid"] is True


def test_expectations_are_read_only_after_requests_are_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    real_builder = SemanticAdjudicationRequestBuilder()
    builder = Mock(wraps=real_builder)

    def tracked_build(**kwargs: object) -> object:
        events.append("build")
        assert "expected_topic" not in kwargs
        assert "expected_format" not in kwargs
        return real_builder.build(**kwargs)

    builder.build.side_effect = tracked_build
    original_expectations = diagnostic.read_expectations

    def tracked_expectations(path: Path) -> list[dict[str, str]]:
        events.append("expectations")
        return original_expectations(path)

    monkeypatch.setattr(diagnostic, "read_expectations", tracked_expectations)
    analyze_request_shadow(builder=builder)
    assert events.count("build") == 18
    assert events[-1] == "expectations"


def test_expected_candidate_coverage_is_offline_and_exact(
    analysis: dict[str, object],
) -> None:
    assert analysis["topic_required_cases"] == 9
    assert analysis["format_required_cases"] == 4
    assert analysis["expected_topic_candidate_coverage"] == 0.0
    assert analysis["expected_format_candidate_coverage"] == 25.0
    assert analysis["cases_missing_expected_topic_candidate"] == [
        "041", "042", "043", "044", "045", "046", "047", "048", "050"
    ]
    assert analysis["cases_missing_expected_format_candidate"] == [
        "044", "045", "047"
    ]
    assert diagnostic_status(analysis) == "FAILED"


def test_isolation_fields_are_all_negative(analysis: dict[str, object]) -> None:
    assert analysis["risk_metadata_present"] is False
    assert analysis["reader_intent_present"] is False
    assert analysis["provider_metadata_present"] is False
    assert analysis["api_credentials_present"] is False
    assert all(
        not case["request_contains_risk_metadata"]
        and not case["request_contains_reader_intent"]
        and not case["request_contains_provider_metadata"]
        and not case["request_contains_api_credentials"]
        for case in analysis["cases"]
    )


def test_json_has_no_full_source_body_or_request_payload_metadata(
    analysis: dict[str, object],
) -> None:
    rendered = render_json(analysis)
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in rendered
    forbidden_payload_fields = (
        '"attribution_required"',
        '"uncertainty_present"',
        '"sensitive_context"',
        '"reader_intent"',
        '"api_key"',
        '"provider"',
        '"model"',
    )
    assert not any(field in rendered for field in forbidden_payload_fields)


def test_persisted_outputs_match_deterministic_rendering(
    analysis: dict[str, object],
) -> None:
    assert OUTPUT_JSON.read_text(encoding="utf-8") == render_json(analysis)
    assert OUTPUT_MD.read_text(encoding="utf-8") == render_markdown(analysis)


def test_runner_never_reads_risk_annotations(monkeypatch: pytest.MonkeyPatch) -> None:
    reads: list[str] = []
    original = Path.read_text

    def tracked(path: Path, *args: object, **kwargs: object) -> str:
        reads.append(path.name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked)
    analyze_request_shadow()
    assert "human_risk_annotations.json" not in reads
    assert not any("risk" in name.casefold() for name in reads)


def test_no_api_web_environment_or_provider_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(os, "getenv", fail)
    analysis = analyze_request_shadow()
    assert analysis["case_count"] == 10
