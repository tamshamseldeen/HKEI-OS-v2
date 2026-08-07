"""Run deterministic unseen validation against registered Batch 02 labels."""

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.intent.deterministic_reader_intent_classifier_v2 import (
    DeterministicReaderIntentClassifierV2,
)
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_02"
VALIDATION_THRESHOLD = 80.0


@dataclass(frozen=True)
class ValidationSource:
    """Represent one parsed Batch 02 source without inferred metadata."""

    case_id: str
    title: str
    body: str
    source_name: str
    source_url: str


def read_manifest(batch_root: Path = BATCH_ROOT) -> tuple[dict[str, str], ...]:
    """Read ordered local Batch 02 manifest entries.

    Args:
        batch_root: Directory containing the frozen validation dataset.

    Returns:
        Ordered manifest case mappings.
    """
    manifest = json.loads(
        (batch_root / "manifest.json").read_text(encoding="utf-8")
    )
    return tuple(manifest["cases"])


def read_expectations(
    batch_root: Path = BATCH_ROOT,
) -> tuple[dict[str, str], ...]:
    """Read pre-registered Batch 02 expectations without modification.

    Args:
        batch_root: Directory containing the frozen validation dataset.

    Returns:
        Ordered expectation mappings.
    """
    expected = json.loads(
        (batch_root / "expected.json").read_text(encoding="utf-8")
    )
    return tuple(expected["expectations"])


def parse_source(path: Path) -> ValidationSource:
    """Parse one local source in the exact Batch 02 Markdown format.

    Args:
        path: Persisted source Markdown path.

    Returns:
        Source fields exactly as supplied in the file.
    """
    content = path.read_text(encoding="utf-8")
    title_part, remainder = content.split("\n# Body\n", maxsplit=1)
    body_part, metadata = remainder.split("\n# Metadata\n", maxsplit=1)
    metadata_lines = [line for line in metadata.splitlines() if line]
    return ValidationSource(
        case_id=metadata_lines[5],
        title=title_part.removeprefix("# Title\n").strip(),
        body=body_part.strip(),
        source_name=metadata_lines[1],
        source_url=metadata_lines[3],
    )


def _source_fields(source: ValidationSource) -> dict[str, object]:
    """Build the exact category-free metadata mapping for validation."""
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


def analyze_validation(
    *,
    batch_root: Path = BATCH_ROOT,
    topic_workflow: EditorialTopicWorkflow | None = None,
    format_workflow: EditorialFormatWorkflow | None = None,
    reader_intent_classifier: DeterministicReaderIntentClassifierV2 | None = None,
) -> dict[str, Any]:
    """Evaluate current deterministic classifiers on the unseen dataset.

    Args:
        batch_root: Directory containing frozen inputs and expectations.
        topic_workflow: Optional topic workflow supplied for isolated tests.
        format_workflow: Optional format workflow supplied for isolated tests.
        reader_intent_classifier: Optional V2 classifier supplied for tests.

    Returns:
        Machine-readable validation results and calculated metrics.
    """
    topic = topic_workflow or EditorialTopicWorkflow()
    format_analysis = format_workflow or EditorialFormatWorkflow()
    intent_classifier = (
        reader_intent_classifier or DeterministicReaderIntentClassifierV2()
    )
    expected_by_id = {
        expectation["id"]: expectation
        for expectation in read_expectations(batch_root)
    }
    cases: list[dict[str, Any]] = []

    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        fields = _source_fields(source)
        topic_result = topic.process(**fields)
        format_result = format_analysis.process(**fields)
        topic_classification = topic_result.topic_classification
        format_classification = format_result.format_classification
        ingestion = topic_result.classification_result.ingestion
        reader_intent = intent_classifier.classify(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            topic_classification=topic_classification,
            format_classification=format_classification,
            user_instruction=None,
        )
        expected = expected_by_id[source.case_id]
        predicted_topic = topic_classification.topic.value
        predicted_format = format_classification.editorial_format.value
        predicted_intent = reader_intent.reader_intent.value
        topic_match = predicted_topic == expected["topic"]
        format_match = predicted_format == expected["editorial_format"]
        intent_match = predicted_intent == expected["reader_intent"]
        cases.append(
            {
                "id": source.case_id,
                "source_name": source.source_name,
                "expected_topic": expected["topic"],
                "predicted_topic": predicted_topic,
                "topic_confidence": topic_classification.confidence.value,
                "topic_match": topic_match,
                "topic_reason_codes": list(topic_classification.reason_codes),
                "topic_warnings": list(topic_classification.warnings),
                "expected_format": expected["editorial_format"],
                "predicted_format": predicted_format,
                "format_confidence": format_classification.confidence.value,
                "format_match": format_match,
                "format_reason_codes": list(format_classification.reason_codes),
                "format_warnings": list(format_classification.warnings),
                "expected_reader_intent": expected["reader_intent"],
                "predicted_reader_intent": predicted_intent,
                "reader_intent_confidence": reader_intent.confidence.value,
                "reader_intent_match": intent_match,
                "reader_intent_reason_codes": list(reader_intent.reason_codes),
                "reader_intent_warnings": list(reader_intent.warnings),
                "case_match": topic_match and format_match and intent_match,
            }
        )

    case_count = len(cases)
    topic_matched = sum(bool(case["topic_match"]) for case in cases)
    format_matched = sum(bool(case["format_match"]) for case in cases)
    intent_matched = sum(bool(case["reader_intent_match"]) for case in cases)
    fully_matched = sum(bool(case["case_match"]) for case in cases)
    percentage = lambda matched: matched / case_count * 100.0 if case_count else 0.0
    return {
        "batch": "batch_02",
        "case_count": case_count,
        "topic_matched": topic_matched,
        "topic_accuracy": percentage(topic_matched),
        "format_matched": format_matched,
        "format_accuracy": percentage(format_matched),
        "reader_intent_matched": intent_matched,
        "reader_intent_accuracy": percentage(intent_matched),
        "fully_matched_cases": fully_matched,
        "full_case_accuracy": percentage(fully_matched),
        "topic_mismatches": case_count - topic_matched,
        "format_mismatches": case_count - format_matched,
        "reader_intent_mismatches": case_count - intent_matched,
        "cases": cases,
    }


