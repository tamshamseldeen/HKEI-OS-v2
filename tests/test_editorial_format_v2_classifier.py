"""Raw-Arabic shadow-selection tests for Editorial Format V2."""

import hashlib
import inspect
from pathlib import Path

import pytest

from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_ambiguity import EditorialFormatAmbiguity
from src.formatting.editorial_format_completeness import EditorialFormatCompleteness
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.formatting.editorial_format_v2_classifier import EditorialFormatV2Classifier
from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature as F
from src.formatting.editorial_treatment_feature_result import EditorialTreatmentFeatureResult
from src.intake.normalized_source import NormalizedSource
from tests.test_deterministic_editorial_format_classifier import (
    make_assessment, make_content, make_facts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _classify(headline: str, lead: str, body: str):
    return EditorialFormatV2Classifier().classify(
        source=NormalizedSource(
            title=headline, body=body, source_name="صحيفة عربية افتراضية",
            language="ar",
        ),
        lead=lead,
    )


CLEAR_BASES = (
    (EditorialFormat.BREAKING, "عاجل: أعلنت الغرفة تطورا الآن", "أعلنت الغرفة بدء الاستجابة.", "المعلومات الأولية لا تزال محدودة والتفاصيل تباعا."),
    (EditorialFormat.STANDARD_NEWS, "أعلنت الرابطة قرارا جديدا", "أصدر مجلس الرابطة القرار بعد جلسة.", "كشف البيان البنود المقررة وموعد العمل بها."),
    (EditorialFormat.SERVICE, "بدء التسجيل في برنامج التدريب", "التقديم متاح حتى الأربعاء.", "تشمل الشروط إثبات الهوية وترفع المستندات عبر المنصة."),
    (EditorialFormat.GUIDE, "نصائح للاستعداد للعرض", "عليك تحديد الرسالة وتجنب التفاصيل الزائدة.", "تأكد من التدريب ثم قم بمراجعة الوقت والصوت."),
    (EditorialFormat.EXPLAINER, "كيف يعمل نظام إعادة التدوير؟", "تعتمد الآلية على مراحل متتابعة.", "تبدأ المرحلة الأولى بالفرز ثم ينتقل المنتج إلى المعالجة."),
    (EditorialFormat.FEATURE, "صباح نابض في سوق الحرف", "في صباح بارد دخل الزوار السوق القديم.", "ثم تحدثوا مع الصناع وبعد ذلك شاهدوا مراحل العمل."),
    (EditorialFormat.FACT_CHECK, "فحص ادعاء عن إجازة عامة", "تحققنا من الادعاء عبر السجل المنشور.", "لا دليل على الإجازة والادعاء غير صحيح."),
    (EditorialFormat.ANALYSIS, "أسباب تباطؤ مشروع النقل", "تأخر التنفيذ بسبب قيود التوريد.", "أدى ذلك إلى رفع التكلفة ولذلك تغيرت مراحل الخطة."),
    (EditorialFormat.INTERVIEW, "أسئلة وأجوبة مع مهندسة", "سؤال: ما الهدف؟ جواب: خفض الاستهلاك. سؤال: ما المنهج؟ جواب: اختبار تدريجي.", "سؤال: متى يبدأ التطبيق؟\nجواب: الشهر المقبل.\nسؤال: كيف تقيسون النجاح؟\nجواب: ببيانات شهرية."),
    (EditorialFormat.PROFILE, "مسيرة طبيبة عبر ثلاثة عقود", "ولدت هناء في بلدة صغيرة وبدأت مسيرتها في عيادة محلية.", "حققت محطة بارزة عام 2011 وتشغل حاليا منصبا تدريبيا."),
    (EditorialFormat.RESULT_REPORT, "فوز الفريق في النتيجة النهائية", "انتهت المباراة وفاز الفريق المضيف.", "النتيجة النهائية حسمت اللقب بعد أن سجل هدفين."),
    (EditorialFormat.TREND_UPDATE, "ارتفع الطلب مقارنة بالعام السابق", "زاد الطلب مقارنة بالشهر السابق.", "واصل النمو للفترة الرابعة على التوالي."),
)

CLEAR_FIXTURES = tuple(
    (
        candidate,
        f"{headline} - صياغة {variant}",
        lead,
        f"{body} وتعرض هذه الصياغة بنية مستقلة رقم {variant}.",
    )
    for candidate, headline, lead, body in CLEAR_BASES
    for variant in (1, 2)
)

COMPETITION_FIXTURES = (
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.BREAKING, "عاجل: أعلنت اللجنة قرارا الآن", "أعلنت اللجنة القرار هذا الصباح.", "المعلومات الأولية لا تزال قيد التطور والتفاصيل تباعا."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.ANALYSIS, "إعلان عن تأخر المشروع", "أعلنت الإدارة التأخير بسبب نقص المعدات.", "أدى ذلك إلى تعديل الميزانية ولذلك تغير المسار."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.EXPLAINER, "إعلان منصة جديدة تشرح كيف يعمل النظام", "أعلنت الجمعية المنصة وشرحت آلية عمل النظام.", "تبدأ المرحلة الأولى بالتسجيل ثم ينتقل الطلب إلى التدقيق."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.RESULT_REPORT, "إعلان النتيجة النهائية", "أعلنت اللجنة اكتمال الفرز.", "انتهت العملية. فاز المقترح الثاني وفق النتيجة النهائية."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.TREND_UPDATE, "إعلان بيانات الحركة", "أعلن المرصد أن العدد ارتفع مقارنة بالشهر السابق.", "واصل النمو للفصل الثالث."),
    (EditorialFormat.SERVICE, EditorialFormat.GUIDE, "دليل التسجيل في الورشة", "عليك التقديم قبل الأحد.", "تشمل الشروط وثيقة الهوية عبر المنصة؛ تأكد من البيانات ثم تجنب التأخير."),
    (EditorialFormat.SERVICE, EditorialFormat.FACT_CHECK, "فحص ادعاء عن رسوم الطلب", "التقديم متاح برسوم حتى الاثنين.", "تحققنا من الادعاء؛ السجل يثبت أن الادعاء غير صحيح والمستندات مطلوبة."),
    (EditorialFormat.ANALYSIS, EditorialFormat.EXPLAINER, "كيف ولماذا تعمل المنظومة؟", "تعتمد الآلية على مرحلتين بسبب ضغط السعة.", "تبدأ أولا بالفرز ثم تنتقل للمعالجة، أدى إلى بطء الخدمة. لذلك تراجع الأداء."),
    (EditorialFormat.RESULT_REPORT, EditorialFormat.TREND_UPDATE, "نتيجة نهائية بعد مسار متغير", "انتهت الجولة. فاز الفريق.", "ارتفع رصيده مقارنة بالموسم السابق وواصل النمو."),
    (EditorialFormat.FEATURE, EditorialFormat.PROFILE, "حكاية موسيقية ومسيرة طويلة", "ولدت سارة في بلدة ساحلية وبدأت مسيرتها هناك.", "في مساء الحفل روت محطتها الكبرى ثم عزفت وتشغل حاليا إدارة الفرقة."),
    (EditorialFormat.INTERVIEW, EditorialFormat.PROFILE, "حوار عن مسيرة عالم", "ولد فؤاد في قرية وبدأ مسيرته مبكرا.", "سؤال: ما أهم محطة في عملك حاليا؟\nجواب: جائزة عام 2017.\nسؤال: ماذا تقود الآن؟\nجواب: أقود فريقا."),
    (EditorialFormat.GUIDE, EditorialFormat.EXPLAINER, "كيف يعمل المقياس وكيف تستخدمه؟", "تعتمد الآلية على حساس، وعليك فحص الطاقة.", "تبدأ القراءة أولا ثم تظهر النتيجة؛ تأكد من المعايرة ثم تجنب الماء."),
)

