"""Pure deterministic authority selection for limited editorial resolution."""

from dataclasses import dataclass
from enum import Enum

from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_ambiguity import EditorialFormatAmbiguity
from src.formatting.editorial_format_completeness import EditorialFormatCompleteness
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_confidence import ReaderIntentConfidence
from src.topic.topic import Topic
from src.topic.topic_confidence import TopicConfidence

from .editorial_dimension_resolution import (
    EditorialDimensionResolution,
    EditorialResolutionDimension,
)
from .editorial_resolution_result import EditorialResolutionResult
from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .editorial_resolution_warning import EditorialResolutionWarning


class EditorialResolverProviderStatus(str, Enum):
    """Normalized provider outcome available before resolution begins."""

    NOT_CALLED = "NOT_CALLED"
    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"


@dataclass(frozen=True)
class EditorialFormatV2TrustSignal:
    """Carry non-authoritative V2 diagnostics without executing V2."""

    selected_format: EditorialFormat
    confidence: EditorialFormatConfidence
    ambiguity: EditorialFormatAmbiguity
    completeness: EditorialFormatCompleteness
    material_competition: bool = False
    contradiction: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.selected_format, EditorialFormat):
            raise ValueError("selected_format must be an EditorialFormat")
        if not isinstance(self.confidence, EditorialFormatConfidence):
            raise ValueError("confidence must be an EditorialFormatConfidence")
        if not isinstance(self.ambiguity, EditorialFormatAmbiguity):
            raise ValueError("ambiguity must be an EditorialFormatAmbiguity")
        if not isinstance(self.completeness, EditorialFormatCompleteness):
            raise ValueError("completeness must be an EditorialFormatCompleteness")
        if not isinstance(self.material_competition, bool) or not isinstance(self.contradiction, bool):
            raise ValueError("trust flags must be booleans")


@dataclass(frozen=True)
class LimitedEditorialResolverInput:
    """Explicit immutable inputs produced before pure resolution."""

    deterministic_topic: Topic
    deterministic_topic_confidence: TopicConfidence
    deterministic_topic_ambiguity: bool
    deterministic_format: EditorialFormat
    deterministic_format_confidence: EditorialFormatConfidence
    deterministic_format_ambiguity: bool
    deterministic_reader_intent: ReaderIntent
    deterministic_reader_intent_confidence: ReaderIntentConfidence
    scope: AdjudicationScope
    provider_status: EditorialResolverProviderStatus
    validated_adjudication_response: SemanticAdjudicationResponse | None
    legal_topic_candidates: tuple[Topic, ...]
    legal_format_candidates: tuple[EditorialFormat, ...]
    expected_input_fingerprint: str | None
    format_v2_trust_signal: EditorialFormatV2TrustSignal | None = None

    def __post_init__(self) -> None:
        typed = (
            (self.deterministic_topic, Topic, "deterministic_topic"),
            (self.deterministic_topic_confidence, TopicConfidence, "deterministic_topic_confidence"),
            (self.deterministic_format, EditorialFormat, "deterministic_format"),
            (self.deterministic_format_confidence, EditorialFormatConfidence, "deterministic_format_confidence"),
            (self.deterministic_reader_intent, ReaderIntent, "deterministic_reader_intent"),
            (self.deterministic_reader_intent_confidence, ReaderIntentConfidence, "deterministic_reader_intent_confidence"),
            (self.scope, AdjudicationScope, "scope"),
            (self.provider_status, EditorialResolverProviderStatus, "provider_status"),
        )
        for value, expected, name in typed:
            if not isinstance(value, expected):
                raise ValueError(f"{name} has an invalid value")
        if not isinstance(self.deterministic_topic_ambiguity, bool) or not isinstance(self.deterministic_format_ambiguity, bool):
            raise ValueError("deterministic ambiguity values must be booleans")
        if self.validated_adjudication_response is not None and not isinstance(
            self.validated_adjudication_response, SemanticAdjudicationResponse
        ):
            raise ValueError("validated_adjudication_response must be a domain response or None")
        if not isinstance(self.legal_topic_candidates, tuple) or any(
            not isinstance(item, Topic) for item in self.legal_topic_candidates
        ):
            raise ValueError("legal_topic_candidates must be a tuple of Topic")
        if not isinstance(self.legal_format_candidates, tuple) or any(
            not isinstance(item, EditorialFormat) for item in self.legal_format_candidates
        ):
            raise ValueError("legal_format_candidates must be a tuple of EditorialFormat")
        if len(self.legal_topic_candidates) != len(set(self.legal_topic_candidates)) or len(
            self.legal_format_candidates
        ) != len(set(self.legal_format_candidates)):
            raise ValueError("legal candidate universes must not contain duplicates")
        if self.expected_input_fingerprint is not None and (
            not isinstance(self.expected_input_fingerprint, str)
            or not self.expected_input_fingerprint
            or self.expected_input_fingerprint != self.expected_input_fingerprint.strip()
        ):
            raise ValueError("expected_input_fingerprint must be normalized or None")
        if self.format_v2_trust_signal is not None and not isinstance(
            self.format_v2_trust_signal, EditorialFormatV2TrustSignal
        ):
            raise ValueError("format_v2_trust_signal has an invalid value")


