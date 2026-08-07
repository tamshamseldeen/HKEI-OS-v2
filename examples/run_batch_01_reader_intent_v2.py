"""Compare deterministic reader intent V1 and V2 across Batch 01."""

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_01_analysis import (
    BATCH_ROOT,
    BenchmarkSource,
    parse_source,
    read_manifest,
)
from src.intent.deterministic_reader_intent_classifier import (
    DeterministicReaderIntentClassifier,
)
from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


EXPECTED_READER_INTENTS: tuple[tuple[str, str], ...] = (
    ("001", "GET_UPDATE"),
    ("002", "GET_UPDATE"),
    ("003", "GET_UPDATE"),
    ("004", "GET_UPDATE"),
    ("005", "GET_UPDATE"),
    ("006", "GET_UPDATE"),
    ("007", "VERIFY_REQUIREMENTS"),
    ("008", "GET_UPDATE"),
    ("009", "FIND_RESULT"),
    ("010", "GET_UPDATE"),
)


def _source_fields(source: BenchmarkSource) -> dict[str, object]:
    """Build the exact common raw metadata mapping for Batch 01."""
    return {
        "title": source.title,
        "body": source.body,
        "source_name": source.source_name,
        "source_url": source.source_url,
        "published_at": None,
        "language": "ar",
        "country": None,
        "author": None,
        "images": (),
        "attachments": (),
        "category": source.benchmark_category,
        "tags": (),
        "user_instruction": None,
    }


def analyze_reader_intents(
    *,
    batch_root: Path = BATCH_ROOT,
    classification_workflow: EditorialClassificationWorkflow | None = None,
    topic_workflow: EditorialTopicWorkflow | None = None,
    format_workflow: EditorialFormatWorkflow | None = None,
    legacy_classifier: DeterministicReaderIntentClassifier | None = None,
    v2_classifier: DeterministicReaderIntentClassifierV2 | None = None,
    expected_intents: tuple[tuple[str, str], ...] = EXPECTED_READER_INTENTS,
) -> dict[str, Any]:
    """Run both intent classifiers over identical deterministic analysis inputs.

    Args:
        batch_root: Directory containing persisted Batch 01 inputs.
        classification_workflow: Optional legacy classification workflow.
        topic_workflow: Optional additive topic workflow.
        format_workflow: Optional additive format workflow.
        legacy_classifier: Optional existing reader-intent classifier.
        v2_classifier: Optional topic-and-format-aware classifier.
        expected_intents: Ordered benchmark-only expected reader intents.

    Returns:
        Complete machine-readable V1-versus-V2 comparison data.
    """
    classification = classification_workflow or EditorialClassificationWorkflow()
    topic = topic_workflow or EditorialTopicWorkflow()
    format_analysis = format_workflow or EditorialFormatWorkflow()
    legacy = legacy_classifier or DeterministicReaderIntentClassifier()
    v2 = v2_classifier or DeterministicReaderIntentClassifierV2()
    expected_by_id = dict(expected_intents)
    cases: list[dict[str, Any]] = []

    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        raw_fields = _source_fields(source)
        classification_result = classification.process(**raw_fields)
        topic_result = topic.process(**raw_fields)
        format_result = format_analysis.process(**raw_fields)
        ingestion = classification_result.ingestion
        content_classification = classification_result.classification
        topic_classification = topic_result.topic_classification
        format_classification = format_result.format_classification

        legacy_intent = legacy.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=content_classification,
            user_instruction=None,
        )
        v2_intent = v2.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            topic_classification=topic_classification,
            format_classification=format_classification,
            user_instruction=None,
        )
        expected = expected_by_id[source.case_id]
        legacy_value = legacy_intent.reader_intent.value
        v2_value = v2_intent.reader_intent.value
        cases.append(
            {
                "id": source.case_id,
                "benchmark_category": source.benchmark_category,
                "legacy_content_type": content_classification.content_type.value,
                "topic": topic_classification.topic.value,
                "editorial_format": format_classification.editorial_format.value,
                "risk_level": ingestion.assessment.risk_level.value,
                "expected_reader_intent": expected,
                "legacy_reader_intent": legacy_value,
                "legacy_confidence": legacy_intent.confidence.value,
                "v2_reader_intent": v2_value,
                "v2_confidence": v2_intent.confidence.value,
                "legacy_match": legacy_value == expected,
                "v2_match": v2_value == expected,
                "intent_changed": legacy_value != v2_value,
                "v2_reason_codes": list(v2_intent.reason_codes),
                "v2_supporting_signals": list(v2_intent.supporting_signals),
                "v2_warnings": list(v2_intent.warnings),
            }
        )

    total = len(cases)
    legacy_matched = sum(bool(case["legacy_match"]) for case in cases)
    v2_matched = sum(bool(case["v2_match"]) for case in cases)
    improvements = sum(
        not case["legacy_match"] and case["v2_match"] for case in cases
    )
    regressions = sum(
        case["legacy_match"] and not case["v2_match"] for case in cases
    )
    return {
        "batch": "batch_01",
        "case_count": total,
        "legacy_matched": legacy_matched,
        "legacy_accuracy": legacy_matched / total * 100.0 if total else 0.0,
        "v2_matched": v2_matched,
        "v2_accuracy": v2_matched / total * 100.0 if total else 0.0,
        "intent_changed": sum(bool(case["intent_changed"]) for case in cases),
        "regressions": regressions,
        "improvements": improvements,
        "cases": cases,
    }


