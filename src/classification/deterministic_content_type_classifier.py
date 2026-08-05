"""Deterministic editorial content type classification."""

from collections.abc import Iterable

from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.verification_status import VerificationStatus
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource

from .classification_confidence import ClassificationConfidence
from .content_type import ContentType
from .content_type_classification import ContentTypeClassification


_REWRITE_TERMS = ("إعادة كتابة", "أعد كتابة", "rewrite")
_FACT_CHECK_TERMS = ("تحقق من صحة", "تدقيق حقيقة", "fact check")
_GOVERNMENT_CATEGORIES = ("government service", "خدمات حكومية")
_SERVICE_TERMS = (
    "تأشيرة",
    "إقامة",
    "تصريح",
    "منصة حكومية",
    "خدمة إلكترونية",
    "أهلية",
    "مستندات مطلوبة",
    "خطوات التقديم",
)
_PROCEDURAL_TERMS = (
    "رسوم",
    "شروط",
    "إجراءات",
    "موعد",
    "تقديم",
    "طلب",
    "تجديد",
)
_HEALTH_TERMS = (
    "دواء",
    "جرعة",
    "تشخيص",
    "علاج",
    "مرض",
    "أعراض",
    "لقاح",
    "صحة",
)
_LEGAL_FINANCIAL_TERMS = (
    "محكمة",
    "حكم قضائي",
    "قانون",
    "عقوبة",
    "غرامة",
    "قرض",
    "فائدة",
    "استثمار",
    "ضريبة",
)
_PUBLIC_SERVICE_TERMS = (
    "غرامة مرورية",
    "مخالفة مرورية",
    "انقطاع خدمة",
    "موعد التقديم",
    "تحذير للمستهلكين",
    "إغلاق طريق",
    "تغيير مواعيد",
    "النقل العام",
    "الطقس",
    "تحذير جوي",
)
_SPORTS_TERMS = (
    "مباراة",
    "فريق",
    "لاعب",
    "بطولة",
    "دوري",
    "هدف",
    "انتقال",
    "مدرب",
)
_SPORTS_CATEGORIES = ("sports", "رياضة")
_TECHNOLOGY_TERMS = (
    "تقنية",
    "تكنولوجيا",
    "ذكاء اصطناعي",
    "برمجيات",
    "تطبيق",
    "منصة رقمية",
    "هاتف",
    "أمن سيبراني",
    "اختراق",
)
_TECHNOLOGY_CATEGORIES = ("technology", "تقنية")
_ECONOMY_TERMS = (
    "اقتصاد",
    "تضخم",
    "بطالة",
    "أسواق",
    "شركة",
    "تجارة",
    "نفط",
    "طاقة",
    "أسعار",
    "مؤشر اقتصادي",
)
_ECONOMY_CATEGORIES = ("economy", "اقتصاد")
_SOCIAL_SOURCE_NAMES = (
    "X",
    "Twitter",
    "Facebook",
    "TikTok",
    "Instagram",
    "فيسبوك",
    "تويتر",
    "تيك توك",
)
_SOCIAL_URL_TERMS = (
    "x.com",
    "twitter.com",
    "facebook.com",
    "tiktok.com",
    "instagram.com",
)
_BREAKING_TERMS = ("عاجل", "الآن", "منذ قليل", "قبل قليل")
_EXPLAINER_INSTRUCTION_TERMS = ("اشرح", "تفسير", "explain")
_EXPLAINER_STRUCTURAL_TERMS = (
    "كيف",
    "لماذا",
    "الأسباب",
    "الخطوات",
    "التفاصيل",
    "ما معنى",
)


