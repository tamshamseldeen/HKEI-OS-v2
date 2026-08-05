"""OpenAI Responses API adapter for provider-agnostic generation."""

from typing import Any

import openai
from openai import OpenAI

from src.prompting.generation_prompt import GenerationPrompt

from .finish_reason import FinishReason
from .generation_configuration import GenerationConfiguration
from .generation_error import GenerationError
from .generation_result import GenerationResult
from .llm_provider import LLMProvider


_MISSING = object()
_QUOTA_SIGNALS = (
    "insufficient_quota",
    "quota exceeded",
    "exceeded your current quota",
)


class OpenAIProvider(LLMProvider):
    """Generate normalized results with the OpenAI Responses API."""

    provider_name = "OPENAI"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        """Initialize the OpenAI provider.

        Args:
            api_key: API key used only when constructing an SDK client.
            client: Optional injected SDK-compatible client.

        Raises:
            GenerationError: If neither a client nor a valid key is supplied.
        """
        if client is not None:
            self.client = client
            return
        if api_key is None or not api_key.strip():
            raise GenerationError("API_KEY_MISSING")
        self.client = OpenAI(api_key=api_key)

    def generate(
        self,
        prompt: GenerationPrompt,
        configuration: GenerationConfiguration,
    ) -> GenerationResult:
        """Submit one request and normalize its response.

        Args:
            prompt: Provider-agnostic generation prompt.
            configuration: Provider generation configuration.

        Returns:
            One normalized generation result.

        Raises:
            GenerationError: If configuration, response, or SDK behavior fails.
        """
        self._validate_configuration(configuration)
        request: dict[str, Any] = {
            "model": configuration.model,
            "instructions": prompt.system_prompt,
            "input": prompt.user_prompt,
            "max_output_tokens": configuration.max_output_tokens,
        }
        if configuration.temperature is not None:
            request["temperature"] = configuration.temperature

        try:
            response = self.client.responses.create(**request)
        except GenerationError:
            raise
        except openai.AuthenticationError as error:
            self._raise_mapped("PROVIDER_AUTHENTICATION_FAILED", error)
        except openai.PermissionDeniedError as error:
            self._raise_mapped("PROVIDER_PERMISSION_DENIED", error)
        except openai.RateLimitError as error:
            code = (
                "PROVIDER_QUOTA_EXCEEDED"
                if self._has_quota_signal(error)
                else "PROVIDER_RATE_LIMITED"
            )
            self._raise_mapped(code, error)
        except openai.APITimeoutError as error:
            self._raise_mapped("PROVIDER_TIMEOUT", error)
        except openai.APIConnectionError as error:
            self._raise_mapped("PROVIDER_CONNECTION_FAILED", error)
        except (openai.BadRequestError, openai.UnprocessableEntityError) as error:
            self._raise_mapped("PROVIDER_REQUEST_REJECTED", error)
        except openai.InternalServerError as error:
            self._raise_mapped("PROVIDER_INTERNAL_ERROR", error)
        except openai.APIStatusError as error:
            self._raise_mapped(self._map_status_error(error), error)
        except openai.APIError as error:
            self._raise_mapped("UNKNOWN_PROVIDER_ERROR", error)

        if response is None:
            raise GenerationError("PROVIDER_RESPONSE_INVALID")
        output_text = getattr(response, "output_text", _MISSING)
        if output_text is _MISSING:
            raise GenerationError("PROVIDER_RESPONSE_INVALID")
        if output_text is None or not isinstance(output_text, str):
            if output_text is None:
                raise GenerationError("GENERATION_EMPTY")
            raise GenerationError("PROVIDER_RESPONSE_INVALID")
        if not output_text.strip():
            raise GenerationError("GENERATION_EMPTY")

        model_name = getattr(response, "model", _MISSING)
        if (
            model_name is _MISSING
            or not isinstance(model_name, str)
            or not model_name.strip()
        ):
            raise GenerationError("PROVIDER_RESPONSE_INVALID")

        warnings: list[str] = []
        input_tokens, output_tokens, total_tokens = self._map_usage(
            response,
            warnings,
        )
        finish_reason = self._map_finish_reason(response)
        if finish_reason is FinishReason.UNKNOWN:
            self._add_warning(warnings, "FINISH_REASON_UNKNOWN")
        if finish_reason is FinishReason.LENGTH_LIMIT:
            self._add_warning(warnings, "OUTPUT_TRUNCATED")

        request_id = getattr(response, "id", None)
        if not isinstance(request_id, str) or not request_id.strip():
            request_id = None
            self._add_warning(warnings, "REQUEST_ID_UNAVAILABLE")

        return GenerationResult(
            content=output_text,
            provider_name=self.provider_name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            finish_reason=finish_reason,
            request_id=request_id,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_configuration(
        configuration: GenerationConfiguration,
    ) -> None:
        """Validate request configuration without inspecting editorial content."""
        if not configuration.model.strip():
            raise GenerationError("MODEL_MISSING")
        if configuration.max_output_tokens <= 0:
            raise GenerationError("INVALID_GENERATION_CONFIGURATION")
        if configuration.timeout_seconds <= 0:
            raise GenerationError("INVALID_GENERATION_CONFIGURATION")
        temperature = configuration.temperature
        if temperature is not None and not 0.0 <= temperature <= 2.0:
            raise GenerationError("INVALID_GENERATION_CONFIGURATION")

    @staticmethod
    def _map_usage(
        response: Any,
        warnings: list[str],
    ) -> tuple[int | None, int | None, int | None]:
        """Normalize available token usage values."""
        usage = getattr(response, "usage", None)
        if usage is None:
            OpenAIProvider._add_warning(warnings, "TOKEN_USAGE_UNAVAILABLE")
            return None, None, None

        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        values = (input_tokens, output_tokens, total_tokens)
        if any(value is None for value in values):
            OpenAIProvider._add_warning(
                warnings,
                "PROVIDER_RESPONSE_INCOMPLETE",
            )
        if (
            total_tokens is None
            and input_tokens is not None
            and output_tokens is not None
        ):
            total_tokens = input_tokens + output_tokens
        return input_tokens, output_tokens, total_tokens

    @staticmethod
    def _map_finish_reason(response: Any) -> FinishReason:
        """Normalize an OpenAI response completion status."""
        status = getattr(response, "status", None)
        normalized_status = status.lower() if isinstance(status, str) else ""
        if normalized_status == "completed":
            return FinishReason.COMPLETED
        if normalized_status == "incomplete":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", "") if details is not None else ""
            normalized_reason = reason.lower() if isinstance(reason, str) else ""
            if normalized_reason in ("max_output_tokens", "length"):
                return FinishReason.LENGTH_LIMIT
            if any(
                signal in normalized_reason
                for signal in ("content_filter", "safety", "refusal")
            ):
                return FinishReason.CONTENT_FILTERED
            return FinishReason.UNKNOWN
        if normalized_status in ("cancelled", "canceled", "stopped"):
            return FinishReason.STOPPED
        if "tool" in normalized_status:
            return FinishReason.TOOL_CALL
        return FinishReason.UNKNOWN

    @staticmethod
    def _map_status_error(error: openai.APIStatusError) -> str:
        """Map a general SDK status error to a stable generation code."""
        status_code = getattr(error, "status_code", None)
        if status_code == 401:
            return "PROVIDER_AUTHENTICATION_FAILED"
        if status_code == 403:
            return "PROVIDER_PERMISSION_DENIED"
        if status_code == 429:
            return (
                "PROVIDER_QUOTA_EXCEEDED"
                if OpenAIProvider._has_quota_signal(error)
                else "PROVIDER_RATE_LIMITED"
            )
        if isinstance(status_code, int) and status_code >= 500:
            return "PROVIDER_INTERNAL_ERROR"
        return "PROVIDER_REQUEST_REJECTED"

    @staticmethod
    def _has_quota_signal(error: Exception) -> bool:
        """Detect quota exhaustion without exposing provider error details."""
        candidates: list[Any] = [str(error)]
        for attribute in ("body", "code"):
            candidates.append(getattr(error, attribute, None))
        body = getattr(error, "body", None)
        if isinstance(body, dict):
            candidates.extend((body.get("code"), body.get("error")))
        combined = " ".join(str(value) for value in candidates if value is not None)
        lowered = combined.lower()
        return any(signal in lowered for signal in _QUOTA_SIGNALS)

    @staticmethod
    def _raise_mapped(code: str, error: Exception) -> None:
        """Raise one stable error while preserving the SDK exception."""
        raise GenerationError(code, original_exception=error) from error

    @staticmethod
    def _add_warning(warnings: list[str], warning: str) -> None:
        """Append one warning only when it is not already present."""
        if warning not in warnings:
            warnings.append(warning)
