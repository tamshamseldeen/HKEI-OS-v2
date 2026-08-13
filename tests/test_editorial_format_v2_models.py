"""Contract tests for additive Editorial Format V2 domain models."""

from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
from pathlib import Path

import pytest

from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_ambiguity import EditorialFormatAmbiguity
from src.formatting.editorial_format_candidate_assessment import (
    EditorialFormatCandidateAssessment,
)
from src.formatting.editorial_format_completeness import EditorialFormatCompleteness
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.formatting.editorial_format_v2_result import EditorialFormatV2Result
from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature
from src.formatting.editorial_treatment_feature_result import (
    EditorialTreatmentFeatureResult,
)
from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_VALUES = (
    "EVENT_REPORTING", "TEMPORAL_MOVEMENT", "COMPLETED_OUTCOME",
    "CAUSAL_EXPLANATION", "MECHANISM_EXPLANATION", "ACTIONABLE_GUIDANCE",
    "PROCEDURAL_SERVICE", "CLAIM_VERIFICATION", "URGENT_BREAKING_SIGNAL",
    "LIST_OR_RANKING_STRUCTURE", "INTERVIEW_QA_STRUCTURE",
    "OPINION_ARGUMENTATION", "COMPARATIVE_STRUCTURE",
    "NARRATIVE_SCENE_STRUCTURE", "BIOGRAPHICAL_ARC",
)


def _assessment(
    candidate: EditorialFormat = EditorialFormat.STANDARD_NEWS,
    completeness: EditorialFormatCompleteness = EditorialFormatCompleteness.COMPLETE,
    strength: SemanticEvidenceStrength = SemanticEvidenceStrength.STRONG,
    ambiguity: EditorialFormatAmbiguity = EditorialFormatAmbiguity.CLEAR,
    competitors: tuple[EditorialFormat, ...] = (EditorialFormat.BREAKING,),
) -> EditorialFormatCandidateAssessment:
    return EditorialFormatCandidateAssessment(
        candidate=candidate,
        completeness=completeness,
        strength=strength,
        supporting_features=(EditorialTreatmentFeature.EVENT_REPORTING,),
        missing_required_features=(),
        disqualifying_features=(),
        competing_candidates=competitors,
        ambiguity=ambiguity,
        warnings=(),
    )


def _features() -> EditorialTreatmentFeatureResult:
    return EditorialTreatmentFeatureResult(
        features=(EditorialTreatmentFeature.EVENT_REPORTING,),
        headline_features=(EditorialTreatmentFeature.EVENT_REPORTING,),
        lead_features=(), body_features=(), cross_section_features=(), warnings=(),
    )


def _result(
    confidence: EditorialFormatConfidence = EditorialFormatConfidence.HIGH,
    ambiguity: EditorialFormatAmbiguity = EditorialFormatAmbiguity.CLEAR,
) -> EditorialFormatV2Result:
    return EditorialFormatV2Result(
        selected_format=EditorialFormat.STANDARD_NEWS,
        confidence=confidence,
        ambiguity=ambiguity,
        candidate_assessments=(_assessment(),),
        treatment_features=_features(), warnings=(),
    )


def test_treatment_feature_enum_exact_contract() -> None:
    assert tuple(item.value for item in EditorialTreatmentFeature) == FEATURE_VALUES


def test_completeness_and_ambiguity_exact_contracts() -> None:
    assert tuple(item.value for item in EditorialFormatCompleteness) == (
        "INCOMPLETE", "PARTIAL", "COMPLETE",
    )
    assert tuple(item.value for item in EditorialFormatAmbiguity) == (
        "CLEAR", "COMPETING", "INSUFFICIENT_EVIDENCE", "CONTRADICTORY",
    )


def test_candidate_assessment_is_frozen() -> None:
    item = _assessment()
    with pytest.raises(FrozenInstanceError):
        item.strength = SemanticEvidenceStrength.WEAK  # type: ignore[misc]


def test_feature_result_is_frozen_and_symbolic_only() -> None:
    result = _features()
    with pytest.raises(FrozenInstanceError):
        result.features = ()  # type: ignore[misc]
    names = {field.name for field in fields(EditorialTreatmentFeatureResult)}
    assert names == {
        "features", "headline_features", "lead_features", "body_features",
        "cross_section_features", "warnings",
    }
    assert not names & {"article", "body", "raw_text", "matched_text", "benchmark"}


def test_v2_result_is_frozen_and_has_no_inference() -> None:
    result = _result()
    with pytest.raises(FrozenInstanceError):
        result.selected_format = EditorialFormat.BREAKING  # type: ignore[misc]
    assert result.selected_format is EditorialFormat.STANDARD_NEWS
    assert result.confidence is EditorialFormatConfidence.HIGH


def test_all_twelve_editorial_formats_are_representable() -> None:
    assessments = tuple(
        _assessment(candidate=item, competitors=()) for item in EditorialFormat
    )
    assert len(assessments) == len(EditorialFormat) == 12
    assert {item.candidate for item in assessments} == set(EditorialFormat)


def test_completeness_is_independent_from_ambiguity_and_strength() -> None:
    item = _assessment(
        completeness=EditorialFormatCompleteness.COMPLETE,
        strength=SemanticEvidenceStrength.WEAK,
        ambiguity=EditorialFormatAmbiguity.COMPETING,
    )
    assert item.completeness is EditorialFormatCompleteness.COMPLETE
    assert item.strength is SemanticEvidenceStrength.WEAK
    assert item.ambiguity is EditorialFormatAmbiguity.COMPETING


