"""Tests for the provider-neutral semantic adjudication interface."""

import inspect
from pathlib import Path

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.semantic_adjudication_provider import (
    SemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderConfigurationError,
    SemanticAdjudicationProviderError,
    SemanticAdjudicationProviderInvalidResponseError,
    SemanticAdjudicationProviderTimeoutError,
    SemanticAdjudicationProviderUnavailableError,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage


class StubSemanticAdjudicationProvider(SemanticAdjudicationProvider):
    """Return a fixed contract-valid response without external access."""

    @property
    def provider_name(self) -> str:
        return "stub-provider"

    @property
    def model_name(self) -> str:
        return "stub-model"

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        return SemanticAdjudicationResponse(
            adjudicated_topic=request.candidate_topics[0],
            adjudicated_format=request.candidate_formats[0],
            topic_confidence=AdjudicationConfidence.HIGH,
            format_confidence=AdjudicationConfidence.MEDIUM,
            topic_reason="Concise structured Topic rationale.",
            format_reason="Concise structured Format rationale.",
            topic_evidence_refs=("TITLE",),
            format_evidence_refs=("BODY_SENTENCE_0",),
            ambiguity_remaining=False,
            warnings=(),
            provider=self.provider_name,
            model=self.model_name,
            request_schema_version="1.0",
            response_schema_version="1.0",
            input_fingerprint=request.input_fingerprint,
            usage=SemanticAdjudicationUsage(10, 5, None),
        )


def make_request() -> SemanticAdjudicationRequest:
    return SemanticAdjudicationRequest(
        request_id="request-1",
        title="Title",
        lead="Lead.",
        body_excerpt="Evidence sentence.",
        deterministic_topic="GENERAL",
        topic_confidence="LOW",
        deterministic_format="STANDARD_NEWS",
        format_confidence="LOW",
        content_type="STANDARD_NEWS",
        contextual_support_labels=(),
        contextual_suppressions=(),
        semantic_relationship_summary=(),
        primary_domain_candidates=(),
        secondary_domain_candidates=(),
        semantic_format_support=(),
        semantic_format_suppression=(),
        topic_reason_codes=(),
        topic_warnings=(),
        format_reason_codes=(),
        format_warnings=(),
        candidate_topics=("GENERAL", "WORLD"),
        candidate_formats=("STANDARD_NEWS", "ANALYSIS"),
        input_fingerprint="a" * 64,
    )


def test_provider_is_abstract_and_cannot_be_instantiated() -> None:
    assert inspect.isabstract(SemanticAdjudicationProvider)
    assert SemanticAdjudicationProvider.__abstractmethods__ == {
        "adjudicate",
        "provider_name",
        "model_name",
    }
    with pytest.raises(TypeError):
        SemanticAdjudicationProvider()


def test_public_contract_members_are_abstract_and_synchronous() -> None:
    assert getattr(
        SemanticAdjudicationProvider.adjudicate, "__isabstractmethod__", False
    )
    assert SemanticAdjudicationProvider.provider_name.__isabstractmethod__
    assert SemanticAdjudicationProvider.model_name.__isabstractmethod__
    assert not inspect.iscoroutinefunction(SemanticAdjudicationProvider.adjudicate)


def test_stub_instantiates_accepts_request_and_returns_response() -> None:
    provider = StubSemanticAdjudicationProvider()
    request = make_request()
    response = provider.adjudicate(request)
    assert isinstance(response, SemanticAdjudicationResponse)
    assert response.adjudicated_topic in request.candidate_topics
    assert response.adjudicated_format in request.candidate_formats
    assert response.input_fingerprint == request.input_fingerprint
    assert provider.provider_name == response.provider == "stub-provider"
    assert provider.model_name == response.model == "stub-model"


@pytest.mark.parametrize(
    "error_type",
    (
        SemanticAdjudicationProviderUnavailableError,
        SemanticAdjudicationProviderTimeoutError,
        SemanticAdjudicationProviderInvalidResponseError,
        SemanticAdjudicationProviderConfigurationError,
    ),
)
def test_specific_errors_inherit_neutral_provider_error(
    error_type: type[SemanticAdjudicationProviderError],
) -> None:
    assert issubclass(error_type, SemanticAdjudicationProviderError)
    assert issubclass(error_type, RuntimeError)
    assert isinstance(error_type("failure"), SemanticAdjudicationProviderError)


def test_base_error_inherits_runtime_error() -> None:
    assert issubclass(SemanticAdjudicationProviderError, RuntimeError)


def test_errors_use_no_vendor_specific_names() -> None:
    module = inspect.getmodule(SemanticAdjudicationProviderError)
    source = inspect.getsource(module).casefold()
    assert not any(name in source for name in ("openai", "anthropic", "gemini"))


def test_interface_has_no_configuration_retry_or_execution_logic() -> None:
    fields = vars(SemanticAdjudicationProvider)
    assert "api_key" not in fields
    assert "timeout" not in fields
    assert "retry_count" not in fields
    source = inspect.getsource(SemanticAdjudicationProvider).casefold()
    forbidden = (
        "api_key",
        "base_url",
        "retry_count",
        "temperature",
        "max_tokens",
        "async def",
        "stream",
        "callback",
    )
    assert not any(value in source for value in forbidden)


def test_interface_imports_only_contract_models_and_standard_abc() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "adjudication"
        / "semantic_adjudication_provider.py"
    )
    source = path.read_text(encoding="utf-8")
    imports = "\n".join(
        line for line in source.splitlines()
        if line.startswith(("from ", "import "))
    ).casefold()
    assert not any(
        value in imports
        for value in (
            "openai",
            "anthropic",
            "gemini",
            "gate",
            "builder",
            "resolver",
            "workflow",
            "risk",
            "intent",
        )
    )
