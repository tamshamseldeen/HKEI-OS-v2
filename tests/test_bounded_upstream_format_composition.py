"""Raw-Arabic generalization tests for bounded editorial treatment composition."""

from pathlib import Path

import pytest

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.normalized_source import NormalizedSource
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)


def format_evidence(*, body: str, title: str = "عنوان صحفي عام") -> tuple[tuple[str, ...], tuple[str, ...]]:
    source = NormalizedSource(
        title=title,
        body=body,
        source_name="مصدر تجريبي",
        source_url="https://example.com/generic-format-fixture",
        language="ar",
    )
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=source,
        contextual_evidence=contextual,
    )
    return semantic.format_support, semantic.format_suppression


@pytest.mark.parametrize(
    ("title", "body", "expected", "absent"),
    (
        (
            "دليل لفهم منظومة تدوير المياه",
            "يشرح التقرير كيف يعمل النظام من خلال مرشحات متتابعة ولماذا تحافظ الآلية على الموارد.",
            "FORMAT_EXPLAINER", None,
        ),
        (
            "إعلان إداري جديد",
            "أعلنت الجهة قرارا وشرح المسؤول خلفية الاجتماع.",
            None, "FORMAT_EXPLAINER",
        ),
        (
            "آلية تنقية الهواء",
            "يعرض التقرير النظام. ويوضح كيف يعمل من خلال مراحل مترابطة لفهم العملية.",
            "FORMAT_EXPLAINER", None,
        ),
        (
            "النظام الجديد لإعادة التدوير",
            "يوضح التقرير كيف يعمل من خلال فصل المواد لفهم لماذا تقل النفايات.",
            "FORMAT_EXPLAINER", None,
        ),
    ),
)
def test_raw_arabic_explainer_composition(
    title: str, body: str, expected: str | None, absent: str | None,
) -> None:
    support, _ = format_evidence(title=title, body=body)
    if expected:
        assert expected in support
    if absent:
        assert absent not in support


@pytest.mark.parametrize(
    ("body", "expected", "absent"),
    (
        ("بلغ المؤشر حاليا 120 نقطة. وارتفع مقارنة بالشهر الماضي.", "FORMAT_TREND_UPDATE", None),
        ("بلغ المؤشر حاليا 120 نقطة دون بيانات سابقة.", None, "FORMAT_TREND_UPDATE"),
        ("في يوم الثلاثاء بلغ المؤشر 120 نقطة.", None, "FORMAT_TREND_UPDATE"),
        ("سجل المعدل حاليا ثمانية بالمئة. وواصل الارتفاع لليوم الثاني.", "FORMAT_TREND_UPDATE", None),
        ("وصل السعر إلى سبعين جنيها. ثم انخفض مقارنة بالعام الماضي.", "FORMAT_TREND_UPDATE", None),
    ),
)
def test_raw_arabic_trend_composition(
    body: str, expected: str | None, absent: str | None,
) -> None:
    support, _ = format_evidence(body=body)
    if expected:
        assert expected in support
    if absent:
        assert absent not in support


@pytest.mark.parametrize(
    "body",
    (
        "أعلنت الوزارة قرارا جديدا لتنظيم ساعات العمل.",
        "شهدت المدينة تطورا جديدا وأكد البيان تفاصيله.",
        "أعلنت الهيئة اليوم قرارا إداريا عاديا.",
        "أعلن المتحدث بيانا عن الحدث وأضاف معلومات من خلفيته.",
    ),
)
def test_raw_arabic_standard_news_composition(body: str) -> None:
    support, _ = format_evidence(body=body)
    assert "FORMAT_STANDARD_NEWS" in support
    assert "FORMAT_BREAKING" not in support


@pytest.mark.parametrize(
    ("body", "expected", "absent"),
    (
        ("انتهت المباراة بفوز الفريق بهدفين.", "FORMAT_RESULT_REPORT", None),
        ("اختتمت البطولة. وجاء الفريق في المركز الأول ضمن الترتيب النهائي.", "FORMAT_RESULT_REPORT", None),
        ("ستقام المباراة غدا وسط توقعات بالنتيجة النهائية.", None, "FORMAT_RESULT_REPORT"),
        ("أعلنت المؤسسة هدفا مستهدفا ومتوقعا للعام المقبل.", None, "FORMAT_RESULT_REPORT"),
        ("المشروع ما زال قيد التنفيذ بعد بلوغ مرحلة وسيطة دون نتائج نهائية.", None, "FORMAT_RESULT_REPORT"),
        ("انتهت العاصفة وأدت إلى تأثير واسع في حركة المرور.", None, "FORMAT_RESULT_REPORT"),
        ("بلغ المؤشر حاليا 90 نقطة وارتفع مقارنة بالشهر الماضي.", "FORMAT_TREND_UPDATE", "FORMAT_RESULT_REPORT"),
        ("انتهت المسابقة مساء أمس. وأعلنت اللجنة النتيجة النهائية بفوز الفريق.", "FORMAT_RESULT_REPORT", None),
    ),
)
def test_raw_arabic_completed_result_boundaries(
    body: str, expected: str | None, absent: str | None,
) -> None:
    support, _ = format_evidence(body=body)
    if expected:
        assert expected in support
    if absent:
        assert absent not in support


@pytest.mark.parametrize(
    ("body", "expected", "absent"),
    (
        ("انتهت البطولة بفوز النادي في الترتيب النهائي دون مقارنة زمنية.", "FORMAT_RESULT_REPORT", "FORMAT_TREND_UPDATE"),
        ("أعلنت الجهة نتائج أولية في بيان عن تطور العمل.", "FORMAT_STANDARD_NEWS", "FORMAT_RESULT_REPORT"),
        ("أعلنت الجهة قرار تشغيل النظام وقدم البيان معلومات عن خلفيته.", "FORMAT_STANDARD_NEWS", "FORMAT_EXPLAINER"),
    ),
)
def test_raw_arabic_format_ontology_boundaries(
    body: str, expected: str, absent: str,
) -> None:
    support, _ = format_evidence(body=body)
    assert expected in support
    assert absent not in support


def test_bounded_format_fix_contains_no_evaluated_holdout_identifiers() -> None:
    project_root = Path(__file__).resolve().parents[1]
    changed_sources = (
        project_root / "src/semantics/deterministic_compositional_semantic_engine.py",
        Path(__file__),
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in changed_sources)
    forbidden = tuple(f"{value:03d}" for value in range(61, 69) if value not in {64, 67})
    assert not any(identifier in text for identifier in forbidden)
