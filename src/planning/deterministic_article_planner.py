"""Deterministic construction of an internal article plan."""

from collections.abc import Iterable
from dataclasses import replace

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
from src.strategy.article_length import ArticleLength
from src.strategy.editorial_strategy import EditorialStrategy

from .article_plan import ArticlePlan
from .article_section_id import ArticleSectionId
from .article_section_plan import ArticleSectionPlan


_BASE_PROHIBITED_CLAIMS = (
    "UNSUPPORTED_FACT",
    "UNSUPPORTED_QUOTE",
    "UNSUPPORTED_NUMBER",
    "UNSUPPORTED_DATE",
    "UNSUPPORTED_CAUSE",
    "UNSUPPORTED_CONSEQUENCE",
    "UNSUPPORTED_ATTRIBUTION",
)
_LEAD_INSTRUCTIONS = {
    ReaderIntent.GET_UPDATE: "Begin with the newest confirmed fact.",
    ReaderIntent.UNDERSTAND_EVENT: (
        "Begin with the event, then establish what requires explanation."
    ),
    ReaderIntent.KNOW_ACTION: (
        "Begin with the practical consequence or required reader action."
    ),
    ReaderIntent.CHECK_CLAIM: (
        "Begin with the claim and preserve its attribution and verification "
        "status."
    ),
    ReaderIntent.COMPARE_OPTIONS: (
        "Begin by identifying the options or values being compared."
    ),
    ReaderIntent.FOLLOW_DEVELOPMENT: (
        "Begin with the latest confirmed development."
    ),
    ReaderIntent.FIND_RESULT: "Begin with the confirmed result.",
    ReaderIntent.UNDERSTAND_IMPACT: (
        "Begin with the event or decision and identify who is affected."
    ),
    ReaderIntent.GET_GUIDANCE: (
        "Begin with cautious source-supported guidance and required "
        "attribution."
    ),
    ReaderIntent.VERIFY_REQUIREMENTS: (
        "Begin with the service, eligibility, or primary requirement."
    ),
}
_CLOSING_INSTRUCTIONS = {
    ReaderIntent.GET_UPDATE: (
        "End with the final confirmed detail without repetition."
    ),
    ReaderIntent.UNDERSTAND_EVENT: (
        "End with the clearest supported explanation or remaining uncertainty."
    ),
    ReaderIntent.KNOW_ACTION: "End with the source-supported next step.",
    ReaderIntent.CHECK_CLAIM: (
        "End with the supported verification status and remaining uncertainty."
    ),
    ReaderIntent.COMPARE_OPTIONS: (
        "End with the clearest supported distinction."
    ),
    ReaderIntent.FOLLOW_DEVELOPMENT: (
        "End with the latest confirmed status without predicting future events."
    ),
    ReaderIntent.FIND_RESULT: (
        "End with one essential confirmed result detail."
    ),
    ReaderIntent.UNDERSTAND_IMPACT: (
        "End with the clearest supported consequence."
    ),
    ReaderIntent.GET_GUIDANCE: (
        "End with a cautious source-supported action or warning."
    ),
    ReaderIntent.VERIFY_REQUIREMENTS: (
        "End with the final supported requirement, deadline, or official next "
        "step."
    ),
}
_PURPOSES = {
    ArticleSectionId.LEAD: (
        "Open with the primary reader need and strongest supported fact."
    ),
    ArticleSectionId.CORE_UPDATE: "Present the main confirmed development.",
    ArticleSectionId.RESULT: "State the confirmed result and essential outcome.",
    ArticleSectionId.KEY_DETAILS: "Add the most useful supported details.",
    ArticleSectionId.OFFICIAL_INFORMATION: (
        "Present attributed official information."
    ),
    ArticleSectionId.CLAIM: "State the identifiable claim with attribution.",
    ArticleSectionId.EVIDENCE: (
        "Present supplied evidence and verification limits."
    ),
    ArticleSectionId.VERDICT: "State the supported verification conclusion.",
    ArticleSectionId.REQUIREMENTS: (
        "List supported eligibility, documents, or conditions."
    ),
    ArticleSectionId.PROCEDURE: "Explain supported procedural steps.",
    ArticleSectionId.FEES: (
        "Present exact supported fees, fines, or monetary values."
    ),
    ArticleSectionId.DEADLINES: (
        "Present exact supported dates and deadlines."
    ),
    ArticleSectionId.READER_ACTION: "State the source-supported next action.",
    ArticleSectionId.IMPACT: (
        "Explain supported consequences and affected parties."
    ),
    ArticleSectionId.EXPLANATION: (
        "Explain how or why using supplied material only."
    ),
    ArticleSectionId.BACKGROUND: (
        "Provide supplied background required for understanding."
    ),
    ArticleSectionId.TIMELINE: (
        "Present supported events in chronological order."
    ),
    ArticleSectionId.COMPARISON: "Compare supplied structured values.",
    ArticleSectionId.QUOTES: "Present exact attributed quotations.",
    ArticleSectionId.MISSING_INFORMATION: (
        "State material unknowns concisely."
    ),
    ArticleSectionId.CLOSING: (
        "End without repetition or unsupported prediction."
    ),
}
_HEADING_GUIDANCE = {
    ArticleSectionId.CORE_UPDATE: (
        "Use a specific Arabic heading describing the main update."
    ),
    ArticleSectionId.RESULT: (
        "Use a specific Arabic heading describing the confirmed result."
    ),
    ArticleSectionId.KEY_DETAILS: (
        "Use a specific Arabic heading describing the key details."
    ),
    ArticleSectionId.OFFICIAL_INFORMATION: (
        "Use a specific Arabic heading identifying the official information."
    ),
    ArticleSectionId.CLAIM: (
        "Use a specific Arabic heading identifying the claim."
    ),
    ArticleSectionId.EVIDENCE: (
        "Use a specific Arabic heading describing the evidence."
    ),
    ArticleSectionId.VERDICT: (
        "Use a specific Arabic heading describing the verification result."
    ),
    ArticleSectionId.REQUIREMENTS: (
        "Use a specific Arabic heading describing the requirements."
    ),
    ArticleSectionId.PROCEDURE: (
        "Use a specific Arabic heading describing the procedure."
    ),
    ArticleSectionId.FEES: (
        "Use a specific Arabic heading describing fees or penalties."
    ),
    ArticleSectionId.DEADLINES: (
        "Use a specific Arabic heading describing dates or deadlines."
    ),
    ArticleSectionId.READER_ACTION: (
        "Use a specific Arabic heading describing the required action."
    ),
    ArticleSectionId.IMPACT: (
        "Use a specific Arabic heading describing the impact."
    ),
    ArticleSectionId.EXPLANATION: (
        "Use a specific Arabic heading describing the explanation."
    ),
    ArticleSectionId.BACKGROUND: (
        "Use a specific Arabic heading describing necessary background."
    ),
    ArticleSectionId.TIMELINE: (
        "Use a specific Arabic heading describing the timeline."
    ),
    ArticleSectionId.COMPARISON: (
        "Use a specific Arabic heading describing the comparison."
    ),
    ArticleSectionId.QUOTES: (
        "Use a specific Arabic heading describing attributed statements."
    ),
    ArticleSectionId.MISSING_INFORMATION: (
        "Use a specific Arabic heading describing what remains unknown."
    ),
}
_PRIMARY_PLAN_CODES = {
    ContentType.BREAKING_NEWS: "UPDATE_FIRST_PLAN",
    ContentType.STANDARD_NEWS: "UPDATE_FIRST_PLAN",
    ContentType.NEWS_REWRITE: "UPDATE_FIRST_PLAN",
    ContentType.PUBLIC_SERVICE_NEWS: "SERVICE_ACTION_PLAN",
    ContentType.GOVERNMENT_SERVICE_CONTENT: "REQUIREMENTS_FIRST_PLAN",
    ContentType.EXPLAINER: "EXPLAINER_STRUCTURE_PLAN",
    ContentType.FACT_CHECK: "FACT_CHECK_STRUCTURE_PLAN",
    ContentType.HEALTH_CONTENT: "HIGH_RISK_ATTRIBUTION_PLAN",
    ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT: (
        "HIGH_RISK_ATTRIBUTION_PLAN"
    ),
    ContentType.SPORTS_NEWS: "RESULT_FIRST_PLAN",
    ContentType.TECHNOLOGY_NEWS: "UPDATE_FIRST_PLAN",
    ContentType.ECONOMY_NEWS: "IMPACT_FOCUSED_PLAN",
    ContentType.TRENDING_SOCIAL_CLAIM: "TREND_CLAIM_CAUTION_PLAN",
}
_SECTION_LIMITS = {
    ArticleLength.VERY_SHORT: 4,
    ArticleLength.SHORT: 6,
    ArticleLength.MEDIUM: 8,
    ArticleLength.LONG: 10,
}
_OPTIONAL_REMOVAL_ORDER = (
    ArticleSectionId.QUOTES,
    ArticleSectionId.BACKGROUND,
    ArticleSectionId.IMPACT,
    ArticleSectionId.KEY_DETAILS,
    ArticleSectionId.OFFICIAL_INFORMATION,
    ArticleSectionId.EXPLANATION,
    ArticleSectionId.READER_ACTION,
    ArticleSectionId.FEES,
    ArticleSectionId.DEADLINES,
    ArticleSectionId.VERDICT,
    ArticleSectionId.EVIDENCE,
    ArticleSectionId.CORE_UPDATE,
    ArticleSectionId.CLAIM,
)


