"""Immutable policy configuration for the limited Topic authority pilot."""

from dataclasses import dataclass

from src.adjudication.adjudication_confidence import AdjudicationConfidence

from .resolver_authority_mode import ResolverAuthorityMode


@dataclass(frozen=True)
class LimitedTopicAuthorityConfig:
    """Represent pilot policy without enabling authority behavior."""

    authority_mode: ResolverAuthorityMode = ResolverAuthorityMode.SHADOW
    minimum_provider_confidence: AdjudicationConfidence = AdjudicationConfidence.MEDIUM
    block_on_review_required: bool = True
    block_on_ambiguity: bool = True
    regression_budget: int = 0
    minimum_audited_override_sample: int = 30

    def __post_init__(self) -> None:
        if not isinstance(self.authority_mode, ResolverAuthorityMode):
            raise ValueError("authority_mode must be a ResolverAuthorityMode")
        if not isinstance(self.minimum_provider_confidence, AdjudicationConfidence):
            raise ValueError("minimum_provider_confidence must be an AdjudicationConfidence")
        if self.minimum_provider_confidence is AdjudicationConfidence.LOW:
            raise ValueError("LOW minimum provider confidence is prohibited")
        if not isinstance(self.block_on_review_required, bool):
            raise ValueError("block_on_review_required must be a boolean")
        if not isinstance(self.block_on_ambiguity, bool):
            raise ValueError("block_on_ambiguity must be a boolean")
        if isinstance(self.regression_budget, bool) or not isinstance(self.regression_budget, int):
            raise ValueError("regression_budget must be an integer")
        if self.regression_budget < 0:
            raise ValueError("regression_budget must not be negative")
        if (
            isinstance(self.minimum_audited_override_sample, bool)
            or not isinstance(self.minimum_audited_override_sample, int)
            or self.minimum_audited_override_sample < 1
        ):
            raise ValueError("minimum_audited_override_sample must be at least 1")
