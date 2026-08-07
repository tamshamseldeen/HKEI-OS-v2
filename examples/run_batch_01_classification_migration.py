"""Generate deterministic Batch 01 classification migration diagnostics."""

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
from src.classification.content_type import ContentType
from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.strategy.writing_mode import WritingMode
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_intent_workflow import EditorialIntentWorkflow
from src.workflows.editorial_strategy_workflow import EditorialStrategyWorkflow
from src.workflows.editorial_topic_workflow import EditorialTopicWorkflow


_LEGACY_TOPIC_MAPPING = {
    ContentType.SPORTS_NEWS.value: "SPORTS",
    ContentType.TECHNOLOGY_NEWS.value: "TECHNOLOGY",
    ContentType.ECONOMY_NEWS.value: "ECONOMY",
    ContentType.HEALTH_CONTENT.value: "HEALTH",
    ContentType.GOVERNMENT_SERVICE_CONTENT.value: "GOVERNMENT",
}

_LEGACY_FORMAT_MAPPING = {
    ContentType.BREAKING_NEWS.value: EditorialFormat.BREAKING.value,
    ContentType.EXPLAINER.value: EditorialFormat.EXPLAINER.value,
    ContentType.FACT_CHECK.value: EditorialFormat.FACT_CHECK.value,
    ContentType.PUBLIC_SERVICE_NEWS.value: EditorialFormat.SERVICE.value,
    ContentType.TRENDING_SOCIAL_CLAIM.value: EditorialFormat.TREND_UPDATE.value,
}

_RISK_MIXING_TYPES = {
    ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT.value,
    ContentType.HEALTH_CONTENT.value,
}

_IMPACT_TERMS = ("تأثير", "تداعيات", "ماذا يعني", "انعكاس", "الأثر")


def _source_fields(source: BenchmarkSource) -> dict[str, object]:
    """Build the exact shared raw fields for all five workflows."""
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


def _impact_treatment_supported(
    *,
    editorial_format: str,
    title: str,
    body: str,
) -> bool:
    """Return whether format or two supplied impact terms justify treatment."""
    if editorial_format in (
        EditorialFormat.ANALYSIS.value,
        EditorialFormat.EXPLAINER.value,
    ):
        return True
    text = f"{title}\n{body}".lower()
    return sum(term in text for term in _IMPACT_TERMS) >= 2


def _diagnose(
    *,
    legacy_content_type: str,
    topic: str,
    editorial_format: str,
    reader_intent: str,
    risk_level: str,
    writing_mode: str,
    title: str,
    body: str,
) -> dict[str, bool]:
    """Apply only the documented deterministic migration diagnoses."""
    implied_topic = _LEGACY_TOPIC_MAPPING.get(legacy_content_type)
    implied_format = _LEGACY_FORMAT_MAPPING.get(legacy_content_type)
    legacy_topic_conflict = implied_topic is not None and implied_topic != topic
    legacy_format_conflict = (
        implied_format is not None and implied_format != editorial_format
    )
    legacy_risk_mixing = legacy_content_type in _RISK_MIXING_TYPES

    sports_intent_suspect = (
        legacy_content_type == ContentType.SPORTS_NEWS.value
        and reader_intent == ReaderIntent.FIND_RESULT.value
        and editorial_format != EditorialFormat.RESULT_REPORT.value
    )
    government_intent_suspect = (
        legacy_content_type == ContentType.GOVERNMENT_SERVICE_CONTENT.value
        and reader_intent == ReaderIntent.VERIFY_REQUIREMENTS.value
        and editorial_format
        not in (EditorialFormat.GUIDE.value, EditorialFormat.SERVICE.value)
    )
    legal_intent_suspect = (
        legacy_content_type
        == ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT.value
        and reader_intent == ReaderIntent.UNDERSTAND_IMPACT.value
        and not _impact_treatment_supported(
            editorial_format=editorial_format,
            title=title,
            body=body,
        )
    )
    reader_intent_suspect = (
        sports_intent_suspect
        or government_intent_suspect
        or legal_intent_suspect
    )

    sports_strategy_suspect = (
        legacy_content_type == ContentType.SPORTS_NEWS.value
        and writing_mode == WritingMode.RESULT_REPORT.value
        and editorial_format != EditorialFormat.RESULT_REPORT.value
    )
    legal_strategy_suspect = (
        legacy_content_type
        == ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT.value
        and writing_mode == WritingMode.HIGH_RISK_CAUTION.value
        and risk_level not in ("HIGH", "CRITICAL")
    )
    breaking_strategy_suspect = (
        legacy_content_type == ContentType.BREAKING_NEWS.value
        and writing_mode == WritingMode.DIRECT_NEWS.value
        and editorial_format != EditorialFormat.BREAKING.value
    )
    return {
        "legacy_topic_conflict": legacy_topic_conflict,
        "legacy_format_conflict": legacy_format_conflict,
        "legacy_risk_mixing": legacy_risk_mixing,
        "reader_intent_suspect": reader_intent_suspect,
        "strategy_suspect": (
            sports_strategy_suspect
            or legal_strategy_suspect
            or breaking_strategy_suspect
        ),
    }


