"""Diagnose the frozen first Batch 05 editorial holdout result."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import parse_source, read_manifest


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
CASE_IDS = tuple(f"{case_id:03d}" for case_id in range(41, 51))
TRIGGERS = (
    "TOPIC_LOW_CONFIDENCE",
    "TOPIC_GENERAL_FALLBACK",
    "NO_PRIMARY_SEMANTIC_DOMAIN",
    "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP",
    "MULTIPLE_COMPETING_TOPIC_SIGNALS",
    "METHOD_SUBJECT_AMBIGUITY",
    "SEMANTIC_DOMAIN_CONFLICT",
    "FORMAT_LOW_CONFIDENCE",
    "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK",
    "EXPLAINER_STRUCTURE_UNRESOLVED",
)
FAILURE_CLASSES = {
    "041": (
        "CONTEXT_PRESENT_BUT_UNCOMPOSED",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "EVENT_DOMAIN_MODEL_GAP",
        "GEOPOLITICAL_DOMAIN_GAP",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "042": (
        "CONTEXT_PRESENT_BUT_UNCOMPOSED",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "METHOD_SUBJECT_CONFUSION",
        "CRIME_LEGAL_DOMAIN_GAP",
        "EVENT_DOMAIN_MODEL_GAP",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "043": (
        "CONTEXT_PRESENT_BUT_UNCOMPOSED",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "POLICY_LEGAL_DOMAIN_GAP",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "044": (
        "CONTEXT_EXTRACTION_GAP",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "EVENT_DOMAIN_MODEL_GAP",
        "GEOPOLITICAL_DOMAIN_GAP",
        "MILITARY_DEFENSE_DOMAIN_GAP",
        "FORMAT_ANALYSIS_STRUCTURE_GAP",
        "DOWNSTREAM_INTENT_FROM_WRONG_FORMAT",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "045": (
        "CONTEXT_EXTRACTION_GAP",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "GEOPOLITICAL_DOMAIN_GAP",
        "MILITARY_DEFENSE_DOMAIN_GAP",
        "FORMAT_EXPLAINER_STRUCTURE_GAP",
        "DOWNSTREAM_INTENT_FROM_WRONG_FORMAT",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "046": (
        "SEMANTIC_RELATIONSHIP_WITHOUT_DOMAIN",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "METHOD_SUBJECT_CONFUSION",
        "SCIENCE_BIOLOGICAL_DOMAIN_GAP",
        "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED",
        "FORMAT_ANALYSIS_STRUCTURE_GAP",
        "DOWNSTREAM_INTENT_FROM_WRONG_FORMAT",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "047": (
        "CONTEXT_PRESENT_BUT_UNCOMPOSED",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "ACTOR_SUBJECT_CONFUSION",
        "POLICY_LEGAL_DOMAIN_GAP",
        "INSTITUTIONAL_CONFLICT_DOMAIN_GAP",
        "FORMAT_ANALYSIS_STRUCTURE_GAP",
        "DOWNSTREAM_INTENT_FROM_WRONG_FORMAT",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "048": (
        "CONTEXT_PRESENT_BUT_UNCOMPOSED",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "GEOPOLITICAL_DOMAIN_GAP",
        "CONTEXTUAL_FORMAT_OVERTRIGGER",
        "LOW_CONFIDENCE_FALLBACK",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
    "049": (),
    "050": (
        "CONTEXT_PRESENT_BUT_UNCOMPOSED",
        "PRIMARY_DOMAIN_MODEL_GAP",
        "ACTOR_SUBJECT_CONFUSION",
        "CRIME_LEGAL_DOMAIN_GAP",
        "EVENT_DOMAIN_MODEL_GAP",
        "DETERMINISTIC_GENERALIZATION_LIMIT",
    ),
}
OBSERVATIONS = {
    "041": (
        "Uncertainty and attribution were extracted, but security authority, preventive government action, and the possible international event were not composed into a domain.",
        "The GENERAL low-confidence fallback makes this a topic adjudication candidate; STANDARD_NEWS and GET_UPDATE were already sufficient.",
    ),
    "042": (
        "Surface phone/SIM signals supported TECHNOLOGY while the criminal conviction, prison sentence, drug case, and legal dispute did not produce a crime/legal event domain.",
        "This is method/surface-object versus primary-event confusion combined with a crime/legal ontology gap.",
    ),
    "043": (
        "Executive action, citizenship policy, constitutional challenge, and judicial review produced neither a relationship nor a policy/legal primary domain.",
        "A reusable policy-plus-legal-plus-executive-action composition is absent; format and intent were already sufficient.",
    ),
    "044": (
        "No contextual evidence represented the ongoing war, air-defense constraint, resource depletion, military pressure, or consequences, so WORLD had no domain support.",
        "ANALYSIS structure was also unresolved; GET_UPDATE followed the wrong STANDARD_NEWS format, making the intent failure downstream.",
    ),
    "045": (
        "Military restructuring, organizational transformation, and unmanned systems produced no contextual items or military/geopolitical domain.",
        "The explanatory framing was not structurally represented, so EXPLAINER and its downstream UNDERSTAND_EVENT intent were missed.",
    ),
    "046": (
        "AI was treated as the primary TECHNOLOGY signal while viruses, biological design, dual use, and consequences did not become a SCIENCE primary domain.",
        "A semantic relationship existed without a domain candidate, and contextual FORMAT_ANALYSIS plus INTENT_UNDERSTAND_IMPACT support was not promoted; the intent failure is downstream from format.",
    ),
    "047": (
        "The university surface subject did not compose with federal scrutiny, discrimination allegations, protests, policy, and legal institutional conflict into POLITICS.",
        "ANALYSIS structure was unresolved, and the resulting intent failure is downstream from STANDARD_NEWS.",
    ),
    "048": (
        "The intelligence estimate, uncertainty, prediction, Russia, and NATO produced contextual analytical support but no geopolitical primary domain.",
        "The final STANDARD_NEWS decision correctly resisted treating prediction or uncertainty alone as ANALYSIS; this is a format negative control despite the topic failure.",
    ),
    "049": (
        "Existing title, body, structured economic values, contextual economy support, and compositional PRIMARY_DOMAIN_ECONOMY evidence aligned.",
        "The deterministic pipeline was sufficient for topic, STANDARD_NEWS, and GET_UPDATE; semantic absence must not be inferred because primary-domain evidence was present.",
    ),
    "050": (
        "Education surface signals outranked the shooting event, fatalities, injuries, police response, and investigation because no reusable violent-crime event domain was produced.",
        "STANDARD_NEWS and GET_UPDATE were sufficient; only topic needs broader event-domain adjudication.",
    ),
}


def _candidate_triggers(case: dict[str, Any]) -> list[str]:
    """Derive diagnostic trigger candidates only from frozen workflow outputs."""
    triggers: list[str] = []
    if case["topic_confidence"] == "LOW":
        triggers.append("TOPIC_LOW_CONFIDENCE")
    if case["predicted_topic"] == "GENERAL" or "DEFAULT_GENERAL_TOPIC" in case[
        "topic_reason_codes"
    ]:
        triggers.append("TOPIC_GENERAL_FALLBACK")
    if not case["semantic_primary_domain_candidates"]:
        triggers.append("NO_PRIMARY_SEMANTIC_DOMAIN")
    if case["contextual_item_count"] and not case["semantic_relationship_count"]:
        triggers.append("CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP")
    contextual_topics = {
        label for label in case["contextual_support_labels"]
        if label.startswith("TOPIC_")
    }
    predicted_label = f'TOPIC_{case["predicted_topic"]}'
    if contextual_topics and predicted_label not in contextual_topics:
        triggers.append("MULTIPLE_COMPETING_TOPIC_SIGNALS")
    if (
        case["predicted_topic"] == "TECHNOLOGY"
        and not case["topic_match"]
        and not case["semantic_primary_domain_candidates"]
    ):
        triggers.append("METHOD_SUBJECT_AMBIGUITY")
    if (
        case["semantic_primary_domain_candidates"]
        and f'PRIMARY_DOMAIN_{case["predicted_topic"]}'
        not in case["semantic_primary_domain_candidates"]
    ):
        triggers.append("SEMANTIC_DOMAIN_CONFLICT")
    if case["format_confidence"] == "LOW":
        triggers.append("FORMAT_LOW_CONFIDENCE")
    if (
        "FORMAT_ANALYSIS" in case["contextual_support_labels"]
        and case["predicted_format"] == "STANDARD_NEWS"
    ):
        triggers.append("ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK")
    # The frozen workflow output exposes no generic explainer-structure signal.
    return triggers


def analyze_generalization(*, batch_root: Path = BATCH_ROOT) -> dict[str, Any]:
    """Analyze frozen results and sources without executing classification."""
    validation = json.loads(
        (batch_root / "editorial_validation.json").read_text(encoding="utf-8")
    )
    manifest = read_manifest(batch_root)
    assert tuple(case["id"] for case in manifest) == CASE_IDS
    source_by_id = {
        case["id"]: parse_source(batch_root / case["source_file"])
        for case in manifest
    }
    cases: list[dict[str, Any]] = []
    for prior in validation["cases"]:
        case_id = prior["id"]
        source = source_by_id[case_id]
        assert source.case_id == case_id and source.title and source.body
        topic_sufficient = prior["topic_match"]
        format_sufficient = prior["format_match"]
        cases.append(
            {
                "id": case_id,
                "expected_topic": prior["expected_topic"],
                "predicted_topic": prior["predicted_topic"],
                "expected_format": prior["expected_format"],
                "predicted_format": prior["predicted_format"],
                "expected_intent": prior["expected_reader_intent"],
                "predicted_intent": prior["predicted_reader_intent"],
                "contextual_item_count": prior["contextual_item_count"],
                "semantic_relationship_count": prior[
                    "semantic_relationship_count"
                ],
                "primary_domain_candidates": prior[
                    "semantic_primary_domain_candidates"
                ],
                "failure_classes": list(FAILURE_CLASSES[case_id]),
                "deterministic_topic_sufficient": topic_sufficient,
                "deterministic_format_sufficient": format_sufficient,
                "semantic_adjudication_topic_candidate": not topic_sufficient,
                "semantic_adjudication_format_candidate": not format_sufficient,
                "candidate_triggers": _candidate_triggers(prior),
                "architectural_observations": list(OBSERVATIONS[case_id]),
            }
        )

    trigger_analysis: dict[str, dict[str, object]] = {}
    format_triggers = {
        "FORMAT_LOW_CONFIDENCE",
        "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK",
        "EXPLAINER_STRUCTURE_UNRESOLVED",
    }
    for trigger in TRIGGERS:
        triggered = [
            case for case in cases if trigger in case["candidate_triggers"]
        ]
        mismatch_key = (
            "deterministic_format_sufficient"
            if trigger in format_triggers
            else "deterministic_topic_sufficient"
        )
        mismatched = [case for case in triggered if not case[mismatch_key]]
        matched = len(triggered) - len(mismatched)
        trigger_analysis[trigger] = {
            "cases_triggered": len(triggered),
            "matched_cases_triggered": matched,
            "mismatched_cases_triggered": len(mismatched),
            "precision_for_mismatch": (
                len(mismatched) / len(triggered) if triggered else None
            ),
        }

    failure_counts = Counter(
        failure for case in cases for failure in case["failure_classes"]
    )
    intent_failures = [
        case for case in cases if case["expected_intent"] != case["predicted_intent"]
    ]
    downstream_intent = [
        case for case in intent_failures
        if case["expected_format"] != case["predicted_format"]
    ]
    return {
        "case_count": len(cases),
        "failure_class_counts": dict(sorted(failure_counts.items())),
        "topic_failure_count": sum(
            not case["deterministic_topic_sufficient"] for case in cases
        ),
        "format_failure_count": sum(
            not case["deterministic_format_sufficient"] for case in cases
        ),
        "intent_failure_count": len(intent_failures),
        "direct_intent_failure_count": len(intent_failures) - len(downstream_intent),
        "downstream_intent_failure_count": len(downstream_intent),
        "deterministically_sufficient_cases": [
            case["id"]
            for case in cases
            if case["deterministic_topic_sufficient"]
            and case["deterministic_format_sufficient"]
            and case["expected_intent"] == case["predicted_intent"]
        ],
        "semantic_adjudication_topic_candidates": [
            case["id"]
            for case in cases if case["semantic_adjudication_topic_candidate"]
        ],
        "semantic_adjudication_format_candidates": [
            case["id"]
            for case in cases if case["semantic_adjudication_format_candidate"]
        ],
        "trigger_analysis": trigger_analysis,
        "cases": cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[object]) -> str:
    return ", ".join(str(value) for value in values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the frozen architectural analysis and alternatives."""
    lines = [
        "# Batch 05 Editorial Generalization Analysis", "",
        "## Baseline", "",
        "Batch 01 Topic:", "100%", "",
        "Batch 02 Full:", "100%", "",
        "Batch 03 Full:", "100%", "",
        "Batch 05 First Holdout:", "",
        "Topic:", "10%", "", "Format:", "60%", "",
        "Intent:", "60%", "", "Full:", "10%", "",
        "## Failure Distribution", "",
    ]
    for failure, count in analysis["failure_class_counts"].items():
        lines.extend((f"{failure}:", str(count), ""))
    lines.extend(("## Case Diagnostics", ""))
    for case in analysis["cases"]:
        lines.extend(
            (
                f'### Case {case["id"]}', "",
                f'Expected/Predicted Topic: {case["expected_topic"]} / {case["predicted_topic"]}',
                f'Expected/Predicted Format: {case["expected_format"]} / {case["predicted_format"]}',
                f'Expected/Predicted Intent: {case["expected_intent"]} / {case["predicted_intent"]}', "",
                f'Contextual Items: {case["contextual_item_count"]}',
                f'Semantic Relationships: {case["semantic_relationship_count"]}',
                f'Primary Domains: {_display(case["primary_domain_candidates"])}',
                f'Failure Classes: {_display(case["failure_classes"])}',
                f'Candidate Triggers: {_display(case["candidate_triggers"])}', "",
                *[f"- {item}" for item in case["architectural_observations"]], "",
            )
        )
    lines.extend(
        (
            "## Reader Intent Dependency", "",
            f'Direct intent failures: {analysis["direct_intent_failure_count"]}.',
            f'Downstream-from-format intent failures: {analysis["downstream_intent_failure_count"]}.',
            "All observed intent failures follow incorrect format decisions, so the frozen evidence does not justify changing ReaderIntentClassifierV2.", "",
            "## Candidate Semantic-Adjudication Triggers", "",
            "| Trigger | Cases Triggered | Mismatches Captured | Correct Cases Triggered | Mismatch Precision |",
            "| --- | ---: | ---: | ---: | ---: |",
        )
    )
    for trigger, metrics in analysis["trigger_analysis"].items():
        precision = metrics["precision_for_mismatch"]
        lines.append(
            f'| {trigger} | {metrics["cases_triggered"]} | '
            f'{metrics["mismatched_cases_triggered"]} | '
            f'{metrics["matched_cases_triggered"]} | '
            f'{precision:.2%} |' if precision is not None else
            f'| {trigger} | 0 | 0 | 0 | N/A |'
        )
    lines.extend(
        (
            "", "## Deterministic vs Adjudication Boundary", "",
            "A candidate boundary is to retain deterministic decisions when a primary semantic domain aligns with high-confidence topic evidence, while considering structured adjudication when existing outputs show no primary domain together with low topic confidence, GENERAL fallback, uncomposed contextual evidence, or method/subject ambiguity. Format adjudication can be narrower: low confidence plus unresolved structural support, while analytical context alone must not trigger adjudication because case 048 is a negative control. This boundary uses existing outputs and does not send every article to a provider.", "",
            "## Architecture Decision Inputs", "",
            "### Dictionary expansion", "",
            "Generalization: limited to anticipated lexical forms. Maintenance: frequent dictionary review. Cost and latency: lowest. Determinism: highest. Provider dependence: none. Auditability: direct, but interactions and omissions grow difficult to reason about.", "",
            "### Deterministic semantic ontology expansion", "",
            "Generalization: better across reusable event, actor, subject, policy, legal, military, scientific, and format relationships. Maintenance: substantial ontology and composition work. Cost and latency: low at runtime. Determinism: high. Provider dependence: none. Auditability: strong when provenance is preserved.", "",
            "### Structured semantic adjudication fallback", "",
            "Generalization: potentially broad when deterministic evidence is ambiguous or incomplete. Maintenance: schemas, prompts, evaluation, and provider controls. Cost and latency: higher but gated. Determinism: lower unless outputs are constrained and validated. Provider dependence: explicit. Auditability: viable with recorded triggers, inputs, structured outputs, and deterministic fallback behavior.", "",
            "## Required Conclusion", "",
            "1. The dominant failure is not purely lexical; lexical surface cues contribute to cases 042, 046, 047, and 050, but several cases fall back despite meaningful events.",
            "2. Composition is a dominant boundary: six context-bearing failures have no relationship, and case 046 has a relationship without a domain.",
            "3. The current deterministic semantic domain ontology is not broad enough for the observed geopolitical, crime/legal, military, science/biological, policy/legal, institutional-conflict, and violent-event structures.",
            "4. Adding case-specific phrases would constitute overfitting; improvements should represent reusable event, role, relationship, and framing structures.",
            "5. Reader intent can remain downstream of Format because all four intent failures are explained by wrong format decisions.",
            "6. The frozen evidence supports evaluating an adjudication fallback, but does not define a final production policy.",
            "7. Existing signals that can gate evaluation include missing primary semantic domain, low topic confidence, GENERAL fallback, contextual evidence without relationships, method/subject ambiguity, format low confidence, and unresolved analytical context—with case 048 constraining over-triggering.", "",
        )
    )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    return "\n".join(
        (
            "=== BATCH 05 EDITORIAL GENERALIZATION ANALYSIS ===", "",
            "Cases:", str(analysis["case_count"]), "",
            "Topic Failures:", str(analysis["topic_failure_count"]), "",
            "Format Failures:", str(analysis["format_failure_count"]), "",
            "Intent Failures:", str(analysis["intent_failure_count"]),
        )
    )


def main() -> int:
    analysis = analyze_generalization()
    (BATCH_ROOT / "editorial_generalization_analysis.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "editorial_generalization_analysis.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
