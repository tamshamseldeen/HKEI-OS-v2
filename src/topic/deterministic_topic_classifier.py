"""Deterministic classification of one primary editorial topic."""

from collections.abc import Iterable

from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource

from .topic import Topic
from .topic_classification import TopicClassification
from .topic_confidence import TopicConfidence


_CATEGORY_TOPICS = {
    "economy": Topic.ECONOMY,
    "اقتصاد": Topic.ECONOMY,
    "business": Topic.BUSINESS,
    "أعمال": Topic.BUSINESS,
    "شركات": Topic.BUSINESS,
    "technology": Topic.TECHNOLOGY,
    "tech": Topic.TECHNOLOGY,
    "تقنية": Topic.TECHNOLOGY,
    "تكنولوجيا": Topic.TECHNOLOGY,
    "sports": Topic.SPORTS,
    "sport": Topic.SPORTS,
    "رياضة": Topic.SPORTS,
    "رياضي": Topic.SPORTS,
    "government": Topic.GOVERNMENT,
    "حكومة": Topic.GOVERNMENT,
    "حكومي": Topic.GOVERNMENT,
    "خدمات حكومية": Topic.GOVERNMENT,
    "weather": Topic.WEATHER,
    "طقس": Topic.WEATHER,
    "مناخ": Topic.WEATHER,
    "health": Topic.HEALTH,
    "صحة": Topic.HEALTH,
    "طبي": Topic.HEALTH,
    "culture": Topic.CULTURE,
    "ثقافة": Topic.CULTURE,
    "آثار": Topic.CULTURE,
    "تراث": Topic.CULTURE,
    "science": Topic.SCIENCE,
    "علوم": Topic.SCIENCE,
    "علم": Topic.SCIENCE,
    "education": Topic.EDUCATION,
    "تعليم": Topic.EDUCATION,
    "جامعات": Topic.EDUCATION,
    "مدارس": Topic.EDUCATION,
    "crime": Topic.CRIME,
    "جريمة": Topic.CRIME,
    "حوادث جنائية": Topic.CRIME,
    "entertainment": Topic.ENTERTAINMENT,
    "فن": Topic.ENTERTAINMENT,
    "ترفيه": Topic.ENTERTAINMENT,
    "politics": Topic.POLITICS,
    "سياسة": Topic.POLITICS,
    "سياسي": Topic.POLITICS,
}

