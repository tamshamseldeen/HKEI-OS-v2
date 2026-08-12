"""Diagnose the single persisted residual false-sufficient assessment offline."""

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_adjudication_unresolved_evidence_trigger_analysis import parse_source  # noqa: E402
from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_semantic_candidate_assessment_shadow import analyze as shadow_analyze  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import ExperimentalSemanticEditorialAnalysisWorkflow  # noqa: E402


PARITY_PATH = PROJECT_ROOT / "benchmark/semantic_candidate_assessment_parity_audit.json"
SHADOW_PATH = PROJECT_ROOT / "benchmark/semantic_candidate_assessment_shadow.json"
OUTPUT_JSON = PROJECT_ROOT / "benchmark/residual_false_sufficient_analysis.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark/residual_false_sufficient_analysis.md"


def _expected(case: dict[str, Any], item: dict[str, Any]) -> str | None:
    return case["expected_topic"] if item["candidate_group"] == "TOPIC_LIKE" else case["expected_format"] if item["candidate_group"] == "FORMAT_LIKE" else None


def _residuals(shadow: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (case, item) for case in shadow["case_inventory"] for item in case["assessments"]
        if _expected(case, item) is not None
        and item["candidate"] != _expected(case, item)
        and item["sufficiency"] == "SUFFICIENT"
    ]


