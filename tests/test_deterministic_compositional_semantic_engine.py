"""Tests for foundational deterministic semantic composition."""

from dataclasses import fields

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType


def make_source(
    *,
    title: str = "عنوان بلا تركيب",
    body: str = "محتوى بلا تركيب",
) -> NormalizedSource:
    """Create one normalized source for semantic composition tests."""
    return NormalizedSource(
        title=title,
        body=body,
        source_name="Source",
        source_url="https://example.com",
        language="ar",
    )


def compose(source: NormalizedSource) -> tuple[
    CompositionalSemanticEvidence,
    ContextualEvidence,
]:
    """Analyze and compose one source using deterministic defaults."""
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=source,
        contextual_evidence=contextual,
    )
    return semantic, contextual


def relationship(
    evidence: CompositionalSemanticEvidence,
    relationship_type: SemanticRelationshipType,
) -> SemanticRelationship:
    """Return the first relationship of one required type."""
    return next(
        item
        for item in evidence.relationships
        if item.relationship_type is relationship_type
    )


def test_compose_returns_empty_typed_evidence_with_warning() -> None:
    """Return the immutable collection and stable warning when nothing composes."""
    evidence, _ = compose(make_source())

    assert isinstance(evidence, CompositionalSemanticEvidence)
    assert evidence.relationships == ()
    assert evidence.warnings == ("SEMANTIC_COMPOSITION_EMPTY",)
    assert evidence.format_support == ()
    assert evidence.format_suppression == ()
    assert evidence.intent_support == ()


def test_health_authority_composes_primary_domain_and_suppression() -> None:
    """Relate a health authority to its medical subject instead of government."""
    source = make_source(
        body=(
            "أعلنت وزارة الصحة والسكان تقديم الخدمات الطبية والفحوصات "
            "المجانية للمواطنين"
        )
    )
    evidence, _ = compose(source)
    item = relationship(
        evidence,
        SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT,
    )

    assert item.subject_text == "وزارة الصحة والسكان"
    assert item.object_text == "الخدمات الطبية والفحوصات المجانية"
    assert item.supports == ("PRIMARY_DOMAIN_HEALTH",)
    assert item.suppresses == ("PRIMARY_DOMAIN_GOVERNMENT",)
    assert item.reason_code == "AUTHORITY_DOMAIN_SUBJECT_COMPOSITION"
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_HEALTH",)


def test_higher_education_authority_composes_education() -> None:
    """Relate the education authority to universities rather than government."""
    source = make_source(
        body=(
            "أعلنت وزارة التعليم العالي تحقيق الجامعات المصرية مراكز متقدمة "
            "في التصنيفات العالمية"
        )
    )
    evidence, _ = compose(source)
    item = relationship(
        evidence,
        SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT,
    )

    assert item.object_text == "الجامعات المصرية"
    assert item.supports == ("PRIMARY_DOMAIN_EDUCATION",)
    assert item.suppresses == ("PRIMARY_DOMAIN_GOVERNMENT",)


def test_government_infrastructure_remains_government() -> None:
    """Keep government primary for an authority operating public infrastructure."""
    source = make_source(
        body="أعلنت الهيئة القومية للأنفاق بدء التشغيل التجريبي لمنظومة المونوريل"
    )
    evidence, _ = compose(source)
    item = relationship(
        evidence,
        SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT,
    )

    assert item.supports == ("PRIMARY_DOMAIN_GOVERNMENT",)
    assert item.suppresses == ()
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_GOVERNMENT",)


def test_ai_medical_method_composes_primary_secondary_and_suppression() -> None:
    """Treat AI as a method applied to a primary medical subject."""
    source = make_source(
        title=(
            "دراسة طبية: الذكاء الاصطناعي ينجح في تشخيص أورام السرطان المبكرة"
        )
    )
    evidence, _ = compose(source)
    item = relationship(
        evidence,
        SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT,
    )

    assert item.subject_text == "الذكاء الاصطناعي"
    assert item.object_text == "تشخيص أورام السرطان المبكرة"
    assert item.supports == (
        "PRIMARY_DOMAIN_HEALTH",
        "SECONDARY_DOMAIN_TECHNOLOGY",
    )
    assert item.suppresses == ("PRIMARY_DOMAIN_TECHNOLOGY",)
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_HEALTH",)
    assert evidence.secondary_domain_candidates == (
        "SECONDARY_DOMAIN_TECHNOLOGY",
    )


