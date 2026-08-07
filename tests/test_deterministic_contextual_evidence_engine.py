"""Tests for deterministic contextual editorial evidence analysis."""

from dataclasses import fields

import pytest

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.evidence.evidence_level import EvidenceLevel
from src.evidence.evidence_role import EvidenceRole
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource


def make_source(
    *,
    title: str = "عنوان بلا إشارات",
    body: str = "محتوى بلا إشارات",
) -> NormalizedSource:
    """Create one normalized source for evidence tests."""
    return NormalizedSource(
        title=title,
        body=body,
        source_name="Source",
        source_url="https://example.com",
        language="ar",
    )


def analyze(
    *,
    title: str = "عنوان بلا إشارات",
    body: str = "محتوى بلا إشارات",
    user_instruction: str | None = None,
):
    """Analyze convenient source defaults."""
    return DeterministicContextualEvidenceEngine().analyze(
        source=make_source(title=title, body=body),
        user_instruction=user_instruction,
    )


@pytest.mark.parametrize("boundary", (".", "؟", "!", "؛", "\n"))
def test_sentence_segmentation_supports_every_boundary(boundary: str) -> None:
    """Split body sentences at every supported Latin and Arabic boundary."""
    segments = DeterministicContextualEvidenceEngine._segment_sentences(
        f"الجملة الأولى{boundary}الجملة الثانية"
    )

    assert segments == ("الجملة الأولى", "الجملة الثانية")


def test_sentence_segmentation_ignores_empty_segments() -> None:
    """Ignore repeated boundaries and whitespace-only bounded segments."""
    segments = DeterministicContextualEvidenceEngine._segment_sentences(
        "  .؟\nالجملة الأولى!! ؛ الجملة الثانية. "
    )

    assert segments == ("الجملة الأولى", "الجملة الثانية")


def test_headline_lead_and_body_provenance_and_indices() -> None:
    """Assign headline, first body sentence, and remaining body provenance."""
    evidence = analyze(
        title="أعلنت وزارة النقل مشروعًا",
        body=(
            "قال مسؤول إن البنك المركزي أصدر بيانًا. "
            "أوضح التقرير أن معرض الكتاب بدأ! "
            "ذكرت الوكالة أن أشباه الموصلات تتوسع"
        ),
    )

    assert evidence.headline_items
    assert all(
        item.source_section is SourceSection.HEADLINE
        and item.sentence_index == 0
        for item in evidence.headline_items
    )
    assert evidence.lead_items
    assert all(
        item.source_section is SourceSection.LEAD and item.sentence_index == 0
        for item in evidence.lead_items
    )
    assert {item.sentence_index for item in evidence.body_items} == {0, 1}
    assert all(item.source_section is SourceSection.BODY for item in evidence.body_items)


def test_phrase_matching_preserves_exact_supplied_text() -> None:
    """Match normalized phrase separators while preserving original match text."""
    evidence = analyze(title="علماء، الفلك يعلنون اكتشافًا")
    science = next(
        item
        for item in evidence.headline_items
        if item.reason_code == "SCIENCE_CONTEXT_PHRASE"
    )

    assert science.matched_text == "علماء، الفلك"
    assert science.evidence_level is EvidenceLevel.PHRASE


def test_single_tokens_use_complete_boundaries() -> None:
    """Match standalone generic tokens without matching longer Arabic words."""
    standalone = analyze(title="سجل هدف")
    embedded = analyze(
        title="تستهدف الخطة التطوير",
        body="أبدى ممثلو الدول رأيًا حول تمثيل البيانات",
    )

    assert any(item.matched_text == "هدف" for item in standalone.headline_items)
    assert not any(
        item.reason_code == "GENERIC_SPORTS_TOKEN"
        for item in embedded.all_items
    )
    assert not any("TOPIC_ENTERTAINMENT" in item.supports for item in embedded.all_items)