INSUFFICIENT_FIXTURES = tuple(
    (
        f"ملاحظة وصفية {index}",
        "يقدم النص اسما ومكانا فقط.",
        "توجد معلومات عامة بلا حدث أو إجراء أو تفسير أو بنية مكتملة.",
    )
    for index in range(1, 7)
)

CONTRADICTORY_FIXTURES = (
    ("لماذا وكيف تعمل الوحدة؟", "تعتمد الآلية على مرحلتين بسبب قيد داخلي.", "تبدأ أولا ثم تنتقل للمعالجة، أدى إلى بطء التنفيذ. لذلك تغير الناتج."),
    ("نتيجة نهائية ضمن حركة سنوية", "انتهت الجولة. فاز النادي.", "ارتفع رصيده مقارنة بالعام السابق وواصل النمو."),
    ("خدمة للتحقق من ادعاء الرسوم", "التقديم متاح حتى الخميس برسوم محددة.", "تحققنا من الادعاء؛ المستندات مطلوبة لكن الادعاء غير صحيح."),
    ("خبر عاجل عن النتيجة النهائية", "أعلنت الجهة النتيجة الآن بعد أن انتهت العملية وفاز الخيار الأول.", "المعلومات الأولية لا تزال محدودة والتفاصيل تباعا."),
    ("حوار يرسم مسيرة فنان", "ولد الفنان في مدينة صغيرة وبدأ مسيرته مبكرا.", "سؤال: ما محطتك حاليا؟\nجواب: معرض جديد.\nسؤال: ما التالي؟\nجواب: جولة خارجية."),
    ("حوار متعارض عن سيرة مصممة", "ولدت المصممة في قرية وبدأت مسيرتها هناك.", "سؤال: ما محطتك حاليا؟\nجواب: معرض جديد.\nسؤال: ماذا تقود الآن؟\nجواب: أقود الاستوديو."),
)


