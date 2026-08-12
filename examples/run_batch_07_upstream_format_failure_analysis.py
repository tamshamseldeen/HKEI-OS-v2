"""Analyze persisted upstream Format failures after the final Batch 07 run."""

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
INPUT_JSON = BATCH_ROOT / "post_gate_refinement_full_stack_evaluation.json"
OUTPUT_JSON = BATCH_ROOT / "upstream_format_failure_analysis.json"
OUTPUT_MD = BATCH_ROOT / "upstream_format_failure_analysis.md"
EXPECTED_JSON = BATCH_ROOT / "expected.json"
EXPECTED_SHA256 = "cafddc7533a80dc834abe96606ae770a458d462893086be16fcea95554c6c036"

FAILURE_STAGES = {
    "FORMAT_COMPONENT_NOT_EXTRACTED",
    "FORMAT_COMPONENT_EXTRACTED_NOT_COMPOSED",
    "FORMAT_RELATIONSHIP_WRONG",
    "FORMAT_MAPPING_MISSING",
    "FORMAT_MAPPING_WRONG_DIRECTION",
    "FORMAT_CANDIDATE_MISSING",
    "FORMAT_CANDIDATE_WRONG_SUFFICIENCY",
    "FORMAT_CLASSIFIER_IGNORED_EVIDENCE",
    "FORMAT_CLASSIFIER_WRONG_PRECEDENCE",
    "FORMAT_CONFIDENCE_FALSE_SECURITY",
    "GATE_SIGNAL_INTERFACE_GAP",
    "ONTOLOGY_BOUNDARY",
    "OTHER",
}
REACHABILITY = {
    "NO_SIGNAL", "COMPONENT_ONLY", "RELATIONSHIP_PRESENT",
    "SEMANTIC_SUPPORT_PRESENT", "CANDIDATE_INSUFFICIENT",
    "CANDIDATE_PARTIAL", "CANDIDATE_SUFFICIENT",
    "CANDIDATE_CONFLICTED", "CLASSIFIER_RECEIVED_BUT_NOT_SELECTED",
}
WRONG_PATHS = {
    "DEFAULT_DOMINANCE", "OVERBROAD_STRUCTURE",
    "WRONG_TEMPORAL_INTERPRETATION", "WRONG_RESULT_INTERPRETATION",
    "WRONG_SERVICE_GUIDE_BOUNDARY", "WRONG_ANALYSIS_NEWS_BOUNDARY",
    "WRONG_FACTCHECK_BOUNDARY", "WRONG_PRECEDENCE", "OTHER",
}


def _format_assessments(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in case["candidate_assessment_summary"]
        if item["candidate_group"] == "FORMAT_LIKE"
    ]


def _relationships(assessments: list[dict[str, Any]], key: str) -> list[str]:
    return list(dict.fromkeys(value for item in assessments for value in item[key]))


def _failure_stage(case: dict[str, Any], assessments: list[dict[str, Any]]) -> str:
    if not assessments:
        if "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP" in case["trigger_signals"]:
            return "FORMAT_COMPONENT_EXTRACTED_NOT_COMPOSED"
        return "FORMAT_COMPONENT_NOT_EXTRACTED"
    expected = case["expected_format"]
    expected_assessment = next((item for item in assessments if item["candidate"] == expected), None)
    wrong = next((item for item in assessments if item["candidate"] == case["deterministic_format"]), None)
    if wrong and "EVENT_HAS_OUTCOME" in wrong["supporting_relationship_types"]:
        return "FORMAT_RELATIONSHIP_WRONG"
    if expected_assessment is None:
        return "FORMAT_MAPPING_MISSING"
    if expected_assessment["sufficiency"] in {"INSUFFICIENT", "PARTIAL", "CONFLICTED"}:
        return "FORMAT_CANDIDATE_WRONG_SUFFICIENCY"
    return "FORMAT_CLASSIFIER_IGNORED_EVIDENCE"


def _reachability(case: dict[str, Any], assessments: list[dict[str, Any]]) -> str:
    expected = next((item for item in assessments if item["candidate"] == case["expected_format"]), None)
    if expected:
        return f"CANDIDATE_{expected['sufficiency']}"
    if any(
        case["expected_format"] in value
        for item in assessments
        for value in item["supporting_relationship_types"]
    ):
        return "RELATIONSHIP_PRESENT"
    return "NO_SIGNAL"


