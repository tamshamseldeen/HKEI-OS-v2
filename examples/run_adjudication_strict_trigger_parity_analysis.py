"""Audit parity between the HKEI-111 strict candidate and the current gate."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_adjudication_unresolved_evidence_trigger_analysis import (
    BATCHES,
    BENCHMARK_ROOT,
    STRICT_NAME,
    _expected_topics,
    candidate_signals,
    parse_batch_01_source,
    parse_source,
    read_manifest,
)
from examples.run_batch_04_editorial_validation import _source_fields
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.topic.topic import Topic
from src.topic.topic_confidence import TopicConfidence
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


OUTPUT_JSON = BENCHMARK_ROOT / "adjudication_strict_trigger_parity_analysis.json"
OUTPUT_MD = BENCHMARK_ROOT / "adjudication_strict_trigger_parity_analysis.md"
AUDIT_CASES = {("batch_02", "014"), ("batch_02", "019"),
               ("batch_05", "049"), ("batch_05", "050")}


LOGIC_DIFFERENCES = (
    ("no primary semantic domain", "required", "required", True,
     "Both test an empty primary_domain_candidates collection."),
    ("contextual evidence exists", "required", "required", True,
     "Both test whether contextual items are present."),
    ("no semantic relationships", "required", "required", True,
     "Both require an empty relationships collection."),
    ("topic already requires adjudication", "must be false", "must be false", True,
     "Both use the same pre-strict topic-required baseline."),
    ("LOW confidence requirement", "any classifier LOW", "topic or format LOW", False,
     "The diagnostic also considers reader-intent LOW; it does not affect audited cases."),
    ("deterministic sufficiency", "predicted TOPIC_* support exists", "topic and format are each sufficient", False,
     "Production couples topic sufficiency to format confidence."),
    ("topic confidence handling", "not part of sufficiency", "HIGH non-GENERAL topic required", False,
     "Production defines a separate confidence-based topic sufficiency predicate."),
    ("format confidence handling", "only contributes to any LOW", "HIGH required for combined sufficiency", False,
     "LOW format confidence defeats production sufficiency even with deterministic topic support."),
    ("unresolved hint handling", "not part of sufficiency", "topic and format hints defeat sufficiency", False,
     "Production added hint-aware sufficiency conditions."),
    ("semantic conflict handling", "not part of sufficiency", "conflict defeats topic or format sufficiency", False,
     "Production added conflict-aware sufficiency conditions."),
    ("method-subject ambiguity handling", "not part of sufficiency", "ambiguity defeats topic sufficiency", False,
     "Production added ambiguity-aware topic sufficiency."),
    ("evaluation ordering", "candidate evaluated after pre-strict decision", "strict evaluated after existing-topic predicate", True,
     "Both evaluate strict logic only after the same pre-strict topic decision."),
)


def _production_sufficiency(result: Any, gate: Any) -> bool:
    contextual_supports = tuple(
        support
        for item in result.contextual_evidence.all_items
        for support in item.supports
    )
    semantic = result.semantic_evidence
    topic = result.topic_classification
    editorial_format = result.format_classification
    semantic_domain_conflict = gate._has_semantic_domain_conflict(semantic)
    method_subject_ambiguity = gate._has_method_subject_ambiguity(
        contextual_supports=contextual_supports,
        semantic_evidence=semantic,
    )
    unresolved_topic_hint = any(
        signal in contextual_supports
        for signal in (
            "ADJUDICATION_EVENT_PUBLIC_SAFETY",
            "ADJUDICATION_INSTITUTIONAL_POLICY_CONFLICT",
        )
    )
    unresolved_format_hint = any(
        signal in contextual_supports
        for signal in (
            "ADJUDICATION_ANALYTICAL_CONSTRAINT",
            "ADJUDICATION_EXPLANATORY_TRANSFORMATION",
            "ADJUDICATION_INSTITUTIONAL_POLICY_CONFLICT",
        )
    )
    format_conflict = gate._has_format_conflict(semantic)
    topic_sufficient = (
        topic.topic is not Topic.GENERAL
        and topic.confidence is TopicConfidence.HIGH
        and not semantic_domain_conflict
        and not method_subject_ambiguity
        and not unresolved_topic_hint
    )
    format_sufficient = (
        editorial_format.confidence is EditorialFormatConfidence.HIGH
        and not unresolved_format_hint
        and not format_conflict
    )
    return topic_sufficient and format_sufficient


def _metrics(cases: list[dict[str, Any]], trigger_key: str) -> dict[str, int]:
    triggered = [case for case in cases if case[trigger_key]]
    incremental = [case for case in triggered if not case["existing_topic_required_before_strict"]]
    return {
        "cases_triggered": len(triggered),
        "incremental_topic_TP": sum(not case["topic_match"] for case in incremental),
        "incremental_topic_FP": sum(case["topic_match"] for case in incremental),
    }


def analyze_strict_trigger_parity(
    *,
    benchmark_root: Path = BENCHMARK_ROOT,
    workflow: Any | None = None,
    gate: Any | None = None,
) -> dict[str, Any]:
    """Evaluate both strict predicates on identical outputs and baseline state."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    all_cases: list[dict[str, Any]] = []
    audited_cases: list[dict[str, Any]] = []

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
            production_trigger = STRICT_NAME in decision.trigger_signals
            pre_strict_required = decision.topic_required and not production_trigger
            _, diagnostic_trigger = candidate_signals(
                topic_classification=result.topic_classification,
                format_classification=result.format_classification,
                intent_classification=result.reader_intent_classification,
                contextual_evidence=result.contextual_evidence,
                semantic_evidence=result.semantic_evidence,
                current_gate_topic_required=pre_strict_required,
            )
            contextual_supports = {
                support
                for item in result.contextual_evidence.all_items
                for support in item.supports
            }
            predicted_support = f"TOPIC_{result.topic_classification.topic.value}"
            record = {
                "batch": batch,
                "id": source.case_id,
                "expected_topic": expected_topics[source.case_id],
                "current_predicted_topic": result.topic_classification.topic.value,
                "topic_match": (
                    result.topic_classification.topic.value
                    == expected_topics[source.case_id]
                ),
                "topic_confidence": result.topic_classification.confidence.value,
                "format_confidence": result.format_classification.confidence.value,
                "primary_domain_candidates": list(
                    result.semantic_evidence.primary_domain_candidates
                ),
                "semantic_relationship_count": len(
                    result.semantic_evidence.relationships
                ),
                "contextual_item_count": len(result.contextual_evidence.all_items),
                "existing_topic_required_before_strict": pre_strict_required,
                "diagnostic_strict_candidate": diagnostic_trigger,
                "production_strict_trigger": production_trigger,
                "diagnostic_deterministic_sufficiency": (
                    predicted_support in contextual_supports
                ),
                "production_deterministic_sufficiency": _production_sufficiency(
                    result, active_gate
                ),
                "current_gate_scope": decision.scope.value,
                "trigger_signals": list(decision.trigger_signals),
            }
            all_cases.append(record)
            if (batch, source.case_id) in AUDIT_CASES:
                audited_cases.append(record)

    diagnostic_metrics = _metrics(all_cases, "diagnostic_strict_candidate")
    production_metrics = _metrics(all_cases, "production_strict_trigger")
    cross_batch_fps = [
        f'{case["batch"]}/{case["id"]}'
        for case in all_cases
        if case["production_strict_trigger"]
        and not case["existing_topic_required_before_strict"]
        and case["topic_match"]
    ]
    return {
        "cases_analyzed": len(all_cases),
        "diagnostic_candidate_metrics": diagnostic_metrics,
        "production_trigger_metrics": production_metrics,
        "logic_differences": [
            {
                "condition": condition,
                "hkei_111_diagnostic_candidate": diagnostic,
                "production_gate": production,
                "equivalent": equivalent,
                "observed_difference": difference,
            }
            for condition, diagnostic, production, equivalent, difference
            in LOGIC_DIFFERENCES
        ],
        "cross_batch_false_positive_cases": cross_batch_fps,
        "primary_discrepancy_cause": "DETERMINISTIC_SUFFICIENCY_DEFINITION_DRIFT",
        "primary_conclusion": "PRODUCTION_TRIGGER_NOT_EQUIVALENT_TO_VALIDATED_CANDIDATE",
        "recommended_action": "ALIGN_PRODUCTION_TO_VALIDATED_STRICT_LOGIC",
        "gate_freeze_safe": False,
        "baseline_consistency": (
            "Both predicates use current pipeline outputs and the same current "
            "existing-topic-required state before strict-trigger application."
        ),
        "temporal_change_audit": {
            "hkei_111_commit": "583bbc4",
            "hkei_112_commit": "435f5b0",
            "hkei_113_commit": "bb1d98c",
            "upstream_evidence_changed_after_hkei_111": False,
            "gate_changed_after_hkei_111": True,
            "tests_changed_after_hkei_111": True,
            "benchmark_runner_changed_after_hkei_111": False,
            "finding": (
                "HKEI-112 implemented a different deterministic-sufficiency "
                "definition; HKEI-113 refreshed outputs only."
            ),
        },
        "cases": sorted(audited_cases, key=lambda item: (item["batch"], item["id"])),
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def render_markdown(analysis: dict[str, Any]) -> str:
    diagnostic = analysis["diagnostic_candidate_metrics"]
    production = analysis["production_trigger_metrics"]
    lines = [
        "# Strict Trigger Diagnostic / Production Parity Audit", "",
        "## Historical Result", "", "HKEI-111:", "",
        "Incremental TP:", "1", "", "Incremental FP:", "0", "",
        "## Production Result", "", "HKEI-113:", "",
        "Incremental TP:", str(production["incremental_topic_TP"]), "",
        "Incremental FP:", str(production["incremental_topic_FP"]), "",
        "False Positives:", "",
        *(analysis["cross_batch_false_positive_cases"] or ["None"]), "",
        "## Logic Comparison", "",
        "| Condition | HKEI-111 Diagnostic Candidate | Production Gate | Equivalent | Observed Difference |",
        "|---|---|---|---|---|",
    ]
    for row in analysis["logic_differences"]:
        lines.append(
            f'| {row["condition"]} | {row["hkei_111_diagnostic_candidate"]} | '
            f'{row["production_gate"]} | {_yes_no(row["equivalent"])} | '
            f'{row["observed_difference"]} |'
        )
    by_id = {case["id"]: case for case in analysis["cases"]}
    for case_id, heading in (("014", "Case 014"), ("019", "Case 019"),
                             ("050", "Case 050"), ("049", "Control 049")):
        case = by_id[case_id]
        lines.extend([
            "", f"## {heading}", "",
            "| Field | Value |", "|---|---|",
        ])
        for key, value in case.items():
            display = ", ".join(map(str, value)) if isinstance(value, list) else value
            lines.append(f"| {key} | {display} |")
    lines.extend([
        "", "## Root Cause", "",
        analysis["primary_conclusion"], "",
        analysis["primary_discrepancy_cause"], "",
        "The diagnostic treats matching contextual TOPIC_* support as deterministic "
        "sufficiency. Production instead requires both topic and format sufficiency; "
        "LOW format confidence therefore fires the trigger for 014 and 019.", "",
        "Production can use the validated diagnostic sufficiency test to avoid 014 "
        "and 019 while retaining 050, which lacks TOPIC_EDUCATION contextual support.", "",
        "## Recommended Action", "", analysis["recommended_action"], "",
        "## Gate Freeze Decision", "", "NOT SAFE", "",
        "Diagnostic and production strict-trigger semantics are not aligned, and the "
        "two cross-batch false positives have not been intentionally accepted or eliminated.", "",
        "## Current Same-Baseline Metrics", "",
        f'Diagnostic cases triggered: {diagnostic["cases_triggered"]}', "",
        f'Diagnostic incremental TP: {diagnostic["incremental_topic_TP"]}', "",
        f'Diagnostic incremental FP: {diagnostic["incremental_topic_FP"]}', "",
        f'Production cases triggered: {production["cases_triggered"]}', "",
        f'Production incremental TP: {production["incremental_topic_TP"]}', "",
        f'Production incremental FP: {production["incremental_topic_FP"]}', "",
    ])
    return "\n".join(lines)


def main() -> None:
    analysis = analyze_strict_trigger_parity()
    OUTPUT_JSON.write_text(render_json(analysis), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(analysis), encoding="utf-8")
    print("=== STRICT TRIGGER DIAGNOSTIC / PRODUCTION PARITY AUDIT ===")
    print(f'Cases analyzed: {analysis["cases_analyzed"]}')
    print(f'Diagnostic: {analysis["diagnostic_candidate_metrics"]}')
    print(f'Production: {analysis["production_trigger_metrics"]}')
    print(f'Conclusion: {analysis["primary_conclusion"]}')
    print(f'Recommendation: {analysis["recommended_action"]}')
    print("Gate freeze safe: NO")


if __name__ == "__main__":
    main()
