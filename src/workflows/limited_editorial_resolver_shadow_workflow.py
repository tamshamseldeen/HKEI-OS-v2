"""Full-stack non-authoritative orchestration for the limited Resolver."""

from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_v2_classifier import EditorialFormatV2Classifier
from src.resolution.limited_editorial_resolver import (
    EditorialFormatV2TrustSignal,
    EditorialResolverProviderStatus,
    LimitedEditorialResolver,
    LimitedEditorialResolverInput,
)
from src.topic.topic import Topic
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)

from .limited_editorial_resolver_shadow_result import LimitedEditorialResolverShadowResult


class LimitedEditorialResolverShadowWorkflow:
    """Observe end-to-end Resolver output without mutating production results."""

    _ERROR_STATUS = {
        "SemanticAdjudicationProviderConfigurationError": EditorialResolverProviderStatus.CONFIGURATION_ERROR,
        "SemanticAdjudicationProviderUnavailableError": EditorialResolverProviderStatus.UNAVAILABLE,
        "SemanticAdjudicationProviderTimeoutError": EditorialResolverProviderStatus.TIMEOUT,
        "SemanticAdjudicationProviderInvalidResponseError": EditorialResolverProviderStatus.INVALID_RESPONSE,
        "SemanticAdjudicationProviderRateLimitError": EditorialResolverProviderStatus.RATE_LIMITED,
    }

    def __init__(
        self,
        *,
        provider: SemanticAdjudicationProvider,
        adjudication_workflow: ExperimentalSemanticAdjudicationShadowWorkflow | None = None,
        resolver: LimitedEditorialResolver | None = None,
        format_v2_classifier: EditorialFormatV2Classifier | None = None,
    ) -> None:
        self.adjudication_workflow = adjudication_workflow or ExperimentalSemanticAdjudicationShadowWorkflow(
            provider=provider
        )
        self.resolver = resolver or LimitedEditorialResolver()
        self.format_v2_classifier = format_v2_classifier or EditorialFormatV2Classifier()

    def analyze(self, **article_fields) -> LimitedEditorialResolverShadowResult:
        """Run existing shadow stages and resolve their completed domain outputs."""
        shadow = self.adjudication_workflow.analyze(**article_fields)
        editorial = shadow.editorial_result
        source = editorial.classification_result.ingestion.source
        format_v2 = self.format_v2_classifier.classify(source=source)
        selected = next(
            item for item in format_v2.candidate_assessments
            if item.candidate is format_v2.selected_format
        )
        trust_signal = EditorialFormatV2TrustSignal(
            selected_format=format_v2.selected_format,
            confidence=format_v2.confidence,
            ambiguity=format_v2.ambiguity,
            completeness=selected.completeness,
            material_competition=bool(selected.competing_candidates),
            contradiction=bool(selected.disqualifying_features),
        )
        request = shadow.request
        if shadow.validated_response is not None:
            provider_status = EditorialResolverProviderStatus.SUCCESS
        elif not shadow.provider_called:
            provider_status = EditorialResolverProviderStatus.NOT_CALLED
        else:
            provider_status = self._ERROR_STATUS.get(
                shadow.provider_error or "",
                EditorialResolverProviderStatus.INVALID_RESPONSE,
            )
        resolution = self.resolver.resolve(LimitedEditorialResolverInput(
            deterministic_topic=editorial.topic_classification.topic,
            deterministic_topic_confidence=editorial.topic_classification.confidence,
            deterministic_topic_ambiguity=False,
            deterministic_format=editorial.format_classification.editorial_format,
            deterministic_format_confidence=editorial.format_classification.confidence,
            deterministic_format_ambiguity=False,
            deterministic_reader_intent=editorial.reader_intent_classification.reader_intent,
            deterministic_reader_intent_confidence=editorial.reader_intent_classification.confidence,
            scope=shadow.adjudication_decision.scope,
            provider_status=provider_status,
            validated_adjudication_response=shadow.validated_response,
            legal_topic_candidates=(
                tuple(Topic(value) for value in request.candidate_topics)
                if request is not None else (editorial.topic_classification.topic,)
            ),
            legal_format_candidates=(
                tuple(EditorialFormat(value) for value in request.candidate_formats)
                if request is not None else (editorial.format_classification.editorial_format,)
            ),
            expected_input_fingerprint=request.input_fingerprint if request is not None else None,
            format_v2_trust_signal=trust_signal,
        ))
        topic_mutated = editorial.topic_classification.topic is not editorial.topic_classification.topic
        format_mutated = editorial.format_classification.editorial_format is not editorial.format_classification.editorial_format
        intent_mutated = editorial.reader_intent_classification.reader_intent is not editorial.reader_intent_classification.reader_intent
        return LimitedEditorialResolverShadowResult(
            editorial_result=editorial,
            format_v2_result=format_v2,
            adjudication_decision=shadow.adjudication_decision,
            request=request,
            validated_response=shadow.validated_response,
            resolution_result=resolution,
            provider_called=shadow.provider_called,
            response_valid=shadow.response_valid,
            topic_mutated=topic_mutated,
            format_mutated=format_mutated,
            reader_intent_mutated=intent_mutated,
            gate_mutated=False,
            format_v2_mutated=False,
            diagnostic_warnings=tuple(resolution_warning.value for resolution_warning in resolution.warnings),
        )