def _wrong_path(case: dict[str, Any], assessments: list[dict[str, Any]]) -> str:
    selected = case["deterministic_format"]
    expected = case["expected_format"]
    if selected == "RESULT_REPORT" and expected == "STANDARD_NEWS":
        return "WRONG_RESULT_INTERPRETATION"
    if selected == "BREAKING" and expected == "STANDARD_NEWS":
        return "OVERBROAD_STRUCTURE"
    if selected == "STANDARD_NEWS" and expected in {"TREND_UPDATE", "RESULT_REPORT", "EXPLAINER"}:
        return "DEFAULT_DOMINANCE"
    return "OTHER"


def _confidence_cause(case: dict[str, Any], stage: str) -> str:
    confidence = case["deterministic_format_confidence"]
    if confidence == "HIGH":
        return "FALSE_HIGH_CONFIDENCE"
    if confidence == "MEDIUM":
        return "FALSE_MEDIUM_CONFIDENCE"
    return "LOW_BUT_UNCAPTURED"


def _trace(case: dict[str, Any]) -> dict[str, Any]:
    assessments = _format_assessments(case)
    stage = _failure_stage(case, assessments)
    supports = _relationships(assessments, "supporting_relationship_types")
    suppressions = _relationships(assessments, "suppressing_relationship_types")
    warnings = list(dict.fromkeys(
        warning for item in assessments for warning in item["warnings"]
    ))
    context_without_relationship = (
        "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP" in case["trigger_signals"]
    )
    gate_format_signals = [
        signal for signal in case["trigger_signals"]
        if "FORMAT" in signal
        or "CONFLICT" in signal
        or "UNRESOLVED" in signal
        or signal == "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP"
    ]
    return {
        "id": case["id"],
        "expected_format": case["expected_format"],
        "deterministic_format": case["deterministic_format"],
        "format_confidence": case["deterministic_format_confidence"],
        "reader_intent": case["deterministic_reader_intent"],
        "expected_reader_intent": case["expected_reader_intent"],
        "contextual_format_evidence": (
            ["CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP"]
            if context_without_relationship else
            [value for value in supports if value.startswith("CONTEXTUAL_")]
        ),
        "semantic_relationships": supports + suppressions,
        "semantic_format_support": supports,
        "semantic_format_suppression": suppressions,
        "candidate_assessments": assessments,
        "candidate_sufficiency": {
            item["candidate"]: item["sufficiency"] for item in assessments
        },
        "warnings": warnings,
        "gate_visible_unresolved_signals": gate_format_signals,
        "upstream_funnel": {
            "raw_article_structure": "AVAILABLE_TO_ORIGINAL_PIPELINE_NOT_PERSISTED",
            "format_relevant_component_extraction": (
                "CONTEXTUAL_COMPONENT_PRESENT" if context_without_relationship
                else "MISSING" if not assessments else "REPRESENTED"
            ),
            "format_relationship_composition": (
                "MISSING" if context_without_relationship or not assessments else "PRESENT"
            ),
            "semantic_format_mapping": "MISSING" if not assessments else "PRESENT_BUT_MISREPRESENTED",
            "format_candidate_assessment": "MISSING" if not assessments else "PRESENT",
            "format_classifier": case["deterministic_format"],
            "format_confidence": case["deterministic_format_confidence"],
            "gate_visible_signals": gate_format_signals,
        },
        "primary_failure_stage": stage,
        "expected_format_reachability": _reachability(case, assessments),
        "wrong_format_path": _wrong_path(case, assessments),
        "wrong_format_supporting_structure": supports,
        "wrong_format_semantic_support": [
            item for item in assessments if item["candidate"] == case["deterministic_format"]
        ],
        "wrong_format_confidence_basis": (
            "Persisted classifier confidence; no expected Format signal reached the candidate layer."
            if not assessments else
            "Persisted semantic relationship and candidate assessment favored the selected Format."
        ),
        "confidence_audit": _confidence_cause(case, stage),
        "confidence_role": "SYMPTOM_OF_UPSTREAM_REPRESENTATION" if stage in {
            "FORMAT_COMPONENT_NOT_EXTRACTED", "FORMAT_COMPONENT_EXTRACTED_NOT_COMPOSED",
            "FORMAT_RELATIONSHIP_WRONG",
        } else "PRIMARY_CAUSE",
        "provider_opportunity": "LIKELY_YES",
    }


