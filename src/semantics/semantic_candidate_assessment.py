"""Immutable candidate-relative semantic assessment model."""

from dataclasses import dataclass

from .semantic_evidence_direction import SemanticEvidenceDirection
from .semantic_evidence_strength import SemanticEvidenceStrength
from .semantic_evidence_sufficiency import SemanticEvidenceSufficiency


@dataclass(frozen=True)
class SemanticCandidateAssessment:
    """Store symbolic direction, strength, sufficiency, and provenance.

    Supplied tuples remain ordered and are never silently normalized. Duplicate
    values are rejected because repeated symbolic provenance must be resolved by
    the future assessment algorithm before this domain model is constructed.
    """

    candidate: str
    direction: SemanticEvidenceDirection
    strength: SemanticEvidenceStrength
    sufficiency: SemanticEvidenceSufficiency
    supporting_relationship_types: tuple[str, ...]
    suppressing_relationship_types: tuple[str, ...]
    role_basis: tuple[str, ...]
    competing_candidates: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        self._require_symbol("candidate", self.candidate)
        if not isinstance(self.direction, SemanticEvidenceDirection):
            raise ValueError("direction must be a SemanticEvidenceDirection")
        if not isinstance(self.strength, SemanticEvidenceStrength):
            raise ValueError("strength must be a SemanticEvidenceStrength")
        if not isinstance(self.sufficiency, SemanticEvidenceSufficiency):
            raise ValueError("sufficiency must be a SemanticEvidenceSufficiency")
        for name in (
            "supporting_relationship_types",
            "suppressing_relationship_types",
            "role_basis",
            "competing_candidates",
            "warnings",
        ):
            self._require_symbol_tuple(name, getattr(self, name))
        if self.candidate in self.competing_candidates:
            raise ValueError("candidate must not compete with itself")

        conflicting = self.direction is SemanticEvidenceDirection.CONFLICTING
        conflicted = (
            self.sufficiency is SemanticEvidenceSufficiency.CONFLICTED
        )
        if conflicting != conflicted:
            raise ValueError(
                "CONFLICTING direction and CONFLICTED sufficiency must occur together"
            )
        if (
            self.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT
            and self.direction is not SemanticEvidenceDirection.SUPPORT
        ):
            raise ValueError("SUFFICIENT evidence requires SUPPORT direction")
        if (
            self.sufficiency is SemanticEvidenceSufficiency.PARTIAL
            and self.direction not in {
                SemanticEvidenceDirection.SUPPORT,
                SemanticEvidenceDirection.SUPPRESS,
            }
        ):
            raise ValueError("PARTIAL evidence requires SUPPORT or SUPPRESS direction")

    @staticmethod
    def _require_symbol(name: str, value: object) -> None:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
        ):
            raise ValueError(f"{name} must be a non-empty stripped string")

    @classmethod
    def _require_symbol_tuple(cls, name: str, value: object) -> None:
        if not isinstance(value, tuple):
            raise ValueError(f"{name} must be a tuple of strings")
        for item in value:
            cls._require_symbol(f"{name} member", item)
        if len(value) != len(set(value)):
            raise ValueError(f"{name} must not contain duplicates")
