"""Evaluate the deterministic adjudication gate in Batch 05 shadow mode."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields
from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
CASE_IDS = tuple(f"{case_id:03d}" for case_id in range(41, 51))
TRIGGER_SIGNALS = (
    "TOPIC_LOW_CONFIDENCE",
    "TOPIC_GENERAL_FALLBACK",
    "NO_PRIMARY_SEMANTIC_DOMAIN",
    "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP",
    "METHOD_SUBJECT_AMBIGUITY",
    "SEMANTIC_DOMAIN_CONFLICT",
    "MULTIPLE_COMPETING_TOPIC_SIGNALS",
    "FORMAT_LOW_CONFIDENCE",
    "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK",
    "EXPLAINER_STRUCTURE_UNRESOLVED",
    "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED",
    "FORMAT_CONFLICT",
)


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _classification_metrics(
    cases: list[dict[str, Any]],
    dimension: str,
) -> dict[str, float | int]:
    required_key = f"{dimension}_required"
    should_key = f"{dimension}_should_adjudicate"
    true_positives = sum(
        case[should_key] and case[required_key] for case in cases
    )
    false_positives = sum(
        not case[should_key] and case[required_key] for case in cases
    )
    true_negatives = sum(
        not case[should_key] and not case[required_key] for case in cases
    )
    false_negatives = sum(
        case[should_key] and not case[required_key] for case in cases
    )
    return {
        f"{dimension}_true_positives": true_positives,
        f"{dimension}_false_positives": false_positives,
        f"{dimension}_true_negatives": true_negatives,
        f"{dimension}_false_negatives": false_negatives,
        f"{dimension}_precision": _percentage(
            true_positives, true_positives + false_positives
        ),
        f"{dimension}_recall": _percentage(
            true_positives, true_positives + false_negatives
        ),
        f"{dimension}_specificity": _percentage(
            true_negatives, true_negatives + false_positives
        ),
        f"{dimension}_accuracy": _percentage(
            true_positives + true_negatives, len(cases)
        ),
    }


def analyze_shadow_gate(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: ExperimentalSemanticEditorialAnalysisWorkflow | None = None,
    gate: DeterministicSemanticAdjudicationGate | None = None,
) -> dict[str, Any]:
    """Run the normal workflow and observe gate decisions without resolution."""
    validation = json.loads(
        (batch_root / "editorial_validation.json").read_text(encoding="utf-8")
    )
    frozen_by_id = {case["id"]: case for case in validation["cases"]}
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    cases: list[dict[str, Any]] = []

    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        workflow_result = active_workflow.process(**_source_fields(source))
        decision = active_gate.evaluate(
            topic_classification=workflow_result.topic_classification,
            format_classification=workflow_result.format_classification,
            contextual_evidence=workflow_result.contextual_evidence,
            semantic_evidence=workflow_result.semantic_evidence,
        )
        frozen = frozen_by_id[source.case_id]
        assert workflow_result.topic_classification.topic.value == frozen[
            "predicted_topic"
        ]
        assert (
            workflow_result.format_classification.editorial_format.value
            == frozen["predicted_format"]
        )
        assert (
            workflow_result.reader_intent_classification.reader_intent.value
            == frozen["predicted_reader_intent"]
        )
        topic_should = not frozen["topic_match"]
        format_should = not frozen["format_match"]
        cases.append(
            {
                "id": source.case_id,
                "topic_match": frozen["topic_match"],
                "format_match": frozen["format_match"],
                "intent_match": frozen["reader_intent_match"],
                "full_match": frozen["full_match"],
                "gate_scope": decision.scope.value,
                "topic_required": decision.topic_required,
                "format_required": decision.format_required,
                "trigger_signals": list(decision.trigger_signals),
                "reason_codes": list(decision.reason_codes),
                "warnings": list(decision.warnings),
                "topic_should_adjudicate": topic_should,
                "format_should_adjudicate": format_should,
                "topic_gate_correct": decision.topic_required is topic_should,
                "format_gate_correct": decision.format_required is format_should,
                "topic_false_positive": (
                    decision.topic_required and not topic_should
                ),
                "topic_false_negative": (
                    topic_should and not decision.topic_required
                ),
                "format_false_positive": (
                    decision.format_required and not format_should
                ),
                "format_false_negative": (
                    format_should and not decision.format_required
                ),
            }
        )

    topic_metrics = _classification_metrics(cases, "topic")
    format_metrics = _classification_metrics(cases, "format")
    provider_calls = [
        case for case in cases
        if case["gate_scope"] != AdjudicationScope.NOT_REQUIRED.value
    ]
    combined_should = {
        case["id"]: (
            case["topic_should_adjudicate"]
            or case["format_should_adjudicate"]
        )
        for case in cases
    }
    scope_counts = Counter(case["gate_scope"] for case in cases)
    trigger_distribution = {
        trigger: {
            "cases_triggered": sum(
                trigger in case["trigger_signals"] for case in cases
            ),
            "topic_mismatch_cases": sum(
                trigger in case["trigger_signals"] and not case["topic_match"]
                for case in cases
            ),
            "format_mismatch_cases": sum(
                trigger in case["trigger_signals"] and not case["format_match"]
                for case in cases
            ),
            "fully_matched_cases": sum(
                trigger in case["trigger_signals"] and case["full_match"]
                for case in cases
            ),
        }
        for trigger in TRIGGER_SIGNALS
    }
    return {
        "batch": "batch_05",
        "case_count": len(cases),
        **topic_metrics,
        **format_metrics,
        "provider_call_cases": len(provider_calls),
        "provider_call_rate": _percentage(len(provider_calls), len(cases)),
        "correctly_avoided_call_cases": sum(
            not combined_should[case["id"]]
            and case["gate_scope"] == AdjudicationScope.NOT_REQUIRED.value
            for case in cases
        ),
        "unnecessary_provider_call_cases": sum(
            not combined_should[case["id"]]
            and case["gate_scope"] != AdjudicationScope.NOT_REQUIRED.value
            for case in cases
        ),
        "missed_adjudication_cases": sum(
            combined_should[case["id"]]
            and case["gate_scope"] == AdjudicationScope.NOT_REQUIRED.value
            for case in cases
        ),
        "topic_captured_cases": [
            case["id"]
            for case in cases
            if case["topic_should_adjudicate"] and case["topic_required"]
        ],
        "format_captured_cases": [
            case["id"]
            for case in cases
            if case["format_should_adjudicate"] and case["format_required"]
        ],
        "scope_distribution": {
            scope.value: scope_counts.get(scope.value, 0)
            for scope in AdjudicationScope
        },
        "trigger_distribution": trigger_distribution,
        "cases": cases,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    """Return the preregistered shadow diagnostic status."""
    if (
        analysis["topic_recall"] == 100.0
        and analysis["topic_false_positives"] == 0
        and analysis["format_recall"] == 100.0
        and analysis["format_false_positives"] == 0
    ):
        return "EXCELLENT"
    if analysis["topic_recall"] >= 80.0 and analysis["format_recall"] >= 75.0:
        return "PASSED"
    return "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _ids(cases: list[dict[str, Any]], key: str) -> str:
    values = [case["id"] for case in cases if case[key]]
    return ", ".join(values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render deterministic gate metrics, cases, and trigger distribution."""
    lines = [
        "# Batch 05 Shadow Adjudication Gate Diagnostic", "",
        "## Summary", "", "Cases:", str(analysis["case_count"]), "",
        "Provider Call Cases:", str(analysis["provider_call_cases"]), "",
        "Provider Call Rate:", f'{analysis["provider_call_rate"]:.2f}%', "",
    ]
    for title, prefix in (("Topic Gate", "topic"), ("Format Gate", "format")):
        lines.extend(
            (
                f"## {title}", "",
                "TP:", str(analysis[f"{prefix}_true_positives"]), "",
                "FP:", str(analysis[f"{prefix}_false_positives"]), "",
                "TN:", str(analysis[f"{prefix}_true_negatives"]), "",
                "FN:", str(analysis[f"{prefix}_false_negatives"]), "",
                "Precision:", f'{analysis[f"{prefix}_precision"]:.2f}%', "",
                "Recall:", f'{analysis[f"{prefix}_recall"]:.2f}%', "",
                "Specificity:", f'{analysis[f"{prefix}_specificity"]:.2f}%', "",
                "Accuracy:", f'{analysis[f"{prefix}_accuracy"]:.2f}%', "",
            )
        )
    lines.extend(("## Scope Distribution", ""))
    for scope, count in analysis["scope_distribution"].items():
        lines.extend((f"{scope}:", str(count), ""))
    lines.extend(
        (
            "## Case Table", "",
            "| ID | Topic Match | Format Match | Gate Scope | Topic Required | Format Required | Triggers | Topic Gate Correct | Format Gate Correct |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        )
    )
    for case in analysis["cases"]:
        lines.append(
            "| " + " | ".join(
                (
                    case["id"], "YES" if case["topic_match"] else "NO",
                    "YES" if case["format_match"] else "NO", case["gate_scope"],
                    "YES" if case["topic_required"] else "NO",
                    "YES" if case["format_required"] else "NO",
                    ", ".join(case["trigger_signals"]) or "None",
                    "YES" if case["topic_gate_correct"] else "NO",
                    "YES" if case["format_gate_correct"] else "NO",
                )
            ) + " |"
        )
    lines.extend(
        (
            "", "## Missed Topic Adjudications", "",
            _ids(analysis["cases"], "topic_false_negative"), "",
            "## Unnecessary Topic Adjudications", "",
            _ids(analysis["cases"], "topic_false_positive"), "",
            "## Missed Format Adjudications", "",
            _ids(analysis["cases"], "format_false_negative"), "",
            "## Unnecessary Format Adjudications", "",
            _ids(analysis["cases"], "format_false_positive"), "",
            "## Trigger Distribution", "",
            "| Trigger | Cases | Topic Mismatches | Format Mismatches | Fully Matched |",
            "| --- | ---: | ---: | ---: | ---: |",
        )
    )
    for trigger, metrics in analysis["trigger_distribution"].items():
        lines.append(
            f'| {trigger} | {metrics["cases_triggered"]} | '
            f'{metrics["topic_mismatch_cases"]} | '
            f'{metrics["format_mismatch_cases"]} | '
            f'{metrics["fully_matched_cases"]} |'
        )
    control = next(case for case in analysis["cases"] if case["id"] == "049")
    lines.extend(
        (
            "", "## Control Case 049", "",
            "Scope:", control["gate_scope"], "",
            "Topic Required:", str(control["topic_required"]), "",
            "Format Required:", str(control["format_required"]), "",
            "Trigger Signals:", ", ".join(control["trigger_signals"]) or "None", "",
        )
    )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    lines = [
        "=== BATCH 05 SHADOW ADJUDICATION GATE ===", "",
        "Cases:", str(analysis["case_count"]), "",
        "Provider Calls:", f'{analysis["provider_call_cases"]}/10', "",
        "Topic Gate:",
        f'TP={analysis["topic_true_positives"]} FP={analysis["topic_false_positives"]} TN={analysis["topic_true_negatives"]} FN={analysis["topic_false_negatives"]}',
        f'Precision={analysis["topic_precision"]:.2f}%',
        f'Recall={analysis["topic_recall"]:.2f}%', "",
        "Format Gate:",
        f'TP={analysis["format_true_positives"]} FP={analysis["format_false_positives"]} TN={analysis["format_true_negatives"]} FN={analysis["format_false_negatives"]}',
        f'Precision={analysis["format_precision"]:.2f}%',
        f'Recall={analysis["format_recall"]:.2f}%', "",
    ]
    lines.extend(
        f'{case["id"]} | scope={case["gate_scope"]} '
        f'| topic_required={"YES" if case["topic_required"] else "NO"} '
        f'| format_required={"YES" if case["format_required"] else "NO"}'
        for case in analysis["cases"]
    )
    return "\n".join(lines)


def main() -> int:
    analysis = analyze_shadow_gate()
    (BATCH_ROOT / "adjudication_gate_shadow.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "adjudication_gate_shadow.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
