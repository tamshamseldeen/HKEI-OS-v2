"""Tests for the provider-agnostic LLM provider interface."""

from typing import cast

import pytest

from src.generation.finish_reason import FinishReason
from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_result import GenerationResult
from src.generation.llm_provider import LLMProvider
from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat


class ConcreteProvider(LLMProvider):
    """Minimal provider implementation used only by interface tests."""

    def __init__(self, result: GenerationResult) -> None:
        """Initialize the test provider with its result."""
        self.result = result
        self.received_prompt: GenerationPrompt | None = None
        self.received_configuration: GenerationConfiguration | None = None

    def generate(
        self,
        prompt: GenerationPrompt,
        configuration: GenerationConfiguration,
    ) -> GenerationResult:
        """Record inputs and return the configured normalized result."""
        self.received_prompt = prompt
        self.received_configuration = configuration
        return self.result


def test_llm_provider_cannot_be_instantiated_directly() -> None:
    """Keep the provider contract abstract."""
    with pytest.raises(TypeError):
        cast(object, LLMProvider)()


def test_concrete_provider_receives_contract_models() -> None:
    """Allow implementations to receive exact prompt and configuration values."""
    prompt = GenerationPrompt(
        "system",
        "user",
        "ar",
        120,
        OutputFormat.MARKDOWN_ARTICLE,
        (),
        (),
        (),
    )
    configuration = GenerationConfiguration("model-id", 800, None, 30.0, ())
    expected = GenerationResult(
        "raw output",
        "provider-id",
        "model-id",
        None,
        None,
        None,
        FinishReason.COMPLETED,
        None,
        (),
    )
    provider = ConcreteProvider(expected)

    actual = provider.generate(prompt, configuration)

    assert actual is expected
    assert provider.received_prompt is prompt
    assert provider.received_configuration is configuration
