"""Diagnose compositional contextual-evidence failures in Batch 03."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_03"
FAILED_CASE_IDS = ("021", "022", "023", "024", "025", "026", "028", "029")
FAILURE_TAXONOMY = (
    "VOCABULARY_GAP",
    "COMPOSITIONAL_RELATIONSHIP_MISSING",
    "AUTHORITY_SUBJECT_CONFUSION",
    "ACTOR_SUBJECT_CONFUSION",
    "METHOD_SUBJECT_CONFUSION",
    "DOMAIN_PRECEDENCE_ERROR",
    "ACTION_STRUCTURE_MISSING",
    "EVENT_DOMAIN_MAPPING_MISSING",
    "FORMAT_ACTION_FALSE_POSITIVE",
    "INSUFFICIENT_CONTEXT_COMPOSITION",
)

_DOMAIN_OBJECT_FIX = "Detect domain-bearing objects and weight them above generic actors or institutions."
_AUTHORITY_FIX = "Compose institution authority with its acted-on subject instead of treating authority as the subject domain."
_ACTOR_FIX = "Separate actors from the primary subject through action-object composition."
_METHOD_FIX = "Distinguish a method or tool from the domain-bearing object it is used to examine."
_EVENT_FIX = "Compose environmental conditions, events, and outcomes into candidate domain evidence."
_ACTION_FIX = "Detect recommended-action structures from adviser, affected audience, and requested action relationships."
_NEGATIVE_FORMAT_FIX = "Add negative format evidence when requirement, deadline, procedure, eligibility, and reader action are absent."
_COMPETITION_FIX = "Resolve candidate domains through contextual competition among authority, actor, method, object, event, and outcome evidence."

_DIAGNOSTICS: dict[str, dict[str, object]] = {
    "021": {
        "diagnostic_roles": {
            "AUTHORITY": ["الهيئة القومية للأنفاق"],
            "PRIMARY_SUBJECT": ["منظومة المونوريل"],
            "ACTION": ["التشغيل التجريبي"],
            "DOMAIN": ["public infrastructure", "government transport"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "AUTHORITY_SUBJECT_CONFUSION",
            "INSUFFICIENT_CONTEXT_COMPOSITION",
        ),
        "missing_relationships": [
            "Official transport authority operates a public-infrastructure project.",
            "Operational project object carries the government-transport domain.",
        ],
        "general_fix_candidates": [_AUTHORITY_FIX, _DOMAIN_OBJECT_FIX],
    },
    "022": {
        "diagnostic_roles": {
            "ACTOR": ["صندوق النقد الدولي"],
            "PRIMARY_SUBJECT": ["النمو الاقتصادي"],
            "INDICATOR": ["الأنشطة غير النفطية", "الاستثمار"],
            "DOMAIN": ["ECONOMY"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "ACTOR_SUBJECT_CONFUSION",
            "INSUFFICIENT_CONTEXT_COMPOSITION",
        ),
        "missing_relationships": [
            "Reporting institution describes macroeconomic subject and indicators.",
            "Economic indicators jointly establish the primary domain.",
        ],
        "general_fix_candidates": [_ACTOR_FIX, _DOMAIN_OBJECT_FIX],
    },
    "023": {
        "diagnostic_roles": {
            "ACTOR": ["الولايات المتحدة", "الصين", "مسؤولون تجاريون"],
            "ACTION": ["مفاوضات"],
            "OBJECT": ["التعرفة والقيود التجارية"],
            "DOMAIN": ["international politics", "diplomacy"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "ACTOR_SUBJECT_CONFUSION",
            "DOMAIN_PRECEDENCE_ERROR",
        ),
        "missing_relationships": [
            "State actors negotiate policy restrictions in an international relationship.",
            "Diplomatic action is primary while trade is secondary evidence.",
        ],
        "general_fix_candidates": [_ACTOR_FIX, _COMPETITION_FIX],
    },
    "024": {
        "diagnostic_roles": {
            "METHOD": ["الذكاء الاصطناعي"],
            "PRIMARY_SUBJECT": ["تشخيص أورام السرطان"],
            "OBJECT": ["الصور الطبية", "الأورام"],
            "DOMAIN": ["HEALTH"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "METHOD_SUBJECT_CONFUSION",
            "DOMAIN_PRECEDENCE_ERROR",
        ),
        "missing_relationships": [
            "Technology is the diagnostic method, not the primary subject.",
            "Medical objects and outcome establish health as the dominant domain.",
        ],
        "general_fix_candidates": [_METHOD_FIX, _DOMAIN_OBJECT_FIX, _COMPETITION_FIX],
    },
    "025": {
        "diagnostic_roles": {
            "AUTHORITY": ["وزارة الصحة"],
            "ACTION": ["تقديم خدمات وفحوصات"],
            "PRIMARY_SUBJECT": ["health screening", "medical services"],
            "DOMAIN": ["HEALTH"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "AUTHORITY_SUBJECT_CONFUSION",
            "DOMAIN_PRECEDENCE_ERROR",
        ),
        "missing_relationships": [
            "Government authority supplies services whose objects carry the health domain.",
            "Institution type should not override the acted-on medical subject.",
        ],
        "general_fix_candidates": [_AUTHORITY_FIX, _DOMAIN_OBJECT_FIX, _COMPETITION_FIX],
    },
    "026": {
        "diagnostic_roles": {
            "ACTOR": ["cybersecurity experts"],
            "PRIMARY_SUBJECT": ["ransomware attacks"],
            "AFFECTED_AUDIENCE": ["financial institutions", "companies"],
            "RECOMMENDED_ACTION": ["update protection", "apply encryption"],
            "DOMAIN": ["TECHNOLOGY"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "ACTION_STRUCTURE_MISSING",
            "INSUFFICIENT_CONTEXT_COMPOSITION",
        ),
        "missing_relationships": [
            "Experts direct protective actions to an affected audience.",
            "Threat, audience, and recommended action jointly support service treatment and action intent.",
        ],
        "general_fix_candidates": [_ACTION_FIX, _DOMAIN_OBJECT_FIX],
    },
    "028": {
        "diagnostic_roles": {
            "ENVIRONMENTAL_CONDITION": ["heavy monsoon rain"],
            "ACTION": ["flooding", "landslides"],
            "OUTCOME": ["displacement", "evacuation"],
            "DOMAIN": ["WEATHER"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "EVENT_DOMAIN_MAPPING_MISSING",
            "INSUFFICIENT_CONTEXT_COMPOSITION",
        ),
        "missing_relationships": [
            "Environmental condition causes hazardous events and human outcomes.",
            "The condition-event-outcome chain establishes the weather domain.",
        ],
        "general_fix_candidates": [_EVENT_FIX, _COMPETITION_FIX],
    },
    "029": {
        "diagnostic_roles": {
            "AUTHORITY": ["وزارة التعليم العالي"],
            "PRIMARY_SUBJECT": ["الجامعات المصرية"],
            "ACTION": ["international rankings"],
            "DOMAIN": ["EDUCATION"],
        },
        "failure_classes": (
            "COMPOSITIONAL_RELATIONSHIP_MISSING",
            "AUTHORITY_SUBJECT_CONFUSION",
            "DOMAIN_PRECEDENCE_ERROR",
            "FORMAT_ACTION_FALSE_POSITIVE",
        ),
        "missing_relationships": [
            "Education authority reports an outcome about universities.",
            "No requirement, deadline, procedure, eligibility, or reader action exists.",
        ],
        "general_fix_candidates": [
            _AUTHORITY_FIX,
            _DOMAIN_OBJECT_FIX,
            _NEGATIVE_FORMAT_FIX,
        ],
    },
}


def analyze_failures(batch_root: Path = BATCH_ROOT) -> dict[str, Any]:
    """Combine frozen validation outcomes with architectural diagnoses."""
    validation = json.loads(
        (batch_root / "contextual_full_validation.json").read_text(encoding="utf-8")
    )
    validation_by_id = {case["id"]: case for case in validation["cases"]}
    cases: list[dict[str, object]] = []
    for case_id in FAILED_CASE_IDS:
        observed = validation_by_id[case_id]
        diagnostic = _DIAGNOSTICS[case_id]
        cases.append(
            {
                "id": case_id,
                "expected_topic": observed["expected_topic"],
                "predicted_topic": observed["predicted_topic"],
                "expected_format": observed["expected_format"],
                "predicted_format": observed["predicted_format"],
                "expected_intent": observed["expected_reader_intent"],
                "predicted_intent": observed["predicted_reader_intent"],
                "current_contextual_support": observed[
                    "contextual_support_labels"
                ],
                "diagnostic_roles": diagnostic["diagnostic_roles"],
                "failure_classes": list(diagnostic["failure_classes"]),
                "missing_relationships": diagnostic["missing_relationships"],
                "general_fix_candidates": diagnostic["general_fix_candidates"],
            }
        )
    counts = Counter(
        failure_class for case in cases for failure_class in case["failure_classes"]
    )
    return {
        "batch": "batch_03",
        "cases_analyzed": len(cases),
        "failure_class_counts": {
            failure_class: counts.get(failure_class, 0)
            for failure_class in FAILURE_TAXONOMY
        },
        "cases": cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic diagnostic JSON without full source bodies."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[str]) -> str:
    """Render ordered values or an explicit None."""
    return ", ".join(values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render summary, case diagnoses, findings, and proposed architecture."""
    lines = [
        "# Batch 03 Compositional Context Failure Analysis",
        "",
        "## Summary",
        "",
        "Cases Analyzed:",
        str(analysis["cases_analyzed"]),
        "",
    ]
    for failure_class, count in analysis["failure_class_counts"].items():
        lines.extend((f"{failure_class}:", str(count), ""))
    lines.extend(("## Case Diagnostics", ""))
    for case in analysis["cases"]:
        roles = [
            f"{role}: {_display(values)}"
            for role, values in case["diagnostic_roles"].items()
        ]
        lines.extend(
            (
                f"### Case {case['id']}",
                "",
                "Current Prediction:",
                f"Topic={case['predicted_topic']}; Format={case['predicted_format']}; Intent={case['predicted_intent']}",
                "",
                "Expected:",
                f"Topic={case['expected_topic']}; Format={case['expected_format']}; Intent={case['expected_intent']}",
                "",
                "Observed Contextual Support:",
                _display(case["current_contextual_support"]),
                "",
                "Conceptual Roles:",
                *[f"- {value}" for value in roles],
                "",
                "Missing Relationships:",
                *[f"- {value}" for value in case["missing_relationships"]],
                "",
                "Failure Classes:",
                *[f"- {value}" for value in case["failure_classes"]],
                "",
                "General Fix Candidates:",
                *[f"- {value}" for value in case["general_fix_candidates"]],
                "",
            )
        )
    lines.extend(
        (
            "## Cross-Case Architectural Findings",
            "",
            "### 1. Authority is being confused with subject",
            "Institution labels can dominate the acted-on domain object.",
            "",
            "### 2. Methods/tools are being confused with subject",
            "A prominent method can outrank the domain-bearing object it serves.",
            "",
            "### 3. Domain-bearing objects are underweighted",
            "Objects and outcomes do not yet compose into strong candidate domains.",
            "",
            "### 4. Event semantics are missing",
            "Condition, event, and outcome relationships are not represented.",
            "",
            "### 5. Recommended-action structure is incomplete",
            "Advice is not composed from adviser, audience, threat, and action.",
            "",
            "### 6. Format negative evidence is missing",
            "Ordinary institutional news lacks an explicit absence signal for actionable structure.",
            "",
            "### 7. Phrase dictionaries do not generalize sufficiently",
            "Independent phrase hits cannot express which entity is acting on which object.",
            "",
            "## Proposed Next Architecture",
            "",
            "Token Evidence",
            "↓",
            "Phrase Evidence",
            "↓",
            "Local Context Evidence",
            "↓",
            "Compositional Semantic Evidence",
            "↓",
            "Candidate Domain Evidence",
            "↓",
            "Topic / Format / Intent classifiers",
            "",
            "Compositional Semantic Evidence should consume relationships between multiple evidence items rather than adding more case-specific keywords.",
            "",
        )
    )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render a compact deterministic diagnostic summary."""
    lines = [
        "=== BATCH 03 COMPOSITIONAL CONTEXT FAILURE ANALYSIS ===",
        "",
        "Cases Analyzed:",
        str(analysis["cases_analyzed"]),
        "",
    ]
    lines.extend(
        f"{failure_class}: {count}"
        for failure_class, count in analysis["failure_class_counts"].items()
    )
    return "\n".join(lines)


def main() -> int:
    """Analyze persisted failures and write deterministic diagnostic reports."""
    analysis = analyze_failures()
    (BATCH_ROOT / "compositional_context_analysis.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "compositional_context_analysis.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
