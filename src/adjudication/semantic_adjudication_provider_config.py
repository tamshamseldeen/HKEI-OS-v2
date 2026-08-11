"""Provider-neutral semantic adjudication configuration contract."""

from dataclasses import dataclass


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

    enabled: bool
