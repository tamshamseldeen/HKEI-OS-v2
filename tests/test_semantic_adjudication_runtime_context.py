"""Tests for provider-neutral adjudication runtime context primitives."""

from dataclasses import FrozenInstanceError, fields
import inspect
from unittest.mock import Mock

import pytest

from src.adjudication.semantic_adjudication_provider_config import (
    SemanticAdjudicationProviderConfig,
)
from src.adjudication.semantic_adjudication_provider_config_validator import (
    SemanticAdjudicationProviderConfigValidator,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
)
from src.adjudication.semantic_adjudication_runtime_context import (
    SemanticAdjudicationRuntimeContext,
)
from src.adjudication.semantic_adjudication_runtime_context_builder import (
    SemanticAdjudicationRuntimeContextBuilder,
)
from src.adjudication.semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


class DictionarySecretResolver(SemanticAdjudicationSecretResolver):
    """Resolve secrets from test-owned in-memory values."""

    def __init__(self, secrets: dict[str, object]) -> None:
        self.secrets = secrets
        self.calls: list[str] = []

    def resolve(self, secret_name: str) -> str:
        self.calls.append(secret_name)
        value = self.secrets[secret_name]
        return value


class RaisingSecretResolver(SemanticAdjudicationSecretResolver):
    def __init__(self, error: Exception) -> None:
        self.error = error

    def resolve(self, secret_name: str) -> str:
        raise self.error


def valid_config(**changes: object) -> SemanticAdjudicationProviderConfig:
    values = {
        "provider": "generic-provider",
        "model": "generic-model",
        "api_key_env_var": "GENERIC_PROVIDER_API_KEY",
        "base_url": "https://provider.invalid/v1",
        "timeout_seconds": 12.5,
        "max_retries": 2,
        "max_output_tokens": 700,
        "temperature": 0.25,
        "enabled": True,
    }
    values.update(changes)
    return SemanticAdjudicationProviderConfig(**values)


def builder(
    resolver: SemanticAdjudicationSecretResolver,
    validator: SemanticAdjudicationProviderConfigValidator | None = None,
) -> SemanticAdjudicationRuntimeContextBuilder:
    return SemanticAdjudicationRuntimeContextBuilder(
        config_validator=validator or SemanticAdjudicationProviderConfigValidator(),
        secret_resolver=resolver,
    )


def test_secret_resolver_is_abstract_and_cannot_be_instantiated() -> None:
    assert inspect.isabstract(SemanticAdjudicationSecretResolver)
    assert getattr(
        SemanticAdjudicationSecretResolver.resolve,
        "__isabstractmethod__",
        False,
    )
    with pytest.raises(TypeError):
        SemanticAdjudicationSecretResolver()


def test_dictionary_test_resolver_works() -> None:
    resolver = DictionarySecretResolver({"KEY": "secret"})
    assert resolver.resolve("KEY") == "secret"
    assert resolver.calls == ["KEY"]


def test_runtime_context_is_frozen_with_exact_field_order_and_hidden_key() -> None:
    context = builder(
        DictionarySecretResolver({"GENERIC_PROVIDER_API_KEY": "secret-value"})
    ).build(valid_config())
    assert tuple(field.name for field in fields(context)) == (
        "provider",
        "model",
        "api_key",
        "base_url",
        "timeout_seconds",
        "max_retries",
        "max_output_tokens",
        "temperature",
        "enabled",
    )
    assert fields(context)[2].repr is False
    assert "secret-value" not in repr(context)
    with pytest.raises(FrozenInstanceError):
        context.model = "changed"


def test_builder_validates_before_resolving_and_copies_exact_values() -> None:
    events: list[str] = []
    real_validator = SemanticAdjudicationProviderConfigValidator()
    validator = Mock(spec=SemanticAdjudicationProviderConfigValidator)

    def validate(config: SemanticAdjudicationProviderConfig) -> object:
        events.append("validate")
        return real_validator.validate(config)

    validator.validate.side_effect = validate
    resolver = DictionarySecretResolver(
        {"GENERIC_PROVIDER_API_KEY": "  exact-secret  "}
    )
    original_resolve = resolver.resolve

    def resolve(secret_name: str) -> str:
        events.append("resolve")
        return original_resolve(secret_name)

    resolver.resolve = resolve
    config = valid_config()
    context = builder(resolver, validator).build(config)
    assert events == ["validate", "resolve"]
    assert resolver.calls == [config.api_key_env_var]
    assert context.provider == config.provider
    assert context.model == config.model
    assert context.api_key == "  exact-secret  "
    assert context.base_url == config.base_url
    assert context.timeout_seconds == config.timeout_seconds
    assert context.max_retries == config.max_retries
    assert context.max_output_tokens == config.max_output_tokens
    assert context.temperature == config.temperature
    assert context.enabled == config.enabled
    assert "api_key_env_var" not in {field.name for field in fields(context)}


def test_disabled_config_is_rejected_without_secret_resolution() -> None:
    resolver = DictionarySecretResolver({})
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^semantic adjudication provider is disabled$",
    ):
        builder(resolver).build(valid_config(enabled=False))
    assert resolver.calls == []


@pytest.mark.parametrize("secret", (None, "", " \t\n", 123))
def test_invalid_resolved_secret_is_rejected_without_disclosure(
    secret: object,
) -> None:
    resolver = DictionarySecretResolver({"GENERIC_PROVIDER_API_KEY": secret})
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^resolved api key is empty$",
    ) as caught:
        builder(resolver).build(valid_config())
    assert resolver.calls == ["GENERIC_PROVIDER_API_KEY"]
    assert repr(secret) not in str(caught.value)


@pytest.mark.parametrize(
    "error",
    (
        SemanticAdjudicationProviderConfigurationError("secret unavailable"),
        ValueError("programming error"),
    ),
)
def test_resolver_errors_propagate_unchanged(error: Exception) -> None:
    with pytest.raises(type(error), match=f"^{str(error)}$") as caught:
        builder(RaisingSecretResolver(error)).build(valid_config())
    assert caught.value is error


def test_equal_inputs_and_resolver_behavior_produce_equal_contexts() -> None:
    config = valid_config()
    first = builder(
        DictionarySecretResolver({config.api_key_env_var: "same-secret"})
    ).build(config)
    second = builder(
        DictionarySecretResolver({config.api_key_env_var: "same-secret"})
    ).build(config)
    assert first == second


def test_builder_has_no_environment_http_provider_retry_or_contract_logic() -> None:
    import src.adjudication.semantic_adjudication_runtime_context_builder as module

    source = inspect.getsource(module)
    forbidden = (
        "os.getenv",
        "os.environ",
        "dotenv",
        "requests",
        "httpx",
        "aiohttp",
        "urllib.request",
        "SemanticAdjudicationProvider(",
        "SemanticAdjudicationRequest",
        "SemanticAdjudicationResponse",
        "for attempt",
        "while attempt",
    )
    assert not any(value in source for value in forbidden)