def _symbolic_path(case: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    source_path = PROJECT_ROOT / "benchmark" / case["batch"] / case["id"] / "source.md"
    source = parse_source(source_path)
    pipeline = ExperimentalSemanticEditorialAnalysisWorkflow().process(**_source_fields(source))
    contextual = [
        {
            "stage": "CONTEXTUAL_EVIDENCE", "section": item.source_section.value,
            "sentence_index": item.sentence_index, "role": item.role.value,
            "strength": item.strength.value, "reason_code": item.reason_code,
            "supports": list(item.supports), "suppresses": list(item.suppresses),
        }
        for item in pipeline.contextual_evidence.all_items
        if f"TOPIC_{target['candidate']}" in item.supports
    ]
    relationships = [
        {
            "stage": "SEMANTIC_RELATIONSHIP", "section": item.source_section.value,
            "sentence_index": item.sentence_index,
            "relationship_type": item.relationship_type.value,
            "subject_component": item.subject_component.value,
            "object_component": item.object_component.value,
            "strength": item.strength.value, "reason_code": item.reason_code,
            "supports": list(item.supports), "suppresses": list(item.suppresses),
            "evidence_indexes": list(item.evidence_indexes),
        }
        for item in pipeline.semantic_evidence.relationships
        if f"PRIMARY_DOMAIN_{target['candidate']}" in item.supports
        or f"TOPIC_{target['candidate']}" in item.supports
    ]
    upstream_other = sorted({
        label for item in pipeline.contextual_evidence.all_items for label in item.supports
        if label.startswith("COMPONENT_") and target["candidate"] not in label
    })
    return {
        "normalized_evidence": {
            "source_sections_present": sorted({item["section"] for item in contextual + relationships}),
            "raw_text_persisted": False,
        },
        "semantic_components": upstream_other,
        "contextual_candidate_support": contextual,
        "semantic_relationships": relationships,
        "candidate_support": target["supporting_relationship_types"],
        "candidate_suppression": target["suppressing_relationship_types"],
        "role_basis": target["role_basis"],
        "competition_detection": target["competing_candidates"],
        "strength_decision": target["strength"],
        "sufficiency_decision": target["sufficiency"],
        "eligibility_stage": "STRENGTH_FROM_REPEATED_CONTEXTUAL_SUBJECT_SUPPORT_PLUS_ACTION_OBJECT_RELATIONSHIP",
    }


def analyze() -> dict[str, Any]:
    parity = json.loads(PARITY_PATH.read_text(encoding="utf-8"))
    persisted_shadow = json.loads(SHADOW_PATH.read_text(encoding="utf-8"))
    shadow = shadow_analyze()
    residuals = _residuals(shadow)
    if len(residuals) != parity["false_sufficient_count"]:
        raise ValueError("persisted residual count does not match parity audit")
    if len(residuals) != 1:
        raise ValueError("analysis requires exactly one persisted residual")
    case, target = residuals[0]
    persisted_keys = {
        (item_case["batch"], item_case["id"], item["candidate"])
        for item_case in persisted_shadow["case_inventory"]
        for item in item_case["assessments"]
    }
    if (case["batch"], case["id"], target["candidate"]) not in persisted_keys:
        raise ValueError("target is not present in persisted candidate assessments")
    expected = _expected(case, target)
    path = _symbolic_path(case, target)
    expected_item = next((item for item in case["assessments"] if item["candidate_group"] == target["candidate_group"] and item["candidate"] == expected), None)

    contextual = path["contextual_candidate_support"]
    relationships = path["semantic_relationships"]
    independence = []
    for index, left in enumerate(contextual + relationships):
        for right in (contextual + relationships)[index + 1:]:
            same_reason = left["reason_code"] == right["reason_code"]
            same_section_sentence = left["section"] == right["section"] and left["sentence_index"] == right["sentence_index"]
            classification = "SEMANTIC_DUPLICATE" if same_reason and same_section_sentence else "DERIVED_FROM_SAME_SIGNAL" if same_reason else "INDEPENDENT"
            independence.append({
                "left": f"{left['stage']}:{left['reason_code']}:{left['section']}:{left['sentence_index']}",
                "right": f"{right['stage']}:{right['reason_code']}:{right['section']}:{right['sentence_index']}",
                "classification": classification,
            })

    controls = []
    candidates = []
    for control_case in shadow["case_inventory"]:
        for item in control_case["assessments"]:
            if item["candidate_group"] == target["candidate_group"] and item["candidate"] == _expected(control_case, item) and item["sufficiency"] == "SUFFICIENT":
                overlap = len(set(item["role_basis"]) & set(target["role_basis"])) + len(set(item["supporting_relationship_types"]) & set(target["supporting_relationship_types"]))
                candidates.append((-
                    overlap, control_case["batch"], control_case["id"], item
                ))
    for _, batch, case_id, item in sorted(candidates)[:3]:
        controls.append({
            "batch": batch, "case_id": case_id, "candidate": item["candidate"],
            "role_quality": "CENTRAL_SUBJECT_BEARING" if "SUBJECT" in item["role_basis"] else "MIXED",
            "independent_evidence_count": len(item["supporting_relationship_types"]),
            "support_types": item["supporting_relationship_types"],
            "suppression": item["suppressing_relationship_types"],
            "competition": item["competing_candidates"],
            "structural_completeness": "STRUCTURE_COMPLETE",
            "strength": item["strength"], "sufficiency": item["sufficiency"],
        })

    target_record = {
        "batch": case["batch"], "case_id": case["id"],
        "corpus_status": parity["batch_metrics"][case["batch"]]["scientific_status"],
        "candidate": target["candidate"], "candidate_group": target["candidate_group"],
        "expected_label": expected, "direction": target["direction"],
        "strength": target["strength"], "sufficiency": target["sufficiency"],
        "supporting_relationship_types": target["supporting_relationship_types"],
        "suppressing_relationship_types": target["suppressing_relationship_types"],
        "role_basis": target["role_basis"], "competing_candidates": target["competing_candidates"],
        "warnings": target["warnings"],
    }
    return {
        "false_sufficient_count": len(residuals), "target_assessment": target_record,
        "assessment_path": path,
        "evidence_independence_analysis": {
            "pair_classifications": independence,
            "finding": "CONTEXTUAL_OCCURRENCES_SHARE_ONE_TECHNOLOGY_SIGNAL_FAMILY_AND_ARE_NOT_FULLY_INDEPENDENT",
            "duplicate_protection_failure": "HIERARCHICAL_DUPLICATION_NOT_DISCOUNTED",
        },
        "role_quality": {
            "classification": "MIXED",
            "finding": "TOOL_METHOD_TECHNOLOGY_MENTIONS_ARE_NORMALIZED_AS_SUBJECT_WHILE_ACTION_OBJECT_SUPPORT_IS_NOT_DOMAIN_BEARING",
        },
        "directionality_analysis": [
            {"relationship_type": "CONTEXTUAL_TECHNOLOGY_CONTEXT_PHRASE", "classification": "OVERGENERALIZED_SUPPORT"},
            {"relationship_type": "ACTION_TARGETS_OBJECT", "classification": "OVERGENERALIZED_SUPPORT"},
        ],
        "suppression_analysis": {
            "classification": "SUPPRESSION_NOT_MAPPED",
            "finding": "UPSTREAM_NON_TECHNOLOGY_SUBJECT_COMPONENT_EXISTS_BUT_DOES_NOT_SUPPRESS_OR_COMPETE_WITH_TECHNOLOGY",
        },
        "competition_analysis": {
            "expected_candidate_assessment_exists": expected_item is not None,
            "expected_candidate_strength": expected_item["strength"] if expected_item else "NONE",
            "expected_candidate_sufficiency": expected_item["sufficiency"] if expected_item else "NONE",
            "expected_candidate_relationship_support": expected_item["supporting_relationship_types"] if expected_item else [],
            "expected_candidate_should_be_competitor": True,
            "classification": "EXPECTED_CANDIDATE_MISSING" if expected_item is None else "COMPETITOR_NOT_DETECTED",
        },
        "structural_completeness": {
            "classification": "STRUCTURE_MISIDENTIFIED",
            "finding": "CENTRAL_SUBJECT_DOMAIN_SUPPORT_IS_NOT ESTABLISHED_FOR_THE_TECHNOLOGY_CANDIDATE",
        },
        "strength_audit": {
            "contributing_factors": ["MULTIPLE_CONTEXTUAL_SUBJECT_RECORDS", "ACTION_OBJECT_RELATIONSHIP", "NO_COMPETITOR", "NO_SUPPRESSION"],
            "classification": "MIXED_INFLATION",
        },
        "sufficiency_prerequisite_audit": {
            "SUPPORT_DIRECTION": "PASS", "STRONG_STRENGTH": "PASS",
            "STRUCTURAL_COMPLETENESS": "FAIL", "CENTRAL_ROLE": "FAIL",
            "NO_MATERIAL_SUPPRESSION": "FAIL", "NO_MEANINGFUL_COMPETITOR": "FAIL",
            "INDEPENDENT_EVIDENCE": "FAIL", "COHERENT_EVIDENCE": "FAIL",
        },
        "expected_label_clarity": "EXPECTED_LABEL_CLEAR",
        "true_sufficient_controls": controls,
        "primary_failure_class": "DIRECTIONAL_MAPPING_OVERGENERALIZATION",
        "secondary_failure_classes": ["DUPLICATE_INDEPENDENCE_FAILURE", "ROLE_BASIS_OVERCLAIM", "MISSING_COMPETITOR", "MISSING_SUPPRESSION", "STRENGTH_CALIBRATION_ERROR"],
        "generic_counterfactual_fix": "TIGHTEN_DIRECTIONAL_MAPPING",
        "overcorrection_risk": {
            "TIGHTEN_DIRECTIONAL_MAPPING": "MODERATE",
            "TIGHTEN_EVIDENCE_INDEPENDENCE": "MODERATE",
            "TIGHTEN_ROLE_BASIS_REQUIREMENT": "HIGH",
            "PROPAGATE_SUPPRESSION": "MODERATE",
            "STRENGTHEN_COMPETITOR_DETECTION": "LOW",
            "TIGHTEN_SUFFICIENCY_FINAL_CHECK": "HIGH",
            "safest_minimal_change": "STRENGTHEN_COMPETITOR_DETECTION",
        },
        "integration_safety": "SHADOW_ONLY", "batch_07_required": True,
        "provider_calls": 0,
    }


def render_markdown(result: dict[str, Any]) -> str:
    target = result["target_assessment"]
    return f"""# Residual False-Sufficient Analysis

Residual count: {result['false_sufficient_count']}

Target: {target['batch']} / {target['case_id']} / {target['candidate']}

Primary failure: {result['primary_failure_class']}

Generic counterfactual: {result['generic_counterfactual_fix']}

Integration safety: {result['integration_safety']}

Provider calls: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
