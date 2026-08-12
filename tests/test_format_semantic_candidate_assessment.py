"""Format-specific structural sufficiency tests for the candidate assessor."""

from dataclasses import replace

import pytest

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


def _relation(
    candidate: str,
    reason: str,
    *,
    kind: SemanticRelationshipType = SemanticRelationshipType.ACTOR_PERFORMS_ACTION,
    subject: SemanticComponent = SemanticComponent.EVENT,
    object_: SemanticComponent = SemanticComponent.ACTION,
    index: int = 0,
    suppress: bool = False,
) -> SemanticRelationship:
    label = f"FORMAT_{candidate}"
    return SemanticRelationship(
        source_section=SourceSection.BODY,
        sentence_index=index,
        relationship_type=kind,
        subject_component=subject,
        subject_text="symbolic-subject",
        object_component=object_,
        object_text="symbolic-object",
        strength=EvidenceStrength.STRONG,
        reason_code=reason,
        evidence_indexes=(),
        supports=() if suppress else (label,),
        suppresses=(label,) if suppress else (),
    )


def _assess(*relations: SemanticRelationship):
    evidence = CompositionalSemanticEvidence(
        relationships=relations,
        primary_domain_candidates=(),
        secondary_domain_candidates=(),
        format_support=(),
        format_suppression=(),
        intent_support=(),
        warnings=(),
    )
    return {
        item.candidate: item
        for item in DeterministicSemanticCandidateAssessor().assess(
            semantic_evidence=evidence
        )
    }


def _full(candidate: str) -> tuple[SemanticRelationship, ...]:
    if candidate == "FACT_CHECK":
        return (
            _relation(candidate, "CLAIM_ASSERTION", subject=SemanticComponent.CLAIM),
            _relation(candidate, "INDEPENDENT_VERIFICATION", index=1),
            _relation(candidate, "TRUTH_STATUS_CONCLUSION", object_=SemanticComponent.OUTCOME, index=2),
        )
    if candidate == "SERVICE":
        return (
            _relation(candidate, "APPLICATION_PROCEDURE_ACTION", index=0),
            _relation(candidate, "ELIGIBILITY_REQUIREMENT", kind=SemanticRelationshipType.REQUIREMENT_APPLIES_TO_AUDIENCE, index=1),
        )
    if candidate == "GUIDE":
        return (
            _relation(candidate, "RECOMMENDED_ACTION_GUIDANCE", kind=SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE, subject=SemanticComponent.RECOMMENDED_ACTION, object_=SemanticComponent.AFFECTED_AUDIENCE),
            _relation(candidate, "SECOND_INSTRUCTION_ACTION", kind=SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE, subject=SemanticComponent.RECOMMENDED_ACTION, object_=SemanticComponent.AFFECTED_AUDIENCE, index=1),
        )
    if candidate == "TREND_UPDATE":
        return (
            _relation(candidate, "CURRENT_INDICATOR_VALUE", kind=SemanticRelationshipType.INTERPRETATION_OF_INDICATOR, subject=SemanticComponent.INDICATOR, object_=SemanticComponent.INTERPRETATION),
            _relation(candidate, "PRIOR_PERIOD_REFERENCE_COMPARISON", index=1),
            _relation(candidate, "DIRECTIONAL_CHANGE_INCREASE", index=2),
        )
    if candidate == "RESULT_REPORT":
        return (_relation(candidate, "COMPLETED_FINAL_RESULT", kind=SemanticRelationshipType.EVENT_HAS_OUTCOME, subject=SemanticComponent.EVENT, object_=SemanticComponent.OUTCOME),)
    if candidate == "ANALYSIS":
        return (
            _relation(candidate, "EVENT_CAUSE_CONSTRAINT", kind=SemanticRelationshipType.CONSEQUENCE_OF_EVENT, object_=SemanticComponent.CONSEQUENCE),
            _relation(candidate, "EFFECT_IMPLICATION_CONSEQUENCE", kind=SemanticRelationshipType.CONSEQUENCE_OF_EVENT, object_=SemanticComponent.CONSEQUENCE, index=1),
        )
    if candidate == "EXPLAINER":
        return (
            _relation(candidate, "SYSTEM_MECHANISM_METHOD", kind=SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT, subject=SemanticComponent.METHOD, object_=SemanticComponent.PRIMARY_SUBJECT),
            _relation(candidate, "UNDERSTANDING_EXPLANATION", kind=SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT, subject=SemanticComponent.METHOD, object_=SemanticComponent.PRIMARY_SUBJECT, index=1),
        )
    return (_relation(candidate, "EVENT_ANNOUNCEMENT_NEWS_REPORT"),)


