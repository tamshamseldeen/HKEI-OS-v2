"""Immutable result of the editorial generation workflow."""

from dataclasses import dataclass

from src.generation.generation_result import GenerationResult

from .editorial_prompt_result import EditorialPromptResult


@dataclass(frozen=True)
class EditorialGenerationResult:
    """Represent prompt preparation and provider-backed generation.

    Attributes:
        prompt_result: Complete editorial prompt workflow result.
        generation_result: Normalized provider generation result.
    """

    prompt_result: EditorialPromptResult
    generation_result: GenerationResult
