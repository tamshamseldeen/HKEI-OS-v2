"""Tests for deterministic primary topic classification."""

from dataclasses import replace

import pytest

from examples.run_benchmark_batch_01_analysis import BATCH_ROOT, parse_source, read_manifest
from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_risk_assessment_engine import SourceRiskAssessmentEngine
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import ContentTypeClassification
from src.classification.deterministic_content_type_classifier import (
    DeterministicContentTypeClassifier,
)
from src.facts.deterministic_fact_extractor import DeterministicFactExtractor
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource
from src.topic.deterministic_topic_classifier import DeterministicTopicClassifier
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence


def make_source(
    *,
    title: str = "عنوان عام",
    body: str = "مادة عامة بلا تفاصيل كافية",
    category: str | None = None,
    tags: tuple[str, ...] = (),
) -> NormalizedSource:
    """Create normalized source material for topic tests."""
    return NormalizedSource(
        title=title,
        body=body,
        source_name="Source",
        source_url="https://example.com",
        category=category,
        tags=tags,
    )


def make_facts(**changes: object) -> ExtractedFacts:
    """Create extracted facts with configurable topic signals."""
    facts = ExtractedFacts(
        core_facts=(),
        claims=(),
        quotes=(),
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=(),
        times=(),
        numbers=(),
        percentages=(),
        currencies=(),
        laws_and_regulations=(),
        products=(),
        events=(),
        unknown_information=(),
        attributions=(),
    )
    return replace(facts, **changes)


def make_assessment(
    *,
    risk_topics: tuple[str, ...] = (),
) -> SourceRiskAssessment:
    """Create an independent low-risk assessment."""
    return SourceRiskAssessment(
        source_status=SourceStatus.IDENTIFIED,
        verification_status=VerificationStatus.SOURCE_PROVIDED,
        risk_level=RiskLevel.LOW,
        risk_topics=risk_topics,
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
        generation_allowed=True,
        reason_codes=("SOURCE_OK",),
    )


def make_content(
    content_type: ContentType = ContentType.STANDARD_NEWS,
    confidence: ClassificationConfidence = ClassificationConfidence.MEDIUM,
) -> ContentTypeClassification:
    """Create transitional legacy content classification."""
    return ContentTypeClassification(content_type, confidence, (), (), ())


def classify(
    *,
    source: NormalizedSource | None = None,
    facts: ExtractedFacts | None = None,
    assessment: SourceRiskAssessment | None = None,
    content: ContentTypeClassification | None = None,
    user_instruction: str | None = None,
) -> TopicClassification:
    """Classify convenient deterministic defaults."""
    return DeterministicTopicClassifier().classify(
        source=source or make_source(),
        facts=facts or make_facts(),
        assessment=assessment or make_assessment(),
        content_classification=content or make_content(),
        user_instruction=user_instruction,
    )


@pytest.mark.parametrize(
    ("category", "expected"),
    (
        ("economy", Topic.ECONOMY),
        ("technology", Topic.TECHNOLOGY),
        ("sports", Topic.SPORTS),
        ("government", Topic.GOVERNMENT),
        ("weather", Topic.WEATHER),
        ("health", Topic.HEALTH),
        ("culture", Topic.CULTURE),
        ("science", Topic.SCIENCE),
        ("education", Topic.EDUCATION),
        ("crime", Topic.CRIME),
        ("entertainment", Topic.ENTERTAINMENT),
        ("politics", Topic.POLITICS),
        ("business", Topic.BUSINESS),
    ),
)
def test_exact_category_mapping_is_strong(category: str, expected: Topic) -> None:
    """Map every supported source category with high confidence."""
    result = classify(source=make_source(category=category))

    assert result.topic is expected
    assert result.confidence is TopicConfidence.HIGH
    assert result.reason_codes[0] == "SOURCE_CATEGORY_TOPIC_MATCH"
    assert result.supporting_signals[0] == f"CATEGORY_{expected.value}"


