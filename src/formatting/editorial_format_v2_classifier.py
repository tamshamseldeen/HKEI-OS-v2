"""Shadow-only deterministic selection for Editorial Format V2."""

from src.intake.normalized_source import NormalizedSource
from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength

from .editorial_format import EditorialFormat
from .editorial_format_ambiguity import EditorialFormatAmbiguity
from .editorial_format_candidate_assessment import (
    EditorialFormatCandidateAssessment,
)
from .editorial_format_completeness import EditorialFormatCompleteness
from .editorial_format_confidence import EditorialFormatConfidence
from .editorial_format_profile_evaluator import EditorialFormatProfileEvaluator
from .editorial_format_v2_result import EditorialFormatV2Result
from .editorial_treatment_feature_extractor import EditorialTreatmentFeatureExtractor
from .editorial_treatment_feature_result import EditorialTreatmentFeatureResult


class EditorialFormatV2Classifier:
    """Compose V2 stages and select a shadow result without production authority.

    Exact semantic ties use the candidate's stable string value only to populate
    the required ``selected_format`` field. Such a label is not treated as a
    semantic winner: ambiguity remains COMPETING and confidence remains LOW.
    When every profile is incomplete, the same stable placeholder policy is used
    with INSUFFICIENT_EVIDENCE. STANDARD_NEWS is therefore never an absence
    fallback.
    """

    _COMPLETENESS = {
        EditorialFormatCompleteness.INCOMPLETE: 0,
        EditorialFormatCompleteness.PARTIAL: 1,
        EditorialFormatCompleteness.COMPLETE: 2,
    }
    _STRENGTH = {
        SemanticEvidenceStrength.WEAK: 0,
        SemanticEvidenceStrength.MODERATE: 1,
        SemanticEvidenceStrength.STRONG: 2,
    }
    _AMBIGUITY = {
        EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE: 0,
        EditorialFormatAmbiguity.CONTRADICTORY: 1,
        EditorialFormatAmbiguity.COMPETING: 2,
        EditorialFormatAmbiguity.CLEAR: 3,
    }

    def __init__(
        self,
        *,
        feature_extractor: EditorialTreatmentFeatureExtractor | None = None,
        profile_evaluator: EditorialFormatProfileEvaluator | None = None,
    ) -> None:
        self._feature_extractor = (
            feature_extractor or EditorialTreatmentFeatureExtractor()
        )
        self._profile_evaluator = (
            profile_evaluator or EditorialFormatProfileEvaluator()
        )

    def classify(
        self, *, source: NormalizedSource, lead: str | None = None,
    ) -> EditorialFormatV2Result:
        """Run raw document structure through all shadow-only V2 stages."""
        features = self._feature_extractor.extract(source=source, lead=lead)
        return self.classify_features(features)

    def classify_features(
        self, treatment_features: EditorialTreatmentFeatureResult,
    ) -> EditorialFormatV2Result:
        """Select from explicitly supplied treatment features without inference IO."""
        if not isinstance(treatment_features, EditorialTreatmentFeatureResult):
            raise ValueError(
                "treatment_features must be an EditorialTreatmentFeatureResult"
            )
        assessments = self._profile_evaluator.evaluate(treatment_features)
        viable = tuple(
            item for item in assessments
            if item.completeness is not EditorialFormatCompleteness.INCOMPLETE
        )
        warnings: list[str] = list(treatment_features.warnings)

        if not viable:
            selected = min(assessments, key=lambda item: item.candidate.value)
            ambiguity = EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE
            confidence = EditorialFormatConfidence.LOW
            warnings.extend((
                "NO_COMPLETE_PROFILE",
                "NO_VIABLE_PROFILE",
                "DETERMINISTIC_PLACEHOLDER_SELECTED",
            ))
        else:
            semantic_keys = {
                item.candidate: self._semantic_key(item, treatment_features)
                for item in viable
            }
            best_key = max(semantic_keys.values())
            tied = tuple(
                item for item in viable
                if semantic_keys[item.candidate] == best_key
            )
            selected = min(tied, key=lambda item: item.candidate.value)
            ambiguity = self._final_ambiguity(
                selected=selected, tied=tied, viable=viable,
            )
            if len(tied) > 1:
                warnings.extend((
                    "LOW_STRUCTURAL_SEPARATION",
                    "DETERMINISTIC_TIE_BREAK_APPLIED",
                ))
            if sum(
                item.completeness is EditorialFormatCompleteness.COMPLETE
                for item in viable
            ) > 1:
                warnings.append("MULTIPLE_COMPLETE_CANDIDATES")
            if not any(
                item.completeness is EditorialFormatCompleteness.COMPLETE
                for item in viable
            ):
                warnings.append("NO_COMPLETE_PROFILE")
            if selected.completeness is EditorialFormatCompleteness.PARTIAL:
                warnings.append("SELECTED_PARTIAL_PROFILE")
            if ambiguity is EditorialFormatAmbiguity.CONTRADICTORY:
                warnings.append("CONTRADICTORY_SELECTED_PROFILE")
            if ambiguity is EditorialFormatAmbiguity.COMPETING:
                warnings.append("MULTIPLE_VIABLE_CANDIDATES")
            confidence = self._confidence(
                selected=selected, ambiguity=ambiguity, exact_tie=len(tied) > 1,
            )

        warnings.extend(selected.warnings)
        return EditorialFormatV2Result(
            selected_format=selected.candidate,
            confidence=confidence,
            ambiguity=ambiguity,
            candidate_assessments=assessments,
            treatment_features=treatment_features,
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _semantic_key(
        self,
        assessment: EditorialFormatCandidateAssessment,
        features: EditorialTreatmentFeatureResult,
    ) -> tuple[int, int, int, int, int, int]:
        """Return a transparent non-probabilistic comparison key."""
        return (
            self._COMPLETENESS[assessment.completeness],
            int(assessment.ambiguity is not EditorialFormatAmbiguity.CONTRADICTORY),
            self._STRENGTH[assessment.strength],
            self._AMBIGUITY[assessment.ambiguity],
            -len(assessment.disqualifying_features),
            self._profile_quality(assessment, features),
        )

    @staticmethod
    def _profile_quality(
        assessment: EditorialFormatCandidateAssessment,
        features: EditorialTreatmentFeatureResult,
    ) -> int:
        """Count structural section coverage, not raw lexical occurrences."""
        quality = 0
        for feature in assessment.supporting_features:
            quality += sum(
                feature in section for section in (
                    features.headline_features, features.lead_features,
                    features.body_features,
                )
            )
            if feature in features.cross_section_features:
                quality += 2
        return quality

    @staticmethod
    def _final_ambiguity(
        *, selected: EditorialFormatCandidateAssessment,
        tied: tuple[EditorialFormatCandidateAssessment, ...],
        viable: tuple[EditorialFormatCandidateAssessment, ...],
    ) -> EditorialFormatAmbiguity:
        if selected.ambiguity is EditorialFormatAmbiguity.CONTRADICTORY:
            return EditorialFormatAmbiguity.CONTRADICTORY
        if len(tied) > 1:
            return EditorialFormatAmbiguity.COMPETING
        if selected.ambiguity is EditorialFormatAmbiguity.COMPETING:
            return EditorialFormatAmbiguity.COMPETING
        if any(
            item.candidate in selected.competing_candidates
            and item.completeness is not EditorialFormatCompleteness.INCOMPLETE
            for item in viable
            if item is not selected
        ):
            return EditorialFormatAmbiguity.COMPETING
        return EditorialFormatAmbiguity.CLEAR

    @staticmethod
    def _confidence(
        *, selected: EditorialFormatCandidateAssessment,
        ambiguity: EditorialFormatAmbiguity,
        exact_tie: bool,
    ) -> EditorialFormatConfidence:
        if ambiguity in {
            EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE,
            EditorialFormatAmbiguity.CONTRADICTORY,
        } or exact_tie:
            return EditorialFormatConfidence.LOW
        if (
            selected.completeness is EditorialFormatCompleteness.COMPLETE
            and selected.strength is SemanticEvidenceStrength.STRONG
            and ambiguity is EditorialFormatAmbiguity.CLEAR
            and not selected.disqualifying_features
        ):
            return EditorialFormatConfidence.HIGH
        if selected.completeness in {
            EditorialFormatCompleteness.COMPLETE,
            EditorialFormatCompleteness.PARTIAL,
        }:
            return EditorialFormatConfidence.MEDIUM
        return EditorialFormatConfidence.LOW
