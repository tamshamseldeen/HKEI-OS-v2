"""Tests for Batch 05 end-to-end adjudication shadow plumbing."""

import inspect
import json
import os
from pathlib import Path
import socket

import pytest

import examples.run_batch_05_adjudication_shadow_plumbing as diagnostic
from examples.run_batch_05_adjudication_shadow_plumbing import (
    BATCH_ROOT,
    CASE_IDS,
    OUTPUT_JSON,
    OUTPUT_MD,
    OfflineOracleProvider,
    analyze_shadow_plumbing,
    diagnostic_status,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.adjudication.adjudication_scope import AdjudicationScope
from src.workflows.experimental_semantic_adjudication_shadow_result import (
    ExperimentalSemanticAdjudicationShadowResult,
)


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    return json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))


def test_exactly_ten_cases_and_expected_request_split(
    analysis: dict[str, object],
) -> None:
    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in analysis["cases"]) == CASE_IDS
    assert analysis["requests_created"] == 9
    assert analysis["requests_avoided"] == 1
    assert analysis["provider_calls"] == 9


def test_not_required_control_avoids_entire_provider_path(
    analysis: dict[str, object],
) -> None:
    control = next(case for case in analysis["cases"] if case["id"] == "049")
    assert control["gate_scope"] == AdjudicationScope.NOT_REQUIRED.value
    assert control["request_created"] is False
    assert control["provider_called"] is False
    assert control["response_valid"] is False
    assert control["oracle_topic"] is None
    assert control["oracle_format"] is None


def test_all_normal_provider_responses_validate_once_per_request(
    analysis: dict[str, object],
) -> None:
    required = [case for case in analysis["cases"] if case["request_created"]]
    assert len(required) == 9
    assert analysis["validated_responses"] == 9
    assert analysis["invalid_responses"] == 0
    assert analysis["provider_errors"] == 0
    assert all(
        case["provider_called"]
        and case["response_valid"]
        and case["fingerprint_valid"]
        and case["provider_error"] is None
        for case in required
    )


def test_oracle_selections_are_covered_by_request_candidates(
    analysis: dict[str, object],
) -> None:
    assert analysis["topic_required_cases"] == 9
    assert analysis["format_required_cases"] == 4
    assert analysis["oracle_expected_topic_in_candidates"] == 9
    assert analysis["oracle_expected_format_in_candidates"] == 4
    assert analysis["expected_topic_candidate_coverage"] == 100.0
    assert analysis["expected_format_candidate_coverage"] == 100.0
    assert analysis["validated_topic_matches_expected"] == 9
    assert analysis["validated_format_matches_expected"] == 4


def test_shadow_never_mutates_deterministic_editorial_dimensions(
    analysis: dict[str, object],
) -> None:
    assert analysis["shadow_topic_mutations"] == 0
    assert analysis["shadow_format_mutations"] == 0
    assert analysis["shadow_intent_mutations"] == 0
    assert all(
        not case["topic_changed_in_shadow"]
        and not case["format_changed_in_shadow"]
        and not case["intent_changed_in_shadow"]
        for case in analysis["cases"]
    )


def test_invalid_and_unavailable_provider_probes_pass(
    analysis: dict[str, object],
) -> None:
    assert analysis["invalid_probe_passed"] is True
    assert analysis["provider_error_probe_passed"] is True


def test_expectations_are_confined_to_offline_oracle() -> None:
    provider_source = inspect.getsource(OfflineOracleProvider)
    workflow_source = inspect.getsource(
        diagnostic.ExperimentalSemanticAdjudicationShadowWorkflow
    )
    result_fields = ExperimentalSemanticAdjudicationShadowResult.__dataclass_fields__
    assert "expected_topic" in provider_source
    assert "expected_format" in provider_source
    assert "expected_topic" not in workflow_source
    assert "expected_format" not in workflow_source
    assert not any(name.startswith("resolved_") for name in result_fields)


def test_oracle_metadata_and_evidence_are_offline_and_contract_bounded() -> None:
    source = inspect.getsource(OfflineOracleProvider)
    assert 'return "offline-oracle"' in source
    assert 'return "diagnostic-v1"' in source
    assert 'request_schema_version="1.0"' in source
    assert 'response_schema_version="1.0"' in source
    assert 'input_fingerprint=request.input_fingerprint' in source
    assert '("HEADLINE",)' in source
    assert '("LEAD",)' in source
    assert "OpenAI" not in source


def test_json_has_no_source_body_resolver_or_risk_metadata(
    analysis: dict[str, object],
) -> None:
    rendered = render_json(analysis)
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in rendered
    forbidden = (
        '"source_body"', '"body"', '"resolved_topic"', '"resolved_format"',
        '"resolved_reader_intent"', '"risk_band"', '"attribution_required"',
        '"uncertainty_present"', '"sensitive_context"',
    )
    assert not any(value in rendered for value in forbidden)


def test_runner_never_reads_risk_annotations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[str] = []
    original = Path.read_text

    def tracked(path: Path, *args: object, **kwargs: object) -> str:
        reads.append(path.name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked)
    result = analyze_shadow_plumbing()
    assert result["case_count"] == 10
    assert "human_risk_annotations.json" not in reads
    assert not any("risk" in name.casefold() for name in reads)


def test_runner_uses_no_external_api_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(os, "getenv", fail)
    assert diagnostic_status(analyze_shadow_plumbing()) == "EXCELLENT"


def test_persisted_outputs_match_deterministic_rendering(
    analysis: dict[str, object],
) -> None:
    assert OUTPUT_JSON.read_text(encoding="utf-8") == render_json(analysis)
    assert OUTPUT_MD.read_text(encoding="utf-8") == render_markdown(analysis)
    assert diagnostic_status(analysis) == "EXCELLENT"
