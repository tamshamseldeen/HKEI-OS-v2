"""Generic raw-Arabic precision/recall fixtures for the HKEI-192 refinement."""

from dataclasses import dataclass

import pytest

from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature as F
from src.formatting.editorial_treatment_feature_extractor import EditorialTreatmentFeatureExtractor
from src.intake.normalized_source import NormalizedSource


@dataclass(frozen=True)
class Fixture:
    name: str
    headline: str
    lead: str
    body: str
    feature: F
    expected: bool
    cross: bool = False
    variation: bool = False
    control: bool = False


def _fx(name, headline, lead, body, feature, expected=True, **flags):
    return Fixture(name, headline, lead, body, feature, expected, **flags)


FIXTURES = (
    # EVENT_REPORTING: nominal, passive, inflected, and statement-led forms.
    _fx("event_nominal_decision", "قرار جديد للمجلس", "أوضح المجلس تفاصيل التنفيذ.", "يبدأ العمل الأسبوع المقبل.", F.EVENT_REPORTING, variation=True),
    _fx("event_nominal_launch", "انطلاق المبادرة", "قدمت المؤسسة برنامج المبادرة.", "يشمل البرنامج ثلاث مدن.", F.EVENT_REPORTING, variation=True),
    _fx("event_passive_announcement", "تم الإعلان عن الخطة", "نشرت الوزارة تفاصيلها.", "يبدأ التنفيذ لاحقا.", F.EVENT_REPORTING, variation=True),
    _fx("event_passive_signature", "تم توقيع الاتفاق", "أكدت الشركة بدء التنفيذ.", "يشمل الاتفاق مرحلتين.", F.EVENT_REPORTING, variation=True),
    _fx("event_inflected_opening", "افتتحت الهيئة المركز", "شهد الافتتاح حضورا عاما.", "بدأ المركز عمله.", F.EVENT_REPORTING, variation=True),
    _fx("event_institutional_approval", "موافقة رسمية", "وافق المجلس على المشروع.", "نشر المجلس القرار.", F.EVENT_REPORTING),
    _fx("event_statement_led", "تحديث جديد", "أفادت الإدارة ببدء البرنامج.", "وأوضح البيان التفاصيل.", F.EVENT_REPORTING),
    _fx("event_entity_only_control", "المجلس والمؤسسة", "تواصل أعضاء من الجهتين.", "ناقشوا موضوعات عامة بلا نتيجة محددة.", F.EVENT_REPORTING, False, control=True),

    # PROCEDURAL_SERVICE: three deliberately distributed structures.
    _fx("service_application", "خدمة إصدار البطاقة", "بدأ تقديم الطلب.", "آخر موعد الخميس والوثائق ترفع عبر الموقع.", F.PROCEDURAL_SERVICE, cross=True, variation=True),
    _fx("service_booking", "حجز موعد للمراجعة", "بدأ الحجز للمراجعة.", "المراكز تعمل حتى الخامسة وتبلغ الرسوم عشرة ريالات.", F.PROCEDURAL_SERVICE, cross=True),
    _fx("service_eligibility", "فتح باب الاشتراك", "الاشتراك يبدأ الأحد.", "الفئات المستحقة تقدم الأوراق المطلوبة في الفرع.", F.PROCEDURAL_SERVICE, cross=True, variation=True),
    _fx("service_renewal", "تجديد التصريح", "التجديد متاح حتى نهاية الشهر.", "يشترط إثبات الهوية عبر المنصة.", F.PROCEDURAL_SERVICE),
    _fx("service_official_steps", "إجراءات التقديم", "تبدأ المواعيد صباحا.", "ترفع المستندات عبر الموقع وتدفع الرسوم إلكترونيا.", F.PROCEDURAL_SERVICE, variation=True),
    _fx("service_location_schedule", "طلب الخدمة في الفروع", "الحصول على الخدمة بالحجز.", "توضح المراكز أيام العمل والموعد المتاح.", F.PROCEDURAL_SERVICE),
    _fx("service_statement_control", "بيان عن خدمة عامة", "أعلنت الهيئة مراجعة إجراءاتها.", "لم تحدد موعدا أو شروطا للتقديم.", F.PROCEDURAL_SERVICE, False, control=True),

    # ACTIONABLE_GUIDANCE: imperatives, advisory verbs, and nominal advice.
    _fx("guidance_distributed_imperative", "حماية الحساب", "عليك مراجعة الإعدادات.", "استخدم كلمة قوية، وبعد ذلك تأكد من التنبيهات.", F.ACTIONABLE_GUIDANCE, cross=True, variation=True),
    _fx("guidance_distributed_nominal", "توصيات للسلامة", "يوصى بفحص الجهاز.", "احذر الأسلاك المكشوفة واستخدم غطاء عازلا.", F.ACTIONABLE_GUIDANCE, cross=True, variation=True),
    _fx("guidance_distributed_advisory", "قبل السفر", "من الضروري مراجعة الوثائق.", "اختر نسخة احتياطية وتجنب حمل الأوراق الأصلية.", F.ACTIONABLE_GUIDANCE, cross=True),
    _fx("guidance_prevention", "الوقاية المنزلية", "ينبغي تهوية الغرفة وتجنب الدخان.", "تأكد من تنظيف المرشح.", F.ACTIONABLE_GUIDANCE),
    _fx("guidance_recommendation", "سلوك موصى به", "نوصي باستخدام الإضاءة المناسبة.", "احرص على الراحة ثم راجع وضع الشاشة.", F.ACTIONABLE_GUIDANCE, variation=True),
    _fx("guidance_ordered", "خطوات يومية", "عليك البدء مبكرا.", "أولا حدد المهمة وبعد ذلك راجع النتيجة.", F.ACTIONABLE_GUIDANCE),
    _fx("guidance_mention_control", "نصائح متداولة", "ذكر المتحدث وجود نصائح كثيرة.", "لم يوص القارئ بفعل محدد.", F.ACTIONABLE_GUIDANCE, False, control=True),

    # MECHANISM_EXPLANATION: how-it-works, process, definition, and Q/A framing.
    _fx("mechanism_distributed_how", "كيف يعمل المرشح؟", "يعتمد على غشاء دقيق.", "تبدأ العملية بالضخ ثم تنتقل المياه إلى الخزان.", F.MECHANISM_EXPLANATION, cross=True, variation=True),
    _fx("mechanism_distributed_nominal", "آلية عمل المحرك", "يتكون النظام من وحدتين.", "في البداية تدور الأولى ثم يتبعها التبريد.", F.MECHANISM_EXPLANATION, cross=True, variation=True),
    _fx("mechanism_distributed_process", "مسار العملية", "تتم العملية آليا.", "المرحلة الأولى للفحص وتليها مرحلة الفرز.", F.MECHANISM_EXPLANATION, cross=True),
    _fx("mechanism_functioning", "طريقة عمل الحساس", "يعمل النظام عند تغير الضوء.", "تبدأ القراءة ثم ينتقل القياس إلى الشاشة.", F.MECHANISM_EXPLANATION, variation=True),
    _fx("mechanism_question", "ما هي الآلية؟", "تعتمد الآلية على التحقق المتتابع.", "أولا يفحص الرمز وبعد ذلك يفتح النظام.", F.MECHANISM_EXPLANATION),
    _fx("mechanism_sequence", "كيفية عمل المضخة", "تمر العملية بمراحل.", "تبدأ بالسحب ثم تنتهي بالدفع.", F.MECHANISM_EXPLANATION),
    _fx("mechanism_word_control", "منظومة جديدة", "تعمل المنظومة في المبنى.", "أعلنت الإدارة موعد افتتاحها فقط.", F.MECHANISM_EXPLANATION, False, control=True),

    # CLAIM_VERIFICATION: claim + evaluation/evidence + conclusion.
    _fx("verify_distributed_claim", "ادعاء عن إغلاق الطريق", "راجعنا السجل الرسمي.", "لا دليل على الإغلاق، والادعاء خاطئ.", F.CLAIM_VERIFICATION, cross=True),
    _fx("verify_distributed_rumor", "شائعة عن رسوم جديدة", "فحصنا القرارات المنشورة.", "تؤكد الأدلة عدم صدورها والخبر زائف.", F.CLAIM_VERIFICATION, cross=True, variation=True),
    _fx("verify_distributed_attribution", "تصريح منسوب إلى الوزير", "تتبعت المصادر أصل التصريح.", "ثبت بطلانه وخلاصة التحقق أنه غير صحيح.", F.CLAIM_VERIFICATION, cross=True, variation=True),
    _fx("verify_documents", "معلومة متداولة عن الدعم", "أظهرت الوثائق بعد المراجعة اختلاف الرقم.", "الادعاء مضلل.", F.CLAIM_VERIFICATION, variation=True),
    _fx("verify_confirmation", "القول المتداول عن الموعد", "تحققنا بمراجعة الجدول.", "ثبتت صحته والخبر صحيح.", F.CLAIM_VERIFICATION),
    _fx("verify_partial", "منشور متداول عن النتائج", "دققنا الأرقام الرسمية.", "الادعاء صحيح جزئيا.", F.CLAIM_VERIFICATION),
    _fx("verify_denial_control", "الهيئة تنفي شائعة", "نفت الهيئة القول المتداول.", "لم يعرض التقرير فحصا أو أدلة أو خلاصة تحقق.", F.CLAIM_VERIFICATION, False, control=True),

    # COMPLETED_OUTCOME: final figures and completed results, not plans.
    _fx("outcome_distributed_final", "الحصيلة النهائية", "اختتمت المسابقة مساء.", "فاز الفريق وسجل ثلاث نقاط.", F.COMPLETED_OUTCOME, cross=True),
    _fx("outcome_distributed_ranking", "الترتيب النهائي", "انتهى السباق.", "جاء في المركز الأول متسابق جديد.", F.COMPLETED_OUTCOME, cross=True, variation=True),
    _fx("outcome_distributed_count", "الأرقام النهائية", "اكتمل العدد بعد الإغلاق.", "بلغ العدد مئة طلب.", F.COMPLETED_OUTCOME, cross=True, variation=True),
    _fx("outcome_official", "النتائج الرسمية", "اختتم الفرز.", "أظهرت النتائج فوز القائمة.", F.COMPLETED_OUTCOME),
    _fx("outcome_completed", "إنجاز العمل", "اكتملت المرحلة الأخيرة.", "سجلت الحصيلة خمس وحدات منجزة.", F.COMPLETED_OUTCOME, variation=True),
    _fx("outcome_loss", "نتيجة نهائية للمباراة", "انتهت المباراة.", "خسر الفريق بهدف.", F.COMPLETED_OUTCOME),
    _fx("outcome_future_control", "الهدف النهائي للخطة", "من المقرر اكتمالها غدا.", "يستهدف الفريق تسجيل خمس نقاط.", F.COMPLETED_OUTCOME, False, control=True),

    # CAUSAL_EXPLANATION precision controls: one incidental passage stays weak.
    _fx("causal_analysis", "أسباب تراجع الإنتاج", "يرجع إلى نقص المواد.", "أدى ذلك إلى تأخر التسليم وتداعيات على التكلفة.", F.CAUSAL_EXPLANATION, variation=True),
    _fx("causal_event_incidental_1", "أعلنت الوزارة قرارا", "أوضح البيان موعد التنفيذ.", "تأخر الموعد بسبب الطقس، ما تسبب في تغيير اليوم.", F.CAUSAL_EXPLANATION, False, control=True),
    _fx("causal_event_incidental_2", "افتتحت الهيئة المركز", "شهد الافتتاح حضورا واسعا.", "انخفض الحضور بسبب المطر، ولذلك أغلقت بوابة جانبية.", F.CAUSAL_EXPLANATION, False, control=True),
    _fx("causal_event_incidental_3", "وافق المجلس على المشروع", "نشر المجلس القرار.", "تغير بند بسبب التكلفة، ما أدى إلى تعديل الجدول.", F.CAUSAL_EXPLANATION, False, control=True),
    _fx("causal_connector_only", "تحديث إداري", "تغير الجدول بسبب ظرف طارئ.", "نشرت الإدارة النسخة الجديدة.", F.CAUSAL_EXPLANATION, False, control=True),
    _fx("causal_effect_only", "متابعة المشروع", "أدى ذلك إلى تغيير الموعد.", "لم يشرح التقرير سببا أو سلسلة آثار.", F.CAUSAL_EXPLANATION, False, control=True),
    _fx("causal_method_control", "كيف تعمل الآلة؟", "تعتمد الآلية على ضغط الهواء.", "تبدأ بالدفع ثم ينتهي المسار عند الصمام.", F.CAUSAL_EXPLANATION, False, control=True),

    # TEMPORAL_MOVEMENT regression controls.
    _fx("trend_valid", "اتجاه المؤشر", "ارتفع المؤشر مقارنة بالشهر السابق.", "واصل النمو للعام الثالث.", F.TEMPORAL_MOVEMENT),
    _fx("trend_static_value", "قيمة المؤشر", "بلغ المؤشر 90 نقطة اليوم.", "هذه قراءة ثابتة منشورة.", F.TEMPORAL_MOVEMENT, False, control=True),
    _fx("trend_date_only", "بيانات شهر مايو", "نشر الرقم في الخامس من مايو.", "لا توجد مقارنة زمنية.", F.TEMPORAL_MOVEMENT, False, control=True),
    _fx("trend_completed_outcome", "النتيجة النهائية", "انتهت المسابقة أمس.", "فاز الفريق وسجل هدفين.", F.TEMPORAL_MOVEMENT, False, control=True),
    _fx("trend_direction_no_reference", "ارتفاع السعر", "ارتفع السعر إلى عشرة ريالات.", "أعلنت الجهة الرقم الحالي.", F.TEMPORAL_MOVEMENT, False, control=True),

    # Positive coverage for the other seven treatment features.
    _fx("coverage_urgent", "عاجل الآن", "المعلومات الأولية لا تزال محدودة.", "التفاصيل تباعا حتى اللحظة.", F.URGENT_BREAKING_SIGNAL),
    _fx("coverage_list", "أفضل ثلاث خطوات", "قائمة عملية.", "1. ابدأ مبكرا\n2. راجع العمل\n3. احفظ النسخة", F.LIST_OR_RANKING_STRUCTURE),
    _fx("coverage_qa", "حوار منظم", "سؤال وجواب.", "سؤال: ما الهدف؟\nجواب: التعلم.\nسؤال: ما التالي؟\nجواب: التطبيق.", F.INTERVIEW_QA_STRUCTURE),
    _fx("coverage_opinion", "في رأيي يلزم التغيير", "أرى أن النهج ضعيف لأن أثره محدود.", "أولا نغير الفرضية ولذلك نختبر البديل.", F.OPINION_ARGUMENTATION),
    _fx("coverage_comparison", "مقارنة بين خيارين", "الأول أسرع بينما الثاني أقل تكلفة.", "الأول أفضل وفي المقابل للثاني مزايا أخرى.", F.COMPARATIVE_STRUCTURE),
    _fx("coverage_narrative", "صباح في المحطة", "في صباح هادئ دخلت سلمى.", "ثم انتظرت وبعد ذلك روت ما حدث.", F.NARRATIVE_SCENE_STRUCTURE),
    _fx("coverage_biography", "مسيرة باحثة", "ولدت مها وبدأت مسيرتها مبكرا.", "حققت محطة عام 2012 وتقود حاليا مركزا.", F.BIOGRAPHICAL_ARC),
)


