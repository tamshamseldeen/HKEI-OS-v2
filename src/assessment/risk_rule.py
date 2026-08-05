"""Immutable deterministic risk rule model."""

from dataclasses import dataclass

from .risk_level import RiskLevel


@dataclass(frozen=True)
class RiskRule:
    """Represent a deterministic editorial risk rule.

    Attributes:
        code: Stable rule identifier.
        topics: Editorial risk topics associated with the rule.
        keywords: Terms that cause the rule to match.
        risk_level: Risk level assigned by the rule.
        warnings: Machine-readable warnings assigned by the rule.
        requires_official_source: Whether the rule requires an official source.
        requires_human_review: Whether the rule requires human review.
    """

    code: str
    topics: tuple[str, ...]
    keywords: tuple[str, ...]
    risk_level: RiskLevel
    warnings: tuple[str, ...]
    requires_official_source: bool
    requires_human_review: bool
