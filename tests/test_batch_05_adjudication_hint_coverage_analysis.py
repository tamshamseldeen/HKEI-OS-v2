"""Tests for Batch 05 contextual adjudication-hint coverage diagnosis."""

import json
from hashlib import sha256
import os
from pathlib import Path
import socket
from unittest.mock import Mock

from examples.run_batch_05_adjudication_hint_coverage_analysis import (
    BATCH_ROOT, NEGATIVE_CONTROLS, TARGETS, analyze_hint_coverage,
    render_json, render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)


def test_exact_target_cases_and_negative_controls_are_analyzed() -> None:
    analysis = analyze_hint_coverage()
    assert analysis["cases_analyzed"] == 6
    assert analysis["target_cases"] == ["044", "045", "047", "050"]
    assert analysis["negative_controls"] == ["048", "049"]
    assert tuple(TARGETS) == ("044", "045", "047", "050")
    assert NEGATIVE_CONTROLS == ("048", "049")


def test_contextual_engine_runs_once_per_case_without_gate_or_classifiers() -> None:
    engine = Mock(wraps=DeterministicContextualEvidenceEngine())
    analysis = analyze_hint_coverage(evidence_engine=engine)
    assert engine.analyze.call_count == 6
    assert analysis["hints_observed"] == 0
    runner = Path(__file__).resolve().parents[1] / "examples" / "run_batch_05_adjudication_hint_coverage_analysis.py"
    source = runner.read_text(encoding="utf-8")
    imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    assert not any(value in line for line in imports for value in ("Gate", "Classifier", "Workflow", "Provider"))


def test_component_and_locality_diagnosis_is_exact_and_deterministic() -> None:
    first = analyze_hint_coverage()
    second = analyze_hint_coverage()
    assert first == second
    assert first["cases_requiring_cross_sentence_structure"] == ["044", "045", "047", "050"]
    assert first["cases_with_components_present_but_uncombined"] == ["044", "045", "047", "050"]
    assert first["cases_with_missing_component_extraction"] == ["044", "045", "047", "050"]
    for case in first["cases"][:4]:
        assert all(component["source_present"] for component in case["component_matrix"])
        assert any(not component["context_detected"] for component in case["component_matrix"])
        assert case["locality_analysis"] == {
            "same_sentence_possible": False,
            "same_paragraph_possible": False,
            "cross_sentence_required": True,
            "document_level_pattern_required": False,
        }


def test_negative_controls_remain_hint_free_and_explained() -> None:
    analysis = analyze_hint_coverage()
    by_id = {case["id"]: case for case in analysis["cases"]}
    assert by_id["048"]["hint_observed"] is False
    assert by_id["049"]["hint_observed"] is False
    assert by_id["048"]["recommendation_classes"] == ["KEEP_CURRENT_BEHAVIOR"]
    assert by_id["049"]["recommendation_classes"] == ["KEEP_CURRENT_BEHAVIOR"]
    assert {component["component_name"] for component in by_id["048"]["component_matrix"]} == {"prediction", "uncertainty", "future_possibility", "intelligence_estimate"}


def test_output_contains_no_body_risk_metadata_or_keyword_recommendation() -> None:
    analysis = analyze_hint_coverage()
    output = render_json(analysis)
    for case_id in (*TARGETS, *NEGATIVE_CONTROLS):
        assert parse_source(BATCH_ROOT / case_id / "source.md").body not in output
    assert "human_risk_annotations" not in output
    assert "expected_risk_band" not in output
    assert "benchmark-specific words" not in render_markdown(analysis)
    assert '"body"' not in output


def test_runner_never_reads_risk_annotations_or_uses_external_access(monkeypatch) -> None:
    original = Path.read_text
    def guarded(path: Path, *args, **kwargs):
        if path.name == "human_risk_annotations.json":
            raise AssertionError("risk annotations are forbidden")
        return original(path, *args, **kwargs)
    def fail(*args, **kwargs):
        raise AssertionError("external access is forbidden")
    monkeypatch.setattr(Path, "read_text", guarded)
    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(os, "getenv", fail)
    assert analyze_hint_coverage()["cases_analyzed"] == 6


def test_hint_engine_and_gate_implementations_are_unchanged() -> None:
    root = Path(__file__).resolve().parents[1]
    assert sha256(
        (root / "src/evidence/deterministic_contextual_evidence_engine.py").read_bytes()
    ).hexdigest() == "d86e8297a60a5474b3b4b25814aba5961ce6c73bf6d80fe2003f9f961b4db505"
    assert sha256(
        (root / "src/adjudication/deterministic_semantic_adjudication_gate.py").read_bytes()
    ).hexdigest() == "01caf926cd7e4819b5efb31441076cca4fcefe714da881ac2ee16addcfc89e26"
