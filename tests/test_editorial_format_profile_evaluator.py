"""End-to-end profile tests for Editorial Format V2 candidate evaluation."""

import hashlib
import inspect
from pathlib import Path

import pytest

from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_ambiguity import EditorialFormatAmbiguity
from src.formatting.editorial_format_completeness import EditorialFormatCompleteness
from src.formatting.editorial_format_profile_evaluator import (
    EditorialFormatProfileEvaluator,
)
from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature as F
from src.formatting.editorial_treatment_feature_extractor import (
    EditorialTreatmentFeatureExtractor,
)
from src.formatting.editorial_treatment_feature_result import (
    EditorialTreatmentFeatureResult,
)
from src.intake.normalized_source import NormalizedSource
from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assess(headline: str, lead: str, body: str):
    source = NormalizedSource(
        title=headline, body=body, source_name="منصة عربية تجريبية", language="ar",
    )
    features = EditorialTreatmentFeatureExtractor().extract(source=source, lead=lead)
    return EditorialFormatProfileEvaluator().evaluate(features)


def _candidate(assessments, candidate: EditorialFormat):
    return next(item for item in assessments if item.candidate is candidate)


POSITIVE_FIXTURES = (
    (EditorialFormat.BREAKING, "عاجل: تطور جديد الآن", "أعلنت الهيئة بدء الاستجابة.", "المعلومات الأولية لا تزال محدودة والتفاصيل تباعا."),
    (EditorialFormat.STANDARD_NEWS, "أعلنت الجمعية قرارها", "أصدر المجلس قرارا بعد الاجتماع.", "وأوضح البيان البنود الأساسية للتنفيذ."),
    (EditorialFormat.SERVICE, "بدء التسجيل في المنحة", "التقديم متاح حتى الخميس.", "تشمل الشروط وثيقة الهوية وترفع المستندات عبر المنصة."),
    (EditorialFormat.GUIDE, "نصائح لتنظيم وقت الدراسة", "عليك تحديد الهدف وتجنب تشتيت الانتباه.", "تأكد من ترتيب الأولويات ثم قم بمراجعة الخطة."),
    (EditorialFormat.EXPLAINER, "كيف يعمل عداد المياه؟", "تعتمد الآلية على مراحل مترابطة.", "تبدأ المرحلة الأولى بالقياس ثم ينتقل الرقم إلى الشاشة."),
    (EditorialFormat.FEATURE, "مساء طويل في ورشة الخزف", "في مساء هادئ دخل الزوار الورشة.", "ثم استمعوا إلى الحرفيين وبعد ذلك تجولوا بين الأفران."),
    (EditorialFormat.FACT_CHECK, "تدقيق ادعاء عن ساعات العمل", "تحققنا من الادعاء بمراجعة السجل.", "لا دليل على التغيير والادعاء غير صحيح."),
    (EditorialFormat.ANALYSIS, "لماذا تأخر بناء الجسر؟", "تأخر المشروع بسبب نقص التمويل.", "أدى ذلك إلى تقليص العمل ولذلك امتد الجدول."),
    (EditorialFormat.INTERVIEW, "حوار مع مصممة منتجات", "مقابلة بصيغة سؤال وجواب.", "سؤال: ما الفكرة؟\nجواب: تقليل الهدر.\nسؤال: كيف تختبرونها؟\nجواب: بنماذج صغيرة."),
    (EditorialFormat.PROFILE, "محطات في مسيرة عالمة", "ولدت ندى في مدينة ساحلية وبدأت مسيرتها في المختبر.", "حققت محطة مهمة عام 2012 وتشغل حاليا منصبا أكاديميا."),
    (EditorialFormat.RESULT_REPORT, "النتيجة النهائية للبطولة", "انتهت المنافسة بعد الجولة الأخيرة.", "فاز النادي الشرقي وسجل هدفين في اللقاء."),
    (EditorialFormat.TREND_UPDATE, "ارتفاع المشاركة خلال عامين", "ارتفعت النسبة مقارنة بالعام السابق.", "واصل النمو للشهر الرابع على التوالي."),
)

