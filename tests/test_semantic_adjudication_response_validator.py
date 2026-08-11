"""Tests for deterministic semantic adjudication response validation."""

from dataclasses import fields, replace
import inspect
from pathlib import Path
import socket
from typing import Callable

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.semantic_adjudication_provider import (
    SemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderInvalidResponseError,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)
from src.adjudication.semantic_adjudication_response_validator import (
    SemanticAdjudicationResponseValidator,
)
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage


class FakeSemanticAdjudicationProvider(SemanticAdjudicationProvider):
    """Test-only deterministic provider with an injectable response factory."""

    def __init__(
        self,
        response_factory: Callable[
            [SemanticAdjudicationRequest], SemanticAdjudicationResponse
        ] | None = None,
    ) -> None:
        self._response_factory = response_factory or valid_response

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        return self._response_factory(request)


def make_request(
    *,
    topics: tuple[str, ...] = ("GENERAL", "WORLD"),
    formats: tuple[str, ...] = ("STANDARD_NEWS", "ANALYSIS"),
) -> SemanticAdjudicationRequest:
    return SemanticAdjudicationRequest(
        request_id="request-1",
        title="Title",
        lead="Lead.",
        body_excerpt="Evidence.",
        deterministic_topic=topics[0],
        topic_confidence="LOW",
        deterministic_format=formats[0],
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
        candidate_topics=topics,
        candidate_formats=formats,
        input_fingerprint="f" * 64,
    )


def valid_response(
    request: SemanticAdjudicationRequest,
) -> SemanticAdjudicationResponse:
    return SemanticAdjudicationResponse(
        adjudicated_topic=request.candidate_topics[0],
        adjudicated_format=request.candidate_formats[0],
        topic_confidence=AdjudicationConfidence.HIGH,
        format_confidence=AdjudicationConfidence.MEDIUM,
        topic_reason="Topic rationale.",
        format_reason="Format rationale.",
        topic_evidence_refs=("TITLE",),
        format_evidence_refs=("BODY_SENTENCE_0",),
        ambiguity_remaining=False,
        warnings=("STRUCTURED_WARNING",),
        provider="fake",
        model="fake-model",
        request_schema_version="1.0",
        response_schema_version="1.0",
        input_fingerprint=request.input_fingerprint,
        usage=SemanticAdjudicationUsage(0, 0, None),
    )


def unsafe_usage(
    input_tokens: object,
    output_tokens: object,
    reasoning_tokens: object,
) -> SemanticAdjudicationUsage:
    usage = object.__new__(SemanticAdjudicationUsage)
    object.__setattr__(usage, "input_tokens", input_tokens)
    object.__setattr__(usage, "output_tokens", output_tokens)
    object.__setattr__(usage, "reasoning_tokens", reasoning_tokens)
    return usage


def validate(
    response: SemanticAdjudicationResponse,
    request: SemanticAdjudicationRequest | None = None,
) -> SemanticAdjudicationResponse:
    return SemanticAdjudicationResponseValidator().validate(
        request=request or make_request(),
        response=response,
    )


