"""Deterministic validation for provider-neutral adjudication configuration."""

from .semantic_adjudication_provider_config import (
    SemanticAdjudicationProviderConfig,
)
from .semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
)


class SemanticAdjudicationProviderConfigValidator:
    """Validate configuration values without accessing secrets or providers."""

    def validate(
        self,
        config: SemanticAdjudicationProviderConfig,
    ) -> SemanticAdjudicationProviderConfig:
        """Return the exact valid config or raise a deterministic error."""
        if not isinstance(config.provider, str) or not config.provider.strip():
            self._invalid("provider is empty")
        if not isinstance(config.model, str) or not config.model.strip():
            self._invalid("model is empty")
        if (
            not isinstance(config.api_key_env_var, str)
            or not config.api_key_env_var.strip()
        ):
            self._invalid("api_key_env_var is empty")
        if config.base_url is not None and (
            not isinstance(config.base_url, str) or not config.base_url.strip()
        ):
            self._invalid("base_url is empty")
        if (
            isinstance(config.timeout_seconds, bool)
            or not isinstance(config.timeout_seconds, (int, float))
            or not config.timeout_seconds > 0
        ):
            self._invalid("timeout_seconds must be greater than zero")
        if (
            isinstance(config.max_retries, bool)
            or not isinstance(config.max_retries, int)
            or config.max_retries < 0
        ):
            self._invalid("max_retries must be non-negative")
        if (
            isinstance(config.max_output_tokens, bool)
            or not isinstance(config.max_output_tokens, int)
            or config.max_output_tokens <= 0
        ):
            self._invalid("max_output_tokens must be greater than zero")
        if (
            isinstance(config.temperature, bool)
            or not isinstance(config.temperature, (int, float))
            or not 0.0 <= config.temperature <= 2.0
        ):
            self._invalid("temperature must be between zero and two")
        if not isinstance(config.enabled, bool):
            self._invalid("enabled must be boolean")
        return config

    @staticmethod
    def _invalid(message: str) -> None:
        raise SemanticAdjudicationProviderConfigurationError(message)
