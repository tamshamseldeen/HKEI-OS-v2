"""Raw-Arabic structural tests for the Format V2 treatment extractor."""

import hashlib
import inspect
from pathlib import Path

import pytest

from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature as F
from src.formatting.editorial_treatment_feature_extractor import (
    EditorialTreatmentFeatureExtractor,
)
from src.intake.normalized_source import NormalizedSource


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _source(headline: str, lead: str, body: str) -> tuple[NormalizedSource, str]:
    return (
        NormalizedSource(
            title=headline, body=body, source_name="صحيفة تجريبية", language="ar",
        ),
        lead,
    )


def _extract(headline: str, lead: str, body: str):
    source, explicit_lead = _source(headline, lead, body)
    return EditorialTreatmentFeatureExtractor().extract(
        source=source, lead=explicit_lead,
    )


# Forty newly authored generic documents: thirty feature/negative pairs and ten
# distributed cross-section structures. They intentionally carry no benchmark
# identifiers, expected labels, or copied corpus text.
RAW_ARABIC_CASES = (
    ("event_positive", "أعلن المجلس قرارا جديدا", "صدر القرار بعد اجتماع معلن.", "وأوضح البيان موعد التنفيذ.", F.EVENT_REPORTING, True),
    ("event_date_negative", "اجتماع يوم الثلاثاء", "عقد اللقاء في العاشر من الشهر.", "تضمن الحضور ثلاثة أعضاء.", F.EVENT_REPORTING, False),
    ("temporal_positive", "ارتفاع المؤشر خلال عام", "ارتفع المؤشر مقارنة بالعام السابق.", "واصل النمو للشهر الثالث.", F.TEMPORAL_MOVEMENT, True),
    ("temporal_static_negative", "قيمة المؤشر اليوم", "بلغ المؤشر 120 نقطة في 5 مايو.", "هذه هي القراءة الحالية المنشورة.", F.TEMPORAL_MOVEMENT, False),
    ("outcome_positive", "النتيجة النهائية للمسابقة", "انتهت المسابقة بعد الجولة الأخيرة.", "فاز الفريق الأزرق وسجل نقطتين.", F.COMPLETED_OUTCOME, True),
    ("outcome_future_negative", "موعد المباراة المقبلة", "ستقام المباراة غدا.", "يستهدف الفريق الفوز بثلاث نقاط.", F.COMPLETED_OUTCOME, False),
    ("causal_positive", "أسباب تعطل المشروع", "تأخر العمل بسبب نقص المواد.", "أدى ذلك إلى زيادة التكلفة ولذلك تغير الجدول.", F.CAUSAL_EXPLANATION, True),
    ("causal_incidental_negative", "تحديث المشروع", "تغير الموعد بسبب الطقس.", "نشر الفريق الجدول الجديد.", F.CAUSAL_EXPLANATION, False),
    ("mechanism_positive", "كيف يعمل نظام التنقية؟", "تعتمد الآلية على ثلاث مراحل.", "تبدأ المرحلة الأولى بالترشيح ثم ينتقل الماء إلى المعالجة.", F.MECHANISM_EXPLANATION, True),
    ("mechanism_incidental_negative", "افتتاح محطة جديدة", "تعمل المنظومة في المدينة منذ شهر.", "قدم المسؤول خلفية موجزة عن المشروع.", F.MECHANISM_EXPLANATION, False),
    ("guidance_positive", "نصائح لحماية الحساب", "عليك تغيير كلمة المرور وتجنب الروابط المجهولة.", "تأكد من التحقق الثنائي ثم قم بمراجعة الأجهزة.", F.ACTIONABLE_GUIDANCE, True),
    ("guidance_word_negative", "حديث عن نصيحة عامة", "ذكر الضيف أن النصيحة مفيدة.", "لم يقدم خطوات أو أفعالا للقارئ.", F.ACTIONABLE_GUIDANCE, False),
    ("service_positive", "فتح باب التسجيل في البرنامج", "التسجيل متاح حتى نهاية الشهر.", "تشمل الشروط إثبات الهوية والمستندات المطلوبة عبر المنصة.", F.PROCEDURAL_SERVICE, True),
    ("service_official_negative", "بيان رسمي عن الإجراءات", "أعلن المكتب مراجعة الإجراء الداخلي.", "لم يحدد البيان موعدا أو شروطا أو طريقة تقديم للجمهور.", F.PROCEDURAL_SERVICE, False),
    ("verification_positive", "فحص ادعاء متداول", "تحققنا من الادعاء بمراجعة السجلات.", "الادعاء غير صحيح ولا تدعمه الوثائق.", F.CLAIM_VERIFICATION, True),
    ("verification_confirmation_negative", "المؤسسة تؤكد الخبر", "أكدت الجهة صدور البيان.", "نقلت الصحيفة التأكيد دون فحص ادعاء أو إصدار حكم.", F.CLAIM_VERIFICATION, False),
    ("urgent_positive", "عاجل: تطور جديد الآن", "المعلومات الأولية لا تزال محدودة.", "التفاصيل تباعا حتى اللحظة.", F.URGENT_BREAKING_SIGNAL, True),
    ("urgent_recent_negative", "خبر نُشر قبل قليل", "صدر التحديث الساعة العاشرة.", "يعرض التقرير معلومات مكتملة ومستقرة.", F.URGENT_BREAKING_SIGNAL, False),
    ("list_positive", "أفضل 3 طرق للتنظيم", "قائمة مرتبة للاستخدام اليومي.", "1. حدد الأولويات\n2. قسم المهام\n3. راجع النتائج", F.LIST_OR_RANKING_STRUCTURE, True),
    ("list_incidental_negative", "تفاصيل الاجتماع", "ناقش الحضور ثلاث نقاط.", "ذكر التقرير أولا الميزانية ثم المكان دون قائمة منظمة.", F.LIST_OR_RANKING_STRUCTURE, False),
    ("qa_positive", "حوار حول التصميم", "مقابلة منظمة بصيغة سؤال وجواب.", "سؤال: ما الهدف؟\nجواب: تبسيط الاستخدام.\nسؤال: ما الخطوة التالية؟\nجواب: اختبار النموذج.", F.INTERVIEW_QA_STRUCTURE, True),
    ("qa_quotes_negative", "تصريحات من لقاء عام", "قال المتحدث إن المشروع مستمر.", "وأضاف: نراجع الخطة. وقال آخر: ننتظر النتائج.", F.INTERVIEW_QA_STRUCTURE, False),
    ("opinion_positive", "في رأيي نحتاج نهجا مختلفا", "أرى أن الحل الحالي غير كاف لأن أثره محدود.", "أولا يجب تغيير الافتراض، ولذلك أدافع عن البديل.", F.OPINION_ARGUMENTATION, True),
    ("opinion_quote_negative", "خبير يعرض وجهة نظره", "قال الخبير: أعتقد أن الخطة جيدة.", "نقل التقرير الرأي ثم عرض موعد الاجتماع.", F.OPINION_ARGUMENTATION, False),
    ("comparison_positive", "مقارنة بين خيارين", "الخيار الأول أسرع بينما الثاني أقل تكلفة.", "الأول أفضل للوقت وفي المقابل يملك الثاني مزايا للسعر.", F.COMPARATIVE_STRUCTURE, True),
    ("comparison_number_negative", "فرق رقمي بسيط", "بلغ الأول 40 مقابل 39 للثاني.", "لم يناقش النص خصائص أو مزايا أو عيوبا.", F.COMPARATIVE_STRUCTURE, False),
    ("narrative_positive", "صباح مختلف في المكتبة", "في صباح هادئ دخلت سلمى القاعة.", "ثم التقت القراء وبعد ذلك روت كيف تغير المكان.", F.NARRATIVE_SCENE_STRUCTURE, True),
    ("narrative_negative", "المكتبة تفتح أبوابها", "أعلنت الإدارة مواعيد العمل.", "تضمن البيان عدد القاعات والخدمات.", F.NARRATIVE_SCENE_STRUCTURE, False),
    ("biography_positive", "مسيرة مهندسة عبر العقود", "ولدت ليلى في بلدة صغيرة وبدأت مسيرتها مبكرا.", "حققت محطة بارزة عام 2010 وتشغل حاليا منصبا تعليميا.", F.BIOGRAPHICAL_ARC, True),
    ("biography_negative", "مهندسة تعلن مبادرة", "أعلنت ليلى المبادرة اليوم.", "شرح البيان أهداف المبادرة الجديدة.", F.BIOGRAPHICAL_ARC, False),
    ("cross_temporal", "المؤشر الحالي عند 80", "ارتفع المؤشر هذا الأسبوع.", "وجاءت القراءة مقارنة بالشهر السابق وواصلت الاتجاه.", F.TEMPORAL_MOVEMENT, True),
    ("cross_outcome", "النتيجة النهائية أصبحت معلنة", "اكتملت عملية الفرز.", "أظهرت النتائج فوز القائمة الأولى.", F.COMPLETED_OUTCOME, True),
    ("cross_causal", "قيود جديدة على التشغيل", "توقف الخط بسبب نقص الطاقة.", "أدى ذلك إلى خفض الإنتاج ولذلك تأخر التسليم.", F.CAUSAL_EXPLANATION, True),
    ("cross_mechanism", "كيف يعمل جهاز القياس؟", "تعتمد الآلية على مستشعر داخلي.", "تبدأ القراءة أولا ثم ينتقل القياس إلى شاشة العرض.", F.MECHANISM_EXPLANATION, True),
    ("cross_guidance", "ما الذي ينبغي فعله قبل السفر؟", "عليك مراجعة الوثائق.", "أولا راجع الصلاحية، وبعد ذلك احتفظ بنسخة.", F.ACTIONABLE_GUIDANCE, True),
    ("cross_service", "بدء التسجيل في الدورة", "التقديم متاح هذا الأسبوع.", "الموعد حتى الخميس والمستندات ترفع عبر المنصة.", F.PROCEDURAL_SERVICE, True),
    ("cross_verification", "ادعاء عن إغلاق المرفق", "راجعنا السجل الرسمي للتحقق.", "لا دليل على الإغلاق والادعاء خاطئ.", F.CLAIM_VERIFICATION, True),
    ("cross_urgent", "عاجل: تحديث الآن", "المعلومات الأولية قيد التطور.", "لا تزال الفرق تعمل والتفاصيل تباعا.", F.URGENT_BREAKING_SIGNAL, True),
    ("cross_comparison", "مقارنة بين النسختين", "النسخة الحالية أسرع.", "النسخة السابقة كانت أقل تكلفة ولها مزايا أخرى.", F.COMPARATIVE_STRUCTURE, True),
    ("cross_biography", "حكاية باحثة بدأت من الريف", "ولدت مها هناك وبدأت مسيرتها في مدرسة صغيرة.", "حققت محطة مهمة عام 2015 وتقود حاليا مركزا بحثيا.", F.BIOGRAPHICAL_ARC, True),
)