@pytest.mark.parametrize(
    "candidate",
    ("FACT_CHECK", "SERVICE", "GUIDE", "TREND_UPDATE", "RESULT_REPORT", "ANALYSIS", "EXPLAINER", "STANDARD_NEWS"),
)
def test_complete_format_structures_can_be_sufficient(candidate: str) -> None:
    result = _assess(*_full(candidate))[candidate]
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


@pytest.mark.parametrize(
    ("candidate", "relations"),
    (
        ("FACT_CHECK", (_relation("FACT_CHECK", "CLAIM_ONLY", subject=SemanticComponent.CLAIM),)),
        ("SERVICE", (_relation("SERVICE", "AUTHORITY_REQUIREMENT"), _relation("SERVICE", "SECOND_REQUIREMENT", index=1))),
        ("GUIDE", (_relation("GUIDE", "ADVICE_MENTION", subject=SemanticComponent.AUTHORITY, object_=SemanticComponent.AUTHORITY), _relation("GUIDE", "SECOND_ADVICE_MENTION", subject=SemanticComponent.AUTHORITY, object_=SemanticComponent.AUTHORITY, index=1))),
        ("TREND_UPDATE", (_relation("TREND_UPDATE", "STATIC_CURRENT_VALUE", subject=SemanticComponent.INDICATOR), _relation("TREND_UPDATE", "DATED_VALUE", subject=SemanticComponent.INDICATOR, index=1))),
        ("RESULT_REPORT", (_relation("RESULT_REPORT", "FUTURE_SCHEDULED_EXPECTED_RESULT", kind=SemanticRelationshipType.EVENT_HAS_OUTCOME, object_=SemanticComponent.OUTCOME),)),
        ("ANALYSIS", (_relation("ANALYSIS", "INCIDENTAL_EFFECT", kind=SemanticRelationshipType.CONSEQUENCE_OF_EVENT, object_=SemanticComponent.CONSEQUENCE), _relation("ANALYSIS", "SECOND_EFFECT", kind=SemanticRelationshipType.CONSEQUENCE_OF_EVENT, object_=SemanticComponent.CONSEQUENCE, index=1))),
        ("EXPLAINER", (_relation("EXPLAINER", "METHOD_BACKGROUND", kind=SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT, subject=SemanticComponent.METHOD, object_=SemanticComponent.PRIMARY_SUBJECT), _relation("EXPLAINER", "SECOND_METHOD", kind=SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT, subject=SemanticComponent.METHOD, object_=SemanticComponent.PRIMARY_SUBJECT, index=1))),
    ),
)
def test_repeated_incomplete_format_support_is_never_sufficient(
    candidate: str, relations: tuple[SemanticRelationship, ...],
) -> None:
    result = _assess(*relations)[candidate]
    assert result.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT
    assert "FORMAT_STRUCTURE_INCOMPLETE" in result.warnings


def test_fact_check_official_denial_or_confirmation_is_not_complete() -> None:
    denial = _relation("FACT_CHECK", "CLAIM_OFFICIAL_DENIAL", subject=SemanticComponent.CLAIM)
    confirmation = replace(denial, reason_code="AUTHORITY_CONFIRMATION", sentence_index=1)
    assert _assess(denial, confirmation)["FACT_CHECK"].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


def test_procedure_evidence_does_not_complete_fact_check() -> None:
    relations = tuple(replace(item, supports=("FORMAT_FACT_CHECK",)) for item in _full("SERVICE"))
    assert _assess(*relations)["FACT_CHECK"].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


@pytest.mark.parametrize(
    ("left", "right"),
    (("GUIDE", "SERVICE"), ("RESULT_REPORT", "TREND_UPDATE"), ("STANDARD_NEWS", "ANALYSIS")),
)
def test_complete_neighboring_formats_compete_without_automatic_resolution(
    left: str, right: str,
) -> None:
    results = _assess(*_full(left), *_full(right))
    assert results[left].sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert results[right].sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert right in results[left].competing_candidates
    assert left in results[right].competing_candidates


def test_incomplete_competitor_does_not_block_complete_structure() -> None:
    incomplete = _relation("SERVICE", "REQUIREMENT_ONLY")
    results = _assess(*_full("GUIDE"), incomplete)
    assert results["GUIDE"].sufficiency is SemanticEvidenceSufficiency.SUFFICIENT
    assert results["SERVICE"].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


