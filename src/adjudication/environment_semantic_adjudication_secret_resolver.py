"""Resolve semantic adjudication secrets from the process environment."""

import os

from .semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
)
from .semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


class EnvironmentSemanticAdjudicationSecretResolver(
    SemanticAdjudicationSecretResolver
):
    """Resolve one exact environment variable on every call."""

    def resolve(self, secret_name: str) -> str:
        """Return an unchanged, non-empty environment secret value."""
        if not isinstance(secret_name, str) or not secret_name.strip():
            raise SemanticAdjudicationProviderConfigurationError(
                "secret name is empty"
            )
        try:
            secret = os.environ[secret_name]
        except KeyError:
            raise SemanticAdjudicationProviderConfigurationError(
                "required secret is not available"
            ) from None
        if not isinstance(secret, str) or not secret.strip():
            raise SemanticAdjudicationProviderConfigurationError(
                "required secret is not available"
            )
        return secret