def test_reusable_method_indicator_composes_tool_with_other_domain() -> None:
    """Compose an indicated technology method with a distinct medical subject."""
    source = make_source(
        body="فحص الأورام باستخدام الذكاء الاصطناعي لتحسين علاج الأمراض"
    )
    evidence, _ = compose(source)
    item = relationship(
        evidence,
        SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT,
    )

    assert item.subject_text == "الذكاء الاصطناعي"
    assert item.object_text in ("الأورام", "علاج")
    assert "PRIMARY_DOMAIN_HEALTH" in item.supports
    assert "SECONDARY_DOMAIN_TECHNOLOGY" in item.supports


def test_genuine_ai_development_does_not_suppress_technology() -> None:
    """Avoid method suppression when AI development is itself the subject."""
    source = make_source(
        body="طور فريق بحثي نموذج ذكاء اصطناعي جديد لمعالجة اللغة"
    )
    evidence, _ = compose(source)

    assert all(
        "PRIMARY_DOMAIN_TECHNOLOGY" not in item.suppresses
        for item in evidence.relationships
    )
    assert not any(
        item.relationship_type is SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT
        for item in evidence.relationships
    )


def test_clear_actor_action_and_action_object_relationships_are_created() -> None:
    """Compose a non-authority actor with action before action-object evidence."""
    source = make_source(
        body=(
            "حذر خبراء الأمن السيبراني الشركات من البرمجيات الخبيثة وطالبوا "
            "بتحديث برامج الحماية"
        )
    )
    evidence, _ = compose(source)
    types = tuple(item.relationship_type for item in evidence.relationships)

    assert SemanticRelationshipType.ACTOR_PERFORMS_ACTION in types
    assert SemanticRelationshipType.ACTION_TARGETS_OBJECT in types
    assert types.index(SemanticRelationshipType.ACTOR_PERFORMS_ACTION) < types.index(
        SemanticRelationshipType.ACTION_TARGETS_OBJECT
    )


def test_generic_actor_without_action_creates_no_actor_relationship() -> None:
    """Reject a generic actor phrase without a supported local action."""
    evidence, _ = compose(make_source(body="فريق بحثي في المختبر"))

    assert not any(
        item.relationship_type is SemanticRelationshipType.ACTOR_PERFORMS_ACTION
        for item in evidence.relationships
    )


def test_relationships_remain_sentence_local_without_cross_composition() -> None:
    """Do not combine an authority in one sentence with a subject in another."""
    source = make_source(
        body="أعلنت وزارة الصحة بيانًا. تقديم الخدمات الطبية للمواطنين"
    )
    evidence, _ = compose(source)

    assert not any(
        item.relationship_type is SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT
        for item in evidence.relationships
    )


def test_provenance_section_sentence_and_indexes_are_valid() -> None:
    """Preserve local provenance and reference only real contextual items."""
    source = make_source(
        body=(
            "مقدمة بلا تركيب. أعلنت وزارة الصحة والسكان تقديم الخدمات الطبية. "
            "حذر خبراء الأمن السيبراني من البرمجيات الخبيثة"
        )
    )
    evidence, contextual = compose(source)

    assert evidence.relationships
    assert all(item.source_section is SourceSection.BODY for item in evidence.relationships)
    assert {item.sentence_index for item in evidence.relationships} == {0, 1}
    assert all(isinstance(item.evidence_indexes, tuple) for item in evidence.relationships)
    assert all(
        0 <= index < len(contextual.all_items)
        for item in evidence.relationships
        for index in item.evidence_indexes
    )
    assert all(
        contextual.all_items[index].source_section is item.source_section
        and contextual.all_items[index].sentence_index == item.sentence_index
        for item in evidence.relationships
        for index in item.evidence_indexes
    )


def test_relationship_and_candidate_deduplication_preserves_first_order() -> None:
    """Remove identical relationships and repeated strong domain candidates."""
    source = make_source(
        title="أعلنت وزارة الصحة تقديم الخدمات الطبية",
        body="أعلنت وزارة الصحة تقديم الخدمات الطبية",
    )
    evidence, contextual = compose(source)
    duplicated_context = ContextualEvidence(
        headline_items=contextual.headline_items + contextual.headline_items,
        lead_items=contextual.lead_items + contextual.lead_items,
        body_items=contextual.body_items,
        metadata_items=contextual.metadata_items,
        user_instruction_items=contextual.user_instruction_items,
        warnings=contextual.warnings,
    )
    duplicated = DeterministicCompositionalSemanticEngine().compose(
        source=source,
        contextual_evidence=duplicated_context,
    )

    assert len(evidence.relationships) == len(set(evidence.relationships))
    assert len(duplicated.relationships) == len(set(duplicated.relationships))
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_HEALTH",)
    assert duplicated.primary_domain_candidates == ("PRIMARY_DOMAIN_HEALTH",)


