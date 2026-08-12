"""Analyze Batch 07 Gate false negatives from persisted HKEI-178 output."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_07"
INPUT_JSON = BATCH_ROOT / "full_stack_shadow_evaluation.json"
OUTPUT_JSON = BATCH_ROOT / "gate_failure_analysis.json"
OUTPUT_MD = BATCH_ROOT / "gate_failure_analysis.md"
EXPECTED_JSON = BATCH_ROOT / "expected.json"
EXPECTED_SHA256 = "cafddc7533a80dc834abe96606ae770a458d462893086be16fcea95554c6c036"
FAILURE_CLASSES = {
    "SIGNAL_MISSING_UPSTREAM",
    "SIGNAL_PRESENT_GATE_IGNORED",
    "FALSE_CONFIDENCE",
    "FALSE_SEMANTIC_SUFFICIENCY",
    "UNRESOLVED_SIGNAL_NOT_PROPAGATED",
    "GATE_THRESHOLD_TOO_STRICT",
    "FORMAT_STRUCTURE_NOT_REPRESENTED",
    "OTHER",
}


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _confusion(cases: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    pairs = [(case[f"{dimension}_required"], not case[f"{dimension}_match_before"]) for case in cases]
    tp = sum(predicted and actual for predicted, actual in pairs)
    fp = sum(predicted and not actual for predicted, actual in pairs)
    tn = sum(not predicted and not actual for predicted, actual in pairs)
    fn = sum(not predicted and actual for predicted, actual in pairs)
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": _percentage(tp, tp + fp),
        "recall": _percentage(tp, tp + fn),
    }


def _relationships(assessments: list[dict[str, Any]], key: str) -> list[str]:
    return list(dict.fromkeys(value for item in assessments for value in item[key]))


def _contextual_present(case: dict[str, Any]) -> bool:
    relationships = _relationships(case["candidate_assessment_summary"], "supporting_relationship_types")
    return (
        "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP" in case["trigger_signals"]
        or any(value.startswith("CONTEXTUAL_") for value in relationships)
    )


def _semantic_relationships_present(case: dict[str, Any]) -> bool:
    relationships = (
        _relationships(case["candidate_assessment_summary"], "supporting_relationship_types")
        + _relationships(case["candidate_assessment_summary"], "suppressing_relationship_types")
    )
    return any(not value.startswith("CONTEXTUAL_") for value in relationships)


def _false_sufficient(case: dict[str, Any], dimension: str) -> list[dict[str, Any]]:
    group = "TOPIC_LIKE" if dimension == "topic" else "FORMAT_LIKE"
    expected = case[f"expected_{dimension}"]
    return [
        item for item in case["candidate_assessment_summary"]
        if item["candidate_group"] == group
        and item["sufficiency"] == "SUFFICIENT"
        and item["candidate"] != expected
    ]


def _format_failure_class(case: dict[str, Any]) -> str:
    if case["deterministic_format_confidence"] == "MEDIUM":
        return "FALSE_CONFIDENCE"
    if _false_sufficient(case, "format"):
        return "FALSE_SEMANTIC_SUFFICIENCY"
    warnings = {warning for item in case["candidate_assessment_summary"] for warning in item["warnings"]}
    if (
        "FORMAT_STRUCTURE_INCOMPLETE" in warnings
        or "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED" in case["trigger_signals"]
    ):
        return "UNRESOLVED_SIGNAL_NOT_PROPAGATED"
    return "FORMAT_STRUCTURE_NOT_REPRESENTED"


def _trace(case: dict[str, Any], dimension: str) -> dict[str, Any]:
    failure_class = (
        "SIGNAL_PRESENT_GATE_IGNORED"
        if dimension == "topic" and "TOPIC_LOW_CONFIDENCE" in case["trigger_signals"]
        else _format_failure_class(case) if dimension == "format"
        else "OTHER"
    )
    assessments = case["candidate_assessment_summary"]
    existing_unresolved = failure_class in {
        "SIGNAL_PRESENT_GATE_IGNORED", "FALSE_CONFIDENCE",
        "UNRESOLVED_SIGNAL_NOT_PROPAGATED", "GATE_THRESHOLD_TOO_STRICT",
    }
    existing_signal = None
    if failure_class == "SIGNAL_PRESENT_GATE_IGNORED":
        existing_signal = "TOPIC_LOW_CONFIDENCE"
    elif failure_class == "FALSE_CONFIDENCE":
        existing_signal = "FORMAT_MEDIUM_CONFIDENCE"
    elif failure_class == "UNRESOLVED_SIGNAL_NOT_PROPAGATED":
        existing_signal = "FORMAT_STRUCTURE_INCOMPLETE / CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED"
    return {
        "id": case["id"],
        "dimension": dimension.upper(),
        "expected_label": case[f"expected_{dimension}"],
        "deterministic_label": case[f"deterministic_{dimension}"],
        "classifier_confidence": case[f"deterministic_{dimension}_confidence"],
        "contextual_evidence_present": _contextual_present(case),
        "semantic_relationships_present": _semantic_relationships_present(case),
        "candidate_assessments": assessments,
        "semantic_sufficiency": list(dict.fromkeys(item["sufficiency"] for item in assessments)) or ["MISSING"],
        "semantic_support": _relationships(assessments, "supporting_relationship_types"),
        "semantic_suppression": _relationships(assessments, "suppressing_relationship_types"),
        "gate_scope": case["gate_scope"],
        "topic_required": case["topic_required"],
        "format_required": case["format_required"],
        "trigger_signals": case["trigger_signals"],
        "failure_class": failure_class,
        "existing_unresolved_format_signal": existing_unresolved if dimension == "format" else None,
        "existing_signal_gate_failed_to_consume": existing_signal,
        "upstream_missing_representation": (
            "No persisted pre-Gate Format signal represented the expected treatment."
            if dimension == "format" and not existing_unresolved else None
        ),
    }


def analyze(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if hashlib.sha256(EXPECTED_JSON.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Batch 07 expected labels changed")
    source = payload or json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    cases = source["cases"]
    topic_gate = _confusion(cases, "topic")
    format_gate = _confusion(cases, "format")
    expected_topic_gate = {"tp": 6, "fp": 2, "tn": 1, "fn": 1, "precision": 75.0, "recall": 85.71428571428571}
    expected_format_gate = {"tp": 1, "fp": 1, "tn": 1, "fn": 7, "precision": 50.0, "recall": 12.5}
    if topic_gate != expected_topic_gate or format_gate != expected_format_gate:
        raise RuntimeError("HKEI-178 Gate baseline was not reproduced")

    topic_fn_cases = [case for case in cases if not case["topic_required"] and not case["topic_match_before"]]
    format_fn_cases = [case for case in cases if not case["format_required"] and not case["format_match_before"]]
    topic_traces = [_trace(case, "topic") for case in topic_fn_cases]
    format_traces = [_trace(case, "format") for case in format_fn_cases]

    false_sufficient = []
    for case in cases:
        for dimension in ("topic", "format"):
            for item in _false_sufficient(case, dimension):
                false_sufficient.append({
                    "id": case["id"], "dimension": dimension.upper(),
                    "candidate": item["candidate"],
                    "expected": case[f"expected_{dimension}"],
                    "sufficiency": item["sufficiency"],
                    "direct_gate_contribution": False,
                })

    format_existing = [trace for trace in format_traces if trace["existing_unresolved_format_signal"]]
    format_missing = [trace for trace in format_traces if not trace["existing_unresolved_format_signal"]]
    captured_topic_ids = {trace["id"] for trace in topic_traces if trace["existing_signal_gate_failed_to_consume"]}
    captured_format_ids = {trace["id"] for trace in format_existing}
    captured_ids = captured_topic_ids | captured_format_ids
    originally_called = {case["id"] for case in cases if case["provider_called"]}

    topic_new_fp = sum(
        not case["topic_required"] and case["topic_match_before"]
        and case["deterministic_topic_confidence"] == "LOW"
        for case in cases
    )
    format_new_fp = sum(
        not case["format_required"] and case["format_match_before"]
        and (
            case["deterministic_format_confidence"] == "MEDIUM"
            or any(
                warning == "FORMAT_STRUCTURE_INCOMPLETE"
                for item in case["candidate_assessment_summary"]
                for warning in item["warnings"]
            )
        )
        for case in cases
    )
    return {
        "hkei_178_topic_gate": topic_gate,
        "hkei_178_format_gate": format_gate,
        "topic_gate_false_negatives": topic_traces,
        "format_gate_false_negatives": format_traces,
        "topic_fn_count": len(topic_traces),
        "format_fn_count": len(format_traces),
        "format_fn_with_existing_unresolved_signal": len(format_existing),
        "format_fn_without_existing_unresolved_signal": len(format_missing),
        "false_sufficient_assessments": false_sufficient,
        "false_sufficient_contributing_to_gate_fn": [],
        "false_sufficient_gate_note": "Candidate assessments were diagnostic-only in HKEI-178 and did not directly influence Gate decisions.",
        "topic_fn_diagnosis": {
            "wrong_topic_false_semantic_sufficiency": bool(_false_sufficient(topic_fn_cases[0], "topic")),
            "classifier_confidence_suppressed_adjudication": True,
            "unresolved_competing_domain_existed": "SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN" in topic_fn_cases[0]["trigger_signals"],
            "gate_lacked_existing_signal": False,
        },
        "counterfactual_topic_fn_captured": len(captured_topic_ids),
        "counterfactual_format_fn_captured": len(captured_format_ids),
        "counterfactual_additional_provider_calls": len(captured_ids - originally_called),
        "counterfactual_new_false_positives": topic_new_fp + format_new_fp,
        "counterfactual_existing_signals_only": True,
        "gate_only_fix_viability": "HIGH",
        "dominant_root_cause": "MIXED_GATE_AND_UPSTREAM_GAP",
        "recommended_next_step": "IMPLEMENT_ONE_BOUNDED_GATE_REFINEMENT",
        "one_gate_refinement_budget": 1,
        "provider_calls": 0,
    }


def render_markdown(result: dict[str, Any]) -> str:
    topic_ids = ", ".join(item["id"] for item in result["topic_gate_false_negatives"])
    format_ids = ", ".join(item["id"] for item in result["format_gate_false_negatives"])
    classes = "\n".join(
        f"- {item['id']}: {item['failure_class']}"
        for item in result["format_gate_false_negatives"]
    )
    return f"""# Batch 07 Gate Failure Analysis

Topic Gate false negative: {topic_ids}

Format Gate false negatives: {format_ids}

## Format failure classes

{classes}

Format FNs with existing unresolved signal: {result['format_fn_with_existing_unresolved_signal']}

Format FNs without existing unresolved signal: {result['format_fn_without_existing_unresolved_signal']}

Counterfactual Topic FN captured: {result['counterfactual_topic_fn_captured']}

Counterfactual Format FNs captured: {result['counterfactual_format_fn_captured']}

Counterfactual additional provider calls: {result['counterfactual_additional_provider_calls']}

Counterfactual new false positives: {result['counterfactual_new_false_positives']}

Gate-only fix viability: {result['gate_only_fix_viability']}

Dominant root cause: {result['dominant_root_cause']}

Recommendation: {result['recommended_next_step']}

One Gate refinement budget: 1

Provider calls: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if not key.endswith("false_negatives")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
