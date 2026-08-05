"""Provider-agnostic service for one LLM generation request."""

from src.prompting.generation_prompt import GenerationPrompt

from .finish_reason import FinishReason
from .generation_configuration import GenerationConfiguration
from .generation_error import GenerationError
from .generation_result import GenerationResult
from .llm_provider import LLMProvider


class GenerationService:
    """Call one LLM provider and validate only returned content."""

    def __init__(self, provider: LLMProvider) -> None:
        """Initialize the generation service.

        Args:
            provider: Provider implementation used for generation.
        """
        self.provider = provider

    def generate(
        self,
        *,
        prompt: GenerationPrompt,
        configuration: GenerationConfiguration,
    ) -> GenerationResult:
        """Generate and return one normalized result.

        Args:
            prompt: Provider-agnostic generation prompt.
            configuration: Provider generation configuration.

        Returns:
            The exact normalized result returned by the provider.

        Raises:
            GenerationError: If content is empty or generation is incomplete.
        """
        result = self.provider.generate(prompt, configuration)
        if not result.content.strip():
            raise GenerationError(code="GENERATION_EMPTY")
        if (
            result.finish_reason is not FinishReason.COMPLETED
            or "OUTPUT_TRUNCATED" in result.warnings
        ):
            raise GenerationError(code="GENERATION_INTERRUPTED")
        return result
