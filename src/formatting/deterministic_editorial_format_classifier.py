"""Deterministic classification of one primary editorial format."""

import re
from collections.abc import Iterable

from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.verification_status import VerificationStatus
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource

from .editorial_format import EditorialFormat
from .editorial_format_classification import EditorialFormatClassification
from .editorial_format_confidence import EditorialFormatConfidence


_FACT_CHECK_REQUESTS = ("تحقق من صحة", "تدقيق حقيقة", "fact check")
_INTERVIEW_REQUESTS = ("مقابلة", "حوار", "أسئلة وأجوبة", "interview", "q&a")
_GUIDE_REQUESTS = ("اكتب دليلًا", "دليل", "كل ما تريد معرفته", "guide")
_SERVICE_REQUESTS = ("خبر خدمي", "خدمي", "service news")
_FEATURE_REQUESTS = ("تقرير قصصي", "فيتشر", "feature", "قصة صحفية")
_ANALYSIS_REQUESTS = ("تحليل", "تقرير تحليلي", "analysis")
_PROFILE_REQUESTS = ("بروفايل", "ملف شخصي", "profile")
_RESULT_REQUESTS = ("تقرير نتيجة", "نتيجة المباراة", "من فاز", "result report")
_BREAKING_REQUESTS = ("اكتب خبرًا عاجلًا", "خبر عاجل", "breaking")
_EXPLAINER_REQUESTS = ("اشرح", "تفسير", "explainer", "explain")
_PROCEDURAL_TERMS = (
    "شروط",
    "متطلبات",
    "خطوات",
    "طريقة",
    "كيفية",
    "موعد",
    "القنوات الناقلة",
    "المستندات",
    "مستندات",
    "الرسوم",
    "رسوم",
    "أهلية",
)
_RESULT_TERMS = ("فاز", "خسر", "تعادل", "انتهت", "حسم", "نتيجة", "النتيجة النهائية")
_PUBLIC_SERVICE_TERMS = (
    "غرامة",
    "مخالفة",
    "إغلاق طريق",
    "انقطاع",
    "تحذير",
    "تنبيه",
    "تعليق الخدمة",
    "موعد التقديم",
    "سلامة",
    "المرور",
)
_ACTION_TERMS = (
    "يجب",
    "ينصح",
    "تجنب",
    "التزام",
    "خطوات",
    "غرامة",
    "عقوبة",
    "موعد",
    "إجراء",
)
_PENALTY_DEADLINE_TERMS = ("غرامة", "عقوبة", "موعد", "الموعد النهائي", "مهلة")
_FEATURE_GROUPS = (
    ("FEATURE_HISTORICAL", ("تاريخ", "تأسس", "منذ", "موسم", "حقبة", "أول فريق")),
    ("FEATURE_IDENTITY", ("هوية", "مدينة", "جماهير", "رمز", "ثقافة")),
    ("FEATURE_UNUSUAL_DETAILS", ("أغرب", "مميز", "لافت", "حكاية", "قصة")),
)
_PROFILE_GROUPS = (
    ("history", ("تاريخ", "تأسس", "منذ")),
    ("achievements", ("إنجاز", "بطولة", "فاز", "حقق")),
    ("background", ("خلفية", "نشأة", "مسيرة")),
    ("milestones", ("محطة", "مرحلة", "عام", "موسم")),
    ("current relevance", ("حاليًا", "اليوم", "الآن", "راهن")),
)
_INTERPRETATION_TERMS = (
    "تأثير",
    "تداعيات",
    "ماذا يعني",
    "لماذا",
    "مستقبل",
    "سيناريو",
    "انعكاس",
    "نتائج محتملة",
)
_BREAKING_TERMS = ("عاجل", "الآن", "منذ قليل", "قبل قليل")
_EXPLANATION_TERMS = (
    "لماذا",
    "كيف",
    "الأسباب",
    "ما معنى",
    "التفاصيل",
    "الخلفية",
    "كيف يعمل",
    "ما الذي",
)
_SOCIAL_TERMS = (
    "x.com",
    "twitter.com",
    "facebook.com",
    "tiktok.com",
    "instagram.com",
    "twitter",
    "facebook",
    "tiktok",
    "instagram",
    "تويتر",
    "فيسبوك",
    "تيك توك",
    "إنستجرام",
)