def _extract(fixture: Fixture):
    source = NormalizedSource(
        title=fixture.headline,
        body=fixture.body,
        source_name="صحيفة عربية تجريبية",
        language="ar",
    )
    return EditorialTreatmentFeatureExtractor().extract(source=source, lead=fixture.lead)


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda item: item.name)
def test_generic_raw_arabic_fixture(fixture: Fixture) -> None:
    result = _extract(fixture)
    assert (fixture.feature in result.features) is fixture.expected
    if fixture.cross and fixture.expected:
        assert fixture.feature in result.cross_section_features
        assert fixture.feature not in result.headline_features
        assert fixture.feature not in result.lead_features
        assert fixture.feature not in result.body_features


def test_required_fixture_distribution_and_independent_annotations() -> None:
    requirements = {
        F.EVENT_REPORTING: 8,
        F.PROCEDURAL_SERVICE: 7,
        F.ACTIONABLE_GUIDANCE: 7,
        F.MECHANISM_EXPLANATION: 7,
        F.CLAIM_VERIFICATION: 7,
        F.COMPLETED_OUTCOME: 7,
        F.CAUSAL_EXPLANATION: 7,
        F.TEMPORAL_MOVEMENT: 5,
    }
    assert len(FIXTURES) >= 50
    assert all(sum(f.feature is feature for f in FIXTURES) >= count for feature, count in requirements.items())
    assert sum(f.cross for f in FIXTURES) >= 15
    assert sum(f.variation for f in FIXTURES) >= 15
    assert sum(f.control for f in FIXTURES) >= 15
    assert {f.feature for f in FIXTURES if f.expected} == set(F)


def test_fixture_level_precision_recall_audit_has_no_critical_collapse() -> None:
    extractor_results = {fixture.name: _extract(fixture) for fixture in FIXTURES}
    for feature in F:
        annotated = [fixture for fixture in FIXTURES if fixture.feature is feature]
        positives = sum(fixture.expected for fixture in annotated)
        correct = sum(
            fixture.expected and feature in extractor_results[fixture.name].features
            for fixture in annotated
        )
        false = sum(
            not fixture.expected and feature in extractor_results[fixture.name].features
            for fixture in annotated
        )
        missed = positives - correct
        precision = correct / (correct + false) if correct + false else 1.0
        recall = correct / positives if positives else 1.0
        assert precision == 1.0, (feature, positives, correct, false, missed)
        assert recall == 1.0, (feature, positives, correct, false, missed)
