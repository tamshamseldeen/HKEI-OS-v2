"""Provider-neutral semantic adjudication orchestration in shadow mode."""

from hashlib import sha256
import json

from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_provider import (
    SemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderError,
    SemanticAdjudicationProviderInvalidResponseError,
)
from src.adjudication.semantic_adjudication_request_builder import (
    SemanticAdjudicationRequestBuilder,
)
from src.adjudication.semantic_adjudication_response_validator import (
    SemanticAdjudicationResponseValidator,
)
from src.intake.normalized_source import NormalizedSource

from .experimental_semantic_adjudication_shadow_result import (
    ExperimentalSemanticAdjudicationShadowResult,
)
from .experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


class ExperimentalSemanticAdjudicationShadowWorkflow:
    """Observe provider recommendations without resolving editorial outputs."""

    def __init__(
        self,
        *,
        provider: SemanticAdjudicationProvider,
        editorial_workflow: ExperimentalSemanticEditorialAnalysisWorkflow | None = None,
        adjudication_gate: DeterministicSemanticAdjudicationGate | None = None,
        request_builder: SemanticAdjudicationRequestBuilder | None = None,
        response_validator: SemanticAdjudicationResponseValidator | None = None,
    ) -> None:
        self.editorial_workflow = (
            editorial_workflow
            if editorial_workflow is not None
            else ExperimentalSemanticEditorialAnalysisWorkflow()
        )
        self.adjudication_gate = (
            adjudication_gate
            if adjudication_gate is not None
            else DeterministicSemanticAdjudicationGate()
        )
        self.request_builder = (
            request_builder
            if request_builder is not None
            else SemanticAdjudicationRequestBuilder()
        )
        self.provider = provider
        self.response_validator = (
            response_validator
            if response_validator is not None
            else SemanticAdjudicationResponseValidator()
        )

    def analyze(
        self,
        *,
        title: str | None,
        body: str | None,
        source_name: str | None,
        source_url: str | None = None,
        published_at: str | None = None,
        language: str | None = None,
        country: str | None = None,
        author: str | None = None,
        images: tuple[str, ...] = (),
        attachments: tuple[str, ...] = (),
        category: str | None = None,
        tags: tuple[str, ...] = (),
        user_instruction: str | None = None,
    ) -> ExperimentalSemanticAdjudicationShadowResult:
        """Run the gate and optional provider while retaining deterministic state."""
        editorial_result = self.editorial_workflow.process(
            title=title,
            body=body,
            source_name=source_name,
            source_url=source_url,
            published_at=published_at,
            language=language,
            country=country,
            author=author,
            images=images,
            attachments=attachments,
            category=category,
            tags=tags,
            user_instruction=user_instruction,
        )
        decision = self.adjudication_gate.evaluate(
            topic_classification=editorial_result.topic_classification,
            format_classification=editorial_result.format_classification,
            contextual_evidence=editorial_result.contextual_evidence,
            semantic_evidence=editorial_result.semantic_evidence,
        )
        if decision.scope is AdjudicationScope.NOT_REQUIRED:
            return ExperimentalSemanticAdjudicationShadowResult(
                editorial_result=editorial_result,
                adjudication_decision=decision,
                request=None,
                provider_response=None,
                validated_response=None,
                provider_called=False,
                response_valid=False,
                provider_error=None,
            )

        source = editorial_result.classification_result.ingestion.source
        request = self.request_builder.build(
            request_id=self._request_id(source),
            source=source,
            content_classification=(
                editorial_result.classification_result.classification
            ),
            topic_classification=editorial_result.topic_classification,
            format_classification=editorial_result.format_classification,
            contextual_evidence=editorial_result.contextual_evidence,
            semantic_evidence=editorial_result.semantic_evidence,
            decision=decision,
        )
        try:
            provider_response = self.provider.adjudicate(request)
        except SemanticAdjudicationProviderError as error:
            return ExperimentalSemanticAdjudicationShadowResult(
                editorial_result=editorial_result,
                adjudication_decision=decision,
                request=request,
                provider_response=None,
                validated_response=None,
                provider_called=True,
                response_valid=False,
                provider_error=type(error).__name__,
            )

        try:
            validated_response = self.response_validator.validate(
                request=request,
                response=provider_response,
            )
        except SemanticAdjudicationProviderInvalidResponseError as error:
            return ExperimentalSemanticAdjudicationShadowResult(
                editorial_result=editorial_result,
                adjudication_decision=decision,
                request=request,
                provider_response=provider_response,
                validated_response=None,
                provider_called=True,
                response_valid=False,
                provider_error=str(error),
            )
        return ExperimentalSemanticAdjudicationShadowResult(
            editorial_result=editorial_result,
            adjudication_decision=decision,
            request=request,
            provider_response=provider_response,
            validated_response=validated_response,
            provider_called=True,
            response_valid=True,
            provider_error=None,
        )

    @staticmethod
    def _request_id(source: NormalizedSource) -> str:
        identity = (
            {"source_url": source.source_url.strip()}
            if source.source_url and source.source_url.strip()
            else {
                "title": source.title,
                "body": source.body,
                "source_name": source.source_name,
                "published_at": source.published_at,
                "language": source.language,
                "country": source.country,
                "author": source.author,
            }
        )
        serialized = json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"semantic-adjudication-{sha256(serialized.encode('utf-8')).hexdigest()}"
