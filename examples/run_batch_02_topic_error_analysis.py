"""Diagnose Batch 02 topic mismatches without changing production rules."""

import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import (
    BATCH_ROOT,
    _source_fields,
    parse_source,
    read_expectations,
    read_manifest,
)
from src.topic.deterministic_topic_classifier import (
    DeterministicTopicClassifier,
    _LEGACY_TOPICS,
    _RISK_TOPIC_SUPPORT,
    _TOPIC_TERMS,
)
from src.topic.topic import Topic
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


HUMAN_ADJUDICATION_IDS = ("011", "013", "014", "016", "020")
_CANDIDATE_VOCABULARY_OBSERVATIONS = {
    "014": "WORLD may need supplied international climate-conference terminology.",
    "017": "ECONOMY may need supplied digital-asset and financial-regulation terminology.",
    "018": "SCIENCE may need supplied astronomy, planet, and observatory terminology.",
    "019": "CULTURE may need supplied book-fair and publishing terminology.",
}
_COMPETING_TOPICS = {
    "011": ("GOVERNMENT", "ECONOMY"),
    "013": ("TECHNOLOGY", "BUSINESS", "ECONOMY", "SCIENCE"),
    "014": ("WORLD", "WEATHER", "POLITICS"),
    "016": ("BUSINESS", "ECONOMY"),
    "020": ("TECHNOLOGY", "ECONOMY", "GOVERNMENT"),
}


def _read_validation(batch_root: Path) -> dict[str, Any]:
    """Read the persisted raw validation result."""
    return json.loads(
        (batch_root / "validation.json").read_text(encoding="utf-8")
    )


def _context(text: str, start: int, end: int) -> str:
    """Return a short whitespace-normalized context around one exact match."""
    context_start = max(0, start - 20)
    context_end = min(len(text), end + 20)
    return " ".join(text[context_start:context_end].split())


def _inside_larger_token(text: str, start: int, end: int) -> bool:
    """Detect a substring match that lacks Unicode word boundaries."""
    preceding_is_word = start > 0 and bool(re.match(r"\w", text[start - 1]))
    following_is_word = end < len(text) and bool(re.match(r"\w", text[end]))
    return preceding_is_word or following_is_word


def matched_topic_terms(text: str) -> dict[str, list[dict[str, object]]]:
    """Report every production-vocabulary match and its exact text context.

    Args:
        text: Title, body, or tags text examined by production substring rules.

    Returns:
        Every supported topic mapped to ordered exact match diagnostics.
    """
    lowered = text.lower()
    matches: dict[str, list[dict[str, object]]] = {}
    for topic, terms in _TOPIC_TERMS.items():
        topic_matches: list[dict[str, object]] = []
        for term in terms:
            for occurrence in re.finditer(re.escape(term), lowered):
                start, end = occurrence.span()
                topic_matches.append(
                    {
                        "matched_term": term,
                        "matched_text_context": _context(text, start, end),
                        "inside_larger_token": _inside_larger_token(
                            lowered,
                            start,
                            end,
                        ),
                    }
                )
        matches[topic.value] = topic_matches
    return matches


def _non_legacy_evidence_is_weak(
    *,
    predicted_topic: str,
    title_signals: dict[str, list[dict[str, object]]],
    body_signals: dict[str, list[dict[str, object]]],
    tag_signals: dict[str, list[dict[str, object]]],
    government_entity_evidence: bool,
    structured_economic_evidence: bool,
    risk_topics: tuple[str, ...],
) -> bool:
    """Apply a diagnostic-only definition of weak non-legacy support."""
    distinct_terms = {
        match["matched_term"]
        for group in (title_signals, body_signals, tag_signals)
        for match in group[predicted_topic]
    }
    risk_support = any(
        _RISK_TOPIC_SUPPORT.get(risk_topic.lower(), Topic.GENERAL).value
        == predicted_topic
        for risk_topic in risk_topics
    )
    structural_support = (
        predicted_topic == Topic.GOVERNMENT.value and government_entity_evidence
    ) or (
        predicted_topic == Topic.ECONOMY.value and structured_economic_evidence
    )
    return len(distinct_terms) <= 1 and not risk_support and not structural_support


