"""Tests for deterministic candidate-relative semantic assessment."""

from dataclasses import replace
from pathlib import Path

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import DeterministicContextualEvidenceEngine
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource
from src.semantics.compositional_semantic_evidence import CompositionalSemanticEvidence
from src.semantics.deterministic_compositional_semantic_engine import DeterministicCompositionalSemanticEngine
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor
from src.semantics.semantic_component import SemanticComponent
from src.semantics.semantic_evidence_direction import SemanticEvidenceDirection
from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength
from src.semantics.semantic_evidence_sufficiency import SemanticEvidenceSufficiency
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def relation(
    *,
    supports: tuple[str, ...] = (),
    suppresses: tuple[str, ...] = (),
    relationship_type: SemanticRelationshipType = SemanticRelationshipType.SUBJECT_BELONGS_TO_DOMAIN,
    subject: SemanticComponent = SemanticComponent.PRIMARY_SUBJECT,
    object_: SemanticComponent = SemanticComponent.DOMAIN,
    sentence_index: int = 0,
    reason_code: str = "GENERIC_TEST_RELATIONSHIP",
    strength: EvidenceStrength = EvidenceStrength.STRONG,
    object_text: str = "DOMAIN",
) -> SemanticRelationship:
    return SemanticRelationship(
        source_section=SourceSection.LEAD,
        sentence_index=sentence_index,
        relationship_type=relationship_type,
        subject_component=subject,
        subject_text="symbolic-subject",
        object_component=object_,
        object_text=object_text,
        strength=strength,
        reason_code=reason_code,
        evidence_indexes=(),
        supports=supports,
        suppresses=suppresses,
    )


def evidence(*relationships: SemanticRelationship, **changes: object) -> CompositionalSemanticEvidence:
    values = {
        "relationships": relationships,
        "primary_domain_candidates": (),
        "secondary_domain_candidates": (),
        "format_support": (),
        "format_suppression": (),
        "intent_support": (),
        "warnings": (),
    }
    values.update(changes)
    return CompositionalSemanticEvidence(**values)  # type: ignore[arg-type]


def assess(*relationships: SemanticRelationship, **changes: object):
    return DeterministicSemanticCandidateAssessor().assess(
        semantic_evidence=evidence(*relationships, **changes)
    )


def one(*relationships: SemanticRelationship, **changes: object):
    values = assess(*relationships, **changes)
    assert len(values) == 1
    return values[0]


def test_support_only_direction() -> None:
    assert one(relation(supports=("PRIMARY_DOMAIN_HEALTH",))).direction is SemanticEvidenceDirection.SUPPORT


def test_suppression_only_direction() -> None:
    assert one(relation(suppresses=("PRIMARY_DOMAIN_HEALTH",))).direction is SemanticEvidenceDirection.SUPPRESS


def test_neutral_direction_from_related_nondiscriminating_relationship() -> None:
    result = one(relation(object_text="PRIMARY_DOMAIN_HEALTH"))
    assert result.direction is SemanticEvidenceDirection.NEUTRAL
    assert result.strength is SemanticEvidenceStrength.WEAK
    assert result.sufficiency is SemanticEvidenceSufficiency.INSUFFICIENT


def test_support_and_suppression_are_conflicted() -> None:
    result = one(relation(
        supports=("FORMAT_TREND_UPDATE",), suppresses=("FORMAT_TREND_UPDATE",)
    ))
    assert result.direction is SemanticEvidenceDirection.CONFLICTING
    assert result.sufficiency is SemanticEvidenceSufficiency.CONFLICTED
    assert "SUPPORT_SUPPRESSION_CONFLICT" in result.warnings


def test_isolated_noncentral_evidence_is_weak_and_insufficient() -> None:
    result = one(relation(
        supports=("PRIMARY_DOMAIN_GOVERNMENT",),
        subject=SemanticComponent.AUTHORITY, object_=SemanticComponent.ACTION,
    ))
    assert (result.strength, result.sufficiency) == (
        SemanticEvidenceStrength.WEAK, SemanticEvidenceSufficiency.INSUFFICIENT,
    )


def test_one_subject_bearing_relationship_is_moderate_partial() -> None:
    result = one(relation(supports=("PRIMARY_DOMAIN_HEALTH",)))
    assert (result.strength, result.sufficiency) == (
        SemanticEvidenceStrength.MODERATE, SemanticEvidenceSufficiency.PARTIAL,
    )


