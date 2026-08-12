"""Raw-text generalization tests for reusable Arabic semantic components."""

from pathlib import Path

import pytest

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.evidence.evidence_role import EvidenceRole
from src.intake.normalized_source import NormalizedSource
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)


def analyze(*, title: str = "تقرير عام", body: str):
    source = NormalizedSource(
        title=title,
        body=body,
        source_name="مصدر اصطناعي",
        source_url="https://example.com/arabic-fixture",
        language="ar",
    )
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=source,
        contextual_evidence=contextual,
    )
    return contextual, semantic


@pytest.mark.parametrize(
    ("body", "role"),
    (
        ("أعلنت الجهة خطة جديدة", EvidenceRole.ACTION),
        ("يعلن المركز تفاصيل المبادرة", EvidenceRole.ACTION),
        ("إعلان النتائج خلال الأسبوع", EvidenceRole.RESULT),
        ("ارتفعت أسعار السلع", EvidenceRole.CHANGE),
        ("يرتفع سعر الصرف تدريجيا", EvidenceRole.CHANGE),
        ("تراجعت معدلات الطلب", EvidenceRole.CHANGE),
        ("انخفاض المعدلات مستمر", EvidenceRole.CHANGE),
    ),
)
def test_verbal_and_nominal_inflection_families(
    body: str, role: EvidenceRole,
) -> None:
    contextual, _ = analyze(body=body)
    assert role in {item.role for item in contextual.all_items}


@pytest.mark.parametrize(
    ("body", "role"),
    (
        ("بلغ متوسط سعر الصرف مستوى جديدا", EvidenceRole.PRICE),
        ("وصلت نسبة الإنتاج إلى مستوى أعلى", EvidenceRole.MEASUREMENT),
        ("توضح النشرة درجة الحرارة المتوقعة", EvidenceRole.MEASUREMENT),
        ("يراقب الطبيب ضغط الدم بانتظام", EvidenceRole.MEASUREMENT),
        ("تغيرت أسعار مواد البناء", EvidenceRole.SUBJECT),
        ("تتناول الخطة الأمراض المزمنة", EvidenceRole.SUBJECT),
    ),
)
def test_multiword_price_measurement_and_subject_concepts(
    body: str, role: EvidenceRole,
) -> None:
    contextual, _ = analyze(body=body)
    assert role in {item.role for item in contextual.all_items}


@pytest.mark.parametrize(
    "body",
    (
        "بدأت مبادرة صحية. واستمرت خلال الفترة الماضية.",
        "تراجع الطلب. وأدى ذلك إلى انخفاض الإنتاج.",
        "أعلنت شركة خطتها. وتسببت في ذلك.",
    ),
)
def test_bounded_implicit_subject_continuation(body: str) -> None:
    contextual, _ = analyze(body=body)
    assert any(
        item.reason_code == "ADJACENT_IMPLICIT_SUBJECT_COMPONENT"
        for item in contextual.all_items
    )


@pytest.mark.parametrize(
    ("title", "role"),
    (
        ("ارتفاع أسعار الوقود", EvidenceRole.CHANGE),
        ("مواعيد مباريات الجولة", EvidenceRole.SCHEDULE),
        ("نتائج الدراسة الجديدة", EvidenceRole.RESULT),
        ("نصائح للوقاية اليومية", EvidenceRole.REQUIREMENT),
    ),
)
def test_headline_ellipsis_emits_components_without_final_labels(
    title: str, role: EvidenceRole,
) -> None:
    contextual, semantic = analyze(title=title, body="تفاصيل عامة متاحة")
    assert any(
        item.source_section.value == "HEADLINE" and item.role is role
        for item in contextual.all_items
    )
    assert semantic.format_support == ()


@pytest.mark.parametrize(
    "body",
    (
        "بلغ السعر مستوى جديدا اليوم. واصل الارتفاع مقارنة بالأسبوع الماضي.",
        "سجل المعدل قيمة جديدة. استمر التراجع على مدار الشهر.",
        "وصلت النسبة إلى مستوى محدد. زادت منذ بداية الفترة.",
    ),
)
def test_temporal_phrasing_composes_trend_only_with_movement(body: str) -> None:
    contextual, semantic = analyze(body=body)
    assert EvidenceRole.TEMPORAL_UPDATE in {item.role for item in contextual.all_items}
    assert "FORMAT_TREND_UPDATE" in semantic.format_support