def _failure_classes(case: dict[str, Any]) -> tuple[str, ...]:
    """Group one mismatch under deterministic diagnostic classes."""
    classes: list[str] = []
    if case["legacy_support_applied"]:
        classes.append("Legacy dependency")
    if "SUBSTRING_COLLISION_SUSPECTED" in case["diagnostic_flags"]:
        classes.append("Substring matching")
    if "EXPECTED_TOPIC_VOCABULARY_GAP" in case["diagnostic_flags"]:
        classes.append("Vocabulary coverage")
    expected_has_matches = bool(
        case["expected_topic_title_matches"]
        or case["expected_topic_body_matches"]
    )
    supported_topics = sum(
        bool(case["title_topic_signals"][topic])
        or bool(case["body_topic_signals"][topic])
        for topic in case["title_topic_signals"]
    )
    if expected_has_matches or supported_topics >= 2:
        classes.append("Topic scoring / precedence")
    if case["id"] in HUMAN_ADJUDICATION_IDS:
        classes.append("Human-label ambiguity")
    return tuple(classes)


def analyze_topic_errors(
    *,
    batch_root: Path = BATCH_ROOT,
    topic_workflow: EditorialTopicWorkflow | None = None,
) -> dict[str, Any]:
    """Diagnose each persisted topic mismatch using current rule inputs.

    Args:
        batch_root: Directory containing Batch 02 inputs and validation.
        topic_workflow: Optional current workflow supplied for isolated tests.

    Returns:
        Machine-readable mismatch evidence and diagnostic groupings.
    """
    validation = _read_validation(batch_root)
    mismatch_records = {
        case["id"]: case for case in validation["cases"] if not case["topic_match"]
    }
    expected_by_id = {
        item["id"]: item for item in read_expectations(batch_root)
    }
    manifest_by_id = {item["id"]: item for item in read_manifest(batch_root)}
    workflow = topic_workflow or EditorialTopicWorkflow()
    diagnostics: list[dict[str, Any]] = []

    for case_id in mismatch_records:
        validation_case = mismatch_records[case_id]
        source = parse_source(
            batch_root / manifest_by_id[case_id]["source_file"]
        )
        result = workflow.process(**_source_fields(source))
        ingestion = result.classification_result.ingestion
        content_classification = result.classification_result.classification
        classification = result.topic_classification
        title_signals = matched_topic_terms(ingestion.source.title)
        body_signals = matched_topic_terms(ingestion.source.body)
        tag_signals = matched_topic_terms("\n".join(ingestion.source.tags))
        legacy_topic = _LEGACY_TOPICS.get(content_classification.content_type)
        legacy_support_applied = legacy_topic is not None
        government_entity_evidence = bool(ingestion.facts.government_entities)
        searchable_text = "\n".join(
            (
                ingestion.source.title.lower(),
                ingestion.source.body.lower(),
                ingestion.source.category or "",
                "\n".join(ingestion.source.tags).lower(),
                "",
            )
        )
        structured_economic = (
            DeterministicTopicClassifier._structured_economic_support(
                searchable_text,
                ingestion.facts,
            )
        )
        expected_topic = expected_by_id[case_id]["topic"]
        predicted_topic = classification.topic.value
        expected_title_matches = title_signals[expected_topic]
        expected_body_matches = body_signals[expected_topic]
        collision = any(
            match["inside_larger_token"]
            for signals in (title_signals, body_signals, tag_signals)
            for matches in signals.values()
            for match in matches
        )
        vocabulary_gap = (
            not expected_title_matches
            and not expected_body_matches
            and ingestion.source.category is None
            and case_id in _CANDIDATE_VOCABULARY_OBSERVATIONS
        )
        legacy_contamination = (
            legacy_topic is not None
            and predicted_topic == legacy_topic.value
            and expected_topic != predicted_topic
            and _non_legacy_evidence_is_weak(
                predicted_topic=predicted_topic,
                title_signals=title_signals,
                body_signals=body_signals,
                tag_signals=tag_signals,
                government_entity_evidence=government_entity_evidence,
                structured_economic_evidence=structured_economic,
                risk_topics=ingestion.assessment.risk_topics,
            )
        )
        flags: list[str] = []
        if legacy_contamination:
            flags.append("LEGACY_TOPIC_CONTAMINATION_SUSPECTED")
        if collision:
            flags.append("SUBSTRING_COLLISION_SUSPECTED")
        if vocabulary_gap:
            flags.append("EXPECTED_TOPIC_VOCABULARY_GAP")
        diagnostic = {
            "id": case_id,
            "expected_topic": expected_topic,
            "predicted_topic": predicted_topic,
            "predicted_confidence": classification.confidence.value,
            "legacy_content_type": content_classification.content_type.value,
            "legacy_content_confidence": content_classification.confidence.value,
            "legacy_implied_topic": legacy_topic.value if legacy_topic else None,
            "legacy_support_applied": legacy_support_applied,
            "risk_topics": list(ingestion.assessment.risk_topics),
            "title_topic_signals": title_signals,
            "body_topic_signals": body_signals,
            "tag_topic_signals": tag_signals,
            "expected_topic_title_matches": expected_title_matches,
            "expected_topic_body_matches": expected_body_matches,
            "government_entity_evidence": government_entity_evidence,
            "structured_economic_evidence": structured_economic,
            "final_reason_codes": list(classification.reason_codes),
            "final_supporting_signals": list(classification.supporting_signals),
            "final_warnings": list(classification.warnings),
            "diagnostic_flags": flags,
        }
        diagnostic["failure_classes"] = list(_failure_classes(diagnostic))
        diagnostics.append(diagnostic)

    adjudication_queue: list[dict[str, Any]] = []
    for case_id in HUMAN_ADJUDICATION_IDS:
        source = parse_source(
            batch_root / manifest_by_id[case_id]["source_file"]
        )
        validation_case = next(
            case for case in validation["cases"] if case["id"] == case_id
        )
        adjudication_queue.append(
            {
                "id": case_id,
                "title": source.title,
                "expected_topic": expected_by_id[case_id]["topic"],
                "predicted_topic": validation_case["predicted_topic"],
                "possible_competing_topics": list(_COMPETING_TOPICS[case_id]),
            }
        )

    return {
        "batch": "batch_02",
        "topic_mismatches": len(diagnostics),
        "legacy_contamination_suspected": sum(
            "LEGACY_TOPIC_CONTAMINATION_SUSPECTED" in case["diagnostic_flags"]
            for case in diagnostics
        ),
        "substring_collision_suspected": sum(
            "SUBSTRING_COLLISION_SUSPECTED" in case["diagnostic_flags"]
            for case in diagnostics
        ),
        "expected_vocabulary_gap": sum(
            "EXPECTED_TOPIC_VOCABULARY_GAP" in case["diagnostic_flags"]
            for case in diagnostics
        ),
        "human_adjudication_required": len(adjudication_queue),
        "mismatches": diagnostics,
        "human_adjudication_queue": adjudication_queue,
    }


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic diagnostics without any full source body."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _value_lines(label: str, values: list[str]) -> list[str]:
    """Render an ordered diagnostic list or explicit None."""
    return [label, *(f"- {value}" for value in values)] if values else [label, "None"]


