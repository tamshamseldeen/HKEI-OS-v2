"""Diagnose the frozen Batch 05 adjudication-gate errors."""

from collections import Counter
import json
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
ERROR_IDS = ("044", "045", "046", "047", "048", "050")
CONTROL_ID = "049"


CASE_DIAGNOSES = {
    "044": {
        "gate_error_type": "FORMAT_FALSE_NEGATIVE",
        "available_structured_signals": ["FORMAT_LOW_CONFIDENCE", "STANDARD_NEWS_FALLBACK"],
        "missing_structured_signals": ["CAUSE_CONSTRAINT_RESOURCE_DEPLETION_IMPACT_STRUCTURE", "FORMAT_ANALYSIS_SUPPORT"],
        "failure_classes": ["FORMAT_FALSE_NEGATIVE", "GATE_SIGNAL_NOT_AVAILABLE"],
        "primary_owner": "CONTEXTUAL_EVIDENCE",
        "counterfactual_signals": ["FORMAT_STRUCTURE_ABSENT"],
        "architectural_observations": [
            "Neither contextual nor semantic evidence exposed cause, constraint, resource depletion, impact, consequence, interpretation, or FORMAT_ANALYSIS support.",
            "Low format confidence existed, but the missing ANALYSIS distinction was absent upstream; the gate cannot infer it from raw prose without becoming a classifier.",
        ],
    },
    "045": {
        "gate_error_type": "FORMAT_FALSE_NEGATIVE",
        "available_structured_signals": ["FORMAT_LOW_CONFIDENCE", "STANDARD_NEWS_FALLBACK"],
        "missing_structured_signals": ["EXPLANATORY_FRAMING", "MECHANISM_OR_TRANSFORMATION_STRUCTURE", "FORMAT_EXPLAINER_SUPPORT"],
        "failure_classes": ["FORMAT_FALSE_NEGATIVE", "GATE_SIGNAL_NOT_AVAILABLE", "EXPLAINER_SIGNAL_NOT_AVAILABLE"],
        "primary_owner": "FORMAT_CLASSIFIER",
        "counterfactual_signals": ["FORMAT_STRUCTURE_ABSENT"],
        "architectural_observations": [
            "No structured output exposed explanatory framing, mechanism, organizational transformation, or how/why structure.",
            "EXPLAINER_STRUCTURE_UNRESOLVED could not be emitted because no contextual or semantic EXPLAINER target existed upstream.",
        ],
    },
    "046": {
        "gate_error_type": "TOPIC_FALSE_NEGATIVE",
        "available_structured_signals": ["TOPIC_TECHNOLOGY", "TOPIC_MEDIUM_CONFIDENCE", "NO_PRIMARY_SEMANTIC_DOMAIN", "ACTION_TARGETS_OBJECT"],
        "missing_structured_signals": ["METHOD_SUBJECT_RELATIONSHIP", "SCIENCE_OR_BIOLOGICAL_PRIMARY_DOMAIN"],
        "failure_classes": ["TOPIC_FALSE_NEGATIVE", "GATE_POLICY_TOO_STRICT", "GATE_SIGNAL_AVAILABLE_BUT_UNUSED", "TOPIC_MEDIUM_CONFIDENCE_AMBIGUITY", "SPECIFIC_TOPIC_FALSE_CONFIDENCE", "METHOD_SUBJECT_AMBIGUITY_NOT_EXPOSED"],
        "primary_owner": "SHARED_UPSTREAM_AND_GATE",
        "counterfactual_signals": ["MEDIUM_TOPIC_CONFIDENCE_WITHOUT_PRIMARY_DOMAIN", "SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN"],
        "architectural_observations": [
            "MEDIUM topic confidence plus no primary domain was a generic unresolved-domain signal that the gate recorded but did not use to request topic adjudication.",
            "The particular method-versus-subject distinction was not structurally represented: ACTION_TARGETS_OBJECT did not identify a method/tool component or SCIENCE domain. A generic gate can identify unresolved domain ambiguity, but cannot select SCIENCE.",
        ],
    },
    "047": {
        "gate_error_type": "FORMAT_FALSE_NEGATIVE",
        "available_structured_signals": ["CLAIM_UNCERTAIN", "STANDARD_NEWS_FALLBACK"],
        "missing_structured_signals": ["INSTITUTIONAL_CONFLICT", "POLICY_OR_LEGAL_IMPLICATION", "CAUSE_CONSEQUENCE_OR_INTERPRETATION", "FORMAT_ANALYSIS_SUPPORT"],
        "failure_classes": ["FORMAT_FALSE_NEGATIVE", "GATE_SIGNAL_NOT_AVAILABLE", "INSTITUTIONAL_CONFLICT_SIGNAL_NOT_AVAILABLE"],
        "primary_owner": "CONTEXTUAL_EVIDENCE",
        "counterfactual_signals": ["FORMAT_STRUCTURE_ABSENT"],
        "architectural_observations": [
            "Only uncertainty was exposed contextually; no relationship, primary domain, format support, institutional conflict, policy/legal implication, or interpretive structure was available.",
            "The ANALYSIS distinction is missing upstream rather than ignored by the gate.",
        ],
    },
    "048": {
        "gate_error_type": "FORMAT_FALSE_POSITIVE",
        "available_structured_signals": ["CLAIM_UNCERTAIN", "FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT", "SOURCE_TOO_THIN_FOR_ANALYSIS", "STANDARD_NEWS_MEDIUM_CONFIDENCE"],
        "missing_structured_signals": ["PRIMARY_SEMANTIC_DOMAIN", "SEMANTIC_FORMAT_SUPPORT"],
        "failure_classes": ["FORMAT_FALSE_POSITIVE", "PREDICTION_FALSE_ANALYSIS_TRIGGER", "UNCERTAINTY_FALSE_ANALYSIS_TRIGGER"],
        "primary_owner": "GATE",
        "counterfactual_signals": ["PREDICTION_ONLY_ANALYSIS_SUPPORT"],
        "architectural_observations": [
            "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK and CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED caused the format request.",
            "The persisted diagnosis attributes contextual FORMAT_ANALYSIS to prediction, uncertainty, future possibility, and an intelligence estimate, while SOURCE_TOO_THIN_FOR_ANALYSIS shows the final classifier correctly rejected that proxy.",
        ],
    },
    "050": {
        "gate_error_type": "TOPIC_FALSE_NEGATIVE",
        "available_structured_signals": ["TOPIC_EDUCATION_HIGH_CONFIDENCE", "CLAIM_ATTRIBUTED", "NO_PRIMARY_SEMANTIC_DOMAIN", "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP"],
        "missing_structured_signals": ["VIOLENT_INCIDENT_EVENT", "FATALITIES_OR_INJURIES", "POLICE_RESPONSE_OR_INVESTIGATION", "CRIME_PRIMARY_DOMAIN"],
        "failure_classes": ["TOPIC_FALSE_NEGATIVE", "GATE_SIGNAL_NOT_AVAILABLE", "SPECIFIC_TOPIC_FALSE_CONFIDENCE", "EVENT_DOMAIN_AMBIGUITY_NOT_EXPOSED"],
        "primary_owner": "CONTEXTUAL_EVIDENCE",
        "counterfactual_signals": ["SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN", "EVENT_EVIDENCE_WITHOUT_DOMAIN_RESOLUTION"],
        "architectural_observations": [
            "The final topic was specific and HIGH confidence, while contextual evidence exposed attribution only and semantic evidence exposed no event relationship or primary domain.",
            "Violence, casualties, police response, investigation, and CRIME were absent from current structured evidence. Detecting them from text belongs upstream or to the adjudicator, not the gate.",
        ],
    },
    "049": {
        "gate_error_type": "CONTROL_CORRECT",
        "available_structured_signals": ["TOPIC_ECONOMY_HIGH_CONFIDENCE", "TOPIC_ECONOMY", "INDICATOR_DESCRIBES_DOMAIN", "PRIMARY_DOMAIN_ECONOMY", "STANDARD_NEWS_MEDIUM_CONFIDENCE"],
        "missing_structured_signals": [],
        "failure_classes": ["CONTROL_CORRECTLY_AVOIDED"],
        "primary_owner": "GATE",
        "counterfactual_signals": [],
        "architectural_observations": [
            "Title/body signals, structured economic values, contextual topic support, a semantic relationship, and PRIMARY_DOMAIN_ECONOMY aligned with the HIGH-confidence topic.",
            "No ambiguity or format-conflict trigger was present, so NOT_REQUIRED correctly preserved deterministic sufficiency.",
        ],
    },
}


