"""Tests for the experimental format-aware editorial strategy workflow."""

from dataclasses import FrozenInstanceError, replace
from unittest.mock import Mock, call, create_autospec

import pytest

from src.assessment.risk_level import RiskLevel
from src.classification.content_type import ContentType
from src.intake.source_intake import SourceValidationError
from src.strategy.editorial_format_strategy_adapter import (
    EditorialFormatStrategyAdapter,
)
from src.strategy.editorial_strategy import EditorialStrategy
from src.workflows.editorial_format_result import EditorialFormatResult
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_strategy_result import EditorialStrategyResult
from src.workflows.editorial_strategy_workflow import EditorialStrategyWorkflow
from src.workflows.experimental_editorial_strategy_result import (
    ExperimentalEditorialStrategyResult,
)
from src.workflows.experimental_editorial_strategy_workflow import (
    ExperimentalEditorialStrategyWorkflow,
)


SOURCE_FIELDS = {
    "title": "موعد خدمة حكومية جديدة",
    "body": "أعلنت الجهة الرسمية موعد الخدمة وخطوات الاستفادة منها.",
    "source_name": "Official Source",
    "source_url": "https://example.com/service",
    "published_at": "2026-08-05T10:00:00Z",
    "language": "ar",
    "country": "Saudi Arabia",
    "author": "Reporter",
    "images": ("image.jpg",),
    "attachments": ("document.pdf",),
    "category": "public service",
    "tags": ("خدمة", "موعد"),
    "user_instruction": "اكتب خبرًا خدميًا",
}


def make_real_results() -> tuple[
    EditorialStrategyResult,
    EditorialFormatResult,
    EditorialStrategy,
]:
    """Create compatible results and their real deterministic adaptation."""
    strategy_result = EditorialStrategyWorkflow().process(**SOURCE_FIELDS)
    format_result = EditorialFormatWorkflow().process(**SOURCE_FIELDS)
    ingestion = strategy_result.intent_result.classification_result.ingestion
    adapted_strategy = EditorialFormatStrategyAdapter().adapt(
        strategy=strategy_result.strategy,
        format_classification=format_result.format_classification,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
    )
    return strategy_result, format_result, adapted_strategy


def make_mocked_workflow(
    *,
    strategy_result: EditorialStrategyResult | None = None,
    format_result: EditorialFormatResult | None = None,
) -> tuple[
    ExperimentalEditorialStrategyWorkflow,
    EditorialStrategyWorkflow,
    EditorialFormatWorkflow,
    EditorialFormatStrategyAdapter,
    EditorialStrategyResult,
    EditorialFormatResult,
    EditorialStrategy,
]:
    """Create configured injected dependencies and compatible real values."""
    real_strategy, real_format, adapted_strategy = make_real_results()
    selected_strategy = strategy_result or real_strategy
    selected_format = format_result or real_format
    strategy_workflow = create_autospec(EditorialStrategyWorkflow, instance=True)
    format_workflow = create_autospec(EditorialFormatWorkflow, instance=True)
    strategy_adapter = create_autospec(
        EditorialFormatStrategyAdapter,
        instance=True,
    )
    strategy_workflow.process.return_value = selected_strategy
    format_workflow.process.return_value = selected_format
    strategy_adapter.adapt.return_value = adapted_strategy
    workflow = ExperimentalEditorialStrategyWorkflow(
        strategy_workflow=strategy_workflow,
        format_workflow=format_workflow,
        strategy_adapter=strategy_adapter,
    )
    return (
        workflow,
        strategy_workflow,
        format_workflow,
        strategy_adapter,
        selected_strategy,
        selected_format,
        adapted_strategy,
    )


def test_valid_input_returns_result_with_default_dependencies() -> None:
    """Run valid input through all default deterministic dependencies."""
    workflow = ExperimentalEditorialStrategyWorkflow()

    result = workflow.process(**SOURCE_FIELDS)

    assert isinstance(workflow.strategy_workflow, EditorialStrategyWorkflow)
    assert isinstance(workflow.format_workflow, EditorialFormatWorkflow)
    assert isinstance(workflow.strategy_adapter, EditorialFormatStrategyAdapter)
    assert isinstance(result, ExperimentalEditorialStrategyResult)
    assert isinstance(result.strategy_result, EditorialStrategyResult)
    assert isinstance(result.format_result, EditorialFormatResult)
    assert isinstance(result.adapted_strategy, EditorialStrategy)
    assert result.adapted_strategy is not result.strategy_result.strategy


