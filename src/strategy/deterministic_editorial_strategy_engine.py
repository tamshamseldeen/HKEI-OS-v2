"""Deterministic selection of an editorial strategy."""

from collections.abc import Iterable

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.classification.content_type import ContentType
from src.classification.content_type_classification import (
    ContentTypeClassification,
)
from src.facts.extracted_facts import ExtractedFacts
from src.intent.reader_intent import ReaderIntent
from src.intent.reader_intent_classification import ReaderIntentClassification
from src.intake.normalized_source import NormalizedSource

from .article_depth import ArticleDepth
from .article_length import ArticleLength
from .editorial_strategy import EditorialStrategy
from .writing_mode import WritingMode


_THIN = "THIN"
_STANDARD = "STANDARD"
_RICH = "RICH"
_BASE_STRATEGIES: dict[
    ContentType,
    tuple[ArticleLength, ArticleDepth, WritingMode, int, str],
] = {
    ContentType.BREAKING_NEWS: (
        ArticleLength.VERY_SHORT,
        ArticleDepth.UPDATE,
        WritingMode.DIRECT_NEWS,
        120,
        "BREAKING_UPDATE_STRATEGY",
    ),
    ContentType.STANDARD_NEWS: (
        ArticleLength.SHORT,
        ArticleDepth.STANDARD,
        WritingMode.DIRECT_NEWS,
        220,
        "STANDARD_NEWS_STRATEGY",
    ),
    ContentType.NEWS_REWRITE: (
        ArticleLength.SHORT,
        ArticleDepth.STANDARD,
        WritingMode.DIRECT_NEWS,
        220,
        "NEWS_REWRITE_STRATEGY",
    ),
    ContentType.PUBLIC_SERVICE_NEWS: (
        ArticleLength.MEDIUM,
        ArticleDepth.EXPLAINED,
        WritingMode.SERVICE,
        450,
        "SERVICE_STRATEGY",
    ),
    ContentType.GOVERNMENT_SERVICE_CONTENT: (
        ArticleLength.MEDIUM,
        ArticleDepth.EXPLAINED,
        WritingMode.SERVICE,
        450,
        "SERVICE_STRATEGY",
    ),
    ContentType.EXPLAINER: (
        ArticleLength.MEDIUM,
        ArticleDepth.EXPLAINED,
        WritingMode.EXPLAINER,
        450,
        "EXPLAINER_STRATEGY",
    ),
    ContentType.FACT_CHECK: (
        ArticleLength.MEDIUM,
        ArticleDepth.DETAILED,
        WritingMode.FACT_CHECK,
        450,
        "FACT_CHECK_STRATEGY",
    ),
    ContentType.HEALTH_CONTENT: (
        ArticleLength.SHORT,
        ArticleDepth.EXPLAINED,
        WritingMode.HIGH_RISK_CAUTION,
        220,
        "HIGH_RISK_CAUTION_STRATEGY",
    ),
    ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT: (
        ArticleLength.SHORT,
        ArticleDepth.EXPLAINED,
        WritingMode.HIGH_RISK_CAUTION,
        220,
        "HIGH_RISK_CAUTION_STRATEGY",
    ),
    ContentType.SPORTS_NEWS: (
        ArticleLength.VERY_SHORT,
        ArticleDepth.UPDATE,
        WritingMode.RESULT_REPORT,
        120,
        "RESULT_FIRST_STRATEGY",
    ),
    ContentType.TECHNOLOGY_NEWS: (
        ArticleLength.SHORT,
        ArticleDepth.STANDARD,
        WritingMode.DIRECT_NEWS,
        220,
        "TECHNOLOGY_NEWS_STRATEGY",
    ),
    ContentType.ECONOMY_NEWS: (
        ArticleLength.SHORT,
        ArticleDepth.STANDARD,
        WritingMode.DIRECT_NEWS,
        220,
        "ECONOMY_NEWS_STRATEGY",
    ),
    ContentType.TRENDING_SOCIAL_CLAIM: (
        ArticleLength.VERY_SHORT,
        ArticleDepth.UPDATE,
        WritingMode.TREND_UPDATE,
        120,
        "TREND_CAUTION_STRATEGY",
    ),
}
_MEDIUM_BASE_TYPES = {
    ContentType.PUBLIC_SERVICE_NEWS,
    ContentType.GOVERNMENT_SERVICE_CONTENT,
    ContentType.EXPLAINER,
    ContentType.FACT_CHECK,
}
_STRUCTURED_CONTENT_TYPES = {
    ContentType.PUBLIC_SERVICE_NEWS,
    ContentType.GOVERNMENT_SERVICE_CONTENT,
    ContentType.EXPLAINER,
    ContentType.FACT_CHECK,
}
_STRUCTURED_INTENTS = {
    ReaderIntent.UNDERSTAND_EVENT,
    ReaderIntent.KNOW_ACTION,
    ReaderIntent.UNDERSTAND_IMPACT,
    ReaderIntent.VERIFY_REQUIREMENTS,
}
_BULLET_CONTENT_TYPES = {
    ContentType.PUBLIC_SERVICE_NEWS,
    ContentType.GOVERNMENT_SERVICE_CONTENT,
}
_BULLET_INTENTS = {
    ReaderIntent.KNOW_ACTION,
    ReaderIntent.GET_GUIDANCE,
    ReaderIntent.VERIFY_REQUIREMENTS,
}
_FAQ_INTENTS = {
    ReaderIntent.KNOW_ACTION,
    ReaderIntent.UNDERSTAND_EVENT,
    ReaderIntent.VERIFY_REQUIREMENTS,
}


