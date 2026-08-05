"""Deterministic classification of a reader's primary intent."""

from collections.abc import Iterable

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.classification.classification_confidence import (
    ClassificationConfidence,
)
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource

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
_CLAIM_TERMS = ("حقيقة", "ادعاء", "شائعة", "مزاعم", "صحيح", "غير صحيح")
_REQUIREMENT_TERMS = (
    "شروط",
    "رسوم",
    "مستندات",
    "أهلية",
    "متطلبات",
    "إجراءات",
    "موعد",
    "طريقة التقديم",
)
_ACTION_TERMS = (
    "يجب",
    "تجنب",
    "خطوات",
    "التقديم",
    "التسجيل",
    "الحجز",
    "اتبع",
    "الإجراء المطلوب",
)
_RESULT_TERMS = (
    "نتيجة",
    "فاز",
    "خسر",
    "انتهت",
    "حسم",
    "النتيجة النهائية",
    "قرار نهائي",
)
_GUIDANCE_TERMS = ("نصائح", "إرشادات", "وقاية", "توصيات", "تجنب", "علاج")
_COMPARISON_TERMS = ("مقارنة", "الأفضل", "الفرق بين", "مقابل", "مزايا", "عيوب")
_ONGOING_TERMS = (
    "تطورات",
    "مستجدات",
    "متابعة",
    "مستمر",
    "قيد التحقيق",
    "آخر التطورات",
)
_IMPACT_TERMS = (
    "تأثير",
    "ينعكس",
    "المتضررون",
    "المستفيدون",
    "ماذا يعني",
    "تداعيات",
)
_UNDERSTANDING_TERMS = (
    "لماذا",
    "كيف",
    "الأسباب",
    "الخلفية",
    "التفاصيل",
    "ما معنى",
)


