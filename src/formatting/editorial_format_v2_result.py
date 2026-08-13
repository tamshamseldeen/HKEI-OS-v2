"""Immutable provider-neutral Editorial Format V2 result model."""

from dataclasses import dataclass

from .editorial_format import EditorialFormat
from .editorial_format_ambiguity import EditorialFormatAmbiguity
from .editorial_format_candidate_assessment import (
    EditorialFormatCandidateAssessment,
)
from .editorial_format_confidence import EditorialFormatConfidence
from .editorial_treatment_feature_result import EditorialTreatmentFeatureResult


@dataclass(frozen=True)
class EditorialFormatV2Result:
    """Store an explicit caller-selected V2 result without inference behavior."""

    selected_format: EditorialFormat
    confidence: EditorialFormatConfidence
    ambiguity: EditorialFormatAmbiguity
    candidate_assessments: tuple[EditorialFormatCandidateAssessment, ...]
    treatment_features: EditorialTreatmentFeatureResult
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.selected_format, EditorialFormat):
            raise ValueError("selected_format must be an EditorialFormat")
        if not isinstance(self.confidence, EditorialFormatConfidence):
            raise ValueError("confidence must be an EditorialFormatConfidence")
        if not isinstance(self.ambiguity, EditorialFormatAmbiguity):
            raise ValueError("ambiguity must be an EditorialFormatAmbiguity")
        if not isinstance(self.candidate_assessments, tuple):
            raise ValueError("candidate_assessments must be a tuple")
        if any(
            not isinstance(item, EditorialFormatCandidateAssessment)
            for item in self.candidate_assessments
        ):
            raise ValueError("candidate_assessments contains an invalid member")
        candidates = tuple(item.candidate for item in self.candidate_assessments)
        if len(candidates) != len(set(candidates)):
            raise ValueError("candidate_assessments must not repeat candidates")
        if not isinstance(self.treatment_features, EditorialTreatmentFeatureResult):
            raise ValueError("treatment_features must be an EditorialTreatmentFeatureResult")
        if not isinstance(self.warnings, tuple):
            raise ValueError("warnings must be a tuple")
        if any(
            not isinstance(item, str) or not item or item != item.strip()
            for item in self.warnings
        ):
            raise ValueError("warnings contains an invalid member")
        if len(self.warnings) != len(set(self.warnings)):
            raise ValueError("warnings must not contain duplicates")
