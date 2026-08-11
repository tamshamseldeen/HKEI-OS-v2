"""Tests for the generic unresolved-evidence trigger diagnostic."""

from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

from examples.run_adjudication_unresolved_evidence_trigger_analysis import (
    BASE_NAME, BENCHMARK_ROOT, BATCHES, STRICT_NAME,
    analyze_unresolved_evidence_triggers, candidate_signals,
    render_json, render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from examples.run_benchmark_batch_01_analysis import (
    parse_source as parse_batch_01_source,
)
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


GATE_DIGEST = "01caf926cd7e4819b5efb31441076cca4fcefe714da881ac2ee16addcfc89e26"


def test_all_five_batches_and_fifty_cases_are_analyzed() -> None:
    analysis = analyze_unresolved_evidence_triggers()
    assert analysis["case_count"] == 50
    assert {case["batch"] for case in analysis["cases"]} == set(BATCHES)
    assert sum(case["id"] == "050" for case in analysis["cases"]) == 1
    assert sum(case["id"] == "049" for case in analysis["cases"]) == 1


def test_candidate_logic_accepts_only_structured_outputs() -> None:
    parameters = tuple(__import__("inspect").signature(candidate_signals).parameters)
    assert parameters == (
        "topic_classification", "format_classification", "intent_classification",
        "contextual_evidence", "semantic_evidence", "current_gate_topic_required",
    )
    assert {"title", "body", "source", "expected_topic"}.isdisjoint(parameters)


def test_workflow_and_gate_run_once_per_case_without_expected_inputs() -> None:
    workflow = Mock(wraps=ExperimentalSemanticEditorialAnalysisWorkflow())
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    analyze_unresolved_evidence_triggers(workflow=workflow, gate=gate)
    assert workflow.process.call_count == gate.evaluate.call_count == 50
    assert all("expected" not in call.kwargs for call in workflow.process.call_args_list)
    assert all("expected" not in call.kwargs for call in gate.evaluate.call_args_list)


def test_calculations_are_deterministic_and_derived_from_cases() -> None:
    first = analyze_unresolved_evidence_triggers()
    assert first == analyze_unresolved_evidence_triggers()
    for name, key in ((BASE_NAME, "candidate_trigger"), (STRICT_NAME, "strict_candidate_trigger")):
        result = first["candidate_analysis"][name]
        cases = first["cases"]
        assert result["incremental_true_positives"] == sum(
            case[key] and not case["topic_match"] and not case["current_gate_topic_required"]
            for case in cases
        )
        assert result["incremental_false_positives"] == sum(
            case[key] and case["topic_match"] and not case["current_gate_topic_required"]
            for case in cases
        )
        assert result["false_positives_by_batch"] == {
            batch: sum(case[key] and case["topic_match"] and not case["current_gate_topic_required"] and case["batch"] == batch for case in cases)
            for batch in BATCHES
        }


def test_critical_cases_are_reported_without_special_case_logic() -> None:
    analysis = analyze_unresolved_evidence_triggers()
    base = analysis["candidate_analysis"][BASE_NAME]
    strict = analysis["candidate_analysis"][STRICT_NAME]
    assert isinstance(base["captures_case_050"], bool)
    assert isinstance(strict["captures_case_050"], bool)
    assert isinstance(base["triggers_control_049"], bool)
    assert isinstance(strict["triggers_control_049"], bool)
    source = Path(__file__).resolve().parents[1].joinpath("examples/run_adjudication_unresolved_evidence_trigger_analysis.py").read_text()
    candidate_body = source.split("def candidate_signals", 1)[1].split("def _percentage", 1)[0]
    assert "050" not in candidate_body
    assert "049" not in candidate_body


def test_outputs_exclude_source_bodies_and_risk_metadata() -> None:
    analysis = analyze_unresolved_evidence_triggers()
    output = render_json(analysis)
    assert '"body"' not in output
    assert "human_risk_annotations" not in output
    assert "expected_risk_band" not in output
    for batch in BATCHES:
        batch_root = BENCHMARK_ROOT / batch
        for item in read_manifest(batch_root):
            path = batch_root / item["source_file"]
            source = (
                parse_batch_01_source(path)
                if batch == "batch_01"
                else parse_source(path)
            )
            assert source.body not in output
    assert "## Recommendation" in render_markdown(analysis)


def test_gate_and_production_code_are_unchanged() -> None:
    root = Path(__file__).resolve().parents[1]
    assert sha256(root.joinpath("src/adjudication/deterministic_semantic_adjudication_gate.py").read_bytes()).hexdigest() == GATE_DIGEST
    changed = __import__("subprocess").run(["git", "diff", "--name-only", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
    assert not any(path.startswith("src/") for path in changed)


def test_no_risk_api_web_or_environment_access(monkeypatch) -> None:
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
    assert analyze_unresolved_evidence_triggers()["case_count"] == 50
