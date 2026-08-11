"""Immutable runtime configuration for semantic adjudication providers."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticAdjudicationRuntimeContext:
    """Hold validated provider settings and an in-memory resolved secret."""

    provider: str
    model: str

    api_key: str = field(repr=False)

    base_url: str | None

    timeout_seconds: float
    max_retries: int
    max_output_tokens: int
    temperature: float

    enabled: bool
