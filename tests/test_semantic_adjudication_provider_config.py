"""Tests for the semantic adjudication provider configuration contract."""

from dataclasses import FrozenInstanceError, fields
import inspect

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


def valid_config(**changes: object) -> SemanticAdjudicationProviderConfig:
    values = {
        "provider": "provider-name",
        "model": "model-name",
        "api_key_env_var": "PROVIDER_API_KEY",
        "base_url": None,
        "timeout_seconds": 30.0,
        "max_retries": 0,
        "max_output_tokens": 512,
        "temperature": 0.0,
        "enabled": True,
    }
    values.update(changes)
    return SemanticAdjudicationProviderConfig(**values)


def validate(**changes: object) -> SemanticAdjudicationProviderConfig:
    return SemanticAdjudicationProviderConfigValidator().validate(
        valid_config(**changes)
    )


def test_config_is_frozen_and_has_exact_field_order() -> None:
    config = valid_config()
    assert tuple(field.name for field in fields(config)) == (
        "provider",
        "model",
        "api_key_env_var",
        "base_url",
        "timeout_seconds",
        "max_retries",
        "max_output_tokens",
        "temperature",
        "enabled",
    )
    with pytest.raises(FrozenInstanceError):
        config.provider = "changed"


def test_valid_config_returns_exact_object() -> None:
    config = valid_config()
    assert SemanticAdjudicationProviderConfigValidator().validate(config) is config


@pytest.mark.parametrize("field", ("provider", "model", "api_key_env_var"))
@pytest.mark.parametrize("value", ("", " \t\n"))
def test_required_strings_reject_empty_and_whitespace(
    field: str,
    value: str,
) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match=rf"^{field} is empty$",
    ):
        validate(**{field: value})


def test_base_url_accepts_none_and_non_empty_string() -> None:
    assert validate(base_url=None).base_url is None
    assert validate(base_url="https://provider.invalid/v1").base_url == (
        "https://provider.invalid/v1"
    )


@pytest.mark.parametrize("value", ("", "  "))
def test_base_url_rejects_empty_or_whitespace(value: str) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^base_url is empty$",
    ):
        validate(base_url=value)


@pytest.mark.parametrize("value", (0.0, -0.1))
def test_timeout_rejects_zero_and_negative(value: float) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^timeout_seconds must be greater than zero$",
    ):
        validate(timeout_seconds=value)


def test_positive_timeout_is_accepted() -> None:
    assert validate(timeout_seconds=0.1).timeout_seconds == 0.1


@pytest.mark.parametrize("value", (0, 3))
def test_zero_and_positive_retries_are_accepted(value: int) -> None:
    assert validate(max_retries=value).max_retries == value


def test_negative_retries_are_rejected() -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^max_retries must be non-negative$",
    ):
        validate(max_retries=-1)


@pytest.mark.parametrize("value", (0, -1))
def test_non_positive_output_tokens_are_rejected(value: int) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^max_output_tokens must be greater than zero$",
    ):
        validate(max_output_tokens=value)


def test_positive_output_tokens_are_accepted() -> None:
    assert validate(max_output_tokens=1).max_output_tokens == 1


@pytest.mark.parametrize("value", (-0.01, 2.01))
def test_temperature_outside_generic_range_is_rejected(value: float) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^temperature must be between zero and two$",
    ):
        validate(temperature=value)


@pytest.mark.parametrize("value", (0.0, 2.0))
def test_temperature_boundaries_are_accepted(value: float) -> None:
    assert validate(temperature=value).temperature == value


@pytest.mark.parametrize("value", (True, False))
def test_boolean_enabled_values_are_accepted(value: bool) -> None:
    assert validate(enabled=value).enabled is value


@pytest.mark.parametrize("value", (0, 1, "true", None))
def test_non_boolean_enabled_values_are_rejected(value: object) -> None:
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^enabled must be boolean$",
    ):
        validate(enabled=value)


def test_validation_order_is_deterministic() -> None:
    config = valid_config(
        provider="",
        model="",
        api_key_env_var="",
        base_url="",
        timeout_seconds=0.0,
        max_retries=-1,
        max_output_tokens=0,
        temperature=-1.0,
        enabled="yes",
    )
    with pytest.raises(
        SemanticAdjudicationProviderConfigurationError,
        match="^provider is empty$",
    ):
        SemanticAdjudicationProviderConfigValidator().validate(config)


def test_contract_has_no_raw_secret_provider_specific_or_default_fields() -> None:
    config_fields = {field.name: field for field in fields(valid_config())}
    forbidden = {
        "api_key",
        "organization_id",
        "project_id",
        "deployment_name",
        "api_version",
        "region",
    }
    assert forbidden.isdisjoint(config_fields)
    assert all(field.default is field.default_factory for field in config_fields.values())


def test_modules_have_no_environment_http_provider_or_retry_implementation() -> None:
    modules = (
        inspect.getmodule(SemanticAdjudicationProviderConfig),
        inspect.getmodule(SemanticAdjudicationProviderConfigValidator),
    )
    source = "\n".join(inspect.getsource(module) for module in modules)
    forbidden = (
        "os.getenv",
        "os.environ",
        "dotenv",
        "requests",
        "httpx",
        "urllib",
        "aiohttp",
        "SemanticAdjudicationProvider(",
        "for attempt",
        "while attempt",
    )
    assert not any(value in source for value in forbidden)