_TOPIC_TERMS = {
    Topic.POLITICS: (
        "انتخابات",
        "برلمان",
        "حزب",
        "رئيس الوزراء",
        "رئيس الجمهورية",
        "دبلوماسية",
        "سياسة خارجية",
        "حكومة ائتلافية",
    ),
    Topic.ECONOMY: (
        "البنك المركزي",
        "أسعار الفائدة",
        "التضخم",
        "الناتج المحلي",
        "النفط",
        "أسعار الذهب",
        "الشحن البحري",
        "الأسواق",
        "السوق",
        "التجارة",
        "البطالة",
        "الإيرادات السياحية",
        "إيرادات القطاع السياحي",
        "أوبك+",
        "أوبك",
    ),
    Topic.BUSINESS: (
        "شركة",
        "شركات",
        "أرباح الشركة",
        "استحواذ",
        "اندماج",
        "صفقة تجارية",
        "نتائج أعمال",
        "مجلس إدارة",
        "أسهم شركة",
    ),
    Topic.TECHNOLOGY: (
        "ذكاء اصطناعي",
        "الذكاء الاصطناعي",
        "أشباه الموصلات",
        "تقنية",
        "تكنولوجيا",
        "برمجيات",
        "تطبيق",
        "منصة رقمية",
        "هاتف",
        "أمن سيبراني",
        "مراكز البيانات",
    ),
    Topic.SPORTS: (
        "مباراة",
        "منتخب",
        "فريق",
        "لاعب",
        "بطولة",
        "دوري",
        "كأس",
        "مدرب",
        "انتقال رياضي",
        "انتقال",
        "تدريبات المنتخب",
        "تدريبات",
        "هدف",
        "نتيجة",
        "فوز",
    ),
    Topic.GOVERNMENT: (
        "وزارة",
        "هيئة حكومية",
        "المرور",
        "مترو الأنفاق",
        "خدمة حكومية",
        "مشروع حكومي",
        "بنية تحتية",
        "تصريح",
        "إقامة",
        "تأشيرة",
    ),
    Topic.WEATHER: (
        "موجة حر",
        "درجات الحرارة",
        "طقس",
        "أمطار",
        "عاصفة",
        "جفاف",
        "أرصاد",
        "رياح",
    ),
    Topic.HEALTH: (
        "دواء",
        "مرض",
        "علاج",
        "تشخيص",
        "أعراض",
        "مستشفى",
        "صحة",
        "لقاح",
    ),
    Topic.CULTURE: (
        "اكتشاف أثري",
        "أثري",
        "آثار",
        "مقابر",
        "متحف",
        "تراث",
        "ثقافة",
        "فنون",
        "أدب",
    ),
    Topic.SCIENCE: (
        "دراسة علمية",
        "اكتشاف علمي",
        "باحثون",
        "أبحاث",
        "فضاء",
        "فيزياء",
        "كيمياء",
        "أحياء",
    ),
    Topic.EDUCATION: (
        "جامعة",
        "مدرسة",
        "امتحانات",
        "طلاب",
        "تعليم",
        "قبول الجامعات",
        "مناهج",
    ),
    Topic.CRIME: (
        "جريمة",
        "قتل",
        "سرقة",
        "ضبط",
        "القبض",
        "تحقيق جنائي",
        "النيابة",
        "متهم",
    ),
    Topic.ENTERTAINMENT: (
        "فيلم",
        "مسلسل",
        "ممثل",
        "مطرب",
        "مهرجان فني",
        "حفل",
        "سينما",
    ),
    Topic.WORLD: (
        "العلاقات الدولية",
        "شؤون دولية",
        "نزاع دولي",
    ),
}

_STRONG_SPORTS_TERMS = (
    "مباراة",
    "منتخب",
    "لاعب",
    "بطولة",
    "دوري",
    "كأس",
    "مدرب",
    "انتقال رياضي",
    "تدريبات المنتخب",
)

_SPORTS_TAG_TERMS = (
    "السوبر",
    "الدوري",
    "المنتخب",
    "نادي",
    "كرة القدم",
    "رياضة",
)

_ECONOMIC_MARKET_TERMS = (
    "اقتصاد",
    "السوق",
    "الأسواق",
    "مالي",
    "الأسعار",
    "الفائدة",
    "التضخم",
    "إيرادات",
    "تكاليف",
    "استثمار",
    "قيمة سوقية",
    "النفط",
    "الذهب",
    "الشحن",
    "التجارة",
)

_LEGACY_TOPICS = {
    ContentType.SPORTS_NEWS: Topic.SPORTS,
    ContentType.TECHNOLOGY_NEWS: Topic.TECHNOLOGY,
    ContentType.ECONOMY_NEWS: Topic.ECONOMY,
    ContentType.HEALTH_CONTENT: Topic.HEALTH,
    ContentType.GOVERNMENT_SERVICE_CONTENT: Topic.GOVERNMENT,
}

_RISK_TOPIC_SUPPORT = {
    "medical": Topic.HEALTH,
    "financial": Topic.ECONOMY,
}


