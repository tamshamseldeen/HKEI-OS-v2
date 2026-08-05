"""Immutable article section plan model."""

from dataclasses import dataclass

from .article_section_id import ArticleSectionId


@dataclass(frozen=True)
class ArticleSectionPlan:
    """Represent one section in an internal article plan.

    Attributes:
        section_id: Stable machine-readable section identifier.
        purpose: Editorial function of the section.
        required_facts: Facts that the section must include.
        optional_facts: Supported facts the section may include.
        required_attributions: Attributions required in the section.
        include_heading: Whether the section should have a heading.
        heading_guidance: Internal heading guidance, when applicable.
        max_words: Maximum word allocation for the section.
    """

    section_id: ArticleSectionId
    purpose: str
    required_facts: tuple[str, ...]
    optional_facts: tuple[str, ...]
    required_attributions: tuple[str, ...]
    include_heading: bool
    heading_guidance: str | None
    max_words: int