@pytest.mark.parametrize(
    ("name", "headline", "lead", "body", "feature", "present"),
    RAW_ARABIC_CASES,
    ids=[item[0] for item in RAW_ARABIC_CASES],
)
def test_raw_arabic_document_treatment_fixtures(
    name: str, headline: str, lead: str, body: str, feature: F, present: bool,
) -> None:
    result = _extract(headline, lead, body)
    assert (feature in result.features) is present, name


@pytest.mark.parametrize("case", RAW_ARABIC_CASES[30:], ids=[item[0] for item in RAW_ARABIC_CASES[30:]])
def test_distributed_fixtures_require_cross_section_reasoning(case) -> None:
    _, headline, lead, body, feature, _ = case
    result = _extract(headline, lead, body)
    assert feature in result.cross_section_features
    assert feature not in result.headline_features
    assert feature not in result.lead_features
    assert feature not in result.body_features


def test_all_fifteen_features_have_positive_structural_coverage() -> None:
    positive = {item[4] for item in RAW_ARABIC_CASES if item[5]}
    assert positive == set(F)


def test_section_results_and_aggregate_are_deterministic_immutable_tuples() -> None:
    result = _extract(
        "أعلن المجلس قرارا", "صدر القرار بعد الاجتماع.",
        "أوضح البيان تفاصيل التنفيذ.",
    )
    repeated = _extract(
        "أعلن المجلس قرارا", "صدر القرار بعد الاجتماع.",
        "أوضح البيان تفاصيل التنفيذ.",
    )
    assert result == repeated
    assert all(isinstance(getattr(result, name), tuple) for name in (
        "features", "headline_features", "lead_features", "body_features",
        "cross_section_features", "warnings",
    ))


