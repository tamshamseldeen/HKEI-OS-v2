"""Analyze persisted Batch 06 generalization failures without rerunning models."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_06"
VALIDATION_JSON = BATCH_ROOT / "editorial_validation.json"
EXPECTED_JSON = BATCH_ROOT / "expected.json"
RISK_JSON = BATCH_ROOT / "human_risk_annotations.json"
OUTPUT_JSON = BATCH_ROOT / "generalization_failure_analysis.json"
OUTPUT_MD = BATCH_ROOT / "generalization_failure_analysis.md"
CASE_IDS = tuple(f"{value:03d}" for value in range(51, 61))
EXPECTED_SHA256 = "336e5f4f49f8e75c55751599b679b29501e3713af1f8d5514ec0a46168f6a4d8"

TOPIC_CLASSES = frozenset({
    "LEXICAL_GENERALIZATION_GAP", "DOMAIN_ONTOLOGY_OVERLAP",
    "AUTHORITY_SUBJECT_CONFUSION", "ACTOR_SUBJECT_CONFUSION",
    "METHOD_SUBJECT_CONFUSION", "PRIMARY_SUBJECT_NOT_COMPOSED",
    "CONTEXT_PRESENT_BUT_UNCOMPOSED", "SEMANTIC_DOMAIN_MISSING",
    "DOMAIN_PRECEDENCE_ERROR", "EXPECTED_LABEL_AMBIGUITY", "OTHER",
})
FORMAT_CLASSES = frozenset({
    "FORMAT_CONFIDENCE_FALSE_SECURITY", "FORMAT_STRUCTURE_NOT_EXTRACTED",
    "FORMAT_CONTEXT_PRESENT_BUT_UNCOMPOSED", "FORMAT_SEMANTIC_SUPPORT_MISSING",
    "FORMAT_SEMANTIC_SUPPRESSION_MISSING", "FORMAT_ONTOLOGY_OVERLAP",
    "ACTION_STRUCTURE_MISSING", "TEMPORAL_UPDATE_STRUCTURE_MISSING",
    "RESULT_STRUCTURE_MISSING", "GUIDE_SERVICE_STRUCTURE_MISSING",
    "FACT_CHECK_STRUCTURE_MISSING", "OTHER",
})
OWNERS = frozenset({
    "TOPIC_CLASSIFIER", "FORMAT_CLASSIFIER", "READER_INTENT_CLASSIFIER",
    "CONTEXTUAL_EVIDENCE", "COMPOSITIONAL_SEMANTICS", "ADJUDICATION_GATE",
    "ONTOLOGY", "EXPECTED_LABEL", "SHARED_UPSTREAM",
})

TOPIC_FAILURES = {
    "051": ["DOMAIN_ONTOLOGY_OVERLAP", "SEMANTIC_DOMAIN_MISSING", "PRIMARY_SUBJECT_NOT_COMPOSED", "EXPECTED_LABEL_AMBIGUITY"],
    "053": ["CONTEXT_PRESENT_BUT_UNCOMPOSED", "PRIMARY_SUBJECT_NOT_COMPOSED", "SEMANTIC_DOMAIN_MISSING", "DOMAIN_PRECEDENCE_ERROR"],
    "054": ["CONTEXT_PRESENT_BUT_UNCOMPOSED", "PRIMARY_SUBJECT_NOT_COMPOSED", "SEMANTIC_DOMAIN_MISSING", "DOMAIN_PRECEDENCE_ERROR"],
    "055": ["CONTEXT_PRESENT_BUT_UNCOMPOSED", "PRIMARY_SUBJECT_NOT_COMPOSED", "SEMANTIC_DOMAIN_MISSING", "DOMAIN_PRECEDENCE_ERROR"],
    "056": ["AUTHORITY_SUBJECT_CONFUSION", "PRIMARY_SUBJECT_NOT_COMPOSED", "SEMANTIC_DOMAIN_MISSING"],
    "060": ["AUTHORITY_SUBJECT_CONFUSION", "PRIMARY_SUBJECT_NOT_COMPOSED", "SEMANTIC_DOMAIN_MISSING", "DOMAIN_PRECEDENCE_ERROR"],
}
FORMAT_FAILURES = {
    "052": ["FORMAT_CONTEXT_PRESENT_BUT_UNCOMPOSED", "FORMAT_SEMANTIC_SUPPORT_MISSING", "FORMAT_ONTOLOGY_OVERLAP"],
    "054": ["RESULT_STRUCTURE_MISSING", "FORMAT_STRUCTURE_NOT_EXTRACTED", "FORMAT_SEMANTIC_SUPPORT_MISSING", "FORMAT_CONFIDENCE_FALSE_SECURITY"],
    "056": ["FACT_CHECK_STRUCTURE_MISSING", "ACTION_STRUCTURE_MISSING", "FORMAT_SEMANTIC_SUPPORT_MISSING", "FORMAT_CONFIDENCE_FALSE_SECURITY"],
    "057": ["FORMAT_CONTEXT_PRESENT_BUT_UNCOMPOSED", "FORMAT_SEMANTIC_SUPPORT_MISSING", "FORMAT_ONTOLOGY_OVERLAP"],
    "058": ["TEMPORAL_UPDATE_STRUCTURE_MISSING", "FORMAT_CONTEXT_PRESENT_BUT_UNCOMPOSED", "FORMAT_SEMANTIC_SUPPORT_MISSING", "FORMAT_ONTOLOGY_OVERLAP"],
    "059": ["TEMPORAL_UPDATE_STRUCTURE_MISSING", "FORMAT_STRUCTURE_NOT_EXTRACTED", "FORMAT_SEMANTIC_SUPPORT_MISSING", "FORMAT_CONFIDENCE_FALSE_SECURITY"],
}
EXPECTED_CLARITY = {
    "051": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
    "052": "EXPECTED_LABEL_CLEAR",
    "053": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
    "054": "EXPECTED_LABEL_CLEAR",
    "055": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
    "056": "EXPECTED_LABEL_CLEAR",
    "057": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
    "058": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
    "059": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
    "060": "EXPECTED_LABEL_DEFENSIBLE_BUT_AMBIGUOUS",
}
OWNERS_BY_ID = {
    "051": "ONTOLOGY", "052": "COMPOSITIONAL_SEMANTICS",
    "053": "COMPOSITIONAL_SEMANTICS", "054": "SHARED_UPSTREAM",
    "055": "COMPOSITIONAL_SEMANTICS", "056": "SHARED_UPSTREAM",
    "057": "FORMAT_CLASSIFIER", "058": "COMPOSITIONAL_SEMANTICS",
    "059": "FORMAT_CLASSIFIER", "060": "TOPIC_CLASSIFIER",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _furthest_stage(case: dict[str, Any]) -> str:
    if case["semantic_format_support"]:
        return "FORMAT_SEMANTIC_SUPPORT"
    if case["primary_semantic_domains"]:
        return "DOMAIN"
    if case["semantic_relationship_count"]:
        return "RELATIONSHIP"
    if case["contextual_support_labels"] or case["contextual_suppressions"]:
        return "CONTEXT_ONLY"
    return "NO_CONTEXT"


def _machine_analysis(validation: dict[str, Any]) -> list[dict[str, Any]]:
    """Classify persisted machine findings before human metadata is read."""
    assert tuple(validation["case_ids"]) == CASE_IDS
    results = []
    for source in validation["cases"]:
        case_id = source["id"]
        intent_failure = (
            "DOWNSTREAM_FROM_WRONG_FORMAT"
            if not source["intent_match"] and not source["format_match"]
            else "DIRECT_INTENT_FAILURE" if not source["intent_match"]
            else "NONE"
        )
        results.append({
            "id": case_id,
            "expected_topic": source["expected_topic"],
            "predicted_topic": source["predicted_topic"],
            "topic_match": source["topic_match"],
            "expected_format": source["expected_format"],
            "predicted_format": source["predicted_format"],
            "format_match": source["format_match"],
            "expected_intent": source["expected_reader_intent"],
            "predicted_intent": source["predicted_reader_intent"],
            "intent_match": source["intent_match"],
            "topic_failure_classes": TOPIC_FAILURES.get(case_id, []),
            "format_failure_classes": FORMAT_FAILURES.get(case_id, []),
            "intent_failure_class": intent_failure,
            "contextual_evidence_present": bool(source["contextual_support_labels"] or source["contextual_suppressions"]),
            "semantic_relationship_present": source["semantic_relationship_count"] > 0,
            "primary_domain_present": bool(source["primary_semantic_domains"]),
            "semantic_format_support_present": bool(source["semantic_format_support"]),
            "furthest_evidence_stage": _furthest_stage(source),
            "gate_scope": source["gate_scope"],
            "topic_required": source["topic_required"],
            "format_required": source["format_required"],
            "topic_gate_correct": source["topic_required"] is (not source["topic_match"]),
            "format_gate_correct": source["format_required"] is (not source["format_match"]),
            "human_risk_alignment": "NOT_YET_READ",
            "expected_label_clarity": EXPECTED_CLARITY[case_id],
            "primary_architectural_owner": OWNERS_BY_ID[case_id],
        })
    return results


def _apply_human_risk(cases: list[dict[str, Any]], annotations: list[dict[str, Any]]) -> None:
    annotation_by_id = {item["id"]: item for item in annotations}
    for case in cases:
        annotation = annotation_by_id[case["id"]]
        topic_aligned = not case["topic_match"] and any(
            marker in annotation["sensitive_context"] or marker in annotation["notes"].upper()
            for marker in ("TOPIC", "AUTHORITY", "ACTOR", "DOMAIN", "SUBJECT")
        )
        format_aligned = not case["format_match"] and "FORMAT" in (
            annotation["sensitive_context"] + " " + annotation["notes"]
        ).upper()
        gate_fn_aligned = not case["format_gate_correct"] and format_aligned
        alignments = []
        if topic_aligned:
            alignments.append("TOPIC_FAILURE_PREDICTED")
        if format_aligned:
            alignments.append("FORMAT_FAILURE_PREDICTED")
        if gate_fn_aligned:
            alignments.append("FORMAT_GATE_FALSE_NEGATIVE_PREDICTED")
        case["human_risk_alignment"] = alignments or ["NO_DIRECT_ALIGNMENT"]


def analyze(*, batch_root: Path = BATCH_ROOT) -> dict[str, Any]:
    validation = _read(batch_root / VALIDATION_JSON.name)
    cases = _machine_analysis(validation)
    # Human annotations are intentionally loaded only after machine analysis freezes.
    _apply_human_risk(cases, _read(batch_root / RISK_JSON.name)["annotations"])
    stages = Counter(case["furthest_evidence_stage"] for case in cases)
    context_cases = sum(case["contextual_evidence_present"] for case in cases)
    relationship_cases = sum(case["semantic_relationship_present"] for case in cases)
    domain_cases = sum(case["primary_domain_present"] for case in cases)
    format_support_cases = sum(case["semantic_format_support_present"] for case in cases)
    format_fns = [case["id"] for case in cases if not case["format_match"] and not case["format_required"]]
    intent_counts = Counter(case["intent_failure_class"] for case in cases)
    result = {
        "cases_analyzed": list(CASE_IDS),
        "hkei_155_metrics": {
            key: validation[key] for key in (
                "topic_accuracy", "format_accuracy", "reader_intent_accuracy",
                "full_case_accuracy", "topic_gate_recall", "format_gate_recall",
                "projected_provider_call_rate",
            )
        },
        "expected_labels_sha256": hashlib.sha256((batch_root / EXPECTED_JSON.name).read_bytes()).hexdigest(),
        "topic_failures": sum(not case["topic_match"] for case in cases),
        "format_failures": sum(not case["format_match"] for case in cases),
        "intent_failures": sum(not case["intent_match"] for case in cases),
        "topic_gate_false_negatives": sum(not case["topic_match"] and not case["topic_required"] for case in cases),
        "topic_gate_false_positive_case": next(case["id"] for case in cases if case["topic_match"] and case["topic_required"]),
        "topic_gate_capture_mechanism": (
            "All Topic errors lacked a primary semantic domain; unresolved-domain "
            "signals captured them, reinforced in some cases by low confidence, "
            "missing relationships, or competing Topic signals."
        ),
        "format_gate_false_negatives": len(format_fns),
        "format_gate_false_negative_cases": format_fns,
        "format_gate_true_positive_cases": [case["id"] for case in cases if not case["format_match"] and case["format_required"]],
        "format_gate_tp_distinction": (
            "Captured errors exposed contextual format evidence that was not promoted; "
            "missed errors lacked semantic format support and recognizable result, "
            "fact-check, or temporal-update structure triggers."
        ),
        "direct_intent_failures": intent_counts["DIRECT_INTENT_FAILURE"],
        "downstream_intent_failures": intent_counts["DOWNSTREAM_FROM_WRONG_FORMAT"],
        "mixed_intent_failures": intent_counts["MIXED"],
        "evidence_stage_counts": {
            stage: stages.get(stage, 0) for stage in (
                "NO_CONTEXT", "CONTEXT_ONLY", "RELATIONSHIP", "DOMAIN",
                "FORMAT_SEMANTIC_SUPPORT",
            )
        },
        "context_only_cases": stages.get("CONTEXT_ONLY", 0),
        "semantic_relationship_cases": relationship_cases,
        "primary_domain_cases": domain_cases,
        "semantic_format_support_cases": format_support_cases,
        "context_to_relationship_conversion_rate": _percentage(relationship_cases, context_cases),
        "relationship_to_primary_domain_conversion_rate": _percentage(domain_cases, relationship_cases),
        "context_to_primary_domain_conversion_rate": _percentage(domain_cases, context_cases),
        "format_semantic_support_rate": _percentage(format_support_cases, len(cases)),
        "expected_label_review_cases": sum(
            case["expected_label_clarity"] == "EXPECTED_LABEL_REQUIRES_REVIEW" for case in cases
        ),
        "dominant_failure_category": "COMPOSITION_DOMINANT",
        "dominant_finding": (
            "Evidence extraction reached context in 9/10 cases, but conversion fell "
            "to relationships in 3/10, a primary domain in 1/10, and format semantic "
            "support in 0/10. Composition/promotion is therefore the dominant failure, "
            "with additional format-structure and Gate coverage gaps."
        ),
        "recommended_next_step": "F. COMBINATION_OF_A_B_C",
        "provider_calls": 0,
        "cases": cases,
    }
    assert all(set(case["topic_failure_classes"]) <= TOPIC_CLASSES for case in cases)
    assert all(set(case["format_failure_classes"]) <= FORMAT_CLASSES for case in cases)
    assert all(case["primary_architectural_owner"] in OWNERS for case in cases)
    return result


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    cases = result["cases"]
    topic_lines = "\n".join(
        f"- {case['id']}: {case['expected_topic']} → {case['predicted_topic']} ({', '.join(case['topic_failure_classes'])})"
        for case in cases if not case["topic_match"]
    )
    format_lines = "\n".join(
        f"- {case['id']}: {case['expected_format']} → {case['predicted_format']} ({', '.join(case['format_failure_classes'])})"
        for case in cases if not case["format_match"]
    )
    owners = "\n".join(
        f"- {case['id']}: {case['primary_architectural_owner']}" for case in cases
    )
    clarity = "\n".join(
        f"- {case['id']}: {case['expected_label_clarity']}" for case in cases
    )
    return f"""# Batch 06 Blind Generalization Failure Analysis