def test_inputs_are_unchanged_and_equal_inputs_are_deterministic() -> None:
    """Avoid input mutation and return equal output for identical inputs."""
    source = make_source(
        body="أعلنت وزارة الصحة والسكان تقديم الخدمات الطبية والفحوصات المجانية"
    )
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    source_snapshot = tuple(getattr(source, field.name) for field in fields(source))
    contextual_snapshot = contextual.all_items
    engine = DeterministicCompositionalSemanticEngine()

    first = engine.compose(source=source, contextual_evidence=contextual)
    second = engine.compose(source=source, contextual_evidence=contextual)

    assert first == second
    assert tuple(getattr(source, field.name) for field in fields(source)) == source_snapshot
    assert contextual.all_items == contextual_snapshot


def test_public_infrastructure_composes_government_domain() -> None:
    """Compose a public institution operating a generic transport system."""
    evidence, _ = compose(
        make_source(
            body=(
                "أعلنت الهيئة القومية للأنفاق بدء التشغيل التجريبي "
                "لمنظومة نقل عامة جديدة"
            )
        )
    )
    item = next(
        value
        for value in evidence.relationships
        if value.reason_code == "PUBLIC_INFRASTRUCTURE_DOMAIN_COMPOSITION"
    )

    assert item.relationship_type is (
        SemanticRelationshipType.INSTITUTION_BELONGS_TO_DOMAIN
    )
    assert item.strength is EvidenceStrength.STRONG
    assert item.supports == ("PRIMARY_DOMAIN_GOVERNMENT",)
    assert "PRIMARY_DOMAIN_GOVERNMENT" in evidence.primary_domain_candidates


def test_official_institution_alone_does_not_create_government_primary() -> None:
    """Require operation and public infrastructure beyond an institution name."""
    evidence, _ = compose(make_source(body="أصدرت الهيئة القومية للأنفاق بيانًا"))

    assert "PRIMARY_DOMAIN_GOVERNMENT" not in evidence.primary_domain_candidates


@pytest.mark.parametrize(
    "body",
    (
        "سجل معدل البطالة تراجعًا مع تحسن سوق العمل",
        "أكد تقرير دولي تسارع نمو الأنشطة غير النفطية والاستثمار",
        "قال صندوق النقد الدولي إن النمو الاقتصادي يواصل التحسن",
    ),
)
def test_macroeconomic_indicators_compose_economy(body: str) -> None:
    """Treat reusable macroeconomic indicators as the primary subject."""
    evidence, _ = compose(make_source(body=body))
    items = [
        item
        for item in evidence.relationships
        if item.relationship_type
        is SemanticRelationshipType.INDICATOR_DESCRIBES_DOMAIN
    ]

    assert items
    assert all(item.subject_component.value == "INDICATOR" for item in items)
    assert all(item.object_component.value == "DOMAIN" for item in items)
    assert all(item.reason_code == "ECONOMIC_INDICATOR_DOMAIN_COMPOSITION" for item in items)
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_ECONOMY",)
    assert "PRIMARY_DOMAIN_GOVERNMENT" not in evidence.primary_domain_candidates


def test_international_trade_negotiation_composes_primary_and_secondary() -> None:
    """Compose interstate negotiation as politics with secondary economy."""
    evidence, _ = compose(
        make_source(
            body=(
                "بدأ مسؤولون من دولتين مفاوضات بشأن الرسوم الجمركية "
                "والقيود التجارية"
            )
        )
    )
    item = next(
        value
        for value in evidence.relationships
        if value.reason_code == "INTERNATIONAL_NEGOTIATION_DOMAIN_COMPOSITION"
    )

    assert item.relationship_type is SemanticRelationshipType.ACTOR_PERFORMS_ACTION
    assert item.strength is EvidenceStrength.STRONG
    assert item.supports == (
        "PRIMARY_DOMAIN_POLITICS",
        "SECONDARY_DOMAIN_ECONOMY",
    )
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_POLITICS",)
    assert evidence.secondary_domain_candidates == ("SECONDARY_DOMAIN_ECONOMY",)


def test_generic_investment_without_economy_context_does_not_compose() -> None:
    """Require economy-wide context for an otherwise generic investment term."""
    evidence, _ = compose(make_source(body="أعلنت شركة الاستثمار في مصنع جديد"))

    assert "PRIMARY_DOMAIN_ECONOMY" not in evidence.primary_domain_candidates


