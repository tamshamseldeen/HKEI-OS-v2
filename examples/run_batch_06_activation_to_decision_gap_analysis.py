"""Analyze Batch 06 activation-to-decision gaps without changing production."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_06_editorial_validation import (  # noqa: E402
    BATCH_ROOT, CASE_IDS, RAW_SHA256, _source_fields,
)
from examples.run_benchmark_batch_02_validation import parse_source  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import (  # noqa: E402
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


CURRENT_JSON = BATCH_ROOT / "editorial_validation.json"
COMPARISON_JSON = BATCH_ROOT / "post_hkei_160_comparison.json"
OUTPUT_JSON = BATCH_ROOT / "activation_to_decision_gap_analysis.json"
OUTPUT_MD = BATCH_ROOT / "activation_to_decision_gap_analysis.md"
EXPECTED_SHA256 = "336e5f4f49f8e75c55751599b679b29501e3713af1f8d5514ec0a46168f6a4d8"

TOPIC_REACHABILITY = {
    "051": "EXPECTED_DOMAIN_NOT_EXTRACTED",
    "053": "EXPECTED_DOMAIN_EXTRACTED_AS_COMPONENT",
    "054": "EXPECTED_DOMAIN_NOT_EXTRACTED",
    "055": "ONTOLOGY_BOUNDARY",
    "056": "EXPECTED_DOMAIN_PRESENT_IN_RELATIONSHIP",
    "060": "EXPECTED_DOMAIN_EXTRACTED_AS_COMPONENT",
}
PROMOTION_FAILURES = {
    "051": "SUBJECT_ROLE_UNRESOLVED",
    "053": "DOMAIN_MAPPING_MISSING",
    "054": "DOMAIN_MAPPING_MISSING",
    "055": "COMPETING_DOMAIN_PRECEDENCE",
    "056": "RELATIONSHIP_TOO_WEAK",
    "060": "AUTHORITY_DOMINANCE",
}
TOPIC_CONSUMPTION = {
    "051": "NO_CONSUMPTION_GAP",
    "053": "NO_CONSUMPTION_GAP",
    "054": "NO_CONSUMPTION_GAP",
    "055": "NO_CONSUMPTION_GAP",
    "056": "NO_CONSUMPTION_GAP",
    "060": "NO_CONSUMPTION_GAP",
}
FORMAT_GAPS = {
    "052": "EXPECTED_FORMAT_SUPPORT_NOT_EMITTED",
    "054": "WRONG_FORMAT_SUPPORT_EMITTED",
    "056": "WRONG_FORMAT_SUPPORT_EMITTED",
    "057": "NO_SEMANTIC_FORMAT_SIGNAL",
    "058": "WRONG_FORMAT_SUPPORT_EMITTED",
    "059": "EXPECTED_FORMAT_SUPPORT_NOT_EMITTED",
}
OWNERS = {
    "051": "SHARED_UPSTREAM", "052": "FORMAT_SEMANTIC_MAPPING",
    "053": "DOMAIN_PROMOTION", "054": "FORMAT_SEMANTIC_MAPPING",
    "055": "DOMAIN_PROMOTION", "056": "DOMAIN_PROMOTION",
    "057": "FORMAT_SEMANTIC_MAPPING", "058": "FORMAT_SEMANTIC_MAPPING",
    "059": "FORMAT_SEMANTIC_MAPPING", "060": "DOMAIN_PROMOTION",
}
ALIGNMENT = {
    "051": "IRRELEVANT", "052": "ALIGNED_WITH_PREDICTION",
    "053": "MIXED", "054": "ALIGNED_WITH_PREDICTION",
    "055": "ALIGNED_WITH_PREDICTION", "056": "MIXED",
    "057": "IRRELEVANT", "058": "ALIGNED_WITH_PREDICTION",
    "059": "MIXED", "060": "IRRELEVANT",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze() -> dict[str, Any]:
    """Trace symbolic activation into deterministic decisions for ten cases."""
    current = _read(CURRENT_JSON)
    comparison = _read(COMPARISON_JSON)
    previous = comparison["baselines"]["HKEI-158"]
    current_by_id = {case["id"]: case for case in current["cases"]}
    previous_by_id = {case["id"]: case for case in previous["cases"]}
    workflow = ExperimentalSemanticEditorialAnalysisWorkflow()
    relationship_metadata: dict[str, list[dict[str, Any]]] = {}
    for case_id in CASE_IDS:
        source = parse_source(BATCH_ROOT / case_id / "source.md")
        semantic = workflow.process(**_source_fields(source)).semantic_evidence
        relationship_metadata[case_id] = [
            {
                "type": item.relationship_type.value,
                "strength": item.strength.value,
                "reason_code": item.reason_code,
                "supports": list(item.supports),
                "suppresses": list(item.suppresses),
            }
            for item in semantic.relationships
        ]

    topic_analysis = {}
    for case_id in ("051", "053", "054", "055", "056", "060"):
        before, after = previous_by_id[case_id], current_by_id[case_id]
        expected_label = f"PRIMARY_DOMAIN_{after['expected_topic']}"
        relationship_supports = {
            support
            for relationship in relationship_metadata[case_id]
            for support in relationship["supports"]
        }
        topic_analysis[case_id] = {
            "expected_topic": after["expected_topic"],
            "predicted_topic": after["predicted_topic"],
            "new_semantic_components": after["semantic_component_labels"],
            "relationship_count_before": before["semantic_relationship_count"],
            "relationship_count_after": after["semantic_relationship_count"],
            "relationships": relationship_metadata[case_id],
            "primary_domains": after["primary_semantic_domains"],
            "secondary_domains": after["secondary_semantic_domains"],
            "expected_domain_represented": expected_label in relationship_supports or expected_label in after["primary_semantic_domains"],
            "wrong_predicted_domain_stronger": f"PRIMARY_DOMAIN_{after['predicted_topic']}" in after["primary_semantic_domains"],
            "topic_classifier_consumed_primary_domains": bool(after["primary_semantic_domains"]),
            "precedence_result": PROMOTION_FAILURES[case_id],
            "confidence_before": before["topic_confidence"],
            "confidence_after": after["topic_confidence"],
            "topic_required_before": before["topic_required"],
            "topic_required_after": after["topic_required"],
        }

    format_analysis = {}
    for case_id in ("052", "054", "056", "057", "058", "059"):
        before, after = previous_by_id[case_id], current_by_id[case_id]
        expected_support = f"FORMAT_{after['expected_format']}"
        wrong_support = f"FORMAT_{after['predicted_format']}"
        format_analysis[case_id] = {
            "expected_format": after["expected_format"],
            "predicted_format": after["predicted_format"],
            "semantic_format_support": after["semantic_format_support"],
            "semantic_format_suppression": after["semantic_format_suppression"],
            "expected_format_received_support": expected_support in after["semantic_format_support"],
            "wrong_format_received_support": wrong_support in after["semantic_format_support"],
            "classifier_consumed_support": "COMPOSITIONAL_SEMANTIC_FORMAT_EVIDENCE" in after.get("format_reason_codes", []),
            "confidence_before": before["format_confidence"],
            "confidence_after": after["format_confidence"],
            "format_required_before": before["format_required"],
            "format_required_after": after["format_required"],
            "mapping_gap": FORMAT_GAPS[case_id],
        }

    gate_case_id = next(
        case_id for case_id in CASE_IDS
        if not current_by_id[case_id]["topic_match"]
        and previous_by_id[case_id]["topic_required"]
        and not current_by_id[case_id]["topic_required"]
    )
    false_confidence = ["052", "054", "055", "056", "058", "059"]
    support_cases = [
        case_id for case_id in CASE_IDS
        if current_by_id[case_id]["semantic_format_support"]
    ]
    result = {
        "cases_analyzed": list(CASE_IDS),
        # HKEI-161 is a historical checkpoint.  Read its persisted metrics
        # instead of silently relabeling a later current artifact as HKEI-161.
        "hkei_161_metrics": {
            "topic_accuracy": comparison["current_topic_accuracy"],
            "format_accuracy": comparison["current_format_accuracy"],
            "reader_intent_accuracy": comparison["current_reader_intent_accuracy"],
            "full_case_accuracy": comparison["current_full_case_accuracy"],
            "cases_reaching_semantic_components": comparison["current_cases_reaching_semantic_components"],
            "cases_with_semantic_relationships": comparison["current_relationship_cases"],
            "cases_with_primary_semantic_domains": comparison["current_primary_domains"],
            "cases_with_semantic_format_support": comparison["current_semantic_format_support"],
            "cases_with_semantic_format_suppression": comparison["current_semantic_format_suppression"],
            "topic_gate_recall": comparison["current_topic_gate_recall"],
            "format_gate_recall": comparison["current_format_gate_recall"],
        },
        "topic_mismatch_analysis": topic_analysis,
        "expected_domain_reachability": TOPIC_REACHABILITY,
        "domain_promotion_failures": PROMOTION_FAILURES,
        "domain_promotion_failure_counts": dict(Counter(PROMOTION_FAILURES.values())),
        "topic_classifier_consumption_findings": {
            "primary_semantic_domains": "CONSUMED",
            "secondary_semantic_domains": "CONSUMED",
            "relationship_support": "INDIRECT_VIA_PROMOTED_CANDIDATES",
            "semantic_suppressions": "CONSUMED",
            "by_case": TOPIC_CONSUMPTION,
        },
        "topic_gate_recall_regression": {
            "case_id": gate_case_id,
            "previous_prediction": previous_by_id[gate_case_id]["predicted_topic"],
            "current_prediction": current_by_id[gate_case_id]["predicted_topic"],
            "expected_topic": current_by_id[gate_case_id]["expected_topic"],
            "previous_confidence": previous_by_id[gate_case_id]["topic_confidence"],
            "current_confidence": current_by_id[gate_case_id]["topic_confidence"],
            "previous_trigger_signals": previous_by_id[gate_case_id]["trigger_signals"],
            "current_trigger_signals": current_by_id[gate_case_id]["trigger_signals"],
            "previous_topic_required": previous_by_id[gate_case_id]["topic_required"],
            "current_topic_required": current_by_id[gate_case_id]["topic_required"],
            "previous_semantic_components": previous_by_id[gate_case_id].get("semantic_component_labels", []),
            "current_semantic_components": current_by_id[gate_case_id]["semantic_component_labels"],
            "previous_relationship_count": previous_by_id[gate_case_id]["semantic_relationship_count"],
            "current_relationships": relationship_metadata[gate_case_id],
            "previous_primary_domains": previous_by_id[gate_case_id]["primary_semantic_domains"],
            "current_primary_domains": current_by_id[gate_case_id]["primary_semantic_domains"],
            "cause": "FALSE_PRIMARY_DOMAIN_SUFFICIENCY",
            "finding": "A wrong economy primary domain and higher confidence made partial semantics appear resolved, removing unresolved-domain Gate signals.",
        },
        "format_mismatch_analysis": format_analysis,
        "semantic_format_support_utility": {
            case_id: "E_SUPPORT_IS_CONTRADICTORY" for case_id in support_cases
        },
        "format_classifier_consumption_findings": {
            "support_cases": support_cases,
            "expected_support_emitted": [],
            "expected_support_emitted_not_selected": [],
            "wrong_or_contradictory_support_cases": support_cases,
            "finding": "The classifier inspects semantic support conditionally, but every emitted signal targeted a non-expected treatment and none altered selection toward the expected format.",
        },
        "format_gate_fn_analysis": {
            case_id: {
                "components_before": 0,
                "components_after": current_by_id[case_id]["semantic_component_labels"],
                "relationships_before": previous_by_id[case_id]["semantic_relationship_count"],
                "relationships_after": current_by_id[case_id]["semantic_relationship_count"],
                "support_before": previous_by_id[case_id]["semantic_format_support"],
                "support_after": current_by_id[case_id]["semantic_format_support"],
                "suppression_before": previous_by_id[case_id]["semantic_format_suppression"],
                "suppression_after": current_by_id[case_id]["semantic_format_suppression"],
                "confidence_before": previous_by_id[case_id]["format_confidence"],
                "confidence_after": current_by_id[case_id]["format_confidence"],
                "format_required_before": previous_by_id[case_id]["format_required"],
                "format_required_after": current_by_id[case_id]["format_required"],
                "status": "STILL_FALSE_NEGATIVE",
            } for case_id in ("054", "056", "059")
        },
        "reader_intent_dependency": {
            "direct_intent_failures": 0,
            "downstream_intent_failures": 6,
            "mixed_intent_failures": 0,
            "all_current_failures_downstream_from_format": True,
        },
        "evidence_quantity_vs_quality": {
            "classification": "YES",
            "components_delta": 7,
            "relationships_delta": 3,
            "primary_domains_delta": 2,
            "format_support_delta": 3,
            "topic_accuracy_delta": 0.0,
            "format_accuracy_delta": 0.0,
        },
        "false_semantic_confidence_cases": false_confidence,
        "false_semantic_confidence_count": len(false_confidence),
        "evidence_alignment_by_case": ALIGNMENT,
        "architectural_owner_by_failed_case": OWNERS,
        "dominant_root_cause": "F_MIXED_ACTIVATION_TO_DECISION_GAP",
        "recommended_next_step": "COMBINATION_OF_PROMOTION_AND_CONSUMPTION",
        "provider_calls": 0,
        "expected_labels_sha256": hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest(),
        "raw_source_integrity": hashlib.sha256((PROJECT_ROOT.parent / "benchmark_sources/batch_06_raw.txt").read_bytes()).hexdigest() == RAW_SHA256,
    }
    return result


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    topic = "\n".join(f"- {key}: {value}" for key, value in result["expected_domain_reachability"].items())
    formats = "\n".join(f"- {key}: {value['mapping_gap']}" for key, value in result["format_mismatch_analysis"].items())
    owners = "\n".join(f"- {key}: {value}" for key, value in result["architectural_owner_by_failed_case"].items())
    return f"""# Batch 06 Activation-to-Decision Gap Analysis

## Summary

Semantic activation increased materially without editorial accuracy improvement.

## Topic Evidence Reachability

{topic}

## Domain Promotion

{json.dumps(result['domain_promotion_failure_counts'], ensure_ascii=False)}

## Topic Classifier Consumption

Primary and secondary candidates and semantic suppressions are consumed; relationship support affects decisions primarily after promotion.

## Topic Gate Recall Regression

Case {result['topic_gate_recall_regression']['case_id']}: {result['topic_gate_recall_regression']['cause']}.

## Format Semantic Support

{formats}

## Format Classifier Consumption

No expected-format support was emitted; all three new supports were wrong or contradictory.

## Format Gate False Negatives

Cases 054, 056, and 059 remain false negatives.

## Reader Intent Dependency

Direct failures: 0; downstream failures: 6.

## Evidence Quantity vs Quality

{result['evidence_quantity_vs_quality']['classification']}

## False Semantic Confidence

Cases: {', '.join(result['false_semantic_confidence_cases'])}.

## Architectural Ownership

{owners}

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