@pytest.mark.parametrize(
    ("title", "body", "expected"),
    (
        (
            "البنك المركزي يثبت أسعار الفائدة",
            "يراقب البنك التضخم والأسواق",
            Topic.ECONOMY,
        ),
        (
            "أوبك+ تمدد تخفيضات إنتاج النفط",
            "القرار يدعم استقرار الأسواق العالمية",
            Topic.ECONOMY,
        ),
        (
            "الذكاء الاصطناعي يدفع أشباه الموصلات لمستويات جديدة",
            "يتوسع الطلب على مراكز البيانات والتكنولوجيا",
            Topic.TECHNOLOGY,
        ),
        (
            "موجة حر ترفع درجات الحرارة",
            "تحذير من الجفاف والرياح",
            Topic.WEATHER,
        ),
        (
            "وزارة النقل تعلن تقدم مترو الأنفاق",
            "المشروع بنية تحتية وخدمة حكومية",
            Topic.GOVERNMENT,
        ),
        (
            "الإيرادات السياحية تسجل نموًا",
            "ارتفعت الأسواق وإيرادات القطاع السياحي",
            Topic.ECONOMY,
        ),
        (
            "الشحن البحري يرفع التكاليف",
            "تأثرت التجارة والأسواق",
            Topic.ECONOMY,
        ),
        (
            "اكتشاف أثري يكشف مقابر جديدة",
            "يعرض متحف آثار الموقع وتراثه",
            Topic.CULTURE,
        ),
        (
            "المنتخب ينهي تدريباته قبل المباراة",
            "يستعد اللاعبون لبطولة كأس جديدة",
            Topic.SPORTS,
        ),
        (
            "أسعار الذهب تنتظر بيانات التضخم",
            "تترقب الأسواق قرار أسعار الفائدة",
            Topic.ECONOMY,
        ),
        (
            "شركة تعلن استحواذًا جديدًا",
            "وافق مجلس إدارة الشركة على الصفقة التجارية",
            Topic.BUSINESS,
        ),
    ),
)
def test_strong_title_and_body_scenarios(
    title: str,
    body: str,
    expected: Topic,
) -> None:
    """Classify representative subject matter without source categories."""
    result = classify(source=make_source(title=title, body=body))

    assert result.topic is expected
    assert result.confidence in (TopicConfidence.HIGH, TopicConfidence.MEDIUM)


def test_technology_financial_metrics_remain_technology() -> None:
    """Keep technology central when financial figures describe its industry."""
    source = make_source(
        title="الذكاء الاصطناعي يرفع شركات أشباه الموصلات",
        body="ارتفعت القيمة السوقية بنسبة 25% مع توسع مراكز البيانات",
    )
    result = classify(
        source=source,
        facts=make_facts(percentages=("25%",), numbers=("25",)),
        assessment=make_assessment(risk_topics=("financial",)),
    )

    assert result.topic is Topic.TECHNOLOGY


def test_government_entity_does_not_override_economy() -> None:
    """Keep a central-bank macroeconomic decision in ECONOMY."""
    result = classify(
        source=make_source(
            title="البنك المركزي يثبت أسعار الفائدة",
            body="يتابع التضخم واستقرار الأسواق",
        ),
        facts=make_facts(government_entities=("البنك المركزي",)),
    )

    assert result.topic is Topic.ECONOMY
    assert "GOVERNMENT_ENTITY_SIGNAL" not in result.reason_codes


def test_government_entity_supports_infrastructure_topic() -> None:
    """Combine a public entity with central infrastructure evidence."""
    result = classify(
        source=make_source(
            title="تقدم بنية تحتية جديدة",
            body="أعلنت الجهة تقدم المشروع",
        ),
        facts=make_facts(government_entities=("وزارة النقل",)),
    )

    assert result.topic is Topic.GOVERNMENT
    assert "GOVERNMENT_ENTITY_SIGNAL" in result.reason_codes


def test_sports_metaphor_does_not_create_sports_topic() -> None:
    """Reject weak sports words used in non-sports corporate language."""
    result = classify(
        source=make_source(
            title="فريق الشركة يحقق هدف النمو",
            body="تسعى الشركة إلى نتيجة أفضل وفوز تجاري",
        )
    )

    assert result.topic is not Topic.SPORTS


def test_sports_training_context_creates_sports_topic() -> None:
    """Recognize genuine national-team training and match context."""
    result = classify(
        source=make_source(
            title="تدريبات المنتخب قبل المباراة",
            body="يستعد اللاعب لخوض البطولة",
        )
    )

    assert result.topic is Topic.SPORTS