@pytest.mark.parametrize(
    ("expected", "headline", "lead", "body"),
    CLEAR_FIXTURES,
    ids=[f"{item[0].value}_{index}" for index, item in enumerate(CLEAR_FIXTURES, 1)],
)
def test_twenty_four_clear_raw_arabic_positive_fixtures(
    expected, headline, lead, body,
) -> None:
    result = _classify(headline, lead, body)
    assert result.selected_format is expected
    assert result.ambiguity is EditorialFormatAmbiguity.CLEAR
    assert result.confidence in {
        EditorialFormatConfidence.HIGH, EditorialFormatConfidence.MEDIUM,
    }


@pytest.mark.parametrize(
    ("first", "second", "headline", "lead", "body"),
    COMPETITION_FIXTURES,
    ids=[f"{item[0].value}_vs_{item[1].value}" for item in COMPETITION_FIXTURES],
)
def test_twelve_neighboring_profile_competition_fixtures(
    first, second, headline, lead, body,
) -> None:
    result = _classify(headline, lead, body)
    by_candidate = {item.candidate: item for item in result.candidate_assessments}
    assert not by_candidate[first].missing_required_features
    assert not by_candidate[second].missing_required_features
    assert (
        second in by_candidate[first].competing_candidates
        or first in by_candidate[second].competing_candidates
    )
    assert result.ambiguity in {
        EditorialFormatAmbiguity.CLEAR,
        EditorialFormatAmbiguity.COMPETING,
        EditorialFormatAmbiguity.CONTRADICTORY,
    }


@pytest.mark.parametrize(
    ("headline", "lead", "body"), INSUFFICIENT_FIXTURES,
)
def test_six_insufficient_evidence_fixtures(headline, lead, body) -> None:
    result = _classify(headline, lead, body)
    assert result.ambiguity is EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE
    assert result.confidence is EditorialFormatConfidence.LOW
    assert "DETERMINISTIC_PLACEHOLDER_SELECTED" in result.warnings
    assert result.selected_format is not EditorialFormat.STANDARD_NEWS


@pytest.mark.parametrize(
    ("headline", "lead", "body"), CONTRADICTORY_FIXTURES,
)
def test_six_contradictory_structure_fixtures(headline, lead, body) -> None:
    result = _classify(headline, lead, body)
    assert any(
        item.ambiguity is EditorialFormatAmbiguity.CONTRADICTORY
        for item in result.candidate_assessments
    )
    assert result.confidence is not EditorialFormatConfidence.HIGH


def _symbolic(*features: F, cross: tuple[F, ...] = ()) -> EditorialTreatmentFeatureResult:
    return EditorialTreatmentFeatureResult(
        features=features, headline_features=(), lead_features=(), body_features=(),
        cross_section_features=cross, warnings=(),
    )