class DeterministicTopicClassifier:
    """Classify analyzed source material into one deterministic topic."""

    def classify(
        self,
        *,
        source: NormalizedSource,
        facts: ExtractedFacts,
        assessment: SourceRiskAssessment,
        content_classification: ContentTypeClassification,
        user_instruction: str | None = None,
    ) -> TopicClassification:
        """Classify one source from supplied deterministic signals only.

        Args:
            source: Normalized source material and metadata.
            facts: Deterministically extracted source facts.
            assessment: Existing independent source risk assessment.
            content_classification: Transitional legacy content classification.
            user_instruction: Optional supplied editorial instruction.

        Returns:
            Exactly one primary topic classification.
        """
        title = source.title.lower()
        body = source.body.lower()
        tags_text = "\n".join(source.tags).lower()
        searchable_text = "\n".join(
            (
                title,
                body,
                source.category or "",
                tags_text,
                user_instruction or "",
            )
        ).lower()
        category_topic = self._category_topic(source.category)
        title_matches = self._matches_by_topic(title)
        body_matches = self._matches_by_topic(body)
        tag_matches = self._matches_by_topic(tags_text)
        self._apply_sports_safety(
            source,
            content_classification,
            title_matches,
            body_matches,
            tag_matches,
        )

        scores = {topic: 0 for topic in Topic if topic is not Topic.GENERAL}
        if category_topic is not None:
            scores[category_topic] += 8
        for topic in scores:
            scores[topic] += len(title_matches.get(topic, ())) * 4
            scores[topic] += len(body_matches.get(topic, ())) * 2
            scores[topic] += int(bool(tag_matches.get(topic))) * 2

        government_entity_support = bool(facts.government_entities)
        if government_entity_support:
            scores[Topic.GOVERNMENT] += 1

        structured_economic = self._structured_economic_support(
            searchable_text,
            facts,
        )
        if structured_economic:
            scores[Topic.ECONOMY] += 2

        legacy_topic = _LEGACY_TOPICS.get(content_classification.content_type)
        legacy_reliable = (
            content_classification.confidence is not ClassificationConfidence.LOW
        )
        if legacy_topic is not None:
            scores[legacy_topic] += 2 if legacy_reliable else 1

        for risk_topic in assessment.risk_topics:
            supported = _RISK_TOPIC_SUPPORT.get(risk_topic.lower())
            if supported is not None and scores[supported] > 0:
                scores[supported] += 1

        selected = self._select_topic(
            scores=scores,
            category_topic=category_topic,
            title_matches=title_matches,
            body_matches=body_matches,
            tag_matches=tag_matches,
            facts=facts,
            government_entity_support=government_entity_support,
            structured_economic=structured_economic,
            legacy_topic=legacy_topic,
            legacy_reliable=legacy_reliable,
        )
        if selected is None:
            return TopicClassification(
                topic=Topic.GENERAL,
                confidence=TopicConfidence.LOW,
                reason_codes=("DEFAULT_GENERAL_TOPIC",),
                supporting_signals=("INSUFFICIENT_TOPIC_EVIDENCE",),
                warnings=(
                    "LOW_TOPIC_CONFIDENCE",
                    "TOPIC_SIGNAL_INSUFFICIENT",
                ),
            )

        category_conflict = (
            category_topic is not None and category_topic is not selected
        )
        strong_topics = self._strong_non_category_topics(
            title_matches,
            body_matches,
        )
        non_category_conflict = (
            category_topic is None
            and len(strong_topics) >= 2
            and selected in strong_topics
        )

        reasons: tuple[str, ...] = ()
        signals: tuple[str, ...] = ()
        warnings: tuple[str, ...] = ()
        if category_topic is selected:
            reasons += ("SOURCE_CATEGORY_TOPIC_MATCH",)
            signals += (f"CATEGORY_{selected.value}",)
        if title_matches.get(selected):
            reasons += ("TITLE_TOPIC_SIGNAL",)
            signals += (f"TITLE_{selected.value}_SIGNAL",)
        if body_matches.get(selected):
            reasons += ("BODY_TOPIC_SIGNAL",)
            signals += (f"BODY_{selected.value}_SIGNAL",)
        if tag_matches.get(selected):
            reasons += ("TAG_TOPIC_SIGNAL",)
            signals += ("TAGS_SUPPORT_TOPIC",)
        if selected is Topic.GOVERNMENT and government_entity_support:
            reasons += ("GOVERNMENT_ENTITY_SIGNAL",)
            signals += ("GOVERNMENT_ENTITIES_PRESENT",)
        if selected is Topic.ECONOMY and structured_economic:
            reasons += ("ECONOMIC_STRUCTURE_SIGNAL",)
            signals += ("STRUCTURED_ECONOMIC_VALUES",)
        if legacy_topic is selected:
            reasons += ("LEGACY_CONTENT_TYPE_TOPIC_SIGNAL",)
            signals += ("LEGACY_TOPIC_SUPPORT",)
        if category_conflict or non_category_conflict:
            reasons += ("TOPIC_CONFLICT_RESOLVED",)
        if category_conflict:
            warnings += ("CATEGORY_TOPIC_CONFLICT",)
        if non_category_conflict:
            warnings += ("CONFLICTING_TOPIC_SIGNALS",)

        confidence = self._confidence(
            selected=selected,
            category_topic=category_topic,
            title_matches=title_matches,
            body_matches=body_matches,
            tag_matches=tag_matches,
            legacy_topic=legacy_topic,
            has_conflict=category_conflict or non_category_conflict,
        )
        if confidence is TopicConfidence.LOW:
            warnings += ("LOW_TOPIC_CONFIDENCE",)
        return TopicClassification(
            topic=selected,
            confidence=confidence,
            reason_codes=self._unique(reasons),
            supporting_signals=self._unique(signals),
            warnings=self._unique(warnings),
        )

    @staticmethod
    def _category_topic(category: str | None) -> Topic | None:
        """Map one exact normalized source category to a supported topic."""
        if category is None:
            return None
        return _CATEGORY_TOPICS.get(category.strip().lower())

    @staticmethod
    def _matches_by_topic(text: str) -> dict[Topic, tuple[str, ...]]:
        """Return distinct matching terms grouped by topic."""
        return {
            topic: tuple(term for term in terms if term in text)
            for topic, terms in _TOPIC_TERMS.items()
            if any(term in text for term in terms)
        }

    @staticmethod
    def _apply_sports_safety(
        source: NormalizedSource,
        content_classification: ContentTypeClassification,
        *matches: dict[Topic, tuple[str, ...]],
    ) -> None:
        """Discard weak sports metaphors unless genuine sports context exists."""
        combined = "\n".join((source.title, source.body, *source.tags)).lower()
        category_support = DeterministicTopicClassifier._category_topic(
            source.category
        ) is Topic.SPORTS
        legacy_support = (
            content_classification.content_type is ContentType.SPORTS_NEWS
        )
        strong_context = any(term in combined for term in _STRONG_SPORTS_TERMS)
        tag_context = any(
            term in "\n".join(source.tags).lower() for term in _SPORTS_TAG_TERMS
        )
        if not (category_support or legacy_support or strong_context or tag_context):
            for grouped_matches in matches:
                grouped_matches.pop(Topic.SPORTS, None)

    @staticmethod
    def _structured_economic_support(text: str, facts: ExtractedFacts) -> bool:
        """Require both structured values and explicit market terminology."""
        has_values = bool(facts.currencies or facts.percentages or facts.numbers)
        return has_values and any(term in text for term in _ECONOMIC_MARKET_TERMS)

    @staticmethod
    def _select_topic(
        *,
        scores: dict[Topic, int],
        category_topic: Topic | None,
        title_matches: dict[Topic, tuple[str, ...]],
        body_matches: dict[Topic, tuple[str, ...]],
        tag_matches: dict[Topic, tuple[str, ...]],
        facts: ExtractedFacts,
        government_entity_support: bool,
        structured_economic: bool,
        legacy_topic: Topic | None,
        legacy_reliable: bool,
    ) -> Topic | None:
        """Select the strongest topic with deterministic semantic tie-breaks."""
        evidence_topics = tuple(topic for topic, score in scores.items() if score > 0)
        if not evidence_topics:
            return None

        technology_evidence = len(title_matches.get(Topic.TECHNOLOGY, ())) + len(
            body_matches.get(Topic.TECHNOLOGY, ())
        )
        economy_evidence = len(title_matches.get(Topic.ECONOMY, ())) + len(
            body_matches.get(Topic.ECONOMY, ())
        )
        if (
            title_matches.get(Topic.TECHNOLOGY)
            and technology_evidence >= 2
            and (economy_evidence or facts.percentages or facts.currencies)
        ):
            return Topic.TECHNOLOGY

        if title_matches.get(Topic.BUSINESS) and (
            len(title_matches[Topic.BUSINESS]) >= 2
            or body_matches.get(Topic.BUSINESS)
        ):
            return Topic.BUSINESS

        if title_matches.get(Topic.ECONOMY) and (
            "البنك المركزي" in title_matches[Topic.ECONOMY]
            or len(title_matches[Topic.ECONOMY]) >= 2
        ):
            return Topic.ECONOMY

        if title_matches.get(Topic.WEATHER):
            return Topic.WEATHER
        if title_matches.get(Topic.CULTURE) and not title_matches.get(Topic.SCIENCE):
            return Topic.CULTURE

        non_category_title = {
            topic: len(terms)
            for topic, terms in title_matches.items()
            if topic is not category_topic
        }
        if non_category_title:
            strongest_title = max(
                non_category_title,
                key=lambda topic: (
                    non_category_title[topic],
                    scores[topic],
                    -list(Topic).index(topic),
                ),
            )
            if non_category_title[strongest_title] >= 2 and (
                scores[strongest_title] >= scores.get(category_topic, 0)
            ):
                return strongest_title

        selected = max(
            evidence_topics,
            key=lambda topic: (
                scores[topic],
                len(title_matches.get(topic, ())),
                len(body_matches.get(topic, ())),
                -list(Topic).index(topic),
            ),
        )
        if category_topic is None:
            distinct_evidence = set(title_matches.get(selected, ())) | set(
                body_matches.get(selected, ())
            ) | set(tag_matches.get(selected, ()))
            textual_groups = sum(
                bool(matches.get(selected))
                for matches in (title_matches, body_matches, tag_matches)
            )
            supported_exception = (
                (legacy_topic is selected and legacy_reliable)
                or (
                    selected is Topic.ECONOMY
                    and structured_economic
                    and bool(distinct_evidence)
                )
                or (
                    selected is Topic.GOVERNMENT
                    and government_entity_support
                    and bool(distinct_evidence)
                )
            )
            if (
                len(distinct_evidence) < 2
                and textual_groups < 2
                and not supported_exception
            ):
                return None
        return selected

    @staticmethod
    def _strong_non_category_topics(
        title_matches: dict[Topic, tuple[str, ...]],
        body_matches: dict[Topic, tuple[str, ...]],
    ) -> tuple[Topic, ...]:
        """Return topics supported by at least two distinct textual groups."""
        return tuple(
            topic
            for topic in _TOPIC_TERMS
            if len(
                set(title_matches.get(topic, ()))
                | set(body_matches.get(topic, ()))
            )
            >= 2
        )

    @staticmethod
    def _confidence(
        *,
        selected: Topic,
        category_topic: Topic | None,
        title_matches: dict[Topic, tuple[str, ...]],
        body_matches: dict[Topic, tuple[str, ...]],
        tag_matches: dict[Topic, tuple[str, ...]],
        legacy_topic: Topic | None,
        has_conflict: bool,
    ) -> TopicConfidence:
        """Return stable confidence from consistency and evidence strength."""
        if has_conflict:
            return TopicConfidence.MEDIUM
        if category_topic is selected:
            return TopicConfidence.HIGH
        textual_groups = sum(
            bool(matches.get(selected))
            for matches in (title_matches, body_matches, tag_matches)
        )
        distinct_terms = len(
            set(title_matches.get(selected, ()))
            | set(body_matches.get(selected, ()))
            | set(tag_matches.get(selected, ()))
        )
        if textual_groups >= 2 and distinct_terms >= 2:
            return TopicConfidence.HIGH
        if legacy_topic is selected or distinct_terms >= 2:
            return TopicConfidence.MEDIUM
        return TopicConfidence.LOW

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Remove duplicates while preserving first occurrence order."""
        return tuple(dict.fromkeys(values))
