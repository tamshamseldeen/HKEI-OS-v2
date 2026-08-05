"""Immutable article plan model."""

from dataclasses import dataclass

from .article_section_plan import ArticleSectionPlan


@dataclass(frozen=True)
class ArticlePlan:
    """Represent the structured internal plan for a future article.

    Attributes:
        working_title: Concise internal descriptive title.
        lead_instruction: Internal guidance for the opening paragraph.
        sections: Ordered internal article section plans.
        closing_instruction: Internal guidance for ending the article.
        required_facts: Facts that the article must include.
        required_attributions: Attributions required in the article.
        required_warnings: Workflow warnings relevant to the article.
        prohibited_claims: Unsupported statements the draft must not add.
        missing_information: Material unknowns affecting understanding.
        target_word_count: Editorial target word count.
        reason_codes: Stable codes explaining the plan.
        warnings: Warnings associated with the plan.
    """

    working_title: str
    lead_instruction: str
    sections: tuple[ArticleSectionPlan, ...]
    closing_instruction: str
    required_facts: tuple[str, ...]
    required_attributions: tuple[str, ...]
    required_warnings: tuple[str, ...]
    prohibited_claims: tuple[str, ...]
    missing_information: tuple[str, ...]
    target_word_count: int
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
