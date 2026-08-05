"""Tests for article planning models."""

from dataclasses import FrozenInstanceError, fields, replace

import pytest

from src.planning.article_plan import ArticlePlan
from src.planning.article_section_id import ArticleSectionId
from src.planning.article_section_plan import ArticleSectionPlan


def make_section() -> ArticleSectionPlan:
    """Create a populated article section plan for testing.

    Returns:
        A section plan containing representative values.
    """
    return ArticleSectionPlan(
        section_id=ArticleSectionId.KEY_DETAILS,
        purpose="Present the essential supporting details.",
        required_facts=("Required fact",),
        optional_facts=("Optional fact",),
        required_attributions=("Official Agency",),
        include_heading=True,
        heading_guidance="Use a descriptive Arabic-oriented heading.",
        max_words=120,
    )


def make_plan() -> ArticlePlan:
    """Create a populated article plan for testing.

    Returns:
        An article plan containing representative values.
    """
    section = make_section()
    return ArticlePlan(
        working_title="Internal working title",
        lead_instruction="Open with the newest confirmed fact.",
        sections=(section,),
        closing_instruction="End with the final confirmed detail.",
        required_facts=("Required fact",),
        required_attributions=("Official Agency",),
        required_warnings=("PLAN_ATTRIBUTION_REQUIRED",),
        prohibited_claims=("Unsupported cause",),
        missing_information=("Publication date is unknown",),
        target_word_count=220,
        reason_codes=("UPDATE_FIRST_PLAN", "WORD_BUDGET_APPLIED"),
        warnings=("PLAN_MISSING_INFORMATION_REQUIRED",),
    )


def test_article_section_id_values() -> None:
    """Expose every section identifier with its exact specified value."""
    assert tuple(section_id.value for section_id in ArticleSectionId) == (
        "LEAD",
        "CORE_UPDATE",
        "RESULT",
        "KEY_DETAILS",
        "OFFICIAL_INFORMATION",
        "CLAIM",
        "EVIDENCE",
        "VERDICT",
        "REQUIREMENTS",
        "PROCEDURE",
        "FEES",
        "DEADLINES",
        "READER_ACTION",
        "IMPACT",
        "EXPLANATION",
        "BACKGROUND",
        "TIMELINE",
        "COMPARISON",
        "QUOTES",
        "MISSING_INFORMATION",
        "CLOSING",
    )


def test_article_section_plan_stores_all_fields() -> None:
    """Store every supplied section-plan field unchanged."""
    section = make_section()

    assert section.section_id is ArticleSectionId.KEY_DETAILS
    assert section.purpose == "Present the essential supporting details."
    assert section.required_facts == ("Required fact",)
    assert section.optional_facts == ("Optional fact",)
    assert section.required_attributions == ("Official Agency",)
    assert section.include_heading is True
    assert section.heading_guidance == (
        "Use a descriptive Arabic-oriented heading."
    )
    assert section.max_words == 120


def test_article_section_plan_is_immutable() -> None:
    """Prevent section-plan fields from reassignment."""
    section = make_section()

    with pytest.raises(FrozenInstanceError):
        section.max_words = 80  # type: ignore[misc]


def test_article_plan_stores_all_fields() -> None:
    """Store every supplied article-plan field unchanged."""
    plan = make_plan()

    assert plan.working_title == "Internal working title"
    assert plan.lead_instruction == "Open with the newest confirmed fact."
    assert plan.sections == (make_section(),)
    assert plan.closing_instruction == "End with the final confirmed detail."
    assert plan.required_facts == ("Required fact",)
    assert plan.required_attributions == ("Official Agency",)
    assert plan.required_warnings == ("PLAN_ATTRIBUTION_REQUIRED",)
    assert plan.prohibited_claims == ("Unsupported cause",)
    assert plan.missing_information == ("Publication date is unknown",)
    assert plan.target_word_count == 220
    assert plan.reason_codes == ("UPDATE_FIRST_PLAN", "WORD_BUDGET_APPLIED")
    assert plan.warnings == ("PLAN_MISSING_INFORMATION_REQUIRED",)


