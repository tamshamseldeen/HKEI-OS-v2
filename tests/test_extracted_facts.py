"""Tests for the extracted facts model."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.facts.extracted_facts import ExtractedFacts


FIELD_NAMES = (
    "core_facts",
    "claims",
    "quotes",
    "named_people",
    "organizations",
    "government_entities",
    "locations",
    "countries",
    "dates",
    "times",
    "numbers",
    "percentages",
    "currencies",
    "laws_and_regulations",
    "products",
    "events",
    "unknown_information",
    "attributions",
)


def make_extracted_facts() -> ExtractedFacts:
    """Create a populated extracted facts model for testing.

    Returns:
        Extracted facts containing representative values.
    """
    return ExtractedFacts(
        core_facts=("The authority issued a notice.",),
        claims=("The company said the product is safe.",),
        quotes=("Testing is complete.",),
        named_people=("Alex Lee, director",),
        organizations=("Example Company",),
        government_entities=("Health Authority",),
        locations=("Central District",),
        countries=("Hong Kong",),
        dates=("5 August 2026",),
        times=("10:30 a.m.",),
        numbers=("250 units",),
        percentages=("12.5%",),
        currencies=("HK$1,000",),
        laws_and_regulations=("Example Regulation",),
        products=("Example Device",),
        events=("Product recall",),
        unknown_information=("The affected batch was not identified.",),
        attributions=("Health Authority spokesperson",),
    )


def test_all_fields_are_stored_correctly() -> None:
    """Store every supplied field value unchanged."""
    extracted_facts = make_extracted_facts()

    assert tuple(getattr(extracted_facts, name) for name in FIELD_NAMES) == (
        ("The authority issued a notice.",),
        ("The company said the product is safe.",),
        ("Testing is complete.",),
        ("Alex Lee, director",),
        ("Example Company",),
        ("Health Authority",),
        ("Central District",),
        ("Hong Kong",),
        ("5 August 2026",),
        ("10:30 a.m.",),
        ("250 units",),
        ("12.5%",),
        ("HK$1,000",),
        ("Example Regulation",),
        ("Example Device",),
        ("Product recall",),
        ("The affected batch was not identified.",),
        ("Health Authority spokesperson",),
    )


def test_extracted_facts_is_immutable() -> None:
    """Prevent extracted fact fields from being reassigned."""
    extracted_facts = make_extracted_facts()

    with pytest.raises(FrozenInstanceError):
        extracted_facts.core_facts = ()  # type: ignore[misc]


def test_every_collection_remains_a_tuple() -> None:
    """Preserve the tuple type of every collection."""
    extracted_facts = make_extracted_facts()

    assert all(
        isinstance(getattr(extracted_facts, name), tuple) for name in FIELD_NAMES
    )


def test_empty_tuples_are_accepted() -> None:
    """Accept empty tuples for every field."""
    extracted_facts = ExtractedFacts(*(() for _ in FIELD_NAMES))

    assert all(getattr(extracted_facts, name) == () for name in FIELD_NAMES)


def test_duplicate_values_are_preserved() -> None:
    """Preserve duplicate values without deduplication."""
    duplicate_values = ("Repeated fact", "Repeated fact")
    extracted_facts = ExtractedFacts(
        duplicate_values, *(() for _ in FIELD_NAMES[1:])
    )

    assert extracted_facts.core_facts == duplicate_values


def test_field_order_matches_specification() -> None:
    """Declare fields in the order required by the specification."""
    assert tuple(field.name for field in fields(ExtractedFacts)) == FIELD_NAMES