@pytest.mark.parametrize(
    ("phrase", "reason", "role", "strength", "support"),
    (
        (
            "علماء الفلك",
            "SCIENCE_CONTEXT_PHRASE",
            EvidenceRole.SUBJECT,
            EvidenceStrength.STRONG,
            "TOPIC_SCIENCE",
        ),
        (
            "أشباه الموصلات",
            "TECHNOLOGY_CONTEXT_PHRASE",
            EvidenceRole.SUBJECT,
            EvidenceStrength.STRONG,
            "TOPIC_TECHNOLOGY",
        ),
        (
            "مصلحة الضرائب",
            "GOVERNMENT_CONTEXT_PHRASE",
            EvidenceRole.AUTHORITY,
            EvidenceStrength.STRONG,
            "TOPIC_GOVERNMENT",
        ),
        (
            "معرض الكتاب",
            "CULTURE_CONTEXT_PHRASE",
            EvidenceRole.SUBJECT,
            EvidenceStrength.STRONG,
            "TOPIC_CULTURE",
        ),
        (
            "البنك المركزي",
            "ECONOMY_CONTEXT_PHRASE",
            EvidenceRole.SUBJECT,
            EvidenceStrength.STRONG,
            "TOPIC_ECONOMY",
        ),
        (
            "الأمم المتحدة",
            "WORLD_CONTEXT_PHRASE",
            EvidenceRole.SUBJECT,
            EvidenceStrength.STRONG,
            "TOPIC_WORLD",
        ),
    ),
)
def test_topic_context_phrase_mappings(
    phrase: str,
    reason: str,
    role: EvidenceRole,
    strength: EvidenceStrength,
    support: str,
) -> None:
    """Map every initial topic phrase group to its exact evidence contract."""
    item = next(
        item for item in analyze(title=phrase).headline_items if item.reason_code == reason
    )

    assert item.role is role
    assert item.strength is strength
    assert item.supports == (support,)
    assert item.suppresses == ()


def test_service_context_supports_format_and_reader_action() -> None:
    """Create strong service and know-action evidence from a service phrase."""
    item = next(
        item
        for item in analyze(body="يجب التسجيل قبل الموعد").lead_items
        if item.reason_code == "SERVICE_CONTEXT_PATTERN"
    )

    assert item.role is EvidenceRole.REQUIREMENT
    assert item.strength is EvidenceStrength.STRONG
    assert item.supports == ("FORMAT_SERVICE", "INTENT_KNOW_ACTION")


def test_interpretation_prediction_and_uncertainty_context_mappings() -> None:
    """Support analysis, impact, prediction, and uncertain-claim interpretation."""
    evidence = analyze(
        body="يشير تحليل إلى أن التقنية قد تسهم خلال السنوات المقبلة"
    )
    analysis_items = [
        item
        for item in evidence.lead_items
        if item.reason_code == "INTERPRETATION_CONTEXT_PATTERN"
    ]
    uncertain_items = [
        item
        for item in evidence.lead_items
        if item.reason_code
        in ("UNCERTAINTY_CONTEXT_PATTERN", "PREDICTION_CONTEXT_PATTERN")
    ]

    assert analysis_items
    assert all(
        item.supports == ("FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT")
        and item.role is EvidenceRole.INTERPRETATION
        for item in analysis_items
    )
    assert uncertain_items
    assert all("CLAIM_UNCERTAIN" in item.supports for item in uncertain_items)
    assert {item.role for item in uncertain_items} == {
        EvidenceRole.UNCERTAINTY,
        EvidenceRole.PREDICTION,
    }


@pytest.mark.parametrize("phrase", ("يشير تحليل", "يرى محللون"))
def test_interpretation_patterns_create_analysis_support(phrase: str) -> None:
    """Map reusable interpretation language to analysis and impact support."""
    item = next(
        item
        for item in analyze(body=f"{phrase} أن النتائج مهمة").lead_items
        if item.reason_code == "INTERPRETATION_CONTEXT_PATTERN"
    )

    assert item.role is EvidenceRole.INTERPRETATION
    assert item.strength is EvidenceStrength.MEDIUM
    assert item.supports == ("FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT")