class DeterministicArticlePlanner:
    """Create one structured article plan using deterministic rules."""

    def plan(
        self,
        *,
        source: NormalizedSource,
        assessment: SourceRiskAssessment,
        facts: ExtractedFacts,
        content_classification: ContentTypeClassification,
        reader_intent: ReaderIntentClassification,
        strategy: EditorialStrategy,
        user_instruction: str | None = None,
    ) -> ArticlePlan:
        """Build an internal article plan from editorial workflow outputs.

        Args:
            source: Normalized source material.
            assessment: Risk assessment for the source.
            facts: Facts extracted from the source.
            content_classification: Editorial content type classification.
            reader_intent: Primary reader intent classification.
            strategy: Deterministic editorial strategy.
            user_instruction: Optional editorial instruction.

        Returns:
            One deterministic article plan.
        """
        del user_instruction
        content_type = content_classification.content_type
        intent = reader_intent.reader_intent
        required_facts = self._required_facts(facts)
        required_attributions = self._required_attributions(
            source, facts, strategy
        )
        required_warnings = self._unique(
            (
                *assessment.warnings,
                *content_classification.warnings,
                *reader_intent.warnings,
                *strategy.warnings,
            )
        )
        missing_information = self._unique_nonempty(
            facts.unknown_information
        )
        prohibited_claims = self._prohibited_claims(content_type)
        warnings: list[str] = list(required_warnings)

        lead_instruction = _LEAD_INSTRUCTIONS[intent]
        if strategy.use_attribution:
            lead_instruction += " Attribution is required."
        if strategy.include_missing_information:
            lead_instruction += " Preserve material uncertainty."

        section_ids = self._section_ids(
            content_type=content_type,
            intent=intent,
            strategy=strategy,
            facts=facts,
            required_attributions=required_attributions,
            missing_information=missing_information,
        )
        if content_type is ContentType.FACT_CHECK and not facts.claims:
            warnings.append("PLAN_FACT_CHECK_EVIDENCE_INSUFFICIENT")

        protected_ids = self._protected_ids(
            content_type,
            bool(missing_information and strategy.include_missing_information),
        )
        section_ids, removed = self._apply_section_limit(
            section_ids,
            _SECTION_LIMITS[strategy.article_length],
            protected_ids,
        )
        sections = tuple(
            self._section(
                section_id=section_id,
                facts=facts,
                required_facts=required_facts,
                required_attributions=required_attributions,
                missing_information=missing_information,
                strategy=strategy,
            )
            for section_id in section_ids
        )
        sections = self._allocate_words(sections, strategy.target_word_count)

        reason_codes: list[str] = list(strategy.reason_codes)
        reason_codes.append(_PRIMARY_PLAN_CODES[content_type])
        if strategy.article_length is ArticleLength.VERY_SHORT:
            reason_codes.append("LIMITED_SOURCE_PLAN")
        if ArticleSectionId.MISSING_INFORMATION in section_ids:
            reason_codes.append("MISSING_INFORMATION_SECTION_REQUIRED")
        if any(section.include_heading for section in sections):
            reason_codes.append("HEADINGS_ENABLED_BY_STRATEGY")
        else:
            reason_codes.append("HEADINGS_DISABLED_BY_STRATEGY")
        if removed:
            reason_codes.append("UNSUPPORTED_SECTION_REMOVED")
        reason_codes.append("WORD_BUDGET_APPLIED")

        if (
            strategy.article_length is ArticleLength.VERY_SHORT
            and len(required_facts) < 2
        ):
            warnings.append("PLAN_SOURCE_TOO_THIN")
        if strategy.use_attribution and not required_attributions:
            warnings.append("PLAN_ATTRIBUTION_REQUIRED")
        if assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            warnings.append("PLAN_HIGH_RISK_REVIEW_REQUIRED")
        if ArticleSectionId.MISSING_INFORMATION in section_ids:
            warnings.append("PLAN_MISSING_INFORMATION_REQUIRED")

        return ArticlePlan(
            working_title=source.title.strip() or "Untitled Source",
            lead_instruction=lead_instruction,
            sections=sections,
            closing_instruction=_CLOSING_INSTRUCTIONS[intent],
            required_facts=required_facts,
            required_attributions=required_attributions,
            required_warnings=required_warnings,
            prohibited_claims=prohibited_claims,
            missing_information=missing_information,
            target_word_count=strategy.target_word_count,
            reason_codes=self._unique(reason_codes),
            warnings=self._unique(warnings),
        )

    @staticmethod
    def _required_facts(facts: ExtractedFacts) -> tuple[str, ...]:
        """Build the ordered unique facts required by the article.

        Args:
            facts: Extracted fact collections.

        Returns:
            Non-empty required facts in specified stage order.
        """
        return DeterministicArticlePlanner._unique_nonempty(
            (
                *facts.core_facts,
                *facts.events,
                *facts.numbers,
                *facts.percentages,
                *facts.currencies,
                *facts.dates,
                *facts.times,
            )
        )

    @staticmethod
    def _required_attributions(
        source: NormalizedSource,
        facts: ExtractedFacts,
        strategy: EditorialStrategy,
    ) -> tuple[str, ...]:
        """Build ordered unique required attributions.

        Args:
            source: Source providing optional source-name attribution.
            facts: Extracted attribution values.
            strategy: Strategy controlling attribution use.

        Returns:
            Non-empty required attribution values.
        """
        values = list(facts.attributions)
        if strategy.use_attribution and source.source_name:
            values.append(source.source_name)
        return DeterministicArticlePlanner._unique_nonempty(values)

    @staticmethod
    def _prohibited_claims(content_type: ContentType) -> tuple[str, ...]:
        """Build prohibited claims for a content type.

        Args:
            content_type: Selected editorial content type.

        Returns:
            Ordered unique prohibited claim codes.
        """
        values = list(_BASE_PROHIBITED_CLAIMS)
        if content_type is ContentType.HEALTH_CONTENT:
            values.append("UNSUPPORTED_MEDICAL_GUIDANCE")
        elif content_type is ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT:
            values.extend(
                (
                    "UNSUPPORTED_LEGAL_INTERPRETATION",
                    "UNSUPPORTED_FINANCIAL_RECOMMENDATION",
                )
            )
        elif content_type is ContentType.SPORTS_NEWS:
            values.append("UNSUPPORTED_RESULT_DETAILS")
        elif content_type is ContentType.TRENDING_SOCIAL_CLAIM:
            values.append("UNVERIFIED_SOCIAL_CLAIM_AS_FACT")
        return DeterministicArticlePlanner._unique(values)

    @staticmethod
    def _section_ids(
        *,
        content_type: ContentType,
        intent: ReaderIntent,
        strategy: EditorialStrategy,
        facts: ExtractedFacts,
        required_attributions: tuple[str, ...],
        missing_information: tuple[str, ...],
    ) -> list[ArticleSectionId]:
        """Create ordered supported section identifiers for a content type.

        Args:
            content_type: Selected editorial content type.
            intent: Selected primary reader intent.
            strategy: Structural editorial strategy.
            facts: Extracted facts supporting conditional sections.
            required_attributions: Available required attributions.
            missing_information: Material unknown information.

        Returns:
            Ordered section identifiers without duplicates.
        """
        missing = bool(
            missing_information and strategy.include_missing_information
        )
        attribution = bool(required_attributions)
        values: list[ArticleSectionId]
        if content_type is ContentType.BREAKING_NEWS:
            values = [ArticleSectionId.LEAD, ArticleSectionId.CORE_UPDATE]
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.STANDARD_NEWS:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
            ]
            if attribution:
                values.append(ArticleSectionId.OFFICIAL_INFORMATION)
            if intent is ReaderIntent.UNDERSTAND_IMPACT:
                values.append(ArticleSectionId.IMPACT)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.NEWS_REWRITE:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
            ]
            if strategy.use_attribution:
                values.append(ArticleSectionId.OFFICIAL_INFORMATION)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.PUBLIC_SERVICE_NEWS:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
            ]
            if strategy.include_reader_action:
                values.append(ArticleSectionId.READER_ACTION)
            if facts.currencies or facts.numbers:
                values.append(ArticleSectionId.FEES)
            if facts.dates or facts.times:
                values.append(ArticleSectionId.DEADLINES)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.GOVERNMENT_SERVICE_CONTENT:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.REQUIREMENTS,
                ArticleSectionId.PROCEDURE,
            ]
            if facts.currencies or facts.numbers:
                values.append(ArticleSectionId.FEES)
            if facts.dates or facts.times:
                values.append(ArticleSectionId.DEADLINES)
            values.append(ArticleSectionId.OFFICIAL_INFORMATION)
            if strategy.include_reader_action:
                values.append(ArticleSectionId.READER_ACTION)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.EXPLAINER:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.EXPLANATION,
            ]
            if strategy.use_background:
                values.append(ArticleSectionId.BACKGROUND)
            if intent is ReaderIntent.UNDERSTAND_IMPACT:
                values.append(ArticleSectionId.IMPACT)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.FACT_CHECK:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CLAIM,
                ArticleSectionId.EVIDENCE,
                ArticleSectionId.VERDICT,
            ]
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.HEALTH_CONTENT:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.OFFICIAL_INFORMATION,
            ]
            if strategy.article_length is not ArticleLength.VERY_SHORT:
                values.append(ArticleSectionId.EXPLANATION)
            if strategy.include_reader_action:
                values.append(ArticleSectionId.READER_ACTION)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.OFFICIAL_INFORMATION,
                ArticleSectionId.IMPACT,
            ]
            if strategy.include_reader_action:
                values.append(ArticleSectionId.READER_ACTION)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.SPORTS_NEWS:
            values = [ArticleSectionId.LEAD, ArticleSectionId.RESULT]
            if strategy.article_length is not ArticleLength.VERY_SHORT:
                values.append(ArticleSectionId.KEY_DETAILS)
            if strategy.use_quotes:
                values.append(ArticleSectionId.QUOTES)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.TECHNOLOGY_NEWS:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
            ]
            if intent is ReaderIntent.UNDERSTAND_IMPACT:
                values.append(ArticleSectionId.IMPACT)
            if attribution:
                values.append(ArticleSectionId.OFFICIAL_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        elif content_type is ContentType.ECONOMY_NEWS:
            values = [
                ArticleSectionId.LEAD,
                ArticleSectionId.CORE_UPDATE,
                ArticleSectionId.KEY_DETAILS,
                ArticleSectionId.IMPACT,
            ]
            if attribution:
                values.append(ArticleSectionId.OFFICIAL_INFORMATION)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        else:
            values = [ArticleSectionId.LEAD, ArticleSectionId.CLAIM]
            if attribution:
                values.append(ArticleSectionId.OFFICIAL_INFORMATION)
            if facts.claims or facts.quotes:
                values.append(ArticleSectionId.EVIDENCE)
            if missing:
                values.append(ArticleSectionId.MISSING_INFORMATION)
            values.append(ArticleSectionId.CLOSING)
        return list(dict.fromkeys(values))

    @staticmethod
    def _protected_ids(
        content_type: ContentType,
        missing_created: bool,
    ) -> set[ArticleSectionId]:
        """Return section identifiers protected from limit removal.

        Args:
            content_type: Selected editorial content type.
            missing_created: Whether a required missing-information section exists.

        Returns:
            Protected section identifiers.
        """
        protected = {ArticleSectionId.LEAD, ArticleSectionId.CLOSING}
        if content_type is ContentType.SPORTS_NEWS:
            protected.add(ArticleSectionId.RESULT)
        elif content_type is ContentType.FACT_CHECK:
            protected.update((ArticleSectionId.CLAIM, ArticleSectionId.EVIDENCE))
        elif content_type is ContentType.GOVERNMENT_SERVICE_CONTENT:
            protected.update(
                (ArticleSectionId.REQUIREMENTS, ArticleSectionId.PROCEDURE)
            )
        if missing_created:
            protected.add(ArticleSectionId.MISSING_INFORMATION)
        return protected

    @staticmethod
    def _apply_section_limit(
        section_ids: list[ArticleSectionId],
        limit: int,
        protected_ids: set[ArticleSectionId],
    ) -> tuple[list[ArticleSectionId], bool]:
        """Remove optional sections in deterministic priority order.

        Args:
            section_ids: Ordered section identifiers.
            limit: Maximum desired section count.
            protected_ids: Identifiers that must not be removed.

        Returns:
            Limited identifiers and whether any section was removed.
        """
        result = list(section_ids)
        removed = False
        for section_id in _OPTIONAL_REMOVAL_ORDER:
            if len(result) <= limit:
                break
            if section_id in result and section_id not in protected_ids:
                result.remove(section_id)
                removed = True
        return result, removed

    @staticmethod
    def _section(
        *,
        section_id: ArticleSectionId,
        facts: ExtractedFacts,
        required_facts: tuple[str, ...],
        required_attributions: tuple[str, ...],
        missing_information: tuple[str, ...],
        strategy: EditorialStrategy,
    ) -> ArticleSectionPlan:
        """Build one section plan with supported facts and heading rules.

        Args:
            section_id: Selected section identifier.
            facts: Extracted fact collections.
            required_facts: Plan-level required facts.
            required_attributions: Plan-level required attributions.
            missing_information: Material unknown information.
            strategy: Editorial strategy controlling headings.

        Returns:
            One immutable article section plan.
        """
        section_facts = DeterministicArticlePlanner._section_facts(
            section_id,
            facts,
            required_facts,
            required_attributions,
            missing_information,
        )
        attribution_sections = {
            ArticleSectionId.OFFICIAL_INFORMATION,
            ArticleSectionId.CLAIM,
            ArticleSectionId.EVIDENCE,
            ArticleSectionId.QUOTES,
        }
        section_attributions = (
            required_attributions
            if section_id in attribution_sections
            or section_id is ArticleSectionId.LEAD
            and strategy.use_attribution
            else ()
        )
        include_heading = (
            strategy.use_headings
            and section_id not in (ArticleSectionId.LEAD, ArticleSectionId.CLOSING)
            and strategy.article_length
            in (ArticleLength.MEDIUM, ArticleLength.LONG)
        )
        return ArticleSectionPlan(
            section_id=section_id,
            purpose=_PURPOSES[section_id],
            required_facts=section_facts,
            optional_facts=(),
            required_attributions=section_attributions,
            include_heading=include_heading,
            heading_guidance=(
                _HEADING_GUIDANCE[section_id] if include_heading else None
            ),
            max_words=0,
        )

    @staticmethod
    def _section_facts(
        section_id: ArticleSectionId,
        facts: ExtractedFacts,
        required_facts: tuple[str, ...],
        required_attributions: tuple[str, ...],
        missing_information: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Select relevant facts for one section identifier.

        Args:
            section_id: Section requiring relevant facts.
            facts: Extracted fact collections.
            required_facts: Ordered plan-level required facts.
            required_attributions: Ordered plan-level attributions.
            missing_information: Material unknown information.

        Returns:
            Ordered unique non-empty section facts.
        """
        mapping: dict[ArticleSectionId, Iterable[str]] = {
            ArticleSectionId.LEAD: required_facts[:1],
            ArticleSectionId.CORE_UPDATE: required_facts[:2],
            ArticleSectionId.RESULT: (*facts.events, *facts.numbers[:1]),
            ArticleSectionId.KEY_DETAILS: required_facts[2:],
            ArticleSectionId.OFFICIAL_INFORMATION: (
                *facts.core_facts,
                *required_attributions,
            ),
            ArticleSectionId.CLAIM: facts.claims,
            ArticleSectionId.EVIDENCE: (
                *facts.quotes,
                *facts.dates,
                *facts.numbers,
                *facts.currencies,
            ),
            ArticleSectionId.VERDICT: facts.claims,
            ArticleSectionId.REQUIREMENTS: (
                *facts.core_facts,
                *facts.dates,
                *facts.currencies,
            ),
            ArticleSectionId.PROCEDURE: facts.core_facts,
            ArticleSectionId.FEES: (*facts.currencies, *facts.numbers),
            ArticleSectionId.DEADLINES: (*facts.dates, *facts.times),
            ArticleSectionId.READER_ACTION: facts.core_facts,
            ArticleSectionId.IMPACT: (
                *facts.core_facts,
                *facts.numbers,
                *facts.currencies,
            ),
            ArticleSectionId.EXPLANATION: facts.core_facts,
            ArticleSectionId.BACKGROUND: facts.core_facts,
            ArticleSectionId.TIMELINE: (*facts.dates, *facts.times),
            ArticleSectionId.COMPARISON: (*facts.numbers, *facts.currencies),
            ArticleSectionId.QUOTES: facts.quotes,
            ArticleSectionId.MISSING_INFORMATION: missing_information,
            ArticleSectionId.CLOSING: required_facts[-1:],
        }
        return DeterministicArticlePlanner._unique_nonempty(mapping[section_id])

    @staticmethod
    def _allocate_words(
        sections: tuple[ArticleSectionPlan, ...],
        target_word_count: int,
    ) -> tuple[ArticleSectionPlan, ...]:
        """Allocate the target word budget across final sections.

        Args:
            sections: Final ordered section plans.
            target_word_count: Total target word budget.

        Returns:
            Section plans with deterministic maximum word allocations.
        """
        if not sections:
            return ()
        allocations = [20 for _ in sections]
        lead_index = next(
            (
                index
                for index, section in enumerate(sections)
                if section.section_id is ArticleSectionId.LEAD
            ),
            None,
        )
        closing_index = next(
            (
                index
                for index, section in enumerate(sections)
                if section.section_id is ArticleSectionId.CLOSING
            ),
            None,
        )
        missing_index = next(
            (
                index
                for index, section in enumerate(sections)
                if section.section_id is ArticleSectionId.MISSING_INFORMATION
            ),
            None,
        )
        if lead_index is not None:
            allocations[lead_index] = max(25, round(target_word_count * 0.15))
        if closing_index is not None:
            allocations[closing_index] = max(
                20, round(target_word_count * 0.10)
            )
        if missing_index is not None:
            allocations[missing_index] = max(
                20, min(round(target_word_count * 0.10), target_word_count)
            )

        remaining = target_word_count - sum(allocations)
        flexible = [
            index
            for index in range(len(sections))
            if index not in (lead_index, closing_index, missing_index)
        ]
        if remaining > 0:
            recipients = flexible or list(range(len(sections)))
            quotient, remainder = divmod(remaining, len(recipients))
            for position, index in enumerate(recipients):
                allocations[index] += quotient + (position < remainder)
        elif remaining < 0:
            for index in reversed(flexible):
                reduction = min(allocations[index] - 20, -remaining)
                allocations[index] -= reduction
                remaining += reduction
                if remaining == 0:
                    break
        return tuple(
            replace(section, max_words=allocation)
            for section, allocation in zip(sections, allocations, strict=True)
        )

    @staticmethod
    def _unique_nonempty(values: Iterable[str]) -> tuple[str, ...]:
        """Return ordered unique non-empty strings.

        Args:
            values: Ordered string values.

        Returns:
            Trim-tested original values preserving first occurrence.
        """
        return tuple(dict.fromkeys(value for value in values if value.strip()))

    @staticmethod
    def _unique(values: Iterable[str]) -> tuple[str, ...]:
        """Return values without duplicates while preserving order.

        Args:
            values: Ordered string values.

        Returns:
            Values preserving only their first occurrence.
        """
        return tuple(dict.fromkeys(values))
