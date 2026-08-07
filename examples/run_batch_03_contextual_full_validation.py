"""Run context-aware unseen validation against registered Batch 03 cases."""

from collections.abc import Iterable
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import (
    ValidationSource,
    parse_source,
    read_expectations,
    read_manifest,
)
from src.workflows.experimental_contextual_editorial_analysis_workflow import (
    ExperimentalContextualEditorialAnalysisWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_03"


def _source_fields(source: ValidationSource) -> dict[str, object]:
    """Build exact category-free workflow arguments from registered source data."""
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
        "category": None,
        "tags": (),
        "user_instruction": None,
    }


def _unique_context_labels(values: Iterable[str]) -> list[str]:
    """Keep contextual downstream labels once in discovery order."""
    return list(
        dict.fromkeys(
            value
            for value in values
            if value.startswith(("TOPIC_", "FORMAT_", "INTENT_", "CLAIM_"))
        )
    )


def analyze_validation(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: ExperimentalContextualEditorialAnalysisWorkflow | None = None,
) -> dict[str, Any]:
    """Evaluate all registered cases using exactly the experimental workflow."""
    active_workflow = workflow or ExperimentalContextualEditorialAnalysisWorkflow()
    expected_by_id = {
        expectation["id"]: expectation for expectation in read_expectations(batch_root)
    }
    cases: list[dict[str, Any]] = []
    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        result = active_workflow.process(**_source_fields(source))
        expected = expected_by_id[source.case_id]
        topic = result.topic_classification
        editorial_format = result.format_classification
        intent = result.reader_intent_classification
        topic_match = topic.topic.value == expected["topic"]
        format_match = (
            editorial_format.editorial_format.value == expected["editorial_format"]
        )
        intent_match = intent.reader_intent.value == expected["reader_intent"]
        cases.append(
            {
                "id": source.case_id,
                "expected_topic": expected["topic"],
                "predicted_topic": topic.topic.value,
                "topic_confidence": topic.confidence.value,
                "topic_match": topic_match,
                "expected_format": expected["editorial_format"],
                "predicted_format": editorial_format.editorial_format.value,
                "format_confidence": editorial_format.confidence.value,
                "format_match": format_match,
                "expected_reader_intent": expected["reader_intent"],
                "predicted_reader_intent": intent.reader_intent.value,
                "reader_intent_confidence": intent.confidence.value,
                "reader_intent_match": intent_match,
                "full_match": topic_match and format_match and intent_match,
                "contextual_support_labels": _unique_context_labels(
                    label
                    for item in result.contextual_evidence.all_items
                    for label in item.supports
                ),
                "contextual_suppression_labels": _unique_context_labels(
                    label
                    for item in result.contextual_evidence.all_items
                    for label in item.suppresses
                ),
            }
        )
    case_count = len(cases)
    topic_matched = sum(case["topic_match"] for case in cases)
    format_matched = sum(case["format_match"] for case in cases)
    intent_matched = sum(case["reader_intent_match"] for case in cases)
    fully_matched = sum(case["full_match"] for case in cases)
    percentage = lambda value: value / case_count * 100.0 if case_count else 0.0
    return {
        "batch": "batch_03",
        "case_count": case_count,
        "topic_matched": topic_matched,
        "topic_accuracy": percentage(topic_matched),
        "format_matched": format_matched,
        "format_accuracy": percentage(format_matched),
        "reader_intent_matched": intent_matched,
        "reader_intent_accuracy": percentage(intent_matched),
        "fully_matched_cases": fully_matched,
        "full_case_accuracy": percentage(fully_matched),
        "contextual_evidence_used": sum(
            bool(case["contextual_support_labels"]) for case in cases
        ),
        "contextual_suppression_used": sum(
            bool(case["contextual_suppression_labels"]) for case in cases
        ),
        "cases": cases,
    }


def validation_status(analysis: dict[str, Any]) -> str:
    """Return EXCELLENT, PASSED, or FAILED from registered thresholds."""
    dimensions = (
        analysis["topic_accuracy"],
        analysis["format_accuracy"],
        analysis["reader_intent_accuracy"],
    )
    if all(value == 100.0 for value in dimensions) and analysis[
        "full_case_accuracy"
    ] == 100.0:
        return "EXCELLENT"
    if all(value >= 80.0 for value in dimensions):
        return "PASSED"
    return "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic validation JSON without source text or prompts."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[str]) -> str:
    """Render contextual labels or explicit None."""
    return ", ".join(values) if values else "None"