def benchmark_status(analysis: dict[str, Any]) -> str:
    """Return PASSED only when all three migration success criteria hold."""
    passed = (
        analysis["v2_accuracy"] > analysis["legacy_accuracy"]
        and analysis["v2_accuracy"] == 100.0
        and analysis["regressions"] == 0
    )
    return "PASSED" if passed else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic UTF-8 comparison JSON without source content."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _changed_cases(
    analysis: dict[str, Any],
    *,
    improvement: bool,
) -> tuple[dict[str, Any], ...]:
    """Return improvements or regressions in unchanged manifest order."""
    return tuple(
        case
        for case in analysis["cases"]
        if (
            (not case["legacy_match"] and case["v2_match"])
            if improvement
            else (case["legacy_match"] and not case["v2_match"])
        )
    )


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render deterministic comparison table, summary, and changed cases."""
    lines = [
        "# Batch 01 Reader Intent V1 vs V2",
        "",
        "| ID | Category | Legacy Type | Topic | Format | Expected Intent | Legacy Intent | V2 Intent | Legacy Match | V2 Match | Changed |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in analysis["cases"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    case["id"],
                    case["benchmark_category"],
                    case["legacy_content_type"],
                    case["topic"],
                    case["editorial_format"],
                    case["expected_reader_intent"],
                    case["legacy_reader_intent"],
                    case["v2_reader_intent"],
                    "YES" if case["legacy_match"] else "NO",
                    "YES" if case["v2_match"] else "NO",
                    "YES" if case["intent_changed"] else "NO",
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "## Summary",
            "",
            "Total Cases:",
            str(analysis["case_count"]),
            "",
            "Legacy Matched:",
            str(analysis["legacy_matched"]),
            "",
            "Legacy Accuracy:",
            f"{analysis['legacy_accuracy']:.2f}%",
            "",
            "V2 Matched:",
            str(analysis["v2_matched"]),
            "",
            "V2 Accuracy:",
            f"{analysis['v2_accuracy']:.2f}%",
            "",
            "Intent Changed:",
            str(analysis["intent_changed"]),
            "",
            "Improvements:",
            str(analysis["improvements"]),
            "",
            "Regressions:",
            str(analysis["regressions"]),
            "",
            "## Improvements",
            "",
        )
    )
    improvements = _changed_cases(analysis, improvement=True)
    if improvements:
        lines.extend(
            f"{case['id']}: {case['legacy_reader_intent']} → {case['v2_reader_intent']}"
            for case in improvements
        )
    else:
        lines.append("None")
    lines.extend(("", "## Regressions", ""))
    regressions = _changed_cases(analysis, improvement=False)
    if regressions:
        lines.extend(
            f"{case['id']}: {case['legacy_reader_intent']} → {case['v2_reader_intent']}"
            for case in regressions
        )
    else:
        lines.append("None")
    lines.append("")
    return "\n".join(lines)


def _detail_items(label: str, values: list[str]) -> list[str]:
    """Return labeled diagnostic values as console bullet lines or None."""
    return [label, *(f"- {value}" for value in values)] if values else [label, "None"]


def render_console(analysis: dict[str, Any]) -> str:
    """Render summary, cases, and full regression or V2 mismatch details."""
    lines = [
        "=== BATCH 01 READER INTENT V2 ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Legacy Accuracy:",
        f"{analysis['legacy_accuracy']:.2f}%",
        "",
        "V2 Accuracy:",
        f"{analysis['v2_accuracy']:.2f}%",
        "",
        "Intent Changed:",
        str(analysis["intent_changed"]),
        "",
        "Improvements:",
        str(analysis["improvements"]),
        "",
        "Regressions:",
        str(analysis["regressions"]),
        "",
        "Status:",
        benchmark_status(analysis),
        "",
    ]
    for case in analysis["cases"]:
        lines.append(
            f"{case['id']} | expected={case['expected_reader_intent']} | "
            f"legacy={case['legacy_reader_intent']} | "
            f"v2={case['v2_reader_intent']} | "
            f"changed={'YES' if case['intent_changed'] else 'NO'}"
        )

    details = tuple(
        case
        for case in analysis["cases"]
        if not case["v2_match"]
        or (case["legacy_match"] and not case["v2_match"])
    )
    if details:
        lines.extend(("", "=== V2 MISMATCH DETAILS ==="))
        for case in details:
            lines.extend(
                (
                    "",
                    "Case:",
                    case["id"],
                    "",
                    "Category:",
                    case["benchmark_category"],
                    "",
                    "Expected:",
                    case["expected_reader_intent"],
                    "",
                    "Legacy:",
                    case["legacy_reader_intent"],
                    "",
                    "V2:",
                    case["v2_reader_intent"],
                    "",
                    "V2 Confidence:",
                    case["v2_confidence"],
                    "",
                )
            )
            lines.extend(_detail_items("Reason Codes:", case["v2_reason_codes"]))
            lines.append("")
            lines.extend(
                _detail_items(
                    "Supporting Signals:",
                    case["v2_supporting_signals"],
                )
            )
            lines.append("")
            lines.extend(_detail_items("Warnings:", case["v2_warnings"]))
    return "\n".join(lines)


def main() -> int:
    """Analyze Batch 01, persist comparison reports, and print benchmark output."""
    analysis = analyze_reader_intents()
    (BATCH_ROOT / "reader_intent_v2_analysis.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "reader_intent_v2_analysis.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0 if benchmark_status(analysis) == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