def analyze_migration(
    *,
    batch_root: Path = BATCH_ROOT,
    classification_workflow: EditorialClassificationWorkflow | None = None,
    topic_workflow: EditorialTopicWorkflow | None = None,
    format_workflow: EditorialFormatWorkflow | None = None,
    intent_workflow: EditorialIntentWorkflow | None = None,
    strategy_workflow: EditorialStrategyWorkflow | None = None,
) -> dict[str, Any]:
    """Run five deterministic analyses and diagnose legacy migration conflicts.

    Args:
        batch_root: Directory containing persisted Batch 01 sources.
        classification_workflow: Optional legacy classification workflow.
        topic_workflow: Optional additive topic workflow.
        format_workflow: Optional additive format workflow.
        intent_workflow: Optional reader-intent workflow.
        strategy_workflow: Optional editorial strategy workflow.

    Returns:
        Complete machine-readable migration report data.
    """
    classification = classification_workflow or EditorialClassificationWorkflow()
    topic = topic_workflow or EditorialTopicWorkflow()
    format_analysis = format_workflow or EditorialFormatWorkflow()
    intent = intent_workflow or EditorialIntentWorkflow()
    strategy = strategy_workflow or EditorialStrategyWorkflow()
    cases: list[dict[str, Any]] = []

    for manifest_case in read_manifest(batch_root):
        source = parse_source(batch_root / manifest_case["source_file"])
        raw_fields = _source_fields(source)
        classification_result = classification.process(**raw_fields)
        topic_result = topic.process(**raw_fields)
        format_result = format_analysis.process(**raw_fields)
        intent_result = intent.process(**raw_fields)
        strategy_result = strategy.process(**raw_fields)

        legacy = classification_result.classification
        topic_classification = topic_result.topic_classification
        format_classification = format_result.format_classification
        reader_intent = intent_result.reader_intent
        assessment = classification_result.ingestion.assessment
        base_strategy = strategy_result.strategy
        diagnoses = _diagnose(
            legacy_content_type=legacy.content_type.value,
            topic=topic_classification.topic.value,
            editorial_format=format_classification.editorial_format.value,
            reader_intent=reader_intent.reader_intent.value,
            risk_level=assessment.risk_level.value,
            writing_mode=base_strategy.writing_mode.value,
            title=source.title,
            body=source.body,
        )
        cases.append(
            {
                "id": source.case_id,
                "benchmark_category": source.benchmark_category,
                "legacy_content_type": legacy.content_type.value,
                "legacy_content_confidence": legacy.confidence.value,
                "topic": topic_classification.topic.value,
                "topic_confidence": topic_classification.confidence.value,
                "editorial_format": format_classification.editorial_format.value,
                "format_confidence": format_classification.confidence.value,
                "reader_intent": reader_intent.reader_intent.value,
                "reader_intent_confidence": reader_intent.confidence.value,
                "risk_level": assessment.risk_level.value,
                "base_strategy": {
                    "article_length": base_strategy.article_length.value,
                    "article_depth": base_strategy.article_depth.value,
                    "writing_mode": base_strategy.writing_mode.value,
                    "target_word_count": base_strategy.target_word_count,
                },
                **diagnoses,
            }
        )

    flag_names = (
        "legacy_topic_conflict",
        "legacy_format_conflict",
        "legacy_risk_mixing",
        "reader_intent_suspect",
        "strategy_suspect",
    )
    counts = {flag: sum(bool(case[flag]) for case in cases) for flag in flag_names}
    return {
        "batch": "batch_01",
        "case_count": len(cases),
        "cases": cases,
        "summary": {
            "legacy_topic_conflicts": counts["legacy_topic_conflict"],
            "legacy_format_conflicts": counts["legacy_format_conflict"],
            "legacy_risk_mixing_cases": counts["legacy_risk_mixing"],
            "reader_intent_suspect_cases": counts["reader_intent_suspect"],
            "strategy_suspect_cases": counts["strategy_suspect"],
        },
    }


