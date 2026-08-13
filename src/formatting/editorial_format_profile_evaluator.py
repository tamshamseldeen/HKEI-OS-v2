"""Deterministic profile evaluation for Editorial Format V2 candidates."""

from dataclasses import dataclass

from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength

from .editorial_format import EditorialFormat
from .editorial_format_ambiguity import EditorialFormatAmbiguity
from .editorial_format_candidate_assessment import (
    EditorialFormatCandidateAssessment,
)
from .editorial_format_completeness import EditorialFormatCompleteness
from .editorial_treatment_feature import EditorialTreatmentFeature as Feature
from .editorial_treatment_feature_result import EditorialTreatmentFeatureResult


@dataclass(frozen=True)
class _Profile:
    required: tuple[Feature, ...]
    supporting: tuple[Feature, ...]
    disqualifying: tuple[Feature, ...]
    competitors: tuple[EditorialFormat, ...]


class EditorialFormatProfileEvaluator:
    """Evaluate all profiles independently without selecting a final Format."""

    _PROFILES = {
        EditorialFormat.BREAKING: _Profile(
            required=(Feature.URGENT_BREAKING_SIGNAL, Feature.EVENT_REPORTING),
            supporting=(),
            disqualifying=(Feature.COMPLETED_OUTCOME,),
            competitors=(
                EditorialFormat.STANDARD_NEWS, EditorialFormat.SERVICE,
                EditorialFormat.RESULT_REPORT,
            ),
        ),
        EditorialFormat.STANDARD_NEWS: _Profile(
            required=(Feature.EVENT_REPORTING,),
            supporting=(),
            disqualifying=(
                Feature.URGENT_BREAKING_SIGNAL, Feature.COMPLETED_OUTCOME,
                Feature.TEMPORAL_MOVEMENT, Feature.CAUSAL_EXPLANATION,
                Feature.MECHANISM_EXPLANATION, Feature.ACTIONABLE_GUIDANCE,
                Feature.PROCEDURAL_SERVICE, Feature.CLAIM_VERIFICATION,
            ),
            competitors=(
                EditorialFormat.BREAKING, EditorialFormat.ANALYSIS,
                EditorialFormat.EXPLAINER, EditorialFormat.RESULT_REPORT,
                EditorialFormat.TREND_UPDATE, EditorialFormat.SERVICE,
                EditorialFormat.FEATURE, EditorialFormat.FACT_CHECK,
                EditorialFormat.INTERVIEW, EditorialFormat.PROFILE,
            ),
        ),
        EditorialFormat.SERVICE: _Profile(
            required=(Feature.PROCEDURAL_SERVICE,),
            supporting=(Feature.EVENT_REPORTING,),
            disqualifying=(Feature.CLAIM_VERIFICATION,),
            competitors=(
                EditorialFormat.GUIDE, EditorialFormat.FACT_CHECK,
                EditorialFormat.STANDARD_NEWS, EditorialFormat.BREAKING,
            ),
        ),
        EditorialFormat.GUIDE: _Profile(
            required=(Feature.ACTIONABLE_GUIDANCE,),
            supporting=(
                Feature.LIST_OR_RANKING_STRUCTURE, Feature.COMPARATIVE_STRUCTURE,
                Feature.PROCEDURAL_SERVICE,
            ),
            disqualifying=(Feature.CLAIM_VERIFICATION,),
            competitors=(
                EditorialFormat.SERVICE, EditorialFormat.EXPLAINER,
                EditorialFormat.FEATURE,
            ),
        ),
        EditorialFormat.EXPLAINER: _Profile(
            required=(Feature.MECHANISM_EXPLANATION,),
            supporting=(Feature.COMPARATIVE_STRUCTURE,),
            disqualifying=(Feature.CAUSAL_EXPLANATION,),
            competitors=(
                EditorialFormat.ANALYSIS, EditorialFormat.GUIDE,
                EditorialFormat.STANDARD_NEWS,
            ),
        ),
        EditorialFormat.FEATURE: _Profile(
            required=(Feature.NARRATIVE_SCENE_STRUCTURE,),
            supporting=(
                Feature.COMPARATIVE_STRUCTURE, Feature.OPINION_ARGUMENTATION,
            ),
            disqualifying=(
                Feature.INTERVIEW_QA_STRUCTURE, Feature.BIOGRAPHICAL_ARC,
            ),
            competitors=(
                EditorialFormat.PROFILE, EditorialFormat.INTERVIEW,
                EditorialFormat.ANALYSIS, EditorialFormat.STANDARD_NEWS,
                EditorialFormat.GUIDE,
            ),
        ),
        EditorialFormat.FACT_CHECK: _Profile(
            required=(Feature.CLAIM_VERIFICATION,),
            supporting=(Feature.COMPARATIVE_STRUCTURE,),
            disqualifying=(Feature.PROCEDURAL_SERVICE,),
            competitors=(
                EditorialFormat.STANDARD_NEWS, EditorialFormat.ANALYSIS,
                EditorialFormat.SERVICE,
            ),
        ),
        EditorialFormat.ANALYSIS: _Profile(
            required=(Feature.CAUSAL_EXPLANATION,),
            supporting=(
                Feature.COMPARATIVE_STRUCTURE, Feature.OPINION_ARGUMENTATION,
            ),
            disqualifying=(Feature.MECHANISM_EXPLANATION,),
            competitors=(
                EditorialFormat.EXPLAINER, EditorialFormat.STANDARD_NEWS,
                EditorialFormat.FEATURE, EditorialFormat.FACT_CHECK,
                EditorialFormat.TREND_UPDATE,
            ),
        ),
        EditorialFormat.INTERVIEW: _Profile(
            required=(Feature.INTERVIEW_QA_STRUCTURE,),
            supporting=(Feature.NARRATIVE_SCENE_STRUCTURE,),
            disqualifying=(Feature.BIOGRAPHICAL_ARC,),
            competitors=(
                EditorialFormat.PROFILE, EditorialFormat.FEATURE,
                EditorialFormat.STANDARD_NEWS,
            ),
        ),
        EditorialFormat.PROFILE: _Profile(
            required=(Feature.BIOGRAPHICAL_ARC,),
            supporting=(Feature.NARRATIVE_SCENE_STRUCTURE,),
            disqualifying=(Feature.INTERVIEW_QA_STRUCTURE,),
            competitors=(
                EditorialFormat.FEATURE, EditorialFormat.INTERVIEW,
                EditorialFormat.STANDARD_NEWS,
            ),
        ),
        EditorialFormat.RESULT_REPORT: _Profile(
            required=(Feature.COMPLETED_OUTCOME,),
            supporting=(
                Feature.LIST_OR_RANKING_STRUCTURE, Feature.EVENT_REPORTING,
            ),
            disqualifying=(
                Feature.TEMPORAL_MOVEMENT, Feature.URGENT_BREAKING_SIGNAL,
            ),
            competitors=(
                EditorialFormat.TREND_UPDATE, EditorialFormat.STANDARD_NEWS,
                EditorialFormat.BREAKING,
            ),
        ),
        EditorialFormat.TREND_UPDATE: _Profile(
            required=(Feature.TEMPORAL_MOVEMENT,),
            supporting=(
                Feature.COMPARATIVE_STRUCTURE, Feature.EVENT_REPORTING,
            ),
            disqualifying=(Feature.COMPLETED_OUTCOME,),
            competitors=(
                EditorialFormat.RESULT_REPORT, EditorialFormat.STANDARD_NEWS,
                EditorialFormat.ANALYSIS,
            ),
        ),
    }

    def evaluate(
        self, treatment_features: EditorialTreatmentFeatureResult,
    ) -> tuple[EditorialFormatCandidateAssessment, ...]:
        """Return one assessment per enum value in canonical enum order."""
        if not isinstance(treatment_features, EditorialTreatmentFeatureResult):
            raise ValueError(
                "treatment_features must be an EditorialTreatmentFeatureResult"
            )
        present = set(treatment_features.features)
        structurally_present = {
            candidate: all(feature in present for feature in profile.required)
            for candidate, profile in self._PROFILES.items()
        }
        disqualified = {
            candidate: bool(set(profile.disqualifying) & present)
            for candidate, profile in self._PROFILES.items()
        }
        assessments = []
        for candidate in EditorialFormat:
            profile = self._PROFILES[candidate]
            missing = tuple(
                feature for feature in profile.required if feature not in present
            )
            support = self._ordered_features(
                (set(profile.required) | set(profile.supporting)) & present
            )
            disqualifying = self._ordered_features(
                set(profile.disqualifying) & present
            )
            competitors = tuple(
                other for other in EditorialFormat
                if other in profile.competitors
                and structurally_present[other]
                and (not disqualified[other] or bool(disqualifying))
                and not missing
            )
            completeness, ambiguity, warnings = self._state(
                missing=missing,
                disqualifying=disqualifying,
                competitors=competitors,
            )
            assessments.append(
                EditorialFormatCandidateAssessment(
                    candidate=candidate,
                    completeness=completeness,
                    strength=self._strength(
                        candidate=candidate,
                        completeness=completeness,
                        support=support,
                        treatment_features=treatment_features,
                    ),
                    supporting_features=support,
                    missing_required_features=missing,
                    disqualifying_features=disqualifying,
                    competing_candidates=competitors,
                    ambiguity=ambiguity,
                    warnings=warnings,
                )
            )
        return tuple(assessments)

    @staticmethod
    def _state(
        *, missing: tuple[Feature, ...],
        disqualifying: tuple[Feature, ...],
        competitors: tuple[EditorialFormat, ...],
    ) -> tuple[
        EditorialFormatCompleteness, EditorialFormatAmbiguity, tuple[str, ...]
    ]:
        if missing:
            return (
                EditorialFormatCompleteness.INCOMPLETE,
                EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE,
                ("INSUFFICIENT_CORE_STRUCTURE",),
            )
        if disqualifying:
            warnings = ["PARTIAL_STRUCTURE", "DISQUALIFYING_FEATURE_PRESENT"]
            if competitors:
                warnings.append("COMPETING_PROFILE")
            return (
                EditorialFormatCompleteness.PARTIAL,
                EditorialFormatAmbiguity.CONTRADICTORY,
                tuple(warnings),
            )
        if competitors:
            return (
                EditorialFormatCompleteness.PARTIAL,
                EditorialFormatAmbiguity.COMPETING,
                ("PARTIAL_STRUCTURE", "COMPETING_PROFILE"),
            )
        return (
            EditorialFormatCompleteness.COMPLETE,
            EditorialFormatAmbiguity.CLEAR,
            (),
        )

    def _strength(
        self, *, candidate: EditorialFormat,
        completeness: EditorialFormatCompleteness,
        support: tuple[Feature, ...],
        treatment_features: EditorialTreatmentFeatureResult,
    ) -> SemanticEvidenceStrength:
        if completeness is EditorialFormatCompleteness.INCOMPLETE:
            return SemanticEvidenceStrength.WEAK
        if completeness is EditorialFormatCompleteness.PARTIAL:
            return SemanticEvidenceStrength.MODERATE
        profile = self._PROFILES[candidate]
        optional_support = any(
            feature in support for feature in profile.supporting
        )
        coherent_core = all(
            self._feature_is_document_level(feature, treatment_features)
            for feature in profile.required
        )
        return (
            SemanticEvidenceStrength.STRONG
            if optional_support or coherent_core
            else SemanticEvidenceStrength.MODERATE
        )

    @staticmethod
    def _feature_is_document_level(
        feature: Feature, result: EditorialTreatmentFeatureResult,
    ) -> bool:
        if feature in result.cross_section_features:
            return True
        return sum(
            feature in section for section in (
                result.headline_features, result.lead_features,
                result.body_features,
            )
        ) >= 2

    @staticmethod
    def _ordered_features(features: set[Feature]) -> tuple[Feature, ...]:
        return tuple(feature for feature in Feature if feature in features)
