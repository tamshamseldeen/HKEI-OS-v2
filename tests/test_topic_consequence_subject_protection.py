"""Generic raw-Arabic tests for primary-subject/consequence Topic separation."""

from pathlib import Path

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.intake.normalized_source import NormalizedSource
from src.resolution.topic_authority_runtime_config import TopicAuthorityRuntimeConfig
from src.resolution.resolver_authority_mode import ResolverAuthorityMode
from src.semantics.deterministic_compositional_semantic_engine import DeterministicCompositionalSemanticEngine
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor
from src.semantics.semantic_evidence_sufficiency import SemanticEvidenceSufficiency
from src.semantics.semantic_relationship_type import SemanticRelationshipType
from src.semantics.compositional_semantic_evidence import CompositionalSemanticEvidence
from src.semantics.topic_consequence_subject_protection import TopicConsequenceSubjectProtector


EMPTY_CONTEXT = ContextualEvidence((), (), (), (), (), ())


def analyze(title: str, body: str):
    source = NormalizedSource(title, body, "generic-fixture", language="ar")
    relationships = TopicConsequenceSubjectProtector().compose(source)
    evidence = CompositionalSemanticEvidence(
        relationships=relationships,
        primary_domain_candidates=tuple(dict.fromkeys(
            support for relationship in relationships for support in relationship.supports
            if support.startswith("PRIMARY_DOMAIN_")
        )),
        secondary_domain_candidates=tuple(dict.fromkeys(
            support for relationship in relationships for support in relationship.supports
            if support.startswith("SECONDARY_DOMAIN_")
        )),
        format_support=(), format_suppression=(), intent_support=(),
        warnings=(),
    )
    assessments = {
        item.candidate: item
        for item in DeterministicSemanticCandidateAssessor().assess(
            semantic_evidence=evidence
        )
    }
    return evidence, assessments


# Every sentence is newly authored for HKEI-216. Consequences span legal Topic
# boundaries and avoid benchmark/canary wording.
PROTECTED = (
    ("الشرطة تحقق في احتيال إلكتروني", "تواصل الشرطة تحقيقها في المخالفة القانونية. وأدى ذلك إلى إصابات صحية محدودة.", "CRIME", "HEALTH"),
    ("البرلمان يناقش سياسة الإسكان", "تركز الجلسة على السياسة الجديدة. ومن تداعيات ذلك ارتفاع أسعار بعض الخدمات.", "POLITICS", "ECONOMY"),
    ("الاقتصاد يسجل نموا جديدا", "يتناول التقرير النمو الاقتصادي. وينعكس ذلك على شؤون عامة في المدن.", "ECONOMY", "GENERAL"),
    ("منصة رقمية تطلق برمجيات جديدة", "تشرح المنصة الرقمية التقنية المطورة. وتسبب ذلك في زيادة مبيعات الشركة.", "TECHNOLOGY", "BUSINESS"),
    ("عاصفة قوية تضرب الساحل", "تستمر الرياح والعاصفة طوال المساء. مما أدى إلى إصابات بين السكان.", "WEATHER", "HEALTH"),
    ("قرار حكومي بشأن المرافق العامة", "يعرض القرار الإداري تنظيم المرفق العام. ومن آثار ذلك تعديل مناهج التعليم.", "GOVERNMENT", "EDUCATION"),
    ("الفريق يستعد لمباراة الدوري", "يخوض الفريق مباراة حاسمة. وتسبب ذلك في ارتفاع مبيعات النادي.", "SPORTS", "BUSINESS"),
    ("اعتقال متهم بعد تحقيق جنائي", "أعلنت الشرطة استمرار التحقيق الجنائي. وسط مخاطر صحية على بعض المتضررين.", "CRIME", "HEALTH"),
    ("انتخابات البرلمان محور النقاش", "تتابع الأحزاب الانتخابات والبرلمان. ما يؤدي إلى تقلبات اقتصادية مؤقتة.", "POLITICS", "ECONOMY"),
    ("أسعار السوق تتراجع", "يرصد التقرير أسعار السوق والتضخم. ومن تداعيات ذلك جدل سياسي محدود.", "ECONOMY", "POLITICS"),
    ("تكنولوجيا جديدة لحماية البيانات", "تظل التقنية والمنصة الرقمية موضوع التقرير. وتسبب ذلك في أرباح إضافية للشركات.", "TECHNOLOGY", "BUSINESS"),
    ("موجة حر متواصلة", "تشرح النشرة موجة الحر ودرجات الحرارة. ما قد يؤدي إلى مرض عابر لدى بعض الأشخاص.", "WEATHER", "HEALTH"),
    ("الجامعة تبدأ العام التعليمي", "ينظم التعليم والطلاب معالجة الخبر. وينعكس ذلك على قرار حكومي لاحق.", "EDUCATION", "GOVERNMENT"),
    ("بطولة الأندية تنطلق غدا", "تغطي المادة البطولة ومنافسات الأندية. ومن آثار ذلك نمو استثمار تجاري محلي.", "SPORTS", "BUSINESS"),
)

