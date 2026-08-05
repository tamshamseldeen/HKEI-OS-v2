"""Immutable fact-extraction output model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedFacts:
    """Represent facts extracted from a normalized source.

    Attributes:
        core_facts: Directly supported factual statements.
        claims: Attributed statements that are not independently verified.
        quotes: Wording explicitly attributed to a speaker or source.
        named_people: Explicitly identified individuals.
        organizations: Explicitly named organized bodies.
        government_entities: Explicitly named public bodies.
        locations: Places identified in the source.
        countries: Countries identified in the source.
        dates: Calendar or relative dates stated in the source.
        times: Times, deadlines, or time references stated in the source.
        numbers: Numeric values preserved with their context.
        percentages: Percentage values preserved exactly.
        currencies: Monetary amounts or currency references.
        laws_and_regulations: Named or cited legal instruments.
        products: Named commercial, medical, digital, or physical offerings.
        events: Occurrences or scheduled activities described in the source.
        unknown_information: Material details left unspecified by the source.
        attributions: Sources or speakers to which information is attributed.
    """

    core_facts: tuple[str, ...]
    claims: tuple[str, ...]
    quotes: tuple[str, ...]
    named_people: tuple[str, ...]
    organizations: tuple[str, ...]
    government_entities: tuple[str, ...]
    locations: tuple[str, ...]
    countries: tuple[str, ...]
    dates: tuple[str, ...]
    times: tuple[str, ...]
    numbers: tuple[str, ...]
    percentages: tuple[str, ...]
    currencies: tuple[str, ...]
    laws_and_regulations: tuple[str, ...]
    products: tuple[str, ...]
    events: tuple[str, ...]
    unknown_information: tuple[str, ...]
    attributions: tuple[str, ...]
