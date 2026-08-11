"""Run the advanced editorial holdout validation against Batch 04."""

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
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_04"


def _source_fields(source: ValidationSource) -> dict[str, object]:
    """Build exact category-free workflow arguments from persisted data."""
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


def _unique_labels(values: Iterable[str]) -> list[str]:
    """Keep symbolic contextual labels once in discovery order."""
    return list(dict.fromkeys(values))


def analyze_validation(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: ExperimentalSemanticEditorialAnalysisWorkflow | None = None,
) -> dict[str, Any]:
    """Evaluate every Batch 04 case using only the registered editorial labels."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    expected_by_id = {item["id"]: item for item in read_expectations(batch_root)}
    cases: list[dict[str, Any]] = []

    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        result = active_workflow.process(**_source_fields(source))
        expected = expected_by_id[source.case_id]
        topic = result.topic_classification
        editorial_format = result.format_classification
        intent = result.reader_intent_classification
        semantic = result.semantic_evidence
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
                "contextual_support_labels": _unique_labels(
                    label
                    for item in result.contextual_evidence.all_items
                    for label in item.supports
                ),
                "semantic_primary_domain_candidates": list(
                    semantic.primary_domain_candidates
                ),
                "semantic_secondary_domain_candidates": list(
                    semantic.secondary_domain_candidates
                ),
                "semantic_format_support": list(semantic.format_support),
                "semantic_format_suppression": list(semantic.format_suppression),
                "semantic_intent_support": list(semantic.intent_support),
                "semantic_suppressions": list(semantic.all_suppressions),
                "topic_reason_codes": list(topic.reason_codes),
                "topic_supporting_signals": list(topic.supporting_signals),
                "topic_warnings": list(topic.warnings),
                "format_reason_codes": list(editorial_format.reason_codes),
                "format_supporting_signals": list(
                    editorial_format.supporting_signals
                ),
                "format_warnings": list(editorial_format.warnings),
                "intent_reason_codes": list(intent.reason_codes),
                "intent_supporting_signals": list(intent.supporting_signals),
                "intent_warnings": list(intent.warnings),
            }
        )

    total = len(cases)
    percentage = lambda value: value / total * 100.0 if total else 0.0
    topic_matched = sum(case["topic_match"] for case in cases)
    format_matched = sum(case["format_match"] for case in cases)
    intent_matched = sum(case["reader_intent_match"] for case in cases)
    fully_matched = sum(case["full_match"] for case in cases)
    return {
        "batch": "batch_04",
        "case_count": total,
        "topic_matched": topic_matched,
        "topic_accuracy": percentage(topic_matched),
        "format_matched": format_matched,
        "format_accuracy": percentage(format_matched),
        "reader_intent_matched": intent_matched,
        "reader_intent_accuracy": percentage(intent_matched),
        "fully_matched_cases": fully_matched,
        "full_case_accuracy": percentage(fully_matched),
        "semantic_evidence_used": sum(
            bool(
                case["semantic_primary_domain_candidates"]
                or case["semantic_secondary_domain_candidates"]
                or case["semantic_format_support"]
                or case["semantic_intent_support"]
            )
            for case in cases
        ),
        "semantic_suppression_used": sum(
            bool(
                case["semantic_format_suppression"]
                or case["semantic_suppressions"]
            )
            for case in cases
        ),
        "cases": cases,
    }


def validation_status(analysis: dict[str, Any]) -> str:
    """Return the preregistered validation status."""
    dimensions = (
        analysis["topic_accuracy"],
        analysis["format_accuracy"],
        analysis["reader_intent_accuracy"],
    )
    if all(value == 100.0 for value in dimensions) and analysis[
        "full_case_accuracy"
    ] == 100.0:
        return "EXCELLENT"
    return "PASSED" if all(value >= 80.0 for value in dimensions) else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic JSON without source bodies or risk metadata."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[str]) -> str:
    return ", ".join(values) if values else "None"


def _mismatch_section(
    analysis: dict[str, Any], title: str, dimension: str
) -> list[str]:
    """Render one required raw mismatch section."""
    cases = [case for case in analysis["cases"] if not case[f"{dimension}_match"]]
    lines = [f"## {title}", ""]
    if not cases:
        return [*lines, "None", ""]
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
    for case in cases:
        fields: list[tuple[str, str]] = [
            ("ID", case["id"]),
            ("Expected", case[expected_key]),
            ("Predicted", case[predicted_key]),
            ("Confidence", case[f"{dimension}_confidence"]),
        ]
        if dimension == "topic":
            fields.extend(
                (
                    ("Semantic Primary Domains", _display(case["semantic_primary_domain_candidates"])),
                    ("Semantic Secondary Domains", _display(case["semantic_secondary_domain_candidates"])),
                    ("Contextual Support", _display(case["contextual_support_labels"])),
                    ("Semantic Suppressions", _display(case["semantic_suppressions"])),
                )
            )
        elif dimension == "format":
            fields.extend(
                (
                    ("Semantic Format Support", _display(case["semantic_format_support"])),
                    ("Semantic Format Suppression", _display(case["semantic_format_suppression"])),
                )
            )
        evidence_prefix = "intent" if dimension == "reader_intent" else dimension
        fields.extend(
            (
                ("Reason Codes", _display(case[f"{evidence_prefix}_reason_codes"])),
                ("Warnings", _display(case[f"{evidence_prefix}_warnings"])),
            )
        )
        for label, value in fields:
            lines.extend((f"{label}:", str(value), ""))
    return lines


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the required deterministic Batch 04 Markdown report."""
    lines = [
        "# Batch 04 Advanced Holdout Editorial Validation",
        "",
        "| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in analysis["cases"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    case["id"], case["expected_topic"], case["predicted_topic"],
                    case["expected_format"], case["predicted_format"],
                    case["expected_reader_intent"], case["predicted_reader_intent"],
                    "YES" if case["full_match"] else "NO",
                )
            )
            + " |"
        )
    lines.extend(
        (
            "", "## Summary", "", "Total Cases:", str(analysis["case_count"]), "",
            "Topic Accuracy:", f'{analysis["topic_accuracy"]:.2f}%', "",
            "Editorial Format Accuracy:", f'{analysis["format_accuracy"]:.2f}%', "",
            "Reader Intent Accuracy:", f'{analysis["reader_intent_accuracy"]:.2f}%', "",
            "Full Case Accuracy:", f'{analysis["full_case_accuracy"]:.2f}%', "",
            "Fully Matched:", str(analysis["fully_matched_cases"]), "",
            "Semantic Evidence Used:", str(analysis["semantic_evidence_used"]), "",
            "Semantic Suppression Used:", str(analysis["semantic_suppression_used"]), "",
        )
    )
    for title, dimension in (
        ("Topic Mismatches", "topic"),
        ("Format Mismatches", "format"),
        ("Reader Intent Mismatches", "reader_intent"),
    ):
        lines.extend(_mismatch_section(analysis, title, dimension))
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render deterministic console metrics and case comparisons."""
    lines = [
        "=== BATCH 04 ADVANCED HOLDOUT EDITORIAL VALIDATION ===", "",
        "Cases:", str(analysis["case_count"]), "",
        "Topic Accuracy:", f'{analysis["topic_accuracy"]:.2f}%', "",
        "Editorial Format Accuracy:", f'{analysis["format_accuracy"]:.2f}%', "",
        "Reader Intent Accuracy:", f'{analysis["reader_intent_accuracy"]:.2f}%', "",
        "Full Case Accuracy:", f'{analysis["full_case_accuracy"]:.2f}%', "",
        "Fully Matched:", str(analysis["fully_matched_cases"]), "",
    ]
    lines.extend(
        f'{case["id"]} | topic={"YES" if case["topic_match"] else "NO"} '
        f'| format={"YES" if case["format_match"] else "NO"} '
        f'| intent={"YES" if case["reader_intent_match"] else "NO"} '
        f'| full={"YES" if case["full_match"] else "NO"}'
        for case in analysis["cases"]
    )
    return "\n".join(lines)


def main() -> int:
    """Run validation, persist reports, and return its registered status."""
    analysis = analyze_validation()
    (BATCH_ROOT / "editorial_validation.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "editorial_validation.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0 if validation_status(analysis) != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
