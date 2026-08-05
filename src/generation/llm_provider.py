"""Abstract provider interface for LLM generation."""

from abc import ABC, abstractmethod

from src.prompting.generation_prompt import GenerationPrompt

from .generation_configuration import GenerationConfiguration
from .generation_result import GenerationResult


class LLMProvider(ABC):
    """Define the provider-agnostic LLM generation contract."""

    @abstractmethod
    def generate(
        self,
        prompt: GenerationPrompt,
        configuration: GenerationConfiguration,
    ) -> GenerationResult:
        """Generate one normalized result.

        Args:
            prompt: Provider-agnostic generation prompt.
            configuration: Provider generation configuration.

        Returns:
            One normalized generation result.
        """
        pass
