"""Tests for the editorial prompt workflow."""

from dataclasses import FrozenInstanceError
from typing import cast
from unittest.mock import Mock, call, create_autospec

import pytest

from src.intake.source_intake import SourceValidationError
from src.prompting.deterministic_prompt_builder import (
    DeterministicPromptBuilder,
    PromptConfigurationError,
)
from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat
from src.workflows.editorial_planning_result import EditorialPlanningResult
from src.workflows.editorial_planning_workflow import EditorialPlanningWorkflow
from src.workflows.editorial_prompt_result import EditorialPromptResult
from src.workflows.editorial_prompt_workflow import EditorialPromptWorkflow


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


def make_generation_prompt() -> GenerationPrompt:
    """Create a representative generation prompt."""
    return GenerationPrompt(
        system_prompt="system",
        user_prompt="user",
        target_language="ar",
        target_word_count=120,
        required_output_format=OutputFormat.MARKDOWN_ARTICLE,
        prohibited_content=(),
        required_warnings=(),
        reason_codes=("PROMPT_PLAN_INCLUDED",),
    )


def make_mocked_workflow() -> tuple[
    EditorialPromptWorkflow,
    EditorialPlanningWorkflow,
    DeterministicPromptBuilder,
    EditorialPlanningResult,
    GenerationPrompt,
]:
    """Create a prompt workflow with configured mock dependencies."""
    planning_result = cast(EditorialPlanningResult, Mock())
    generation_prompt = make_generation_prompt()
    planning_workflow = create_autospec(
        EditorialPlanningWorkflow, instance=True
    )
    prompt_builder = create_autospec(
        DeterministicPromptBuilder, instance=True
    )
    planning_workflow.process.return_value = planning_result
    prompt_builder.build.return_value = generation_prompt
    workflow = EditorialPromptWorkflow(
        editorial_policy="ignored policy",
        planning_workflow=planning_workflow,
        prompt_builder=prompt_builder,
    )
    return (
        workflow,
        planning_workflow,
        prompt_builder,
        planning_result,
        generation_prompt,
    )


def test_injected_dependencies_are_used_once_in_order() -> None:
    """Return exact dependency results after exactly one ordered call each."""
    workflow, planning, builder, planning_result, prompt = (
        make_mocked_workflow()
    )
    calls = Mock()
    calls.attach_mock(planning, "planning")
    calls.attach_mock(builder, "builder")

    result = workflow.process(
        **SOURCE_FIELDS,
        user_instruction="preserve emphasis",
    )

    assert isinstance(result, EditorialPromptResult)
    assert result.planning_result is planning_result
    assert result.generation_prompt is prompt
    assert workflow.planning_workflow is planning
    assert workflow.prompt_builder is builder
    assert calls.mock_calls == [
        call.planning.process(
            **SOURCE_FIELDS,
            user_instruction="preserve emphasis",
        ),
        call.builder.build(
            planning_result=planning_result,
            user_instruction="preserve emphasis",
        ),
    ]


def test_default_dependencies_and_policy_are_created() -> None:
    """Create default planning and prompt-building dependencies."""
    workflow = EditorialPromptWorkflow(editorial_policy="policy text")

    assert isinstance(workflow.planning_workflow, EditorialPlanningWorkflow)
    assert isinstance(workflow.prompt_builder, DeterministicPromptBuilder)
    assert workflow.prompt_builder.editorial_policy == "policy text"


def test_injected_prompt_builder_ignores_editorial_policy() -> None:
    """Store an injected prompt builder without applying the policy argument."""
    builder = create_autospec(DeterministicPromptBuilder, instance=True)

    workflow = EditorialPromptWorkflow(
        editorial_policy="must be ignored",
        prompt_builder=builder,
    )

    assert workflow.prompt_builder is builder
    assert builder.mock_calls == []


@pytest.mark.parametrize(
    "failure",
    (
        SourceValidationError(("MISSING_TITLE",)),
        RuntimeError("planning failed"),
    ),
)
def test_planning_failures_propagate_unchanged(failure: Exception) -> None:
    """Propagate validation and planning failures without prompt building."""
    workflow, planning, builder, *_ = make_mocked_workflow()
    planning.process.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    planning.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    assert builder.mock_calls == []


@pytest.mark.parametrize(
    "failure",
    (
        PromptConfigurationError("EDITORIAL_POLICY_MISSING"),
        RuntimeError("prompt building failed"),
    ),
)
def test_prompt_builder_failures_propagate_unchanged(
    failure: Exception,
) -> None:
    """Propagate configuration and builder failures after planning once."""
    workflow, planning, builder, planning_result, _ = make_mocked_workflow()
    builder.build.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    planning.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    builder.build.assert_called_once_with(
        planning_result=planning_result,
        user_instruction=None,
    )


def test_prompt_building_runs_when_generation_is_not_allowed() -> None:
    """Build a prompt even when the nested assessment blocks generation."""
    workflow, _, builder, planning_result, prompt = make_mocked_workflow()
    ingestion = (
        planning_result.strategy_result
        .intent_result.classification_result.ingestion
    )
    ingestion.assessment.generation_allowed = False

    result = workflow.process(**SOURCE_FIELDS)

    builder.build.assert_called_once_with(
        planning_result=planning_result,
        user_instruction=None,
    )
    assert result.generation_prompt is prompt


def test_result_model_is_immutable() -> None:
    """Prevent editorial prompt result fields from reassignment."""
    _, _, _, planning_result, prompt = make_mocked_workflow()
    result = EditorialPromptResult(planning_result, prompt)

    with pytest.raises(FrozenInstanceError):
        result.generation_prompt = prompt  # type: ignore[misc]