def test_multiple_independent_subject_relationships_are_strong_sufficient() -> None:
    first = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    second = replace(first, sentence_index=1, reason_code="INDEPENDENT_HEALTH_STATE")
    result = one(first, second)
    assert (result.strength, result.sufficiency) == (
        SemanticEvidenceStrength.STRONG, SemanticEvidenceSufficiency.SUFFICIENT,
    )


def test_exact_duplicate_evidence_does_not_inflate_strength() -> None:
    item = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    result = one(item, item)
    assert result.strength is SemanticEvidenceStrength.MODERATE
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert "DUPLICATE_EVIDENCE_DISCOUNTED" in result.warnings


@pytest.mark.parametrize(
    ("role", "warning"),
    (
        (SemanticComponent.AUTHORITY, "AUTHORITY_DOMINATED"),
        (SemanticComponent.ACTOR, "ACTOR_DOMINATED"),
        (SemanticComponent.METHOD, "METHOD_DOMINATED"),
    ),
)
def test_secondary_role_only_support_never_resolves(
    role: SemanticComponent, warning: str,
) -> None:
    result = one(relation(
        supports=("PRIMARY_DOMAIN_TECHNOLOGY",), subject=role, object_=role,
    ))
    assert result.strength is SemanticEvidenceStrength.WEAK
    assert result.sufficiency is SemanticEvidenceSufficiency.INSUFFICIENT
    assert warning in result.warnings


def test_subject_bearing_support_outranks_authority_role_risk() -> None:
    authority = relation(
        supports=("PRIMARY_DOMAIN_HEALTH",), subject=SemanticComponent.AUTHORITY,
        object_=SemanticComponent.ACTION,
    )
    subject = replace(
        authority, sentence_index=1, subject_component=SemanticComponent.PRIMARY_SUBJECT,
        object_component=SemanticComponent.DOMAIN, reason_code="CENTRAL_SUBJECT",
    )
    result = one(authority, subject)
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert "AUTHORITY_DOMINATED" not in result.warnings


def test_comparable_domain_candidates_are_recorded_and_prevent_sufficiency() -> None:
    health = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    economy = replace(
        health, supports=("PRIMARY_DOMAIN_ECONOMY",), sentence_index=1,
        reason_code="ECONOMY_SUBJECT",
    )
    results = {item.candidate: item for item in assess(health, economy)}
    assert results["HEALTH"].competing_candidates == ("ECONOMY",)
    assert results["ECONOMY"].competing_candidates == ("HEALTH",)
    assert all(item.sufficiency is SemanticEvidenceSufficiency.PARTIAL for item in results.values())


def test_weak_competitor_is_ignored() -> None:
    strong = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    strong_2 = replace(strong, sentence_index=1, reason_code="SECOND_HEALTH_SUPPORT")
    weak = relation(
        supports=("PRIMARY_DOMAIN_GOVERNMENT",), subject=SemanticComponent.AUTHORITY,
        object_=SemanticComponent.AUTHORITY, sentence_index=2,
    )
    results = {item.candidate: item for item in assess(strong, strong_2, weak)}
    assert results["HEALTH"].competing_candidates == ()
    assert results["HEALTH"].sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_candidate_is_never_listed_as_its_own_competitor() -> None:
    item = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    assert "HEALTH" not in one(item).competing_candidates


def test_candidates_are_sorted_lexically_and_not_full_enum_generated() -> None:
    results = assess(
        relation(supports=("FORMAT_TREND_UPDATE",)),
        relation(supports=("PRIMARY_DOMAIN_HEALTH",), sentence_index=1),
    )
    assert tuple(item.candidate for item in results) == ("HEALTH", "TREND_UPDATE")


def test_symbolic_provenance_is_unique_and_contains_no_source_text() -> None:
    result = one(relation(supports=("PRIMARY_DOMAIN_HEALTH",)))
    assert result.supporting_relationship_types == ("SUBJECT_BELONGS_TO_DOMAIN",)
    assert result.suppressing_relationship_types == ()
    assert result.role_basis == ("SUBJECT", "DOMAIN")


def test_collection_only_candidate_presence_is_not_sufficient() -> None:
    result = one(primary_domain_candidates=("PRIMARY_DOMAIN_HEALTH",))
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.strength is SemanticEvidenceStrength.WEAK
    assert result.sufficiency is SemanticEvidenceSufficiency.INSUFFICIENT