NEGATIVE_FIXTURES = tuple(
    (
        candidate,
        f"مادة عامة رقم {index}",
        "يعرض النص معلومات وصفية موجزة.",
        "ترد أسماء وأماكن دون تنظيم علاجي مكتمل.",
    )
    for index, candidate in enumerate(EditorialFormat, start=1)
)

COMPETITION_FIXTURES = (
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.BREAKING, "عاجل: إعلان جديد الآن", "أعلنت اللجنة القرار.", "المعلومات الأولية لا تزال قيد التطور والتفاصيل تباعا."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.ANALYSIS, "إعلان عن تأخر الخطة", "أعلنت الإدارة تغيير الموعد بسبب نقص المواد.", "أدى ذلك إلى زيادة التكلفة ولذلك تغيرت الأولويات."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.EXPLAINER, "إعلان نظام جديد", "أعلنت المؤسسة إطلاق النظام وشرحت كيف يعمل.", "تبدأ المرحلة الأولى بالتحقق ثم ينتقل الطلب إلى المراجعة."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.RESULT_REPORT, "إعلان النتيجة النهائية", "أعلنت اللجنة أن الفرز اكتمل.", "أظهرت النتائج فوز المقترح الأول وانتهت العملية."),
    (EditorialFormat.STANDARD_NEWS, EditorialFormat.TREND_UPDATE, "إعلان قراءة اقتصادية", "أعلن المركز أن المؤشر ارتفع مقارنة بالشهر السابق.", "واصل النمو للفترة الثالثة."),
    (EditorialFormat.SERVICE, EditorialFormat.GUIDE, "دليل التقديم للبرنامج", "عليك التسجيل قبل الخميس.", "تشمل الشروط المستندات عبر المنصة؛ تأكد من الهوية ثم تجنب التأخير."),
    (EditorialFormat.SERVICE, EditorialFormat.FACT_CHECK, "فحص ادعاء عن رسوم التسجيل", "التقديم متاح برسوم محددة حتى الجمعة.", "تحققنا من الادعاء؛ السجل يثبت أن الادعاء خاطئ والمستندات مطلوبة."),
    (EditorialFormat.ANALYSIS, EditorialFormat.EXPLAINER, "لماذا وكيف تعمل الشبكة؟", "تعتمد الآلية على مرحلتين بسبب قيود السعة.", "تبدأ أولا بالفرز ثم تنتقل للمعالجة، أدى إلى بطء الخدمة. لذلك تراجع الأداء."),
    (EditorialFormat.RESULT_REPORT, EditorialFormat.TREND_UPDATE, "نتيجة نهائية بعد تغير ممتد", "انتهت الجولة. فاز الفريق.", "ارتفع رصيده مقارنة بالموسم السابق وواصل النمو."),
    (EditorialFormat.FEATURE, EditorialFormat.PROFILE, "حكاية فنانة ومسيرتها", "ولدت ريم في قرية صغيرة وبدأت مسيرتها هناك.", "في صباح المعرض روت محطتها الكبرى ثم عرضت أعمالها وتشغل حاليا إدارة المرسم."),
    (EditorialFormat.INTERVIEW, EditorialFormat.PROFILE, "حوار عن مسيرة باحث", "ولد سامر في بلدة جبلية وبدأ مسيرته مبكرا.", "سؤال: ما أهم محطة في عملك حاليا؟\nجواب: جائزة عام 2018.\nسؤال: ماذا تقود الآن؟\nجواب: أقود مختبرا."),
    (EditorialFormat.GUIDE, EditorialFormat.EXPLAINER, "كيف يعمل الجهاز وكيف تستخدمه؟", "تعتمد الآلية على مستشعر، وعليك فحص البطارية.", "تبدأ القراءة أولا ثم تظهر النتيجة؛ تأكد من المعايرة ثم تجنب الرطوبة."),
)


