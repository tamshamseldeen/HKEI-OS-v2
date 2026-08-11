"""Provider-neutral semantic adjudication configuration contract."""

from dataclasses import dataclass

from .semantic_adjudication_reasoning_effort import (
    SemanticAdjudicationReasoningEffort,
)


@dataclass(frozen=True)
class SemanticAdjudicationProviderConfig:
    """Store explicit configuration without resolving credentials."""

    provider: str
    model: str

    api_key_env_var: str

    base_url: str | None

    timeout_seconds: float

    max_retries: int

    max_output_tokens: int

    temperature: float
    reasoning_effort: SemanticAdjudicationReasoningEffort | None

    enabled: bool
