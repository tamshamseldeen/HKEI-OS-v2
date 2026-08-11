"""Provider-neutral semantic adjudication errors."""


class SemanticAdjudicationProviderError(RuntimeError):
    """Base error for failures at the semantic adjudication provider boundary."""


class SemanticAdjudicationProviderUnavailableError(
    SemanticAdjudicationProviderError
):
    """Indicate that the provider or its service is temporarily unavailable."""


class SemanticAdjudicationProviderTimeoutError(SemanticAdjudicationProviderError):
    """Indicate that a request exceeded the provider timeout."""


class SemanticAdjudicationProviderInvalidResponseError(
    SemanticAdjudicationProviderError
):
    """Indicate malformed output or output that violates the response contract."""


class SemanticAdjudicationProviderConfigurationError(
    SemanticAdjudicationProviderError
):
    """Indicate missing or invalid concrete-provider configuration."""