def test_valid_response_is_accepted_and_returned_by_identity() -> None:
    request = make_request()
    response = valid_response(request)
    assert validate(response, request) is response


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"adjudicated_topic": "CRIME"}, "adjudicated topic is not in request candidates"),
        ({"adjudicated_format": "GUIDE"}, "adjudicated format is not in request candidates"),
        ({"input_fingerprint": "x" * 64}, "input fingerprint mismatch"),
        ({"provider": ""}, "provider identity is empty"),
        ({"provider": "   "}, "provider identity is empty"),
        ({"model": ""}, "model identity is empty"),
        ({"request_schema_version": ""}, "request schema version is empty"),
        ({"response_schema_version": " "}, "response schema version is empty"),
        ({"topic_confidence": "HIGH"}, "topic confidence is invalid"),
        ({"format_confidence": "MEDIUM"}, "format confidence is invalid"),
        ({"topic_reason": ""}, "topic reason is required"),
        ({"format_reason": " "}, "format reason is required"),
        ({"topic_evidence_refs": ()}, "topic evidence refs are required"),
        ({"format_evidence_refs": ()}, "format evidence refs are required"),
        ({"topic_evidence_refs": ("",)}, "topic evidence refs contain an invalid item"),
        ({"format_evidence_refs": (1,)}, "format evidence refs contain an invalid item"),
        ({"warnings": ("ok", 1)}, "warnings must be a tuple of strings"),
        ({"ambiguity_remaining": 1}, "ambiguity remaining is not boolean"),
        ({"usage": object()}, "usage is invalid"),
        (
            {"usage": unsafe_usage(-1, 0, None)},
            "usage input tokens must be non-negative",
        ),
        (
            {"usage": unsafe_usage(0, -1, None)},
            "usage output tokens must be non-negative",
        ),
        (
            {"usage": unsafe_usage(0, 1, -1)},
            "usage reasoning tokens must be non-negative",
        ),
        (
            {"usage": unsafe_usage(0, 1, 2)},
            "usage reasoning tokens exceed output tokens",
        ),
    ),
)
def test_invalid_response_fields_are_rejected_in_deterministic_order(
    changes: dict[str, object],
    message: str,
) -> None:
    response = replace(valid_response(make_request()), **changes)
    with pytest.raises(
        SemanticAdjudicationProviderInvalidResponseError,
        match=f"^{message}$",
    ):
        validate(response)


def test_empty_reasons_and_evidence_are_allowed_for_single_candidate_dimensions() -> None:
    request = make_request(topics=("GENERAL",), formats=("STANDARD_NEWS",))
    response = replace(
        valid_response(request),
        topic_reason="",
        format_reason="",
        topic_evidence_refs=(),
        format_evidence_refs=(),
    )
    assert validate(response, request) is response


def test_warning_tuple_ambiguity_true_and_zero_usage_are_valid() -> None:
    request = make_request()
    response = replace(
        valid_response(request),
        ambiguity_remaining=True,
        warnings=(),
        usage=SemanticAdjudicationUsage(0, 0, 0),
    )
    assert validate(response, request) is response


def test_fake_provider_implements_interface_and_is_deterministic() -> None:
    provider = FakeSemanticAdjudicationProvider()
    request = make_request()
    assert isinstance(provider, SemanticAdjudicationProvider)
    assert provider.provider_name == "fake"
    assert provider.model_name == "fake-model"
    assert provider.adjudicate(request) == provider.adjudicate(request)
    assert validate(provider.adjudicate(request), request)


def test_validator_never_calls_provider() -> None:
    class ExplodingProvider(FakeSemanticAdjudicationProvider):
        def adjudicate(
            self,
            request: SemanticAdjudicationRequest,
        ) -> SemanticAdjudicationResponse:
            raise AssertionError("provider must not be called")

    request = make_request()
    provider = ExplodingProvider()
    response = valid_response(request)
    assert SemanticAdjudicationResponseValidator().validate(
        request=request,
        response=response,
    ) is response
    assert provider.provider_name == "fake"


def test_response_contract_has_no_raw_payload_or_hidden_reasoning_fields() -> None:
    names = {field.name for field in fields(SemanticAdjudicationResponse)}
    assert names.isdisjoint(
        {"raw_response", "chain_of_thought", "provider_json", "logprobs"}
    )


def test_validator_has_no_benchmark_api_provider_or_resolver_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.adjudication.semantic_adjudication_response_validator as module

    source = inspect.getsource(module).casefold()
    imports = "\n".join(
        line for line in source.splitlines()
        if line.startswith(("from ", "import "))
    )
    forbidden = (
        "benchmark",
        "openai",
        "provider.adjudicate",
        "resolver",
        "workflow",
        "risk",
        "reader_intent",
    )
    assert not any(value in imports for value in forbidden)
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *args, **kwargs: pytest.fail("network access attempted"),
    )
    request = make_request()
    assert validate(valid_response(request), request)
