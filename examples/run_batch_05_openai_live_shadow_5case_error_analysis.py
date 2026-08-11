"""Analyze persisted five-case OpenAI shadow errors without provider execution."""

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
LIVE_RESULT = BATCH_ROOT / "openai_live_shadow_5case.json"
REQUEST_DIAGNOSTIC = BATCH_ROOT / "adjudication_request_shadow.json"
EDITORIAL_DIAGNOSTIC = BATCH_ROOT / "editorial_validation.json"
OUTPUT_JSON = BATCH_ROOT / "openai_live_shadow_5case_error_analysis.json"
OUTPUT_MD = BATCH_ROOT / "openai_live_shadow_5case_error_analysis.md"
CASE_IDS = ("044", "045", "046", "048", "050")

FAILURE_CLASSES = frozenset({
    "LABEL_SEMANTICS_UNDERSPECIFIED",
    "DETERMINISTIC_TOPIC_ANCHORING",
    "DETERMINISTIC_FORMAT_ANCHORING",
    "STRUCTURED_EVIDENCE_UNDERUSED",
    "EXCERPT_INFORMATION_GAP",
    "FORMAT_ONTOLOGY_OVERLAP",
    "TOPIC_ONTOLOGY_OVERLAP",
    "PROMPT_SCOPE_UNCLEAR",
    "AMBIGUITY_SIGNAL_MEANINGFUL",
    "AMBIGUITY_SIGNAL_WEAK",
    "EXPECTED_LABEL_AMBIGUITY",
    "MODEL_SELECTION_ERROR",
    "UNKNOWN",
})


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _failure_classes(
    live: dict[str, Any],
    editorial: dict[str, Any],
    excerpt: str,
) -> list[str]:
    classes: list[str] = []
    topic_wrong = live["topic_required"] and live["topic_match_expected"] is False
    format_wrong = live["format_required"] and live["format_match_expected"] is False
    if topic_wrong and live["deterministic_topic"] == live["adjudicated_topic"]:
        classes.append("DETERMINISTIC_TOPIC_ANCHORING")
    if topic_wrong and {live["adjudicated_topic"], live["expected_topic"]} == {
        "SCIENCE", "TECHNOLOGY"
    }:
        classes.append("TOPIC_ONTOLOGY_OVERLAP")
    elif topic_wrong:
        classes.append("PROMPT_SCOPE_UNCLEAR")
    if format_wrong:
        classes.extend((
            "LABEL_SEMANTICS_UNDERSPECIFIED",
            "FORMAT_ONTOLOGY_OVERLAP",
        ))
        if live["deterministic_format"] == live["adjudicated_format"]:
            classes.append("DETERMINISTIC_FORMAT_ANCHORING")
        expected_support = f"FORMAT_{live['expected_format']}"
        supports = set(editorial["contextual_support_labels"]) | set(
            editorial["semantic_format_support"]
        )
        if expected_support in supports:
            classes.append("STRUCTURED_EVIDENCE_UNDERUSED")
        if excerpt == "EXCERPT_INFORMATION_GAP":
            classes.append("EXCERPT_INFORMATION_GAP")
    if live["ambiguity_remaining"] is True:
        classes.append(
            "AMBIGUITY_SIGNAL_MEANINGFUL"
            if not topic_wrong and not format_wrong
            else "AMBIGUITY_SIGNAL_WEAK"
        )
    return list(dict.fromkeys(classes)) or ["UNKNOWN"]


def _primary(classes: list[str]) -> str:
    priority = (
        "STRUCTURED_EVIDENCE_UNDERUSED",
        "LABEL_SEMANTICS_UNDERSPECIFIED",
        "TOPIC_ONTOLOGY_OVERLAP",
        "DETERMINISTIC_TOPIC_ANCHORING",
        "AMBIGUITY_SIGNAL_MEANINGFUL",
        "AMBIGUITY_SIGNAL_WEAK",
        "UNKNOWN",
    )
    return next(value for value in priority if value in classes)