def test_injected_dependencies_receive_exact_values_once_in_order() -> None:
    """Store dependencies and make exactly three ordered calls with exact values."""
    (
        workflow,
        strategy_workflow,
        format_workflow,
        adapter,
        strategy_result,
        format_result,
        adapted_strategy,
    ) = make_mocked_workflow()
    calls = Mock()
    calls.attach_mock(strategy_workflow, "strategy")
    calls.attach_mock(format_workflow, "format")
    calls.attach_mock(adapter, "adapter")
    ingestion = strategy_result.intent_result.classification_result.ingestion
    base_snapshot = replace(strategy_result.strategy)

    result = workflow.process(**SOURCE_FIELDS)

    assert workflow.strategy_workflow is strategy_workflow
    assert workflow.format_workflow is format_workflow
    assert workflow.strategy_adapter is adapter
    assert result.strategy_result is strategy_result
    assert result.format_result is format_result
    assert result.adapted_strategy is adapted_strategy
    assert result.strategy_result.strategy is strategy_result.strategy
    assert result.strategy_result.strategy == base_snapshot
    assert calls.mock_calls == [
        call.strategy.process(**SOURCE_FIELDS),
        call.format.process(**SOURCE_FIELDS),
        call.adapter.adapt(
            strategy=strategy_result.strategy,
            format_classification=format_result.format_classification,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
        ),
    ]


@pytest.mark.parametrize(
    "failure",
    (
        SourceValidationError(("MISSING_TITLE",)),
        RuntimeError("strategy workflow failed"),
    ),
)
def test_strategy_workflow_failures_propagate_unchanged(
    failure: Exception,
) -> None:
    """Propagate strategy failures without invoking later dependencies."""
    workflow, strategy_workflow, format_workflow, adapter, *_ = (
        make_mocked_workflow()
    )
    strategy_workflow.process.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    strategy_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    assert format_workflow.mock_calls == []
    assert adapter.mock_calls == []


def test_format_workflow_failure_propagates_unchanged() -> None:
    """Propagate format failure after one strategy call and before adaptation."""
    workflow, strategy_workflow, format_workflow, adapter, *_ = (
        make_mocked_workflow()
    )
    failure = RuntimeError("format workflow failed")
    format_workflow.process.side_effect = failure

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    strategy_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    format_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    assert adapter.mock_calls == []


def test_adapter_failure_propagates_unchanged() -> None:
    """Propagate adapter failure after both compatible workflow calls."""
    (
        workflow,
        strategy_workflow,
        format_workflow,
        adapter,
        strategy_result,
        format_result,
        _,
    ) = make_mocked_workflow()
    failure = RuntimeError("adapter failed")
    adapter.adapt.side_effect = failure
    ingestion = strategy_result.intent_result.classification_result.ingestion

    with pytest.raises(RuntimeError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    strategy_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    format_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    adapter.adapt.assert_called_once_with(
        strategy=strategy_result.strategy,
        format_classification=format_result.format_classification,
        facts=ingestion.facts,
        assessment=ingestion.assessment,
    )


def mismatched_format_result(kind: str) -> EditorialFormatResult:
    """Create one format result differing in exactly one compatibility value."""
    _, format_result, _ = make_real_results()
    classification_result = format_result.classification_result
    ingestion = classification_result.ingestion
    if kind == "source":
        ingestion = replace(
            ingestion,
            source=replace(ingestion.source, title="Different title"),
        )
    elif kind == "assessment":
        ingestion = replace(
            ingestion,
            assessment=replace(ingestion.assessment, risk_level=RiskLevel.CRITICAL),
        )
    elif kind == "facts":
        ingestion = replace(
            ingestion,
            facts=replace(ingestion.facts, core_facts=("different",)),
        )
    elif kind == "classification":
        classification_result = replace(
            classification_result,
            classification=replace(
                classification_result.classification,
                content_type=ContentType.BREAKING_NEWS,
            ),
        )
        return replace(format_result, classification_result=classification_result)
    classification_result = replace(classification_result, ingestion=ingestion)
    return replace(format_result, classification_result=classification_result)


@pytest.mark.parametrize(
    "kind",
    ("source", "assessment", "facts", "classification"),
)
def test_compatibility_mismatch_raises_exact_error(kind: str) -> None:
    """Reject every specified parallel-result incompatibility before adaptation."""
    strategy_result, _, _ = make_real_results()
    format_result = mismatched_format_result(kind)
    workflow, strategy_workflow, format_workflow, adapter, *_ = (
        make_mocked_workflow(
            strategy_result=strategy_result,
            format_result=format_result,
        )
    )

    with pytest.raises(ValueError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert str(raised.value) == "EXPERIMENTAL_WORKFLOW_RESULT_MISMATCH"
    strategy_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    format_workflow.process.assert_called_once_with(**SOURCE_FIELDS)
    assert adapter.mock_calls == []


def test_result_is_immutable() -> None:
    """Prevent reassignment of experimental result fields."""
    workflow, *_, strategy_result, format_result, adapted = make_mocked_workflow()
    result = ExperimentalEditorialStrategyResult(
        strategy_result,
        format_result,
        adapted,
    )

    with pytest.raises(FrozenInstanceError):
        result.adapted_strategy = strategy_result.strategy  # type: ignore[misc]


def test_raw_input_objects_remain_unchanged() -> None:
    """Forward raw immutable objects without changing their values."""
    workflow, *_ = make_mocked_workflow()
    fields = dict(SOURCE_FIELDS)
    images = fields["images"]
    attachments = fields["attachments"]
    tags = fields["tags"]

    workflow.process(**fields)

    assert fields == SOURCE_FIELDS
    assert fields["images"] is images
    assert fields["attachments"] is attachments
    assert fields["tags"] is tags
