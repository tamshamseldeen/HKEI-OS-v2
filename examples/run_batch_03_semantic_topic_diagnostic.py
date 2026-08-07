"""Run semantic-aware topic diagnostics for selected Batch 03 cases."""

from collections.abc import Iterable
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.workflows.editorial_semantic_topic_workflow import (
    EditorialSemanticTopicWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_03"
DIAGNOSTIC_EXPECTATIONS = (
    ("024", "HEALTH"),
    ("025", "HEALTH"),
    ("029", "EDUCATION"),
)


def _source_fields(path: Path) -> dict[str, object]:
    """Build exact category-free workflow fields from one persisted source."""
    source = parse_source(path)
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
    """Keep symbolic labels once in deterministic discovery order."""
    return list(dict.fromkeys(values))


def analyze_diagnostic(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: EditorialSemanticTopicWorkflow | None = None,
) -> dict[str, Any]:
    """Analyze exactly the three persisted semantic diagnostic cases."""
    active_workflow = workflow or EditorialSemanticTopicWorkflow()
    manifest = {case["id"]: case for case in read_manifest(batch_root)}
    cases: list[dict[str, Any]] = []
    for case_id, expected_topic in DIAGNOSTIC_EXPECTATIONS:
        result = active_workflow.process(
            **_source_fields(batch_root / manifest[case_id]["source_file"])
        )
        topic = result.topic_classification
        semantic = result.semantic_evidence
        predicted = topic.topic.value
        cases.append(
            {
                "id": case_id,
                "expected_topic": expected_topic,
                "predicted_topic": predicted,
                "confidence": topic.confidence.value,
                "match": predicted == expected_topic,
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
                "semantic_suppressions": list(semantic.all_suppressions),
                "reason_codes": list(topic.reason_codes),
                "supporting_signals": list(topic.supporting_signals),
                "warnings": list(topic.warnings),
            }
        )
    matched = sum(case["match"] for case in cases)
    total = len(cases)
    return {
        "cases": cases,
        "matched": matched,
        "mismatched": total - matched,
        "accuracy": matched / total * 100.0 if total else 0.0,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    """Return PASSED only when all three registered topics match."""
    return "PASSED" if analysis["matched"] == 3 else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic JSON without source bodies."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[str]) -> str:
    """Render ordered labels or an explicit None."""
    return ", ".join(values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the required topic comparison table and summary."""
    lines = [
        "# Batch 03 Semantic Topic Diagnostic",
        "",
        "| ID | Expected Topic | Predicted Topic | Confidence | Match | Semantic Primary | Semantic Secondary | Semantic Suppression |",
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
                    case["confidence"],
                    "YES" if case["match"] else "NO",
                    _display(case["semantic_primary_domain_candidates"]),
                    _display(case["semantic_secondary_domain_candidates"]),
                    _display(case["semantic_suppressions"]),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "## Summary",
            "",
            "Cases:",
            str(len(analysis["cases"])),
            "",
            "Matched:",
            str(analysis["matched"]),
            "",
            "Mismatched:",
            str(analysis["mismatched"]),
            "",
            "Accuracy:",
            f'{analysis["accuracy"]:.2f}%',
            "",
        )
    )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render the required concise console diagnostic."""
    lines = [
        "=== BATCH 03 SEMANTIC TOPIC DIAGNOSTIC ===",
        "",
        "Cases:",
        str(len(analysis["cases"])),
        "",
        "Matched:",
        str(analysis["matched"]),
        "",
        "Mismatched:",
        str(analysis["mismatched"]),
        "",
        "Accuracy:",
        f'{analysis["accuracy"]:.2f}%',
        "",
    ]
    lines.extend(
        f'{case["id"]} | expected={case["expected_topic"]} '
        f'| predicted={case["predicted_topic"]} '
        f'| match={"YES" if case["match"] else "NO"}'
        for case in analysis["cases"]
    )
    return "\n".join(lines)


def main() -> int:
    """Write both reports, print results, and return diagnostic status."""
    analysis = analyze_diagnostic()
    (BATCH_ROOT / "semantic_topic_diagnostic.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "semantic_topic_diagnostic.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0 if diagnostic_status(analysis) == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
