"""Deterministic validation for semantic adjudication provider responses."""

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderInvalidResponseError,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)


class SemanticAdjudicationResponseValidator:
    """Validate untrusted response structure against its originating request."""

    def validate(
        self,
        *,
        request: SemanticAdjudicationRequest,
        response: SemanticAdjudicationResponse,
    ) -> SemanticAdjudicationResponse:
        """Return the exact valid response or raise a deterministic error."""
        if response.adjudicated_topic not in request.candidate_topics:
            self._invalid("adjudicated topic is not in request candidates")
        if response.adjudicated_format not in request.candidate_formats:
            self._invalid("adjudicated format is not in request candidates")
        if response.input_fingerprint != request.input_fingerprint:
            self._invalid("input fingerprint mismatch")
        if not isinstance(response.provider, str) or not response.provider.strip():
            self._invalid("provider identity is empty")
        if not isinstance(response.model, str) or not response.model.strip():
            self._invalid("model identity is empty")
        if (
            not isinstance(response.request_schema_version, str)
            or not response.request_schema_version.strip()
        ):
            self._invalid("request schema version is empty")
        if (
            not isinstance(response.response_schema_version, str)
            or not response.response_schema_version.strip()
        ):
            self._invalid("response schema version is empty")
        if not isinstance(response.topic_confidence, AdjudicationConfidence):
            self._invalid("topic confidence is invalid")
        if not isinstance(response.format_confidence, AdjudicationConfidence):
            self._invalid("format confidence is invalid")
        if not isinstance(response.topic_reason, str):
            self._invalid("topic reason is not a string")
        if len(request.candidate_topics) > 1 and not response.topic_reason.strip():
            self._invalid("topic reason is required")
        if not isinstance(response.format_reason, str):
            self._invalid("format reason is not a string")
        if len(request.candidate_formats) > 1 and not response.format_reason.strip():
            self._invalid("format reason is required")
        self._validate_evidence_refs(
            name="topic",
            values=response.topic_evidence_refs,
            required=len(request.candidate_topics) > 1,
        )
        self._validate_evidence_refs(
            name="format",
            values=response.format_evidence_refs,
            required=len(request.candidate_formats) > 1,
        )
        if not isinstance(response.ambiguity_remaining, bool):
            self._invalid("ambiguity remaining is not boolean")
        if not isinstance(response.warnings, tuple) or not all(
            isinstance(warning, str) for warning in response.warnings
        ):
            self._invalid("warnings must be a tuple of strings")
        self._validate_usage("input", response.usage_input_tokens)
        self._validate_usage("output", response.usage_output_tokens)
        return response

    def _validate_evidence_refs(
        self,
        *,
        name: str,
        values: object,
        required: bool,
    ) -> None:
        if not isinstance(values, tuple):
            self._invalid(f"{name} evidence refs must be a tuple of strings")
        if not all(
            isinstance(value, str) and bool(value.strip()) for value in values
        ):
            self._invalid(f"{name} evidence refs contain an invalid item")
        if required and not values:
            self._invalid(f"{name} evidence refs are required")

    def _validate_usage(self, name: str, value: object) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            self._invalid(f"usage {name} tokens must be non-negative")

    @staticmethod
    def _invalid(message: str) -> None:
        raise SemanticAdjudicationProviderInvalidResponseError(message)
