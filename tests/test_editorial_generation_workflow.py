"""Tests for the editorial generation workflow."""

from dataclasses import FrozenInstanceError, replace
from typing import cast
from unittest.mock import MagicMock, Mock, call, create_autospec

import pytest

from src.generation.finish_reason import FinishReason
from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_error import GenerationError
from src.generation.generation_result import GenerationResult
from src.generation.generation_service import GenerationService
from src.intake.source_intake import SourceValidationError
from src.prompting.deterministic_prompt_builder import PromptConfigurationError
from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat
from src.workflows.editorial_generation_result import EditorialGenerationResult
from src.workflows.editorial_generation_workflow import (
    EditorialGenerationWorkflow,
)
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


def make_prompt() -> GenerationPrompt:
    """Create a representative deterministic prompt."""
    return GenerationPrompt(
        "system",
        "user",
        "ar",
        120,
        OutputFormat.MARKDOWN_ARTICLE,
        (),
        (),
        (),
    )


def make_configuration() -> GenerationConfiguration:
    """Create representative provider generation configuration."""
    return GenerationConfiguration("model-id", 800, None, 30.0, ())


def make_generation_result() -> GenerationResult:
    """Create a representative normalized generation result."""
    return GenerationResult(
        "raw output",
        "provider-id",
        "model-id",
        100,
        50,
        150,
        FinishReason.COMPLETED,
        "request-id",
        (),
    )


def make_prompt_result(
    *,
    generation_allowed: bool = True,
) -> EditorialPromptResult:
    """Create a prompt result with a configurable nested assessment."""
    result = MagicMock()
    result.generation_prompt = make_prompt()
    assessment = (
        result.planning_result.strategy_result.intent_result
        .classification_result.ingestion.assessment
    )
    assessment.generation_allowed = generation_allowed
    return cast(EditorialPromptResult, result)


def make_mocked_workflow(
    *,
    generation_allowed: bool = True,
) -> tuple[
    EditorialGenerationWorkflow,
    EditorialPromptWorkflow,
    GenerationService,
    GenerationConfiguration,
    EditorialPromptResult,
    GenerationResult,
]:
    """Create a generation workflow with configured mock dependencies."""
    prompt_result = make_prompt_result(
        generation_allowed=generation_allowed
    )
    generation_result = make_generation_result()
    prompt_workflow = create_autospec(EditorialPromptWorkflow, instance=True)
    generation_service = create_autospec(GenerationService, instance=True)
    prompt_workflow.process.return_value = prompt_result
    generation_service.generate.return_value = generation_result
    configuration = make_configuration()
    workflow = EditorialGenerationWorkflow(
        prompt_workflow,
        generation_service,
        configuration,
    )
    return (
        workflow,
        prompt_workflow,
        generation_service,
        configuration,
        prompt_result,
        generation_result,
    )


def test_valid_input_uses_dependencies_once_in_order() -> None:
    """Forward exact inputs and return exact dependency results in order."""
    (
        workflow,
        prompt_workflow,
        generation_service,
        configuration,
        prompt_result,
        generation_result,
    ) = make_mocked_workflow()
    calls = Mock()
    calls.attach_mock(prompt_workflow, "prompt")
    calls.attach_mock(generation_service, "generation")
    original_configuration = replace(configuration)
    source_fields = dict(SOURCE_FIELDS)

    result = workflow.process(
        **source_fields,
        user_instruction="preserve emphasis",
    )

    assert isinstance(result, EditorialGenerationResult)
    assert result.prompt_result is prompt_result
    assert result.generation_result is generation_result
    assert workflow.prompt_workflow is prompt_workflow
    assert workflow.generation_service is generation_service
    assert workflow.generation_configuration is configuration
    assert calls.mock_calls == [
        call.prompt.process(
            **SOURCE_FIELDS,
            user_instruction="preserve emphasis",
        ),
        call.generation.generate(
            prompt=prompt_result.generation_prompt,
            configuration=configuration,
        ),
    ]
    assert configuration == original_configuration
    assert source_fields == SOURCE_FIELDS


@pytest.mark.parametrize(
    "failure",
    (
        SourceValidationError(("MISSING_TITLE",)),
        PromptConfigurationError("EDITORIAL_POLICY_MISSING"),
        RuntimeError("prompt workflow failed"),
    ),
)
def test_prompt_workflow_failures_propagate_unchanged(
    failure: Exception,
) -> None:
    """Propagate prompt workflow failures without calling generation."""
    workflow, prompt_workflow, generation_service, *_ = (
        make_mocked_workflow()
    )
    prompt_workflow.process.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    prompt_workflow.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    assert generation_service.mock_calls == []


@pytest.mark.parametrize(
    "failure",
    (
        GenerationError("PROVIDER_TIMEOUT"),
        RuntimeError("unexpected provider failure"),
    ),
)
def test_generation_failures_propagate_unchanged(
    failure: Exception,
) -> None:
    """Propagate service and provider failures without replacement or retry."""
    (
        workflow,
        prompt_workflow,
        generation_service,
        configuration,
        prompt_result,
        _,
    ) = make_mocked_workflow()
    generation_service.generate.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value is failure
    prompt_workflow.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    generation_service.generate.assert_called_once_with(
        prompt=prompt_result.generation_prompt,
        configuration=configuration,
    )


def test_generation_block_raises_and_skips_service() -> None:
    """Enforce generation eligibility after prompt preparation."""
    workflow, prompt_workflow, generation_service, *_ = (
        make_mocked_workflow(generation_allowed=False)
    )

    with pytest.raises(GenerationError) as raised:
        workflow.process(**SOURCE_FIELDS)

    assert raised.value.code == "GENERATION_INTERRUPTED"
    assert str(raised.value) == "GENERATION_INTERRUPTED"
    prompt_workflow.process.assert_called_once_with(
        **SOURCE_FIELDS,
        user_instruction=None,
    )
    assert generation_service.mock_calls == []


def test_result_model_is_immutable() -> None:
    """Prevent editorial generation result fields from reassignment."""
    prompt_result = make_prompt_result()
    generation_result = make_generation_result()
    result = EditorialGenerationResult(prompt_result, generation_result)

    with pytest.raises(FrozenInstanceError):
        result.generation_result = generation_result  # type: ignore[misc]