class DeterministicContentTypeClassifier:
    """Classify editorial ingestion data using deterministic signals."""

    def classify(
        self,
        *,
        source: NormalizedSource,
        assessment: SourceRiskAssessment,
        facts: ExtractedFacts,
        user_instruction: str | None = None,
    ) -> ContentTypeClassification:
        """Classify one source into one primary editorial content type.

        Args:
            source: Normalized source material.
            assessment: Risk assessment for the source.
            facts: Facts extracted from the source.
            user_instruction: Optional explicit editorial instruction.

        Returns:
            One deterministic content type classification.
        """
        text = self._searchable_text(source, user_instruction)
        instruction = (user_instruction or "").lower()
        category = (source.category or "").lower()
        carried_warnings: tuple[str, ...] = ()

        if self._matching_terms(instruction, _REWRITE_TERMS):
            return self._classification(
                ContentType.NEWS_REWRITE,
                ClassificationConfidence.HIGH,
                ("EXPLICIT_REWRITE_INTENT",),
                ("USER_INSTRUCTION_REWRITE",),
                carried_warnings,
            )

        if self._matching_terms(instruction, _FACT_CHECK_TERMS):
            if facts.claims:
                return self._classification(
                    ContentType.FACT_CHECK,
                    ClassificationConfidence.HIGH,
                    ("EXPLICIT_FACT_CHECK_INTENT",),
                    ("USER_INSTRUCTION_FACT_CHECK", "CLAIMS_PRESENT"),
                    carried_warnings,
                )
            carried_warnings = ("FACT_CHECK_EVIDENCE_MISSING",)

        category_signals = self._matching_terms(
            category, _GOVERNMENT_CATEGORIES
        )
        service_signals = self._matching_terms(text, _SERVICE_TERMS)
        procedural_signals = self._matching_terms(text, _PROCEDURAL_TERMS)
        if category_signals or (service_signals and procedural_signals):
            structural_match = bool(service_signals and procedural_signals)
            reason = (
                "GOVERNMENT_SERVICE_SIGNALS"
                if structural_match
                else "EXPLICIT_GOVERNMENT_SERVICE_CATEGORY"
            )
            signals = self._prefixed("CATEGORY", category_signals)
            signals += self._prefixed("SERVICE_TERM", service_signals)
            signals += self._prefixed("PROCEDURAL_TERM", procedural_signals)
            return self._classification(
                ContentType.GOVERNMENT_SERVICE_CONTENT,
                ClassificationConfidence.HIGH
                if structural_match
                else ClassificationConfidence.MEDIUM,
                (reason,),
                signals,
                carried_warnings + ("GOVERNMENT_SOURCE_RECOMMENDED",),
            )

        medical_topics = self._matching_topics(
            assessment.risk_topics, ("medical",)
        )
        health_signals = self._matching_terms(text, _HEALTH_TERMS)
        if medical_topics or health_signals:
            signals = self._prefixed("RISK_TOPIC", medical_topics)
            signals += self._prefixed("HEALTH_TERM", health_signals)
            return self._classification(
                ContentType.HEALTH_CONTENT,
                ClassificationConfidence.HIGH
                if medical_topics
                else ClassificationConfidence.MEDIUM,
                ("MEDICAL_CONTENT_SIGNAL",),
                signals,
                carried_warnings + ("HIGH_RISK_TREATMENT_REQUIRED",),
            )

        risk_topics = self._matching_topics(
            assessment.risk_topics, ("legal", "financial")
        )
        legal_financial_signals = self._matching_terms(
            text, _LEGAL_FINANCIAL_TERMS
        )
        if risk_topics or legal_financial_signals:
            signals = self._prefixed("RISK_TOPIC", risk_topics)
            signals += self._prefixed(
                "LEGAL_FINANCIAL_TERM", legal_financial_signals
            )
            return self._classification(
                ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
                ClassificationConfidence.HIGH
                if risk_topics
                else ClassificationConfidence.MEDIUM,
                ("LEGAL_FINANCIAL_RISK_SIGNAL",),
                signals,
                carried_warnings + ("HIGH_RISK_TREATMENT_REQUIRED",),
            )

        public_service_signals = self._matching_terms(
            text, _PUBLIC_SERVICE_TERMS
        )
        if public_service_signals:
            return self._classification(
                ContentType.PUBLIC_SERVICE_NEWS,
                ClassificationConfidence.MEDIUM,
                ("PUBLIC_SERVICE_SIGNAL",),
                self._prefixed("PUBLIC_SERVICE_TERM", public_service_signals),
                carried_warnings,
            )

        sports_signals = self._matching_terms(text, _SPORTS_TERMS)
        if sports_signals:
            sports_categories = self._matching_terms(
                category, _SPORTS_CATEGORIES
            )
            signals = self._prefixed("SPORTS_TERM", sports_signals)
            signals += self._prefixed("CATEGORY", sports_categories)
            return self._classification(
                ContentType.SPORTS_NEWS,
                ClassificationConfidence.HIGH
                if sports_categories
                else ClassificationConfidence.MEDIUM,
                ("SPORTS_SIGNAL",),
                signals,
                carried_warnings,
            )

        technology_signals = self._matching_terms(text, _TECHNOLOGY_TERMS)
        if technology_signals:
            technology_categories = self._matching_terms(
                category, _TECHNOLOGY_CATEGORIES
            )
            signals = self._prefixed("TECHNOLOGY_TERM", technology_signals)
            signals += self._prefixed("CATEGORY", technology_categories)
            return self._classification(
                ContentType.TECHNOLOGY_NEWS,
                ClassificationConfidence.HIGH
                if technology_categories
                else ClassificationConfidence.MEDIUM,
                ("TECHNOLOGY_SIGNAL",),
                signals,
                carried_warnings,
            )

        economy_signals = self._matching_terms(text, _ECONOMY_TERMS)
        if economy_signals:
            economy_categories = self._matching_terms(
                category, _ECONOMY_CATEGORIES
            )
            signals = self._prefixed("ECONOMY_TERM", economy_signals)
            signals += self._prefixed("CATEGORY", economy_categories)
            return self._classification(
                ContentType.ECONOMY_NEWS,
                ClassificationConfidence.HIGH
                if economy_categories
                else ClassificationConfidence.MEDIUM,
                ("ECONOMY_SIGNAL",),
                signals,
                carried_warnings,
            )

        social_signals = self._social_signals(source)
        if social_signals and assessment.verification_status in (
            VerificationStatus.UNVERIFIED,
            VerificationStatus.SOURCE_PROVIDED,
        ):
            return self._classification(
                ContentType.TRENDING_SOCIAL_CLAIM,
                ClassificationConfidence.MEDIUM,
                ("SOCIAL_SOURCE_SIGNAL",),
                social_signals,
                carried_warnings + ("SOCIAL_CLAIM_UNVERIFIED",),
            )

        breaking_signals = self._matching_terms(text, _BREAKING_TERMS)
        if breaking_signals:
            return self._classification(
                ContentType.BREAKING_NEWS,
                ClassificationConfidence.MEDIUM,
                ("BREAKING_SIGNAL",),
                self._prefixed("BREAKING_TERM", breaking_signals),
                carried_warnings,
            )

        explicit_explainer = self._matching_terms(
            instruction, _EXPLAINER_INSTRUCTION_TERMS
        )
        structural_explainer = self._matching_terms(
            text, _EXPLAINER_STRUCTURAL_TERMS
        )
        if explicit_explainer or len(structural_explainer) >= 2:
            signals = self._prefixed(
                "USER_INSTRUCTION", explicit_explainer
            )
            signals += self._prefixed(
                "STRUCTURAL_TERM", structural_explainer
            )
            return self._classification(
                ContentType.EXPLAINER,
                ClassificationConfidence.HIGH
                if explicit_explainer
                else ClassificationConfidence.MEDIUM,
                ("EXPLAINER_SIGNAL",),
                signals,
                carried_warnings,
            )

        return self._classification(
            ContentType.STANDARD_NEWS,
            ClassificationConfidence.LOW,
            ("DEFAULT_STANDARD_NEWS",),
            (),
            carried_warnings + ("LOW_CLASSIFICATION_CONFIDENCE",),
        )

    @staticmethod
    def _searchable_text(
        source: NormalizedSource, user_instruction: str | None
    ) -> str:
        """Build lowercase searchable text from permitted source fields.

        Args:
            source: Source providing searchable text fields.
            user_instruction: Optional editorial instruction.

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
        """Return unique terms contained in text in configured order.

        Args:
            text: Lowercase searchable text.
            terms: Terms to find.

        Returns:
            Matching terms without duplicates.
        """
        return DeterministicContentTypeClassifier._unique(
            term for term in terms if term.lower() in text
        )

    @staticmethod
    def _matching_topics(
        risk_topics: tuple[str, ...], terms: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Return risk topics containing configured terms.

        Args:
            risk_topics: Assessment risk topics.
            terms: Topic terms to find.

        Returns:
            Matching original risk topics in source order.
        """
        return DeterministicContentTypeClassifier._unique(
            topic
            for topic in risk_topics
            if any(term in topic.lower() for term in terms)
        )

    @staticmethod
    def _social_signals(source: NormalizedSource) -> tuple[str, ...]:
        """Return matching social source name and URL signals.

        Args:
            source: Source providing attribution metadata.

        Returns:
            Unique matching social-source signals.
        """
        name_matches = (
            name
            for name in _SOCIAL_SOURCE_NAMES
            if (
                (name == "X" and name in source.source_name)
                or (
                    name != "X"
                    and name.lower() in source.source_name.lower()
                )
            )
        )
        url = (source.source_url or "").lower()
        url_matches = (term for term in _SOCIAL_URL_TERMS if term in url)
        signals = DeterministicContentTypeClassifier._prefixed(
            "SOURCE_NAME", name_matches
        )
        signals += DeterministicContentTypeClassifier._prefixed(
            "SOURCE_URL", url_matches
        )
        return DeterministicContentTypeClassifier._unique(signals)

    @staticmethod
    def _prefixed(prefix: str, values: Iterable[str]) -> tuple[str, ...]:
        """Create stable supporting signals from matched values.

        Args:
            prefix: Signal source label.
            values: Matched evidence values.

        Returns:
            Prefixed supporting signals.
        """
        return tuple(f"{prefix}:{value}" for value in values)

    @staticmethod
    def _classification(
        content_type: ContentType,
        confidence: ClassificationConfidence,
        reason_codes: Iterable[str],
        supporting_signals: Iterable[str],
        warnings: Iterable[str],
    ) -> ContentTypeClassification:
        """Build a classification with stable unique tuple values.

        Args:
            content_type: Selected editorial content type.
            confidence: Confidence in the selection.
            reason_codes: Reasons supporting the selection.
            supporting_signals: Evidence exposed for the selected rule.
            warnings: Classification warnings.

        Returns:
            One immutable classification result.
        """
        return ContentTypeClassification(
            content_type=content_type,
            confidence=confidence,
            reason_codes=DeterministicContentTypeClassifier._unique(
                reason_codes
            ),
            supporting_signals=DeterministicContentTypeClassifier._unique(
                supporting_signals
            ),
            warnings=DeterministicContentTypeClassifier._unique(warnings),
        )

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Return values in order without duplicates.

        Args:
            values: Ordered string values.

        Returns:
            Unique values preserving first occurrence order.
        """
        return tuple(dict.fromkeys(values))
