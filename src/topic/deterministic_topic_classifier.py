"""Deterministic classification of one primary editorial topic."""

from collections.abc import Iterable
import re

from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.evidence_level import EvidenceLevel
from src.evidence.evidence_strength import EvidenceStrength
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)

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
        "العملات المشفرة",
        "الأصول الرقمية",
        "النظام المالي",
        "هيئات تنظيمية مالية",
        "رقابة مالية",
        "المستثمرين",
        "سوق العمل",
        "معدل البطالة",
    ),
    Topic.BUSINESS: (
        "شركة",
        "شركات",
        "صافي أرباح",
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
        "البطاريات الصلبة",
        "بطاريات الحالة الصلبة",
        "السيارات الكهربائية",
        "الرقائق الإلكترونية",
        "صناعة الرقائق",
    ),
    Topic.SPORTS: (
        "مباراة",
        "المباراة",
        "منتخب",
        "المنتخب",
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
        "مصلحة الضرائب",
        "مصلحة الضرائب المصرية",
        "الفاتورة الإلكترونية",
        "الممولين",
        "المكلفين",
        "التسجيل في منظومة",
        "جهة حكومية",
    ),
    Topic.WEATHER: (
        "موجة حر",
        "درجات الحرارة",
        "ودرجات الحرارة",
        "طقس",
        "أمطار",
        "عاصفة",
        "جفاف",
        "الجفاف",
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
        "معرض الكتاب",
        "معرض القاهرة الدولي للكتاب",
        "هيئة الكتاب",
        "نشر",
        "ثقافي",
        "ثقافية",
    ),
    Topic.SCIENCE: (
        "دراسة علمية",
        "اكتشاف علمي",
        "باحثون",
        "أبحاث",
        "فضاء",
        "الفضاء",
        "فيزياء",
        "كيمياء",
        "أحياء",
        "علماء",
        "علماء الفلك",
        "كوكب",
        "كوكب خارجي",
        "المجموعة الشمسية",
        "مرصد",
        "فلك",
        "قمر صناعي",
        "أقمار صناعية",
        "تلسكوب",
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
        "الأمم المتحدة",
        "قمة المناخ",
        "مؤتمر الأمم المتحدة",
        "الدول المشاركة",
        "اتفاق دولي",
        "مساعدات دولية",
    ),
}

_WEAK_TOPIC_TERMS = {
    Topic.SPORTS: frozenset(("فريق", "هدف", "نتيجة", "انتقال", "تدريبات")),
    Topic.BUSINESS: frozenset(("شركة", "شركات")),
    Topic.GOVERNMENT: frozenset(("وزارة",)),
}

_CATEGORY_WEIGHT = 10
_STRONG_TITLE_WEIGHT = 8
_STRONG_BODY_WEIGHT = 3
_WEAK_TITLE_WEIGHT = 2
_WEAK_BODY_WEIGHT = 1
_STRONG_TAG_WEIGHT = 3
_WEAK_TAG_WEIGHT = 1
_LEGACY_CORROBORATION_WEIGHT = 1

