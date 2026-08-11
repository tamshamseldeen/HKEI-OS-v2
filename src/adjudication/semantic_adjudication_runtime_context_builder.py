"""Build provider-neutral semantic adjudication runtime context."""

from .semantic_adjudication_provider_config import (
    SemanticAdjudicationProviderConfig,
)
from .semantic_adjudication_provider_config_validator import (
    SemanticAdjudicationProviderConfigValidator,
)
from .semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
)
from .semantic_adjudication_runtime_context import (
    SemanticAdjudicationRuntimeContext,
)
from .semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


class SemanticAdjudicationRuntimeContextBuilder:
    """Validate config and resolve its secret into an immutable context."""

    def __init__(
        self,
        *,
        config_validator: SemanticAdjudicationProviderConfigValidator,
        secret_resolver: SemanticAdjudicationSecretResolver,
    ) -> None:
        self.config_validator = config_validator
        self.secret_resolver = secret_resolver

    def build(
        self,
        config: SemanticAdjudicationProviderConfig,
    ) -> SemanticAdjudicationRuntimeContext:
        """Build context in deterministic validation and resolution order."""
        validated_config = self.config_validator.validate(config)
        if not validated_config.enabled:
            raise SemanticAdjudicationProviderConfigurationError(
                "semantic adjudication provider is disabled"
            )
        api_key = self.secret_resolver.resolve(validated_config.api_key_env_var)
        if not isinstance(api_key, str) or not api_key.strip():
            raise SemanticAdjudicationProviderConfigurationError(
                "resolved api key is empty"
            )
        return SemanticAdjudicationRuntimeContext(
            provider=validated_config.provider,
            model=validated_config.model,
            api_key=api_key,
            base_url=validated_config.base_url,
            timeout_seconds=validated_config.timeout_seconds,
            max_retries=validated_config.max_retries,
            max_output_tokens=validated_config.max_output_tokens,
            temperature=validated_config.temperature,
            reasoning_effort=validated_config.reasoning_effort,
            enabled=validated_config.enabled,
        )
