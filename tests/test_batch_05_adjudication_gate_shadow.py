"""Tests for the frozen Batch 05 shadow adjudication gate diagnostic."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_05_adjudication_gate_shadow import (
    BATCH_ROOT,
    CASE_IDS,
    TRIGGER_SIGNALS,
    analyze_shadow_gate,
    diagnostic_status,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


VALIDATION_DIGESTS = {
    "editorial_validation.json": (
        "a8b210cb8ece13d77cb3f594a3048cac1d306148d9de30fcedc1abd0ae5c9fe3"
    ),
    "editorial_validation.md": (
        "120046742a0466d1666f9684e5582fd85505f72066d6d905b2745b06582fa3ad"
    ),
}
CASE_KEYS = {
    "id",
    "topic_match",
    "format_match",
    "intent_match",
    "full_match",
    "gate_scope",
    "topic_required",
    "format_required",
    "trigger_signals",
    "reason_codes",
    "warnings",
    "topic_should_adjudicate",
    "format_should_adjudicate",
    "topic_gate_correct",
    "format_gate_correct",
    "topic_false_positive",
    "topic_false_negative",
    "format_false_positive",
    "format_false_negative",
}


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    return json.loads(
        (BATCH_ROOT / "adjudication_gate_shadow.json").read_text(
            encoding="utf-8"
        )
    )


def _case(analysis: dict[str, object], case_id: str) -> dict[str, object]:
    return next(case for case in analysis["cases"] if case["id"] == case_id)


def test_exactly_cases_041_through_050_are_analyzed(
    analysis: dict[str, object],
) -> None:
    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in analysis["cases"]) == CASE_IDS
    assert all(set(case) == CASE_KEYS for case in analysis["cases"])


def test_existing_validation_supplies_only_gate_quality_truth(
    analysis: dict[str, object],
) -> None:
    validation = json.loads(
        (BATCH_ROOT / "editorial_validation.json").read_text(encoding="utf-8")
    )
    for case, frozen in zip(analysis["cases"], validation["cases"]):
        assert case["topic_match"] is frozen["topic_match"]
        assert case["format_match"] is frozen["format_match"]
        assert case["intent_match"] is frozen["reader_intent_match"]
        assert case["full_match"] is frozen["full_match"]
        assert case["topic_should_adjudicate"] is (not frozen["topic_match"])
        assert case["format_should_adjudicate"] is (not frozen["format_match"])
    for filename, digest in VALIDATION_DIGESTS.items():
        assert sha256((BATCH_ROOT / filename).read_bytes()).hexdigest() == digest


def test_workflow_and_gate_run_once_per_case_without_truth_inputs() -> None:
    workflow = Mock(wraps=ExperimentalSemanticEditorialAnalysisWorkflow())
    gate = Mock(wraps=DeterministicSemanticAdjudicationGate())
    analyze_shadow_gate(workflow=workflow, gate=gate)
    assert workflow.process.call_count == gate.evaluate.call_count == 10
    for workflow_call, gate_call, manifest_case in zip(
        workflow.process.call_args_list,
        gate.evaluate.call_args_list,
        read_manifest(BATCH_ROOT),
    ):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert workflow_call.kwargs["title"] == source.title
        assert workflow_call.kwargs["body"] == source.body
        assert workflow_call.kwargs["category"] is None
        assert set(gate_call.kwargs) == {
            "topic_classification",
            "format_classification",
            "contextual_evidence",
            "semantic_evidence",
        }
        assert "topic_should_adjudicate" not in gate_call.kwargs
        assert "format_should_adjudicate" not in gate_call.kwargs


def test_topic_confusion_matrix_and_metrics_are_exact(
    analysis: dict[str, object],
) -> None:
    assert (
        analysis["topic_true_positives"],
        analysis["topic_false_positives"],
        analysis["topic_true_negatives"],
        analysis["topic_false_negatives"],
    ) == (8, 0, 1, 1)
    assert analysis["topic_precision"] == 100.0
    assert analysis["topic_recall"] == 8 / 9 * 100.0
    assert analysis["topic_specificity"] == 100.0
    assert analysis["topic_accuracy"] == 90.0


def test_format_confusion_matrix_and_metrics_are_exact(
    analysis: dict[str, object],
) -> None:
    assert (
        analysis["format_true_positives"],
        analysis["format_false_positives"],
        analysis["format_true_negatives"],
        analysis["format_false_negatives"],
    ) == (1, 0, 6, 3)
    assert analysis["format_precision"] == 100.0
    assert analysis["format_recall"] == 25.0
    assert analysis["format_specificity"] == 100.0
    assert analysis["format_accuracy"] == 70.0


def test_case_flags_derive_the_same_confusion_matrix(
    analysis: dict[str, object],
) -> None:
    cases = analysis["cases"]
    for dimension in ("topic", "format"):
        assert analysis[f"{dimension}_false_positives"] == sum(
            case[f"{dimension}_false_positive"] for case in cases
        )
        assert analysis[f"{dimension}_false_negatives"] == sum(
            case[f"{dimension}_false_negative"] for case in cases
        )
        assert all(
            case[f"{dimension}_gate_correct"]
            is not (
                case[f"{dimension}_false_positive"]
                or case[f"{dimension}_false_negative"]
            )
            for case in cases
        )


def test_provider_call_metrics_and_scope_distribution_are_exact(
    analysis: dict[str, object],
) -> None:
    assert analysis["provider_call_cases"] == 8
    assert analysis["provider_call_rate"] == 80.0
    assert analysis["correctly_avoided_call_cases"] == 1
    assert analysis["unnecessary_provider_call_cases"] == 0
    assert analysis["missed_adjudication_cases"] == 1
    assert analysis["scope_distribution"] == {
        "NOT_REQUIRED": 2,
        "TOPIC_REQUIRED": 7,
        "FORMAT_REQUIRED": 0,
        "TOPIC_AND_FORMAT_REQUIRED": 1,
    }
    assert analysis["provider_call_cases"] == sum(
        case["gate_scope"] != AdjudicationScope.NOT_REQUIRED.value
        for case in analysis["cases"]
    )


def test_trigger_distribution_is_derived_from_case_records(
    analysis: dict[str, object],
) -> None:
    assert tuple(analysis["trigger_distribution"]) == TRIGGER_SIGNALS
    for trigger, metrics in analysis["trigger_distribution"].items():
        triggered = [
            case for case in analysis["cases"]
            if trigger in case["trigger_signals"]
        ]
        assert metrics == {
            "cases_triggered": len(triggered),
            "topic_mismatch_cases": sum(not case["topic_match"] for case in triggered),
            "format_mismatch_cases": sum(not case["format_match"] for case in triggered),
            "fully_matched_cases": sum(case["full_match"] for case in triggered),
        }


def test_control_case_049_avoids_adjudication(
    analysis: dict[str, object],
) -> None:
    control = _case(analysis, "049")
    assert control["topic_match"] is True
    assert control["gate_scope"] == "NOT_REQUIRED"
    assert control["topic_required"] is False
    assert control["format_required"] is False
    assert control["trigger_signals"] == []


def test_coverage_and_errors_are_preserved_without_tuning(
    analysis: dict[str, object],
) -> None:
    assert analysis["topic_captured_cases"] == [
        "041", "042", "043", "044", "045", "046", "047", "048"
    ]
    assert analysis["format_captured_cases"] == ["046"]
    assert [
        case["id"] for case in analysis["cases"]
        if case["topic_false_negative"]
    ] == ["050"]
    assert [
        case["id"] for case in analysis["cases"]
        if case["topic_false_positive"]
    ] == []
    assert [
        case["id"] for case in analysis["cases"]
        if case["format_false_negative"]
    ] == ["044", "045", "047"]
    assert [
        case["id"] for case in analysis["cases"]
        if case["format_false_positive"]
    ] == []
    assert diagnostic_status(analysis) == "FAILED"


def test_json_excludes_source_bodies_and_risk_metadata(
    analysis: dict[str, object],
) -> None:
    output = render_json(analysis)
    forbidden = (
        "expected_risk_band",
        "attribution_required",
        "uncertainty_present",
        "sensitive_context",
    )
    assert not any(field in output for field in forbidden)
    for manifest_case in read_manifest(BATCH_ROOT):
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_outputs_are_deterministic_and_match_reports(
    analysis: dict[str, object],
) -> None:
    assert (BATCH_ROOT / "adjudication_gate_shadow.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "adjudication_gate_shadow.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_shadow_runner_has_no_provider_dependency() -> None:
    runner = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "run_batch_05_adjudication_gate_shadow.py"
    ).read_text(encoding="utf-8")
    import_lines = [
        line for line in runner.splitlines()
        if line.startswith(("import ", "from "))
    ]
    assert not any(
        value in line.casefold()
        for line in import_lines
        for value in ("provider", "openai", "anthropic")
    )


def test_shadow_never_reads_human_risk_annotations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "human_risk_annotations.json":
            raise AssertionError("risk annotations must not be read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    assert analyze_shadow_gate()["case_count"] == 10


def test_shadow_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert analyze_shadow_gate()["case_count"] == 10
