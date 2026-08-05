"""Tests for the editorial planning workflow."""

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call, create_autospec

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.classification.classification_confidence import (
    ClassificationConfidence,
)
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.intake.normalized_source import NormalizedSource
from src.intake.source_intake import SourceValidationError
from src.planning.article_plan import ArticlePlan
from src.planning.deterministic_article_planner import DeterministicArticlePlanner
from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_ingestion_result import EditorialIngestionResult
from src.workflows.editorial_intent_result import EditorialIntentResult
from src.workflows.editorial_planning_result import EditorialPlanningResult
from src.workflows.editorial_planning_workflow import EditorialPlanningWorkflow
from src.workflows.editorial_strategy_result import EditorialStrategyResult
from src.workflows.editorial_strategy_workflow import EditorialStrategyWorkflow


SOURCE_FIELDS = {
    "title": "Headline",
    "body": "Article body",
    "source_name": "News Agency",
    "source_url": "https://example.com/article",
    "published_at": "2026-08-05T10:00:00Z",
    "language": "en",
    "country": "Saudi Arabia",
    "author": "Reporter",
    "images": ("image.jpg",),
    "attachments": ("document.pdf",),
    "category": "news",
    "tags": ("example",),
}


def make_strategy_result(
    *, generation_allowed: bool = True
) -> EditorialStrategyResult:
    """Create a complete editorial strategy result for workflow tests.

    Args:
        generation_allowed: Whether the assessment permits generation.

    Returns:
        A representative editorial strategy result.
    """
    source = NormalizedSource("Headline", "Article body", "News Agency")
    assessment = SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=RiskLevel.LOW,
        risk_topics=(),
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=generation_allowed,
        reason_codes=("SOURCE_OK",),
    )
    facts = ExtractedFacts(
        core_facts=(source.title, source.body),
        claims=(),
        quotes=(),
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=(),
        times=(),
        numbers=(),
        percentages=(),
        currencies=(),
        laws_and_regulations=(),
        products=(),
        events=(source.title,),
        unknown_information=(),
        attributions=(source.source_name,),
    )
    ingestion = EditorialIngestionResult(source, assessment, facts)
    classification = ContentTypeClassification(
        ContentType.STANDARD_NEWS,
        ClassificationConfidence.MEDIUM,
        ("DEFAULT_STANDARD_NEWS",),
        (),
        (),
    )
    classification_result = EditorialClassificationResult(
        ingestion, classification
    )
    reader_intent = ReaderIntentClassification(
        ReaderIntent.GET_UPDATE,
        ReaderIntentConfidence.MEDIUM,
        ("DEFAULT_GET_UPDATE",),
        ("CONTENT_TYPE_FALLBACK",),
        (),
    )
    intent_result = EditorialIntentResult(
        classification_result, reader_intent
    )
    strategy = EditorialStrategy(
        article_length=ArticleLength.VERY_SHORT,
        article_depth=ArticleDepth.UPDATE,
        writing_mode=WritingMode.DIRECT_NEWS,
        use_headings=False,
        use_bullets=False,
        use_table=False,
        use_faq=False,
        use_timeline=False,
        use_background=False,
        use_quotes=False,
        use_attribution=True,
        include_missing_information=False,
        include_reader_action=False,
        target_word_count=120,
        reason_codes=("LIMITED_SOURCE_DEPTH",),
        warnings=(),
    )
    return EditorialStrategyResult(intent_result, strategy)


def make_article_plan() -> ArticlePlan:
    """Create an article plan for workflow tests.

    Returns:
        A representative deterministic article plan.
    """
    return ArticlePlan(
        working_title="Headline",
        lead_instruction="Begin with the newest confirmed fact.",
        sections=(),
        closing_instruction=(
            "End with the final confirmed detail without repetition."
        ),
        required_facts=("Headline", "Article body"),
        required_attributions=("News Agency",),
        required_warnings=(),
        prohibited_claims=("UNSUPPORTED_FACT",),
        missing_information=(),
        target_word_count=120,
        reason_codes=("LIMITED_SOURCE_PLAN",),
        warnings=(),
    )


