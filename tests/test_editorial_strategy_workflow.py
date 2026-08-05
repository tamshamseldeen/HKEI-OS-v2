"""Tests for the editorial strategy workflow."""

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
from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.deterministic_editorial_strategy_engine import (
    DeterministicEditorialStrategyEngine,
)
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode
from src.workflows.editorial_classification_result import (
    EditorialClassificationResult,
)
from src.workflows.editorial_ingestion_result import EditorialIngestionResult
from src.workflows.editorial_intent_result import EditorialIntentResult
from src.workflows.editorial_intent_workflow import EditorialIntentWorkflow
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


def make_intent_result(
    *, generation_allowed: bool = True
) -> EditorialIntentResult:
    """Create a complete editorial intent result for workflow tests.

    Args:
        generation_allowed: Whether the assessment permits generation.

    Returns:
        A representative editorial intent result.
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
        content_type=ContentType.STANDARD_NEWS,
        confidence=ClassificationConfidence.MEDIUM,
        reason_codes=("DEFAULT_STANDARD_NEWS",),
        supporting_signals=(),
        warnings=(),
    )
    classification_result = EditorialClassificationResult(
        ingestion, classification
    )
    reader_intent = ReaderIntentClassification(
        reader_intent=ReaderIntent.GET_UPDATE,
        confidence=ReaderIntentConfidence.MEDIUM,
        reason_codes=("DEFAULT_GET_UPDATE",),
        supporting_signals=("CONTENT_TYPE_FALLBACK",),
        warnings=(),
    )
    return EditorialIntentResult(classification_result, reader_intent)


def make_strategy() -> EditorialStrategy:
    """Create an editorial strategy for workflow tests.

    Returns:
        A representative editorial strategy.
    """
    return EditorialStrategy(
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


def make_mocked_workflow(
    intent_result: EditorialIntentResult | None = None,
) -> tuple[
    EditorialStrategyWorkflow,
    EditorialIntentWorkflow,
    DeterministicEditorialStrategyEngine,
    EditorialIntentResult,
    EditorialStrategy,
]:
    """Create a strategy workflow with configured mock dependencies.

    Args:
        intent_result: Upstream intent result, or None for a default result.

    Returns:
        The workflow, dependencies, and configured results.
    """
    upstream_result = intent_result or make_intent_result()
    strategy = make_strategy()
    intent_workflow = create_autospec(EditorialIntentWorkflow, instance=True)
    strategy_engine = create_autospec(
        DeterministicEditorialStrategyEngine, instance=True
    )
    intent_workflow.process.return_value = upstream_result
    strategy_engine.decide.return_value = strategy
    workflow = EditorialStrategyWorkflow(
        intent_workflow=intent_workflow,
        strategy_engine=strategy_engine,
    )
    return (
        workflow,
        intent_workflow,
        strategy_engine,
        upstream_result,
        strategy,
    )


def test_valid_raw_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using default workflow dependencies."""
    workflow = EditorialStrategyWorkflow()

    result = workflow.process(**SOURCE_FIELDS, user_instruction=None)

    assert isinstance(workflow.intent_workflow, EditorialIntentWorkflow)
    assert isinstance(
        workflow.strategy_engine, DeterministicEditorialStrategyEngine
    )
    assert isinstance(result, EditorialStrategyResult)
    assert isinstance(result.intent_result, EditorialIntentResult)
    assert isinstance(result.strategy, EditorialStrategy)


def test_injected_dependencies_are_used_once_in_order() -> None:
    """Store and call injected dependencies once in required order."""
    workflow, upstream, engine, intent_result, strategy = (
        make_mocked_workflow()
    )
    classification_result = intent_result.classification_result
    ingestion = classification_result.ingestion
    classification = classification_result.classification
    reader_intent = intent_result.reader_intent
    calls = Mock()
    calls.attach_mock(upstream, "intent_workflow")
    calls.attach_mock(engine, "strategy")
    instruction = "short"

    result = workflow.process(**SOURCE_FIELDS, user_instruction=instruction)

    assert workflow.intent_workflow is upstream
    assert workflow.strategy_engine is engine
    assert result.intent_result is intent_result
    assert result.strategy is strategy
    assert calls.mock_calls == [
        call.intent_workflow.process(
            **SOURCE_FIELDS, user_instruction=instruction
        ),
        call.strategy.decide(
            source=ingestion.source,
            assessment=ingestion.assessment,
            facts=ingestion.facts,
            content_classification=classification,
            reader_intent=reader_intent,
            user_instruction=instruction,
        ),
    ]


def test_source_validation_error_propagates_unchanged() -> None:
    """Propagate source validation errors without strategy selection."""
    workflow, upstream, engine, *_ = make_mocked_workflow()
    expected = SourceValidationError(("MISSING_TITLE",))
    upstream.process.side_effect = expected

    with pytest.raises(SourceValidationError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction=None
    )
    assert engine.mock_calls == []


def test_intent_workflow_failure_propagates_unchanged() -> None:
    """Propagate upstream failures without strategy selection."""
    workflow, upstream, engine, *_ = make_mocked_workflow()
    expected = RuntimeError("intent workflow failed")
    upstream.process.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction=None
    )
    assert engine.mock_calls == []


def test_strategy_engine_failure_propagates_unchanged() -> None:
    """Propagate strategy failures after one upstream call."""
    workflow, upstream, engine, result, _ = make_mocked_workflow()
    classification_result = result.classification_result
    ingestion = classification_result.ingestion
    expected = RuntimeError("strategy failed")
    engine.decide.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS, user_instruction="short")

    assert raised.value is expected
    upstream.process.assert_called_once_with(
        **SOURCE_FIELDS, user_instruction="short"
    )
    engine.decide.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification_result.classification,
        reader_intent=result.reader_intent,
        user_instruction="short",
    )


def test_strategy_runs_when_generation_is_not_allowed() -> None:
    """Select a strategy when the assessment blocks generation."""
    result = make_intent_result(generation_allowed=False)
    workflow, _, engine, _, strategy = make_mocked_workflow(result)
    classification_result = result.classification_result
    ingestion = classification_result.ingestion

    actual = workflow.process(**SOURCE_FIELDS)

    engine.decide.assert_called_once_with(
        source=ingestion.source,
        assessment=ingestion.assessment,
        facts=ingestion.facts,
        content_classification=classification_result.classification,
        reader_intent=result.reader_intent,
        user_instruction=None,
    )
    assert actual.strategy is strategy


def test_result_model_is_immutable() -> None:
    """Prevent editorial strategy result fields from reassignment."""
    intent_result = make_intent_result()
    result = EditorialStrategyResult(
        intent_result=intent_result,
        strategy=make_strategy(),
    )

    with pytest.raises(FrozenInstanceError):
        result.intent_result = intent_result  # type: ignore[misc]