def test_format_suppression_still_produces_candidate_relative_conflict() -> None:
    support = _full("TREND_UPDATE")
    suppression = _relation("TREND_UPDATE", "NO_TEMPORAL_COMPARISON", suppress=True, index=3)
    result = _assess(*support, suppression)["TREND_UPDATE"]
    assert result.direction is SemanticEvidenceDirection.CONFLICTING
    assert result.sufficiency is SemanticEvidenceSufficiency.CONFLICTED


def test_duplicate_relations_do_not_complete_an_incomplete_structure() -> None:
    item = _relation("SERVICE", "REQUIREMENT_ONLY")
    result = _assess(item, item)["SERVICE"]
    assert result.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT
    assert "DUPLICATE_EVIDENCE_DISCOUNTED" in result.warnings


def _raw(body: str):
    source = NormalizedSource(
        title="عنوان تحريري عام", body=body, source_name="مصدر عام",
        source_url="https://example.com/story", language="ar",
    )
    context = DeterministicContextualEvidenceEngine().analyze(source=source)
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=source, contextual_evidence=context,
    )
    return {
        item.candidate: item
        for item in DeterministicSemanticCandidateAssessor().assess(
            semantic_evidence=semantic, contextual_evidence=context,
        )
    }


@pytest.mark.parametrize(
    ("body", "candidate", "sufficient"),
    (
        ("انتشر ادعاء بين القراء. ورد الادعاء بلا فحص أو نتيجة.", "FACT_CHECK", False),
        ("انتشر ادعاء ونفته جهة رسمية. نشر البيان تفاصيل النفي.", "FACT_CHECK", False),
        ("انتشر ادعاء. تحقق الفريق من الأدلة وثبت أنه زائف.", "FACT_CHECK", True),
        ("أعلنت الجهة شروط الأهلية. آخر موعد للتسجيل يوم الخميس.", "SERVICE", True),
        ("ذكرت الجهة إجراء رسميا. نشر البيان معلومات عامة فقط.", "SERVICE", False),
        ("ينصح الأطباء بتجنب التدخين. يجب اتباع خطوات وقائية يومية.", "GUIDE", True),
        ("ذكر البيان نصائح عامة. أعلن المسؤول معلومات إضافية.", "GUIDE", False),
        ("يجب اتباع خطوات التسجيل. تشمل الخدمة موعدا وشروط أهلية.", "GUIDE", True),
        ("بلغ السعر مئة جنيه اليوم. نشر التقرير القيمة الحالية فقط.", "TREND_UPDATE", False),
        ("في يوم الاثنين بلغ السعر مئة جنيه. بقي البيان عند قيمة واحدة.", "TREND_UPDATE", False),
        ("بلغ السعر مئة جنيه اليوم. ارتفع مقارنة بالشهر الماضي. سجل المعدل خمسين اليوم. انخفض مقارنة بالعام الماضي.", "TREND_UPDATE", True),
        ("انتهت المباراة بفوز الفريق. النتيجة النهائية هدفان.", "RESULT_REPORT", True),
        ("تقام المباراة غدا. أعلن النادي موعد البداية.", "RESULT_REPORT", False),
        ("انتهت المباراة بنتيجة نهائية. زاد الفارق بهدف واحد.", "TREND_UPDATE", False),
        ("ارتفع المعدل خلال العام الماضي. واصل الارتفاع هذا الأسبوع.", "RESULT_REPORT", False),
        ("أعلنت الوزارة قرارا جديدا. تضمن البيان تفاصيل القرار.", "STANDARD_NEWS", True),
        ("بدأ الحدث وأضيفت خلفية موجزة. نشر البيان تفاصيل الحدث.", "ANALYSIS", False),
        ("بدأ الحدث بسبب نقص الموارد. أدى ذلك إلى تأثير واسع.", "ANALYSIS", True),
        ("يوضح التقرير النظام. يعمل عبر آلية مترابطة لفهم العملية.", "EXPLAINER", True),
        ("أعلنت الجهة حدثا جديدا. أضافت جملة تشرح خلفية عابرة.", "EXPLAINER", False),
        ("أطلقت المؤسسة خدمة جديدة. يوضح البيان معلومات الإطلاق.", "STANDARD_NEWS", True),
        ("بلغ المعدل مستوى جديدا حاليا. نشر التقرير تفاصيل الرقم.", "TREND_UPDATE", False),
        ("أعلنت اللجنة موعد الجلسة المقبلة. يبدأ الحدث الأسبوع المقبل.", "RESULT_REPORT", False),
    ),
)
def test_generalized_raw_arabic_format_boundaries(
    body: str, candidate: str, sufficient: bool,
) -> None:
    result = _raw(body).get(candidate)
    if sufficient:
        assert result is not None
        assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT
    else:
        assert result is None or result.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT
