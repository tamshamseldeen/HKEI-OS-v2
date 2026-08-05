"""Deterministic extraction of facts from normalized source material."""

import re
from collections.abc import Iterable
from re import Match

from src.intake.normalized_source import NormalizedSource

from .extracted_facts import ExtractedFacts


_DIGIT = "0-9\u0660-\u0669"
_NUMBER = rf"[{_DIGIT}]+(?:,[{_DIGIT}]{{3}})*(?:\.[{_DIGIT}]+)?"
_DATE_PATTERN = re.compile(
    rf"(?<![{_DIGIT}])(?:"
    rf"[{_DIGIT}]{{2}}/[{_DIGIT}]{{2}}/[{_DIGIT}]{{4}}|"
    rf"[{_DIGIT}]{{2}}-[{_DIGIT}]{{2}}-[{_DIGIT}]{{4}}|"
    rf"[{_DIGIT}]{{4}}-[{_DIGIT}]{{2}}-[{_DIGIT}]{{2}}"
    rf")(?![{_DIGIT}])"
)
_TIME_PATTERN = re.compile(
    rf"(?<![{_DIGIT}])[{_DIGIT}]{{2}}:[{_DIGIT}]{{2}}"
    rf"(?: (?:AM|PM|صباحًا|مساءً))?(?![{_DIGIT}])"
)
_PERCENTAGE_PATTERN = re.compile(
    rf"(?<![{_DIGIT}]){_NUMBER}[٪%](?![{_DIGIT}])"
)
_CURRENCY_PATTERN = re.compile(
    rf"(?:"
    rf"[$€]\s*{_NUMBER}|"
    rf"(?<![{_DIGIT}]){_NUMBER}\s*(?:"
    rf"ريال سعودي|جنيه مصري|دولار أمريكي|ريال|جنيه|دولار|يورو|"
    rf"AED|SAR|USD|EGP|EUR|د\.إ|[$€]"
    rf")(?!\w)"
    rf")"
)
_NUMBER_PATTERN = re.compile(
    rf"(?<![{_DIGIT}]){_NUMBER}(?![{_DIGIT}])"
)
_QUOTE_PATTERN = re.compile(
    r'"([^"\n]*)"|\'([^\'\n]*)\'|«([^»\n]*)»|“([^”\n]*)”'
)


class DeterministicFactExtractor:
    """Extract explicitly supported facts using deterministic patterns."""

    def extract(self, source: NormalizedSource) -> ExtractedFacts:
        """Extract facts from one normalized source.

        Args:
            source: Normalized source material to inspect.

        Returns:
            Facts found through deterministic extraction rules.
        """
        text = f"{source.title}\n{source.body}"
        date_matches = tuple(_DATE_PATTERN.finditer(text))
        time_matches = tuple(_TIME_PATTERN.finditer(text))
        percentage_matches = tuple(_PERCENTAGE_PATTERN.finditer(text))
        currency_matches = tuple(_CURRENCY_PATTERN.finditer(text))
        excluded_spans = tuple(
            match.span()
            for matches in (
                date_matches,
                time_matches,
                percentage_matches,
                currency_matches,
            )
            for match in matches
        )

        return ExtractedFacts(
            core_facts=(source.title, source.body),
            claims=(),
            quotes=self._extract_quotes(text),
            named_people=(),
            organizations=(),
            government_entities=(),
            locations=(),
            countries=(source.country,) if source.country is not None else (),
            dates=self._matched_text(date_matches),
            times=self._matched_text(time_matches),
            numbers=self._extract_numbers(text, excluded_spans),
            percentages=self._matched_text(percentage_matches),
            currencies=self._matched_text(currency_matches),
            laws_and_regulations=(),
            products=(),
            events=(source.title,),
            unknown_information=(),
            attributions=(source.source_name,) if source.source_name else (),
        )

    @staticmethod
    def _matched_text(matches: Iterable[Match[str]]) -> tuple[str, ...]:
        """Return the complete text of regex matches.

        Args:
            matches: Regex matches in discovery order.

        Returns:
            Complete matched values in the same order.
        """
        return tuple(match.group(0) for match in matches)

    @staticmethod
    def _extract_quotes(text: str) -> tuple[str, ...]:
        """Extract non-empty content inside supported quote pairs.

        Args:
            text: Combined title and body text.

        Returns:
            Trimmed quote contents in discovery order.
        """
        quotes = (
            next(group for group in match.groups() if group is not None).strip()
            for match in _QUOTE_PATTERN.finditer(text)
        )
        return tuple(quote for quote in quotes if quote)

    @staticmethod
    def _extract_numbers(
        text: str,
        excluded_spans: tuple[tuple[int, int], ...],
    ) -> tuple[str, ...]:
        """Extract numbers that do not overlap classified values.

        Args:
            text: Combined title and body text.
            excluded_spans: Character spans belonging to other fact types.

        Returns:
            Unclassified numeric tokens in discovery order.
        """
        return tuple(
            match.group(0)
            for match in _NUMBER_PATTERN.finditer(text)
            if not DeterministicFactExtractor._overlaps(
                match.span(), excluded_spans
            )
        )

    @staticmethod
    def _overlaps(
        span: tuple[int, int],
        excluded_spans: tuple[tuple[int, int], ...],
    ) -> bool:
        """Check whether a span intersects any excluded span.

        Args:
            span: Candidate start and end offsets.
            excluded_spans: Start and end offsets to exclude.

        Returns:
            True when the candidate intersects an excluded span.
        """
        start, end = span
        return any(
            start < excluded_end and excluded_start < end
            for excluded_start, excluded_end in excluded_spans
        )
