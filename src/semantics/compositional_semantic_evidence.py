"""Immutable collection of compositional semantic evidence."""

from dataclasses import dataclass

from .semantic_relationship import SemanticRelationship


@dataclass(frozen=True)
class CompositionalSemanticEvidence:
    """Store semantic relationships and classification-independent candidates.

    Attributes:
        relationships: Ordered semantic relationships.
        primary_domain_candidates: Ordered primary-domain candidate labels.
        secondary_domain_candidates: Ordered secondary-domain candidate labels.
        format_support: Ordered format support labels.
        format_suppression: Ordered format suppression labels.
        intent_support: Ordered reader-intent support labels.
        warnings: Ordered semantic evidence warnings.
    """

    relationships: tuple[SemanticRelationship, ...]
    primary_domain_candidates: tuple[str, ...]
    secondary_domain_candidates: tuple[str, ...]
    format_support: tuple[str, ...]
    format_suppression: tuple[str, ...]
    intent_support: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def all_supports(self) -> tuple[str, ...]:
        """Return every support in required order without deduplication."""
        relationship_supports = tuple(
            support
            for relationship in self.relationships
            for support in relationship.supports
        )
        return (
            relationship_supports
            + self.primary_domain_candidates
            + self.secondary_domain_candidates
            + self.format_support
            + self.intent_support
        )

    @property
    def all_suppressions(self) -> tuple[str, ...]:
        """Return every suppression in required order without deduplication."""
        relationship_suppressions = tuple(
            suppression
            for relationship in self.relationships
            for suppression in relationship.suppresses
        )
        return relationship_suppressions + self.format_suppression
