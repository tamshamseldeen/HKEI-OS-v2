"""Public service for deterministic fact extraction."""

from src.intake.normalized_source import NormalizedSource

from .deterministic_fact_extractor import DeterministicFactExtractor
from .extracted_facts import ExtractedFacts


class FactExtractionService:
    """Provide the public entry point for fact extraction."""

    def __init__(
        self,
        extractor: DeterministicFactExtractor | None = None,
    ) -> None:
        """Initialize the fact extraction service.

        Args:
            extractor: Extractor to use, or None to create the default.
        """
        self.extractor = (
            extractor
            if extractor is not None
            else DeterministicFactExtractor()
        )

    def process(self, source: NormalizedSource) -> ExtractedFacts:
        """Extract facts from one normalized source.

        Args:
            source: Normalized source material to process.

        Returns:
            The extracted facts returned by the configured extractor.
        """
        return self.extractor.extract(source)
