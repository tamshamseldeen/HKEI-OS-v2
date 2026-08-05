"""Tests for the deterministic fact extractor."""

from src.facts.deterministic_fact_extractor import DeterministicFactExtractor
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource


def extract(
    title: str = "Title",
    body: str = "Body",
    source_name: str = "News Agency",
    country: str | None = None,
) -> ExtractedFacts:
    """Extract facts from representative normalized source values.

    Args:
        title: Source title.
        body: Source body.
        source_name: Source attribution name.
        country: Optional source country.

    Returns:
        Deterministically extracted facts.
    """
    source = NormalizedSource(
        title=title,
        body=body,
        source_name=source_name,
        country=country,
    )
    return DeterministicFactExtractor().extract(source)


def test_core_facts_contain_title_and_body() -> None:
    """Return title and body as core facts in exact order."""
    assert extract("Headline", "Article").core_facts == ("Headline", "Article")


def test_country_is_preserved() -> None:
    """Return a supplied country without alteration."""
    assert extract(country="Saudi Arabia").countries == ("Saudi Arabia",)


def test_source_name_is_preserved_as_attribution() -> None:
    """Return a non-empty source name as attribution."""
    assert extract(source_name="Official Agency").attributions == (
        "Official Agency",
    )


def test_supported_quotes_are_extracted() -> None:
    """Extract Arabic, straight, single, and smart quote contents."""
    facts = extract(
        'قال «مرحبًا» ثم "hello"',
        "وأضاف 'confirmed' ثم “finished”",
    )

    assert facts.quotes == ("مرحبًا", "hello", "confirmed", "finished")


def test_empty_quotes_are_ignored() -> None:
    """Ignore empty and whitespace-only quoted values."""
    assert extract('"" «   »', "'' “ ”").quotes == ()


def test_dates_are_extracted() -> None:
    """Extract every supported deterministic date format."""
    facts = extract("05/08/2026 and 05-08-2026", "then 2026-08-05")

    assert facts.dates == ("05/08/2026", "05-08-2026", "2026-08-05")


def test_times_are_extracted() -> None:
    """Extract supported times while preserving matched text."""
    facts = extract(
        "09:30 and 10:45 AM and 11:15 PM",
        "08:00 صباحًا and 07:00 مساءً",
    )

    assert facts.times == (
        "09:30",
        "10:45 AM",
        "11:15 PM",
        "08:00 صباحًا",
        "07:00 مساءً",
    )


def test_supported_number_forms_are_extracted() -> None:
    """Extract Latin, Arabic-Indic, decimal, and grouped numbers."""
    facts = extract("123 then ١٢٣", "12.5 then 3,000")

    assert facts.numbers == ("123", "١٢٣", "12.5", "3,000")


def test_percentages_are_extracted() -> None:
    """Extract Latin and Arabic percentage forms."""
    facts = extract("25% and ٢٥٪", "12.5%")

    assert facts.percentages == ("25%", "٢٥٪", "12.5%")


def test_currencies_are_extracted() -> None:
    """Extract supported currency names, codes, and symbols."""
    facts = extract(
        "3,000 ريال and 6,000 ريال سعودي and 100 USD",
        "250 د.إ and $50 and 40€",
    )

    assert facts.currencies == (
        "3,000 ريال",
        "6,000 ريال سعودي",
        "100 USD",
        "250 د.إ",
        "$50",
        "40€",
    )


def test_classified_values_are_excluded_from_numbers() -> None:
    """Exclude dates, times, percentages, and currencies from numbers."""
    facts = extract(
        "05/08/2026 at 10:45 PM was 25%",
        "The cost was 3,000 ريال and the count was 7",
    )

    assert facts.numbers == ("7",)


def test_discovery_order_and_duplicates_are_preserved() -> None:
    """Preserve repeated values in title-before-body discovery order."""
    facts = extract("2 then 1 then 2", "1 then 2")

    assert facts.numbers == ("2", "1", "2", "1", "2")


def test_empty_optional_collections_are_returned_correctly() -> None:
    """Return empty tuples when optional deterministic facts are absent."""
    facts = extract(source_name="", country=None)

    assert facts.claims == ()
    assert facts.quotes == ()
    assert facts.named_people == ()
    assert facts.organizations == ()
    assert facts.government_entities == ()
    assert facts.locations == ()
    assert facts.countries == ()
    assert facts.dates == ()
    assert facts.times == ()
    assert facts.numbers == ()
    assert facts.percentages == ()
    assert facts.currencies == ()
    assert facts.laws_and_regulations == ()
    assert facts.products == ()
    assert facts.unknown_information == ()
    assert facts.attributions == ()


def test_event_contains_source_title() -> None:
    """Return the source title as the sole event."""
    assert extract(title="Public announcement").events == (
        "Public announcement",
    )
