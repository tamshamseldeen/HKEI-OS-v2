"""Additive adaptation of editorial strategy from editorial format."""

from dataclasses import replace
from typing import Any

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.facts.extracted_facts import ExtractedFacts
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence

from .article_depth import ArticleDepth
from .article_length import ArticleLength
from .editorial_strategy import EditorialStrategy
from .writing_mode import WritingMode


class EditorialFormatStrategyAdapter:
    """Adapt an existing editorial strategy using additive format analysis."""

    def adapt(
        self,
        *,
        strategy: EditorialStrategy,
        format_classification: EditorialFormatClassification,
        facts: ExtractedFacts,
        assessment: SourceRiskAssessment,
    ) -> EditorialStrategy:
        """Return a new strategy adapted for format and then source risk.

        Args:
            strategy: Existing authoritative editorial strategy.
            format_classification: Additive editorial format classification.
            facts: Deterministically extracted facts.
            assessment: Existing source risk assessment.

        Returns:
            A new strategy with format adjustments and final risk safeguards.
        """
        changes: dict[str, Any] = {}
        reasons: tuple[str, ...] = strategy.reason_codes
        warnings: tuple[str, ...] = strategy.warnings
        editorial_format = format_classification.editorial_format

        if editorial_format is EditorialFormat.BREAKING:
            changes.update(
                article_length=ArticleLength.VERY_SHORT,
                article_depth=ArticleDepth.UPDATE,
                writing_mode=WritingMode.DIRECT_NEWS,
                use_headings=False,
                use_bullets=False,
                use_table=False,
                use_faq=False,
                use_timeline=False,
                use_background=False,
                target_word_count=120,
            )
            reasons += ("FORMAT_BREAKING_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.STANDARD_NEWS:
            reasons += ("FORMAT_STANDARD_NEWS_CONFIRMED",)
        elif editorial_format is EditorialFormat.SERVICE:
            article_length = strategy.article_length
            changes.update(
                writing_mode=WritingMode.SERVICE,
                include_reader_action=True,
                use_bullets=True,
                use_table=len(facts.numbers) + len(facts.currencies) >= 2,
            )
            if article_length is not ArticleLength.VERY_SHORT:
                article_length = ArticleLength.MEDIUM
                changes.update(
                    article_length=article_length,
                    article_depth=ArticleDepth.EXPLAINED,
                    target_word_count=450,
                )
            changes["use_headings"] = article_length in (
                ArticleLength.MEDIUM,
                ArticleLength.LONG,
            )
            reasons += ("FORMAT_SERVICE_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.GUIDE:
            structured = (
                len(facts.dates)
                + len(facts.times)
                + len(facts.numbers)
                + len(facts.currencies)
            )
            faq_support = len(facts.core_facts) + structured
            changes.update(
                article_length=ArticleLength.MEDIUM,
                article_depth=ArticleDepth.EXPLAINED,
                writing_mode=WritingMode.SERVICE,
                target_word_count=450,
                use_headings=True,
                use_bullets=True,
                use_table=structured >= 2,
                use_faq=faq_support >= 6,
                include_reader_action=True,
            )
            reasons += ("FORMAT_GUIDE_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.EXPLAINER:
            very_short = strategy.article_length is ArticleLength.VERY_SHORT
            article_length = ArticleLength.SHORT if very_short else ArticleLength.MEDIUM
            changes.update(
                article_length=article_length,
                article_depth=ArticleDepth.EXPLAINED,
                writing_mode=WritingMode.EXPLAINER,
                target_word_count=220 if very_short else 450,
                use_headings=article_length in (
                    ArticleLength.MEDIUM,
                    ArticleLength.LONG,
                ),
            )
            reasons += ("FORMAT_EXPLAINER_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.FEATURE:
            if assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                warnings += ("FORMAT_FEATURE_RESTRICTED_BY_RISK",)
                reasons += ("FORMAT_FEATURE_RESTRICTION_APPLIED",)
            elif format_classification.confidence in (
                EditorialFormatConfidence.HIGH,
                EditorialFormatConfidence.MEDIUM,
            ):
                changes.update(
                    article_length=ArticleLength.LONG,
                    article_depth=ArticleDepth.DETAILED,
                    writing_mode=WritingMode.EXPLAINER,
                    target_word_count=800,
                    use_headings=True,
                    use_background=True,
                    use_quotes=bool(facts.quotes),
                )
                reasons += ("FORMAT_FEATURE_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.FACT_CHECK:
            changes.update(
                article_length=ArticleLength.MEDIUM,
                article_depth=ArticleDepth.DETAILED,
                writing_mode=WritingMode.FACT_CHECK,
                target_word_count=450,
                use_headings=True,
                use_attribution=True,
                include_missing_information=True,
            )
            reasons += ("FORMAT_FACT_CHECK_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.ANALYSIS:
            if assessment.risk_level is RiskLevel.CRITICAL:
                warnings += ("FORMAT_ANALYSIS_RESTRICTED_BY_RISK",)
                reasons += ("FORMAT_ANALYSIS_RESTRICTION_APPLIED",)
            else:
                changes.update(
                    article_length=ArticleLength.LONG,
                    article_depth=ArticleDepth.DETAILED,
                    writing_mode=WritingMode.EXPLAINER,
                    target_word_count=800,
                    use_headings=True,
                    use_background=True,
                    use_attribution=True,
                )
                reasons += ("FORMAT_ANALYSIS_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.INTERVIEW:
            changes.update(
                article_length=ArticleLength.MEDIUM,
                article_depth=ArticleDepth.DETAILED,
                writing_mode=WritingMode.DIRECT_NEWS,
                target_word_count=450,
                use_headings=True,
                use_quotes=True,
                use_attribution=True,
            )
            reasons += ("FORMAT_INTERVIEW_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.PROFILE:
            if assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                warnings += ("FORMAT_PROFILE_RESTRICTED_BY_RISK",)
            else:
                changes.update(
                    article_length=ArticleLength.LONG,
                    article_depth=ArticleDepth.DETAILED,
                    writing_mode=WritingMode.EXPLAINER,
                    target_word_count=800,
                    use_headings=True,
                    use_background=True,
                    use_quotes=bool(facts.quotes),
                )
                reasons += ("FORMAT_PROFILE_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.RESULT_REPORT:
            changes.update(
                article_length=ArticleLength.VERY_SHORT,
                article_depth=ArticleDepth.UPDATE,
                writing_mode=WritingMode.RESULT_REPORT,
                target_word_count=120,
                use_headings=False,
                use_bullets=False,
                use_table=False,
                use_faq=False,
                use_timeline=False,
                use_background=False,
            )
            reasons += ("FORMAT_RESULT_REPORT_STRATEGY_APPLIED",)
        elif editorial_format is EditorialFormat.TREND_UPDATE:
            changes.update(
                article_length=ArticleLength.VERY_SHORT,
                article_depth=ArticleDepth.UPDATE,
                writing_mode=WritingMode.TREND_UPDATE,
                target_word_count=120,
                use_headings=False,
                use_bullets=False,
                use_table=False,
                use_faq=False,
                use_timeline=False,
                use_background=False,
                use_attribution=True,
                include_missing_information=True,
            )
            reasons += ("FORMAT_TREND_UPDATE_STRATEGY_APPLIED",)

        if assessment.risk_level is RiskLevel.HIGH:
            changes.update(
                writing_mode=WritingMode.HIGH_RISK_CAUTION,
                use_attribution=True,
                use_background=False,
            )
            warnings += ("HIGH_RISK_REVIEW_REQUIRED",)
        elif assessment.risk_level is RiskLevel.CRITICAL:
            changes.update(
                article_length=ArticleLength.VERY_SHORT,
                article_depth=ArticleDepth.UPDATE,
                writing_mode=WritingMode.HIGH_RISK_CAUTION,
                target_word_count=120,
                use_headings=False,
                use_bullets=False,
                use_table=False,
                use_faq=False,
                use_timeline=False,
                use_background=False,
                use_attribution=True,
            )
            warnings += ("CRITICAL_RISK_GENERATION_RESTRICTED",)

        return replace(
            strategy,
            **changes,
            reason_codes=self._unique(reasons),
            warnings=self._unique(warnings),
        )

    @staticmethod
    def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
        """Remove duplicates while preserving first occurrence order."""
        return tuple(dict.fromkeys(values))