_CONTEXTUAL_TOPIC_LABELS = {
    f"TOPIC_{topic.value}": topic for topic in Topic if topic is not Topic.GENERAL
}
_SEMANTIC_PRIMARY_LABELS = {
    f"PRIMARY_DOMAIN_{topic.value}": topic
    for topic in Topic
    if topic is not Topic.GENERAL
}
_SEMANTIC_SECONDARY_LABELS = {
    f"SECONDARY_DOMAIN_{topic.value}": topic
    for topic in Topic
    if topic is not Topic.GENERAL
}
_CONTEXTUAL_WEIGHTS = {
    (EvidenceLevel.STRUCTURAL, EvidenceStrength.STRONG): 14,
    (EvidenceLevel.CONTEXT, EvidenceStrength.STRONG): 12,
    (EvidenceLevel.PHRASE, EvidenceStrength.STRONG): 10,
    (EvidenceLevel.STRUCTURAL, EvidenceStrength.MEDIUM): 10,
    (EvidenceLevel.CONTEXT, EvidenceStrength.MEDIUM): 7,
    (EvidenceLevel.PHRASE, EvidenceStrength.MEDIUM): 6,
    (EvidenceLevel.TOKEN, EvidenceStrength.WEAK): 1,
}
_CONTEXTUAL_SECTION_BONUS = {
    "HEADLINE": 2,
    "LEAD": 1,
}
_STRONG_SUPPRESSION_PENALTY = 4

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
        contextual_evidence: ContextualEvidence | None = None,
        semantic_evidence: CompositionalSemanticEvidence | None = None,
    ) -> TopicClassification:
        """Classify one source from supplied deterministic signals only.

        Args:
            source: Normalized source material and metadata.
            facts: Deterministically extracted source facts.
            assessment: Existing independent source risk assessment.
            content_classification: Transitional legacy content classification.
            user_instruction: Optional supplied editorial instruction.
            contextual_evidence: Optional deterministic contextual evidence.
            semantic_evidence: Optional compositional semantic evidence.

        Returns:
            Exactly one primary topic classification.
        """
        title = self._normalize_for_matching(source.title)
        body = self._normalize_for_matching(source.body)
        tags_text = self._normalize_for_matching("\n".join(source.tags))
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

        scores = {topic: 0 for topic in Topic if topic is not Topic.GENERAL}
        if category_topic is not None:
            scores[category_topic] += _CATEGORY_WEIGHT
        for topic in scores:
            scores[topic] += self._match_score(
                topic,
                title_matches.get(topic, ()),
                strong_weight=_STRONG_TITLE_WEIGHT,
                weak_weight=_WEAK_TITLE_WEIGHT,
            )
            scores[topic] += self._match_score(
                topic,
                body_matches.get(topic, ()),
                strong_weight=_STRONG_BODY_WEIGHT,
                weak_weight=_WEAK_BODY_WEIGHT,
            )
            scores[topic] += self._match_score(
                topic,
                tag_matches.get(topic, ()),
                strong_weight=_STRONG_TAG_WEIGHT,
                weak_weight=_WEAK_TAG_WEIGHT,
            )

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
        legacy_support_applied = (
            legacy_topic is not None
            and legacy_reliable
            and self._has_strong_textual_support(
                legacy_topic,
                title_matches,
                body_matches,
                tag_matches,
            )
        )
        if legacy_support_applied and legacy_topic is not None:
            scores[legacy_topic] += _LEGACY_CORROBORATION_WEIGHT

        for risk_topic in assessment.risk_topics:
            supported = _RISK_TOPIC_SUPPORT.get(risk_topic.lower())
            if supported is not None and scores[supported] > 0:
                scores[supported] += 1

        contextual_scores, contextual_counts = self._contextual_topic_scores(
            contextual_evidence
        )
        semantic_primary, semantic_secondary, strong_semantic_primary = (
            self._semantic_topics(semantic_evidence)
        )
        semantic_suppressed = self._semantic_suppressed_topics(semantic_evidence)
        scores_before_suppression = scores.copy()
        for topic, score in contextual_scores.items():
            scores[topic] += score
            scores_before_suppression[topic] += score
        suppressed_topics = self._strongly_suppressed_topics(contextual_evidence)
        suppression_applied: set[Topic] = set()
        for topic in suppressed_topics:
            if scores[topic] <= 0:
                continue
            has_genuine_support = self._has_strong_textual_support(
                topic,
                title_matches,
                body_matches,
                tag_matches,
            ) or contextual_scores.get(topic, 0) >= _CONTEXTUAL_WEIGHTS[
                (EvidenceLevel.PHRASE, EvidenceStrength.STRONG)
            ]
            penalty = min(
                scores[topic],
                _STRONG_SUPPRESSION_PENALTY if has_genuine_support else scores[topic],
            )
            scores[topic] -= penalty
            suppression_applied.add(topic)

        semantic_suppression_applied: set[Topic] = set()
        if strong_semantic_primary:
            for topic in semantic_suppressed:
                if topic in strong_semantic_primary:
                    continue
                if scores[topic] > 0:
                    scores[topic] = 0
                    semantic_suppression_applied.add(topic)

        baseline_selected = self._select_topic(
            scores=scores,
            category_topic=category_topic,
            title_matches=title_matches,
            body_matches=body_matches,
            tag_matches=tag_matches,
            government_entity_support=government_entity_support,
            structured_economic=structured_economic,
            contextual_scores=contextual_scores,
        )
        selected = baseline_selected
        if category_topic is None:
            unsuppressed_strong = tuple(
                topic
                for topic in strong_semantic_primary
                if topic not in semantic_suppressed
            )
            if unsuppressed_strong:
                selected = unsuppressed_strong[0]
            elif selected is None:
                unsuppressed_primary = tuple(
                    topic
                    for topic in semantic_primary
                    if topic not in semantic_suppressed
                )
                if unsuppressed_primary:
                    selected = unsuppressed_primary[0]
                elif semantic_secondary:
                    selected = semantic_secondary[0]
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

        semantic_category_conflict = bool(
            category_topic is not None
            and semantic_primary
            and category_topic not in semantic_primary
        )
        category_conflict = bool(
            category_topic is not None
            and (category_topic is not selected or semantic_category_conflict)
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
        if legacy_topic is selected and legacy_support_applied:
            reasons += ("LEGACY_CONTENT_TYPE_TOPIC_SIGNAL",)
            signals += ("LEGACY_TOPIC_SUPPORT",)
        contextual_selected = contextual_scores.get(selected, 0) > 0
        if contextual_selected:
            reasons += ("CONTEXTUAL_TOPIC_EVIDENCE",)
            signals += ("CONTEXTUAL_TOPIC_SUPPORT",)
        suppression_material = bool(
            suppression_applied
            and any(
                topic is not selected and scores_before_suppression[topic] > 0
                for topic in suppression_applied
            )
        )
        if suppression_material:
            reasons += ("CONTEXTUAL_TOPIC_SUPPRESSION",)
            signals += ("CONTEXTUAL_COMPETING_TOPIC_SUPPRESSED",)
        semantic_primary_material = selected in semantic_primary and (
            category_topic is None
            and (
                baseline_selected is not selected
                or baseline_selected is None
                or selected in strong_semantic_primary
            )
        )
        semantic_secondary_material = bool(
            semantic_primary_material
            and any(topic is not selected for topic in semantic_secondary)
        ) or (
            selected in semantic_secondary and selected not in semantic_primary
        )
        semantic_suppression_material = bool(
            semantic_primary_material
            and (
                semantic_suppression_applied
                or any(
                    topic is not selected
                    and topic in semantic_suppressed
                    and topic in semantic_primary + semantic_secondary
                    for topic in semantic_suppressed
                )
            )
        )
        if semantic_primary_material or semantic_secondary_material:
            reasons += ("COMPOSITIONAL_SEMANTIC_TOPIC_EVIDENCE",)
        if semantic_suppression_material:
            reasons += ("COMPOSITIONAL_SEMANTIC_TOPIC_SUPPRESSION",)
        if semantic_primary_material and semantic_secondary:
            reasons += ("PRIMARY_SECONDARY_DOMAIN_RESOLUTION",)
        if semantic_primary_material:
            signals += ("SEMANTIC_PRIMARY_DOMAIN_SUPPORT",)
        if semantic_secondary_material:
            signals += ("SEMANTIC_SECONDARY_DOMAIN_SUPPORT",)
        if semantic_suppression_material:
            signals += ("SEMANTIC_COMPETING_DOMAIN_SUPPRESSED",)
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
            legacy_support_applied=legacy_support_applied,
            has_conflict=category_conflict or non_category_conflict,
        )
        confidence = self._contextual_confidence(
            current=confidence,
            selected=selected,
            contextual_scores=contextual_scores,
            contextual_counts=contextual_counts,
            scores=scores,
            suppression_material=suppression_material,
        )
        if semantic_primary_material:
            unsuppressed_competing = tuple(
                topic
                for topic in semantic_primary
                if topic is not selected and topic not in semantic_suppressed
            )
            confidence = (
                TopicConfidence.HIGH
                if selected in strong_semantic_primary
                and not unsuppressed_competing
                and len(semantic_primary) == 1
                else TopicConfidence.MEDIUM
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
        """Return distinct token-aware matching terms grouped by topic."""
        normalized = DeterministicTopicClassifier._normalize_for_matching(text)
        return {
            topic: tuple(
                term
                for term in terms
                if DeterministicTopicClassifier._contains_term(normalized, term)
            )
            for topic, terms in _TOPIC_TERMS.items()
            if any(
                DeterministicTopicClassifier._contains_term(normalized, term)
                for term in terms
            )
        }

    @staticmethod
    def _normalize_for_matching(text: str) -> str:
        """Lowercase text, separate punctuation, and collapse whitespace."""
        return " ".join(re.sub(r"[\W_]+", " ", text.lower()).split())

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        """Match a normalized term only at complete Unicode token boundaries."""
        normalized_term = DeterministicTopicClassifier._normalize_for_matching(term)
        if not normalized_term:
            return False
        return re.search(
            rf"(?<!\w){re.escape(normalized_term)}(?!\w)",
            text,
        ) is not None

    @staticmethod
    def _is_weak_term(topic: Topic, term: str) -> bool:
        """Return whether one topic term is intentionally weak evidence."""
        return term in _WEAK_TOPIC_TERMS.get(topic, frozenset())

    @staticmethod
    def _match_score(
        topic: Topic,
        terms: tuple[str, ...],
        *,
        strong_weight: int,
        weak_weight: int,
    ) -> int:
        """Score strong and weak terms with distinct deterministic weights."""
        return sum(
            weak_weight
            if DeterministicTopicClassifier._is_weak_term(topic, term)
            else strong_weight
            for term in terms
        )

    @staticmethod
    def _has_strong_textual_support(
        topic: Topic,
        *matches: dict[Topic, tuple[str, ...]],
    ) -> bool:
        """Return whether independent non-weak text corroborates one topic."""
        return any(
            not DeterministicTopicClassifier._is_weak_term(topic, term)
            for grouped_matches in matches
            for term in grouped_matches.get(topic, ())
        )

    @staticmethod
    def _structured_economic_support(text: str, facts: ExtractedFacts) -> bool:
        """Require both structured values and explicit market terminology."""
        has_values = bool(facts.currencies or facts.percentages or facts.numbers)
        return has_values and any(
            DeterministicTopicClassifier._contains_term(text, term)
            for term in _ECONOMIC_MARKET_TERMS
        )

    @staticmethod
    def _select_topic(
        *,
        scores: dict[Topic, int],
        category_topic: Topic | None,
        title_matches: dict[Topic, tuple[str, ...]],
        body_matches: dict[Topic, tuple[str, ...]],
        tag_matches: dict[Topic, tuple[str, ...]],
        government_entity_support: bool,
        structured_economic: bool,
        contextual_scores: dict[Topic, int],
    ) -> Topic | None:
        """Select the strongest topic with deterministic semantic tie-breaks."""
        evidence_topics = tuple(topic for topic, score in scores.items() if score > 0)
        if not evidence_topics:
            return None

        eligible_topics = tuple(
            topic
            for topic in evidence_topics
            if topic is category_topic
            or DeterministicTopicClassifier._has_strong_textual_support(
                topic,
                title_matches,
                body_matches,
                tag_matches,
            )
            or (topic is Topic.GOVERNMENT and government_entity_support)
            or (topic is Topic.ECONOMY and structured_economic)
            or contextual_scores.get(topic, 0) > 0
        )
        if not eligible_topics:
            return None

        selected = max(
            eligible_topics,
            key=lambda topic: (
                scores[topic],
                DeterministicTopicClassifier._match_score(
                    topic,
                    title_matches.get(topic, ()),
                    strong_weight=1,
                    weak_weight=0,
                ),
                DeterministicTopicClassifier._match_score(
                    topic,
                    body_matches.get(topic, ()),
                    strong_weight=1,
                    weak_weight=0,
                ),
                -list(Topic).index(topic),
            ),
        )
        if category_topic is None:
            has_strong_text = DeterministicTopicClassifier._has_strong_textual_support(
                selected,
                title_matches,
                body_matches,
                tag_matches,
            )
            if not has_strong_text and not (
                (selected is Topic.ECONOMY and structured_economic)
                or (selected is Topic.GOVERNMENT and government_entity_support)
                or contextual_scores.get(selected, 0) > 0
            ):
                return None
        return selected

    @staticmethod
    def _contextual_topic_scores(
        contextual_evidence: ContextualEvidence | None,
    ) -> tuple[dict[Topic, int], dict[Topic, int]]:
        """Aggregate recognized contextual topic labels with integer weights."""
        scores: dict[Topic, int] = {}
        strong_counts: dict[Topic, int] = {}
        if contextual_evidence is None:
            return scores, strong_counts
        for item in contextual_evidence.all_items:
            weight = _CONTEXTUAL_WEIGHTS.get((item.evidence_level, item.strength), 0)
            if weight == 0:
                continue
            weight += _CONTEXTUAL_SECTION_BONUS.get(item.source_section.value, 0)
            for label in item.supports:
                topic = _CONTEXTUAL_TOPIC_LABELS.get(label)
                if topic is None:
                    continue
                scores[topic] = scores.get(topic, 0) + weight
                if item.strength is EvidenceStrength.STRONG:
                    strong_counts[topic] = strong_counts.get(topic, 0) + 1
        return scores, strong_counts

    @staticmethod
    def _strongly_suppressed_topics(
        contextual_evidence: ContextualEvidence | None,
    ) -> frozenset[Topic]:
        """Return recognized topics targeted by strong contextual suppression."""
        if contextual_evidence is None:
            return frozenset()
        return frozenset(
            topic
            for item in contextual_evidence.all_items
            if item.strength is EvidenceStrength.STRONG
            for label in item.suppresses
            if (topic := _CONTEXTUAL_TOPIC_LABELS.get(label)) is not None
        )

    @staticmethod
    def _semantic_topics(
        semantic_evidence: CompositionalSemanticEvidence | None,
    ) -> tuple[tuple[Topic, ...], tuple[Topic, ...], tuple[Topic, ...]]:
        """Map ordered semantic candidates and detect strong primary support."""
        if semantic_evidence is None:
            return (), (), ()
        primary = tuple(
            dict.fromkeys(
                topic
                for label in semantic_evidence.primary_domain_candidates
                if (topic := _SEMANTIC_PRIMARY_LABELS.get(label)) is not None
            )
        )
        secondary = tuple(
            dict.fromkeys(
                topic
                for label in semantic_evidence.secondary_domain_candidates
                if (topic := _SEMANTIC_SECONDARY_LABELS.get(label)) is not None
            )
        )
        strong_labels = {
            label
            for relationship in semantic_evidence.relationships
            if relationship.strength is EvidenceStrength.STRONG
            for label in relationship.supports
        }
        strong_primary = tuple(
            topic
            for topic in primary
            if f"PRIMARY_DOMAIN_{topic.value}" in strong_labels
        )
        return primary, secondary, strong_primary

    @staticmethod
    def _semantic_suppressed_topics(
        semantic_evidence: CompositionalSemanticEvidence | None,
    ) -> frozenset[Topic]:
        """Map recognized semantic primary-domain suppression labels."""
        if semantic_evidence is None:
            return frozenset()
        return frozenset(
            topic
            for label in semantic_evidence.all_suppressions
            if (topic := _SEMANTIC_PRIMARY_LABELS.get(label)) is not None
        )

    @staticmethod
    def _contextual_confidence(
        *,
        current: TopicConfidence,
        selected: Topic,
        contextual_scores: dict[Topic, int],
        contextual_counts: dict[Topic, int],
        scores: dict[Topic, int],
        suppression_material: bool,
    ) -> TopicConfidence:
        """Increase confidence from consistent contextual evidence when justified."""
        if not contextual_scores.get(selected):
            return current
        competing = any(
            score > 0 for topic, score in scores.items() if topic is not selected
        )
        contextual = TopicConfidence.MEDIUM
        if contextual_counts.get(selected, 0) >= 2 and not competing:
            contextual = TopicConfidence.HIGH
        if suppression_material or competing:
            contextual = TopicConfidence.MEDIUM
        rank = {
            TopicConfidence.LOW: 0,
            TopicConfidence.MEDIUM: 1,
            TopicConfidence.HIGH: 2,
        }
        return current if rank[current] >= rank[contextual] else contextual

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
        legacy_support_applied: bool,
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
        if (
            legacy_topic is selected and legacy_support_applied
        ) or distinct_terms >= 2:
            return TopicConfidence.MEDIUM
        return TopicConfidence.LOW

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Remove duplicates while preserving first occurrence order."""
        return tuple(dict.fromkeys(values))