def migration_candidates(analysis: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Group case IDs under migration actions derived from diagnosis flags."""
    groups = (
        ("Remove legacy topic dependency", "legacy_topic_conflict"),
        ("Remove legacy format dependency", "legacy_format_conflict"),
        ("Remove legacy risk dependency", "legacy_risk_mixing"),
        ("Review reader intent dependency", "reader_intent_suspect"),
        ("Review strategy dependency", "strategy_suspect"),
    )
    return {
        label: tuple(case["id"] for case in analysis["cases"] if case[flag])
        for label, flag in groups
        if any(case[flag] for case in analysis["cases"])
    }


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic UTF-8 migration JSON without source content."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render deterministic migration table, summary, and candidate groups."""
    lines = [
        "# Batch 01 Classification Migration",
        "",
        "| ID | Category | Legacy Content Type | Topic | Editorial Format | Reader Intent | Risk | Topic Conflict | Format Conflict | Risk Mixing | Intent Suspect | Strategy Suspect |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
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
                    case["reader_intent"],
                    case["risk_level"],
                    "YES" if case["legacy_topic_conflict"] else "NO",
                    "YES" if case["legacy_format_conflict"] else "NO",
                    "YES" if case["legacy_risk_mixing"] else "NO",
                    "YES" if case["reader_intent_suspect"] else "NO",
                    "YES" if case["strategy_suspect"] else "NO",
                )
            )
            + " |"
        )

    summary = analysis["summary"]
    lines.extend(
        (
            "",
            "## Summary",
            "",
            "Legacy Topic Conflicts:",
            str(summary["legacy_topic_conflicts"]),
            "",
            "Legacy Format Conflicts:",
            str(summary["legacy_format_conflicts"]),
            "",
            "Legacy Risk Mixing Cases:",
            str(summary["legacy_risk_mixing_cases"]),
            "",
            "Reader Intent Suspect Cases:",
            str(summary["reader_intent_suspect_cases"]),
            "",
            "Strategy Suspect Cases:",
            str(summary["strategy_suspect_cases"]),
            "",
            "## Migration Candidates",
        )
    )
    for label, case_ids in migration_candidates(analysis).items():
        lines.extend(
            ("", f"### {label}", "", *(f"- {case_id}" for case_id in case_ids))
        )
    lines.append("")
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render exact deterministic console totals and one line per case."""
    summary = analysis["summary"]
    lines = [
        "=== BATCH 01 CLASSIFICATION MIGRATION ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Legacy Topic Conflicts:",
        str(summary["legacy_topic_conflicts"]),
        "",
        "Legacy Format Conflicts:",
        str(summary["legacy_format_conflicts"]),
        "",
        "Legacy Risk Mixing Cases:",
        str(summary["legacy_risk_mixing_cases"]),
        "",
        "Reader Intent Suspect Cases:",
        str(summary["reader_intent_suspect_cases"]),
        "",
        "Strategy Suspect Cases:",
        str(summary["strategy_suspect_cases"]),
        "",
    ]
    for case in analysis["cases"]:
        lines.append(
            f"{case['id']} | legacy={case['legacy_content_type']} | "
            f"topic={case['topic']} | format={case['editorial_format']} | "
            f"intent={case['reader_intent']} | risk={case['risk_level']}"
        )
    return "\n".join(lines)


def main() -> int:
    """Analyze Batch 01, persist migration reports, and print diagnostics."""
    analysis = analyze_migration()
    (BATCH_ROOT / "classification_migration.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "classification_migration.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
