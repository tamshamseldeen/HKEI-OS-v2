"""Immutable normalized generated article model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedArticle:
    """Represent the structural parsing result for a generated article.

    Attributes:
        headline: Extracted Markdown H1 headline text.
        body_markdown: Normalized Markdown content after the headline.
        full_markdown: Normalized complete Markdown article.
        headings: Extracted H2 heading texts.
        paragraphs: Extracted article paragraph blocks.
        bullet_items: Extracted unordered bullet item texts.
        table_count: Number of detected Markdown tables.
        faq_detected: Whether FAQ structure was detected.
        timeline_detected: Whether timeline structure was detected.
        word_count: Deterministic visible-text word count.
        warnings: Machine-readable parsing warnings.
        reason_codes: Stable codes describing parsing operations.
    """

    headline: str
    body_markdown: str
    full_markdown: str
    headings: tuple[str, ...]
    paragraphs: tuple[str, ...]
    bullet_items: tuple[str, ...]
    table_count: int
    faq_detected: bool
    timeline_detected: bool
    word_count: int
    warnings: tuple[str, ...]
    reason_codes: tuple[str, ...]
