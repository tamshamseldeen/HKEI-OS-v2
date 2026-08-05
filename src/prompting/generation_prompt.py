"""Immutable provider-agnostic generation prompt model."""

from dataclasses import dataclass

from .output_format import OutputFormat


@dataclass(frozen=True)
class GenerationPrompt:
    """Represent a provider-agnostic editorial generation request.

    Attributes:
        system_prompt: System-level editorial and safety instructions.
        user_prompt: Source-specific generation instructions and material.
        target_language: Required language of generated content.
        target_word_count: Editorial target word count.
        required_output_format: Required generated-content format.
        prohibited_content: Content the generated article must not include.
        required_warnings: Workflow warnings relevant to generation.
        reason_codes: Stable codes explaining prompt construction.
    """

    system_prompt: str
    user_prompt: str
    target_language: str
    target_word_count: int
    required_output_format: OutputFormat
    prohibited_content: tuple[str, ...]
    required_warnings: tuple[str, ...]
    reason_codes: tuple[str, ...]