class DeterministicEditorialStrategyEngine:
    """Generate one editorial strategy using deterministic rules."""

    def decide(
        self,
        *,
        source: NormalizedSource,
        assessment: SourceRiskAssessment,
        facts: ExtractedFacts,
        content_classification: ContentTypeClassification,
        reader_intent: ReaderIntentClassification,
        user_instruction: str | None = None,
    ) -> EditorialStrategy:
        """Select an editorial strategy for analyzed source material.

        Args:
            source: Normalized source material.
            assessment: Risk assessment for the source.
            facts: Facts extracted from the source.
            content_classification: Editorial content type classification.
            reader_intent: Primary reader intent classification.
            user_instruction: Optional deterministic strategy instruction.

        Returns:
            One deterministic editorial strategy.
        """
        source_word_count = len(f"{source.title} {source.body}".split())
        fact_count = self._fact_count(facts)
        unknown_count = len(facts.unknown_information)
        depth_band, depth_reason = self._depth_band(
            source_word_count, fact_count, unknown_count
        )
        content_type = content_classification.content_type
        intent = reader_intent.reader_intent
        (
            article_length,
            article_depth,
            writing_mode,
            target_word_count,
            base_reason,
        ) = _BASE_STRATEGIES[content_type]
        reason_codes: list[str] = [base_reason, depth_reason]
        warnings: list[str] = []

        if depth_band == _THIN:
            if content_type in _MEDIUM_BASE_TYPES:
                warnings.append("SOURCE_TOO_THIN_FOR_LONG_FORM")
                reason_codes.append("SOURCE_TOO_THIN_FOR_REQUESTED_LENGTH")
            article_length = ArticleLength.VERY_SHORT
            article_depth = ArticleDepth.UPDATE
            target_word_count = 120
        elif depth_band == _STANDARD:
            if article_length is ArticleLength.LONG:
                article_length = ArticleLength.MEDIUM
            target_word_count = min(target_word_count, 450)
        elif content_type in (ContentType.EXPLAINER, ContentType.FACT_CHECK):
            article_length = ArticleLength.LONG
            target_word_count = 800

        instruction = (user_instruction or "").lower()
        short_requested = self._contains(
            instruction, ("قصير", "مختصر", "short")
        )
        long_requested = self._contains(
            instruction, ("طويل", "مفصل", "long", "detailed")
        )
        headings_requested = self._contains(
            instruction, ("استخدم عناوين", "use headings")
        )
        table_requested = self._contains(
            instruction, ("استخدم جدول", "use table")
        )
        faq_requested = self._contains(
            instruction, ("أضف أسئلة شائعة", "faq")
        )
        timeline_requested = self._contains(
            instruction, ("أضف خط زمني", "timeline")
        )

        if short_requested and article_length in (
            ArticleLength.MEDIUM,
            ArticleLength.LONG,
        ):
            article_length = ArticleLength.SHORT
            target_word_count = 220
        if long_requested:
            if depth_band == _THIN:
                warnings.append("SOURCE_TOO_THIN_FOR_LONG_FORM")
                reason_codes.append("SOURCE_TOO_THIN_FOR_REQUESTED_LENGTH")
            elif depth_band == _STANDARD:
                article_length = ArticleLength.MEDIUM
                target_word_count = 450
            else:
                article_length = ArticleLength.LONG
                target_word_count = 800

        include_reader_action = intent in (
            ReaderIntent.KNOW_ACTION,
            ReaderIntent.GET_GUIDANCE,
            ReaderIntent.VERIFY_REQUIREMENTS,
        )
        if include_reader_action:
            reason_codes.append("READER_ACTION_REQUIRED")
        if intent is ReaderIntent.CHECK_CLAIM:
            writing_mode = WritingMode.FACT_CHECK
        elif intent is ReaderIntent.COMPARE_OPTIONS:
            writing_mode = WritingMode.COMPARISON
        elif intent is ReaderIntent.FIND_RESULT:
            writing_mode = WritingMode.RESULT_REPORT
        elif intent is ReaderIntent.GET_GUIDANCE:
            writing_mode = WritingMode.HIGH_RISK_CAUTION
        elif intent is ReaderIntent.VERIFY_REQUIREMENTS:
            writing_mode = WritingMode.SERVICE

        use_quotes = bool(facts.quotes)
        use_attribution = (
            bool(facts.attributions or facts.claims)
            or intent is ReaderIntent.CHECK_CLAIM
            or assessment.risk_level
            in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
        )
        include_missing_information = bool(facts.unknown_information) or (
            intent is ReaderIntent.CHECK_CLAIM
        )
        if include_missing_information:
            reason_codes.append("MISSING_INFORMATION_MUST_BE_SHOWN")
            warnings.append("MISSING_INFORMATION_NOTICE_REQUIRED")

        length_supports_structure = article_length in (
            ArticleLength.MEDIUM,
            ArticleLength.LONG,
        )
        structure_benefits = (
            content_type in _STRUCTURED_CONTENT_TYPES
            or intent in _STRUCTURED_INTENTS
        )
        implicit_headings = structure_benefits and length_supports_structure
        use_headings = implicit_headings or (
            headings_requested
            and length_supports_structure
            and structure_benefits
        )
        headings_would_be_requested = structure_benefits or headings_requested
        if headings_would_be_requested and not use_headings and (
            article_length is ArticleLength.VERY_SHORT or headings_requested
        ):
            reason_codes.append("HEADINGS_NOT_JUSTIFIED")
        if intent in (ReaderIntent.GET_UPDATE, ReaderIntent.FIND_RESULT) and (
            article_length in (ArticleLength.VERY_SHORT, ArticleLength.SHORT)
        ):
            use_headings = False

        use_bullets = depth_band != _THIN and (
            intent in _BULLET_INTENTS or content_type in _BULLET_CONTENT_TYPES
        )
        numeric_value_count = len(facts.numbers) + len(facts.currencies)
        table_supported = depth_band != _THIN and numeric_value_count >= 2 and (
            intent is ReaderIntent.COMPARE_OPTIONS
            or content_type in _BULLET_CONTENT_TYPES
        )
        use_table = table_supported
        if intent is ReaderIntent.COMPARE_OPTIONS and not table_supported:
            reason_codes.append("TABLE_NOT_JUSTIFIED")
            warnings.append("UNSUPPORTED_TABLE_REQUEST")
        elif table_requested and not table_supported:
            reason_codes.append("TABLE_NOT_JUSTIFIED")
            warnings.append("UNSUPPORTED_TABLE_REQUEST")

        faq_supported = (
            intent in _FAQ_INTENTS
            and length_supports_structure
            and fact_count >= 6
        )
        use_faq = faq_supported
        if faq_requested and not faq_supported:
            reason_codes.append("FAQ_NOT_JUSTIFIED")
            warnings.append("UNSUPPORTED_FAQ_REQUEST")

        timeline_supported = (
            depth_band != _THIN
            and intent is ReaderIntent.FOLLOW_DEVELOPMENT
            and len(facts.dates) >= 2
        )
        use_timeline = timeline_supported
        if intent is ReaderIntent.FOLLOW_DEVELOPMENT and not timeline_supported:
            reason_codes.append("TIMELINE_NOT_JUSTIFIED")
            warnings.append("UNSUPPORTED_TIMELINE_REQUEST")
        elif timeline_requested and not timeline_supported:
            reason_codes.append("TIMELINE_NOT_JUSTIFIED")
            warnings.append("UNSUPPORTED_TIMELINE_REQUEST")

        use_background = depth_band == _RICH and intent in (
            ReaderIntent.UNDERSTAND_EVENT,
            ReaderIntent.UNDERSTAND_IMPACT,
        )

        if assessment.risk_level is RiskLevel.HIGH:
            use_attribution = True
            writing_mode = WritingMode.HIGH_RISK_CAUTION
            use_background = False
            warnings.append("HIGH_RISK_REVIEW_REQUIRED")
        elif assessment.risk_level is RiskLevel.CRITICAL:
            use_attribution = True
            writing_mode = WritingMode.HIGH_RISK_CAUTION
            article_length = ArticleLength.VERY_SHORT
            article_depth = ArticleDepth.UPDATE
            target_word_count = 120
            use_headings = False
            use_bullets = False
            use_table = False
            use_faq = False
            use_timeline = False
            use_background = False
            warnings.append("CRITICAL_RISK_GENERATION_RESTRICTED")

        return EditorialStrategy(
            article_length=article_length,
            article_depth=article_depth,
            writing_mode=writing_mode,
            use_headings=use_headings,
            use_bullets=use_bullets,
            use_table=use_table,
            use_faq=use_faq,
            use_timeline=use_timeline,
            use_background=use_background,
            use_quotes=use_quotes,
            use_attribution=use_attribution,
            include_missing_information=include_missing_information,
            include_reader_action=include_reader_action,
            target_word_count=target_word_count,
            reason_codes=self._unique(reason_codes),
            warnings=self._unique(warnings),
        )

    @staticmethod
    def _fact_count(facts: ExtractedFacts) -> int:
        """Count facts used to determine source depth.

        Args:
            facts: Extracted fact collections.

        Returns:
            Total count across the specified depth collections.
        """
        return sum(
            len(values)
            for values in (
                facts.core_facts,
                facts.claims,
                facts.quotes,
                facts.dates,
                facts.numbers,
                facts.currencies,
                facts.events,
            )
        )

    @staticmethod
    def _depth_band(
        source_word_count: int,
        fact_count: int,
        unknown_count: int,
    ) -> tuple[str, str]:
        """Select the source depth band in required precedence order.

        Args:
            source_word_count: Whitespace-separated title and body word count.
            fact_count: Supported fact count.
            unknown_count: Material unknown-information count.

        Returns:
            Depth band and its stable reason code.
        """
        if (
            source_word_count < 60
            or fact_count <= 2
            or unknown_count >= fact_count
            and unknown_count > 0
        ):
            return _THIN, "LIMITED_SOURCE_DEPTH"
        if 60 <= source_word_count <= 249 and 3 <= fact_count <= 12:
            return _STANDARD, "SUFFICIENT_STANDARD_DEPTH"
        return _RICH, "RICH_SOURCE_DEPTH"

    @staticmethod
    def _contains(text: str, terms: Iterable[str]) -> bool:
        """Check whether lowercase text contains any configured term.

        Args:
            text: Lowercase searchable instruction.
            terms: Deterministic terms to match.

        Returns:
            True when at least one term is present.
        """
        return any(term.lower() in text for term in terms)

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Return values without duplicates while preserving order.

        Args:
            values: Ordered string values.

        Returns:
            Values preserving only their first occurrence.
        """
        return tuple(dict.fromkeys(values))
