"""Tests for generation prompt models."""

from dataclasses import FrozenInstanceError, fields, replace

import pytest

from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat


def make_prompt() -> GenerationPrompt:
    """Create a populated generation prompt for testing.

    Returns:
        A generation prompt containing representative values.
    """
    return GenerationPrompt(
        system_prompt="Follow the supplied editorial and safety policy.",
        user_prompt="Write one grounded article from the supplied material.",
        target_language="ar",
        target_word_count=450,
        required_output_format=OutputFormat.MARKDOWN_ARTICLE,
        prohibited_content=("UNSUPPORTED_FACT", "INTERNAL_PLANNING_LABEL"),
        required_warnings=("HIGH_RISK_REVIEW_REQUIRED",),
        reason_codes=(
            "PROMPT_EDITORIAL_POLICY_INCLUDED",
            "PROMPT_MARKDOWN_OUTPUT_REQUIRED",
        ),
    )


def test_output_format_value() -> None:
    """Expose the exact supported generation output format."""
    assert tuple(output_format.value for output_format in OutputFormat) == (
        "MARKDOWN_ARTICLE",
    )


def test_all_fields_are_stored_correctly() -> None:
    """Store every supplied generation prompt field unchanged."""
    prompt = make_prompt()

    assert prompt.system_prompt == (
        "Follow the supplied editorial and safety policy."
    )
    assert prompt.user_prompt == (
        "Write one grounded article from the supplied material."
    )
    assert prompt.target_language == "ar"
    assert prompt.target_word_count == 450
    assert prompt.required_output_format is OutputFormat.MARKDOWN_ARTICLE
    assert prompt.prohibited_content == (
        "UNSUPPORTED_FACT",
        "INTERNAL_PLANNING_LABEL",
    )
    assert prompt.required_warnings == ("HIGH_RISK_REVIEW_REQUIRED",)
    assert prompt.reason_codes == (
        "PROMPT_EDITORIAL_POLICY_INCLUDED",
        "PROMPT_MARKDOWN_OUTPUT_REQUIRED",
    )


def test_generation_prompt_is_immutable() -> None:
    """Prevent generation prompt fields from reassignment."""
    prompt = make_prompt()

    with pytest.raises(FrozenInstanceError):
        prompt.target_word_count = 220  # type: ignore[misc]


def test_tuple_fields_remain_tuples() -> None:
    """Preserve tuple types for every collection field."""
    prompt = make_prompt()

    assert isinstance(prompt.prohibited_content, tuple)
    assert isinstance(prompt.required_warnings, tuple)
    assert isinstance(prompt.reason_codes, tuple)


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for every collection field."""
    prompt = replace(
        make_prompt(),
        prohibited_content=(),
        required_warnings=(),
        reason_codes=(),
    )

    assert prompt.prohibited_content == ()
    assert prompt.required_warnings == ()
    assert prompt.reason_codes == ()


def test_duplicate_values_are_preserved() -> None:
    """Preserve duplicate tuple values without deduplication."""
    duplicates = ("REPEATED", "REPEATED")
    prompt = replace(
        make_prompt(),
        prohibited_content=duplicates,
        required_warnings=duplicates,
        reason_codes=duplicates,
    )

    assert prompt.prohibited_content == duplicates
    assert prompt.required_warnings == duplicates
    assert prompt.reason_codes == duplicates


def test_target_word_count_and_language_are_preserved() -> None:
    """Preserve the supplied integer target and language string."""
    prompt = make_prompt()

    assert prompt.target_word_count == 450
    assert isinstance(prompt.target_word_count, int)
    assert prompt.target_language == "ar"


def test_field_order_matches_specification() -> None:
    """Declare fields in the order required by the specification."""
    assert tuple(field.name for field in fields(GenerationPrompt)) == (
        "system_prompt",
        "user_prompt",
        "target_language",
        "target_word_count",
        "required_output_format",
        "prohibited_content",
        "required_warnings",
        "reason_codes",
    )