def test_duplicated_lead_is_not_independent_body_evidence() -> None:
    lead = "ارتفع المؤشر مقارنة بالشهر السابق."
    result = _extract("تحديث المؤشر", lead, f"{lead}\nنشر المركز القراءة الجديدة.")
    assert F.TEMPORAL_MOVEMENT in result.lead_features
    assert F.TEMPORAL_MOVEMENT not in result.body_features
    assert "DUPLICATED_LEAD_REMOVED_FROM_BODY_ANALYSIS" in result.warnings


def test_default_lead_uses_first_body_paragraph_and_deduplicates_it() -> None:
    source = NormalizedSource(
        title="تحديث المؤشر",
        body="ارتفع المؤشر مقارنة بالشهر السابق.\nنشر المركز القراءة الجديدة.",
        source_name="صحيفة تجريبية",
    )
    result = EditorialTreatmentFeatureExtractor().extract(source=source)
    assert F.TEMPORAL_MOVEMENT in result.lead_features
    assert F.TEMPORAL_MOVEMENT not in result.body_features


def test_no_topic_labels_selection_confidence_or_ambiguity_are_emitted() -> None:
    result = _extract("إعلان تقني صحي حكومي", "وردت أسماء مجالات متعددة.", "لا توجد بنية تحريرية كافية.")
    assert result.features == ()
    assert not hasattr(result, "selected_format")
    assert not hasattr(result, "confidence")
    assert not hasattr(result, "ambiguity")


def test_extractor_has_no_v1_profile_gate_provider_or_resolver_coupling() -> None:
    source = inspect.getsource(EditorialTreatmentFeatureExtractor)
    forbidden = (
        "DeterministicEditorialFormatClassifier", "EditorialFormatCandidateAssessment",
        "OpenAI", "provider", "adjudication_gate", "Resolver", "selected_format",
    )
    assert not any(term in source for term in forbidden)


def test_no_benchmark_identifiers_or_corpus_paths_leak_into_extractor_or_fixtures() -> None:
    source = (
        inspect.getsource(EditorialTreatmentFeatureExtractor)
        + Path(__file__).read_text(encoding="utf-8")
    ).casefold()
    forbidden = ("bench" + "mark/", "batch" + "_07", "batch" + "_08")
    assert not any(term in source for term in forbidden)


def test_v1_classifier_remains_unchanged() -> None:
    path = PROJECT_ROOT / "src/formatting/deterministic_editorial_format_classifier.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "a332c14f12c7cb6bad0fab214d1ff44512ccc9bbacd6f9ef9f86f262c278c117"
    )