@pytest.mark.parametrize(
    "phrase",
    ("قد يسهم", "قد يؤدي", "من المتوقع أن", "من المرجح أن"),
)
def test_prediction_patterns_create_uncertain_analysis_support(phrase: str) -> None:
    """Map explicit forward-looking language to strong prediction evidence."""
    item = next(
        item
        for item in analyze(body=f"{phrase} القرار في تحسن النتائج").lead_items
        if item.reason_code == "PREDICTION_CONTEXT_PATTERN"
    )

    assert item.role is EvidenceRole.PREDICTION
    assert item.strength is EvidenceStrength.STRONG
    assert item.supports == (
        "CLAIM_UNCERTAIN",
        "FORMAT_ANALYSIS",
        "INTENT_UNDERSTAND_IMPACT",
    )


@pytest.mark.parametrize("phrase", ("يؤدي إلى", "يسهم في", "ينعكس على"))
def test_consequence_patterns_create_analysis_support(phrase: str) -> None:
    """Map deterministic consequence constructions to impact support."""
    item = next(
        item
        for item in analyze(body=f"القرار {phrase} تحسن النتائج").lead_items
        if item.reason_code == "CONSEQUENCE_CONTEXT_PATTERN"
    )

    assert item.role is EvidenceRole.CONSEQUENCE
    assert item.strength is EvidenceStrength.MEDIUM
    assert item.supports == ("FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT")


@pytest.mark.parametrize(
    "sentence",
    (
        "يشير تحليل إلى أن القرار قد يؤدي إلى تحسن النتائج",
        "قد يسهم القرار في النمو بما يؤدي إلى زيادة الإنتاج",
    ),
)
def test_multiple_analytical_roles_create_one_structural_item(sentence: str) -> None:
    """Create at most one combined analytical item for each local sentence."""
    combined = [
        item
        for item in analyze(body=sentence).lead_items
        if item.reason_code == "COMBINED_ANALYTICAL_CONTEXT"
    ]

    assert len(combined) == 1
    assert combined[0].role is EvidenceRole.INTERPRETATION
    assert combined[0].evidence_level is EvidenceLevel.STRUCTURAL
    assert combined[0].strength is EvidenceStrength.STRONG
    assert combined[0].matched_text == sentence


@pytest.mark.parametrize(
    "sentence",
    (
        "تقام المباراة الأسبوع المقبل",
        "تبدأ المرحلة الثانية الشهر المقبل",
        "يغلق باب التسجيل يوم الخميس",
    ),
)
def test_future_reporting_alone_does_not_create_analysis(sentence: str) -> None:
    """Avoid treating schedules and deadlines as analytical evidence."""
    analytical_reasons = {
        "INTERPRETATION_CONTEXT_PATTERN",
        "PREDICTION_CONTEXT_PATTERN",
        "CONSEQUENCE_CONTEXT_PATTERN",
        "COMBINED_ANALYTICAL_CONTEXT",
    }

    assert not any(
        item.reason_code in analytical_reasons
        for item in analyze(body=sentence).all_items
    )


def test_case_013_style_sentence_creates_complete_analytical_evidence() -> None:
    """Recognize conjunction-prefixed interpretation and overlapping roles."""
    sentence = (
        "ويشير تحليل نشرته الشرق إلى أن هذه التقنية قد تسهم في خفض أسعار "
        "السيارات الكهربائية بما يقارب 20% خلال السنوات القليلة القادمة"
    )
    items = analyze(body=sentence).lead_items

    assert {
        EvidenceRole.INTERPRETATION,
        EvidenceRole.PREDICTION,
        EvidenceRole.CONSEQUENCE,
    }.issubset({item.role for item in items})
    supports = {support for item in items for support in item.supports}
    assert {
        "FORMAT_ANALYSIS",
        "INTENT_UNDERSTAND_IMPACT",
        "CLAIM_UNCERTAIN",
    }.issubset(supports)
    assert sum(
        item.reason_code == "COMBINED_ANALYTICAL_CONTEXT" for item in items
    ) == 1


