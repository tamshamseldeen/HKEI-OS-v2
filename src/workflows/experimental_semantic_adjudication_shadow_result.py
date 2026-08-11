"""Immutable result of experimental semantic adjudication shadow execution."""

from dataclasses import dataclass

from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)

from .experimental_semantic_editorial_analysis_result import (
    ExperimentalSemanticEditorialAnalysisResult,
)


@dataclass(frozen=True)
class ExperimentalSemanticAdjudicationShadowResult:
    """Store deterministic analysis and non-resolving provider observations."""

    editorial_result: ExperimentalSemanticEditorialAnalysisResult
    adjudication_decision: SemanticAdjudicationDecision
    request: SemanticAdjudicationRequest | None
    provider_response: SemanticAdjudicationResponse | None
    validated_response: SemanticAdjudicationResponse | None
    provider_called: bool
    response_valid: bool
    provider_error: str | None