def test_schedule_announcement_composes_service_not_result() -> None:
    _, semantic = analyze(body="أعلنت الجهة موعد المباراة. تقام الجولة غدا في الموقع المحدد.")
    assert "FORMAT_SERVICE" in semantic.format_support
    assert "FORMAT_RESULT_REPORT" not in semantic.format_support


def test_completed_outcome_composes_result_report() -> None:
    _, semantic = analyze(body="انتهت المباراة. وأكدت الحصيلة فوز الفريق.")
    assert "FORMAT_RESULT_REPORT" in semantic.format_support


def test_preventive_actions_compose_guide() -> None:
    _, semantic = analyze(body="ينصح الأطباء بتجنب العدوى. اتبع خطوات الوقاية والفحوصات.")
    assert "FORMAT_GUIDE" in semantic.format_support


def test_official_requirements_compose_service_without_fact_check() -> None:
    _, semantic = analyze(body="أعلنت الجهة بدء التسجيل. يجب تقديم المستندات قبل آخر موعد.")
    assert "FORMAT_SERVICE" in semantic.format_support or "FORMAT_GUIDE" in semantic.format_support
    assert "FORMAT_FACT_CHECK" not in semantic.format_support


def test_health_authority_keeps_health_subject_primary() -> None:
    _, semantic = analyze(body="أعلنت وزارة الصحة المبادرة. تشمل فحوصات الأمراض المزمنة.")
    assert "PRIMARY_DOMAIN_HEALTH" in semantic.primary_domain_candidates


def test_government_actor_with_economic_subject_promotes_economy() -> None:
    _, semantic = analyze(body="أعلنت الوزارة بيانات جديدة. ارتفعت أسعار مواد البناء.")
    assert "PRIMARY_DOMAIN_ECONOMY" in semantic.primary_domain_candidates


def test_company_actor_alone_does_not_define_market_subject() -> None:
    contextual, semantic = analyze(body="أعلنت شركة خطتها. تراجع الطلب في السوق.")
    assert EvidenceRole.SUBJECT in {item.role for item in contextual.all_items}
    assert "PRIMARY_DOMAIN_BUSINESS" not in semantic.primary_domain_candidates


def test_event_cause_and_consequence_compose_analysis() -> None:
    _, semantic = analyze(body="بدأ التغيير بسبب نقص الموارد. أدى ذلك إلى تأثير واسع.")
    assert "FORMAT_ANALYSIS" in semantic.format_support


def test_process_mechanism_composes_explainer() -> None:
    _, semantic = analyze(body="تغيرت المنظومة. ويوضح التقرير كيف يعمل النظام لفهم العملية.")
    assert "FORMAT_EXPLAINER" in semantic.format_support


def test_explicit_claim_verification_and_verdict_compose_fact_check() -> None:
    _, semantic = analyze(body="انتشر ادعاء. تحقق الفريق من الأدلة وثبت بطلانه.")
    assert "FORMAT_FACT_CHECK" in semantic.format_support


@pytest.mark.parametrize(
    ("body", "absent"),
    (
        ("اليوم صدر التقرير", "FORMAT_TREND_UPDATE"),
        ("ورد الرقم 37 في البيان", "FORMAT_TREND_UPDATE"),
        ("وزارة", "PRIMARY_DOMAIN_GOVERNMENT"),
        ("شركة", "PRIMARY_DOMAIN_BUSINESS"),
        ("أكد المسؤول البيان", "FORMAT_FACT_CHECK"),
        ("تقام المباراة غدا", "FORMAT_RESULT_REPORT"),
        ("ذكر التقرير وجود نصائح عامة", "FORMAT_GUIDE"),
        ("بلغ السعر 20", "FORMAT_TREND_UPDATE"),
        ("بسبب", "FORMAT_ANALYSIS"),
    ),
)
def test_incomplete_structures_are_negative_controls(body: str, absent: str) -> None:
    _, semantic = analyze(body=body)
    assert absent not in semantic.format_support
    assert absent not in semantic.primary_domain_candidates


def test_new_code_contains_no_holdout_identifiers() -> None:
    paths = (
        Path("src/evidence/evidence_role.py"),
        Path("src/evidence/deterministic_contextual_evidence_engine.py"),
        Path("src/semantics/deterministic_compositional_semantic_engine.py"),
        Path(__file__),
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for value in range(51, 61):
        assert f"{value:03d}" not in combined
