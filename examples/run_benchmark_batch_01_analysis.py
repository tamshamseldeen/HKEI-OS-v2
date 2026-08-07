"""Generate deterministic editorial analysis reports for benchmark batch 01."""

from collections import Counter
from dataclasses import dataclass, fields
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.assessment.risk_level import RiskLevel
from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.strategy.editorial_strategy import EditorialStrategy
from src.workflows.experimental_editorial_strategy_workflow import (
    ExperimentalEditorialStrategyWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_01"
_STRATEGY_METADATA_FIELDS = {"reason_codes", "warnings"}


@dataclass(frozen=True)
class BenchmarkSource:
    """Represent parsed source material and metadata from one benchmark file."""

    case_id: str
    title: str
    body: str
    source_name: str
    source_url: str
    benchmark_category: str


def read_manifest(batch_root: Path = BATCH_ROOT) -> tuple[dict[str, str], ...]:
    """Read ordered case entries from the local batch manifest.

    Args:
        batch_root: Directory containing the batch manifest and case files.

    Returns:
        Ordered manifest case mappings.
    """
    manifest = json.loads(
        (batch_root / "manifest.json").read_text(encoding="utf-8")
    )
    return tuple(manifest["cases"])


def parse_source(path: Path) -> BenchmarkSource:
    """Parse only the established benchmark source Markdown format.

    Args:
        path: Local source Markdown path.

    Returns:
        Parsed source fields without rewriting their values.
    """
    content = path.read_text(encoding="utf-8")
    title_part, remainder = content.split("\n# Body\n", maxsplit=1)
    body_part, metadata = remainder.split("\n# Metadata\n", maxsplit=1)
    metadata_lines = [line for line in metadata.splitlines() if line]
    return BenchmarkSource(
        case_id=metadata_lines[7],
        title=title_part.removeprefix("# Title\n").strip(),
        body=body_part.strip(),
        source_name=metadata_lines[1],
        source_url=metadata_lines[3],
        benchmark_category=metadata_lines[5],
    )


def _strategy_record(strategy: EditorialStrategy) -> dict[str, object]:
    """Return the exact report fields for one editorial strategy."""
    return {
        "article_length": strategy.article_length.value,
        "article_depth": strategy.article_depth.value,
        "writing_mode": strategy.writing_mode.value,
        "target_word_count": strategy.target_word_count,
        "warnings": list(strategy.warnings),
    }


def _strategy_changed(base: EditorialStrategy, adapted: EditorialStrategy) -> bool:
    """Compare operational strategy values while ignoring explanatory metadata."""
    return any(
        getattr(base, field.name) != getattr(adapted, field.name)
        for field in fields(EditorialStrategy)
        if field.name not in _STRATEGY_METADATA_FIELDS
    )


def analyze_batch(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: ExperimentalEditorialStrategyWorkflow | None = None,
) -> dict[str, Any]:
    """Analyze every persisted source using only deterministic workflows.

    Args:
        batch_root: Directory containing the batch input files.
        workflow: Optional experimental workflow supplied for isolated testing.

    Returns:
        Complete machine-readable batch analysis data.
    """
    active_workflow = (
        workflow if workflow is not None else ExperimentalEditorialStrategyWorkflow()
    )
    analyzed_cases: list[dict[str, Any]] = []
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
        strategy_result = result.strategy_result
        intent_result = strategy_result.intent_result
        classification_result = intent_result.classification_result
        ingestion = classification_result.ingestion
        assessment = ingestion.assessment
        content_classification = classification_result.classification
        format_classification = result.format_result.format_classification
        reader_intent = intent_result.reader_intent
        base_strategy = strategy_result.strategy
        adapted_strategy = result.adapted_strategy
        analyzed_cases.append(
            {
                "id": source.case_id,
                "source_name": source.source_name,
                "benchmark_category": source.benchmark_category,
                "risk_level": assessment.risk_level.value,
                "risk_topics": list(assessment.risk_topics),
                "risk_warnings": list(assessment.warnings),
                "generation_allowed": assessment.generation_allowed,
                "content_type": content_classification.content_type.value,
                "content_confidence": content_classification.confidence.value,
                "content_warnings": list(content_classification.warnings),
                "editorial_format": format_classification.editorial_format.value,
                "format_confidence": format_classification.confidence.value,
                "format_warnings": list(format_classification.warnings),
                "reader_intent": reader_intent.reader_intent.value,
                "reader_intent_confidence": reader_intent.confidence.value,
                "reader_intent_warnings": list(reader_intent.warnings),
                "base_strategy": _strategy_record(base_strategy),
                "adapted_strategy": _strategy_record(adapted_strategy),
                "_strategy_changed": _strategy_changed(
                    base_strategy,
                    adapted_strategy,
                ),
            }
        )
    return {
        "batch": "batch_01",
        "case_count": len(analyzed_cases),
        "cases": analyzed_cases,
    }


def _public_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Remove internal rendering fields from machine-readable report data."""
    return {
        "batch": analysis["batch"],
        "case_count": analysis["case_count"],
        "cases": [
            {key: value for key, value in case.items() if not key.startswith("_")}
            for case in analysis["cases"]
        ],
    }


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic UTF-8 JSON without source bodies or prompts."""
    return json.dumps(
        _public_analysis(analysis),
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _strategy_summary(strategy: dict[str, object]) -> str:
    """Render one strategy in the required compact order."""
    return "/".join(
        (
            str(strategy["article_length"]),
            str(strategy["article_depth"]),
            str(strategy["writing_mode"]),
            str(strategy["target_word_count"]),
        )
    )


def _unique_warnings(case: dict[str, Any]) -> tuple[str, ...]:
    """Collect every warning code once in stable report-field order."""
    warnings = (
        *case["risk_warnings"],
        *case["content_warnings"],
        *case["format_warnings"],
        *case["reader_intent_warnings"],
        *case["base_strategy"]["warnings"],
        *case["adapted_strategy"]["warnings"],
    )
    return tuple(dict.fromkeys(warnings))


def _summary(analysis: dict[str, Any]) -> dict[str, object]:
    """Calculate deterministic summary values from analyzed case data."""
    cases = analysis["cases"]
    risk_distribution = Counter(case["risk_level"] for case in cases)
    format_distribution = Counter(case["editorial_format"] for case in cases)
    intent_distribution = Counter(case["reader_intent"] for case in cases)
    changed = sum(bool(case["_strategy_changed"]) for case in cases)
    return {
        "risk_distribution": risk_distribution,
        "format_distribution": format_distribution,
        "intent_distribution": intent_distribution,
        "generation_blocked": sum(
            not case["generation_allowed"] for case in cases
        ),
        "strategy_changed": changed,
        "strategy_unchanged": len(cases) - changed,
    }


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the deterministic human-readable analysis table and summary."""
    cases = analysis["cases"]
    lines = [
        "# Batch 01 Editorial Analysis",
        "",
        "| ID | Category | Risk | Content Type | Editorial Format | Reader Intent | Base Strategy | Adapted Strategy | Warnings |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        warnings = _unique_warnings(case)
        lines.append(
            "| "
            + " | ".join(
                (
                    case["id"],
                    case["benchmark_category"],
                    case["risk_level"],
                    case["content_type"],
                    case["editorial_format"],
                    case["reader_intent"],
                    _strategy_summary(case["base_strategy"]),
                    _strategy_summary(case["adapted_strategy"]),
                    ", ".join(warnings) if warnings else "None",
                )
            )
            + " |"
        )

    summary = _summary(analysis)
    risk_distribution = summary["risk_distribution"]
    format_distribution = summary["format_distribution"]
    intent_distribution = summary["intent_distribution"]
    lines.extend(
        (
            "",
            "## Summary",
            "",
            "Total Cases:",
            str(analysis["case_count"]),
            "",
            "Risk Distribution:",
        )
    )
    for risk_level in RiskLevel:
        lines.append(f"{risk_level.value}: {risk_distribution[risk_level.value]}")
    lines.extend(("", "Editorial Format Distribution:"))
    for editorial_format in EditorialFormat:
        count = format_distribution[editorial_format.value]
        if count:
            lines.append(f"{editorial_format.value}: {count}")
    lines.extend(("", "Reader Intent Distribution:"))
    for reader_intent in ReaderIntent:
        count = intent_distribution[reader_intent.value]
        if count:
            lines.append(f"{reader_intent.value}: {count}")
    lines.extend(
        (
            "",
            "Generation Blocked:",
            str(summary["generation_blocked"]),
            "",
            "Format Strategy Changed:",
            str(summary["strategy_changed"]),
            "",
            "Format Strategy Unchanged:",
            str(summary["strategy_unchanged"]),
            "",
        )
    )
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render the exact deterministic console summary and case lines."""
    summary = _summary(analysis)
    risk_distribution = summary["risk_distribution"]
    lines = [
        "=== BATCH 01 ANALYSIS ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Risk Distribution:",
    ]
    for risk_level in RiskLevel:
        lines.append(f"{risk_level.value}: {risk_distribution[risk_level.value]}")
    lines.extend(
        (
            "",
            "Generation Blocked:",
            str(summary["generation_blocked"]),
            "",
            "Format Strategy Changed:",
            str(summary["strategy_changed"]),
            "",
            "Format Strategy Unchanged:",
            str(summary["strategy_unchanged"]),
            "",
        )
    )
    for case in analysis["cases"]:
        lines.append(
            " | ".join(
                (
                    case["id"],
                    case["risk_level"],
                    case["content_type"],
                    case["editorial_format"],
                    case["reader_intent"],
                    _strategy_summary(case["adapted_strategy"]),
                )
            )
        )
    return "\n".join(lines)


def main() -> int:
    """Analyze batch 01, persist both reports, and print the console summary."""
    analysis = analyze_batch()
    (BATCH_ROOT / "analysis.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "analysis.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
