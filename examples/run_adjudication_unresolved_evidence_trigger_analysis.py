"""Evaluate generic unresolved-evidence triggers across benchmark batches."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields
from examples.run_benchmark_batch_01_analysis import (
    parse_source as parse_batch_01_source,
)
from examples.run_benchmark_batch_02_validation import (
    parse_source,
    read_expectations,
    read_manifest,
)
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.topic.topic_confidence import TopicConfidence
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BENCHMARK_ROOT = PROJECT_ROOT / "benchmark"
BATCHES = tuple(f"batch_{number:02d}" for number in range(1, 6))
BASE_NAME = "UNRESOLVED_EVIDENCE_STACK"
STRICT_NAME = "UNRESOLVED_EVIDENCE_STACK_STRICT"


def _expected_topics(batch_root: Path) -> dict[str, str]:
    expected_path = batch_root / "expected.json"
    if expected_path.exists():
        return {item["id"]: item["topic"] for item in read_expectations(batch_root)}
    return {
        item["id"]: item["benchmark_category"].upper()
        for item in read_manifest(batch_root)
    }


def candidate_signals(
    *,
    topic_classification: Any,
    format_classification: Any,
    intent_classification: Any,
    contextual_evidence: Any,
    semantic_evidence: Any,
    current_gate_topic_required: bool,
) -> tuple[bool, bool]:
    """Derive both candidates solely from existing structured outputs."""
    no_primary_domain = not semantic_evidence.primary_domain_candidates
    context_exists = bool(contextual_evidence.all_items)
    no_relationships = not semantic_evidence.relationships
    topic_not_confirmed_high = (
        topic_classification.confidence is not TopicConfidence.HIGH
    )
    another_classifier_low = (
        format_classification.confidence is EditorialFormatConfidence.LOW
        or intent_classification.confidence is ReaderIntentConfidence.LOW
    )
    base = (
        no_primary_domain
        and context_exists
        and no_relationships
        and (topic_not_confirmed_high or another_classifier_low)
    )

    all_contextual_supports = {
        support
        for item in contextual_evidence.all_items
        for support in item.supports
    }
    predicted_topic_support = f"TOPIC_{topic_classification.topic.value}"
    structured_sufficiency = predicted_topic_support in all_contextual_supports
    any_classification_low = (
        topic_classification.confidence is TopicConfidence.LOW
        or format_classification.confidence is EditorialFormatConfidence.LOW
        or intent_classification.confidence is ReaderIntentConfidence.LOW
    )
    strict = (
        no_primary_domain
        and context_exists
        and no_relationships
        and not current_gate_topic_required
        and any_classification_low
        and not structured_sufficiency
    )
    return base, strict


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _candidate_metrics(
    cases: list[dict[str, Any]],
    *,
    key: str,
    name: str,
) -> dict[str, Any]:
    true_positives = sum(case[key] and not case["topic_match"] for case in cases)
    false_positives = sum(case[key] and case["topic_match"] for case in cases)
    true_negatives = sum(not case[key] and case["topic_match"] for case in cases)
    false_negatives = sum(not case[key] and not case["topic_match"] for case in cases)
    incremental_tp = sum(
        case[key]
        and not case["topic_match"]
        and not case["current_gate_topic_required"]
        for case in cases
    )
    incremental_fp_cases = [
        case for case in cases
        if case[key]
        and case["topic_match"]
        and not case["current_gate_topic_required"]
    ]
    captures_050 = any(
        case["batch"] == "batch_05" and case["id"] == "050" and case[key]
        for case in cases
    )
    triggers_049 = any(
        case["batch"] == "batch_05" and case["id"] == "049" and case[key]
        for case in cases
    )
    incremental_fp = len(incremental_fp_cases)
    quality = (
        "EXCELLENT" if captures_050 and incremental_fp == 0
        else "PROMISING" if captures_050 and incremental_fp <= 1
        else "POOR"
    )
    by_batch = Counter(case["batch"] for case in incremental_fp_cases)
    return {
        "name": name,
        "cases_triggered": sum(case[key] for case in cases),
        "topic_mismatches_triggered": true_positives,
        "topic_matches_triggered": false_positives,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "precision": _percentage(true_positives, true_positives + false_positives),
        "recall": _percentage(true_positives, true_positives + false_negatives),
        "specificity": _percentage(true_negatives, true_negatives + false_positives),
        "accuracy": _percentage(true_positives + true_negatives, len(cases)),
        "incremental_true_positives": incremental_tp,
        "incremental_false_positives": incremental_fp,
        "captures_case_050": captures_050,
        "triggers_control_049": triggers_049,
        "false_positives_by_batch": {
            batch: by_batch.get(batch, 0) for batch in BATCHES
        },
        "quality": quality,
    }


def analyze_unresolved_evidence_triggers(
    *,
    benchmark_root: Path = BENCHMARK_ROOT,
    workflow: ExperimentalSemanticEditorialAnalysisWorkflow | None = None,
    gate: DeterministicSemanticAdjudicationGate | None = None,
) -> dict[str, Any]:
    """Reconstruct current outputs and evaluate both counterfactuals."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    cases: list[dict[str, Any]] = []
    for batch in BATCHES:
        batch_root = benchmark_root / batch
        expected_topics = _expected_topics(batch_root)
        for manifest_case in read_manifest(batch_root):
            source_path = batch_root / manifest_case["source_file"]
            source = (
                parse_batch_01_source(source_path)
                if batch == "batch_01"
                else parse_source(source_path)
            )
            result = active_workflow.process(**_source_fields(source))
            decision = active_gate.evaluate(
                topic_classification=result.topic_classification,
                format_classification=result.format_classification,
                contextual_evidence=result.contextual_evidence,
                semantic_evidence=result.semantic_evidence,
            )
            base, strict = candidate_signals(
                topic_classification=result.topic_classification,
                format_classification=result.format_classification,
                intent_classification=result.reader_intent_classification,
                contextual_evidence=result.contextual_evidence,
                semantic_evidence=result.semantic_evidence,
                current_gate_topic_required=decision.topic_required,
            )
            topic_match = (
                result.topic_classification.topic.value
                == expected_topics[source.case_id]
            )
            cases.append(
                {
                    "batch": batch,
                    "id": source.case_id,
                    "topic_match": topic_match,
                    "current_gate_topic_required": decision.topic_required,
                    "candidate_trigger": base,
                    "strict_candidate_trigger": strict,
                    "would_change_gate_decision": (
                        not decision.topic_required and (base or strict)
                    ),
                }
            )

    mismatches = sum(not case["topic_match"] for case in cases)
    current_captured = sum(
        not case["topic_match"] and case["current_gate_topic_required"]
        for case in cases
    )
    batch_05_cases = [case for case in cases if case["batch"] == "batch_05"]
    batch_05_mismatches = sum(not case["topic_match"] for case in batch_05_cases)
    batch_05_captured = sum(
        not case["topic_match"] and case["current_gate_topic_required"]
        for case in batch_05_cases
    )
    base_analysis = _candidate_metrics(cases, key="candidate_trigger", name=BASE_NAME)
    strict_analysis = _candidate_metrics(
        cases, key="strict_candidate_trigger", name=STRICT_NAME
    )
    quality_order = {"EXCELLENT": 2, "PROMISING": 1, "POOR": 0}
    if quality_order[strict_analysis["quality"]] >= 1:
        recommendation = "IMPLEMENT_STRICT_CANDIDATE"
    elif quality_order[base_analysis["quality"]] >= 1:
        recommendation = "IMPLEMENT_BASE_CANDIDATE"
    else:
        recommendation = "DO_NOT_IMPLEMENT"
    return {
        "case_count": len(cases),
        "current_gate_topic_recall": _percentage(current_captured, mismatches),
        "batch_05_current_gate_topic_recall": _percentage(
            batch_05_captured, batch_05_mismatches
        ),
        "candidate_analysis": {
            BASE_NAME: base_analysis,
            STRICT_NAME: strict_analysis,
        },
        "recommendation": recommendation,
        "cases": cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(a: dict[str, Any]) -> str:
    base = a["candidate_analysis"][BASE_NAME]
    strict = a["candidate_analysis"][STRICT_NAME]
    lines = [
        "# Generic Unresolved-Evidence Trigger Analysis", "",
        "## Current Gate", "", "Batch 05 Topic Recall:",
        f'{a["batch_05_current_gate_topic_recall"]:.2f}%', "",
        "Remaining Topic False Negative:", "050", "",
    ]
    for heading, result in (("Candidate 1", base), ("Candidate 2", strict)):
        lines.extend((f"## {heading}", "", result["name"], ""))
        for label, key in (
            ("Cases triggered", "cases_triggered"),
            ("True positives", "true_positives"),
            ("False positives", "false_positives"),
            ("True negatives", "true_negatives"),
            ("False negatives", "false_negatives"),
            ("Incremental true positives", "incremental_true_positives"),
            ("Incremental false positives", "incremental_false_positives"),
        ):
            lines.extend((f"{label}:", str(result[key]), ""))
        lines.extend(("Precision:", f'{result["precision"]:.2f}%', "", "Recall:", f'{result["recall"]:.2f}%', "", "Specificity:", f'{result["specificity"]:.2f}%', "", "Accuracy:", f'{result["accuracy"]:.2f}%', "", "Quality:", result["quality"], ""))
    lines.extend(("## Cross-Batch False Positives", "", "| Batch | Candidate | New False Positives |", "| --- | --- | ---: |"))
    for batch in BATCHES:
        for result in (base, strict):
            lines.append(f'| {batch} | {result["name"]} | {result["false_positives_by_batch"][batch]} |')
    lines.extend(("", "## Critical Controls", "", f'050 captured by base: {base["captures_case_050"]}', "", f'050 captured by strict: {strict["captures_case_050"]}', "", f'049 triggered by base: {base["triggers_control_049"]}', "", f'049 triggered by strict: {strict["triggers_control_049"]}', "", "## Recommendation", "", a["recommendation"], ""))
    return "\n".join(lines)


def main() -> int:
    analysis = analyze_unresolved_evidence_triggers()
    (BENCHMARK_ROOT / "adjudication_unresolved_evidence_trigger_analysis.json").write_text(render_json(analysis), encoding="utf-8")
    (BENCHMARK_ROOT / "adjudication_unresolved_evidence_trigger_analysis.md").write_text(render_markdown(analysis), encoding="utf-8")
    print(f'Cases analyzed: {analysis["case_count"]}')
    print(f'Recommendation: {analysis["recommendation"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
