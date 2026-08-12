"""Evaluate sufficiency-informed Topic and Format consumption in shadow only."""

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_adjudication_unresolved_evidence_trigger_analysis import (  # noqa: E402
    _expected_topics, parse_batch_01_source, parse_source, read_manifest,
)
from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_benchmark_batch_02_validation import read_expectations  # noqa: E402
from examples.run_semantic_candidate_assessment_shadow import _assessment_record, _candidate_groups  # noqa: E402
from src.adjudication.deterministic_semantic_adjudication_gate import DeterministicSemanticAdjudicationGate  # noqa: E402
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import ExperimentalSemanticEditorialAnalysisWorkflow  # noqa: E402


BENCHMARK_ROOT = PROJECT_ROOT / "benchmark"
BATCHES = ("batch_01", "batch_02", "batch_03", "batch_05", "batch_06")
BATCH_STATUSES = {
    "batch_01": "HISTORICAL_REGRESSION_CORPUS",
    "batch_02": "HISTORICAL_REGRESSION_CORPUS",
    "batch_03": "HISTORICAL_REGRESSION_CORPUS",
    "batch_05": "SEMANTIC_ADJUDICATION_DEVELOPMENT_CORPUS",
    "batch_06": "DIAGNOSTIC_DEVELOPMENT_SET",
}
OUTPUT_JSON = BENCHMARK_ROOT / "semantic_sufficiency_shadow_consumption.json"
OUTPUT_MD = BENCHMARK_ROOT / "semantic_sufficiency_shadow_consumption.md"


def shadow_decision(
    *, dimension: str, current_candidate: str,
    assessments: list[dict[str, Any]], candidate_group: str,
) -> dict[str, Any]:
    relevant = [item for item in assessments if item["candidate_group"] == candidate_group]
    current = next((item for item in relevant if item["candidate"] == current_candidate), None)
    sufficient = sorted(item["candidate"] for item in relevant if item["sufficiency"] == "SUFFICIENT")
    if not relevant:
        shadow, reason = current_candidate, "NO_ASSESSMENTS"
    elif len(sufficient) > 1:
        shadow, reason = current_candidate, "MULTIPLE_SUFFICIENT_CONFLICT"
    elif sufficient == [current_candidate]:
        shadow, reason = current_candidate, "CURRENT_ALREADY_SUFFICIENT"
    elif len(sufficient) == 1:
        shadow, reason = sufficient[0], "SUFFICIENT_ALTERNATIVE_OVERRIDE"
    elif any(item["candidate"] != current_candidate for item in relevant):
        shadow, reason = current_candidate, "ALTERNATIVE_NOT_STRONG_ENOUGH"
    else:
        shadow, reason = current_candidate, "NO_SUFFICIENT_OVERRIDE"
    selected = next((item for item in relevant if item["candidate"] == shadow), None)
    return {
        "dimension": dimension, "current_candidate": current_candidate,
        "shadow_candidate": shadow, "changed": shadow != current_candidate,
        "decision_reason": reason, "current_assessment": current,
        "selected_assessment": selected,
        "competing_sufficient_candidates": sufficient,
    }


def _expectations(batch_root: Path) -> dict[str, dict[str, str | None]]:
    topics = _expected_topics(batch_root)
    path = batch_root / "expected.json"
    if not path.exists():
        return {case_id: {"topic": topic, "format": None} for case_id, topic in topics.items()}
    return {
        item["id"]: {"topic": item["topic"], "format": item["editorial_format"]}
        for item in read_expectations(batch_root)
    }