def test_clear_complete_strong_produces_high_confidence() -> None:
    result = EditorialFormatV2Classifier().classify_features(
        _symbolic(F.EVENT_REPORTING, cross=(F.EVENT_REPORTING,))
    )
    selected = next(
        item for item in result.candidate_assessments
        if item.candidate is result.selected_format
    )
    assert selected.completeness is EditorialFormatCompleteness.COMPLETE
    assert result.ambiguity is EditorialFormatAmbiguity.CLEAR
    assert result.confidence is EditorialFormatConfidence.HIGH


def test_competing_partial_insufficient_and_contradictory_are_never_high() -> None:
    classifier = EditorialFormatV2Classifier()
    competing = classifier.classify_features(
        _symbolic(F.PROCEDURAL_SERVICE, F.ACTIONABLE_GUIDANCE)
    )
    insufficient = classifier.classify_features(_symbolic())
    contradictory = classifier.classify_features(
        _symbolic(F.CAUSAL_EXPLANATION, F.MECHANISM_EXPLANATION)
    )
    assert competing.ambiguity is EditorialFormatAmbiguity.COMPETING
    assert competing.confidence is not EditorialFormatConfidence.HIGH
    assert any(
        item.completeness is EditorialFormatCompleteness.PARTIAL
        for item in competing.candidate_assessments
    )
    assert insufficient.confidence is EditorialFormatConfidence.LOW
    assert contradictory.ambiguity is EditorialFormatAmbiguity.CONTRADICTORY
    assert contradictory.confidence is not EditorialFormatConfidence.HIGH


def test_exact_semantic_tie_is_stable_explicit_and_not_enum_order_semantics() -> None:
    classifier = EditorialFormatV2Classifier()
    features = _symbolic(F.PROCEDURAL_SERVICE, F.ACTIONABLE_GUIDANCE)
    results = tuple(classifier.classify_features(features) for _ in range(10))
    assert len(set(results)) == 1
    assert results[0].ambiguity is EditorialFormatAmbiguity.COMPETING
    assert results[0].confidence is EditorialFormatConfidence.LOW
    assert "DETERMINISTIC_TIE_BREAK_APPLIED" in results[0].warnings


def test_all_twelve_formats_are_selectable() -> None:
    selected = {
        _classify(headline, lead, body).selected_format
        for expected, headline, lead, body in CLEAR_FIXTURES
    }
    assert selected == set(EditorialFormat)


def test_identical_raw_input_is_fully_deterministic() -> None:
    args = CLEAR_FIXTURES[0][1:]
    results = tuple(_classify(*args) for _ in range(5))
    assert len(set(results)) == 1


def test_v2_execution_does_not_mutate_v1_output() -> None:
    source = NormalizedSource(
        title="عنوان خبري", body="تفاصيل خبرية مؤكدة من المصدر.",
        source_name="وكالة الأنباء",
    )
    classifier = DeterministicEditorialFormatClassifier()
    kwargs = {
        "source": source, "assessment": make_assessment(),
        "facts": make_facts(), "content_classification": make_content(),
    }
    before = classifier.classify(**kwargs)
    _classify(*CLEAR_FIXTURES[5][1:])
    after = classifier.classify(**kwargs)
    assert after == before


def test_shadow_classifier_has_no_v1_gate_reader_intent_provider_or_resolver_coupling() -> None:
    source = inspect.getsource(EditorialFormatV2Classifier)
    forbidden = (
        "DeterministicEditorialFormatClassifier", "adjudication_gate",
        "ReaderIntent", "OpenAI", "provider", "Resolver",
    )
    assert not any(term in source for term in forbidden)


def test_no_holdout_truth_or_corpus_paths_leak() -> None:
    source = (
        inspect.getsource(EditorialFormatV2Classifier)
        + Path(__file__).read_text(encoding="utf-8")
    ).casefold()
    forbidden = (
        "bench" + "mark/", "batch" + "_07", "batch" + "_08",
        "expected" + "_labels", "expected" + "_topic", "expected" + "_format",
    )
    assert not any(term in source for term in forbidden)


def test_v1_classifier_file_remains_unchanged() -> None:
    path = PROJECT_ROOT / "src/formatting/deterministic_editorial_format_classifier.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "a332c14f12c7cb6bad0fab214d1ff44512ccc9bbacd6f9ef9f86f262c278c117"
    )
