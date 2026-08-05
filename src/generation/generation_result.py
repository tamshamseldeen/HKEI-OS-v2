"""Immutable normalized LLM generation result."""

from dataclasses import dataclass

from .finish_reason import FinishReason


@dataclass(frozen=True)
class GenerationResult:
    """Represent one normalized LLM generation result.

    Attributes:
        content: Unchanged raw model output.
        provider_name: Stable provider identifier.
        model_name: Actual model used for generation.
        input_tokens: Input token count when available.
        output_tokens: Output token count when available.
        total_tokens: Total token count when available.
        finish_reason: Normalized completion status.
        request_id: Provider request identifier when available.
        warnings: Machine-readable generation warnings.
    """

    content: str
    provider_name: str
    model_name: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    finish_reason: FinishReason
    request_id: str | None
    warnings: tuple[str, ...]
