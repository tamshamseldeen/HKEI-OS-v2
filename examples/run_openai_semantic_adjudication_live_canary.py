"""Run one explicitly configured OpenAI adjudication request in shadow mode."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import OpenAI

from src.adjudication.environment_semantic_adjudication_secret_resolver import (
    EnvironmentSemanticAdjudicationSecretResolver,
)
from src.adjudication.openai_semantic_adjudication_provider import (
    OpenAISemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_config import (
    SemanticAdjudicationProviderConfig,
)
from src.adjudication.semantic_adjudication_provider import (
    SemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_config_validator import (
    SemanticAdjudicationProviderConfigValidator,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
    SemanticAdjudicationProviderError,
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
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)


CANARY_SOURCE = {
    "title": "خطة حكومية جديدة تثير نقاشاً حول آثارها",
    "body": (
        "أعلنت الحكومة خطة جديدة لإعادة تنظيم خدمات عامة، بينما قال خبراء إن "
        "آثارها الاقتصادية والاجتماعية تحتاج إلى تحليل أوسع. ويشرح التقرير "
        "خلفية القرار والخلاف المؤسسي حول تنفيذه."
    ),
    "source_name": "مصدر اصطناعي محلي",
    "source_url": "https://canary.invalid/synthetic-arabic-editorial",
    "language": "ar",
}
API_KEY_ENV_VAR = "OPENAI_API_KEY"

EXIT_SUCCESS = 0
EXIT_CONFIGURATION_ERROR = 2
EXIT_PROVIDER_ERROR = 3
EXIT_INVALID_RESPONSE = 4


@dataclass(frozen=True)
class CanaryReport:
    """Store only sanitized, console-safe canary observations."""

    status: str
    provider: str
    model: str
    gate_scope: str
    provider_called: bool
    response_valid: bool
    deterministic_topic: str
    deterministic_format: str
    adjudicated_topic: str | None
    adjudicated_format: str | None
    ambiguity_remaining: bool | None
    input_tokens: int
    output_tokens: int
    latency_milliseconds: int
    input_fingerprint: str | None
    shadow_topic_mutated: bool
    shadow_format_mutated: bool
    shadow_intent_mutated: bool
    error_category: str | None
    sanitized_provider_error: str | None
    exit_code: int


class _SingleRequestResponses:
    def __init__(self, responses: Any) -> None:
        self._responses = responses
        self.call_count = 0

    def create(self, **kwargs: Any) -> Any:
        if self.call_count >= 1:
            raise RuntimeError("live canary permits at most one provider call")
        self.call_count += 1
        return self._responses.create(**kwargs)


class _SingleRequestClient:
    def __init__(self, client: Any) -> None:
        self.responses = _SingleRequestResponses(client.responses)


class _SanitizedErrorCapturingProvider(SemanticAdjudicationProvider):
    """Retain only an HKEI provider-neutral sanitized error message."""

    def __init__(self, provider: SemanticAdjudicationProvider) -> None:
        self._provider = provider
        self.sanitized_error: str | None = None

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def adjudicate(self, request: Any) -> Any:
        try:
            return self._provider.adjudicate(request)
        except SemanticAdjudicationProviderError as error:
            self.sanitized_error = str(error)
            raise


def _create_openai_client(context: SemanticAdjudicationRuntimeContext) -> Any:
    """Construct the official client only after live configuration succeeds."""
    return OpenAI(
        api_key=context.api_key,
        base_url=context.base_url,
        timeout=context.timeout_seconds,
        max_retries=0,
    )


def _configuration(model: str) -> SemanticAdjudicationProviderConfig:
    return SemanticAdjudicationProviderConfig(
        provider="openai",
        model=model,
        api_key_env_var=API_KEY_ENV_VAR,
        base_url=None,
        timeout_seconds=30.0,
        max_retries=0,
        max_output_tokens=500,
        temperature=0.0,
        enabled=True,
    )


def _configuration_error_report(model: str) -> CanaryReport:
    return CanaryReport(
        status="CONFIGURATION_ERROR",
        provider="openai",
        model=model,
        gate_scope="NONE",
        provider_called=False,
        response_valid=False,
        deterministic_topic="NONE",
        deterministic_format="NONE",
        adjudicated_topic=None,
        adjudicated_format=None,
        ambiguity_remaining=None,
        input_tokens=0,
        output_tokens=0,
        latency_milliseconds=0,
        input_fingerprint=None,
        shadow_topic_mutated=False,
        shadow_format_mutated=False,
        shadow_intent_mutated=False,
        error_category="SemanticAdjudicationProviderConfigurationError",
        sanitized_provider_error=None,
        exit_code=EXIT_CONFIGURATION_ERROR,
    )


def run_canary(
    *,
    model: str,
    config_validator: SemanticAdjudicationProviderConfigValidator | None = None,
    secret_resolver: SemanticAdjudicationSecretResolver | None = None,
    client_factory: Callable[[SemanticAdjudicationRuntimeContext], Any] | None = None,
    adjudication_gate: Any = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> CanaryReport:
    """Run the fixed synthetic source through at most one provider request."""
    validator = config_validator or SemanticAdjudicationProviderConfigValidator()
    resolver = secret_resolver or EnvironmentSemanticAdjudicationSecretResolver()
    context_builder = SemanticAdjudicationRuntimeContextBuilder(
        config_validator=validator,
        secret_resolver=resolver,
    )
    try:
        runtime_context = context_builder.build(_configuration(model))
        raw_client = (client_factory or _create_openai_client)(runtime_context)
    except SemanticAdjudicationProviderConfigurationError:
        return _configuration_error_report(model)

    guarded_client = _SingleRequestClient(raw_client)
    openai_provider = OpenAISemanticAdjudicationProvider(
        runtime_context=runtime_context,
        client=guarded_client,
    )
    provider = _SanitizedErrorCapturingProvider(openai_provider)
    workflow_arguments = {"provider": provider}
    if adjudication_gate is not None:
        workflow_arguments["adjudication_gate"] = adjudication_gate
    workflow = ExperimentalSemanticAdjudicationShadowWorkflow(**workflow_arguments)

    started = monotonic()
    result = workflow.analyze(**CANARY_SOURCE)
    latency_milliseconds = max(0, round((monotonic() - started) * 1000))
    request = result.request
    response = result.validated_response
    editorial = result.editorial_result
    deterministic_topic = editorial.topic_classification.topic.value
    deterministic_format = editorial.format_classification.editorial_format.value
    topic_mutated = bool(
        request and request.deterministic_topic != deterministic_topic
    )
    format_mutated = bool(
        request and request.deterministic_format != deterministic_format
    )

    if request is None:
        status = "SKIPPED"
        exit_code = EXIT_SUCCESS
        error_category = "CANARY_SKIPPED_NOT_REQUIRED"
    elif result.response_valid:
        status = "SUCCESS"
        exit_code = EXIT_SUCCESS
        error_category = None
    elif result.provider_error == "SemanticAdjudicationProviderConfigurationError":
        status = "CONFIGURATION_ERROR"
        exit_code = EXIT_CONFIGURATION_ERROR
        error_category = result.provider_error
    elif result.provider_error == "SemanticAdjudicationProviderInvalidResponseError":
        status = "INVALID_RESPONSE"
        exit_code = EXIT_INVALID_RESPONSE
        error_category = result.provider_error
    else:
        status = "PROVIDER_ERROR"
        exit_code = EXIT_PROVIDER_ERROR
        error_category = result.provider_error or "PROVIDER_ERROR"

    return CanaryReport(
        status=status,
        provider="openai",
        model=runtime_context.model,
        gate_scope=result.adjudication_decision.scope.value,
        provider_called=result.provider_called,
        response_valid=result.response_valid,
        deterministic_topic=deterministic_topic,
        deterministic_format=deterministic_format,
        adjudicated_topic=response.adjudicated_topic if response else None,
        adjudicated_format=response.adjudicated_format if response else None,
        ambiguity_remaining=response.ambiguity_remaining if response else None,
        input_tokens=response.usage_input_tokens if response else 0,
        output_tokens=response.usage_output_tokens if response else 0,
        latency_milliseconds=latency_milliseconds,
        input_fingerprint=request.input_fingerprint if request else None,
        shadow_topic_mutated=topic_mutated,
        shadow_format_mutated=format_mutated,
        shadow_intent_mutated=False,
        error_category=error_category,
        sanitized_provider_error=provider.sanitized_error,
        exit_code=exit_code,
    )


def _display(value: Any) -> str:
    if value is None:
        return "NONE"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    return str(value)


def print_summary(report: CanaryReport) -> None:
    """Print only the approved sanitized canary fields."""
    print("=== OPENAI SEMANTIC ADJUDICATION LIVE CANARY ===")
    rows = (
        ("Status", report.status),
        ("Provider", report.provider),
        ("Model", report.model),
        ("Gate Scope", report.gate_scope),
        ("Provider Called", report.provider_called),
        ("Response Valid", report.response_valid),
        ("Deterministic Topic", report.deterministic_topic),
        ("Deterministic Format", report.deterministic_format),
        ("Adjudicated Topic", report.adjudicated_topic),
        ("Adjudicated Format", report.adjudicated_format),
        ("Ambiguity Remaining", report.ambiguity_remaining),
        ("Input Tokens", report.input_tokens),
        ("Output Tokens", report.output_tokens),
        ("Latency Milliseconds", report.latency_milliseconds),
        ("Input Fingerprint", report.input_fingerprint),
        ("Shadow Topic Mutated", report.shadow_topic_mutated),
        ("Shadow Format Mutated", report.shadow_format_mutated),
        ("Shadow Intent Mutated", report.shadow_intent_mutated),
        ("Sanitized Provider Error", report.sanitized_provider_error),
    )
    for label, value in rows:
        print(f"{label}:\n{_display(value)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one OpenAI semantic adjudication shadow canary."
    )
    parser.add_argument("--model", required=True)
    arguments = parser.parse_args(argv)
    report = run_canary(model=arguments.model)
    print_summary(report)
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