def test_company_negotiation_does_not_create_politics() -> None:
    """Reject ordinary commercial talks without state actors."""
    evidence, _ = compose(
        make_source(body="بدأت شركتان مفاوضات بشأن صفقة تجارية جديدة")
    )

    assert "PRIMARY_DOMAIN_POLITICS" not in evidence.primary_domain_candidates


def test_cybersecurity_recommendation_composes_service_and_action_intent() -> None:
    """Compose expert cybersecurity guidance directed at companies."""
    evidence, _ = compose(
        make_source(
            body=(
                "حذر خبراء الأمن السيبراني الشركات بضرورة تحديث "
                "برامج الحماية"
            )
        )
    )
    item = relationship(
        evidence,
        SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE,
    )

    assert item.reason_code == "RECOMMENDED_ACTION_AUDIENCE_COMPOSITION"
    assert item.strength is EvidenceStrength.STRONG
    assert item.object_text == "الشركات"
    assert item.supports == (
        "PRIMARY_DOMAIN_TECHNOLOGY",
        "FORMAT_SERVICE",
        "INTENT_KNOW_ACTION",
    )
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_TECHNOLOGY",)
    assert evidence.format_support == ("FORMAT_SERVICE",)
    assert evidence.intent_support == ("INTENT_KNOW_ACTION",)


def test_recommendation_requires_actor_audience_and_directive() -> None:
    """Reject generic warnings and guidance without the full action structure."""
    no_audience, _ = compose(
        make_source(body="حذر خبراء الأمن السيبراني من هجمات الفدية")
    )
    no_directive, _ = compose(
        make_source(body="حذر خبراء الأمن السيبراني الشركات من المخاطر")
    )

    for evidence in (no_audience, no_directive):
        assert "FORMAT_SERVICE" not in evidence.format_support
        assert "INTENT_KNOW_ACTION" not in evidence.intent_support
        assert not any(
            item.relationship_type
            is SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE
            for item in evidence.relationships
        )


@pytest.mark.parametrize(
    "body",
    (
        "تسببت الأمطار الموسمية الغزيرة في فيضانات وأعمال إجلاء",
        "أدت أمطار غزيرة إلى سيول مفاجئة وإغلاق الطرق",
        "ضربت عواصف قوية المنطقة وخلفت أضرار العاصفة",
        "اجتاحت فيضانات القرى وأدت إلى إجلاء السكان",
    ),
)
def test_immediate_weather_event_composes_weather(body: str) -> None:
    """Compose immediate weather conditions with hazardous local events."""
    evidence, _ = compose(make_source(body=body))
    item = relationship(evidence, SemanticRelationshipType.EVENT_HAS_OUTCOME)

    assert item.reason_code == "WEATHER_EVENT_DOMAIN_COMPOSITION"
    assert item.strength is EvidenceStrength.STRONG
    assert item.supports == ("PRIMARY_DOMAIN_WEATHER",)
    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_WEATHER",)


def test_scientific_rain_study_does_not_compose_weather_event() -> None:
    """Keep scientific climate research outside immediate weather reporting."""
    evidence, _ = compose(
        make_source(body="نشرت جامعة دراسة علمية عن تغير أنماط هطول الأمطار")
    )

    assert "PRIMARY_DOMAIN_WEATHER" not in evidence.primary_domain_candidates
    assert not any(
        item.relationship_type is SemanticRelationshipType.EVENT_HAS_OUTCOME
        for item in evidence.relationships
    )


def test_new_support_collections_are_deduplicated_in_first_order() -> None:
    """Deduplicate repeated primary, secondary, format, and intent supports."""
    source = make_source(
        title="بدأت واشنطن وبكين مفاوضات بشأن الرسوم الجمركية",
        body=(
            "بدأ مسؤولون من دولتين مفاوضات بشأن القيود التجارية. "
            "حذر خبراء الأمن السيبراني الشركات بضرورة تحديث برامج الحماية. "
            "طالب الخبراء الشركات بضرورة تحديث برامج الحماية"
        ),
    )
    evidence, _ = compose(source)

    assert evidence.primary_domain_candidates == (
        "PRIMARY_DOMAIN_POLITICS",
        "PRIMARY_DOMAIN_TECHNOLOGY",
    )
    assert evidence.secondary_domain_candidates == ("SECONDARY_DOMAIN_ECONOMY",)
    assert evidence.format_support == ("FORMAT_SERVICE",)
    assert evidence.intent_support == ("INTENT_KNOW_ACTION",)