@pytest.mark.parametrize(
    "text",
    (
        "تستهدف هذه الخطوة حماية المستثمرين",
        "أبدى ممثلو عدد من الدول",
        "يعتمد العمل على تمثيل دقيق",
    ),
)
def test_larger_arabic_tokens_do_not_create_topic_matches(text: str) -> None:
    """Reject topic terms embedded inside longer Arabic tokens."""
    matches = DeterministicTopicClassifier._matches_by_topic(text)

    assert "هدف" not in matches.get(Topic.SPORTS, ())
    assert "ممثل" not in matches.get(Topic.ENTERTAINMENT, ())


def test_standalone_goal_matches_with_genuine_sports_context() -> None:
    """Keep standalone weak sports terms when strong sports evidence exists."""
    result = classify(
        source=make_source(
            title="مباراة حاسمة",
            body="سجل اللاعب هدف، ثم حقق الفوز",
        )
    )

    assert result.topic is Topic.SPORTS
    assert "هدف" in DeterministicTopicClassifier._matches_by_topic(
        "سجل هدف"
    )[Topic.SPORTS]


def test_weak_team_alone_does_not_create_sports() -> None:
    """Prevent a generic team reference from establishing SPORTS."""
    result = classify(
        source=make_source(
            title="أعلن فريق دولي بيانًا",
            body="تضمن البيان معلومات جديدة",
        )
    )

    assert result.topic is Topic.GENERAL


def test_scientist_team_is_science_not_sports() -> None:
    """Let strong astronomy evidence beat the generic word for team."""
    result = classify(
        source=make_source(
            title="اكتشاف جديد",
            body="أعلن فريق دولي من علماء الفلك اكتشاف كوكب",
        ),
        content=make_content(ContentType.SPORTS_NEWS),
    )

    assert result.topic is Topic.SCIENCE
    assert "LEGACY_CONTENT_TYPE_TOPIC_SIGNAL" not in result.reason_codes


def test_legacy_sports_does_not_reinforce_accidental_or_weak_evidence() -> None:
    """Require a genuine strong sports term before transitional reinforcement."""
    result = classify(
        source=make_source(
            title="خطوة جديدة",
            body="تستهدف هذه الخطوة حماية المستثمرين عبر فريق دولي",
        ),
        content=make_content(ContentType.SPORTS_NEWS),
    )

    assert result.topic is not Topic.SPORTS
    assert "LEGACY_CONTENT_TYPE_TOPIC_SIGNAL" not in result.reason_codes


def test_reliable_legacy_sports_may_reinforce_genuine_evidence() -> None:
    """Retain transitional support when an independent strong term agrees."""
    result = classify(
        source=make_source(
            title="مباراة اليوم",
            body="استعدادات جديدة قبل اللقاء",
        ),
        content=make_content(ContentType.SPORTS_NEWS),
    )

    assert result.topic is Topic.SPORTS
    assert "LEGACY_CONTENT_TYPE_TOPIC_SIGNAL" in result.reason_codes


@pytest.mark.parametrize(
    ("title", "body", "expected"),
    (
        ("العملات المشفرة", "تحديث جديد", Topic.ECONOMY),
        ("الأصول الرقمية", "تحديث جديد", Topic.ECONOMY),
        ("النظام المالي", "تحديث جديد", Topic.ECONOMY),
        ("معرض الكتاب", "تبدأ الاستعدادات", Topic.CULTURE),
        ("هيئة الكتاب", "تعلن ترتيبات جديدة", Topic.CULTURE),
        ("علماء الفلك", "أعلنوا اكتشافًا", Topic.SCIENCE),
        ("كوكب جديد", "أعلن العلماء اكتشافه", Topic.SCIENCE),
        ("مرصد جديد", "نشر بيانات أولية", Topic.SCIENCE),
        ("وكالة الفضاء", "بيانات جديدة", Topic.SCIENCE),
        ("توقعات جديدة", "صافي أرباح مرتفع", Topic.BUSINESS),
        ("الفاتورة الإلكترونية", "تحديث جديد", Topic.GOVERNMENT),
        ("مصلحة الضرائب", "أعلنت قرارًا", Topic.GOVERNMENT),
        ("البطاريات الصلبة", "تطور جديد", Topic.TECHNOLOGY),
        ("أشباه الموصلات", "توسع جديد", Topic.TECHNOLOGY),
        ("مؤتمر الأمم المتحدة", "اتفقت الدول المشاركة", Topic.WORLD),
    ),
)
def test_general_reusable_vocabulary_supports_topics(
    title: str,
    body: str,
    expected: Topic,
) -> None:
    """Classify reusable science, culture, economy, world, and service terms."""
    assert classify(source=make_source(title=title, body=body)).topic is expected


