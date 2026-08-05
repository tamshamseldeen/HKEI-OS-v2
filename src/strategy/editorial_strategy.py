"""Immutable editorial strategy model."""

from dataclasses import dataclass

from .article_depth import ArticleDepth
from .article_length import ArticleLength
from .writing_mode import WritingMode


@dataclass(frozen=True)
class EditorialStrategy:
    """Represent the strategy for building an editorial article.

    Attributes:
        article_length: Target editorial length.
        article_depth: Target editorial depth.
        writing_mode: Editorial writing treatment.
        use_headings: Whether the article should use headings.
        use_bullets: Whether the article should use bullet lists.
        use_table: Whether the article should use a table.
        use_faq: Whether the article should use an FAQ structure.
        use_timeline: Whether the article should use a timeline.
        use_background: Whether the article should include background.
        use_quotes: Whether the article should use direct quotes.
        use_attribution: Whether the article should preserve attribution.
        include_missing_information: Whether to state material omissions.
        include_reader_action: Whether to include a supported next action.
        target_word_count: Editorial target word count.
        reason_codes: Stable codes explaining the strategy.
        warnings: Warnings associated with the strategy.
    """

    article_length: ArticleLength
    article_depth: ArticleDepth
    writing_mode: WritingMode
    use_headings: bool
    use_bullets: bool
    use_table: bool
    use_faq: bool
    use_timeline: bool
    use_background: bool
    use_quotes: bool
    use_attribution: bool
    include_missing_information: bool
    include_reader_action: bool
    target_word_count: int
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
