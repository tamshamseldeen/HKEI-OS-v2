"""Tests for the editorial ingestion workflow."""

from unittest.mock import Mock, call, create_autospec

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_risk_assessment_engine import (
    SourceRiskAssessmentEngine,
)
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.facts.extracted_facts import ExtractedFacts
from src.facts.fact_extraction_service import FactExtractionService
from src.intake.normalized_source import NormalizedSource
from src.intake.source_intake import SourceIntake, SourceValidationError
from src.workflows.editorial_ingestion_result import EditorialIngestionResult
from src.workflows.editorial_ingestion_workflow import EditorialIngestionWorkflow


RAW_FIELDS = {
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


def make_assessment(*, generation_allowed: bool = True) -> SourceRiskAssessment:
    """Create a risk assessment for workflow tests.

    Args:
        generation_allowed: Whether the result permits generation.

    Returns:
        A representative source risk assessment.
    """
    return SourceRiskAssessment(
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


def make_facts() -> ExtractedFacts:
    """Create extracted facts for workflow tests.

    Returns:
        A representative extracted facts result.
    """
    return ExtractedFacts(
        core_facts=("Headline", "Article body"),
        claims=(),
        quotes=(),
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=("Saudi Arabia",),
        dates=(),
        times=(),
        numbers=(),
        percentages=(),
        currencies=(),
        laws_and_regulations=(),
        products=(),
        events=("Headline",),
        unknown_information=(),
        attributions=("News Agency",),
    )


def make_mocked_workflow(
    assessment: SourceRiskAssessment | None = None,
) -> tuple[
    EditorialIngestionWorkflow,
    SourceIntake,
    SourceRiskAssessmentEngine,
    FactExtractionService,
    NormalizedSource,
    SourceRiskAssessment,
    ExtractedFacts,
]:
    """Create a workflow with configured mock dependencies.

    Args:
        assessment: Assessment result to use, or None for a default result.

    Returns:
        The workflow, mocks, and their configured return values.
    """
    source = NormalizedSource("Headline", "Article body", "News Agency")
    assessment_result = assessment or make_assessment()
    facts = make_facts()
    source_intake = create_autospec(SourceIntake, instance=True)
    assessment_engine = create_autospec(
        SourceRiskAssessmentEngine, instance=True
    )
    fact_service = create_autospec(FactExtractionService, instance=True)
    source_intake.process.return_value = source
    assessment_engine.assess.return_value = assessment_result
    fact_service.process.return_value = facts
    workflow = EditorialIngestionWorkflow(
        source_intake=source_intake,
        assessment_engine=assessment_engine,
        fact_extraction_service=fact_service,
    )
    return (
        workflow,
        source_intake,
        assessment_engine,
        fact_service,
        source,
        assessment_result,
        facts,
    )


def test_valid_raw_input_returns_result_with_default_dependencies() -> None:
    """Process valid raw input using all default workflow dependencies."""
    workflow = EditorialIngestionWorkflow()

    result = workflow.process(**RAW_FIELDS)

    assert isinstance(workflow.source_intake, SourceIntake)
    assert isinstance(workflow.assessment_engine, SourceRiskAssessmentEngine)
    assert isinstance(workflow.fact_extraction_service, FactExtractionService)
    assert isinstance(result, EditorialIngestionResult)
    assert isinstance(result.source, NormalizedSource)
    assert isinstance(result.assessment, SourceRiskAssessment)
    assert isinstance(result.facts, ExtractedFacts)


def test_injected_dependencies_are_stored_and_called_in_order() -> None:
    """Use injected dependencies once in intake, assessment, facts order."""
    (
        workflow,
        source_intake,
        assessment_engine,
        fact_service,
        source,
        assessment,
        facts,
    ) = make_mocked_workflow()
    calls = Mock()
    calls.attach_mock(source_intake, "intake")
    calls.attach_mock(assessment_engine, "assessment")
    calls.attach_mock(fact_service, "facts")

    result = workflow.process(**RAW_FIELDS)

    assert workflow.source_intake is source_intake
    assert workflow.assessment_engine is assessment_engine
    assert workflow.fact_extraction_service is fact_service
    assert result.source is source
    assert result.assessment is assessment
    assert result.facts is facts
    assert calls.mock_calls == [
        call.intake.process(**RAW_FIELDS),
        call.assessment.assess(source),
        call.facts.process(source),
    ]


def test_source_validation_error_propagates_unchanged() -> None:
    """Propagate the intake validation error without downstream calls."""
    workflow, source_intake, assessment_engine, fact_service, *_ = (
        make_mocked_workflow()
    )
    expected = SourceValidationError(("MISSING_TITLE",))
    source_intake.process.side_effect = expected

    with pytest.raises(SourceValidationError) as raised:
        workflow.process(**RAW_FIELDS)

    assert raised.value is expected
    source_intake.process.assert_called_once_with(**RAW_FIELDS)
    assert assessment_engine.mock_calls == []
    assert fact_service.mock_calls == []


def test_assessment_failure_propagates_unchanged() -> None:
    """Propagate assessment failure without attempting fact extraction."""
    workflow, source_intake, assessment_engine, fact_service, source, *_ = (
        make_mocked_workflow()
    )
    expected = RuntimeError("assessment failed")
    assessment_engine.assess.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**RAW_FIELDS)

    assert raised.value is expected
    source_intake.process.assert_called_once_with(**RAW_FIELDS)
    assessment_engine.assess.assert_called_once_with(source)
    assert fact_service.mock_calls == []


def test_fact_extraction_failure_propagates_unchanged() -> None:
    """Propagate fact extraction failure after prior workflow stages."""
    (
        workflow,
        source_intake,
        assessment_engine,
        fact_service,
        source,
        assessment,
        _,
    ) = make_mocked_workflow()
    expected = RuntimeError("fact extraction failed")
    fact_service.process.side_effect = expected

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**RAW_FIELDS)

    assert raised.value is expected
    source_intake.process.assert_called_once_with(**RAW_FIELDS)
    assessment_engine.assess.assert_called_once_with(source)
    assert assessment_engine.assess.return_value is assessment
    fact_service.process.assert_called_once_with(source)


def test_facts_are_extracted_when_generation_is_not_allowed() -> None:
    """Continue fact extraction for an assessment blocking generation."""
    assessment = make_assessment(generation_allowed=False)
    workflow, _, _, fact_service, source, _, facts = make_mocked_workflow(
        assessment
    )

    result = workflow.process(**RAW_FIELDS)

    fact_service.process.assert_called_once_with(source)
    assert result.assessment is assessment
    assert result.facts is facts