def validation_status(analysis: dict[str, Any]) -> str:
    """Apply the inclusive 80 percent threshold to all three dimensions."""
    passed = all(
        analysis[key] >= VALIDATION_THRESHOLD
        for key in (
            "topic_accuracy",
            "format_accuracy",
            "reader_intent_accuracy",
        )
    )
    return "PASSED" if passed else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic validation JSON without source content."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _detail_values(label: str, values: list[str]) -> list[str]:
    """Render a mismatch tuple field as bullets or an explicit None."""
    return [label, *(f"- {value}" for value in values)] if values else [label, "None"]


def _mismatch_section(
    title: str,
    cases: list[dict[str, Any]],
    *,
    prefix: str,
) -> list[str]:
    """Render one complete Markdown mismatch section."""
    mismatches = [case for case in cases if not case[f"{prefix}_match"]]
    lines = [f"## {title}", ""]
    if not mismatches:
        return [*lines, "None", ""]
    for case in mismatches:
        expected_key = (
            "expected_reader_intent"
            if prefix == "reader_intent"
            else f"expected_{prefix}"
        )
        predicted_key = (
            "predicted_reader_intent"
            if prefix == "reader_intent"
            else f"predicted_{prefix}"
        )
        lines.extend(
            (
                "ID:",
                case["id"],
                "",
                "Expected:",
                case[expected_key],
                "",
                "Predicted:",
                case[predicted_key],
                "",
                "Confidence:",
                case[f"{prefix}_confidence"],
                "",
            )
        )
        lines.extend(_detail_values("Reason Codes:", case[f"{prefix}_reason_codes"]))
        lines.append("")
        lines.extend(_detail_values("Warnings:", case[f"{prefix}_warnings"]))
        lines.append("")
    return lines


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the validation table, summary, and raw mismatch details."""
    lines = [
        "# Batch 02 Unseen Validation",
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
                    "YES" if case["case_match"] else "NO",
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
            "Fully Matched Cases:",
            str(analysis["fully_matched_cases"]),
            "",
            "Full Case Accuracy:",
            f"{analysis['full_case_accuracy']:.2f}%",
            "",
        )
    )
    lines.extend(
        _mismatch_section(
            "Topic Mismatches",
            analysis["cases"],
            prefix="topic",
        )
    )
    lines.extend(
        _mismatch_section(
            "Editorial Format Mismatches",
            analysis["cases"],
            prefix="format",
        )
    )
    lines.extend(
        _mismatch_section(
            "Reader Intent Mismatches",
            analysis["cases"],
            prefix="reader_intent",
        )
    )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render required unseen-validation summary and per-case outcomes."""
    lines = [
        "=== BATCH 02 UNSEEN VALIDATION ===",
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
        "Status:",
        validation_status(analysis),
        "",
    ]
    for case in analysis["cases"]:
        yes_no = lambda value: "YES" if value else "NO"
        lines.append(
            f"{case['id']} | topic={yes_no(case['topic_match'])} | "
            f"format={yes_no(case['format_match'])} | "
            f"intent={yes_no(case['reader_intent_match'])} | "
            f"full={yes_no(case['case_match'])}"
        )
    return "\n".join(lines)


def main() -> int:
    """Run validation, persist raw reports, and return threshold status."""
    analysis = analyze_validation()
    (BATCH_ROOT / "validation.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "validation.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0 if validation_status(analysis) == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
