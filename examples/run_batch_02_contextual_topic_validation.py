"""Validate experimental context-aware topic classification on Batch 02."""

from collections.abc import Iterable
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import (
    BATCH_ROOT,
    ValidationSource,
    parse_source,
    read_expectations,
    read_manifest,
)
from src.workflows.editorial_contextual_topic_workflow import (
    EditorialContextualTopicWorkflow,
)


VALIDATION_THRESHOLD = 90.0


def _source_fields(source: ValidationSource) -> dict[str, object]:
    """Build the exact metadata-free Batch 02 workflow arguments."""
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


def _unique_topic_labels(values: Iterable[str]) -> list[str]:
    """Keep recognized topic labels once in discovery order."""
    return list(dict.fromkeys(value for value in values if value.startswith("TOPIC_")))


def analyze_validation(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: EditorialContextualTopicWorkflow | None = None,
) -> dict[str, Any]:
    """Analyze all Batch 02 cases through the experimental workflow."""
    active_workflow = workflow or EditorialContextualTopicWorkflow()
    expected_by_id = {
        expectation["id"]: expectation for expectation in read_expectations(batch_root)
    }
    cases: list[dict[str, Any]] = []
    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        result = active_workflow.process(**_source_fields(source))
        classification = result.topic_classification
        support_labels = _unique_topic_labels(
            label
            for item in result.contextual_evidence.all_items
            for label in item.supports
        )
        suppression_labels = _unique_topic_labels(
            label
            for item in result.contextual_evidence.all_items
            for label in item.suppresses
        )
        expected_topic = expected_by_id[source.case_id]["topic"]
        predicted_topic = classification.topic.value
        cases.append(
            {
                "id": source.case_id,
                "expected_topic": expected_topic,
                "predicted_topic": predicted_topic,
                "confidence": classification.confidence.value,
                "match": expected_topic == predicted_topic,
                "reason_codes": list(classification.reason_codes),
                "supporting_signals": list(classification.supporting_signals),
                "warnings": list(classification.warnings),
                "contextual_support_labels": support_labels,
                "contextual_suppression_labels": suppression_labels,
            }
        )
    case_count = len(cases)
    matched = sum(case["match"] for case in cases)
    return {
        "batch": "batch_02",
        "case_count": case_count,
        "matched": matched,
        "mismatched": case_count - matched,
        "accuracy": matched / case_count * 100.0 if case_count else 0.0,
        "cases": cases,
    }


def validation_status(analysis: dict[str, Any]) -> str:
    """Return status using the inclusive 90 percent scientific threshold."""
    return "PASSED" if analysis["accuracy"] >= VALIDATION_THRESHOLD else "FAILED"


def contextual_selection_count(analysis: dict[str, Any]) -> int:
    """Count cases whose selected topic materially used contextual evidence."""
    return sum(
        "CONTEXTUAL_TOPIC_EVIDENCE" in case["reason_codes"]
        for case in analysis["cases"]
    )


def contextual_suppression_count(analysis: dict[str, Any]) -> int:
    """Count cases whose selection materially used contextual suppression."""
    return sum(
        "CONTEXTUAL_TOPIC_SUPPRESSION" in case["reason_codes"]
        for case in analysis["cases"]
    )


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic machine-readable output without source bodies."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[str]) -> str:
    """Render labels compactly with an explicit empty value."""
    return ", ".join(values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render deterministic table, summary, and mismatch details."""
    lines = [
        "# Batch 02 Context-Aware Topic Validation",
        "",
        "| ID | Expected Topic | Predicted Topic | Confidence | Match | Contextual Support | Contextual Suppression |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in analysis["cases"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    case["id"],
                    case["expected_topic"],
                    case["predicted_topic"],
                    case["confidence"],
                    "YES" if case["match"] else "NO",
                    _display(case["contextual_support_labels"]),
                    _display(case["contextual_suppression_labels"]),
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
            "Matched:",
            str(analysis["matched"]),
            "",
            "Mismatched:",
            str(analysis["mismatched"]),
            "",
            "Accuracy:",
            f"{analysis['accuracy']:.2f}%",
            "",
            "Contextual Selection Used:",
            str(contextual_selection_count(analysis)),
            "",
            "Contextual Suppression Used:",
            str(contextual_suppression_count(analysis)),
            "",
            "## Mismatches",
            "",
        )
    )
    mismatches = [case for case in analysis["cases"] if not case["match"]]
    if not mismatches:
        lines.extend(("None", ""))
    for case in mismatches:
        for label, value in (
            ("ID", case["id"]),
            ("Expected", case["expected_topic"]),
            ("Predicted", case["predicted_topic"]),
            ("Confidence", case["confidence"]),
            ("Reason Codes", _display(case["reason_codes"])),
            ("Supporting Signals", _display(case["supporting_signals"])),
            ("Warnings", _display(case["warnings"])),
            ("Contextual Support", _display(case["contextual_support_labels"])),
            (
                "Contextual Suppression",
                _display(case["contextual_suppression_labels"]),
            ),
        ):
            lines.extend((f"{label}:", value, ""))
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render the required console summary and ordered case results."""
    lines = [
        "=== BATCH 02 CONTEXT-AWARE TOPIC VALIDATION ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Matched:",
        str(analysis["matched"]),
        "",
        "Mismatched:",
        str(analysis["mismatched"]),
        "",
        "Accuracy:",
        f"{analysis['accuracy']:.2f}%",
        "",
        "Contextual Selection Used:",
        str(contextual_selection_count(analysis)),
        "",
        "Contextual Suppression Used:",
        str(contextual_suppression_count(analysis)),
        "",
    ]
    lines.extend(
        f"{case['id']} | expected={case['expected_topic']} | "
        f"predicted={case['predicted_topic']} | "
        f"match={'YES' if case['match'] else 'NO'}"
        for case in analysis["cases"]
    )
    return "\n".join(lines)


def main() -> int:
    """Run validation, persist both reports, and return threshold status."""
    analysis = analyze_validation()
    (BATCH_ROOT / "contextual_topic_validation.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "contextual_topic_validation.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0 if validation_status(analysis) == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