class LimitedEditorialResolver:
    """Resolve authority from completed domain results without side effects."""

    _PROVIDER_WARNINGS = {
        EditorialResolverProviderStatus.UNAVAILABLE: EditorialResolutionWarning.PROVIDER_UNAVAILABLE,
        EditorialResolverProviderStatus.CONFIGURATION_ERROR: EditorialResolutionWarning.PROVIDER_CONFIGURATION_ERROR,
        EditorialResolverProviderStatus.AUTHENTICATION_ERROR: EditorialResolutionWarning.PROVIDER_AUTHENTICATION_ERROR,
        EditorialResolverProviderStatus.PERMISSION_ERROR: EditorialResolutionWarning.PROVIDER_PERMISSION_ERROR,
        EditorialResolverProviderStatus.RATE_LIMITED: EditorialResolutionWarning.PROVIDER_RATE_LIMITED,
        EditorialResolverProviderStatus.TIMEOUT: EditorialResolutionWarning.PROVIDER_TIMEOUT,
        EditorialResolverProviderStatus.INVALID_RESPONSE: EditorialResolutionWarning.INVALID_ADJUDICATION_RESPONSE,
        EditorialResolverProviderStatus.INCOMPLETE_RESPONSE: EditorialResolutionWarning.INCOMPLETE_ADJUDICATION_RESPONSE,
    }

    def resolve(self, inputs: LimitedEditorialResolverInput) -> EditorialResolutionResult:
        """Return one deterministic resolution from already-completed inputs."""
        if not isinstance(inputs, LimitedEditorialResolverInput):
            raise ValueError("inputs must be a LimitedEditorialResolverInput")
        topic_requested = inputs.scope in {
            AdjudicationScope.TOPIC_REQUIRED,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        }
        format_requested = inputs.scope in {
            AdjudicationScope.FORMAT_REQUIRED,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        }
        topic = self._topic(inputs, topic_requested)
        editorial_format = self._format(inputs, format_requested)
        reader_intent = EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.READER_INTENT,
            value=inputs.deterministic_reader_intent,
            status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
            source=EditorialResolutionSource.DETERMINISTIC_V1,
            confidence=inputs.deterministic_reader_intent_confidence.value,
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            ambiguity=False,
            review_required=False,
            warnings=(),
        )
        warnings = self._ordered_warnings(topic.warnings + editorial_format.warnings)
        return EditorialResolutionResult(
            deterministic_topic=inputs.deterministic_topic,
            topic_resolution=topic,
            format_resolution=editorial_format,
            reader_intent_resolution=reader_intent,
            review_required=topic.review_required or editorial_format.review_required,
            warnings=warnings,
            provider_used=(
                topic.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
                or editorial_format.status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
            ),
            input_fingerprint=inputs.expected_input_fingerprint,
        )

    def _topic(
        self, inputs: LimitedEditorialResolverInput, requested: bool,
    ) -> EditorialDimensionResolution[Topic]:
        if not requested:
            return self._deterministic_topic(inputs)
        failure = self._trust_failure(inputs, "topic")
        if failure is not None:
            return self._fallback_topic(inputs, (failure,))
        response = inputs.validated_adjudication_response
        assert response is not None
        try:
            value = Topic(response.adjudicated_topic)
        except (ValueError, TypeError):
            return self._fallback_topic(
                inputs, (EditorialResolutionWarning.ILLEGAL_ADJUDICATED_CANDIDATE,),
            )
        if value not in inputs.legal_topic_candidates:
            return self._fallback_topic(
                inputs, (EditorialResolutionWarning.ILLEGAL_ADJUDICATED_CANDIDATE,),
            )
        warnings = (
            (EditorialResolutionWarning.ADJUDICATION_AMBIGUITY_REMAINS,)
            if response.ambiguity_remaining else ()
        )
        return EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.TOPIC,
            value=value,
            status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
            source=EditorialResolutionSource.ADJUDICATION,
            confidence=response.topic_confidence.value,
            confidence_source=EditorialResolutionSource.ADJUDICATION,
            ambiguity=response.ambiguity_remaining,
            review_required=response.ambiguity_remaining,
            warnings=warnings,
        )

    def _format(
        self, inputs: LimitedEditorialResolverInput, requested: bool,
    ) -> EditorialDimensionResolution[EditorialFormat]:
        if not requested:
            warnings: list[EditorialResolutionWarning] = []
            review = inputs.deterministic_format_ambiguity
            signal = inputs.format_v2_trust_signal
            if signal is not None:
                if signal.selected_format is not inputs.deterministic_format:
                    warnings.append(EditorialResolutionWarning.FORMAT_V1_V2_DISAGREEMENT)
                    review = True
                if (
                    signal.completeness is not EditorialFormatCompleteness.COMPLETE
                    or signal.ambiguity is not EditorialFormatAmbiguity.CLEAR
                    or signal.material_competition
                    or signal.contradiction
                ):
                    warnings.append(EditorialResolutionWarning.FORMAT_STRUCTURE_INCOMPLETE)
                    review = True
            return EditorialDimensionResolution(
                dimension=EditorialResolutionDimension.FORMAT,
                value=inputs.deterministic_format,
                status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
                source=EditorialResolutionSource.DETERMINISTIC_V1,
                confidence=inputs.deterministic_format_confidence.value,
                confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
                ambiguity=inputs.deterministic_format_ambiguity,
                review_required=review,
                warnings=self._ordered_warnings(tuple(warnings)),
            )
        failure = self._trust_failure(inputs, "format")
        if failure is not None:
            return self._fallback_format(inputs, (failure,))
        response = inputs.validated_adjudication_response
        assert response is not None
        try:
            value = EditorialFormat(response.adjudicated_format)
        except (ValueError, TypeError):
            return self._fallback_format(
                inputs, (EditorialResolutionWarning.ILLEGAL_ADJUDICATED_CANDIDATE,),
            )
        if value not in inputs.legal_format_candidates:
            return self._fallback_format(
                inputs, (EditorialResolutionWarning.ILLEGAL_ADJUDICATED_CANDIDATE,),
            )
        warnings = (
            (EditorialResolutionWarning.ADJUDICATION_AMBIGUITY_REMAINS,)
            if response.ambiguity_remaining else ()
        )
        return EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.FORMAT,
            value=value,
            status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
            source=EditorialResolutionSource.ADJUDICATION,
            confidence=response.format_confidence.value,
            confidence_source=EditorialResolutionSource.ADJUDICATION,
            ambiguity=response.ambiguity_remaining,
            review_required=response.ambiguity_remaining,
            warnings=warnings,
        )

    def _trust_failure(
        self, inputs: LimitedEditorialResolverInput, dimension: str,
    ) -> EditorialResolutionWarning | None:
        if inputs.provider_status is not EditorialResolverProviderStatus.SUCCESS:
            return self._PROVIDER_WARNINGS.get(
                inputs.provider_status,
                EditorialResolutionWarning.INVALID_ADJUDICATION_RESPONSE,
            )
        response = inputs.validated_adjudication_response
        if response is None:
            return EditorialResolutionWarning.INVALID_ADJUDICATION_RESPONSE
        if (
            inputs.expected_input_fingerprint is not None
            and response.input_fingerprint != inputs.expected_input_fingerprint
        ):
            return EditorialResolutionWarning.FINGERPRINT_MISMATCH
        selected = response.adjudicated_topic if dimension == "topic" else response.adjudicated_format
        if not isinstance(selected, str) or not selected.strip():
            return EditorialResolutionWarning.INVALID_ADJUDICATION_RESPONSE
        return None

    @staticmethod
    def _deterministic_topic(
        inputs: LimitedEditorialResolverInput,
    ) -> EditorialDimensionResolution[Topic]:
        return EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.TOPIC,
            value=inputs.deterministic_topic,
            status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
            source=EditorialResolutionSource.DETERMINISTIC_V1,
            confidence=inputs.deterministic_topic_confidence.value,
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            ambiguity=inputs.deterministic_topic_ambiguity,
            review_required=False,
            warnings=(),
        )

    def _fallback_topic(
        self,
        inputs: LimitedEditorialResolverInput,
        warnings: tuple[EditorialResolutionWarning, ...],
    ) -> EditorialDimensionResolution[Topic]:
        return EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.TOPIC,
            value=inputs.deterministic_topic,
            status=EditorialResolutionStatus.FALLBACK_ACCEPTED,
            source=EditorialResolutionSource.FALLBACK,
            confidence=inputs.deterministic_topic_confidence.value,
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            ambiguity=inputs.deterministic_topic_ambiguity,
            review_required=True,
            warnings=self._ordered_warnings(warnings),
        )

    def _fallback_format(
        self,
        inputs: LimitedEditorialResolverInput,
        warnings: tuple[EditorialResolutionWarning, ...],
    ) -> EditorialDimensionResolution[EditorialFormat]:
        return EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.FORMAT,
            value=inputs.deterministic_format,
            status=EditorialResolutionStatus.FALLBACK_ACCEPTED,
            source=EditorialResolutionSource.FALLBACK,
            confidence=inputs.deterministic_format_confidence.value,
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            ambiguity=inputs.deterministic_format_ambiguity,
            review_required=True,
            warnings=self._ordered_warnings(
                warnings + (EditorialResolutionWarning.FORMAT_FALLBACK_USED,)
            ),
        )

    @staticmethod
    def _ordered_warnings(
        warnings: tuple[EditorialResolutionWarning, ...],
    ) -> tuple[EditorialResolutionWarning, ...]:
        present = set(warnings)
        return tuple(item for item in EditorialResolutionWarning if item in present)