def test_overlapping_consequence_patterns_are_deduplicated() -> None:
    """Prefer one consequence item when a longer pattern contains a shorter one."""
    items = [
        item
        for item in analyze(body="تغير السعر بما يؤدي إلى زيادة الطلب").lead_items
        if item.reason_code == "CONSEQUENCE_CONTEXT_PATTERN"
    ]

    assert len(items) == 1
    assert items[0].matched_text == "بما يؤدي إلى"


def test_attribution_verb_creates_attributed_claim_support() -> None:
    """Create medium attribution evidence without inferring the speaker."""
    item = next(
        item
        for item in analyze(body="أعلنت الجهة تحديثًا").lead_items
        if item.reason_code == "ATTRIBUTION_SIGNAL"
    )

    assert item.role is EvidenceRole.ATTRIBUTION
    assert item.strength is EvidenceStrength.MEDIUM
    assert item.evidence_level is EvidenceLevel.TOKEN
    assert item.supports == ("CLAIM_ATTRIBUTED",)


def test_generic_team_is_weak_and_science_context_suppresses_sports() -> None:
    """Keep team weak and add strong suppression in local science context."""
    evidence = analyze(
        body="أعلن فريق دولي من علماء الفلك اكتشاف كوكب جديد"
    )
    team = next(
        item
        for item in evidence.lead_items
        if item.matched_text == "فريق"
        and item.reason_code == "GENERIC_SPORTS_TOKEN"
    )
    suppression = next(
        item
        for item in evidence.lead_items
        if item.reason_code == "SCIENCE_CONTEXT_SUPPRESSES_GENERIC_TEAM"
    )

    assert team.strength is EvidenceStrength.WEAK
    assert team.supports == ("TOPIC_SPORTS",)
    assert suppression.role is EvidenceRole.ACTOR
    assert suppression.strength is EvidenceStrength.STRONG
    assert suppression.supports == ()
    assert suppression.suppresses == ("TOPIC_SPORTS",)
    assert any("TOPIC_SCIENCE" in item.supports for item in evidence.lead_items)


def test_generic_companies_stay_weak_beside_strong_technology() -> None:
    """Preserve weak business support without weakening technology evidence."""
    evidence = analyze(
        title="شركات السيارات الكهربائية تعتمد البطاريات الصلبة"
    )
    business = next(
        item
        for item in evidence.headline_items
        if item.reason_code == "GENERIC_BUSINESS_TOKEN"
    )
    technology = [
        item
        for item in evidence.headline_items
        if item.reason_code == "TECHNOLOGY_CONTEXT_PHRASE"
    ]

    assert business.strength is EvidenceStrength.WEAK
    assert business.supports == ("TOPIC_BUSINESS",)
    assert technology
    assert all(item.strength is EvidenceStrength.STRONG for item in technology)


def test_generic_ministry_creates_only_weak_government_evidence() -> None:
    """Treat an isolated ministry token as weak authority evidence."""
    item = next(
        item
        for item in analyze(title="وزارة تعلن تحديثًا").headline_items
        if item.reason_code == "GENERIC_GOVERNMENT_TOKEN"
    )

    assert item.role is EvidenceRole.AUTHORITY
    assert item.strength is EvidenceStrength.WEAK
    assert item.supports == ("TOPIC_GOVERNMENT",)