class DeterministicEditorialFormatClassifier:
    """Classify analyzed material into one deterministic editorial format."""

    def classify(
        self,
        *,
        source: NormalizedSource,
        assessment: SourceRiskAssessment,
        facts: ExtractedFacts,
        content_classification: ContentTypeClassification,
        user_instruction: str | None = None,
    ) -> EditorialFormatClassification:
        """Classify one source using only supplied deterministic signals.

        Args:
            source: Normalized source material.
            assessment: Existing source and risk assessment.
            facts: Deterministically extracted source facts.
            content_classification: Existing compatible content classification.
            user_instruction: Optional explicit requested editorial treatment.

        Returns:
            Exactly one editorial format classification.
        """
        text = self._searchable_text(source, user_instruction)
        instruction = (user_instruction or "").lower()
        depth = self._source_depth(source, facts)
        warnings: tuple[str, ...] = ()

        explicit, warnings = self._explicit_format(
            instruction,
            text,
            source,
            facts,
            content_classification.content_type,
            depth,
            warnings,
        )
        if explicit is not None:
            return explicit

        content_type = content_classification.content_type
        if content_type is ContentType.FACT_CHECK:
            if facts.claims:
                return self._result(
                    EditorialFormat.FACT_CHECK,
                    EditorialFormatConfidence.HIGH,
                    ("FACT_CHECK_STRUCTURE_SIGNAL",),
                    ("CONTENT_TYPE_FACT_CHECK", "CLAIMS_PRESENT"),
                    warnings,
                )
            warnings += ("FACT_CHECK_EVIDENCE_MISSING",)

        if len(facts.quotes) >= 3 and self._has_question_answer_structure(source.body):
            return self._result(
                EditorialFormat.INTERVIEW,
                EditorialFormatConfidence.HIGH,
                ("INTERVIEW_STRUCTURE_SIGNAL",),
                ("MULTIPLE_QUOTES_PRESENT", "QUESTION_ANSWER_STRUCTURE"),
                warnings,
            )

        result_terms_title = self._matching_terms(source.title.lower(), _RESULT_TERMS)
        result_terms_body = self._matching_terms(source.body.lower(), _RESULT_TERMS)
        if content_type is ContentType.SPORTS_NEWS and (
            result_terms_title or result_terms_body
        ):
            signals: tuple[str, ...] = ("CONTENT_TYPE_SPORTS",)
            if result_terms_title:
                signals += ("RESULT_TERM_IN_TITLE",)
            if result_terms_body:
                signals += ("RESULT_TERM_IN_BODY",)
            if facts.numbers:
                signals += ("NUMERIC_RESULT_PRESENT",)
            return self._result(
                EditorialFormat.RESULT_REPORT,
                EditorialFormatConfidence.HIGH
                if result_terms_title
                else EditorialFormatConfidence.MEDIUM,
                ("RESULT_STRUCTURE_SIGNAL",),
                signals,
                warnings,
            )

        guide_signals = self._guide_group_signals(text, facts, content_type)
        if len(guide_signals) >= 2:
            return self._result(
                EditorialFormat.GUIDE,
                EditorialFormatConfidence.HIGH
                if len(guide_signals) >= 3
                else EditorialFormatConfidence.MEDIUM,
                ("GUIDE_STRUCTURE_SIGNAL",),
                guide_signals,
                warnings,
            )

        service_signals = self._service_signals(text, content_type)
        if service_signals:
            return self._result(
                EditorialFormat.SERVICE,
                EditorialFormatConfidence.HIGH
                if content_type is ContentType.PUBLIC_SERVICE_NEWS
                else EditorialFormatConfidence.MEDIUM,
                ("SERVICE_STRUCTURE_SIGNAL",),
                service_signals,
                warnings,
            )

        feature_signals = self._feature_signals(source, facts, text)
        if len(feature_signals) >= 3:
            if depth == "RICH":
                return self._result(
                    EditorialFormat.FEATURE,
                    EditorialFormatConfidence.HIGH
                    if len(feature_signals) >= 4
                    else EditorialFormatConfidence.MEDIUM,
                    ("FEATURE_STRUCTURE_SIGNAL",),
                    feature_signals,
                    warnings,
                )
            warnings += ("SOURCE_TOO_THIN_FOR_FEATURE",)

        if self._profile_supported(source, text, depth):
            return self._result(
                EditorialFormat.PROFILE,
                EditorialFormatConfidence.MEDIUM,
                ("PROFILE_STRUCTURE_SIGNAL",),
                ("DOMINANT_SUBJECT_PROFILE",),
                warnings,
            )

        interpretation_terms = self._matching_terms(text, _INTERPRETATION_TERMS)
        evidence_categories = self._evidence_categories(facts)
        if len(interpretation_terms) >= 2:
            if depth == "RICH" and len(evidence_categories) >= 2:
                return self._result(
                    EditorialFormat.ANALYSIS,
                    EditorialFormatConfidence.MEDIUM,
                    ("ANALYSIS_STRUCTURE_SIGNAL",),
                    (
                        "INTERPRETATION_TERMS_PRESENT",
                        "MULTIPLE_EVIDENCE_CATEGORIES",
                    ),
                    warnings,
                )
            warnings += ("SOURCE_TOO_THIN_FOR_ANALYSIS",)

        social_signals = self._social_signals(source)
        if (
            content_type is ContentType.TRENDING_SOCIAL_CLAIM or social_signals
        ) and assessment.verification_status in (
            VerificationStatus.UNVERIFIED,
            VerificationStatus.SOURCE_PROVIDED,
        ):
            signals = (
                ("CONTENT_TYPE_TRENDING_SOCIAL_CLAIM",)
                if content_type is ContentType.TRENDING_SOCIAL_CLAIM
                else ()
            ) + social_signals
            return self._result(
                EditorialFormat.TREND_UPDATE,
                EditorialFormatConfidence.MEDIUM,
                ("TREND_SOURCE_SIGNAL",),
                signals,
                warnings + ("TREND_VERIFICATION_INCOMPLETE",),
            )

        immediacy_terms = self._matching_terms(text, _BREAKING_TERMS)
        if (
            immediacy_terms and depth in ("THIN", "STANDARD")
        ) or content_type is ContentType.BREAKING_NEWS:
            signals = ("IMMEDIACY_TERMS_PRESENT",) if immediacy_terms else (
                "CONTENT_TYPE_BREAKING",
            )
            return self._result(
                EditorialFormat.BREAKING,
                EditorialFormatConfidence.MEDIUM,
                ("BREAKING_IMMEDIACY_SIGNAL",),
                signals,
                warnings,
            )

        explanation_terms = self._matching_terms(text, _EXPLANATION_TERMS)
        if len(explanation_terms) >= 2 or content_type is ContentType.EXPLAINER:
            signals = ("EXPLANATION_TERMS_PRESENT",) if explanation_terms else (
                "CONTENT_TYPE_EXPLAINER",
            )
            return self._result(
                EditorialFormat.EXPLAINER,
                EditorialFormatConfidence.MEDIUM,
                ("EXPLAINER_STRUCTURE_SIGNAL",),
                signals,
                warnings,
            )

        low_confidence = (
            content_classification.confidence is ClassificationConfidence.LOW
        )
        return self._result(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.LOW
            if low_confidence
            else EditorialFormatConfidence.MEDIUM,
            ("DEFAULT_STANDARD_NEWS_FORMAT",),
            ("EXISTING_CONTENT_TYPE_FALLBACK",),
            warnings + (("LOW_EDITORIAL_FORMAT_CONFIDENCE",) if low_confidence else ()),
        )

    def _explicit_format(
        self,
        instruction: str,
        text: str,
        source: NormalizedSource,
        facts: ExtractedFacts,
        content_type: ContentType,
        depth: str,
        warnings: tuple[str, ...],
    ) -> tuple[EditorialFormatClassification | None, tuple[str, ...]]:
        """Resolve supported explicit requests and carry unsupported warnings."""
        if self._contains(instruction, _FACT_CHECK_REQUESTS):
            if facts.claims:
                return self._explicit_result(
                    EditorialFormat.FACT_CHECK,
                    "EXPLICIT_FACT_CHECK_FORMAT",
                    "USER_INSTRUCTION_FACT_CHECK",
                    warnings,
                ), warnings
            warnings += ("FACT_CHECK_EVIDENCE_MISSING",)

        if self._contains(instruction, _INTERVIEW_REQUESTS):
            if len(facts.quotes) >= 2 or self._explicit_interview_structure(
                source.body
            ):
                return self._explicit_result(
                    EditorialFormat.INTERVIEW,
                    "EXPLICIT_INTERVIEW_FORMAT",
                    "USER_INSTRUCTION_INTERVIEW",
                    warnings,
                ), warnings
            warnings += ("INTERVIEW_STRUCTURE_MISSING",)

        if self._contains(instruction, _GUIDE_REQUESTS):
            if self._explicit_guide_supported(text, facts):
                return self._explicit_result(
                    EditorialFormat.GUIDE,
                    "EXPLICIT_GUIDE_FORMAT",
                    "USER_INSTRUCTION_GUIDE",
                    warnings,
                ), warnings
            warnings += ("GUIDE_STRUCTURE_INSUFFICIENT",)

        if self._contains(instruction, _SERVICE_REQUESTS):
            return self._explicit_result(
                EditorialFormat.SERVICE,
                "EXPLICIT_SERVICE_FORMAT",
                "USER_INSTRUCTION_SERVICE",
                warnings,
            ), warnings

        if self._contains(instruction, _FEATURE_REQUESTS):
            if depth == "RICH":
                return self._explicit_result(
                    EditorialFormat.FEATURE,
                    "EXPLICIT_FEATURE_FORMAT",
                    "USER_INSTRUCTION_FEATURE",
                    warnings,
                ), warnings
            warnings += ("SOURCE_TOO_THIN_FOR_FEATURE",)

        if self._contains(instruction, _ANALYSIS_REQUESTS):
            if depth == "RICH" and len(self._evidence_categories(facts)) >= 2:
                return self._explicit_result(
                    EditorialFormat.ANALYSIS,
                    "EXPLICIT_ANALYSIS_FORMAT",
                    "USER_INSTRUCTION_ANALYSIS",
                    warnings,
                ), warnings
            warnings += ("SOURCE_TOO_THIN_FOR_ANALYSIS",)

        if self._contains(instruction, _PROFILE_REQUESTS):
            if depth == "RICH" or self._thematic_block_count(source.body) >= 3:
                return self._explicit_result(
                    EditorialFormat.PROFILE,
                    "EXPLICIT_PROFILE_FORMAT",
                    "USER_INSTRUCTION_PROFILE",
                    warnings,
                ), warnings
            warnings += ("UNSUPPORTED_FORMAT_REQUEST",)

        if self._contains(instruction, _RESULT_REQUESTS):
            result_terms = self._matching_terms(text, _RESULT_TERMS)
            if result_terms or (
                content_type is ContentType.SPORTS_NEWS and facts.numbers
            ):
                return self._explicit_result(
                    EditorialFormat.RESULT_REPORT,
                    "EXPLICIT_RESULT_REPORT_FORMAT",
                    "USER_INSTRUCTION_RESULT_REPORT",
                    warnings,
                ), warnings

        if self._contains(instruction, _BREAKING_REQUESTS):
            return self._explicit_result(
                EditorialFormat.BREAKING,
                "EXPLICIT_BREAKING_FORMAT",
                "USER_INSTRUCTION_BREAKING",
                warnings,
            ), warnings

        if self._contains(instruction, _EXPLAINER_REQUESTS):
            return self._explicit_result(
                EditorialFormat.EXPLAINER,
                "EXPLICIT_EXPLAINER_FORMAT",
                "USER_INSTRUCTION_EXPLAINER",
                warnings,
            ), warnings
        return None, self._unique(warnings)

    @staticmethod
    def _source_depth(source: NormalizedSource, facts: ExtractedFacts) -> str:
        """Return the first matching deterministic source-depth band."""
        word_count = len(f"{source.title} {source.body}".split())
        structured = (
            len(facts.dates)
            + len(facts.times)
            + len(facts.numbers)
            + len(facts.percentages)
            + len(facts.currencies)
        )
        evidence = (
            len(facts.claims)
            + len(facts.quotes)
            + len(facts.events)
            + structured
        )
        if word_count < 80 or evidence <= 2:
            return "THIN"
        if 80 <= word_count <= 299:
            return "STANDARD"
        return "RICH"

    @staticmethod
    def _explicit_guide_supported(text: str, facts: ExtractedFacts) -> bool:
        """Return whether at least two explicit-guide requirements are met."""
        structured = (
            len(facts.dates)
            + len(facts.times)
            + len(facts.numbers)
            + len(facts.percentages)
            + len(facts.currencies)
        )
        checks = (
            bool(facts.dates),
            bool(facts.times),
            bool(facts.currencies),
            structured >= 2,
            DeterministicEditorialFormatClassifier._contains(text, _PROCEDURAL_TERMS),
        )
        return sum(checks) >= 2

    @staticmethod
    def _guide_group_signals(
        text: str, facts: ExtractedFacts, content_type: ContentType
    ) -> tuple[str, ...]:
        """Return every supported guide group signal in stable order."""
        signals: list[str] = []
        if facts.dates or facts.times:
            signals.append("GUIDE_DATE_OR_TIME")
        if facts.numbers or facts.currencies or facts.percentages:
            signals.append("GUIDE_STRUCTURED_VALUES")
        if DeterministicEditorialFormatClassifier._contains(
            text, _PROCEDURAL_TERMS
        ):
            signals.append("GUIDE_PROCEDURAL_TERMS")
        if DeterministicEditorialFormatClassifier._contains(
            text,
            (
                "موعد",
                "القنوات الناقلة",
                "كيف تشاهد",
                "كل ما تريد معرفته",
                "الأسئلة الشائعة",
            ),
        ):
            signals.append("GUIDE_REFERENCE_ANSWER_TERMS")
        if content_type is ContentType.GOVERNMENT_SERVICE_CONTENT:
            signals.append("CONTENT_TYPE_GOVERNMENT_SERVICE")
        return tuple(signals)

    @staticmethod
    def _service_signals(
        text: str, content_type: ContentType
    ) -> tuple[str, ...]:
        """Return service signals only when practical action is present."""
        action = DeterministicEditorialFormatClassifier._contains(
            text, _ACTION_TERMS
        )
        if not action:
            return ()
        signals: list[str] = []
        if content_type is ContentType.PUBLIC_SERVICE_NEWS:
            signals.append("CONTENT_TYPE_PUBLIC_SERVICE")
        if DeterministicEditorialFormatClassifier._contains(
            text, _PUBLIC_SERVICE_TERMS
        ):
            signals.append("PUBLIC_SERVICE_TERM")
        signals.append("PRACTICAL_ACTION_SIGNAL")
        if DeterministicEditorialFormatClassifier._contains(
            text, _PENALTY_DEADLINE_TERMS
        ):
            signals.append("PENALTY_OR_DEADLINE_SIGNAL")
        if (
            content_type is ContentType.GOVERNMENT_SERVICE_CONTENT
            and len(signals) == 1
        ):
            signals.append("CONTENT_TYPE_GOVERNMENT_SERVICE")
        return tuple(signals) if len(signals) > 1 else ()

    @staticmethod
    def _feature_signals(
        source: NormalizedSource, facts: ExtractedFacts, text: str
    ) -> tuple[str, ...]:
        """Return every supported narrative feature group."""
        signals = [
            signal
            for signal, terms in _FEATURE_GROUPS
            if DeterministicEditorialFormatClassifier._contains(text, terms)
        ]
        if len(facts.quotes) >= 2:
            signals.append("FEATURE_PERSONALITIES")
        if (
            DeterministicEditorialFormatClassifier._thematic_block_count(
                source.body
            )
            >= 3
        ):
            signals.append("FEATURE_MULTIPLE_THEMATIC_BLOCKS")
        return tuple(signals)

    @staticmethod
    def _profile_supported(source: NormalizedSource, text: str, depth: str) -> bool:
        """Detect a dominant repeated title subject with profile information."""
        if depth != "RICH":
            return False
        title_terms = [term for term in source.title.lower().split() if len(term) >= 4]
        dominant = any(source.body.lower().count(term) >= 3 for term in title_terms)
        groups = sum(
            DeterministicEditorialFormatClassifier._contains(text, terms)
            for _, terms in _PROFILE_GROUPS
        )
        return dominant and groups >= 2

    @staticmethod
    def _evidence_categories(facts: ExtractedFacts) -> tuple[str, ...]:
        """Return populated structured evidence categories in stable order."""
        values = (
            ("NUMBERS", facts.numbers),
            ("CURRENCIES", facts.currencies),
            ("DATES", facts.dates),
            ("QUOTES", facts.quotes),
            ("CLAIMS", facts.claims),
        )
        return tuple(name for name, items in values if items)

    @staticmethod
    def _social_signals(source: NormalizedSource) -> tuple[str, ...]:
        """Return stable social-source name and URL signals."""
        source_text = f"{source.source_name} {source.source_url or ''}".lower()
        return (
            ("SOCIAL_SOURCE_PRESENT",)
            if DeterministicEditorialFormatClassifier._contains(
                source_text, _SOCIAL_TERMS
            )
            else ()
        )

    @staticmethod
    def _explicit_interview_structure(body: str) -> bool:
        """Detect at least two questions and two attributed response lines."""
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        questions = sum(
            line.endswith(("?", "؟")) or line.startswith(("س:", "سؤال"))
            for line in lines
        )
        responses = sum(
            line.startswith(("ج:", "إجابة"))
            or any(term in line for term in ("قال", "أجاب", "أوضح"))
            for line in lines
        )
        return questions >= 2 and responses >= 2

    @staticmethod
    def _has_question_answer_structure(body: str) -> bool:
        """Detect three questions or explicit question-and-answer markers."""
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        question_count = sum(line.endswith(("?", "؟")) for line in lines)
        return question_count >= 3 or any(
            marker in body for marker in ("س:", "ج:", "سؤال", "إجابة")
        )

    @staticmethod
    def _thematic_block_count(body: str) -> int:
        """Count distinct non-empty blocks separated by blank lines or headings."""
        blocks = [
            block
            for block in re.split(
                r"\n\s*\n|(?=^##?\s)",
                body,
                flags=re.MULTILINE,
            )
            if block.strip()
        ]
        return len(blocks)

    @staticmethod
    def _searchable_text(source: NormalizedSource, instruction: str | None) -> str:
        """Build one lowercase searchable text from permitted input fields."""
        values = (
            source.title,
            source.body,
            source.category or "",
            *source.tags,
            instruction or "",
        )
        return "\n".join(values).lower()

    @staticmethod
    def _contains(text: str, terms: Iterable[str]) -> bool:
        """Return whether any configured literal term occurs in text."""
        return any(term.lower() in text for term in terms)

    @staticmethod
    def _matching_terms(text: str, terms: Iterable[str]) -> tuple[str, ...]:
        """Return unique matching literal terms in configured order."""
        return DeterministicEditorialFormatClassifier._unique(
            term for term in terms if term.lower() in text
        )

    @staticmethod
    def _explicit_result(
        editorial_format: EditorialFormat,
        reason: str,
        signal: str,
        warnings: tuple[str, ...],
    ) -> EditorialFormatClassification:
        """Build one high-confidence explicitly requested result."""
        return DeterministicEditorialFormatClassifier._result(
            editorial_format,
            EditorialFormatConfidence.HIGH,
            (reason,),
            (signal,),
            warnings,
        )

    @staticmethod
    def _result(
        editorial_format: EditorialFormat,
        confidence: EditorialFormatConfidence,
        reasons: tuple[str, ...],
        signals: tuple[str, ...],
        warnings: tuple[str, ...],
    ) -> EditorialFormatClassification:
        """Build one result with stable order-preserving deduplication."""
        return EditorialFormatClassification(
            editorial_format=editorial_format,
            confidence=confidence,
            reason_codes=DeterministicEditorialFormatClassifier._unique(reasons),
            supporting_signals=DeterministicEditorialFormatClassifier._unique(signals),
            warnings=DeterministicEditorialFormatClassifier._unique(warnings),
        )

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Remove duplicates while preserving first occurrence order."""
        return tuple(dict.fromkeys(values))
