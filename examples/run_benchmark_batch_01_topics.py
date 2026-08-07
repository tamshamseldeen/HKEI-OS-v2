"""Generate deterministic topic benchmark reports for Batch 01."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_01_analysis import (
    BATCH_ROOT,
    parse_source,
    read_manifest,
)
from src.topic.topic_confidence import TopicConfidence
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


EXPECTED_TOPICS: tuple[tuple[str, str], ...] = (
    ("001", "ECONOMY"),
    ("002", "ECONOMY"),
    ("003", "TECHNOLOGY"),
    ("004", "WEATHER"),
    ("005", "GOVERNMENT"),
    ("006", "ECONOMY"),
    ("007", "ECONOMY"),
    ("008", "CULTURE"),
    ("009", "SPORTS"),
    ("010", "ECONOMY"),
)


def analyze_topics(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: EditorialTopicWorkflow | None = None,
    expected_topics: tuple[tuple[str, str], ...] = EXPECTED_TOPICS,
) -> dict[str, Any]:
    """Analyze persisted cases and compare predictions with benchmark labels.

    Args:
        batch_root: Directory containing persisted Batch 01 inputs.
        workflow: Optional topic workflow supplied for isolated testing.
        expected_topics: Ordered benchmark-only expected topic labels.

    Returns:
        Complete machine-readable topic benchmark data.
    """
    active_workflow = workflow if workflow is not None else EditorialTopicWorkflow()
    expected_by_id = dict(expected_topics)
    analyzed_cases: list[dict[str, object]] = []
    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        result = active_workflow.process(
            title=source.title,
            body=source.body,
            source_name=source.source_name,
            source_url=source.source_url,
            published_at=None,
            language="ar",
            country=None,
            author=None,
            images=(),
            attachments=(),
            category=source.benchmark_category,
            tags=(),
            user_instruction=None,
        )
        topic = result.topic_classification
        expected = expected_by_id[source.case_id]
        predicted = topic.topic.value
        analyzed_cases.append(
            {
                "id": source.case_id,
                "benchmark_category": source.benchmark_category,
                "expected_topic": expected,
                "predicted_topic": predicted,
                "confidence": topic.confidence.value,
                "match": predicted == expected,
                "reason_codes": list(topic.reason_codes),
                "supporting_signals": list(topic.supporting_signals),
                "warnings": list(topic.warnings),
            }
        )

    matched = sum(bool(case["match"]) for case in analyzed_cases)
    total = len(analyzed_cases)
    return {
        "batch": "batch_01",
        "case_count": total,
        "matched": matched,
        "mismatched": total - matched,
        "accuracy": matched / total * 100.0 if total else 0.0,
        "cases": analyzed_cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic UTF-8 topic benchmark JSON."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _unique(values: list[str]) -> tuple[str, ...]:
    """Remove duplicate warning codes while preserving their order."""
    return tuple(dict.fromkeys(values))


def _summary(analysis: dict[str, Any]) -> dict[str, object]:
    """Calculate deterministic topic and confidence summary data."""
    cases = analysis["cases"]
    topic_distribution: dict[str, int] = {}
    for case in cases:
        predicted = case["predicted_topic"]
        topic_distribution[predicted] = topic_distribution.get(predicted, 0) + 1
    confidence_distribution = Counter(case["confidence"] for case in cases)
    conflict_codes = {"CATEGORY_TOPIC_CONFLICT", "CONFLICTING_TOPIC_SIGNALS"}
    return {
        "topic_distribution": topic_distribution,
        "confidence_distribution": confidence_distribution,
        "conflict_warnings": sum(
            bool(conflict_codes.intersection(case["warnings"])) for case in cases
        ),
        "low_confidence": confidence_distribution[TopicConfidence.LOW.value],
    }


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the deterministic topic table and benchmark summary."""
    lines = [
        "# Batch 01 Topic Benchmark",
        "",
        "| ID | Category | Expected Topic | Predicted Topic | Confidence | Match | Warnings |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in analysis["cases"]:
        warnings = _unique(case["warnings"])
        lines.append(
            "| "
            + " | ".join(
                (
                    case["id"],
                    case["benchmark_category"],
                    case["expected_topic"],
                    case["predicted_topic"],
                    case["confidence"],
                    "YES" if case["match"] else "NO",
                    ", ".join(warnings) if warnings else "None",
                )
            )
            + " |"
        )

    summary = _summary(analysis)
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
            "Topic Distribution:",
        )
    )
    for topic, count in summary["topic_distribution"].items():
        lines.append(f"{topic}: {count}")
    lines.extend(("", "Confidence Distribution:"))
    for confidence in TopicConfidence:
        count = summary["confidence_distribution"][confidence.value]
        lines.append(f"{confidence.value}: {count}")
    lines.extend(
        (
            "",
            "Conflict Warnings:",
            str(summary["conflict_warnings"]),
            "",
            "Low Confidence:",
            str(summary["low_confidence"]),
            "",
        )
    )
    return "\n".join(lines)


def _print_items(label: str, values: list[str]) -> list[str]:
    """Return console lines for one labeled list or ``None``."""
    return [label, *(f"- {value}" for value in values)] if values else [label, "None"]


def render_console(analysis: dict[str, Any]) -> str:
    """Render exact console output, including detailed mismatches when present."""
    lines = [
        "=== BATCH 01 TOPIC BENCHMARK ===",
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
    ]
    for case in analysis["cases"]:
        lines.append(
            f"{case['id']} | expected={case['expected_topic']} | "
            f"predicted={case['predicted_topic']} | "
            f"confidence={case['confidence']} | "
            f"match={'YES' if case['match'] else 'NO'}"
        )

    mismatches = [case for case in analysis["cases"] if not case["match"]]
    if mismatches:
        lines.extend(("", "=== MISMATCHES ==="))
        for case in mismatches:
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
                    case["expected_topic"],
                    "",
                    "Predicted:",
                    case["predicted_topic"],
                    "",
                    "Confidence:",
                    case["confidence"],
                    "",
                )
            )
            lines.extend(_print_items("Reason Codes:", case["reason_codes"]))
            lines.append("")
            lines.extend(
                _print_items("Supporting Signals:", case["supporting_signals"])
            )
            lines.append("")
            lines.extend(_print_items("Warnings:", case["warnings"]))
    return "\n".join(lines)


def run_benchmark(analysis: dict[str, Any]) -> int:
    """Print benchmark output and return zero only when all cases match."""
    print(render_console(analysis))
    return 0 if analysis["mismatched"] == 0 else 1


def main() -> int:
    """Analyze Batch 01, persist topic reports, and print benchmark results."""
    analysis = analyze_topics()
    (BATCH_ROOT / "topic_analysis.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "topic_analysis.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    return run_benchmark(analysis)


if __name__ == "__main__":
    raise SystemExit(main())