def test_article_plan_is_immutable() -> None:
    """Prevent article-plan fields from reassignment."""
    plan = make_plan()

    with pytest.raises(FrozenInstanceError):
        plan.working_title = "Changed"  # type: ignore[misc]


def test_tuple_fields_remain_tuples() -> None:
    """Preserve tuple types for all collection fields."""
    section = make_section()
    plan = make_plan()

    assert isinstance(section.required_facts, tuple)
    assert isinstance(section.optional_facts, tuple)
    assert isinstance(section.required_attributions, tuple)
    assert isinstance(plan.sections, tuple)
    assert isinstance(plan.required_facts, tuple)
    assert isinstance(plan.required_attributions, tuple)
    assert isinstance(plan.required_warnings, tuple)
    assert isinstance(plan.prohibited_claims, tuple)
    assert isinstance(plan.missing_information, tuple)
    assert isinstance(plan.reason_codes, tuple)
    assert isinstance(plan.warnings, tuple)


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for every collection field."""
    section = replace(
        make_section(),
        required_facts=(),
        optional_facts=(),
        required_attributions=(),
    )
    plan = replace(
        make_plan(),
        sections=(),
        required_facts=(),
        required_attributions=(),
        required_warnings=(),
        prohibited_claims=(),
        missing_information=(),
        reason_codes=(),
        warnings=(),
    )

    assert section.required_facts == ()
    assert section.optional_facts == ()
    assert section.required_attributions == ()
    assert plan.sections == ()
    assert plan.required_facts == ()
    assert plan.required_attributions == ()
    assert plan.required_warnings == ()
    assert plan.prohibited_claims == ()
    assert plan.missing_information == ()
    assert plan.reason_codes == ()
    assert plan.warnings == ()


def test_duplicate_values_are_preserved() -> None:
    """Preserve duplicate collection values without deduplication."""
    duplicates = ("Repeated", "Repeated")
    section = replace(
        make_section(),
        required_facts=duplicates,
        optional_facts=duplicates,
        required_attributions=duplicates,
    )
    plan = replace(
        make_plan(),
        sections=(section, section),
        required_facts=duplicates,
        required_attributions=duplicates,
        required_warnings=duplicates,
        prohibited_claims=duplicates,
        missing_information=duplicates,
        reason_codes=duplicates,
        warnings=duplicates,
    )

    assert section.required_facts == duplicates
    assert section.optional_facts == duplicates
    assert section.required_attributions == duplicates
    assert plan.sections == (section, section)
    assert plan.required_facts == duplicates
    assert plan.required_attributions == duplicates
    assert plan.required_warnings == duplicates
    assert plan.prohibited_claims == duplicates
    assert plan.missing_information == duplicates
    assert plan.reason_codes == duplicates
    assert plan.warnings == duplicates


def test_heading_guidance_accepts_none() -> None:
    """Accept None when a section has no heading guidance."""
    section = replace(make_section(), heading_guidance=None)

    assert section.heading_guidance is None


def test_boolean_and_integer_values_are_preserved() -> None:
    """Preserve section booleans and all integer values."""
    section = make_section()
    plan = make_plan()

    assert section.include_heading is True
    assert section.max_words == 120
    assert isinstance(section.max_words, int)
    assert plan.target_word_count == 220
    assert isinstance(plan.target_word_count, int)


def test_article_plan_field_order_matches_specification() -> None:
    """Declare article-plan fields in the required order."""
    assert tuple(field.name for field in fields(ArticlePlan)) == (
        "working_title",
        "lead_instruction",
        "sections",
        "closing_instruction",
        "required_facts",
        "required_attributions",
        "required_warnings",
        "prohibited_claims",
        "missing_information",
        "target_word_count",
        "reason_codes",
        "warnings",
    )


def test_article_section_plan_field_order_matches_specification() -> None:
    """Declare section-plan fields in the required order."""
    assert tuple(field.name for field in fields(ArticleSectionPlan)) == (
        "section_id",
        "purpose",
        "required_facts",
        "optional_facts",
        "required_attributions",
        "include_heading",
        "heading_guidance",
        "max_words",
    )