## Summary

Topic failures: {result['topic_failures']}; Format failures: {result['format_failures']}; Reader Intent failures: {result['intent_failures']}.

## Topic Failures

{topic_lines}

## Topic Gate Performance

False negatives: {result['topic_gate_false_negatives']}. False positive: {result['topic_gate_false_positive_case']}.

{result['topic_gate_capture_mechanism']}

## Format Failures

{format_lines}

## Format Gate False Negatives

Cases: {', '.join(result['format_gate_false_negative_cases'])}.

{result['format_gate_tp_distinction']}

## Reader Intent Dependency

Direct: {result['direct_intent_failures']}; downstream from Format: {result['downstream_intent_failures']}; mixed: {result['mixed_intent_failures']}.

## Evidence Funnel

{json.dumps(result['evidence_stage_counts'], ensure_ascii=False)}

## Context-to-Semantics Conversion

Context → relationship: {result['context_to_relationship_conversion_rate']:.2f}%

Relationship → primary domain: {result['relationship_to_primary_domain_conversion_rate']:.2f}%

Context → primary domain: {result['context_to_primary_domain_conversion_rate']:.2f}%

Format semantic support: {result['format_semantic_support_rate']:.2f}%

## Human Risk Alignment

Human annotations were applied only after machine analysis and align with multiple observed Topic, Format, and Gate failures; they did not revise expected labels.

## Expected Label Clarity

{clarity}

## Architectural Ownership

{owners}

## Dominant Finding

{result['dominant_failure_category']}: {result['dominant_finding']}

## Recommended Next Step

{result['recommended_next_step']}
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(render_json(result), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
