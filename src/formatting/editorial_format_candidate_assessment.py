"""Immutable assessment of one Editorial Format V2 candidate profile."""

from dataclasses import dataclass

from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength

from .editorial_format import EditorialFormat
from .editorial_format_ambiguity import EditorialFormatAmbiguity
from .editorial_format_completeness import EditorialFormatCompleteness
from .editorial_treatment_feature import EditorialTreatmentFeature


@dataclass(frozen=True)
class EditorialFormatCandidateAssessment:
    """Store caller-supplied profile evidence without making a decision."""

    candidate: EditorialFormat
    completeness: EditorialFormatCompleteness
    strength: SemanticEvidenceStrength
    supporting_features: tuple[EditorialTreatmentFeature, ...]
    missing_required_features: tuple[EditorialTreatmentFeature, ...]
    disqualifying_features: tuple[EditorialTreatmentFeature, ...]
    competing_candidates: tuple[EditorialFormat, ...]
    ambiguity: EditorialFormatAmbiguity
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, EditorialFormat):
            raise ValueError("candidate must be an EditorialFormat")
        if not isinstance(self.completeness, EditorialFormatCompleteness):
            raise ValueError("completeness must be an EditorialFormatCompleteness")
        if not isinstance(self.strength, SemanticEvidenceStrength):
            raise ValueError("strength must be a SemanticEvidenceStrength")
        if not isinstance(self.ambiguity, EditorialFormatAmbiguity):
            raise ValueError("ambiguity must be an EditorialFormatAmbiguity")
        for name in (
            "supporting_features", "missing_required_features",
            "disqualifying_features",
        ):
            self._require_enum_tuple(
                name, getattr(self, name), EditorialTreatmentFeature,
            )
        self._require_enum_tuple(
            "competing_candidates", self.competing_candidates, EditorialFormat,
        )
        self._require_warning_tuple(self.warnings)
        if self.candidate in self.competing_candidates:
            raise ValueError("candidate must not compete with itself")

    @staticmethod
    def _require_enum_tuple(name: str, value: object, member_type: type) -> None:
        if not isinstance(value, tuple):
            raise ValueError(f"{name} must be a tuple")
        if any(not isinstance(item, member_type) for item in value):
            raise ValueError(f"{name} contains an invalid member")
        if len(value) != len(set(value)):
            raise ValueError(f"{name} must not contain duplicates")

    @staticmethod
    def _require_warning_tuple(value: object) -> None:
        if not isinstance(value, tuple):
            raise ValueError("warnings must be a tuple")
        if any(
            not isinstance(item, str) or not item or item != item.strip()
            for item in value
        ):
            raise ValueError("warnings contains an invalid member")
        if len(value) != len(set(value)):
            raise ValueError("warnings must not contain duplicates")
