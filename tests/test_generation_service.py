"""Tests for the provider-agnostic generation service."""

from dataclasses import replace
from unittest.mock import create_autospec

import pytest

from src.generation.finish_reason import FinishReason
from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_error import GenerationError
from src.generation.generation_result import GenerationResult
from src.generation.generation_service import GenerationService
from src.generation.llm_provider import LLMProvider
from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat


def make_prompt() -> GenerationPrompt:
    """Create a representative provider-agnostic prompt."""
    return GenerationPrompt(
        system_prompt="system",
        user_prompt="user",
        target_language="ar",
        target_word_count=120,
        required_output_format=OutputFormat.MARKDOWN_ARTICLE,
        prohibited_content=("unsupported claim",),
        required_warnings=("warning",),
        reason_codes=("PROMPT_PLAN_INCLUDED",),
    )


def make_configuration() -> GenerationConfiguration:
    """Create representative generation configuration."""
    return GenerationConfiguration(
        model="model-id",
        max_output_tokens=800,
        temperature=None,
        reasoning_effort=None,
        timeout_seconds=30.0,
        request_metadata=(("workflow_id", "workflow-1"),),
    )


def make_result(content: str = "  raw model output  ") -> GenerationResult:
    """Create a representative normalized generation result."""
    return GenerationResult(
        content=content,
        provider_name="provider-id",
        model_name="model-id",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        finish_reason=FinishReason.COMPLETED,
        request_id="request-1",
        warnings=("PROVIDER_OPTION_IGNORED", "PROVIDER_OPTION_IGNORED"),
    )


def test_constructor_stores_supplied_provider() -> None:
    """Store the exact supplied provider without creating a default."""
    provider = create_autospec(LLMProvider, instance=True)

    service = GenerationService(provider)

    assert service.provider is provider
    assert provider.mock_calls == []


def test_generate_calls_provider_once_and_returns_result_unchanged() -> None:
    """Forward exact inputs once and preserve every successful result field."""
    prompt = make_prompt()
    configuration = make_configuration()
    expected = make_result()
    provider = create_autospec(LLMProvider, instance=True)
    provider.generate.return_value = expected
    service = GenerationService(provider)

    actual = service.generate(
        prompt=prompt,
        configuration=configuration,
    )

    assert actual is expected
    provider.generate.assert_called_once_with(prompt, configuration)
    assert actual.content == "  raw model output  "
    assert actual.warnings is expected.warnings
    assert actual.finish_reason is FinishReason.COMPLETED
    assert actual.input_tokens == 100
    assert actual.output_tokens == 50
    assert actual.total_tokens == 150
    assert actual.request_id == "request-1"


@pytest.mark.parametrize("content", ("", " \t\n "))
def test_empty_content_raises_generation_empty(content: str) -> None:
    """Reject empty or whitespace-only provider content after one call."""
    prompt = make_prompt()
    configuration = make_configuration()
    provider = create_autospec(LLMProvider, instance=True)
    provider.generate.return_value = make_result(content)
    service = GenerationService(provider)

    with pytest.raises(GenerationError) as raised:
        service.generate(prompt=prompt, configuration=configuration)

    assert raised.value.code == "GENERATION_EMPTY"
    assert str(raised.value) == "GENERATION_EMPTY"
    assert raised.value.original_exception is None
    provider.generate.assert_called_once_with(prompt, configuration)


@pytest.mark.parametrize(
    "result",
    (
        replace(
            make_result(),
            finish_reason=FinishReason.LENGTH_LIMIT,
        ),
        replace(
            make_result(),
            warnings=("OUTPUT_TRUNCATED",),
        ),
        replace(
            make_result(),
            finish_reason=FinishReason.UNKNOWN,
        ),
    ),
)
def test_incomplete_result_raises_generation_interrupted(
    result: GenerationResult,
) -> None:
    """Reject incomplete results without modifying them or calling twice."""
    prompt = make_prompt()
    configuration = make_configuration()
    original = replace(result)
    provider = create_autospec(LLMProvider, instance=True)
    provider.generate.return_value = result
    service = GenerationService(provider)

    with pytest.raises(GenerationError) as raised:
        service.generate(prompt=prompt, configuration=configuration)

    assert raised.value.code == "GENERATION_INTERRUPTED"
    assert result == original
    provider.generate.assert_called_once_with(prompt, configuration)


def test_provider_generation_error_propagates_unchanged() -> None:
    """Propagate stable provider errors without remapping or retrying."""
    prompt = make_prompt()
    configuration = make_configuration()
    expected = GenerationError("PROVIDER_TIMEOUT")
    provider = create_autospec(LLMProvider, instance=True)
    provider.generate.side_effect = expected
    service = GenerationService(provider)

    with pytest.raises(GenerationError) as raised:
        service.generate(prompt=prompt, configuration=configuration)

    assert raised.value is expected
    provider.generate.assert_called_once_with(prompt, configuration)


def test_unexpected_provider_exception_propagates_unchanged() -> None:
    """Propagate unexpected provider exceptions without remapping or retrying."""
    prompt = make_prompt()
    configuration = make_configuration()
    expected = RuntimeError("unexpected provider failure")
    provider = create_autospec(LLMProvider, instance=True)
    provider.generate.side_effect = expected
    service = GenerationService(provider)

    with pytest.raises(RuntimeError) as raised:
        service.generate(prompt=prompt, configuration=configuration)

    assert raised.value is expected
    provider.generate.assert_called_once_with(prompt, configuration)


def test_optional_result_metadata_remains_unchanged() -> None:
    """Return unavailable token and request metadata without modification."""
    expected = replace(
        make_result(),
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        finish_reason=FinishReason.COMPLETED,
        request_id=None,
        warnings=(),
    )
    provider = create_autospec(LLMProvider, instance=True)
    provider.generate.return_value = expected
    service = GenerationService(provider)

    actual = service.generate(
        prompt=make_prompt(),
        configuration=make_configuration(),
    )

    assert actual is expected
    assert actual.input_tokens is None
    assert actual.output_tokens is None
    assert actual.total_tokens is None
    assert actual.finish_reason is FinishReason.COMPLETED
    assert actual.request_id is None
    assert actual.warnings == ()
    provider.generate.assert_called_once()
