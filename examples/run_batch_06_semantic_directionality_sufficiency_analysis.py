"""Analyze Batch 06 semantic directionality and sufficiency offline."""

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_06"
CURRENT_JSON = BATCH_ROOT / "editorial_validation.json"
OUTPUT_JSON = BATCH_ROOT / "semantic_directionality_sufficiency_analysis.json"
OUTPUT_MD = BATCH_ROOT / "semantic_directionality_sufficiency_analysis.md"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_06_raw.txt"
RAW_SHA256 = "7ef269f70c78816521c8d3228db720b771294c9fb91fcbe31629b7748f115a06"
EXPECTED_SHA256 = "336e5f4f49f8e75c55751599b679b29501e3713af1f8d5514ec0a46168f6a4d8"
CASE_IDS = tuple(f"{value:03d}" for value in range(51, 61))

DOMAIN_FAILURES = {
    "051": "SUBJECT_NOT_IDENTIFIED",
    "053": "DOMAIN_MAPPING_MISSING",
    "054": "DOMAIN_MAPPING_MISSING",
    "055": "WRONG_DOMAIN_RELATIONSHIP",
    "056": "RELATIONSHIP_TOO_WEAK",
    "060": "AUTHORITY_OVERWEIGHTED",
}
FORMAT_GATE_CAUSES = {
    "054": "WRONG_FORMAT_SUPPORT_MARKED_RESOLVED",
    "056": "WRONG_FORMAT_SUPPORT_MARKED_RESOLVED",
    "058": "WRONG_FORMAT_SUPPORT_MARKED_RESOLVED",
    "059": "UNRESOLVED_FORMAT_SIGNAL_LOST",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _support_direction(case: dict[str, Any], label: str) -> str:
    if label in {f"PRIMARY_DOMAIN_{case['expected_topic']}", f"FORMAT_{case['expected_format']}"}:
        return "CORRECT_DIRECTION"
    if label in {f"PRIMARY_DOMAIN_{case['predicted_topic']}", f"FORMAT_{case['predicted_format']}"}:
        return "WRONG_DIRECTION"
    return "IRRELEVANT_DIRECTION"


def analyze() -> dict[str, Any]:
    """Diagnose persisted evidence without executing the editorial pipeline."""
    current = _read(CURRENT_JSON)
    cases = {case["id"]: case for case in current["cases"]}
    directionality: dict[str, list[dict[str, Any]]] = {}
    direction_counts: Counter[str] = Counter()
    for case_id in CASE_IDS:
        entries = []
        for relationship in cases[case_id]["semantic_relationships"]:
            for label in relationship["supports"]:
                direction = _support_direction(cases[case_id], label)
                direction_counts[direction] += 1
                entries.append({
                    "source_structure": relationship["reason_code"],
                    "semantic_relationship": relationship["type"],
                    "mapped_support": label,
                    "direction": direction,
                })
        directionality[case_id] = entries

    topic_promotion = {}
    for case_id in ("051", "053", "054", "055", "056", "060"):
        case = cases[case_id]
        topic_promotion[case_id] = {
            "expected_domain": f"PRIMARY_DOMAIN_{case['expected_topic']}",
            "domain_bearing_components": case["semantic_component_labels"],
            "semantic_relationships": case["semantic_relationships"],
            "candidate_domains": list(dict.fromkeys(
                support for relationship in case["semantic_relationships"]
                for support in relationship["supports"] if "DOMAIN_" in support
            )),
            "primary_domain": case["primary_semantic_domains"],
            "secondary_domains": case["secondary_semantic_domains"],
            "promotion_strength": "STRONG" if case["primary_semantic_domains"] else "INSUFFICIENT",
            "precedence_outcome": DOMAIN_FAILURES[case_id],
        }

    sufficiency = {
        "052": {
            "candidate": "PRIMARY_DOMAIN_ECONOMY", "subject_bearing": True,
            "uniquely_dominant": True, "competing_domains": [],
            "relationship_strength": "STRONG", "independent_support_count": 3,
            "classification": "STRONG_SUFFICIENCY",
        },
        "055": {
            "candidate": "PRIMARY_DOMAIN_ECONOMY", "subject_bearing": False,
            "uniquely_dominant": False, "competing_domains": ["WORLD", "BUSINESS"],
            "relationship_strength": "STRONG", "independent_support_count": 1,
            "classification": "FALSE_SUFFICIENCY",
        },
        "059": {
            "candidate": "PRIMARY_DOMAIN_ECONOMY", "subject_bearing": True,
            "uniquely_dominant": True, "competing_domains": [],
            "relationship_strength": "STRONG", "independent_support_count": 3,
            "classification": "STRONG_SUFFICIENCY",
        },
    }
    sufficiency_counts = dict(Counter(item["classification"] for item in sufficiency.values()))

    confidence = {}
    for case_id, case in cases.items():
        if not case["topic_match"] and case["topic_confidence"] in {"MEDIUM", "HIGH"}:
            confidence[f"{case_id}:TOPIC"] = {
                "confidence": case["topic_confidence"],
                "contributors": case["trigger_signals"],
                "classification": "SEMANTICALLY_INFLATED" if case["primary_semantic_domains"] else "DETERMINISTICALLY_INFLATED",
            }
        if not case["format_match"] and case["format_confidence"] in {"MEDIUM", "HIGH"}:
            confidence[f"{case_id}:FORMAT"] = {
                "confidence": case["format_confidence"],
                "contributors": case["semantic_format_support"],
                "classification": "SEMANTICALLY_INFLATED" if case["semantic_format_support"] else "DETERMINISTICALLY_INFLATED",
            }

    total_directional = sum(direction_counts.values())
    correct = direction_counts["CORRECT_DIRECTION"]
    result = {
        "batch_scientific_status": "DIAGNOSTIC_DEVELOPMENT_SET",
        "scientific_use": ["HISTORICAL_COMPARISON", "FAILURE_DIAGNOSIS", "REGRESSION_OBSERVATION"],
        "final_generalization_claims_allowed": False,
        "recommended_future_holdout": "BATCH_07",
        "cases_analyzed": list(CASE_IDS),
        "current_hkei_164_metrics": {
            key: current[key] for key in (
                "topic_accuracy", "format_accuracy", "reader_intent_accuracy",
                "full_case_accuracy", "topic_gate_recall", "format_gate_recall",
            )
        },
        "semantic_directionality_by_case": directionality,
        "case_054_analysis": {
            "components": cases["054"]["semantic_component_labels"],
            "relationships": cases["054"]["semantic_relationships"],
            "mapping_rule_selected": "BOUNDED_TREND_UPDATE_STRUCTURE",
            "suppression_considered": cases["054"]["semantic_format_suppression"],
            "confidence_contribution": "STRONG_SUPPORT_TO_HIGH_CONFIDENCE",
            "root_cause": "RESULT_SIGNAL_UNDERWEIGHTED",
        },
        "case_056_analysis": {
            "claim_assertion_components": ["CLAIM_ATTRIBUTED"],
            "verification_components": [], "truth_conclusion_components": [],
            "procedure_components": cases["056"]["semantic_component_labels"],
            "relationships": cases["056"]["semantic_relationships"],
            "mapping_path": "ACTION_HAS_DEADLINE_TO_SERVICE",
            "root_cause": "VERIFICATION_STRUCTURE_MISSING",
        },
        "case_058_analysis": {
            "expected_treatment": "TREND_UPDATE",
            "emitted_support": cases["058"]["semantic_format_support"],
            "components": cases["058"]["semantic_component_labels"],
            "mapping_rule": "BOUNDED_RESULT_REPORT_STRUCTURE",
            "confidence_effect": "HIGH",
            "root_cause": "COMPLETED_VS_TEMPORAL_EVENT_BOUNDARY_ERROR",
        },
        "case_059_analysis": {
            "expected_treatment": "TREND_UPDATE",
            "current_state_signal": True, "prior_reference_state": False,
            "direction_change": True, "continuation": False,
            "temporal_comparison": False, "relationship_composed": False,
            "activation_break": "TEMPORAL_COMPARISON_NOT_COMPOSED",
        },
        "topic_domain_promotion_analysis": topic_promotion,
        "expected_domain_failure_reasons": DOMAIN_FAILURES,
        "primary_domain_sufficiency_analysis": sufficiency,
        "primary_domain_sufficiency_counts": sufficiency_counts,
        "case_055_gate_safety_analysis": {
            "primary_domain": cases["055"]["primary_semantic_domains"],
            "secondary_domains": cases["055"]["secondary_semantic_domains"],
            "confidence": cases["055"]["topic_confidence"],
            "unresolved_evidence": ["EXPECTED_WORLD_ABSENT", "BUSINESS_BASELINE_COMPETES_WITH_ECONOMY"],
            "suppressions": cases["055"]["semantic_format_suppression"],
            "trigger_signals": cases["055"]["trigger_signals"],
            "semantic_sufficiency": "FALSE_SUFFICIENCY",
            "safety_break": "PARTIAL_SEMANTICS_MARKED_RESOLVED",
        },
        "format_gate_safety_analysis": {
            "previous_recall": 50.0, "current_recall": current["format_gate_recall"],
            "false_negative_cases": ["054", "056", "058", "059"],
            "causes": FORMAT_GATE_CAUSES,
        },
        "confidence_contribution_analysis": confidence,
        "confidence_inflation_cases": sorted(key for key, value in confidence.items() if value["classification"] != "JUSTIFIED"),
        "semantic_evidence_direction_metrics": {
            "aligned_with_expected": correct,
            "aligned_with_wrong_prediction": direction_counts["WRONG_DIRECTION"],
            "neutral_or_irrelevant": direction_counts["IRRELEVANT_DIRECTION"] + direction_counts["AMBIGUOUS_DIRECTION"],
            "total_directional_items": total_directional,
            "direction_accuracy": correct / total_directional * 100.0 if total_directional else 0.0,
        },
        "format_semantic_mapping_matrix": {
            "EVENT_UPDATE": "UNDERRECOGNIZED", "TEMPORAL_CHANGE": "OVERBROAD",
            "RESULT_OUTCOME": "CONFLICTING", "GUIDANCE_ACTION": "UNDERRECOGNIZED",
            "SERVICE_PROCEDURE": "OVERBROAD", "CLAIM_VERIFICATION": "UNDERRECOGNIZED",
            "CAUSE_EFFECT": "UNDERRECOGNIZED", "PROCESS_EXPLANATION": "UNDERRECOGNIZED",
        },
        "domain_mapping_matrix": {
            "SUBJECT+ECONOMIC_CONCEPT": "CORRECT",
            "OBJECT+EDUCATION_CONCEPT": "PROMOTION_MISSING",
            "CHANGE_RESULT+BUSINESS_CONCEPT": "MAPPING_MISSING",
            "ACTOR_AUTHORITY+SUBJECT_CONCEPT": "ROLE_INSENSITIVE",
            "CROSS_BORDER_EVENT+ECONOMIC_CONCEPT": "OVERBROAD",
        },
        "evidence_vs_sufficiency_conflation": "PARTIALLY",
        "dominant_root_cause": "F_MIXED_MAPPING_AND_SUFFICIENCY_FAILURE",
        "recommended_next_step": "COMBINATION_OF_DIRECTIONALITY_AND_SUFFICIENCY",
        "provider_calls": 0,
        "expected_labels_sha256": hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest(),
        "raw_source_integrity": hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() == RAW_SHA256,
    }
    return result


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    metrics = result["semantic_evidence_direction_metrics"]
    return f"""# Batch 06 Semantic Directionality and Sufficiency Analysis

## Scientific Status

{result['batch_scientific_status']}. Batch 06 is restricted to historical comparison, failure diagnosis, and regression observation. A new preregistered Batch 07 is required for final generalization claims.

## Evidence Directionality

Direction accuracy: {metrics['direction_accuracy']:.2f}% ({metrics['aligned_with_expected']}/{metrics['total_directional_items']}).

## Domain Promotion Sufficiency

{json.dumps(result['primary_domain_sufficiency_counts'], ensure_ascii=False)}

## Topic Gate Safety

Case 055: {result['case_055_gate_safety_analysis']['safety_break']}.

## Format Gate Safety

False negatives: {', '.join(result['format_gate_safety_analysis']['false_negative_cases'])}.

## Dominant Root Cause

{result['dominant_root_cause']}

## Recommended Next Step

{result['recommended_next_step']}
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(render_json(result), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
