"""Tests for the offline OpenAI adjudication prompt contract audit."""

import inspect
import json

import examples.run_openai_adjudication_prompt_contract_audit as diagnostic


def test_prompt_version_formats_and_critical_matrix_are_deterministic() -> None:
    first = diagnostic.audit()
    second = diagnostic.audit()
    assert first == second
    assert first["prompt_version"] == "1.1"
    assert first["format_count"] == 12
    assert first["format_operational_count"] == 12
    assert len(first["format_definitions"]) == 12
    assert first["critical_pair_matrix"] == diagnostic.CRITICAL_PAIR_MATRIX
    assert "HIGH_OVERLAP" not in first["critical_pair_matrix"].values()


def test_semantics_anchoring_evidence_and_safety_findings() -> None:
    result = diagnostic.audit()
    assert result["topic_definition_operational"] is True
    assert result["anchoring_reduction_strength"] == "STRONG"
    assert set(result["structured_evidence_audit"].values()) == {
        "DEFINED_AND_ACTIONABLE"
    }
    assert result["suppression_semantics_correct"] is True
    assert result["evidence_priority_order"][-1] == (
        "deterministic baseline as reference only"
    )
    assert result["cot_safe"] is True
    assert result["confidence_semantics"] == "CLEAR"
    assert result["ambiguity_guidance_clear"] is True
    assert result["candidate_duplication"] == {
        "label_occurrences_across_definitions_legal_candidates_baseline": 18,
        "qualitative_impact": "LOW",
        "explanation": (
            "Candidate names recur in definitions, legal candidates, and the "
            "baseline only where needed to define, constrain, and contextualize."
        ),
    }


def test_prompt_sizes_and_economy_are_deterministic() -> None:
    result = diagnostic.audit()
    metrics = result["prompt_size_metrics"]
    assert set(metrics) == {
        "TOPIC_REQUIRED", "FORMAT_REQUIRED", "TOPIC_AND_FORMAT_REQUIRED"
    }
    assert all(
        set(item) == {
            "instruction_chars",
            "total_prompt_chars",
            "label_definition_chars",
            "structured_evidence_instruction_chars",
        }
        for item in metrics.values()
    )
    assert all(item["total_prompt_chars"] <= 7000 for item in metrics.values())
    assert result["prompt_economy"] == "COMPACT"


def test_outputs_have_no_source_body_or_benchmark_leakage() -> None:
    result = diagnostic.audit()
    combined = diagnostic.render_json(result) + diagnostic.render_markdown(result)
    assert result["benchmark_leakage"] is False
    assert "Synthetic body excerpt" not in combined
    assert "SOURCE_CONTENT_UNTRUSTED" not in combined
    assert not any(case_id in combined for case_id in ("044", "045", "046", "048", "050"))
    assert json.loads(diagnostic.render_json(result))["overall_quality"] == "EXCELLENT"


def test_audit_has_no_provider_call_network_or_production_write() -> None:
    source = inspect.getsource(diagnostic)
    forbidden = (
        "responses.create",
        ".adjudicate(",
        "OpenAI(",
        "httpx",
        "socket",
        "OPENAI_API_KEY",
        "src/adjudication/openai_semantic_adjudication_provider.py",
    )
    assert not any(value in source for value in forbidden)
    assert diagnostic.OUTPUT_JSON.parent.name == "benchmark"
    assert diagnostic.OUTPUT_MD.parent.name == "benchmark"
