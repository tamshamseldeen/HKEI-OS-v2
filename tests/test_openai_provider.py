"""Tests for the OpenAI Responses API provider adapter."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest

from src.generation.finish_reason import FinishReason
from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_error import GenerationError
from src.generation.generation_result import GenerationResult
from src.generation.openai_provider import OpenAIProvider
from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat


def make_prompt() -> GenerationPrompt:
    """Create a representative generation prompt."""
    return GenerationPrompt(
        " exact system prompt ",
        " exact user prompt ",
        "ar",
        120,
        OutputFormat.MARKDOWN_ARTICLE,
        (),
        (),
        (),
    )


def make_configuration(
    **changes: object,
) -> GenerationConfiguration:
    """Create representative OpenAI generation configuration."""
    configuration = GenerationConfiguration(
        "model-id",
        800,
        None,
        30.0,
        (("ignored", "metadata"),),
    )
    return replace(configuration, **changes)


def make_response(**changes: object) -> SimpleNamespace:
    """Create a representative mocked Responses API response."""
    values: dict[str, object] = {
        "output_text": "  exact output text  ",
        "model": "actual-model",
        "id": "response-id",
        "usage": SimpleNamespace(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        ),
        "status": "completed",
        "incomplete_details": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def make_provider(
    response: object | None = None,
) -> tuple[OpenAIProvider, MagicMock]:
    """Create a provider with an injected mock client."""
    client = MagicMock()
    client.responses.create.return_value = response or make_response()
    return OpenAIProvider(client=client), client


def test_missing_key_without_client_raises_api_key_missing() -> None:
    """Require a non-empty key only when constructing the SDK client."""
    for api_key in (None, "   "):
        with pytest.raises(GenerationError) as raised:
            OpenAIProvider(api_key=api_key)
        assert raised.value.code == "API_KEY_MISSING"


def test_injected_client_is_stored_without_api_key() -> None:
    """Store an injected client unchanged and do not expose a key in repr."""
    client = MagicMock()
    provider = OpenAIProvider(client=client)

    assert provider.client is client
    assert "secret-key" not in repr(provider)


def test_official_client_is_created_when_not_injected() -> None:
    """Construct the official client once with the supplied API key."""
    client = MagicMock()
    with patch("src.generation.openai_provider.OpenAI", return_value=client) as sdk:
        provider = OpenAIProvider(api_key="secret-key")

    sdk.assert_called_once_with(api_key="secret-key")
    assert provider.client is client
    assert "secret-key" not in repr(provider)
    assert not hasattr(provider, "api_key")


@pytest.mark.parametrize(
    ("changes", "code"),
    (
        ({"model": "  "}, "MODEL_MISSING"),
        ({"max_output_tokens": 0}, "INVALID_GENERATION_CONFIGURATION"),
        ({"timeout_seconds": 0.0}, "INVALID_GENERATION_CONFIGURATION"),
        ({"temperature": -0.1}, "INVALID_GENERATION_CONFIGURATION"),
        ({"temperature": 2.1}, "INVALID_GENERATION_CONFIGURATION"),
    ),
)
def test_invalid_configuration_prevents_request(
    changes: dict[str, object],
    code: str,
) -> None:
    """Reject invalid configuration without calling the API."""
    provider, client = make_provider()

    with pytest.raises(GenerationError) as raised:
        provider.generate(make_prompt(), make_configuration(**changes))

    assert raised.value.code == code
    assert client.responses.create.mock_calls == []


def test_required_request_arguments_and_content_are_exact() -> None:
    """Send exact prompt text and required configuration once."""
    provider, client = make_provider()
    prompt = make_prompt()
    configuration = make_configuration()
    original_prompt = replace(prompt)
    original_configuration = replace(configuration)

    result = provider.generate(prompt, configuration)

    client.responses.create.assert_called_once_with(
        model="model-id",
        instructions=" exact system prompt ",
        input=" exact user prompt ",
        max_output_tokens=800,
    )
    assert prompt == original_prompt
    assert configuration == original_configuration
    assert isinstance(result, GenerationResult)


def test_temperature_is_included_only_when_present() -> None:
    """Include temperature when configured and omit it when unavailable."""
    provider, client = make_provider()
    provider.generate(make_prompt(), make_configuration(temperature=0.5))
    assert client.responses.create.call_args.kwargs["temperature"] == 0.5

    provider, client = make_provider()
    provider.generate(make_prompt(), make_configuration(temperature=None))
    assert "temperature" not in client.responses.create.call_args.kwargs


def test_successful_response_is_normalized_without_rewriting() -> None:
    """Preserve output and map complete response metadata exactly."""
    provider, client = make_provider()

    result = provider.generate(make_prompt(), make_configuration())

    assert result == GenerationResult(
        content="  exact output text  ",
        provider_name="OPENAI",
        model_name="actual-model",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        finish_reason=FinishReason.COMPLETED,
        request_id="response-id",
        warnings=(),
    )
    client.responses.create.assert_called_once()


def test_missing_output_text_is_invalid() -> None:
    """Reject a response without an output_text attribute."""
    response = make_response()
    del response.output_text
    provider, client = make_provider(response)

    with pytest.raises(GenerationError) as raised:
        provider.generate(make_prompt(), make_configuration())

    assert raised.value.code == "PROVIDER_RESPONSE_INVALID"
    client.responses.create.assert_called_once()


@pytest.mark.parametrize("content", (None, "", " \t\n "))
def test_empty_output_raises_generation_empty(content: object) -> None:
    """Reject absent, empty, and whitespace-only output text."""
    provider, client = make_provider(make_response(output_text=content))

    with pytest.raises(GenerationError) as raised:
        provider.generate(make_prompt(), make_configuration())

    assert raised.value.code == "GENERATION_EMPTY"
    client.responses.create.assert_called_once()


@pytest.mark.parametrize("model", (None, "", "  "))
def test_missing_response_model_is_invalid(model: object) -> None:
    """Reject responses without a usable actual model identifier."""
    provider, _ = make_provider(make_response(model=model))

    with pytest.raises(GenerationError) as raised:
        provider.generate(make_prompt(), make_configuration())

    assert raised.value.code == "PROVIDER_RESPONSE_INVALID"


def test_missing_metadata_adds_warnings_in_stable_order() -> None:
    """Normalize absent usage, unknown finish status, and request ID."""
    response = make_response(
        usage=None,
        status="unexpected",
        id=None,
    )
    provider, _ = make_provider(response)

    result = provider.generate(make_prompt(), make_configuration())

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.total_tokens is None
    assert result.finish_reason is FinishReason.UNKNOWN
    assert result.request_id is None
    assert result.warnings == (
        "TOKEN_USAGE_UNAVAILABLE",
        "FINISH_REASON_UNKNOWN",
        "REQUEST_ID_UNAVAILABLE",
    )
    assert len(result.warnings) == len(set(result.warnings))


def test_partial_usage_is_preserved_and_total_is_calculated() -> None:
    """Keep available token values and safely calculate an absent total."""
    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        total_tokens=None,
    )
    provider, _ = make_provider(make_response(usage=usage))

    result = provider.generate(make_prompt(), make_configuration())

    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.total_tokens == 150
    assert result.warnings == ("PROVIDER_RESPONSE_INCOMPLETE",)


@pytest.mark.parametrize(
    ("status", "reason", "expected", "warnings"),
    (
        ("completed", None, FinishReason.COMPLETED, ()),
        (
            "incomplete",
            "max_output_tokens",
            FinishReason.LENGTH_LIMIT,
            ("OUTPUT_TRUNCATED",),
        ),
        (
            "incomplete",
            "safety_filter",
            FinishReason.CONTENT_FILTERED,
            (),
        ),
        ("stopped", None, FinishReason.STOPPED, ()),
        ("tool_call", None, FinishReason.TOOL_CALL, ()),
        (
            "unexpected",
            None,
            FinishReason.UNKNOWN,
            ("FINISH_REASON_UNKNOWN",),
        ),
    ),
)
def test_finish_reason_mapping(
    status: str,
    reason: str | None,
    expected: FinishReason,
    warnings: tuple[str, ...],
) -> None:
    """Map response status and incomplete reason deterministically."""
    details = SimpleNamespace(reason=reason) if reason is not None else None
    provider, _ = make_provider(
        make_response(status=status, incomplete_details=details)
    )

    result = provider.generate(make_prompt(), make_configuration())

    assert result.finish_reason is expected
    assert result.warnings == warnings


def make_status_error(
    error_type: type[openai.APIStatusError],
    status_code: int,
    message: str = "provider failure",
    body: object | None = None,
) -> openai.APIStatusError:
    """Create an official SDK status exception for mapping tests."""
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(status_code, request=request)
    return error_type(message, response=response, body=body)


@pytest.mark.parametrize(
    ("error", "code"),
    (
        (
            make_status_error(openai.AuthenticationError, 401),
            "PROVIDER_AUTHENTICATION_FAILED",
        ),
        (
            make_status_error(openai.PermissionDeniedError, 403),
            "PROVIDER_PERMISSION_DENIED",
        ),
        (
            make_status_error(openai.RateLimitError, 429),
            "PROVIDER_RATE_LIMITED",
        ),
        (
            make_status_error(
                openai.RateLimitError,
                429,
                body={"code": "insufficient_quota"},
            ),
            "PROVIDER_QUOTA_EXCEEDED",
        ),
        (
            make_status_error(openai.BadRequestError, 400),
            "PROVIDER_REQUEST_REJECTED",
        ),
        (
            make_status_error(openai.InternalServerError, 500),
            "PROVIDER_INTERNAL_ERROR",
        ),
        (
            make_status_error(openai.APIStatusError, 418),
            "PROVIDER_REQUEST_REJECTED",
        ),
        (
            make_status_error(openai.APIStatusError, 401),
            "PROVIDER_AUTHENTICATION_FAILED",
        ),
        (
            make_status_error(openai.APIStatusError, 403),
            "PROVIDER_PERMISSION_DENIED",
        ),
        (
            make_status_error(openai.APIStatusError, 429),
            "PROVIDER_RATE_LIMITED",
        ),
        (
            make_status_error(
                openai.APIStatusError,
                429,
                body={"error": {"code": "insufficient_quota"}},
            ),
            "PROVIDER_QUOTA_EXCEEDED",
        ),
        (
            make_status_error(openai.APIStatusError, 503),
            "PROVIDER_INTERNAL_ERROR",
        ),
    ),
)
def test_status_errors_are_mapped(
    error: openai.APIStatusError,
    code: str,
) -> None:
    """Map official status exceptions while preserving private context."""
    provider, client = make_provider()
    client.responses.create.side_effect = error

    with pytest.raises(GenerationError) as raised:
        provider.generate(make_prompt(), make_configuration())

    assert raised.value.code == code
    assert str(raised.value) == code
    assert raised.value.original_exception is error
    assert "provider failure" not in str(raised.value)
    client.responses.create.assert_called_once()


@pytest.mark.parametrize(
    ("error", "code"),
    (
        (
            openai.APITimeoutError(
                request=httpx.Request("POST", "https://example.invalid")
            ),
            "PROVIDER_TIMEOUT",
        ),
        (
            openai.APIConnectionError(
                request=httpx.Request("POST", "https://example.invalid")
            ),
            "PROVIDER_CONNECTION_FAILED",
        ),
        (
            openai.APIError(
                "unknown sdk failure",
                httpx.Request("POST", "https://example.invalid"),
                body=None,
            ),
            "UNKNOWN_PROVIDER_ERROR",
        ),
    ),
)
def test_non_status_sdk_errors_are_mapped(
    error: openai.APIError,
    code: str,
) -> None:
    """Map timeout, connection, and unknown official SDK errors."""
    provider, client = make_provider()
    client.responses.create.side_effect = error

    with pytest.raises(GenerationError) as raised:
        provider.generate(make_prompt(), make_configuration())

    assert raised.value.code == code
    assert raised.value.original_exception is error
    client.responses.create.assert_called_once()


@pytest.mark.parametrize(
    "error",
    (GenerationError("GENERATION_INTERRUPTED"), ValueError("unexpected")),
)
def test_non_sdk_errors_propagate_unchanged(error: Exception) -> None:
    """Propagate stable and unexpected non-SDK exceptions without remapping."""
    provider, client = make_provider()
    client.responses.create.side_effect = error

    with pytest.raises(type(error)) as raised:
        provider.generate(make_prompt(), make_configuration())

    assert raised.value is error
    client.responses.create.assert_called_once()