class DeterministicReaderIntentClassifier:
    """Identify one primary reader intent using deterministic signals."""

    def classify(
        self,
        *,
        source: NormalizedSource,
        assessment: SourceRiskAssessment,
        facts: ExtractedFacts,
        content_classification: ContentTypeClassification,
        user_instruction: str | None = None,
    ) -> ReaderIntentClassification:
        """Classify the reader's primary need for one editorial result.

        Args:
            source: Normalized source material.
            assessment: Risk assessment for the source.
            facts: Facts extracted from the source.
            content_classification: Editorial content type classification.
            user_instruction: Optional explicit reader-intent instruction.

        Returns:
            One deterministic reader intent classification.
        """
        text = self._searchable_text(source, user_instruction)
        instruction = (user_instruction or "").lower()
        content_type = content_classification.content_type

        explicit = self._explicit_intent(instruction, assessment.risk_level)
        if explicit is not None:
            return explicit

        claim_terms = self._matching_terms(text, _CLAIM_TERMS)
        if (
            content_type in (ContentType.FACT_CHECK, ContentType.TRENDING_SOCIAL_CLAIM)
            or facts.claims
            and claim_terms
        ):
            signals: tuple[str, ...] = ()
            if content_type is ContentType.FACT_CHECK:
                signals += ("CONTENT_TYPE_FACT_CHECK",)
            if content_type is ContentType.TRENDING_SOCIAL_CLAIM:
                signals += ("CONTENT_TYPE_TRENDING_SOCIAL_CLAIM",)
            if facts.claims:
                signals += ("CLAIMS_PRESENT",)
            warnings = (
                ("CLAIM_EVIDENCE_REQUIRED",)
                if content_type is ContentType.TRENDING_SOCIAL_CLAIM
                and not facts.claims
                else ()
            )
            return self._result(
                ReaderIntent.CHECK_CLAIM,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.FACT_CHECK
                else ReaderIntentConfidence.MEDIUM,
                ("CLAIM_VERIFICATION_SIGNAL",),
                signals,
                warnings,
            )

        requirement_terms = self._matching_terms(text, _REQUIREMENT_TERMS)
        if (
            content_type is ContentType.GOVERNMENT_SERVICE_CONTENT
            or len(requirement_terms) >= 2
        ):
            signals = (
                ("CONTENT_TYPE_GOVERNMENT_SERVICE",)
                if content_type is ContentType.GOVERNMENT_SERVICE_CONTENT
                else ()
            )
            if len(requirement_terms) >= 2:
                signals += ("PROCEDURAL_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.VERIFY_REQUIREMENTS,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.GOVERNMENT_SERVICE_CONTENT
                else ReaderIntentConfidence.MEDIUM,
                ("REQUIREMENTS_SIGNAL",),
                signals,
                ("REQUIREMENTS_SOURCE_RECOMMENDED",),
            )

        action_terms = self._matching_terms(text, _ACTION_TERMS)
        if (
            content_type is ContentType.PUBLIC_SERVICE_NEWS
            or len(action_terms) >= 2
        ):
            signals = (
                ("CONTENT_TYPE_PUBLIC_SERVICE",)
                if content_type is ContentType.PUBLIC_SERVICE_NEWS
                else ()
            )
            if len(action_terms) >= 2:
                signals += ("ACTION_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.KNOW_ACTION,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.PUBLIC_SERVICE_NEWS
                else ReaderIntentConfidence.MEDIUM,
                ("ACTION_SIGNAL",),
                signals,
                (),
            )

        result_terms = self._matching_terms(text, _RESULT_TERMS)
        if content_type is ContentType.SPORTS_NEWS or result_terms:
            signals = (
                ("CONTENT_TYPE_SPORTS",)
                if content_type is ContentType.SPORTS_NEWS
                else ()
            )
            if result_terms:
                signals += ("RESULT_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.FIND_RESULT,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.SPORTS_NEWS
                else ReaderIntentConfidence.MEDIUM,
                ("RESULT_SIGNAL",),
                signals,
                (),
            )

        medical_topics = self._matching_topics(
            assessment.risk_topics, "medical"
        )
        guidance_terms = self._matching_terms(text, _GUIDANCE_TERMS)
        if (
            content_type is ContentType.HEALTH_CONTENT
            or medical_topics
            or guidance_terms
        ):
            signals = (
                ("CONTENT_TYPE_HEALTH",)
                if content_type is ContentType.HEALTH_CONTENT
                else ()
            )
            if medical_topics:
                signals += ("MEDICAL_RISK_TOPIC",)
            if guidance_terms:
                signals += ("GUIDANCE_TERMS_PRESENT",)
            warnings = (
                ("HIGH_RISK_GUIDANCE_REQUIRES_REVIEW",)
                if assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                else ()
            )
            return self._result(
                ReaderIntent.GET_GUIDANCE,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.HEALTH_CONTENT
                else ReaderIntentConfidence.MEDIUM,
                ("GUIDANCE_SIGNAL",),
                signals,
                warnings,
            )

        comparison_terms = self._matching_terms(text, _COMPARISON_TERMS)
        if comparison_terms:
            return self._result(
                ReaderIntent.COMPARE_OPTIONS,
                ReaderIntentConfidence.MEDIUM,
                ("COMPARISON_SIGNAL",),
                ("COMPARISON_TERMS_PRESENT",),
                (),
            )

        ongoing_terms = self._matching_terms(text, _ONGOING_TERMS)
        if ongoing_terms:
            return self._result(
                ReaderIntent.FOLLOW_DEVELOPMENT,
                ReaderIntentConfidence.MEDIUM,
                ("ONGOING_DEVELOPMENT_SIGNAL",),
                ("ONGOING_EVENT_TERMS_PRESENT",),
                (),
            )

        impact_terms = self._matching_terms(text, _IMPACT_TERMS)
        if (
            content_type
            in (
                ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
                ContentType.ECONOMY_NEWS,
            )
            or impact_terms
        ):
            signals = ()
            if content_type is ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT:
                signals += ("CONTENT_TYPE_HIGH_RISK",)
            if content_type is ContentType.ECONOMY_NEWS:
                signals += ("CONTENT_TYPE_ECONOMY",)
            if impact_terms:
                signals += ("IMPACT_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.UNDERSTAND_IMPACT,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT
                else ReaderIntentConfidence.MEDIUM,
                ("IMPACT_SIGNAL",),
                signals,
                (),
            )

        understanding_terms = self._matching_terms(text, _UNDERSTANDING_TERMS)
        if (
            content_type is ContentType.EXPLAINER
            or len(understanding_terms) >= 2
        ):
            signals = (
                ("CONTENT_TYPE_EXPLAINER",)
                if content_type is ContentType.EXPLAINER
                else ()
            )
            if len(understanding_terms) >= 2:
                signals += ("EXPLANATORY_TERMS_PRESENT",)
            return self._result(
                ReaderIntent.UNDERSTAND_EVENT,
                ReaderIntentConfidence.HIGH
                if content_type is ContentType.EXPLAINER
                else ReaderIntentConfidence.MEDIUM,
                ("UNDERSTANDING_SIGNAL",),
                signals,
                (),
            )

        low_confidence = (
            content_classification.confidence is ClassificationConfidence.LOW
        )
        return self._result(
            ReaderIntent.GET_UPDATE,
            ReaderIntentConfidence.LOW
            if low_confidence
            else ReaderIntentConfidence.MEDIUM,
            ("DEFAULT_GET_UPDATE",),
            ("CONTENT_TYPE_FALLBACK",),
            ("LOW_READER_INTENT_CONFIDENCE",) if low_confidence else (),
        )

    @staticmethod
    def _explicit_intent(
        instruction: str, risk_level: RiskLevel
    ) -> ReaderIntentClassification | None:
        """Return the first explicitly requested intent, when present.

        Args:
            instruction: Lowercase explicit user instruction.
            risk_level: Editorial risk level for guidance warnings.

        Returns:
            Explicit intent classification, or None when none matches.
        """
        for intent, terms, reason, signal in _EXPLICIT_RULES:
            if any(term.lower() in instruction for term in terms):
                warnings = (
                    ("HIGH_RISK_GUIDANCE_REQUIRES_REVIEW",)
                    if intent is ReaderIntent.GET_GUIDANCE
                    and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                    else ()
                )
                return DeterministicReaderIntentClassifier._result(
                    intent,
                    ReaderIntentConfidence.HIGH,
                    (reason,),
                    (signal,),
                    warnings,
                )
        return None

    @staticmethod
    def _searchable_text(
        source: NormalizedSource, user_instruction: str | None
    ) -> str:
        """Build lowercase searchable text from permitted fields.

        Args:
            source: Source providing searchable fields.
            user_instruction: Optional reader-intent instruction.

        Returns:
            Combined lowercase searchable text.
        """
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
        """Return configured terms found in searchable text.

        Args:
            text: Lowercase searchable text.
            terms: Terms to locate.

        Returns:
            Unique matching terms in configured order.
        """
        return DeterministicReaderIntentClassifier._unique(
            term for term in terms if term.lower() in text
        )

    @staticmethod
    def _matching_topics(
        risk_topics: tuple[str, ...], term: str
    ) -> tuple[str, ...]:
        """Return risk topics containing a configured term.

        Args:
            risk_topics: Assessment risk topics.
            term: Lowercase topic term to locate.

        Returns:
            Unique matching topics in source order.
        """
        return DeterministicReaderIntentClassifier._unique(
            topic for topic in risk_topics if term in topic.lower()
        )

    @staticmethod
    def _result(
        reader_intent: ReaderIntent,
        confidence: ReaderIntentConfidence,
        reason_codes: Iterable[str],
        supporting_signals: Iterable[str],
        warnings: Iterable[str],
    ) -> ReaderIntentClassification:
        """Build a classification with ordered unique tuple values.

        Args:
            reader_intent: Selected primary reader intent.
            confidence: Confidence in the selected intent.
            reason_codes: Reasons supporting the intent.
            supporting_signals: Evidence from the selected rule.
            warnings: Warnings associated with the result.

        Returns:
            One immutable reader intent classification.
        """
        return ReaderIntentClassification(
            reader_intent=reader_intent,
            confidence=confidence,
            reason_codes=DeterministicReaderIntentClassifier._unique(
                reason_codes
            ),
            supporting_signals=DeterministicReaderIntentClassifier._unique(
                supporting_signals
            ),
            warnings=DeterministicReaderIntentClassifier._unique(warnings),
        )

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Return values without duplicates while preserving order.

        Args:
            values: Ordered string values.

        Returns:
            Values preserving only their first occurrence.
        """
        return tuple(dict.fromkeys(values))