def test_weak_companies_do_not_beat_strong_technology() -> None:
    """Keep technology primary when generic companies describe its industry."""
    result = classify(
        source=make_source(
            title="شركات السيارات الكهربائية تعتمد البطاريات الصلبة",
            body="تتوسع تقنيات أشباه الموصلات",
        )
    )

    assert result.topic is Topic.TECHNOLOGY


def test_weak_ministry_does_not_override_strong_economy() -> None:
    """Keep macroeconomic evidence primary over one generic ministry mention."""
    result = classify(
        source=make_source(
            title="وزارة تتابع البنك المركزي وأسعار الفائدة",
            body="يراقب القرار التضخم والأسواق",
        )
    )

    assert result.topic is Topic.ECONOMY


def test_number_alone_does_not_create_economy() -> None:
    """Ignore an isolated structured number without market terminology."""
    result = classify(facts=make_facts(numbers=("100",)))

    assert result.topic is Topic.GENERAL


def test_currency_and_market_terminology_support_economy() -> None:
    """Combine a currency fact with explicit market terminology."""
    result = classify(
        source=make_source(title="تحديث الأسواق", body="تغيرت الأسعار اليوم"),
        facts=make_facts(currencies=("100 USD",)),
    )

    assert result.topic is Topic.ECONOMY
    assert "ECONOMIC_STRUCTURE_SIGNAL" in result.reason_codes
    assert "STRUCTURED_ECONOMIC_VALUES" in result.supporting_signals


@pytest.mark.parametrize(
    "content_type",
    (
        ContentType.SPORTS_NEWS,
        ContentType.TECHNOLOGY_NEWS,
        ContentType.ECONOMY_NEWS,
    ),
)
def test_legacy_topic_values_cannot_establish_topic_alone(
    content_type: ContentType,
) -> None:
    """Prevent mapped legacy values from establishing a primary topic."""
    result = classify(content=make_content(content_type))

    assert result.topic is Topic.GENERAL
    assert "LEGACY_CONTENT_TYPE_TOPIC_SIGNAL" not in result.reason_codes


def test_low_confidence_legacy_value_does_not_determine_topic_alone() -> None:
    """Require independent support when transitional legacy confidence is low."""
    result = classify(
        content=make_content(
            ContentType.SPORTS_NEWS,
            ClassificationConfidence.LOW,
        )
    )

    assert result.topic is Topic.GENERAL


@pytest.mark.parametrize(
    "content_type",
    (
        ContentType.BREAKING_NEWS,
        ContentType.STANDARD_NEWS,
        ContentType.NEWS_REWRITE,
        ContentType.PUBLIC_SERVICE_NEWS,
        ContentType.EXPLAINER,
        ContentType.FACT_CHECK,
        ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
        ContentType.TRENDING_SOCIAL_CLAIM,
    ),
)
def test_mixed_legacy_values_do_not_force_topic(content_type: ContentType) -> None:
    """Keep mixed editorial-treatment values out of topic selection."""
    assert classify(content=make_content(content_type)).topic is Topic.GENERAL


def test_category_title_conflict_is_resolved_by_strong_title() -> None:
    """Override contradictory category with a strong central title subject."""
    result = classify(
        source=make_source(
            category="sports",
            title="البنك المركزي يغير أسعار الفائدة",
            body="يراقب التضخم والأسواق",
        )
    )

    assert result.topic is Topic.ECONOMY
    assert result.confidence is TopicConfidence.MEDIUM
    assert "CATEGORY_TOPIC_CONFLICT" in result.warnings
    assert "TOPIC_CONFLICT_RESOLVED" in result.reason_codes


