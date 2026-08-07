"""Tests for deterministic Batch 01 classification migration diagnostics."""

import json
import os
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_01_classification_migration import (
    _diagnose,
    analyze_migration,
    migration_candidates,
    render_console,
    render_json,
    render_markdown,
)
from examples.run_benchmark_batch_01_analysis import BATCH_ROOT, parse_source, read_manifest
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


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real deterministic migration analysis."""
    return analyze_migration()


def test_exactly_ten_cases_record_all_required_dimensions(
    analysis: dict[str, object],
) -> None:
    """Record legacy, topic, format, intent, risk, and strategy for ten cases."""
    cases = analysis["cases"]

    assert analysis["case_count"] == 10
    assert tuple(case["id"] for case in cases) == tuple(
        manifest_case["id"] for manifest_case in read_manifest()
    )
    for case in cases:
        assert case["legacy_content_type"]
        assert case["legacy_content_confidence"]
        assert case["topic"]
        assert case["topic_confidence"]
        assert case["editorial_format"]
        assert case["format_confidence"]
        assert case["reader_intent"]
        assert case["reader_intent_confidence"]
        assert case["risk_level"]
        assert set(case["base_strategy"]) == {
            "article_length",
            "article_depth",
            "writing_mode",
            "target_word_count",
        }


def test_topic_values_match_persisted_topic_benchmark(
    analysis: dict[str, object],
) -> None:
    """Use the same predictions recorded by the existing topic benchmark."""
    topic_analysis = json.loads(
        (BATCH_ROOT / "topic_analysis.json").read_text(encoding="utf-8")
    )

    assert tuple(case["topic"] for case in analysis["cases"]) == tuple(
        case["predicted_topic"] for case in topic_analysis["cases"]
    )


def test_all_five_workflows_run_once_per_case_with_same_fields() -> None:
    """Run every required deterministic workflow with identical source mapping."""
    workflows = (
        Mock(wraps=EditorialClassificationWorkflow()),
        Mock(wraps=EditorialTopicWorkflow()),
        Mock(wraps=EditorialFormatWorkflow()),
        Mock(wraps=EditorialIntentWorkflow()),
        Mock(wraps=EditorialStrategyWorkflow()),
    )

    analyze_migration(
        classification_workflow=workflows[0],
        topic_workflow=workflows[1],
        format_workflow=workflows[2],
        intent_workflow=workflows[3],
        strategy_workflow=workflows[4],
    )

    assert all(workflow.process.call_count == 10 for workflow in workflows)
    for calls in zip(*(workflow.process.call_args_list for workflow in workflows)):
        assert all(item.kwargs == calls[0].kwargs for item in calls[1:])


def test_topic_and_format_conflicts_are_deterministic() -> None:
    """Detect only mapped legacy topic and format contradictions."""
    diagnosis = _diagnose(
        legacy_content_type=ContentType.SPORTS_NEWS.value,
        topic="ECONOMY",
        editorial_format=EditorialFormat.STANDARD_NEWS.value,
        reader_intent=ReaderIntent.GET_UPDATE.value,
        risk_level="LOW",
        writing_mode=WritingMode.DIRECT_NEWS.value,
        title="عنوان اقتصادي",
        body="تفاصيل اقتصادية",
    )
    format_diagnosis = _diagnose(
        legacy_content_type=ContentType.BREAKING_NEWS.value,
        topic="WEATHER",
        editorial_format=EditorialFormat.STANDARD_NEWS.value,
        reader_intent=ReaderIntent.GET_UPDATE.value,
        risk_level="LOW",
        writing_mode=WritingMode.DIRECT_NEWS.value,
        title="عنوان",
        body="تفاصيل",
    )

    assert diagnosis["legacy_topic_conflict"] is True
    assert diagnosis["legacy_format_conflict"] is False
    assert format_diagnosis["legacy_format_conflict"] is True


def test_risk_mixing_and_suspect_dependencies_follow_exact_rules() -> None:
    """Flag specified risk, sports intent, and result-strategy dependencies."""
    sports = _diagnose(
        legacy_content_type=ContentType.SPORTS_NEWS.value,
        topic="ECONOMY",
        editorial_format=EditorialFormat.STANDARD_NEWS.value,
        reader_intent=ReaderIntent.FIND_RESULT.value,
        risk_level="LOW",
        writing_mode=WritingMode.RESULT_REPORT.value,
        title="أسواق",
        body="اقتصاد",
    )
    legal = _diagnose(
        legacy_content_type=ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT.value,
        topic="ECONOMY",
        editorial_format=EditorialFormat.STANDARD_NEWS.value,
        reader_intent=ReaderIntent.UNDERSTAND_IMPACT.value,
        risk_level="HIGH",
        writing_mode=WritingMode.HIGH_RISK_CAUTION.value,
        title="أسعار الذهب",
        body="تتابع الأسواق البيانات",
    )

    assert sports["reader_intent_suspect"] is True
    assert sports["strategy_suspect"] is True
    assert legal["legacy_risk_mixing"] is True
    assert legal["reader_intent_suspect"] is True
    assert legal["strategy_suspect"] is False


def test_summary_counts_equal_case_flags(analysis: dict[str, object]) -> None:
    """Calculate every summary value directly from its corresponding flag."""
    cases = analysis["cases"]
    summary = analysis["summary"]
    mappings = {
        "legacy_topic_conflicts": "legacy_topic_conflict",
        "legacy_format_conflicts": "legacy_format_conflict",
        "legacy_risk_mixing_cases": "legacy_risk_mixing",
        "reader_intent_suspect_cases": "reader_intent_suspect",
        "strategy_suspect_cases": "strategy_suspect",
    }

    for summary_name, flag_name in mappings.items():
        assert summary[summary_name] == sum(bool(case[flag_name]) for case in cases)


def test_migration_candidate_groups_exactly_match_flags(
    analysis: dict[str, object],
) -> None:
    """Group only flagged case IDs beneath their corresponding migration action."""
    candidates = migration_candidates(analysis)

    assert candidates == {
        "Remove legacy topic dependency": ("002", "005", "006"),
        "Remove legacy risk dependency": ("001", "003", "010"),
        "Review reader intent dependency": (
            "002",
            "003",
            "005",
            "006",
            "010",
        ),
        "Review strategy dependency": ("002", "005", "006"),
    }
    assert "Remove legacy format dependency" not in candidates


def test_json_excludes_source_bodies_and_prompts(
    analysis: dict[str, object],
) -> None:
    """Keep machine-readable migration output free of source and prompt content."""
    output = render_json(analysis)

    assert "prompt" not in output.lower()
    assert '"body"' not in output
    for manifest_case in read_manifest():
        source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        assert source.body not in output


def test_persisted_outputs_are_deterministic(
    analysis: dict[str, object],
) -> None:
    """Keep JSON, Markdown, and console output stable for identical input."""
    expected_json = render_json(analysis)
    expected_markdown = render_markdown(analysis)

    assert (BATCH_ROOT / "classification_migration.json").read_text(
        encoding="utf-8"
    ) == expected_json
    assert (BATCH_ROOT / "classification_migration.md").read_text(
        encoding="utf-8"
    ) == expected_markdown
    assert render_json(analysis) == expected_json
    assert render_markdown(analysis) == expected_markdown
    assert render_console(analysis) == render_console(analysis)


def test_analysis_requires_no_network_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run all deterministic workflows with external access disabled."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_migration()["case_count"] == 10