@pytest.mark.parametrize(
    ("candidate", "headline", "lead", "body"),
    POSITIVE_FIXTURES,
    ids=[item[0].value for item in POSITIVE_FIXTURES],
)
def test_raw_arabic_complete_profile_scenarios(candidate, headline, lead, body) -> None:
    assessment = _candidate(_assess(headline, lead, body), candidate)
    assert assessment.completeness is EditorialFormatCompleteness.COMPLETE
    assert assessment.missing_required_features == ()
    assert assessment.ambiguity is EditorialFormatAmbiguity.CLEAR


@pytest.mark.parametrize(
    ("candidate", "headline", "lead", "body"),
    NEGATIVE_FIXTURES,
    ids=[item[0].value for item in NEGATIVE_FIXTURES],
)
def test_raw_arabic_incomplete_profile_scenarios(candidate, headline, lead, body) -> None:
    assessment = _candidate(_assess(headline, lead, body), candidate)
    assert assessment.completeness is EditorialFormatCompleteness.INCOMPLETE
    assert assessment.missing_required_features
    assert assessment.ambiguity is EditorialFormatAmbiguity.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize(
    ("first", "second", "headline", "lead", "body"),
    COMPETITION_FIXTURES,
    ids=[f"{item[0].value}_vs_{item[1].value}" for item in COMPETITION_FIXTURES],
)
def test_raw_arabic_competition_scenarios(
    first, second, headline, lead, body,
) -> None:
    assessments = _assess(headline, lead, body)
    first_item = _candidate(assessments, first)
    second_item = _candidate(assessments, second)
    assert not first_item.missing_required_features
    assert not second_item.missing_required_features
    assert (
        second in first_item.competing_candidates
        or first in second_item.competing_candidates
    )
    assert (
        first_item.ambiguity is not EditorialFormatAmbiguity.CLEAR
        or second_item.ambiguity is not EditorialFormatAmbiguity.CLEAR
    )


def _symbolic(*features: F, cross: tuple[F, ...] = ()) -> EditorialTreatmentFeatureResult:
    return EditorialTreatmentFeatureResult(
        features=features, headline_features=(), lead_features=(), body_features=(),
        cross_section_features=cross, warnings=(),
    )


def test_every_input_returns_exactly_twelve_assessments_in_enum_order() -> None:
    assessments = EditorialFormatProfileEvaluator().evaluate(_symbolic())
    assert len(assessments) == 12
    assert tuple(item.candidate for item in assessments) == tuple(EditorialFormat)


def test_required_absence_core_completion_and_competed_partial_states() -> None:
    evaluator = EditorialFormatProfileEvaluator()
    absent = _candidate(evaluator.evaluate(_symbolic()), EditorialFormat.STANDARD_NEWS)
    complete = _candidate(
        evaluator.evaluate(_symbolic(F.EVENT_REPORTING)),
        EditorialFormat.STANDARD_NEWS,
    )
    partial = _candidate(
        evaluator.evaluate(_symbolic(F.PROCEDURAL_SERVICE, F.ACTIONABLE_GUIDANCE)),
        EditorialFormat.SERVICE,
    )
    assert absent.completeness is EditorialFormatCompleteness.INCOMPLETE
    assert complete.completeness is EditorialFormatCompleteness.COMPLETE
    assert partial.completeness is EditorialFormatCompleteness.PARTIAL


def test_strength_uses_coherence_not_raw_feature_count() -> None:
    evaluator = EditorialFormatProfileEvaluator()
    isolated = _candidate(
        evaluator.evaluate(_symbolic(F.EVENT_REPORTING)),
        EditorialFormat.STANDARD_NEWS,
    )
    coherent = _candidate(
        evaluator.evaluate(_symbolic(F.EVENT_REPORTING, cross=(F.EVENT_REPORTING,))),
        EditorialFormat.STANDARD_NEWS,
    )
    assert isolated.strength is SemanticEvidenceStrength.MODERATE
    assert coherent.strength is SemanticEvidenceStrength.STRONG