def make_mocked_workflow(
    strategy_result: EditorialStrategyResult | None = None,
) -> tuple[
    EditorialPlanningWorkflow,
    EditorialStrategyWorkflow,
    DeterministicArticlePlanner,
    EditorialStrategyResult,
    ArticlePlan,
]:
    """Create a planning workflow with configured mock dependencies.

    Args:
        strategy_result: Upstream strategy result, or None for a default.

    Returns:
        The workflow, dependencies, and configured results.
    """
    upstream_result = strategy_result or make_strategy_result()
    article_plan = make_article_plan()
    strategy_workflow = create_autospec(
        EditorialStrategyWorkflow, instance=True
    )
    article_planner = create_autospec(
        DeterministicArticlePlanner, instance=True
    )
    strategy_workflow.process.return_value = upstream_result
    article_planner.plan.return_value = article_plan
    workflow = EditorialPlanningWorkflow(
        strategy_workflow=strategy_workflow,
        article_planner=article_planner,
    )
    return (
        workflow,
        strategy_workflow,
        article_planner,
        upstream_result,
        article_plan,
    )


def test_valid_raw_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using default workflow dependencies."""
    workflow = EditorialPlanningWorkflow()

    result = workflow.process(**SOURCE_FIELDS, user_instruction=None)

    assert isinstance(workflow.strategy_workflow, EditorialStrategyWorkflow)
    assert isinstance(workflow.article_planner, DeterministicArticlePlanner)
    assert isinstance(result, EditorialPlanningResult)
    assert isinstance(result.strategy_result, EditorialStrategyResult)
    assert isinstance(result.article_plan, ArticlePlan)


def test_injected_dependencies_are_used_once_in_order() -> None:
    """Store and call injected dependencies once in required order."""
    workflow, upstream, planner, strategy_result, article_plan = (
        make_mocked_workflow()
    )
    intent_result = strategy_result.intent_result
    classification_result = intent_result.classification_result
    ingestion = classification_result.ingestion
    instruction = "use headings"
    calls = Mock()
    calls.attach_mock(upstream, "strategy_workflow")
    calls.attach_mock(planner, "article_planner")

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)

    assert workflow.strategy_workflow is upstream
    assert workflow.article_planner is planner
    assert result.strategy_result is strategy_result
    assert result.article_plan is article_plan
    assert calls.mock_calls == [
        call.strategy_workflow.process(
            **SOURCE_FIELDS, user_instruction=instruction
        ),
        call.article_planner.plan(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification_result.classification,
            reader_intent=intent_result.reader_intent,
            strategy=strategy_result.strategy,
            user_instruction=instruction,
        ),
    ]


def test_source_validation_error_propagates_unchanged() -> None:
    """Propagate source validation errors without article planning."""
    workflow, upstream, planner, *_ = make_mocked_workflow()
    expected = SourceValidationError(("MISSING_TITLE",))
    upstream.process.side_effect = expected

    with pytest.raises(SourceValidationError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction=None
    )
    assert planner.mock_calls == []


def test_strategy_workflow_failure_propagates_unchanged() -> None:
    """Propagate upstream failures without article planning."""
    workflow, upstream, planner, *_ = make_mocked_workflow()
    expected = RuntimeError("strategy workflow failed")
    upstream.process.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction=None
    )
    assert planner.mock_calls == []


def test_article_planner_failure_propagates_unchanged() -> None:
    """Propagate planner failures after one upstream call."""
    workflow, upstream, planner, result, _ = make_mocked_workflow()
    intent_result = result.intent_result
    classification_result = intent_result.classification_result
    ingestion = classification_result.ingestion
    expected = RuntimeError("article planning failed")
    planner.plan.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS, user_instruction="use headings")

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction="use headings"
    )
    planner.plan.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification_result.classification,
        reader_intent=intent_result.reader_intent,
        strategy=result.strategy,
        user_instruction="use headings",
    )


def test_planning_runs_when_generation_is_not_allowed() -> None:
    """Plan an article when the assessment blocks generation."""
    result = make_strategy_result(generation_allowed=False)
    workflow, _, planner, _, article_plan = make_mocked_workflow(result)
    intent_result = result.intent_result
    classification_result = intent_result.classification_result
    ingestion = classification_result.ingestion

    actual = workflow.process(**SOURCE_FIELDS)

    planner.plan.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification_result.classification,
        reader_intent=intent_result.reader_intent,
        strategy=result.strategy,
        user_instruction=None,
    )
    assert actual.article_plan is article_plan


def test_result_model_is_immutable() -> None:
    """Prevent editorial planning result fields from reassignment."""
    strategy_result = make_strategy_result()
    result = EditorialPlanningResult(
        strategy_result=strategy_result,
        article_plan=make_article_plan(),
    )

    with pytest.raises(FrozenInstanceError):
        result.strategy_result = strategy_result  # type: ignore[misc]
