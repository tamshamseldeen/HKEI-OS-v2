"""Immutable result of the editorial prompt workflow."""

from dataclasses import dataclass

from src.prompting.generation_prompt import GenerationPrompt

from .editorial_planning_result import EditorialPlanningResult


@dataclass(frozen=True)
class EditorialPromptResult:
    """Represent editorial planning and its generation prompt.

    Attributes:
        planning_result: Complete editorial planning result.
        generation_prompt: Deterministic provider-agnostic generation prompt.
    """

    planning_result: EditorialPlanningResult
    generation_prompt: GenerationPrompt