LEGITIMATE = (
    ("الصحة تواجه وباء جديدا", "تتابع المستشفيات الوباء والعلاج. وأدى إغلاق طريق إلى تعقيد الاستجابة.", "HEALTH"),
    ("التضخم وآثاره محور تحليل اقتصادي", "يفسر التحليل التضخم وأسعار السوق. مما أدى إلى جدل سياسي محدود.", "ECONOMY"),
    ("الانتخابات تعيد تشكيل السياسة", "يناقش التقرير الأحزاب والبرلمان والانتخابات. مما أدى إلى تغير محدود في الأسواق.", "POLITICS"),
    ("إصابات صحية بعد موجة الحر", "يركز التقرير على الإصابات والعلاج في المستشفى. مما أدى إلى نقاش بشأن درجات الحرارة.", "HEALTH"),
    ("أرباح الشركات تقود نشاط الأعمال", "تتناول المادة الشركات والأرباح والمبيعات. مما أدى إلى استخدام تقنية حديثة.", "BUSINESS"),
    ("الطلاب يعودون إلى المدارس", "يتابع الخبر التعليم والمدارس والطلاب. مما أدى إلى قرار حكومي لتنظيم العودة.", "EDUCATION"),
    ("مباراة البطولة تحسم لقب الدوري", "يعرض التقرير المباراة والفريق والبطولة. مما أدى إلى ارتفاع المبيعات بعد الفوز.", "SPORTS"),
    ("المنصة الرقمية تغير استخدام البرمجيات", "تشرح المادة التكنولوجيا والبرمجيات والمنصة الرقمية. مما أدى إلى استفادة شركات عدة.", "TECHNOLOGY"),
)

AMBIGUOUS = (
    ("السياسة والاقتصاد في قلب قرار البرلمان", "يناقش البرلمان السياسة والاقتصاد معا دون ترجيح أحدهما.", {"POLITICS", "ECONOMY"}),
    ("التكنولوجيا وأعمال الشركات في منصة مشتركة", "تعرض المادة التقنية والشركات باعتبارهما محورين متساويين.", {"TECHNOLOGY", "BUSINESS"}),
    ("الطقس والصحة في مواجهة موجة الحر", "تتابع النشرة درجات الحرارة والصحة والإصابات بالتساوي.", {"WEATHER", "HEALTH"}),
    ("الحكومة والتعليم يراجعان المناهج", "يتناول الخبر القرار الحكومي والتعليم والمدارس كموضوعين مركزيين.", {"GOVERNMENT", "EDUCATION"}),
    ("الرياضة والأعمال التجارية وراء توسع النادي", "يرصد التقرير الفريق والمبيعات والرياضة والشركات دون محور منفرد.", {"SPORTS", "BUSINESS"}),
    ("الجريمة والصحة بعد حادث عام", "يناقش التحقيق الجنائي والصحة والإصابات بوصفهما مسارين رئيسيين.", {"CRIME", "HEALTH"}),
    ("الثقافة والتعليم في مشروع المتحف", "يعالج الخبر المتحف والتراث والتعليم والطلاب على قدم المساواة.", {"CULTURE", "EDUCATION"}),
    ("العلم والتكنولوجيا يقودان الاكتشاف", "يتابع الباحثون الدراسة العلمية والتقنية كموضوعين متكاملين.", {"SCIENCE", "TECHNOLOGY"}),
)


@pytest.mark.parametrize("title,body,primary,consequence", PROTECTED)
def test_primary_subject_outweighs_consequence_only_domain(title, body, primary, consequence):
    evidence, assessments = analyze(title, body)
    assert f"PRIMARY_DOMAIN_{primary}" in evidence.primary_domain_candidates
    assert f"SECONDARY_DOMAIN_{consequence}" in evidence.secondary_domain_candidates
    assert assessments[consequence].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT
    assert "CONSEQUENCE_ONLY_SUPPORT" in assessments[consequence].warnings
    assert assessments[primary].sufficiency in {
        SemanticEvidenceSufficiency.SUFFICIENT,
        SemanticEvidenceSufficiency.PARTIAL,
    }


