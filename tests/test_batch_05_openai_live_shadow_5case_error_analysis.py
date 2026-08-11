"""Tests for offline analysis of persisted five-case OpenAI results."""

import inspect
import json
from pathlib import Path

import pytest

import examples.run_batch_05_openai_live_shadow_5case_error_analysis as diagnostic
from examples.run_benchmark_batch_02_validation import parse_source


def test_analysis_uses_exact_persisted_cases_and_metrics() -> None:
    analysis = diagnostic.analyze()
    assert analysis["cases_analyzed"] == ["044", "045", "046", "048", "050"]
    assert [case["id"] for case in analysis["cases"]] == analysis["cases_analyzed"]
    assert analysis["topic_accuracy"] == 60.0
    assert analysis["format_accuracy"] == 0.0
    assert analysis["valid_responses"] == 5


def test_candidate_availability_anchoring_and_ambiguity_metrics() -> None:
    analysis = diagnostic.analyze()
    cases = analysis["cases"]
    assert all(case["expected_topic_available"] is True for case in cases)
    assert all(
        case["expected_format_available"] is True
        for case in cases if case["format_correct"] is not None
    )
    assert analysis["format_required_cases"] == 3
    assert analysis["format_deterministic_preserved_count"] == 3
    assert analysis["format_deterministic_preserved_rate"] == 100.0
    assert analysis["wrong_format_with_deterministic_preserved_count"] == 3
    assert analysis["topic_deterministic_preserved_count"] == 2
    assert analysis["ambiguity_correct_cases"] == 1
    assert analysis["ambiguity_wrong_cases"] == 2


def test_deterministic_failure_classes_and_excerpt_rules() -> None:
    analysis = diagnostic.analyze()
    by_id = {case["id"]: case for case in analysis["cases"]}
    assert analysis["label_semantics_issue_cases"] == 3
    assert analysis["structured_evidence_underused_cases"] == 1
    assert analysis["excerpt_information_gap_cases"] == 2
    assert by_id["044"]["primary_failure_class"] == (
        "LABEL_SEMANTICS_UNDERSPECIFIED"
    )
    assert by_id["045"]["primary_failure_class"] == (
        "LABEL_SEMANTICS_UNDERSPECIFIED"
    )
    assert by_id["046"]["primary_failure_class"] == (
        "STRUCTURED_EVIDENCE_UNDERUSED"
    )
    assert by_id["048"]["primary_failure_class"] == (
        "AMBIGUITY_SIGNAL_MEANINGFUL"
    )
    assert by_id["050"]["primary_failure_class"] == "UNKNOWN"
    assert all(
        set(case["failure_classes"]).issubset(diagnostic.FAILURE_CLASSES)
        for case in analysis["cases"]
    )


def test_outputs_are_metrics_only_without_sources_or_secrets(tmp_path: Path) -> None:
    analysis = diagnostic.analyze()
    json_text = diagnostic.render_json(analysis)
    markdown = diagnostic.render_markdown(analysis)
    combined = json_text + markdown
    assert "OPENAI_API_KEY" not in combined
    assert "test-only-secret" not in combined
    assert "SOURCE_CONTENT_UNTRUSTED" not in combined
    assert "raw_response" not in combined
    for case_id in diagnostic.CASE_IDS:
        source = parse_source(diagnostic.BATCH_ROOT / case_id / "source.md")
        assert source.body not in combined
    assert json.loads(json_text)["recommended_next_step"] == "COMBINATION_OF_A_B_C"


def test_module_has_no_provider_gate_prompt_or_network_execution() -> None:
    source = inspect.getsource(diagnostic)
    forbidden = (
        "OpenAI(",
        "responses.create",
        "provider.adjudicate",
        "ExperimentalSemanticAdjudicationShadowWorkflow",
        "DeterministicSemanticAdjudicationGate",
        "SemanticAdjudicationRequestBuilder",
        "OPENAI_API_KEY",
        "_INSTRUCTIONS",
        "socket",
        "httpx",
    )
    assert not any(value in source for value in forbidden)