def test_deadline_requirement_and_audience_patterns() -> None:
    """Create exact service roles and downstream support from bounded patterns."""
    evidence = analyze(
        body="يجب على الشركات التسجيل قبل نهاية الشهر"
    )
    deadline = next(
        item
        for item in evidence.lead_items
        if item.reason_code == "DEADLINE_CONTEXT_PATTERN"
    )
    requirement = next(
        item
        for item in evidence.lead_items
        if item.reason_code == "REQUIREMENT_CONTEXT_PATTERN"
    )
    audience = next(
        item
        for item in evidence.lead_items
        if item.reason_code == "AFFECTED_AUDIENCE_CONTEXT_PATTERN"
    )

    assert deadline.role is EvidenceRole.DEADLINE
    assert deadline.strength is EvidenceStrength.STRONG
    assert deadline.supports == (
        "FORMAT_SERVICE",
        "INTENT_KNOW_ACTION",
        "INTENT_VERIFY_REQUIREMENTS",
    )
    assert requirement.role is EvidenceRole.REQUIREMENT
    assert requirement.supports == ("FORMAT_SERVICE", "INTENT_KNOW_ACTION")
    assert audience.role is EvidenceRole.AFFECTED_AUDIENCE
    assert audience.strength is EvidenceStrength.MEDIUM


def test_registration_invitation_creates_requirement_context() -> None:
    """Detect a bounded invitation-to-register pattern without grammar parsing."""
    evidence = analyze(
        body="دعت مصلحة الضرائب الشركات والمكلفين للتسجيل فورًا"
    )

    assert any(
        item.reason_code == "REQUIREMENT_CONTEXT_PATTERN"
        and item.role is EvidenceRole.REQUIREMENT
        for item in evidence.lead_items
    )


def test_user_instruction_upgrades_applicable_medium_context() -> None:
    """Apply strong structural weighting to instruction context evidence."""
    evidence = analyze(user_instruction="اكتب وفق تحليل واضح للتأثير")
    analysis_item = next(
        item
        for item in evidence.user_instruction_items
        if item.reason_code == "INTERPRETATION_CONTEXT_PATTERN"
    )

    assert analysis_item.source_section is SourceSection.USER_INSTRUCTION
    assert analysis_item.strength is EvidenceStrength.STRONG


def test_identical_items_are_deduplicated_and_order_is_stable() -> None:
    """Remove identical repeated matches and preserve first discovery ordering."""
    evidence = analyze(title="قال قال البنك المركزي وزارة")
    attribution_items = [
        item
        for item in evidence.headline_items
        if item.reason_code == "ATTRIBUTION_SIGNAL"
    ]

    assert len(attribution_items) == 1
    assert [item.reason_code for item in evidence.headline_items] == [
        "ATTRIBUTION_SIGNAL",
        "ECONOMY_CONTEXT_PHRASE",
        "GENERIC_GOVERNMENT_TOKEN",
    ]


def test_source_is_unchanged_and_equal_inputs_are_deterministic() -> None:
    """Avoid input mutation and return equal evidence for identical input."""
    source = make_source(
        title="أعلنت مصلحة الضرائب تحديثًا",
        body="يجب التسجيل قبل نهاية الشهر",
    )
    snapshot = tuple(getattr(source, field.name) for field in fields(source))
    engine = DeterministicContextualEvidenceEngine()

    first = engine.analyze(source=source)
    second = engine.analyze(source=source)

    assert first == second
    assert first is not second
    assert tuple(getattr(source, field.name) for field in fields(source)) == snapshot


def test_empty_input_has_only_empty_evidence_warning() -> None:
    """Return the stable warning only when no evidence exists anywhere."""
    evidence = analyze(title="", body="", user_instruction=None)

    assert evidence.all_items == ()
    assert isinstance(evidence.all_items, tuple)
    assert evidence.warnings == ("CONTEXTUAL_EVIDENCE_EMPTY",)
    assert evidence.metadata_items == ()


def test_engine_output_all_items_preserves_section_order() -> None:
    """Expose engine items through the model's fixed section aggregation."""
    evidence = analyze(
        title="أعلنت وزارة النقل",
        body="قال البنك المركزي بيانًا. أوضح معرض الكتاب خطته",
        user_instruction="اكتب وفق تحليل",
    )

    assert evidence.all_items == (
        evidence.headline_items
        + evidence.lead_items
        + evidence.body_items
        + evidence.metadata_items
        + evidence.user_instruction_items
    )