def test_all_ambiguity_states_are_representable() -> None:
    evaluator = EditorialFormatProfileEvaluator()
    insufficient = _candidate(evaluator.evaluate(_symbolic()), EditorialFormat.ANALYSIS)
    clear = _candidate(evaluator.evaluate(_symbolic(F.CAUSAL_EXPLANATION)), EditorialFormat.ANALYSIS)
    competing = _candidate(
        evaluator.evaluate(_symbolic(F.PROCEDURAL_SERVICE, F.ACTIONABLE_GUIDANCE)),
        EditorialFormat.GUIDE,
    )
    contradictory = _candidate(
        evaluator.evaluate(_symbolic(F.CAUSAL_EXPLANATION, F.MECHANISM_EXPLANATION)),
        EditorialFormat.ANALYSIS,
    )
    assert {
        insufficient.ambiguity, clear.ambiguity,
        competing.ambiguity, contradictory.ambiguity,
    } == set(EditorialFormatAmbiguity)


@pytest.mark.parametrize(
    ("features", "candidate"),
    (
        ((F.EVENT_REPORTING,), EditorialFormat.ANALYSIS),
        ((F.TEMPORAL_MOVEMENT,), EditorialFormat.RESULT_REPORT),
        ((F.COMPLETED_OUTCOME,), EditorialFormat.TREND_UPDATE),
        ((F.PROCEDURAL_SERVICE,), EditorialFormat.GUIDE),
        ((F.ACTIONABLE_GUIDANCE,), EditorialFormat.FACT_CHECK),
        ((F.CLAIM_VERIFICATION,), EditorialFormat.SERVICE),
        ((F.INTERVIEW_QA_STRUCTURE,), EditorialFormat.ANALYSIS),
    ),
)
def test_negative_controls_do_not_complete_unrelated_profiles(features, candidate) -> None:
    assessment = _candidate(
        EditorialFormatProfileEvaluator().evaluate(_symbolic(*features)), candidate,
    )
    assert assessment.completeness is EditorialFormatCompleteness.INCOMPLETE


def test_support_missing_disqualifiers_competitors_and_warnings_are_symbolic_ordered() -> None:
    assessment = _candidate(
        EditorialFormatProfileEvaluator().evaluate(
            _symbolic(F.EVENT_REPORTING, F.COMPLETED_OUTCOME, F.TEMPORAL_MOVEMENT)
        ),
        EditorialFormat.RESULT_REPORT,
    )
    assert assessment.supporting_features == (
        F.EVENT_REPORTING, F.COMPLETED_OUTCOME,
    )
    assert assessment.missing_required_features == ()
    assert assessment.disqualifying_features == (F.TEMPORAL_MOVEMENT,)
    assert EditorialFormat.TREND_UPDATE in assessment.competing_candidates
    assert assessment.warnings == (
        "PARTIAL_STRUCTURE", "DISQUALIFYING_FEATURE_PRESENT", "COMPETING_PROFILE",
    )


def test_evaluator_emits_no_selection_ranking_confidence_or_winner() -> None:
    assessments = EditorialFormatProfileEvaluator().evaluate(_symbolic(F.EVENT_REPORTING))
    assert not hasattr(assessments, "selected_format")
    source = inspect.getsource(EditorialFormatProfileEvaluator)
    assert not any(term in source for term in (
        "selected_format", "final_confidence", "winner", "ranking",
    ))


def test_no_v1_gate_provider_semantic_engine_or_resolver_coupling() -> None:
    source = inspect.getsource(EditorialFormatProfileEvaluator)
    forbidden = (
        "DeterministicEditorialFormatClassifier", "adjudication_gate", "OpenAI",
        "provider", "DeterministicCompositionalSemanticEngine", "Resolver",
    )
    assert not any(term in source for term in forbidden)


def test_no_benchmark_identifiers_or_corpus_paths_leak_into_evaluator_or_fixtures() -> None:
    source = (
        inspect.getsource(EditorialFormatProfileEvaluator)
        + Path(__file__).read_text(encoding="utf-8")
    ).casefold()
    forbidden = ("bench" + "mark/", "batch" + "_07", "batch" + "_08")
    assert not any(term in source for term in forbidden)


def test_v1_classifier_remains_unchanged() -> None:
    path = PROJECT_ROOT / "src/formatting/deterministic_editorial_format_classifier.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "a332c14f12c7cb6bad0fab214d1ff44512ccc9bbacd6f9ef9f86f262c278c117"
    )
