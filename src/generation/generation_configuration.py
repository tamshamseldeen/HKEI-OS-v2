"""Immutable provider-agnostic generation configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationConfiguration:
    """Represent configuration for one LLM generation request.

    Attributes:
        model: Provider-specific model configuration value.
        max_output_tokens: Maximum number of output tokens requested.
        temperature: Optional generation temperature.
        reasoning_effort: Optional provider reasoning effort.
        timeout_seconds: Request timeout in seconds.
        request_metadata: Operational metadata key-value pairs.
    """

    model: str
    max_output_tokens: int
    temperature: float | None
    reasoning_effort: str | None
    timeout_seconds: float
    request_metadata: tuple[tuple[str, str], ...]