def analyze(
    *,
    batch_root: Path = BATCH_ROOT,
    live_result: Path | None = None,
) -> dict[str, Any]:
    """Combine only persisted sanitized live and deterministic diagnostics."""
    live_payload = _read(live_result or batch_root / LIVE_RESULT.name)
    assert tuple(live_payload["cases_selected"]) == CASE_IDS
    live_by_id = {case["id"]: case for case in live_payload["cases"]}
    request_by_id = {
        case["id"]: case
        for case in _read(batch_root / REQUEST_DIAGNOSTIC.name)["cases"]
    }
    editorial_by_id = {
        case["id"]: case
        for case in _read(batch_root / EDITORIAL_DIAGNOSTIC.name)["cases"]
    }
    cases: list[dict[str, Any]] = []
    for case_id in CASE_IDS:
        live = live_by_id[case_id]
        request = request_by_id[case_id]
        editorial = editorial_by_id[case_id]
        incorrect_required = (
            live["topic_match_expected"] is False
            or live["format_match_expected"] is False
        )
        excerpt = (
            "EXCERPT_INFORMATION_GAP"
            if incorrect_required
            and request["excerpt_ratio"] < 0.75
            and request["semantic_relationship_summary_count"] == 0
            else "EXCERPT_SUFFICIENT"
        )
        classes = _failure_classes(live, editorial, excerpt)
        observations = []
        if live["format_required"]:
            observations.append(
                "Format labels were supplied as candidates without operational definitions."
            )
        if "DETERMINISTIC_FORMAT_ANCHORING" in classes:
            observations.append(
                "The adjudicator preserved STANDARD_NEWS after Format adjudication opened."
            )
        if "STRUCTURED_EVIDENCE_UNDERUSED" in classes:
            observations.append(
                "Available FORMAT_ANALYSIS support did not change the selected Format."
            )
        cases.append({
            "id": case_id,
            "gate_scope": live["gate_scope"],
            "deterministic_topic": live["deterministic_topic"],
            "adjudicated_topic": live["adjudicated_topic"],
            "expected_topic": live["expected_topic"],
            "topic_correct": live["topic_match_expected"],
            "deterministic_format": live["deterministic_format"],
            "adjudicated_format": live["adjudicated_format"],
            "expected_format": live["expected_format"],
            "format_correct": live["format_match_expected"],
            "topic_confidence": live["topic_confidence"],
            "format_confidence": live["format_confidence"],
            "ambiguity_remaining": live["ambiguity_remaining"],
            "expected_topic_available": request["expected_topic_available_in_candidates"],
            "expected_format_available": request["expected_format_available_in_candidates"],
            "excerpt_adequacy": excerpt,
            "deterministic_topic_preserved": (
                live["deterministic_topic"] == live["adjudicated_topic"]
            ),
            "deterministic_format_preserved": (
                live["deterministic_format"] == live["adjudicated_format"]
            ),
            "relevant_contextual_supports": editorial["contextual_support_labels"],
            "relevant_semantic_supports": [
                *editorial["semantic_primary_domain_candidates"],
                *editorial["semantic_secondary_domain_candidates"],
                *editorial["semantic_format_support"],
            ],
            "relevant_suppressions": [
                *editorial["contextual_suppression_labels"],
                *editorial["semantic_format_suppression"],
                *editorial["semantic_suppressions"],
            ],
            "failure_classes": classes,
            "primary_failure_class": _primary(classes),
            "architectural_observation": " ".join(observations) or (
                "The selected adjudication matched the required expected dimension."
            ),
        })
    format_cases = [case for case in cases if case["format_correct"] is not None]
    ambiguous = [case for case in cases if case["ambiguity_remaining"] is True]
    ambiguity_correct = sum(
        case["topic_correct"] is not False and case["format_correct"] is not False
        for case in ambiguous
    )
    analysis = {
        "cases_analyzed": list(CASE_IDS),
        "topic_accuracy": live_payload["topic_accuracy"],
        "format_accuracy": live_payload["format_accuracy"],
        "valid_responses": live_payload["valid_responses"],
        "format_required_cases": len(format_cases),
        "format_deterministic_preserved_count": sum(
            case["deterministic_format_preserved"] for case in format_cases
        ),
        "wrong_format_with_deterministic_preserved_count": sum(
            case["format_correct"] is False
            and case["deterministic_format_preserved"] for case in format_cases
        ),
        "topic_deterministic_preserved_count": sum(
            case["deterministic_topic_preserved"] for case in cases
        ),
        "ambiguity_correct_cases": ambiguity_correct,
        "ambiguity_wrong_cases": len(ambiguous) - ambiguity_correct,
        "excerpt_information_gap_cases": sum(
            case["excerpt_adequacy"] == "EXCERPT_INFORMATION_GAP" for case in cases
        ),
        "label_semantics_issue_cases": sum(
            "LABEL_SEMANTICS_UNDERSPECIFIED" in case["failure_classes"]
            for case in cases
        ),
        "structured_evidence_underused_cases": sum(
            "STRUCTURED_EVIDENCE_UNDERUSED" in case["failure_classes"]
            for case in cases
        ),
        "prompt_contract": {
            "candidate_labels_named": True,
            "topic_labels_operationally_defined": False,
            "format_labels_operationally_defined": False,
            "subject_vs_treatment_distinction_defined": False,
            "standard_news_vs_analysis_defined": False,
            "standard_news_vs_explainer_defined": False,
            "suppression_handling_defined": False,
            "ambiguity_handling_defined": False,
        },
        "dominant_architectural_finding": (
            "LABEL_SEMANTICS_UNDERSPECIFIED with repeated "
            "DETERMINISTIC_FORMAT_ANCHORING; case 046 also shows "
            "STRUCTURED_EVIDENCE_UNDERUSED."
        ),
        "recommended_next_step": "COMBINATION_OF_A_B_C",
        "cases": cases,
    }
    analysis["format_deterministic_preserved_rate"] = (
        analysis["format_deterministic_preserved_count"]
        / analysis["format_required_cases"] * 100.0
    )
    assert all(
        set(case["failure_classes"]).issubset(FAILURE_CLASSES) for case in cases
    )
    return analysis


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(analysis: dict[str, Any]) -> str:
    primary = ", ".join(
        f"{case['id']}: {case['primary_failure_class']}"
        for case in analysis["cases"]
    )
    return f"""# OpenAI Five-Case Live Adjudication Error Analysis

## Summary

Topic Accuracy: {analysis['topic_accuracy']:.2f}%

Format Accuracy: {analysis['format_accuracy']:.2f}%

Valid Responses: {analysis['valid_responses']}/5

## Topic Findings

Three cases improved the deterministic Topic. Cases 044 and 046 preserved an incorrect deterministic Topic; 046 also exposes SCIENCE/TECHNOLOGY ontology overlap.

## Format Findings

All {analysis['format_required_cases']} Format-required cases preserved STANDARD_NEWS and missed ANALYSIS or EXPLAINER. Expected labels were available in every required candidate set.

## Deterministic Anchoring

Deterministic Format was preserved in {analysis['format_deterministic_preserved_count']}/{analysis['format_required_cases']} required cases ({analysis['format_deterministic_preserved_rate']:.2f}%).

## Label Semantics

The provider receives labels such as ANALYSIS, EXPLAINER, and STANDARD_NEWS without operational definitions: LABEL_SEMANTICS_UNDERSPECIFIED.

## Structured Evidence Use

Case 046 preserved STANDARD_NEWS despite contextual FORMAT_ANALYSIS support. Cases 044/045 lacked comparable structured format semantics.

## Excerpt Adequacy

Cases 044/045 are classified EXCERPT_INFORMATION_GAP because partial excerpts accompanied incorrect required decisions and no semantic relationship summary. Other selected excerpts are sufficient for this diagnostic.

## Ambiguity Signal

Ambiguity was meaningful for {analysis['ambiguity_correct_cases']} correct case and weak for {analysis['ambiguity_wrong_cases']} incorrect cases.

## Architectural Conclusion

{analysis['dominant_architectural_finding']}

Primary classes: {primary}

## Recommended Next Step

{analysis['recommended_next_step']}
"""


def main() -> int:
    analysis = analyze()
    OUTPUT_JSON.write_text(render_json(analysis), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(analysis), encoding="utf-8")
    print(json.dumps({
        key: value for key, value in analysis.items() if key != "cases"
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