def _dimension_metrics(cases: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    values = [case for case in cases if case[f"expected_{dimension}"] is not None]
    current_correct = sum(case[f"current_{dimension}"] == case[f"expected_{dimension}"] for case in values)
    shadow_correct = sum(case[f"shadow_{dimension}"] == case[f"expected_{dimension}"] for case in values)
    overrides = [case for case in values if case[f"shadow_{dimension}"] != case[f"current_{dimension}"]]
    improvements = [case for case in overrides if case[f"current_{dimension}"] != case[f"expected_{dimension}"] and case[f"shadow_{dimension}"] == case[f"expected_{dimension}"]]
    regressions = [case for case in overrides if case[f"current_{dimension}"] == case[f"expected_{dimension}"] and case[f"shadow_{dimension}"] != case[f"expected_{dimension}"]]
    wrong_to_wrong = [case for case in overrides if case[f"current_{dimension}"] != case[f"expected_{dimension}"] and case[f"shadow_{dimension}"] != case[f"expected_{dimension}"]]
    wrong_overrides = [case for case in overrides if case[f"shadow_{dimension}"] != case[f"expected_{dimension}"]]
    unchanged = [case for case in values if case not in overrides]
    return {
        "evaluable_cases": len(values),
        f"current_{dimension}_correct": current_correct,
        f"shadow_{dimension}_correct": shadow_correct,
        f"current_{dimension}_accuracy": current_correct / len(values) * 100 if values else None,
        f"shadow_{dimension}_accuracy": shadow_correct / len(values) * 100 if values else None,
        f"{dimension}_net_delta": shadow_correct - current_correct,
        f"{dimension}_improvements": len(improvements),
        f"{dimension}_regressions": len(regressions),
        f"{dimension}_unchanged_correct": sum(case[f"current_{dimension}"] == case[f"expected_{dimension}"] for case in unchanged),
        f"{dimension}_unchanged_wrong": sum(case[f"current_{dimension}"] != case[f"expected_{dimension}"] for case in unchanged),
        f"{dimension}_shadow_overrides": len(overrides),
        f"{dimension}_correct_overrides": len(improvements),
        f"{dimension}_wrong_overrides": len(wrong_overrides),
        f"{dimension}_wrong_to_wrong_overrides": len(wrong_to_wrong),
        f"{dimension}_override_precision": len(improvements) / len(overrides) * 100 if overrides else None,
        "override_cases": [f"{case['batch']}:{case['id']}" for case in overrides],
        "improvement_cases": [f"{case['batch']}:{case['id']}" for case in improvements],
        "regression_cases": [f"{case['batch']}:{case['id']}" for case in regressions],
        "wrong_to_wrong_cases": [f"{case['batch']}:{case['id']}" for case in wrong_to_wrong],
    }


def analyze(
    *, workflow: Any | None = None, gate: Any | None = None,
    assessor: Any | None = None,
) -> dict[str, Any]:
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    active_assessor = assessor or DeterministicSemanticCandidateAssessor()
    cases: list[dict[str, Any]] = []
    for batch in BATCHES:
        root = BENCHMARK_ROOT / batch
        for manifest in read_manifest(root):
            source = parse_batch_01_source(root / manifest["source_file"]) if batch == "batch_01" else parse_source(root / manifest["source_file"])
            pipeline = active_workflow.process(**_source_fields(source))
            gate_decision = active_gate.evaluate(
                topic_classification=pipeline.topic_classification,
                format_classification=pipeline.format_classification,
                contextual_evidence=pipeline.contextual_evidence,
                semantic_evidence=pipeline.semantic_evidence,
            )
            groups = _candidate_groups(pipeline.semantic_evidence, pipeline.contextual_evidence)
            assessments = [
                _assessment_record(item, groups.get(item.candidate, "CANDIDATE_TYPE_NOT_EXPLICIT"))
                for item in active_assessor.assess(
                    semantic_evidence=pipeline.semantic_evidence,
                    contextual_evidence=pipeline.contextual_evidence,
                )
            ]
            topic = pipeline.topic_classification.topic.value
            format_ = pipeline.format_classification.editorial_format.value
            topic_shadow = shadow_decision(
                dimension="TOPIC", current_candidate=topic,
                assessments=assessments, candidate_group="TOPIC_LIKE",
            )
            format_shadow = shadow_decision(
                dimension="FORMAT", current_candidate=format_,
                assessments=assessments, candidate_group="FORMAT_LIKE",
            )
            cases.append({
                "batch": batch, "scientific_status": BATCH_STATUSES[batch],
                "id": source.case_id, "current_topic": topic,
                "shadow_topic": topic_shadow["shadow_candidate"],
                "topic_shadow_decision": topic_shadow,
                "current_format": format_, "shadow_format": format_shadow["shadow_candidate"],
                "format_shadow_decision": format_shadow,
                "reader_intent": pipeline.reader_intent_classification.reader_intent.value,
                "topic_confidence": pipeline.topic_classification.confidence.value,
                "format_confidence": pipeline.format_classification.confidence.value,
                "gate_scope": gate_decision.scope.value,
                "assessments": assessments,
            })

    # Expected labels are loaded only after current outputs, assessments, and
    # both shadow decisions have been frozen for every case.
    truth = {batch: _expectations(BENCHMARK_ROOT / batch) for batch in BATCHES}
    for case in cases:
        expected = truth[case["batch"]][case["id"]]
        case["expected_topic"] = expected["topic"]
        case["expected_format"] = expected["format"]

    topic_metrics = _dimension_metrics(cases, "topic")
    format_metrics = _dimension_metrics(cases, "format")
    batch_metrics = {}
    for batch in BATCHES:
        values = [case for case in cases if case["batch"] == batch]
        batch_metrics[batch] = {
            "scientific_status": BATCH_STATUSES[batch],
            "topic": _dimension_metrics(values, "topic"),
            "format": _dimension_metrics(values, "format"),
        }

    any_sufficient = [case for case in cases if any(item["sufficiency"] == "SUFFICIENT" for item in case["assessments"])]
    topic_sufficient = [case for case in cases if any(item["candidate_group"] == "TOPIC_LIKE" and item["sufficiency"] == "SUFFICIENT" for item in case["assessments"])]
    format_sufficient = [case for case in cases if any(item["candidate_group"] == "FORMAT_LIKE" and item["sufficiency"] == "SUFFICIENT" for item in case["assessments"])]
    opportunities = [case for case in cases if any(decision["decision_reason"] == "SUFFICIENT_ALTERNATIVE_OVERRIDE" for decision in (case["topic_shadow_decision"], case["format_shadow_decision"]))]
    actual_overrides = [case for case in cases if any(decision["changed"] for decision in (case["topic_shadow_decision"], case["format_shadow_decision"]))]
    prevented: dict[str, set[str]] = {
        "PARTIAL": set(), "INSUFFICIENT": set(), "CONFLICTED": set(),
        "MULTIPLE_SUFFICIENT_CONFLICT": set(),
    }
    for case in cases:
        case_key = f"{case['batch']}:{case['id']}"
        for group, current in (("TOPIC_LIKE", case["current_topic"]), ("FORMAT_LIKE", case["current_format"])):
            for item in case["assessments"]:
                if item["candidate_group"] == group and item["candidate"] != current and item["sufficiency"] in {"PARTIAL", "INSUFFICIENT", "CONFLICTED"}:
                    prevented[item["sufficiency"]].add(case_key)
        if any(decision["decision_reason"] == "MULTIPLE_SUFFICIENT_CONFLICT" for decision in (case["topic_shadow_decision"], case["format_shadow_decision"])):
            prevented["MULTIPLE_SUFFICIENT_CONFLICT"].add(case_key)

    regressions = topic_metrics["topic_regressions"] + format_metrics["format_regressions"]
    improvements = topic_metrics["topic_improvements"] + format_metrics["format_improvements"]
    overrides = topic_metrics["topic_shadow_overrides"] + format_metrics["format_shadow_overrides"]
    wrong_to_wrong = topic_metrics["topic_wrong_to_wrong_overrides"] + format_metrics["format_wrong_to_wrong_overrides"]
    all_correct = topic_metrics["topic_wrong_overrides"] == 0 and format_metrics["format_wrong_overrides"] == 0
    if regressions and improvements:
        quality = "MIXED"
    elif regressions:
        quality = "UNSAFE"
    elif improvements and all_correct:
        quality = "EXCELLENT"
    elif improvements:
        quality = "PROMISING"
    else:
        quality = "SAFE_BUT_LOW_UTILITY"
    recommendation = (
        "READY_FOR_PREREGISTERED_SHADOW_EVALUATION"
        if quality in {"EXCELLENT", "PROMISING"}
        else "KEEP_AS_DIAGNOSTIC_ONLY" if quality == "SAFE_BUT_LOW_UTILITY"
        else "REFINE_SHADOW_CONSUMPTION_POLICY" if quality == "MIXED"
        else "UNSAFE_FOR_CONSUMPTION"
    )
    return {
        "cases_evaluated": len(cases), "case_inventory": cases,
        "topic_metrics": topic_metrics, "format_metrics": format_metrics,
        "batch_metrics": batch_metrics,
        "sufficiency_utilization": {
            "cases_with_any_sufficient_assessment": len(any_sufficient),
            "cases_with_topic_sufficient": len(topic_sufficient),
            "cases_with_format_sufficient": len(format_sufficient),
            "cases_with_override_opportunity": len(opportunities),
            "cases_with_actual_shadow_override": len(actual_overrides),
        },
        "override_suppression": {
            "prevented_by_partial": len(prevented["PARTIAL"]),
            "prevented_by_insufficient": len(prevented["INSUFFICIENT"]),
            "prevented_by_conflicted": len(prevented["CONFLICTED"]),
            "prevented_by_multiple_sufficient_conflict": len(prevented["MULTIPLE_SUFFICIENT_CONFLICT"]),
        },
        "evaluation_classification": quality,
        "integration_recommendation": recommendation,
        "mutation_audit": {
            "actual_topic_mutated": False, "actual_format_mutated": False,
            "actual_reader_intent_mutated": False,
            "actual_confidence_mutated": False, "gate_mutated": False,
        },
        "batch_07_required": True, "provider_calls": 0,
    }


def render_markdown(result: dict[str, Any]) -> str:
    topic, format_ = result["topic_metrics"], result["format_metrics"]
    utilization = result["sufficiency_utilization"]
    suppression = result["override_suppression"]
    batch_rows = "\n".join(
        f"| {batch} | {values['scientific_status']} | {values['topic']['topic_net_delta']} | {values['format']['format_net_delta']} |"
        for batch, values in result["batch_metrics"].items()
    )
    return f"""# Semantic Sufficiency Shadow Consumption

Cases evaluated: {result['cases_evaluated']}

Evaluation: {result['evaluation_classification']}

Topic accuracy: {topic['current_topic_accuracy']} -> {topic['shadow_topic_accuracy']} (delta {topic['topic_net_delta']})

Format accuracy: {format_['current_format_accuracy']} -> {format_['shadow_format_accuracy']} (delta {format_['format_net_delta']})

Topic overrides: {topic['topic_shadow_overrides']} (correct {topic['topic_correct_overrides']}, wrong {topic['topic_wrong_overrides']}, wrong-to-wrong {topic['topic_wrong_to_wrong_overrides']}, regressions {topic['topic_regressions']})

Format overrides: {format_['format_shadow_overrides']} (correct {format_['format_correct_overrides']}, wrong {format_['format_wrong_overrides']}, wrong-to-wrong {format_['format_wrong_to_wrong_overrides']}, regressions {format_['format_regressions']})

Cases with any sufficient assessment: {utilization['cases_with_any_sufficient_assessment']}

Override opportunities / actual overrides: {utilization['cases_with_override_opportunity']} / {utilization['cases_with_actual_shadow_override']}

Prevented by partial / insufficient / conflicted / multiple sufficient: {suppression['prevented_by_partial']} / {suppression['prevented_by_insufficient']} / {suppression['prevented_by_conflicted']} / {suppression['prevented_by_multiple_sufficient_conflict']}

| Batch | Scientific status | Topic delta | Format delta |
| --- | --- | ---: | ---: |
{batch_rows}

Batch 06 results are diagnostic only and are not evidence of generalization.

Recommendation: {result['integration_recommendation']}

Batch 07 required: YES

Provider calls: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "case_inventory"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