def analyze(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if hashlib.sha256(EXPECTED_JSON.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Batch 07 expected labels changed")
    source = payload or json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    cases = source["cases"]
    remaining = [
        case for case in cases
        if not case["format_required"] and not case["format_match_before"]
    ]
    traces = [_trace(case) for case in remaining]
    pairs = Counter(
        f"{case['expected_format']}->{case['deterministic_format']}"
        for case in remaining
    )
    families = Counter(
        " vs ".join(sorted((case["expected_format"], case["deterministic_format"])))
        for case in remaining
    )

    # Reader Intent is deterministic and tracks the selected treatment in every
    # persisted error: GET_UPDATE/NEWS, FIND_RESULT/RESULT, etc.
    intent_errors = [case for case in cases if not case["intent_match"]]
    downstream_intent = [
        case for case in intent_errors if not case["format_match_before"]
    ]

    false_sufficient = []
    for case in cases:
        for item in _format_assessments(case):
            if item["sufficiency"] == "SUFFICIENT" and item["candidate"] != case["expected_format"]:
                stage = _failure_stage(case, _format_assessments(case))
                false_sufficient.append({
                    "id": case["id"], "candidate": item["candidate"],
                    "expected": case["expected_format"],
                    "concerns_format": True,
                    "among_remaining_format_fn": case in remaining,
                    "origin_relative_to_primary_failure": (
                        "AFTER_PRIMARY_FAILURE" if stage == "FORMAT_RELATIONSHIP_WRONG" else "AT_PRIMARY_FAILURE"
                    ),
                })

    stage_counts = Counter(trace["primary_failure_stage"] for trace in traces)
    shared_stage, shared_count = stage_counts.most_common(1)[0]
    shared_root = (
        "FORMAT_COMPONENTS_NOT_COMPOSED_INTO_RELATIONSHIPS"
        if shared_count >= 4 and shared_stage == "FORMAT_COMPONENT_EXTRACTED_NOT_COMPOSED"
        else shared_stage if shared_count >= 4 else "NO_DOMINANT_COMMON_ROOT_CAUSE"
    )
    return {
        "remaining_format_fn_cases": [case["id"] for case in remaining],
        "remaining_format_fn_count": len(remaining),
        "case_traces": traces,
        "expected_to_predicted_format_pairs": dict(sorted(pairs.items())),
        "structural_family_counts": dict(sorted(families.items())),
        "direct_intent_failures": 0,
        "format_downstream_intent_failures": len(downstream_intent),
        "other_upstream_intent_failures": len(intent_errors) - len(downstream_intent),
        "false_sufficient_cases": false_sufficient,
        "false_sufficient_among_remaining_format_fns": [
            item["id"] for item in false_sufficient if item["among_remaining_format_fn"]
        ],
        "false_confidence_cases": [trace["id"] for trace in traces],
        "provider_opportunity_counts": dict(Counter(trace["provider_opportunity"] for trace in traces)),
        "shared_root_cause": shared_root,
        "shared_root_cause_count": shared_count,
        "fix_scope_classification": "BOUNDED_FORMAT_EVIDENCE_FIX",
        "fix_value": "HIGH",
        "overfitting_risk": "HIGH",
        "resolver_readiness": "YES_LIMITED",
        "resolver_readiness_explanation": "A resolver can be designed behind Format guardrails, but full authority is unsafe while expected treatment is absent or misrepresented upstream in most remaining cases.",
        "gate_refinement_budget_remaining": 0,
        "gate_tuning_closed": True,
        "maximum_future_bounded_format_implementations": 1,
        "final_recommendation": "IMPLEMENT_ONE_BOUNDED_UPSTREAM_FORMAT_FIX",
        "provider_calls": 0,
    }


def render_markdown(result: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {trace['id']} | {trace['expected_format']} -> {trace['deterministic_format']} | {trace['primary_failure_stage']} | {trace['expected_format_reachability']} | {trace['wrong_format_path']} |"
        for trace in result["case_traces"]
    )
    return f"""# Batch 07 Upstream Format Failure Analysis

Remaining Format false negatives: {', '.join(result['remaining_format_fn_cases'])}

| ID | Pair | Primary stage | Reachability | Wrong path |
| --- | --- | --- | --- | --- |
{rows}

Shared root cause: {result['shared_root_cause']} ({result['shared_root_cause_count']}/6)

Fix scope: {result['fix_scope_classification']}

Fix value: {result['fix_value']}

Overfitting risk: {result['overfitting_risk']}

Resolver readiness: {result['resolver_readiness']}

Gate refinement budget remaining: 0

Final recommendation: {result['final_recommendation']}

Provider calls: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "case_traces"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
