"""Tests for environment-backed semantic adjudication secret resolution."""

import inspect
import pytest

from src.adjudication.environment_semantic_adjudication_secret_resolver import (
    EnvironmentSemanticAdjudicationSecretResolver,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
)
from src.adjudication.semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)


SECRET_NAME = "HKEI_TEST_SEMANTIC_ADJUDICATION_SECRET"


def test_resolver_implements_secret_resolver_abstraction() -> None:
    resolver = EnvironmentSemanticAdjudicationSecretResolver()
    assert isinstance(resolver, SemanticAdjudicationSecretResolver)


def test_valid_environment_value_is_returned_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "  exact-value-with-spacing  "
    monkeypatch.setenv(SECRET_NAME, value)
    assert EnvironmentSemanticAdjudicationSecretResolver().resolve(SECRET_NAME) == value


@pytest.mark.parametrize("secret_name", ("", " \t\n", None, 123))
def test_invalid_secret_name_is_rejected(secret_name: object) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^secret name is empty$",
    ):
        EnvironmentSemanticAdjudicationSecretResolver().resolve(secret_name)


def test_missing_environment_variable_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(SECRET_NAME, raising=False)
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^required secret is not available$",
    ):
        EnvironmentSemanticAdjudicationSecretResolver().resolve(SECRET_NAME)


@pytest.mark.parametrize("value", ("", " \t\n"))
def test_empty_environment_value_is_rejected_without_disclosure(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv(SECRET_NAME, value)
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^required secret is not available$",
    ) as caught:
        EnvironmentSemanticAdjudicationSecretResolver().resolve(SECRET_NAME)
    if value:
        assert value not in str(caught.value)


def test_repeated_resolution_observes_current_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = EnvironmentSemanticAdjudicationSecretResolver()
    monkeypatch.setenv(SECRET_NAME, "first-value")
    assert resolver.resolve(SECRET_NAME) == "first-value"
    monkeypatch.setenv(SECRET_NAME, "second-value")
    assert resolver.resolve(SECRET_NAME) == "second-value"


def test_resolver_uses_one_direct_lookup_without_enumeration_or_caching() -> None:
    import src.adjudication.environment_semantic_adjudication_secret_resolver as module

    source = inspect.getsource(module)
    assert "os.environ[secret_name]" in source
    assert "os.getenv" not in source
    assert "os.environ.get" not in source
    assert "os.environ.items" not in source
    assert "os.environ.keys" not in source
    assert "for " not in inspect.getsource(
        EnvironmentSemanticAdjudicationSecretResolver.resolve
    )
    assert not hasattr(EnvironmentSemanticAdjudicationSecretResolver(), "__dict__") or (
        EnvironmentSemanticAdjudicationSecretResolver().__dict__ == {}
    )


def test_module_has_no_forbidden_integrations() -> None:
    import src.adjudication.environment_semantic_adjudication_secret_resolver as module

    source = inspect.getsource(module)
    imports = "\n".join(
        line for line in source.splitlines()
        if line.startswith(("from ", "import "))
    )
    forbidden = (
        "dotenv",
        "requests",
        "httpx",
        "aiohttp",
        "urllib",
        "runtime_context",
        "provider_config",
        "semantic_adjudication_provider import",
        "openai",
        "anthropic",
        "gemini",
    )
    assert not any(value in imports.casefold() for value in forbidden)
    assert "SemanticAdjudicationRuntimeContext(" not in source
    assert "SemanticAdjudicationProvider(" not in source
    assert "print(" not in source
    assert "logging" not in source