@pytest.mark.parametrize("title,body,primary", LEGITIMATE)
def test_legitimate_consequence_like_domain_remains_primary(title, body, primary):
    evidence, assessments = analyze(title, body)
    assert f"PRIMARY_DOMAIN_{primary}" in evidence.primary_domain_candidates
    assert "CONSEQUENCE_ONLY_SUPPORT" not in assessments[primary].warnings
    assert assessments[primary].sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


@pytest.mark.parametrize("title,body,domains", AMBIGUOUS)
def test_dual_central_domains_preserve_competition(title, body, domains):
    _, assessments = analyze(title, body)
    assert domains <= assessments.keys()
    for domain in domains:
        assert assessments[domain].sufficiency is SemanticEvidenceSufficiency.PARTIAL
        assert set(assessments[domain].competing_candidates) & (domains - {domain})


def test_consequence_relationship_uses_existing_provider_neutral_contract():
    evidence, _ = analyze(*PROTECTED[0][:2])
    item = next(
        relation for relation in evidence.relationships
        if relation.relationship_type is SemanticRelationshipType.CONSEQUENCE_OF_EVENT
    )
    assert item.supports == ("SECONDARY_DOMAIN_HEALTH",)
    assert item.suppresses == ()


def test_production_engine_integrates_only_noncentral_consequence_role():
    source = NormalizedSource(
        "عاصفة قوية تضرب الساحل",
        "تستمر العاصفة مساء. مما أدى إلى إصابات صحية محدودة.",
        "generic-fixture",
        language="ar",
    )
    evidence = DeterministicCompositionalSemanticEngine().compose(
        source=source, contextual_evidence=EMPTY_CONTEXT
    )
    assert "SECONDARY_DOMAIN_HEALTH" in evidence.secondary_domain_candidates
    assert "PRIMARY_DOMAIN_WEATHER" not in evidence.primary_domain_candidates


def test_repeated_consequence_does_not_become_primary_without_central_evidence():
    _, assessments = analyze(
        "عاصفة تضرب الإقليم",
        "تستمر العاصفة. مما أدى إلى إصابات. ومن تداعيات ذلك مرض. ومن آثار ذلك مخاطر صحية.",
    )
    assert assessments["HEALTH"].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


def test_independent_central_evidence_can_promote_a_domain_also_seen_as_consequence():
    _, assessments = analyze(
        "الصحة وموجة الحر محور المتابعة",
        "تتابع المستشفيات الصحة والعلاج. وتسببت العاصفة في إصابات صحية.",
    )
    assert assessments["HEALTH"].sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_elliptical_headline_uses_lead_centrality_without_promoting_consequence():
    evidence, assessments = analyze(
        "تطور جديد...",
        "تواصل الشرطة التحقيق الجنائي في المخالفة القانونية. مما أدى إلى مخاطر صحية محدودة.",
    )
    assert "PRIMARY_DOMAIN_CRIME" in evidence.primary_domain_candidates
    assert assessments["HEALTH"].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


def test_passive_arabic_consequence_form_remains_secondary():
    evidence, assessments = analyze(
        "قرار سياسي محور جلسة البرلمان",
        "نوقشت السياسة في الجلسة. وانعكس ذلك على أسعار السوق.",
    )
    assert "SECONDARY_DOMAIN_ECONOMY" in evidence.secondary_domain_candidates
    assert assessments["ECONOMY"].sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


def test_existing_authority_actor_and_method_models_are_unchanged():
    source = Path("src/semantics/semantic_component.py").read_text(encoding="utf-8")
    assert 'AUTHORITY = "AUTHORITY"' in source
    assert 'ACTOR = "ACTOR"' in source
    assert 'METHOD = "METHOD"' in source


def test_frozen_downstream_contracts_are_not_modified_by_implementation():
    changed_source = Path("src/semantics/topic_consequence_subject_protection.py").read_text(encoding="utf-8")
    assert "Gate" not in changed_source
    assert "Resolver" not in changed_source
    assert "Provider" not in changed_source
    assert "adjudicate" not in changed_source


def test_pilot_remains_shadow_and_no_canary_continuation_is_encoded():
    assert TopicAuthorityRuntimeConfig().resolve() is ResolverAuthorityMode.SHADOW
    assert "CANARY-003" not in Path("src/semantics/topic_consequence_subject_protection.py").read_text(encoding="utf-8")
