"""Deterministic document-level treatment feature extraction for Format V2."""

import re

from src.intake.normalized_source import NormalizedSource

from .editorial_treatment_feature import EditorialTreatmentFeature as Feature
from .editorial_treatment_feature_result import EditorialTreatmentFeatureResult


class EditorialTreatmentFeatureExtractor:
    """Extract symbolic treatment structure without classifying a Format."""

    _EVENT = (
        "اعلن", "اعلنت", "قرر", "قررت", "افاد", "افادت", "اصدر", "اصدرت",
        "كشف", "كشفت", "وقع", "وقعت", "شهد", "شهدت", "بيان", "تطور",
        "دشن", "دشنت", "اطلق", "اطلقت", "افتتح", "افتتحت", "اعتمد",
        "اعتمدت", "وافق", "وافقت", "جرى الاعلان", "تم الاعلان", "تم توقيع",
    )
    _EVENT_NOMINAL = (
        "اعلان", "قرار", "بدء", "انطلاق", "توقيع", "اجتماع", "موافقة",
        "افتتاح", "اطلاق", "اعتماد", "تحديث", "تطورات",
    )
    _EVENT_CONTEXT = (
        "المجلس", "اللجنة", "الوزارة", "الهيئة", "المؤسسة", "الشركة",
        "الادارة", "الاتحاد", "الجهة", "السلطات", "المشروع", "البرنامج",
        "المبادرة", "الخطة", "التنفيذ", "التفاصيل", "رسميا",
    )
    _DIRECTION = (
        "ارتفع", "ارتفعت", "انخفض", "انخفضت", "زاد", "زادت", "تراجع",
        "تراجعت", "صعد", "صعدت", "هبط", "هبطت", "نمو", "انكماش",
        "تسارع", "تباطا", "تحسن", "تحسنت",
    )
    _REFERENCE = (
        "مقارنة", "مقابل", "عن العام الماضي", "عن الشهر الماضي", "سابقا",
        "الفترة السابقة", "العام السابق", "الشهر السابق", "منذ", "خلال عامين",
        "على مدى", "للشهر", "للعام الثالث",
    )
    _OUTCOME_FINAL = (
        "النتيجة النهائية", "نتيجة نهائية", "انتهت", "اختتمت", "حسم",
        "حسمت", "اكتمل", "اكتملت", "نهائي", "الترتيب النهائي",
        "انتهى", "اختتم", "انجز", "انجزت", "اكتمل العدد", "الحصيلة النهائية",
        "الارقام النهائية", "النتائج الرسمية", "النتيجة الرسمية",
    )
    _OUTCOME_OBSERVED = (
        "فاز", "فازت", "خسر", "خسرت", "تعادل", "سجل", "حصل على",
        "جاء في المركز", "بلغت الحصيلة", "اظهرت النتائج", "اسفرت النتائج",
        "حل في المركز", "احرز", "احرزت", "بلغ العدد", "سجلت الحصيلة",
    )
    _FUTURE = (
        "سيقام", "ستقام", "سيعقد", "ستعقد", "من المقرر", "متوقع",
        "يتوقع", "خطة", "يستهدف", "موعد المباراة", "غدا",
    )
    _CAUSE = (
        "بسبب", "نتيجة ل", "يرجع الى", "تعود الى", "مدفوعا ب", "نظرا ل",
        "العامل الرئيسي", "من اسباب",
    )
    _EFFECT = (
        "ادى الى", "ادت الى", "ادى ذلك الى", "ادت تلك الى", "ما تسبب في", "لذلك", "ومن ثم", "ينعكس على",
        "يؤدي الى", "تداعيات", "اثره", "اثر ذلك", "النتيجة المترتبة",
    )
    _MECHANISM = (
        "كيف يعمل", "الية عمل", "كيف تتم", "تعمل المنظومة", "يتكون النظام",
        "تمر العملية", "تجري العملية", "تعتمد الالية", "مراحل العملية",
        "طريقة عمل", "كيفية عمل", "ما هي الالية", "يعمل النظام", "تتم العملية",
        "يقوم النظام", "تنتقل البيانات", "مسار العملية",
    )
    _PROCESS = (
        "المرحلة الاولى", "المرحلة الثانية", "اولا", "ثانيا", "بعد ذلك", "وبعد ذلك",
        "ثم", "ينتقل", "تبدأ", "تنتهي", "خطوة",
        "تبدا", "يتبعها", "تليها", "في البداية", "في النهاية", "مرحلة",
    )
    _GUIDANCE = (
        "عليك", "ينبغي", "ينصح", "احرص", "اتبع",
        "لا تفعل", "افعل", "للقارئ",
        "يوصى", "نوصي", "يفضل", "من المهم", "من الضروري", "حافظ على",
        "ابتعد عن", "استعمل",
    )
    _ACTION_DETAIL = (
        "اولا", "ثانيا", "خطوات", "نصائح", "قم ب", "بعد ذلك", "وبعد ذلك", "قبل ان",
        "يجب ان", "من الافضل", "اختر", "تجنب", "تاكد",
        "ينبغي", "يوصى", "حافظ على", "استخدم", "راجع", "احذر", "احرص",
    )
    _SERVICE_ANCHOR = (
        "التقديم", "التسجيل", "الحجز", "طلب الخدمة", "الحصول على",
        "استلام", "التجديد", "التسجيل متاح", "باب التسجيل",
        "تقديم الطلب", "رفع الطلب", "حجز موعد", "اصدار", "استخراج",
        "الاشتراك", "الوصول الى الخدمة", "اجراءات التقديم",
    )
    _SERVICE_GROUPS = (
        ("موعد", "الموعد", "ابتداء من", "حتى", "المهلة", "اخر موعد", "المواعيد"),
        ("الشروط", "يشترط", "الاهلية", "المؤهلون", "الفئات المستحقة"),
        ("المستندات", "الوثائق", "صورة الهوية", "اثبات", "الاوراق المطلوبة"),
        ("الموقع", "المراكز", "الفرع", "المنصة", "الكترونيا", "عبر الموقع"),
        ("الرسوم", "السعر", "التكلفة", "جنيه", "ريال", "دولار"),
        ("متاح", "التوافر", "ساعات العمل", "ايام العمل"),
    )
    _CLAIM = ("ادعاء", "يزعم", "زعم", "القول المتداول", "منشور متداول", "شائعة", "معلومة متداولة", "تصريح منسوب")
    _VERIFY = ("تحققنا", "التحقق", "راجعنا", "فحصنا", "قارن فريق التدقيق", "دققنا", "بمراجعة", "بفحص", "تتبعت المصادر", "اظهرت الوثائق")
    _VERDICT = (
        "الادعاء صحيح", "الادعاء خاطئ", "غير صحيح", "مضلل", "صحيح جزئيا",
        "لا دليل", "النتيجة: صحيح", "النتيجة: خاطئ",
        "ثبتت صحته", "ثبت بطلانه", "تؤكد الادلة", "تنفي الادلة", "الخبر صحيح",
        "الخبر زائف", "خلاصة التحقق",
    )
    _URGENT = ("عاجل", "الان", "منذ قليل", "قبل قليل", "تطور عاجل", "خبر عاجل")
    _UNFOLDING = (
        "حتى اللحظة", "تفاصيل تباعا", "لا تزال", "ما زال", "جار", "جارية",
        "قيد التطور", "المعلومات الاولية",
    )
    _LIST_PROMISE = ("افضل", "اهم", "ابرز", "خطوات", "نصائح", "ترتيب", "قائمة")
    _OPINION = ("ارى ان", "نرى ان", "في رايي", "اعتقد ان", "اجادل بان", "موقفي هو")
    _ARGUMENT = ("لان", "اولا", "ثانيا", "لذلك", "من جهة", "في المقابل", "الحجة")
    _COMPARISON = ("مقارنة", "مقابل", "بينما", "على خلاف", "من جهة", "في المقابل", "بين")
    _COMPARATIVE_DETAIL = (
        "اعلى", "اقل", "افضل", "اسرع", "ابطا", "مزايا", "عيوب", "السابق",
        "الحالي", "قبل", "بعد", "يتفوق", "يفوق",
    )
    _NARRATIVE = (
        "في صباح", "في مساء", "داخل", "بينما كان", "يتذكر", "يروي",
        "وسط", "على مقربة", "في ذلك اليوم",
    )
    _NARRATIVE_ARC = ("ثم", "بعد ذلك", "لاحقا", "عندما", "منذ ذلك الحين", "عاد")
    _BIOGRAPHY = ("ولد", "ولدت", "نشا", "نشأت", "تاسس", "تاسست", "بدا مسيرته")
    _MILESTONE = ("مسيرته", "مسيرتها", "حقق", "حققت", "محطة", "عام", "بطولة", "منصب")
    _CURRENT = ("اليوم", "حاليا", "الان", "في الوقت الراهن", "يشغل", "تقود حاليا")

    def extract(
        self, *, source: NormalizedSource, lead: str | None = None,
    ) -> EditorialTreatmentFeatureResult:
        """Extract deterministic features from headline, lead, and body."""
        if not isinstance(source, NormalizedSource):
            raise ValueError("source must be a NormalizedSource")
        explicit_lead = lead if lead is not None else self._first_paragraph(source.body)
        if not isinstance(explicit_lead, str):
            raise ValueError("lead must be a string")
        headline = self._normalize(source.title)
        normalized_lead = self._normalize(explicit_lead)
        body, duplicate_removed = self._body_without_lead(source.body, explicit_lead)
        normalized_body = self._normalize(body)

        headline_features = self._detect_section(headline)
        lead_features = self._detect_section(normalized_lead)
        body_features = self._detect_section(normalized_body)
        cross_features = self._detect_cross_section(
            (headline, normalized_lead, normalized_body),
            (headline_features, lead_features, body_features),
        )
        aggregate = (
            set(headline_features)
            | set(lead_features)
            | set(body_features)
            | set(cross_features)
        )
        # A single contextual cause/effect passage does not make an otherwise
        # event-framed report an analysis.  Causal framing in the headline or
        # sustained causal treatment outside the body remains eligible.
        event_framed = Feature.EVENT_REPORTING in (
            set(headline_features) | set(lead_features)
        )
        causal_framed = self._has(headline, self._CAUSE) or self._has(
            headline, ("اسباب", "لماذا", "تداعيات", "اثر", "اثار")
        )
        if (
            event_framed
            and not causal_framed
            and Feature.CAUSAL_EXPLANATION not in headline_features
            and Feature.CAUSAL_EXPLANATION not in lead_features
            and Feature.CAUSAL_EXPLANATION in body_features
        ):
            aggregate.discard(Feature.CAUSAL_EXPLANATION)
        all_features = self._ordered(aggregate)
        warnings = (
            ("DUPLICATED_LEAD_REMOVED_FROM_BODY_ANALYSIS",)
            if duplicate_removed else ()
        )
        return EditorialTreatmentFeatureResult(
            features=all_features,
            headline_features=headline_features,
            lead_features=lead_features,
            body_features=body_features,
            cross_section_features=cross_features,
            warnings=warnings,
        )

    def _detect_section(self, text: str) -> tuple[Feature, ...]:
        found: set[Feature] = set()
        for window in self._bounded_windows(text):
            found.update(self._detect_window(window))
        if self._is_list_structure(text):
            found.add(Feature.LIST_OR_RANKING_STRUCTURE)
        if self._is_qa_structure(text):
            found.add(Feature.INTERVIEW_QA_STRUCTURE)
        return self._ordered(found)

    def _detect_cross_section(
        self,
        sections: tuple[str, str, str],
        local: tuple[tuple[Feature, ...], tuple[Feature, ...], tuple[Feature, ...]],
    ) -> tuple[Feature, ...]:
        distinct = tuple(dict.fromkeys(section for section in sections if section))
        if len(distinct) < 2:
            return ()
        combined = " . ".join(distinct)
        combined_features = set(self._detect_section(combined))
        if (
            any(self._has(section, self._LIST_PROMISE) for section in distinct)
            and sum(
                len(re.findall(r"(?:^|\n)\s*(?:\d+|[١-٩])\s*[.)-]", section))
                for section in distinct
            ) >= 3
        ):
            combined_features.add(Feature.LIST_OR_RANKING_STRUCTURE)
        local_sets = tuple(set(items) for items in local)
        cross: set[Feature] = set()
        for feature in combined_features:
            local_count = sum(feature in items for items in local_sets)
            contributors = sum(
                self._contributes(feature, section) for section in distinct
            )
            if contributors >= 2 and (local_count == 0 or len(distinct) >= 2):
                cross.add(feature)
        return self._ordered(cross)

    def _detect_window(self, text: str) -> set[Feature]:
        found: set[Feature] = set()
        if self._has(text, self._EVENT) or (
            self._has(text, self._EVENT_NOMINAL)
            and self._has(text, self._EVENT_CONTEXT)
        ):
            found.add(Feature.EVENT_REPORTING)
        if self._has(text, self._DIRECTION) and self._has(text, self._REFERENCE):
            found.add(Feature.TEMPORAL_MOVEMENT)
        if (
            self._has(text, self._OUTCOME_FINAL)
            and self._has(text, self._OUTCOME_OBSERVED)
            and not self._has(text, self._FUTURE)
        ):
            found.add(Feature.COMPLETED_OUTCOME)
        if self._has(text, self._CAUSE) and self._has(text, self._EFFECT):
            found.add(Feature.CAUSAL_EXPLANATION)
        if self._has(text, self._MECHANISM) and self._count_groups(text, (self._PROCESS,)):
            found.add(Feature.MECHANISM_EXPLANATION)
        if self._has(text, self._GUIDANCE) and len(self._matched(text, self._ACTION_DETAIL)) >= 2:
            found.add(Feature.ACTIONABLE_GUIDANCE)
        if self._has(text, self._SERVICE_ANCHOR) and self._count_groups(text, self._SERVICE_GROUPS) >= 2:
            found.add(Feature.PROCEDURAL_SERVICE)
        if self._has(text, self._CLAIM) and self._has(text, self._VERIFY) and self._has(text, self._VERDICT):
            found.add(Feature.CLAIM_VERIFICATION)
        if self._has(text, self._URGENT) and self._has(text, self._UNFOLDING):
            found.add(Feature.URGENT_BREAKING_SIGNAL)
        if self._has(text, self._OPINION) and len(self._matched(text, self._ARGUMENT)) >= 2:
            found.add(Feature.OPINION_ARGUMENTATION)
        if self._has(text, self._COMPARISON) and len(self._matched(text, self._COMPARATIVE_DETAIL)) >= 2:
            found.add(Feature.COMPARATIVE_STRUCTURE)
        if self._has(text, self._NARRATIVE) and self._has(text, self._NARRATIVE_ARC):
            found.add(Feature.NARRATIVE_SCENE_STRUCTURE)
        if self._has(text, self._BIOGRAPHY) and self._has(text, self._MILESTONE) and self._has(text, self._CURRENT):
            found.add(Feature.BIOGRAPHICAL_ARC)
        return found

    def _contributes(self, feature: Feature, text: str) -> bool:
        groups = {
            Feature.EVENT_REPORTING: (
                self._EVENT, self._EVENT_NOMINAL, self._EVENT_CONTEXT,
            ),
            Feature.TEMPORAL_MOVEMENT: (self._DIRECTION, self._REFERENCE),
            Feature.COMPLETED_OUTCOME: (self._OUTCOME_FINAL, self._OUTCOME_OBSERVED),
            Feature.CAUSAL_EXPLANATION: (self._CAUSE, self._EFFECT),
            Feature.MECHANISM_EXPLANATION: (self._MECHANISM, self._PROCESS),
            Feature.ACTIONABLE_GUIDANCE: (self._GUIDANCE, self._ACTION_DETAIL),
            Feature.PROCEDURAL_SERVICE: (self._SERVICE_ANCHOR, *self._SERVICE_GROUPS),
            Feature.CLAIM_VERIFICATION: (self._CLAIM, self._VERIFY, self._VERDICT),
            Feature.URGENT_BREAKING_SIGNAL: (self._URGENT, self._UNFOLDING),
            Feature.LIST_OR_RANKING_STRUCTURE: (self._LIST_PROMISE,),
            Feature.INTERVIEW_QA_STRUCTURE: (("سؤال", "جواب", "س:", "ج:"),),
            Feature.OPINION_ARGUMENTATION: (self._OPINION, self._ARGUMENT),
            Feature.COMPARATIVE_STRUCTURE: (self._COMPARISON, self._COMPARATIVE_DETAIL),
            Feature.NARRATIVE_SCENE_STRUCTURE: (self._NARRATIVE, self._NARRATIVE_ARC),
            Feature.BIOGRAPHICAL_ARC: (self._BIOGRAPHY, self._MILESTONE, self._CURRENT),
        }[feature]
        return any(self._has(text, group) for group in groups)

    def _is_list_structure(self, text: str) -> bool:
        numbered = len(re.findall(r"(?:^|\n)\s*(?:\d+|[١-٩])\s*[.)-]", text))
        ranks = len(self._matched(text, ("المرتبة الاولى", "المرتبة الثانية", "المرتبة الثالثة", "المركز الاول", "المركز الثاني")))
        return (numbered >= 3 and self._has(text, self._LIST_PROMISE)) or ranks >= 2

    @staticmethod
    def _is_qa_structure(text: str) -> bool:
        questions = len(re.findall(r"(?:^|\n)\s*(?:سؤال|س)\s*[:：]", text))
        answers = len(re.findall(r"(?:^|\n)\s*(?:جواب|ج)\s*[:：]", text))
        return questions >= 2 and answers >= 2

    def _bounded_windows(self, text: str) -> tuple[str, ...]:
        if not text:
            return ()
        paragraphs = tuple(part.strip() for part in text.split("\n") if part.strip())
        windows: list[str] = []
        for paragraph in paragraphs or (text,):
            sentences = tuple(
                item.strip() for item in re.split(r"[.!؟?؛;]+", paragraph)
                if item.strip()
            )
            windows.extend(sentences)
            windows.extend(
                f"{sentences[index]} . {sentences[index + 1]}"
                for index in range(len(sentences) - 1)
            )
            windows.append(paragraph)
        return tuple(dict.fromkeys(windows))

    @staticmethod
    def _first_paragraph(body: str) -> str:
        return next((item.strip() for item in body.split("\n") if item.strip()), "")

    def _body_without_lead(self, body: str, lead: str) -> tuple[str, bool]:
        paragraphs = [item.strip() for item in body.split("\n") if item.strip()]
        normalized_lead = self._normalize(lead)
        if paragraphs and normalized_lead and self._normalize(paragraphs[0]) == normalized_lead:
            return "\n".join(paragraphs[1:]), True
        return "\n".join(paragraphs), False

    @staticmethod
    def _normalize(text: str) -> str:
        arabic = "".join(
            {
                "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي",
            }.get(character, " " if character in "ـ\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652" else character)
            for character in text
        )
        # Preserve newlines for list/Q&A structure while normalizing punctuation.
        lines = [" ".join(re.sub(r"[^\w\s:.)-]", " ", line.casefold()).split()) for line in arabic.splitlines()]
        return "\n".join(line for line in lines if line)

    @classmethod
    def _has(cls, text: str, terms: tuple[str, ...]) -> bool:
        return any(
            re.search(
                rf"(?<!\w)(?:و)?{re.escape(cls._normalize(term))}(?!\w)", text,
            ) is not None
            for term in terms
        )

    @classmethod
    def _matched(cls, text: str, terms: tuple[str, ...]) -> set[str]:
        return {term for term in terms if cls._has(text, (term,))}

    @classmethod
    def _count_groups(cls, text: str, groups: tuple[tuple[str, ...], ...]) -> int:
        return sum(cls._has(text, group) for group in groups)

    @staticmethod
    def _ordered(features: set[Feature]) -> tuple[Feature, ...]:
        return tuple(feature for feature in Feature if feature in features)