def _mismatch_lines(
    analysis: dict[str, Any],
    *,
    dimension: str,
) -> list[str]:
    """Render raw mismatch details for one classification dimension."""
    mismatches = [
        case for case in analysis["cases"] if not case[f"{dimension}_match"]
    ]
    if not mismatches:
        return ["None", ""]
    expected_key = (
        "expected_reader_intent"
        if dimension == "reader_intent"
        else f"expected_{dimension}"
    )
    predicted_key = (
        "predicted_reader_intent"
        if dimension == "reader_intent"
        else f"predicted_{dimension}"
    )
    lines: list[str] = []
    for case in mismatches:
        for label, value in (
            ("ID", case["id"]),
            ("Expected", case[expected_key]),
            ("Predicted", case[predicted_key]),
            ("Confidence", case[f"{dimension}_confidence"]),
            ("Contextual Support", _display(case["contextual_support_labels"])),
            (
                "Contextual Suppression",
                _display(case["contextual_suppression_labels"]),
            ),
        ):
            lines.extend((f"{label}:", value, ""))
    return lines


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the required table, summary, and raw mismatch sections."""
    lines = [
        "# Batch 03 Context-Aware Unseen Validation",
        "",
        "| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in analysis["cases"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    case["id"],
                    case["expected_topic"],
                    case["predicted_topic"],
                    case["expected_format"],
                    case["predicted_format"],
                    case["expected_reader_intent"],
                    case["predicted_reader_intent"],
                    "YES" if case["full_match"] else "NO",
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
            "Topic Accuracy:",
            f"{analysis['topic_accuracy']:.2f}%",
            "",
            "Editorial Format Accuracy:",
            f"{analysis['format_accuracy']:.2f}%",
            "",
            "Reader Intent Accuracy:",
            f"{analysis['reader_intent_accuracy']:.2f}%",
            "",
            "Full Case Accuracy:",
            f"{analysis['full_case_accuracy']:.2f}%",
            "",
            "Fully Matched:",
            str(analysis["fully_matched_cases"]),
            "",
            "Contextual Evidence Used:",
            str(analysis["contextual_evidence_used"]),
            "",
            "Contextual Suppression Used:",
            str(analysis["contextual_suppression_used"]),
            "",
        )
    )
    for title, dimension in (
        ("Topic Mismatches", "topic"),
        ("Format Mismatches", "format"),
        ("Reader Intent Mismatches", "reader_intent"),
    ):
        lines.extend((f"## {title}", ""))
        lines.extend(_mismatch_lines(analysis, dimension=dimension))
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render required summary and one deterministic line per case."""
    lines = [
        "=== BATCH 03 CONTEXT-AWARE UNSEEN VALIDATION ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Topic Accuracy:",
        f"{analysis['topic_accuracy']:.2f}%",
        "",
        "Editorial Format Accuracy:",
        f"{analysis['format_accuracy']:.2f}%",
        "",
        "Reader Intent Accuracy:",
        f"{analysis['reader_intent_accuracy']:.2f}%",
        "",
        "Full Case Accuracy:",
        f"{analysis['full_case_accuracy']:.2f}%",
        "",
        "Fully Matched:",
        str(analysis["fully_matched_cases"]),
        "",
    ]
    for case in analysis["cases"]:
        yes_no = lambda value: "YES" if value else "NO"
        lines.append(
            f"{case['id']} | topic={yes_no(case['topic_match'])} | "
            f"format={yes_no(case['format_match'])} | "
            f"intent={yes_no(case['reader_intent_match'])} | "
            f"full={yes_no(case['full_match'])}"
        )
    return "\n".join(lines)


def main() -> int:
    """Run unseen validation, persist reports, and return registered status."""
    analysis = analyze_validation()
    (BATCH_ROOT / "contextual_full_validation.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "contextual_full_validation.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0 if validation_status(analysis) != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
