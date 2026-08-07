"""Topic-and-format-aware deterministic reader intent classification."""

from collections.abc import Iterable

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.facts.extracted_facts import ExtractedFacts
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.intake.normalized_source import NormalizedSource
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification

from .reader_intent import ReaderIntent
from .reader_intent_classification import ReaderIntentClassification
from .reader_intent_confidence import ReaderIntentConfidence


_EXPLICIT_RULES = (
    (
        ReaderIntent.CHECK_CLAIM,
        ("تحقق من صحة", "هل هذا صحيح", "دقق الادعاء", "fact check", "verify claim"),
        "EXPLICIT_CHECK_CLAIM_INTENT",
        "USER_INSTRUCTION_CHECK_CLAIM",
    ),
    (
        ReaderIntent.VERIFY_REQUIREMENTS,
        (
            "ما هي الشروط",
            "ما المستندات",
            "ما الرسوم",
            "طريقة التقديم",
            "متطلبات",
            "requirements",
            "eligibility",
        ),
        "EXPLICIT_VERIFY_REQUIREMENTS_INTENT",
        "USER_INSTRUCTION_VERIFY_REQUIREMENTS",
    ),
    (
        ReaderIntent.KNOW_ACTION,
        ("ماذا أفعل", "ما الخطوات", "كيف أتصرف", "what should i do", "steps"),
        "EXPLICIT_KNOW_ACTION_INTENT",
        "USER_INSTRUCTION_KNOW_ACTION",
    ),
    (
        ReaderIntent.FIND_RESULT,
        ("ما النتيجة", "من فاز", "النتيجة النهائية", "result", "who won"),
        "EXPLICIT_FIND_RESULT_INTENT",
        "USER_INSTRUCTION_FIND_RESULT",
    ),
    (
        ReaderIntent.GET_GUIDANCE,
        ("نصائح", "إرشادات", "توصيات", "guidance", "advice"),
        "EXPLICIT_GET_GUIDANCE_INTENT",
        "USER_INSTRUCTION_GET_GUIDANCE",
    ),
    (
        ReaderIntent.COMPARE_OPTIONS,
        ("قارن", "مقارنة", "ما الفرق", "الأفضل", "compare", "difference between"),
        "EXPLICIT_COMPARE_OPTIONS_INTENT",
        "USER_INSTRUCTION_COMPARE_OPTIONS",
    ),
    (
        ReaderIntent.FOLLOW_DEVELOPMENT,
        ("آخر التطورات", "المستجدات", "تابع", "latest developments", "updates"),
        "EXPLICIT_FOLLOW_DEVELOPMENT_INTENT",
        "USER_INSTRUCTION_FOLLOW_DEVELOPMENT",
    ),
    (
        ReaderIntent.UNDERSTAND_IMPACT,
        ("ما التأثير", "من سيتأثر", "ماذا يعني", "impact", "who is affected"),
        "EXPLICIT_UNDERSTAND_IMPACT_INTENT",
        "USER_INSTRUCTION_UNDERSTAND_IMPACT",
    ),
    (
        ReaderIntent.UNDERSTAND_EVENT,
        ("اشرح", "لماذا", "كيف حدث", "التفاصيل", "explain", "why"),
        "EXPLICIT_UNDERSTAND_EVENT_INTENT",
        "USER_INSTRUCTION_UNDERSTAND_EVENT",
    ),
    (
        ReaderIntent.GET_UPDATE,
        ("ما الجديد", "تحديث", "آخر الأخبار", "update", "latest news"),
        "EXPLICIT_GET_UPDATE_INTENT",
        "USER_INSTRUCTION_GET_UPDATE",
    ),
)

_FORMAT_DEFAULTS = {
    EditorialFormat.BREAKING: ReaderIntent.GET_UPDATE,
    EditorialFormat.STANDARD_NEWS: ReaderIntent.GET_UPDATE,
    EditorialFormat.SERVICE: ReaderIntent.KNOW_ACTION,
    EditorialFormat.GUIDE: ReaderIntent.VERIFY_REQUIREMENTS,
    EditorialFormat.EXPLAINER: ReaderIntent.UNDERSTAND_EVENT,
    EditorialFormat.FEATURE: ReaderIntent.UNDERSTAND_EVENT,
    EditorialFormat.FACT_CHECK: ReaderIntent.CHECK_CLAIM,
    EditorialFormat.ANALYSIS: ReaderIntent.UNDERSTAND_IMPACT,
    EditorialFormat.INTERVIEW: ReaderIntent.UNDERSTAND_EVENT,
    EditorialFormat.PROFILE: ReaderIntent.UNDERSTAND_EVENT,
    EditorialFormat.RESULT_REPORT: ReaderIntent.FIND_RESULT,
    EditorialFormat.TREND_UPDATE: ReaderIntent.CHECK_CLAIM,
}

