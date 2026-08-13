"""Immutable non-authoritative full-stack Resolver shadow result."""

from dataclasses import dataclass

from src.adjudication.semantic_adjudication_decision import SemanticAdjudicationDecision
from src.adjudication.semantic_adjudication_request import SemanticAdjudicationRequest
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.formatting.editorial_format_v2_result import EditorialFormatV2Result
from src.resolution.editorial_resolution_result import EditorialResolutionResult

from .experimental_semantic_editorial_analysis_result import ExperimentalSemanticEditorialAnalysisResult


@dataclass(frozen=True)
class LimitedEditorialResolverShadowResult:
    """Expose shadow resolution and safe orchestration diagnostics."""

    editorial_result: ExperimentalSemanticEditorialAnalysisResult
    format_v2_result: EditorialFormatV2Result | None
    adjudication_decision: SemanticAdjudicationDecision
    request: SemanticAdjudicationRequest | None
    validated_response: SemanticAdjudicationResponse | None
    resolution_result: EditorialResolutionResult
    provider_called: bool
    response_valid: bool
    topic_mutated: bool
    format_mutated: bool
    reader_intent_mutated: bool
    gate_mutated: bool
    format_v2_mutated: bool
    diagnostic_warnings: tuple[str, ...]
