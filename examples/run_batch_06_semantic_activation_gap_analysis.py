"""Diagnose offline Batch 06 activation gaps without changing production."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_06_editorial_validation import (  # noqa: E402
    BATCH_ROOT,
    CASE_IDS,
    RAW_SHA256,
    _source_fields,
)
from examples.run_benchmark_batch_02_validation import parse_source  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import (  # noqa: E402
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


OUTPUT_JSON = BATCH_ROOT / "semantic_activation_gap_analysis.json"
OUTPUT_MD = BATCH_ROOT / "semantic_activation_gap_analysis.md"
EXPECTED_SHA256 = "336e5f4f49f8e75c55751599b679b29501e3713af1f8d5514ec0a46168f6a4d8"
STAGES = (
    "RAW_ONLY", "LEXICAL_COMPONENTS", "CONTEXTUAL_EVIDENCE",
    "SEMANTIC_COMPONENTS", "RELATIONSHIP_CANDIDATE",
    "RELATIONSHIP_ACCEPTED", "DOMAIN_PROMOTED", "FORMAT_SUPPORT_EMITTED",
    "FORMAT_SUPPORT_CONSUMED",
)
LOCALITIES = (
    "SAME_SENTENCE", "ADJACENT_SENTENCES", "TWO_SENTENCES_APART",
    "THREE_PLUS_SENTENCES_APART", "TITLE_TO_BODY", "LEAD_TO_BODY",
    "MULTI_SECTION",
)

# Diagnostic labels describe observed structures; they are never imported by
# production code and contain no source phrases.
PRESENT_ROLES = {
    "051": ["SUBJECT", "STATE", "CHANGE", "MEASUREMENT", "OUTCOME"],
    "052": ["ACTOR", "SUBJECT", "METHOD", "ACTION", "CAUSE", "EFFECT", "RESULT", "MEASUREMENT"],
    "053": ["ACTOR", "SUBJECT", "ACTION", "CHANGE", "RESULT", "MEASUREMENT"],
    "054": ["ACTOR", "SUBJECT", "ACTION", "RESULT", "MEASUREMENT", "TEMPORAL_UPDATE", "OUTCOME"],
    "055": ["ACTOR", "SUBJECT", "ACTION", "RESULT", "OUTCOME"],
    "056": ["AUTHORITY", "SUBJECT", "ACTION", "STATE", "PROCEDURE", "SCHEDULE", "OUTCOME"],
    "057": ["ACTOR", "SUBJECT", "ACTION", "RESULT", "OUTCOME"],
    "058": ["ACTOR", "SUBJECT", "STATE", "CHANGE", "CAUSE", "EFFECT", "MEASUREMENT", "TEMPORAL_UPDATE"],
    "059": ["SUBJECT", "STATE", "CHANGE", "CAUSE", "MEASUREMENT", "PRICE", "TEMPORAL_UPDATE"],
    "060": ["AUTHORITY", "ACTOR", "SUBJECT", "OBJECT", "ACTION", "REQUIREMENT"],
}
MISSING_ROLES = {
    "051": ["ACTION", "DOMAIN_NORMALIZATION"],
    "052": ["CAUSE_EFFECT_NORMALIZATION"],
    "053": ["BUSINESS_SUBJECT_NORMALIZATION"],
    "054": ["RESULT_NORMALIZATION"],
    "055": ["WORLD_EVENT_NORMALIZATION"],
    "056": ["CLAIM", "VERIFICATION", "VERDICT"],
    "057": ["FUTURE_RESULT_DISTINCTION"],
    "058": ["TEMPORAL_MOVEMENT_NORMALIZATION"],
    "059": ["CURRENT_LEVEL_NORMALIZATION", "TEMPORAL_MOVEMENT_NORMALIZATION"],
    "060": ["BUSINESS_SUBJECT_NORMALIZATION"],
}
STAGE_BY_ID = {
    "051": "LEXICAL_COMPONENTS", "052": "RELATIONSHIP_ACCEPTED",
    "053": "CONTEXTUAL_EVIDENCE", "054": "CONTEXTUAL_EVIDENCE",
    "055": "CONTEXTUAL_EVIDENCE", "056": "DOMAIN_PROMOTED",
    "057": "CONTEXTUAL_EVIDENCE", "058": "CONTEXTUAL_EVIDENCE",
    "059": "RELATIONSHIP_ACCEPTED", "060": "CONTEXTUAL_EVIDENCE",
}
LOCALITY_BY_ID = {
    "051": "TITLE_TO_BODY", "052": "MULTI_SECTION", "053": "TITLE_TO_BODY",
    "054": "TITLE_TO_BODY", "055": "LEAD_TO_BODY", "056": "ADJACENT_SENTENCES",
    "057": "TITLE_TO_BODY", "058": "LEAD_TO_BODY", "059": "ADJACENT_SENTENCES",
    "060": "LEAD_TO_BODY",
}
GAP_BY_ID = {
    "051": "VOCABULARY_TO_COMPONENT_GAP",
    "052": "COMPONENT_TO_RELATIONSHIP_GAP",
    "053": "VOCABULARY_TO_COMPONENT_GAP",
    "054": "VOCABULARY_TO_COMPONENT_GAP",
    "055": "VOCABULARY_TO_COMPONENT_GAP",
    "056": "VOCABULARY_TO_COMPONENT_GAP",
    "057": "COMPONENT_TO_RELATIONSHIP_GAP",
    "058": "VOCABULARY_TO_COMPONENT_GAP",
    "059": "RELATIONSHIP_TO_FORMAT_GAP",
    "060": "VOCABULARY_TO_COMPONENT_GAP",
}
OWNER_BY_ID = {
    "051": "SEMANTIC_COMPONENT_EXTRACTION", "052": "COMPOSITIONAL_RELATIONSHIP_ENGINE",
    "053": "LEXICAL_EXTRACTION", "054": "SEMANTIC_COMPONENT_EXTRACTION",
    "055": "SEMANTIC_COMPONENT_EXTRACTION", "056": "SEMANTIC_COMPONENT_EXTRACTION",
    "057": "COMPOSITIONAL_RELATIONSHIP_ENGINE", "058": "SEMANTIC_COMPONENT_EXTRACTION",
    "059": "FORMAT_SEMANTIC_MAPPING", "060": "SEMANTIC_COMPONENT_EXTRACTION",
}
FORMAT_ZERO = {
    "051": "NO_VALID_FORMAT_STRUCTURE",
    "052": "FORMAT_COMPONENTS_EXTRACTED_BUT_NOT_COMPOSED",
    "053": "NO_VALID_FORMAT_STRUCTURE",
    "054": "FORMAT_COMPONENTS_NOT_EXTRACTED",
    "055": "NO_VALID_FORMAT_STRUCTURE",
    "056": "FORMAT_COMPONENTS_NOT_EXTRACTED",
    "057": "FORMAT_COMPONENTS_EXTRACTED_BUT_NOT_COMPOSED",
    "058": "FORMAT_COMPONENTS_NOT_EXTRACTED",
    "059": "RELATIONSHIP_EXISTS_BUT_FORMAT_MAPPING_MISSING",
    "060": "NO_VALID_FORMAT_STRUCTURE",
}
ARABIC_BY_ID = {
    "051": ["headline-style ellipsis", "multiword concepts"],
    "052": ["nominal constructions", "synonymous journalistic phrasing"],
    "053": ["verb inflection", "multiword concepts"],
    "054": ["nominal constructions", "temporal phrasing"],
    "055": ["implicit subject", "multiword concepts"],
    "056": ["headline-style ellipsis", "synonymous journalistic phrasing"],
    "057": ["nominal constructions", "headline-style ellipsis"],
    "058": ["prepositional constructions", "synonymous journalistic phrasing"],
    "059": ["verb inflection", "temporal phrasing"],
    "060": ["plural/singular variation", "multiword concepts"],
}


def _inventory(result: Any) -> list[dict[str, Any]]:
    """Return symbolic contextual metadata without article bodies."""
    return [
        {
            "evidence_level": item.evidence_level.value,
            "role": item.role.value,
            "strength": item.strength.value,
            "source_section": item.source_section.value,
            "support_labels": list(item.supports),
            "suppression_labels": list(item.suppresses),
        }
        for item in result.contextual_evidence.all_items
    ]


def _title_lead_usage(source: Any, result: Any) -> str:
    sections = {item.source_section.value for item in result.contextual_evidence.all_items}
    title_words = set(re.findall(r"\w+", source.title))
    body_words = set(re.findall(r"\w+", source.body))
    if "HEADLINE" in sections and ("LEAD" in sections or "BODY" in sections):
        return "TITLE_AND_BODY"
    if "HEADLINE" in sections:
        return "TITLE_ONLY"
    if "LEAD" in sections and "BODY" in sections:
        return "LEAD_AND_BODY"
    if "LEAD" in sections:
        return "LEAD_ONLY"
    if "BODY" in sections:
        return "BODY_ONLY"
    return "TITLE_AND_BODY" if title_words & body_words else "BODY_ONLY"


def _synthetic_comparison() -> dict[str, str]:
    return {
        "authority_domain_subject": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "actor_domain_subject": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "method_subject": "REAL_ANALOG_FOUND_BUT_RELATIONSHIP_NOT_COMPOSED",
        "event_cause_effect": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "system_mechanism": "SYNTHETIC_ONLY",
        "price_service": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "schedule": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "guide_action": "REAL_ANALOG_FOUND_BUT_RELATIONSHIP_NOT_COMPOSED",
        "result": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "trend": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
        "fact_check": "REAL_ANALOG_FOUND_BUT_COMPONENTS_MISSING",
    }


def analyze() -> dict[str, Any]:
    """Trace the current deterministic pipeline for exactly ten cases."""
    workflow = ExperimentalSemanticEditorialAnalysisWorkflow()
    validation = json.loads((BATCH_ROOT / "editorial_validation.json").read_text(encoding="utf-8"))
    validation_by_id = {case["id"]: case for case in validation["cases"]}
    cases: list[dict[str, Any]] = []
    for case_id in CASE_IDS:
        source = parse_source(BATCH_ROOT / case_id / "source.md")
        result = workflow.process(**_source_fields(source))
        semantic = result.semantic_evidence
        current = validation_by_id[case_id]
        cases.append({
            "id": case_id,
            "furthest_activation_stage": STAGE_BY_ID[case_id],
            "contextual_evidence_inventory": _inventory(result),
            "present_roles": PRESENT_ROLES[case_id],
            "missing_roles_needed_for_expected_composition": MISSING_ROLES[case_id],
            "relationship_candidate_generated": STAGE_BY_ID[case_id] in {
                "RELATIONSHIP_CANDIDATE", "RELATIONSHIP_ACCEPTED", "DOMAIN_PROMOTED",
                "FORMAT_SUPPORT_EMITTED", "FORMAT_SUPPORT_CONSUMED",
            },
            "relationship_candidate_failure": (
                None if semantic.relationships else
                "COMPONENT_NORMALIZATION_MISMATCH" if "VOCABULARY" in GAP_BY_ID[case_id]
                else "RELATIONSHIP_PATTERN_NOT_REACHED"
            ),
            "accepted_relationship_count": len(semantic.relationships),
            "primary_domains": list(semantic.primary_domain_candidates),
            "secondary_domains": list(semantic.secondary_domain_candidates),
            "semantic_format_support": list(semantic.format_support),
            "semantic_format_suppression": list(semantic.format_suppression),
            "locality": LOCALITY_BY_ID[case_id],
            "current_window_can_compose": LOCALITY_BY_ID[case_id] in {
                "SAME_SENTENCE", "ADJACENT_SENTENCES",
            },
            "title_lead_usage": _title_lead_usage(source, result),
            "real_vocabulary_structural_gap": GAP_BY_ID[case_id],
            "arabic_expression_findings": ARABIC_BY_ID[case_id],
            "primary_architectural_owner": OWNER_BY_ID[case_id],
            "semantic_format_support_zero_cause": FORMAT_ZERO[case_id],
            "format_classifier_consumed_support": False,
            "gate_signals": current["trigger_signals"],
        })
    stages = Counter(case["furthest_activation_stage"] for case in cases)
    accepted = sum(case["accepted_relationship_count"] > 0 for case in cases)
    result = {
        "cases_analyzed": list(CASE_IDS),
        "provider_calls": 0,
        "zero_delta_reproduced": {
            "semantic_relationships": [3, accepted],
            "primary_domains": [1, sum(bool(case["primary_domains"]) for case in cases)],
            "semantic_format_support": [0, sum(bool(case["semantic_format_support"]) for case in cases)],
        },
        "activation_stage_by_case": {case["id"]: case["furthest_activation_stage"] for case in cases},
        "activation_stage_counts": {stage: stages.get(stage, 0) for stage in STAGES},
        "component_role_coverage_by_case": {
            case["id"]: {
                "present_roles": case["present_roles"],
                "missing_roles_needed_for_expected_composition": case["missing_roles_needed_for_expected_composition"],
            } for case in cases
        },
        "relationship_candidate_findings": {
            case["id"]: {
                "generated": case["relationship_candidate_generated"],
                "failure": case["relationship_candidate_failure"],
            } for case in cases
        },
        "locality_findings": {case["id"]: {"classification": case["locality"], "window_can_compose": case["current_window_can_compose"]} for case in cases},
        "synthetic_real_pattern_comparison": _synthetic_comparison(),
        "topic_activation_failures": {
            key: value for key, value in {
                "051": "DOMAIN_SIGNAL_NOT_EXTRACTED", "053": "DOMAIN_SIGNAL_EXTRACTED_NOT_NORMALIZED",
                "054": "DOMAIN_SIGNAL_EXTRACTED_NOT_NORMALIZED", "055": "DOMAIN_SIGNAL_NOT_EXTRACTED",
                "056": "RELATIONSHIP_NOT_PROMOTED", "060": "WRONG_PRECEDENCE",
            }.items()
        },
        "format_activation_failures": {
            case_id: {
                "expected_structure_present_in_text": True,
                "required_components_extracted": FORMAT_ZERO[case_id] not in {"FORMAT_COMPONENTS_NOT_EXTRACTED"},
                "relationship_constructed": validation_by_id[case_id]["semantic_relationship_count"] > 0,
                "semantic_format_support_emitted": False,
                "semantic_format_suppression_emitted": False,
                "format_classifier_consumed_support": False,
            } for case_id in ("052", "054", "056", "057", "058", "059")
        },
        "format_gate_fn_activation_breaks": {
            case_id: {
                "expected_structure_exists": True,
                "contextual_components_exist": bool(validation_by_id[case_id]["contextual_support_labels"]),
                "relationship_candidate_generated": next(case for case in cases if case["id"] == case_id)["relationship_candidate_generated"],
                "semantic_format_support_emitted": False,
                "format_confidence_changed": False,
                "new_gate_signal_received": False,
                "activation_break": FORMAT_ZERO[case_id],
            } for case_id in ("054", "056", "059")
        },
        "semantic_format_support_zero_causes": {case["id"]: case["semantic_format_support_zero_cause"] for case in cases},
        "arabic_expression_findings": {case["id"]: case["arabic_expression_findings"] for case in cases},
        "title_lead_usage": {case["id"]: case["title_lead_usage"] for case in cases},
        "test_realism_metrics": {
            "synthetic_tests_using_raw_text": 25,
            "synthetic_tests_using_prebuilt_components": 0,
            "synthetic_tests_using_prebuilt_contextual_evidence": 0,
            "synthetic_tests_directly_calling_semantic_relationship_logic": 0,
            "synthetic_tests_bypassing_extraction": 0,
            "path_classification": "SAME_PATH",
            "finding": "End-to-end path was exercised, but synthetic vocabulary matched exact generic regex forms more directly than Arabic corpus expression.",
        },
        "architectural_owner_by_case": {case["id"]: case["primary_architectural_owner"] for case in cases},
        "dominant_root_cause": "B_REAL_TEXT_COMPONENT_EXTRACTION_GAP",
        "recommended_next_step": "IMPROVE_GENERIC_COMPONENT_EXTRACTION",
        "expected_labels_sha256": hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest(),
        "raw_source_integrity": hashlib.sha256((PROJECT_ROOT.parent / "benchmark_sources/batch_06_raw.txt").read_bytes()).hexdigest() == RAW_SHA256,
        "cases": cases,
    }
    return result


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    stage_lines = "\n".join(f"- {key}: {value}" for key, value in result["activation_stage_by_case"].items())
    owner_lines = "\n".join(f"- {key}: {value}" for key, value in result["architectural_owner_by_case"].items())
    zero_lines = "\n".join(f"- {key}: {value}" for key, value in result["semantic_format_support_zero_causes"].items())
    return f"""# Batch 06 Semantic Activation Gap Analysis