_CLAIM_TERMS = ("حقيقة", "ادعاء", "شائعة", "مزاعم", "صحيح", "غير صحيح")
_REQUIREMENT_TERMS = (
    "شروط",
    "رسوم",
    "مستندات",
    "متطلبات",
    "أهلية",
    "موعد",
    "طريقة التقديم",
    "القنوات الناقلة",
    "كيف تشاهد",
)
_ACTION_TERMS = (
    "يجب",
    "تجنب",
    "التزام",
    "خطوات",
    "إجراء",
    "غرامة",
    "مخالفة",
    "تحذير",
    "تنبيه",
)
_RESULT_TERMS = ("نتيجة", "فاز", "خسر", "انتهت", "حسم", "النتيجة النهائية")
_GUIDANCE_TERMS = ("نصائح", "إرشادات", "توصيات", "وقاية", "تجنب")
_IMPACT_TERMS = (
    "تأثير",
    "تداعيات",
    "ماذا يعني",
    "ينعكس",
    "المتضررون",
    "المستفيدون",
)
_UNDERSTANDING_TERMS = (
    "لماذا",
    "كيف",
    "الأسباب",
    "الخلفية",
    "التفاصيل",
    "ما معنى",
)


class DeterministicReaderIntentClassifierV2:
    """Identify reader intent from independent topic and format dimensions."""

    def classify(
        self,
        *,
        source: NormalizedSource,
        assessment: SourceRiskAssessment,
        facts: ExtractedFacts,
        topic_classification: TopicClassification,
        format_classification: EditorialFormatClassification,
        user_instruction: str | None = None,
    ) -> ReaderIntentClassification:
        """Classify one primary reader need without legacy content type.

        Args:
            source: Normalized source material.
            assessment: Independent source and risk assessment.
            facts: Deterministically extracted facts.
            topic_classification: Independent primary topic classification.
            format_classification: Independent editorial format classification.
            user_instruction: Optional explicit reader-intent instruction.

        Returns:
            Exactly one deterministic reader-intent classification.
        """
        instruction = (user_instruction or "").lower()
        explicit = self._explicit_intent(instruction, assessment.risk_level)
        if explicit is not None:
            return explicit

        text = self._searchable_text(source, user_instruction)
        editorial_format = format_classification.editorial_format
        topic = topic_classification.topic
        format_signal = f"FORMAT_{editorial_format.value}"
        topic_signal = f"TOPIC_{topic.value}"

        claim_terms = self._matching_terms(text, _CLAIM_TERMS)
        if editorial_format in (
            EditorialFormat.FACT_CHECK,
            EditorialFormat.TREND_UPDATE,
        ) or (facts.claims and claim_terms):
            signals: tuple[str, ...] = (format_signal, topic_signal)
            if facts.claims:
                signals += ("CLAIMS_PRESENT",)
            if claim_terms:
                signals += ("CLAIM_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.CHECK_CLAIM,
                ReaderIntentConfidence.HIGH,
                ("CLAIM_STRUCTURE_SIGNAL",),
                signals,
                (),
            )

        requirement_terms = self._matching_terms(text, _REQUIREMENT_TERMS)
        if editorial_format is EditorialFormat.GUIDE and requirement_terms:
            return self._result(
                ReaderIntent.VERIFY_REQUIREMENTS,
                ReaderIntentConfidence.HIGH,
                ("REQUIREMENTS_STRUCTURE_SIGNAL",),
                (format_signal, topic_signal, "REQUIREMENTS_TERMS_PRESENT"),
                (),
            )

        action_terms = self._matching_terms(text, _ACTION_TERMS)
        if editorial_format is EditorialFormat.SERVICE and action_terms:
            return self._result(
                ReaderIntent.KNOW_ACTION,
                ReaderIntentConfidence.HIGH,
                ("ACTION_STRUCTURE_SIGNAL",),
                (format_signal, topic_signal, "ACTION_TERMS_PRESENT"),
                (),
            )

        if editorial_format is EditorialFormat.RESULT_REPORT:
            result_terms = self._matching_terms(text, _RESULT_TERMS)
            signals = (format_signal, topic_signal)
            if result_terms:
                signals += ("RESULT_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.FIND_RESULT,
                ReaderIntentConfidence.HIGH,
                ("RESULT_STRUCTURE_SIGNAL",),
                signals,
                (),
            )

        guidance_terms = self._matching_terms(text, _GUIDANCE_TERMS)
        if guidance_terms and (
            topic is Topic.HEALTH or len(guidance_terms) >= 2
        ):
            warnings = (
                ("HIGH_RISK_GUIDANCE_REQUIRES_REVIEW",)
                if assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                else ()
            )
            return self._result(
                ReaderIntent.GET_GUIDANCE,
                ReaderIntentConfidence.MEDIUM,
                ("GUIDANCE_STRUCTURE_SIGNAL",),
                (topic_signal, "GUIDANCE_TERMS_PRESENT"),
                warnings,
            )

        impact_terms = self._matching_terms(text, _IMPACT_TERMS)
        if editorial_format is EditorialFormat.ANALYSIS or len(impact_terms) >= 2:
            signals = (format_signal, topic_signal)
            if impact_terms:
                signals += ("IMPACT_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.UNDERSTAND_IMPACT,
                ReaderIntentConfidence.HIGH
                if editorial_format is EditorialFormat.ANALYSIS
                else ReaderIntentConfidence.MEDIUM,
                ("IMPACT_STRUCTURE_SIGNAL",),
                signals,
                (),
            )

        understanding_terms = self._matching_terms(text, _UNDERSTANDING_TERMS)
        if editorial_format in (
            EditorialFormat.EXPLAINER,
            EditorialFormat.FEATURE,
            EditorialFormat.INTERVIEW,
            EditorialFormat.PROFILE,
        ) or len(understanding_terms) >= 2:
            signals = (format_signal, topic_signal)
            if understanding_terms:
                signals += ("UNDERSTANDING_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.UNDERSTAND_EVENT,
                ReaderIntentConfidence.HIGH
                if editorial_format
                in (
                    EditorialFormat.EXPLAINER,
                    EditorialFormat.FEATURE,
                    EditorialFormat.INTERVIEW,
                    EditorialFormat.PROFILE,
                )
                else ReaderIntentConfidence.MEDIUM,
                ("UNDERSTANDING_STRUCTURE_SIGNAL",),
                signals,
                (),
            )

        default_intent = _FORMAT_DEFAULTS[editorial_format]
        low_update = (
            default_intent is ReaderIntent.GET_UPDATE
            and format_classification.confidence is EditorialFormatConfidence.LOW
        )
        reasons: tuple[str, ...] = ("FORMAT_READER_INTENT_MAPPING",)
        if default_intent is ReaderIntent.GET_UPDATE:
            reasons += ("DEFAULT_GET_UPDATE",)
        return self._result(
            default_intent,
            ReaderIntentConfidence.LOW
            if low_update
            else ReaderIntentConfidence.HIGH,
            reasons,
            (format_signal, topic_signal),
            ("LOW_READER_INTENT_CONFIDENCE",) if low_update else (),
        )

    @staticmethod
    def _explicit_intent(
        instruction: str,
        risk_level: RiskLevel,
    ) -> ReaderIntentClassification | None:
        """Return the first supported explicit reader-intent request."""
        for intent, terms, specific_reason, signal in _EXPLICIT_RULES:
            if any(term.lower() in instruction for term in terms):
                warnings = (
                    ("HIGH_RISK_GUIDANCE_REQUIRES_REVIEW",)
                    if intent is ReaderIntent.GET_GUIDANCE
                    and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                    else ()
                )
                return DeterministicReaderIntentClassifierV2._result(
                    intent,
                    ReaderIntentConfidence.HIGH,
                    ("EXPLICIT_READER_INTENT", specific_reason),
                    (signal,),
                    warnings,
                )
        return None

    @staticmethod
    def _searchable_text(
        source: NormalizedSource,
        user_instruction: str | None,
    ) -> str:
        """Build lowercase searchable text from permitted source fields."""
        values = (
            source.title,
            source.body,
            source.category or "",
            *source.tags,
            user_instruction or "",
        )
        return "\n".join(values).lower()

    @staticmethod
    def _matching_terms(text: str, terms: Iterable[str]) -> tuple[str, ...]:
        """Return configured terms found in text in stable configured order."""
        return DeterministicReaderIntentClassifierV2._unique(
            term for term in terms if term.lower() in text
        )

    @staticmethod
    def _result(
        reader_intent: ReaderIntent,
        confidence: ReaderIntentConfidence,
        reason_codes: Iterable[str],
        supporting_signals: Iterable[str],
        warnings: Iterable[str],
    ) -> ReaderIntentClassification:
        """Build one immutable result with stable deduplicated collections."""
        return ReaderIntentClassification(
            reader_intent=reader_intent,
            confidence=confidence,
            reason_codes=DeterministicReaderIntentClassifierV2._unique(reason_codes),
            supporting_signals=DeterministicReaderIntentClassifierV2._unique(
                supporting_signals
            ),
            warnings=DeterministicReaderIntentClassifierV2._unique(warnings),
        )

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Remove duplicates while preserving first occurrence order."""
        return tuple(dict.fromkeys(values))