def test_expanded_relationships_preserve_valid_local_provenance() -> None:
    """Reference only real local contextual items when indexes are available."""
    source = make_source(
        body=(
            "قال صندوق النقد إن النمو الاقتصادي تحسن. "
            "حذر خبراء الأمن السيبراني الشركات بضرورة تحديث برامج الحماية. "
            "تسببت الأمطار الموسمية الغزيرة في فيضانات وأعمال إجلاء"
        )
    )
    evidence, contextual = compose(source)

    assert evidence.relationships
    for item in evidence.relationships:
        for index in item.evidence_indexes:
            assert 0 <= index < len(contextual.all_items)
            contextual_item = contextual.all_items[index]
            assert contextual_item.source_section is item.source_section
            assert contextual_item.sentence_index == item.sentence_index


@pytest.mark.parametrize(
    "body",
    (
        "أعلنت وزارة التعليم العالي تحقيق الجامعات مراكز متقدمة في التصنيفات الدولية",
        "أعلنت الهيئة الانتهاء من المشروع بعد تقدم الأعمال",
        "أعلنت وزارة الصحة فحص خمسة ملايين مواطن",
        "أعلن البنك المركزي ارتفاع الاحتياطيات",
    ),
)
def test_non_actionable_institutional_reporting_suppresses_guide(
    body: str,
) -> None:
    """Support standard news and suppress guide for ordinary reporting."""
    evidence, _ = compose(make_source(body=body))

    assert "FORMAT_STANDARD_NEWS" in evidence.format_support
    assert "FORMAT_GUIDE" in evidence.format_suppression


def test_authority_alone_is_insufficient_for_format_suppression() -> None:
    """Require reporting action and status subject beyond an authority name."""
    evidence, _ = compose(make_source(body="وزارة التعليم العالي"))

    assert "FORMAT_STANDARD_NEWS" not in evidence.format_support
    assert "FORMAT_GUIDE" not in evidence.format_suppression


def test_university_ranking_reporting_has_negative_guide_evidence() -> None:
    """Resolve the reusable education ranking scenario as non-actionable news."""
    evidence, _ = compose(
        make_source(
            body=(
                "أعلنت وزارة التعليم العالي والبحث العلمي تحقيق عدد من "
                "الجامعات الحكومية والأهلية مراكز متقدمة في التصنيفات "
                "العالمية للجامعات"
            )
        )
    )

    assert evidence.primary_domain_candidates == ("PRIMARY_DOMAIN_EDUCATION",)
    assert evidence.format_support == ("FORMAT_STANDARD_NEWS",)
    assert evidence.format_suppression == ("FORMAT_GUIDE",)


@pytest.mark.parametrize(
    "body",
    (
        "تعرف على شروط القبول بالجامعات والمستندات المطلوبة",
        "تغلق الوزارة باب التسجيل يوم الأحد",
        "يمكن للطلاب تسجيل الرغبات عبر الموقع",
        "تشمل المتطلبات صورة الهوية ورسوم التسجيل",
        "توضح الوزارة أهلية الطلاب وطريقة التقديم",
    ),
)
def test_actionable_guide_structure_prevents_suppression(body: str) -> None:
    """Preserve guide capability for requirements, deadlines, and procedures."""
    evidence, _ = compose(make_source(body=body))

    assert "FORMAT_GUIDE" not in evidence.format_suppression


def test_cybersecurity_recommendation_remains_service_capable() -> None:
    """Preserve semantic SERVICE support without adding GUIDE suppression."""
    evidence, _ = compose(
        make_source(
            body=(
                "حذر خبراء الأمن السيبراني الشركات بضرورة تحديث "
                "برامج الحماية"
            )
        )
    )

    assert evidence.format_support == ("FORMAT_SERVICE",)
    assert evidence.intent_support == ("INTENT_KNOW_ACTION",)
    assert "FORMAT_GUIDE" not in evidence.format_suppression


def test_format_support_and_suppression_remain_deduplicated() -> None:
    """Deduplicate repeated institutional reporting across source sections."""
    source = make_source(
        title="أعلنت الوزارة تقدم الجامعات في التصنيفات الدولية",
        body="أعلنت الوزارة تقدم الجامعات في التصنيفات الدولية",
    )
    evidence, _ = compose(source)

    assert evidence.format_support == ("FORMAT_STANDARD_NEWS",)
    assert evidence.format_suppression == ("FORMAT_GUIDE",)
