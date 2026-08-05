"""Tests for the fact extraction service."""

from unittest.mock import call, create_autospec

from src.facts.deterministic_fact_extractor import DeterministicFactExtractor
from src.facts.extracted_facts import ExtractedFacts
from src.facts.fact_extraction_service import FactExtractionService
from src.intake.normalized_source import NormalizedSource


def make_extracted_facts() -> ExtractedFacts:
    """Create an empty extracted facts result for delegation tests.

    Returns:
        An extracted facts instance with empty collections.
    """
    return ExtractedFacts(
        core_facts=(),
        claims=(),
        quotes=(),
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=(),
        times=(),
        numbers=(),
        percentages=(),
        currencies=(),
        laws_and_regulations=(),
        products=(),
        events=(),
        unknown_information=(),
        attributions=(),
    )


def test_default_extractor_is_created() -> None:
    """Create and store a deterministic extractor by default."""
    service = FactExtractionService()

    assert isinstance(service.extractor, DeterministicFactExtractor)


def test_injected_extractor_is_stored() -> None:
    """Store the exact extractor supplied to the constructor."""
    extractor = create_autospec(DeterministicFactExtractor, instance=True)

    service = FactExtractionService(extractor)

    assert service.extractor is extractor


def test_process_delegates_once_and_returns_result_unchanged() -> None:
    """Delegate exactly once with the source and preserve result identity."""
    source = NormalizedSource("Title", "Body", "Source")
    expected = make_extracted_facts()
    extractor = create_autospec(DeterministicFactExtractor, instance=True)
    extractor.extract.return_value = expected
    service = FactExtractionService(extractor)

    actual = service.process(source)

    extractor.extract.assert_called_once_with(source)
    assert extractor.extract.call_args.args[0] is source
    assert actual is expected
    assert extractor.mock_calls == [call.extract(source)]