def test_conflicting_non_category_signals_add_warning() -> None:
    """Choose headline-led weather while warning about strong science overlap."""
    result = classify(
        source=make_source(
            title="موجة حر ودرجات الحرارة في دراسة علمية",
            body="باحثون يناقشون الجفاف وأبحاث المناخ",
        )
    )

    assert result.topic is Topic.WEATHER
    assert result.confidence is TopicConfidence.MEDIUM
    assert "CONFLICTING_TOPIC_SIGNALS" in result.warnings


def test_general_fallback_has_exact_low_confidence_output() -> None:
    """Return stable safe fallback when topic evidence is insufficient."""
    result = classify()

    assert result == TopicClassification(
        topic=Topic.GENERAL,
        confidence=TopicConfidence.LOW,
        reason_codes=("DEFAULT_GENERAL_TOPIC",),
        supporting_signals=("INSUFFICIENT_TOPIC_EVIDENCE",),
        warnings=("LOW_TOPIC_CONFIDENCE", "TOPIC_SIGNAL_INSUFFICIENT"),
    )


def test_output_collections_are_deduplicated() -> None:
    """Expose each stable reason, signal, and warning at most once."""
    result = classify(
        source=make_source(
            category="technology",
            title="تقنية تكنولوجيا وذكاء اصطناعي",
            body="تقنية وذكاء اصطناعي في مراكز البيانات",
            tags=("الذكاء الاصطناعي", "الذكاء الاصطناعي"),
        ),
        content=make_content(ContentType.TECHNOLOGY_NEWS),
    )

    assert len(result.reason_codes) == len(set(result.reason_codes))
    assert len(result.supporting_signals) == len(set(result.supporting_signals))
    assert len(result.warnings) == len(set(result.warnings))


def test_inputs_remain_unchanged_and_results_are_deterministic() -> None:
    """Avoid input mutation and return equal single objects for equal input."""
    source = make_source(
        title="أسعار الذهب في الأسواق",
        body="تتابع التجارة أسعار الفائدة",
        tags=("اقتصاد",),
    )
    facts = make_facts(currencies=("100 USD",))
    assessment = make_assessment(risk_topics=("financial",))
    content = make_content(ContentType.ECONOMY_NEWS)
    snapshots = (source, facts, assessment, content)

    first = classify(
        source=source,
        facts=facts,
        assessment=assessment,
        content=content,
        user_instruction="ركز على الأثر الاقتصادي",
    )
    second = classify(
        source=source,
        facts=facts,
        assessment=assessment,
        content=content,
        user_instruction="ركز على الأثر الاقتصادي",
    )

    assert isinstance(first, TopicClassification)
    assert first == second
    assert first is not second
    assert (source, facts, assessment, content) == snapshots


def test_all_batch_01_expected_topics() -> None:
    """Classify every persisted Batch 01 source without fixture-specific rules."""
    expected_topics = (
        Topic.ECONOMY,
        Topic.ECONOMY,
        Topic.TECHNOLOGY,
        Topic.WEATHER,
        Topic.GOVERNMENT,
        Topic.ECONOMY,
        Topic.ECONOMY,
        Topic.CULTURE,
        Topic.SPORTS,
        Topic.ECONOMY,
    )

    actual: list[Topic] = []
    for manifest_case in read_manifest():
        benchmark_source = parse_source(BATCH_ROOT / manifest_case["source_file"])
        source = NormalizedSource(
            title=benchmark_source.title,
            body=benchmark_source.body,
            source_name=benchmark_source.source_name,
            source_url=benchmark_source.source_url,
            language="ar",
            category=benchmark_source.benchmark_category,
        )
        assessment = SourceRiskAssessmentEngine().assess(source)
        facts = DeterministicFactExtractor().extract(source)
        content = DeterministicContentTypeClassifier().classify(
            source=source,
            assessment=assessment,
            facts=facts,
            user_instruction=None,
        )
        actual.append(
            classify(
                source=source,
                facts=facts,
                assessment=assessment,
                content=content,
            ).topic
        )

    assert tuple(actual) == expected_topics