def _match_lines(
    label: str,
    signals: dict[str, list[dict[str, object]]],
) -> list[str]:
    """Render matched production terms grouped under their topic."""
    lines = [label, ""]
    matched_topics = {
        topic: matches for topic, matches in signals.items() if matches
    }
    if not matched_topics:
        return [*lines, "None"]
    for topic, matches in matched_topics.items():
        lines.append(f"{topic}:")
        for match in matches:
            lines.append(
                f"- {match['matched_term']} — {match['matched_text_context']}"
            )
    return lines


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render mismatch evidence, review queue, and failure-class groups."""
    lines = [
        "# Batch 02 Topic Error Analysis",
        "",
        "## Summary",
        "",
        "Topic Mismatches:",
        str(analysis["topic_mismatches"]),
        "",
        "Legacy Contamination Suspected:",
        str(analysis["legacy_contamination_suspected"]),
        "",
        "Substring Collision Suspected:",
        str(analysis["substring_collision_suspected"]),
        "",
        "Expected Vocabulary Gap:",
        str(analysis["expected_vocabulary_gap"]),
        "",
        "Human Adjudication Required:",
        str(analysis["human_adjudication_required"]),
        "",
        "## Mismatch Diagnostics",
        "",
    ]
    for case in analysis["mismatches"]:
        lines.extend(
            (
                f"### Case {case['id']}",
                "",
                "Expected:",
                case["expected_topic"],
                "",
                "Predicted:",
                case["predicted_topic"],
                "",
                "Confidence:",
                case["predicted_confidence"],
                "",
                "Legacy Content Type:",
                case["legacy_content_type"],
                "",
                "Legacy Implied Topic:",
                case["legacy_implied_topic"] or "None",
                "",
                "Legacy Support Applied:",
                "YES" if case["legacy_support_applied"] else "NO",
                "",
            )
        )
        lines.extend(_match_lines("Title Matches:", case["title_topic_signals"]))
        lines.append("")
        lines.extend(_match_lines("Body Matches:", case["body_topic_signals"]))
        lines.append("")
        lines.extend(_value_lines("Risk Topics:", case["risk_topics"]))
        lines.extend(
            (
                "",
                "Government Entity Evidence:",
                "YES" if case["government_entity_evidence"] else "NO",
                "",
                "Structured Economic Evidence:",
                "YES" if case["structured_economic_evidence"] else "NO",
                "",
            )
        )
        lines.extend(_value_lines("Reason Codes:", case["final_reason_codes"]))
        lines.append("")
        lines.extend(
            _value_lines("Supporting Signals:", case["final_supporting_signals"])
        )
        lines.append("")
        lines.extend(_value_lines("Warnings:", case["final_warnings"]))
        lines.append("")
        lines.extend(_value_lines("Diagnostic Flags:", case["diagnostic_flags"]))
        lines.append("")

    lines.extend(("## Human Adjudication Queue", ""))
    for case in analysis["human_adjudication_queue"]:
        lines.extend(
            (
                f"### Case {case['id']}",
                "",
                "Title:",
                case["title"],
                "",
                "Expected Topic:",
                case["expected_topic"],
                "",
                "Predicted Topic:",
                case["predicted_topic"],
                "",
                "Possible Competing Topics:",
                *(
                    f"- {topic}"
                    for topic in case["possible_competing_topics"]
                ),
                "",
                "Short Diagnostic Summary:",
                "Multiple primary-topic labels remain defensible from the supplied title and body.",
                "",
            )
        )

    lines.extend(("### Candidate Vocabulary Observations", ""))
    lines.extend(
        f"- {case_id}: {observation}"
        for case_id, observation in _CANDIDATE_VOCABULARY_OBSERVATIONS.items()
    )
    lines.extend(("", "## Candidate Failure Classes", ""))
    for failure_class in (
        "Legacy dependency",
        "Substring matching",
        "Vocabulary coverage",
        "Topic scoring / precedence",
        "Human-label ambiguity",
    ):
        case_ids = [
            case["id"]
            for case in analysis["mismatches"]
            if failure_class in case["failure_classes"]
        ]
        lines.extend(
            (
                f"### {failure_class}",
                "",
                ", ".join(case_ids) if case_ids else "None",
                "",
            )
        )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render a compact deterministic diagnostic summary."""
    lines = [
        "=== BATCH 02 TOPIC ERROR ANALYSIS ===",
        "",
        "Topic Mismatches:",
        str(analysis["topic_mismatches"]),
        "",
        "Legacy Contamination Suspected:",
        str(analysis["legacy_contamination_suspected"]),
        "",
        "Substring Collision Suspected:",
        str(analysis["substring_collision_suspected"]),
        "",
        "Expected Vocabulary Gap:",
        str(analysis["expected_vocabulary_gap"]),
        "",
        "Human Adjudication Required:",
        str(analysis["human_adjudication_required"]),
        "",
    ]
    for case in analysis["mismatches"]:
        flags = ",".join(case["diagnostic_flags"]) or "None"
        lines.append(
            f"{case['id']} | expected={case['expected_topic']} | "
            f"predicted={case['predicted_topic']} | flags={flags}"
        )
    return "\n".join(lines)


def main() -> int:
    """Persist deterministic error analysis and print its summary."""
    analysis = analyze_topic_errors()
    (BATCH_ROOT / "topic_error_analysis.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "topic_error_analysis.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