def test_effect_only_analysis_is_strong_but_structurally_partial() -> None:
    item = relation(
        supports=("FORMAT_ANALYSIS",),
        relationship_type=SemanticRelationshipType.CONSEQUENCE_OF_EVENT,
        subject=SemanticComponent.EVENT, object_=SemanticComponent.CONSEQUENCE,
    )
    result = one(item, replace(item, sentence_index=1, reason_code="SECOND_CAUSAL_CHAIN"))
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert "FORMAT_STRUCTURE_INCOMPLETE" in result.warnings


def test_static_measurement_is_not_sufficient_for_trend() -> None:
    result = one(relation(
        supports=("FORMAT_TREND_UPDATE",),
        relationship_type=SemanticRelationshipType.INTERPRETATION_OF_INDICATOR,
        subject=SemanticComponent.INDICATOR, object_=SemanticComponent.INTERPRETATION,
    ))
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL


def test_completed_result_relationship_is_structurally_sufficient() -> None:
    result = one(relation(
        supports=("FORMAT_RESULT_REPORT",),
        relationship_type=SemanticRelationshipType.EVENT_HAS_OUTCOME,
        subject=SemanticComponent.EVENT, object_=SemanticComponent.OUTCOME,
    ))
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_incomplete_fact_check_structure_is_not_sufficient() -> None:
    result = one(relation(
        supports=("FORMAT_FACT_CHECK",),
        relationship_type=SemanticRelationshipType.CLAIM_ATTRIBUTED_TO_AUTHORITY,
        subject=SemanticComponent.CLAIM, object_=SemanticComponent.AUTHORITY,
    ))
    assert result.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


@pytest.mark.parametrize(
    ("candidate", "relationship_type", "subject", "object_"),
    (
        ("GUIDE", SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE, SemanticComponent.RECOMMENDED_ACTION, SemanticComponent.AFFECTED_AUDIENCE),
        ("SERVICE", SemanticRelationshipType.ACTION_HAS_DEADLINE, SemanticComponent.ACTION, SemanticComponent.DEADLINE),
    ),
)
def test_guide_and_service_keep_distinct_provenance(
    candidate: str,
    relationship_type: SemanticRelationshipType,
    subject: SemanticComponent,
    object_: SemanticComponent,
) -> None:
    result = one(relation(
        supports=(f"FORMAT_{candidate}",), relationship_type=relationship_type,
        subject=subject, object_=object_,
    ))
    assert result.candidate == candidate
    assert result.supporting_relationship_types == (relationship_type.value,)


def _raw_assess(body: str):
    source = NormalizedSource(
        title="عنوان عام", body=body, source_name="مصدر",
        source_url="https://example.com", language="ar",
    )
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=source, contextual_evidence=contextual,
    )
    return DeterministicSemanticCandidateAssessor().assess(
        semantic_evidence=semantic, contextual_evidence=contextual,
    )


@pytest.mark.parametrize(
    ("body", "candidate"),
    (
        ("أعلنت وزارة الصحة تقديم الخدمات الطبية وعلاج الأمراض", "HEALTH"),
        ("أعلن البنك المركزي أن معدل البطالة تراجع مع تحسن سوق العمل", "ECONOMY"),
        ("فحص الأورام باستخدام الذكاء الاصطناعي لتحسين علاج الأمراض", "HEALTH"),
        ("بدأ الحدث بسبب نقص الموارد. أدى ذلك إلى تأثير واسع", "ANALYSIS"),
        ("انتهت المباراة بفوز الفريق. النتيجة النهائية هدفان", "RESULT_REPORT"),
        ("بلغ السعر مئة جنيه. ارتفع مقارنة بالشهر الماضي", "TREND_UPDATE"),
        ("أعلنت الجهة موعد التسجيل. تشمل الخدمة شروط الأهلية", "SERVICE"),
        ("انتشر ادعاء. تحقق الفريق من الأدلة وثبت أنه زائف", "FACT_CHECK"),
    ),
)
def test_raw_arabic_evidence_flows_into_candidate_assessment(
    body: str, candidate: str,
) -> None:
    results = {item.candidate: item for item in _raw_assess(body)}
    assert candidate in results
    assert results[candidate].supporting_relationship_types


def test_no_holdout_identifiers_in_assessor_or_tests() -> None:
    text = "\n".join(
        (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/semantics/deterministic_semantic_candidate_assessor.py",
            "tests/test_deterministic_semantic_candidate_assessor.py",
        )
    )
    forbidden = tuple(f'"{value:03d}"' for value in range(51, 61))
    assert not any(identifier in text for identifier in forbidden)


def test_empty_evidence_emits_no_full_candidate_universe() -> None:
    assert assess() == ()
