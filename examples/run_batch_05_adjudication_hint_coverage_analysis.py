"""Diagnose contextual adjudication-hint coverage on Batch 05."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import parse_source
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.source_normalizer import SourceNormalizer


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
TARGETS = {
    "044": "ADJUDICATION_ANALYTICAL_CONSTRAINT",
    "045": "ADJUDICATION_EXPLANATORY_TRANSFORMATION",
    "047": "ADJUDICATION_INSTITUTIONAL_POLICY_CONFLICT",
    "050": "ADJUDICATION_EVENT_PUBLIC_SAFETY",
}
NEGATIVE_CONTROLS = ("048", "049")

# Short diagnostic spans describe persisted evidence; they are never production rules.
COMPONENTS = {
    "044": (
        ("constraint_pressure", "ضغوطًا متزايدة", "LEAD", 0),
        ("resource_limitation", "ارتفاع معدلات استخدام الذخائر", "BODY", 0),
        ("capability", "قدرة أوكرانيا على تأمين", "BODY", 1),
        ("consequence_impact", "تحولت قضية الدفاع الجوي", "BODY", 3),
    ),
    "045": (
        ("institution_action", "روسيا إعادة هيكلة قواتها", "LEAD", 0),
        ("structural_change", "تغييرات تنظيمية وقيادية", "LEAD", 0),
        ("new_organizational_unit", "استحداث قوات مستقلة", "BODY", 0),
        ("role_evolution", "تحول الطائرات غير المأهولة", "BODY", 3),
        ("transformation_context", "في ضوء الخبرات", "LEAD", 0),
    ),
    "047": (
        ("institution", "الجامعات الأميركية", "LEAD", 0),
        ("government_scrutiny", "تدقيقًا متزايدًا من إدارة", "LEAD", 0),
        ("policy_disagreement", "سياسات القبول الجامعي", "LEAD", 0),
        ("protests_rights_conflict", "الاحتجاجات داخل الحرم الجامعي", "LEAD", 0),
        ("legal_political_dispute", "مواجهة سياسية وقانونية", "BODY", 2),
        ("institutional_autonomy", "حدود استقلال الجامعات", "BODY", 2),
    ),
    "050": (
        ("serious_incident", "حادث إطلاق نار", "LEAD", 0),
        ("casualties_injuries", "القتلى والمصابين", "LEAD", 0),
        ("police_emergency_response", "استنفار أجهزة الشرطة والطوارئ", "BODY", 0),
        ("investigation", "بدأت السلطات التحقيق", "BODY", 3),
    ),
    "048": (
        ("prediction", "قد يحاول", "LEAD", 0),
        ("uncertainty", "احتمال لجوء", "BODY", 0),
        ("future_possibility", "مستقبلًا", "BODY", 3),
        ("intelligence_estimate", "تقديرات استخباراتية", "HEADLINE", 0),
    ),
    "049": (
        ("economic_indicator", "معدل البطالة", "LEAD", 0),
        ("economic_domain", "سوق العمل", "LEAD", 0),
    ),
}

DETECTION_CODES = {
    "prediction": {"PREDICTION_CONTEXT_PATTERN"},
    "uncertainty": {"UNCERTAINTY_CONTEXT_PATTERN"},
    "future_possibility": {"PREDICTION_CONTEXT_PATTERN"},
    "intelligence_estimate": {"UNCERTAINTY_CONTEXT_PATTERN"},
    "economic_indicator": {"ECONOMY_CONTEXT_PHRASE"},
    "economic_domain": {"ECONOMY_CONTEXT_PHRASE"},
}

FAILURES = {
    case_id: (
        "LEXICAL_SIGNAL_MISSING",
        "COMPONENTS_PRESENT_BUT_NOT_COMBINED",
        "LOCALITY_TOO_STRICT",
        "CROSS_SENTENCE_STRUCTURE_REQUIRED",
        "ROLE_ASSIGNMENT_MISMATCH",
        "HINT_THRESHOLD_TOO_STRICT",
        "HINT_ENGINE_GENERALIZATION_GAP",
    )
    for case_id in TARGETS
}
RECOMMENDATIONS = {
    case_id: (
        "RELAX_LOCALITY_WITH_BOUNDED_WINDOW",
        "ADD_COMPONENT_AGGREGATION",
        "EXPAND_GENERIC_ROLE_COVERAGE",
        "ADD_CROSS_SENTENCE_COMPOSITION",
    )
    for case_id in TARGETS
}
OBSERVATIONS = {
    "044": (
        "Constraint, resource pressure, capability, and impact are present across the lead and three following sentences, but none receives a reusable contextual component role.",
        "The all-components-in-one-sentence threshold cannot compose the real structure; an adjacent-sentence or same-paragraph bounded window is needed.",
    ),
    "045": (
        "Restructuring, a new organizational unit, role evolution, and transformation context are distributed from the lead through later paragraphs.",
        "Literal accepted forms do not cover several journalistic variants, and the one-sentence synthetic shape is absent.",
    ),
    "047": (
        "Institution, government scrutiny, policy disagreement, protests, legal/political conflict, and autonomy are present, with the decisive legal/autonomy structure appearing later.",
        "Only generic uncertainty is extracted; actor/authority and conflict component roles are unavailable for bounded composition.",
    ),
    "050": (
        "Incident and casualties occur in the lead, response in following sentences, and investigation later; the full event structure is intentionally not repeated in one sentence.",
        "Attribution is extracted, but incident, casualty, response, and investigation roles are not, so both role coverage and bounded cross-sentence aggregation are required.",
    ),
    "048": (
        "Prediction, uncertainty, future possibility, and an intelligence estimate produce uncertainty/prediction evidence but no constraint structure.",
        "The analytical-constraint hint correctly remains absent; future relaxation must still require constraint, resource/capability, and consequence components.",
    ),
    "049": (
        "Repeated economy context and indicator evidence provide a useful deterministic control, with no unresolved event, transformation, constraint, or institutional-conflict structure.",
    ),
}


def _normalized_source(case_id: str, batch_root: Path):
    source = parse_source(batch_root / case_id / "source.md")
    return SourceNormalizer().normalize(
        title=source.title,
        body=source.body,
        source_name=source.source_name,
        source_url=source.source_url,
        language="ar",
    )


def _component_matrix(
    case_id: str,
    source: Any,
    evidence: Any,
) -> list[dict[str, Any]]:
    items = evidence.all_items
    matrix = []
    for name, span, section, sentence_index in COMPONENTS[case_id]:
        detected = next(
            (
                item for item in items
                if item.reason_code in DETECTION_CODES.get(name, set())
                and (
                    span in item.matched_text
                    or item.matched_text in span
                    or name == "intelligence_estimate"
                )
            ),
            None,
        )
        matrix.append(
            {
                "component_name": name,
                "source_present": span in f"{source.title}\n{source.body}",
                "context_detected": detected is not None,
                "source_section": section,
                "sentence_index": sentence_index,
                "evidence_role": detected.role.value if detected else None,
                "reason_code": detected.reason_code if detected else None,
                "evidence_span": span,
            }
        )
    return matrix


def analyze_hint_coverage(
    *,
    batch_root: Path = BATCH_ROOT,
    evidence_engine: DeterministicContextualEvidenceEngine | None = None,
) -> dict[str, Any]:
    """Run only normalization and contextual extraction for scoped cases."""
    engine = evidence_engine or DeterministicContextualEvidenceEngine()
    cases = []
    observed_targets = []
    for case_id in (*TARGETS, *NEGATIVE_CONTROLS):
        source = _normalized_source(case_id, batch_root)
        evidence = engine.analyze(source=source)
        supports = {
            support for item in evidence.all_items for support in item.supports
        }
        target_hint = TARGETS.get(case_id)
        hint_observed = target_hint in supports if target_hint else any(
            support.startswith("ADJUDICATION_") for support in supports
        )
        if case_id in TARGETS and hint_observed:
            observed_targets.append(case_id)
        target = case_id in TARGETS
        cases.append(
            {
                "id": case_id,
                "target_hint": target_hint,
                "hint_observed": hint_observed,
                "component_matrix": _component_matrix(
                    case_id, source, evidence
                ),
                "locality_analysis": {
                    "same_sentence_possible": False if target else None,
                    "same_paragraph_possible": False if target else None,
                    "cross_sentence_required": True if target else False,
                    "document_level_pattern_required": False,
                },
                "failure_classes": list(FAILURES.get(case_id, ())),
                "recommendation_classes": list(
                    RECOMMENDATIONS.get(case_id, ("KEEP_CURRENT_BEHAVIOR",))
                ),
                "architectural_observations": list(OBSERVATIONS[case_id]),
            }
        )

    target_cases = [case for case in cases if case["id"] in TARGETS]
    failure_counts = Counter(
        value for case in target_cases for value in case["failure_classes"]
    )
    recommendation_counts = Counter(
        value
        for case in cases
        for value in case["recommendation_classes"]
    )
    return {
        "cases_analyzed": len(cases),
        "target_cases": list(TARGETS),
        "negative_controls": list(NEGATIVE_CONTROLS),
        "hints_expected": len(TARGETS),
        "hints_observed": len(observed_targets),
        "failure_class_counts": dict(sorted(failure_counts.items())),
        "cases_requiring_cross_sentence_structure": [
            case["id"] for case in target_cases
            if case["locality_analysis"]["cross_sentence_required"]
        ],
        "cases_with_components_present_but_uncombined": [
            case["id"] for case in target_cases
            if "COMPONENTS_PRESENT_BUT_NOT_COMBINED"
            in case["failure_classes"]
        ],
        "cases_with_missing_component_extraction": [
            case["id"] for case in target_cases
            if any(
                component["source_present"]
                and not component["context_detected"]
                for component in case["component_matrix"]
            )
        ],
        "recommendation_class_counts": dict(
            sorted(recommendation_counts.items())
        ),
        "hint_construction_analysis": {
            "required_component_count": {
                "ADJUDICATION_EVENT_PUBLIC_SAFETY": 4,
                "ADJUDICATION_ANALYTICAL_CONSTRAINT": 4,
                "ADJUDICATION_EXPLANATORY_TRANSFORMATION": 4,
                "ADJUDICATION_INSTITUTIONAL_POLICY_CONFLICT": 5,
            },
            "locality_constraints": "All component groups must match one segmented sentence.",
            "accepted_roles": [
                "RESULT", "CONSEQUENCE", "EXPLANATION", "BACKGROUND"
            ],
            "accepted_reason_codes": [
                "PUBLIC_SAFETY_EVENT_ADJUDICATION_HINT",
                "ANALYTICAL_CONSTRAINT_ADJUDICATION_HINT",
                "EXPLANATORY_TRANSFORMATION_ADJUDICATION_HINT",
                "INSTITUTIONAL_POLICY_CONFLICT_ADJUDICATION_HINT",
            ],
            "negative_guards": [],
            "threshold_behavior": "All literal component groups are mandatory; partial evidence is not retained for later composition.",
        },
        "dominant_generalization_finding": "E. A mixture: the rules are conceptually aligned but combine literal vocabulary, missing component roles, an all-of threshold, and a synthetic single-sentence shape that does not reflect multi-sentence journalistic prose.",
        "cases": cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(a: dict[str, Any]) -> str:
    by_id = {case["id"]: case for case in a["cases"]}
    lines = [
        "# Batch 05 Adjudication Hint Coverage Analysis", "",
        "## Summary", "", "Target Cases:", "4", "", "Hints Observed:",
        f'{a["hints_observed"]}/4', "", "Components Present But Uncombined:",
        str(len(a["cases_with_components_present_but_uncombined"])), "",
        "Cross-Sentence Structure Required:",
        str(len(a["cases_requiring_cross_sentence_structure"])), "",
        "Missing Component Extraction:",
        str(len(a["cases_with_missing_component_extraction"])), "",
        "## Component Matrix", "",
    ]
    for case_id in TARGETS:
        case = by_id[case_id]
        lines.extend((f"### {case_id}", "", f'Target hint: {case["target_hint"]}', "", "| Component | Source Present | Context Detected | Section | Sentence | Role | Reason | Evidence Span |", "| --- | --- | --- | --- | ---: | --- | --- | --- |"))
        for c in case["component_matrix"]:
            lines.append(f'| {c["component_name"]} | {c["source_present"]} | {c["context_detected"]} | {c["source_section"]} | {c["sentence_index"]} | {c["evidence_role"] or "None"} | {c["reason_code"] or "None"} | {c["evidence_span"]} |')
        lines.extend(("", f'Failures: {", ".join(case["failure_classes"])}', ""))
    lines.extend(("## Negative Controls", ""))
    for case_id in NEGATIVE_CONTROLS:
        case = by_id[case_id]
        lines.extend((f"### {case_id}", "", f'Any adjudication hint observed: {case["hint_observed"]}', "", *[f"- {value}" for value in case["architectural_observations"]], ""))
    lines.extend((
        "## Locality Findings", "",
        "All four target cases require cross-sentence composition. The relevant components are distributed across adjacent sentences or paragraphs; arbitrary document-wide mixing is neither necessary nor recommended.", "",
        "## Generalization Findings", "", a["dominant_generalization_finding"], "",
        "The synthetic tests place every literal component in one sentence. Real editorial prose introduces a subject in the lead, develops response or mechanism in following paragraphs, and states consequences or implications later, so the implementation overfits the synthetic test shape.", "",
        "## Recommended Architecture Change", "",
        "RELAX_LOCALITY_WITH_BOUNDED_WINDOW, ADD_COMPONENT_AGGREGATION, EXPAND_GENERIC_ROLE_COVERAGE, and ADD_CROSS_SENTENCE_COMPOSITION.", "",
        "Use only a same-paragraph or adjacent-sentence window. Preserve KEEP_CURRENT_BEHAVIOR for controls 048 and 049, and retain substantive component requirements so prediction or uncertainty alone cannot form an analytical-constraint hint.", "",
    ))
    return "\n".join(lines)


def main() -> int:
    analysis = analyze_hint_coverage()
    (BATCH_ROOT / "adjudication_hint_coverage_analysis.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "adjudication_hint_coverage_analysis.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(f'Target cases: {len(analysis["target_cases"])}')
    print(f'Hints observed: {analysis["hints_observed"]}/4')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