def _load_inputs(batch_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    names = ("editorial_validation.json", "adjudication_gate_shadow.json", "editorial_generalization_analysis.json")
    return tuple(json.loads((batch_root / name).read_text(encoding="utf-8")) for name in names)  # type: ignore[return-value]


def _counterfactuals(validation: dict[str, Any], generalization: dict[str, Any]) -> dict[str, dict[str, int]]:
    general_by_id = {case["id"]: case for case in generalization["cases"]}
    predicates: dict[str, Callable[[dict[str, Any]], bool]] = {
        "MEDIUM_TOPIC_CONFIDENCE_WITHOUT_PRIMARY_DOMAIN": lambda c: c["topic_confidence"] == "MEDIUM" and not c["semantic_primary_domain_candidates"],
        "SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN": lambda c: c["predicted_topic"] != "GENERAL" and not c["semantic_primary_domain_candidates"],
        "CONTEXTUAL_ANALYSIS_SUPPORT_WITH_FORMAT_MISMATCH": lambda c: "FORMAT_ANALYSIS" in c["contextual_support_labels"] and not c["format_match"],
        "FORMAT_STRUCTURE_ABSENT": lambda c: not c["format_match"] and not c["semantic_format_support"] and not any(label.startswith("FORMAT_") for label in c["contextual_support_labels"]),
        "PREDICTION_ONLY_ANALYSIS_SUPPORT": lambda c: "FORMAT_ANALYSIS" in c["contextual_support_labels"] and "SOURCE_TOO_THIN_FOR_ANALYSIS" in c["format_warnings"],
        "EVENT_EVIDENCE_WITHOUT_DOMAIN_RESOLUTION": lambda c: "EVENT_DOMAIN_MODEL_GAP" in general_by_id[c["id"]]["failure_classes"] and not c["semantic_primary_domain_candidates"],
    }
    result = {}
    for name, predicate in predicates.items():
        cases = [case for case in validation["cases"] if predicate(case)]
        result[name] = {
            "cases_triggered": len(cases),
            "topic_mismatches_triggered": sum(not case["topic_match"] for case in cases),
            "format_mismatches_triggered": sum(not case["format_match"] for case in cases),
            "matched_cases_triggered": sum(case["full_match"] for case in cases),
        }
    return result


def analyze_gate_errors(*, batch_root: Path = BATCH_ROOT) -> dict[str, Any]:
    validation, shadow, generalization = _load_inputs(batch_root)
    assert validation["case_count"] == shadow["case_count"] == generalization["case_count"] == 10
    shadow_by_id = {case["id"]: case for case in shadow["cases"]}
    cases = []
    for case_id in (*ERROR_IDS, CONTROL_ID):
        frozen = shadow_by_id[case_id]
        case = {
            "id": case_id,
            "gate_error_type": CASE_DIAGNOSES[case_id]["gate_error_type"],
            "observed_scope": frozen["gate_scope"],
            "trigger_signals": frozen["trigger_signals"],
            **{key: value for key, value in CASE_DIAGNOSES[case_id].items() if key != "gate_error_type"},
        }
        cases.append(case)
    errors = cases[:-1]
    failure_counts = Counter(item for case in errors for item in case["failure_classes"])
    owner_counts = Counter(case["primary_owner"] for case in errors)
    return {
        "cases_analyzed": len(errors),
        "topic_false_negatives": ["046", "050"],
        "format_false_negatives": ["044", "045", "047"],
        "format_false_positives": ["048"],
        "failure_class_counts": dict(sorted(failure_counts.items())),
        "primary_owner_counts": dict(sorted(owner_counts.items())),
        "signals_available_but_unused": ["046"],
        "signals_not_available": ["044", "045", "047", "050"],
        "counterfactual_signal_analysis": _counterfactuals(validation, generalization),
        "control": cases[-1],
        "cases": errors,
        "architectural_principle": "The gate must not become a second classifier. Reading raw text, recognizing new domain vocabulary, interpreting event semantics, or deciding whether prose is analytical belongs upstream or to the adjudicator.",
        "gate_precision_recall_conclusion": "Favor recall enough to surface unresolved deterministic errors, but constrain it with structured ambiguity evidence because false positives incur provider cost; Batch 05 supports a measured recall increase, not unconditional low-confidence or contextual-analysis triggers.",
        "recommended_next_step_category": "D",
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(a: dict[str, Any]) -> str:
    case_by_id = {case["id"]: case for case in [*a["cases"], a["control"]]}
    lines = [
        "# Batch 05 Adjudication Gate Error Analysis", "", "## Baseline", "",
        "Topic:", "TP 7", "FP 0", "TN 1", "FN 2", "", "Topic Precision:", "100%", "", "Topic Recall:", "77.78%", "",
        "Format:", "TP 1", "FP 1", "TN 5", "FN 3", "", "Format Precision:", "50%", "", "Format Recall:", "25%", "",
    ]
    for heading, ids in (("Topic False Negatives", ["046", "050"]), ("Format False Negatives", ["044", "045", "047"]), ("Format False Positive", ["048"]), ("Control", ["049"])):
        lines.extend((f"## {heading}", ""))
        for case_id in ids:
            c = case_by_id[case_id]
            lines.extend((f"### {case_id}", "", f'Scope: {c["observed_scope"]}', "", f'Triggers: {", ".join(c["trigger_signals"]) or "None"}', "", f'Failure classes: {", ".join(c["failure_classes"])}', ""))
            lines.extend(f"- {observation}" for observation in c["architectural_observations"])
            lines.append("")
    lines.extend(("## Gate vs Upstream Responsibility", "", "| ID | Error | Primary Owner | Signal Available? | Missing Distinction |", "| --- | --- | --- | --- | --- |"))
    for c in [*a["cases"], a["control"]]:
        availability = "N/A" if c["id"] == "049" else ("Yes, but misused" if c["id"] == "048" else "Yes, but unused" if c["id"] in a["signals_available_but_unused"] else "No")
        lines.append(f'| {c["id"]} | {c["gate_error_type"]} | {c["primary_owner"]} | {availability} | {", ".join(c["missing_structured_signals"]) or "None"} |')
    lines.extend(("", a["architectural_principle"], "", "## Counterfactual Signals", "", "| Signal | Cases Triggered | Topic Mismatches | Format Mismatches | Matched Cases |", "| --- | ---: | ---: | ---: | ---: |"))
    for signal, m in a["counterfactual_signal_analysis"].items():
        lines.append(f'| {signal} | {m["cases_triggered"]} | {m["topic_mismatches_triggered"]} | {m["format_mismatches_triggered"]} | {m["matched_cases_triggered"]} |')
    lines.extend(("", "These are conceptual diagnostics only. FORMAT_STRUCTURE_ABSENT and EVENT_EVIDENCE_WITHOUT_DOMAIN_RESOLUTION rely on persisted diagnostic truth and are not deployable gate predicates.", "", "## Gate Precision vs Recall", "", a["gate_precision_recall_conclusion"], "", "## Recommended Next Step", "", "D. Combine refinement using existing structured ambiguity (A), additional upstream evidence (B), and adjudicator/provider architecture for semantics that should not be inferred by the gate (C).", ""))
    return "\n".join(lines)


def main() -> int:
    analysis = analyze_gate_errors()
    (BATCH_ROOT / "adjudication_gate_error_analysis.json").write_text(render_json(analysis), encoding="utf-8")
    (BATCH_ROOT / "adjudication_gate_error_analysis.md").write_text(render_markdown(analysis), encoding="utf-8")
    print(f'Cases analyzed: {analysis["cases_analyzed"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