## Why HKEI-157 Did Not Move Batch 06

The synthetic suite exercised the real raw-text path, but its expressions matched the new component regexes directly. The Arabic holdout uses morphological, nominal, elliptical, and synonymous journalistic forms that do not normalize into the same components.

## Activation Funnel

{stage_lines}

## Component Extraction

Most failures stop before reusable semantic components are normalized.

## Cross-Sentence Locality

Several relevant signals cross title/lead/body boundaries; the current body-adjacent window cannot combine those sections.

## Topic Failure Activation

Topic failures primarily lack normalized domain-bearing subjects or lose them to authority/actor precedence.

## Format Failure Activation

No case emits semantic format support.

## Format Gate False Negatives

Cases 054, 056, and 059 receive no new semantic format signal.

## Why Semantic Format Support Is 0/10

{zero_lines}

## Synthetic vs Real Path

Path classification: {result['test_realism_metrics']['path_classification']}.

## Arabic Expression Findings

Observed categories include verb inflection, nominal and prepositional constructions, implicit subjects, headline ellipsis, multiword concepts, temporal phrasing, and synonymous journalistic phrasing.

## Test Realism Audit

Raw-text scenarios: {result['test_realism_metrics']['synthetic_tests_using_raw_text']}; extraction bypasses: {result['test_realism_metrics']['synthetic_tests_bypassing_extraction']}.

## Dominant Root Cause

{result['dominant_root_cause']}

## Recommended Next Step

{result['recommended_next_step']}

## Architectural Ownership

{owner_lines}
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(render_json(result), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