def test_ambiguity_is_independent_from_confidence() -> None:
    clear_low = _result(
        confidence=EditorialFormatConfidence.LOW,
        ambiguity=EditorialFormatAmbiguity.CLEAR,
    )
    competing_high = _result(
        confidence=EditorialFormatConfidence.HIGH,
        ambiguity=EditorialFormatAmbiguity.COMPETING,
    )
    assert clear_low.confidence is EditorialFormatConfidence.LOW
    assert competing_high.ambiguity is EditorialFormatAmbiguity.COMPETING


def test_self_competition_and_duplicate_competitors_are_rejected() -> None:
    with pytest.raises(ValueError, match="itself"):
        _assessment(competitors=(EditorialFormat.STANDARD_NEWS,))
    with pytest.raises(ValueError, match="duplicates"):
        _assessment(competitors=(EditorialFormat.BREAKING, EditorialFormat.BREAKING))


def test_duplicate_features_are_rejected_in_candidate_and_feature_result() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        EditorialFormatCandidateAssessment(
            candidate=EditorialFormat.GUIDE,
            completeness=EditorialFormatCompleteness.PARTIAL,
            strength=SemanticEvidenceStrength.MODERATE,
            supporting_features=(
                EditorialTreatmentFeature.ACTIONABLE_GUIDANCE,
                EditorialTreatmentFeature.ACTIONABLE_GUIDANCE,
            ),
            missing_required_features=(), disqualifying_features=(),
            competing_candidates=(), ambiguity=EditorialFormatAmbiguity.COMPETING,
            warnings=(),
        )
    with pytest.raises(ValueError, match="duplicates"):
        EditorialTreatmentFeatureResult(
            features=(
                EditorialTreatmentFeature.EVENT_REPORTING,
                EditorialTreatmentFeature.EVENT_REPORTING,
            ),
            headline_features=(), lead_features=(), body_features=(),
            cross_section_features=(), warnings=(),
        )


@pytest.mark.parametrize(
    ("constructor", "message"),
    [
        (
            lambda: EditorialTreatmentFeatureResult(
                features=("EVENT_REPORTING",),  # type: ignore[arg-type]
                headline_features=(), lead_features=(), body_features=(),
                cross_section_features=(), warnings=(),
            ),
            "invalid member",
        ),
        (
            lambda: EditorialFormatCandidateAssessment(
                candidate=EditorialFormat.SERVICE,
                completeness=EditorialFormatCompleteness.COMPLETE,
                strength=SemanticEvidenceStrength.STRONG,
                supporting_features=(), missing_required_features=(),
                disqualifying_features=(),
                competing_candidates=("GUIDE",),  # type: ignore[arg-type]
                ambiguity=EditorialFormatAmbiguity.CLEAR, warnings=(),
            ),
            "invalid member",
        ),
        (
            lambda: EditorialFormatV2Result(
                selected_format=EditorialFormat.SERVICE,
                confidence=EditorialFormatConfidence.HIGH,
                ambiguity=EditorialFormatAmbiguity.CLEAR,
                candidate_assessments=("invalid",),  # type: ignore[arg-type]
                treatment_features=_features(), warnings=(),
            ),
            "invalid member",
        ),
    ],
)
def test_invalid_tuple_members_are_rejected(constructor, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        constructor()


def test_duplicate_candidate_assessments_and_warning_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="repeat candidates"):
        EditorialFormatV2Result(
            selected_format=EditorialFormat.STANDARD_NEWS,
            confidence=EditorialFormatConfidence.MEDIUM,
            ambiguity=EditorialFormatAmbiguity.COMPETING,
            candidate_assessments=(_assessment(), _assessment()),
            treatment_features=_features(), warnings=(),
        )
    with pytest.raises(ValueError, match="duplicates"):
        EditorialTreatmentFeatureResult(
            features=(), headline_features=(), lead_features=(), body_features=(),
            cross_section_features=(), warnings=("WARNING", "WARNING"),
        )


def test_models_have_no_benchmark_provider_semantic_engine_or_resolver_dependency() -> None:
    modules = (
        EditorialFormatCandidateAssessment,
        EditorialTreatmentFeatureResult,
        EditorialFormatV2Result,
    )
    source = "\n".join(inspect.getsource(item) for item in modules).casefold()
    forbidden = (
        "benchmark", "openai", "provider", "request_builder",
        "deterministiccompositionalsemanticengine", "resolver",
    )
    assert not any(term in source for term in forbidden)


def test_v1_classifier_is_unchanged() -> None:
    path = PROJECT_ROOT / "src/formatting/deterministic_editorial_format_classifier.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "a332c14f12c7cb6bad0fab214d1ff44512ccc9bbacd6f9ef9f86f262c278c117"
    )


def test_models_align_with_canonical_specification_contract() -> None:
    specification = (
        PROJECT_ROOT / "docs/EDITORIAL_FORMAT_SUBSYSTEM_V2_SPECIFICATION.md"
    ).read_text(encoding="utf-8")
    assert all(f"`{value}`" in specification for value in FEATURE_VALUES)
    assert all(f"`{item.value}`" in specification for item in EditorialFormat)
    assert "**REUSE_AS_SUPPORT_ONLY**" in specification
    assert "**HYBRID_DOCUMENT_PROFILE_AND_RULE_GRAPH**" in specification
    assert "**READY_FOR_IMPLEMENTATION**" in specification
