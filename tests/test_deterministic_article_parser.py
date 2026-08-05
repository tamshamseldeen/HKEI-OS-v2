"""Tests for deterministic generated-article Markdown parsing."""

from dataclasses import replace
from typing import cast
from unittest.mock import MagicMock

import pytest

from src.generation.finish_reason import FinishReason
from src.generation.generation_result import GenerationResult
from src.parsing.deterministic_article_parser import DeterministicArticleParser
from src.parsing.parsed_article import ParsedArticle
from src.parsing.parsing_error import ParsingError
from src.prompting.generation_prompt import GenerationPrompt
from src.prompting.output_format import OutputFormat
from src.workflows.editorial_planning_result import EditorialPlanningResult


REASON_CODES = (
    "ARTICLE_MARKDOWN_PARSED",
    "ARTICLE_HEADLINE_EXTRACTED",
    "ARTICLE_BODY_EXTRACTED",
    "ARTICLE_STRUCTURE_DETECTED",
    "ARTICLE_WORD_COUNT_CALCULATED",
    "ARTICLE_STRATEGY_STRUCTURE_CHECKED",
    "ARTICLE_LENGTH_CHECKED",
    "ARTICLE_INTERNAL_LABEL_CHECKED",
    "ARTICLE_DISALLOWED_OUTPUT_CHECKED",
)


def make_generation_result(content: str) -> GenerationResult:
    """Create a generation result containing supplied Markdown."""
    return GenerationResult(
        content,
        "provider-id",
        "model-id",
        10,
        10,
        20,
        FinishReason.COMPLETED,
        "request-id",
        (),
    )


def make_prompt(target_word_count: int = 20) -> GenerationPrompt:
    """Create a generation prompt with a supplied target length."""
    return GenerationPrompt(
        "system",
        "user",
        "ar",
        target_word_count,
        OutputFormat.MARKDOWN_ARTICLE,
        (),
        (),
        (),
    )


def make_planning_result(
    *,
    use_headings: bool = True,
    use_bullets: bool = True,
    use_table: bool = True,
    use_faq: bool = True,
    use_timeline: bool = True,
) -> EditorialPlanningResult:
    """Create a planning result exposing structural strategy flags."""
    result = MagicMock()
    strategy = result.strategy_result.strategy
    strategy.use_headings = use_headings
    strategy.use_bullets = use_bullets
    strategy.use_table = use_table
    strategy.use_faq = use_faq
    strategy.use_timeline = use_timeline
    return cast(EditorialPlanningResult, result)


def parse(
    content: str,
    *,
    target_word_count: int = 20,
    planning_result: EditorialPlanningResult | None = None,
) -> ParsedArticle:
    """Parse Markdown with representative valid dependencies."""
    return DeterministicArticleParser().parse(
        generation_result=make_generation_result(content),
        generation_prompt=make_prompt(target_word_count),
        planning_result=planning_result or make_planning_result(),
    )


@pytest.mark.parametrize("content", ("", " \t\r\n "))
def test_empty_content_raises_exact_error(content: str) -> None:
    """Reject empty and whitespace-only generated content."""
    with pytest.raises(ParsingError) as raised:
        parse(content)

    assert raised.value.code == "GENERATED_CONTENT_EMPTY"


@pytest.mark.parametrize(
    ("content", "code"),
    (
        ("Plain headline\n\nBody", "ARTICLE_HEADLINE_MISSING"),
        ("Intro\n# Headline\n\nBody", "ARTICLE_HEADLINE_MISSING"),
        ("# First\n\nBody\n\n# Second", "ARTICLE_HEADLINE_MULTIPLE"),
        ("# \n\nBody", "ARTICLE_HEADLINE_MISSING"),
        ("# Headline", "ARTICLE_BODY_MISSING"),
        ("# Headline\n\n \n", "ARTICLE_BODY_MISSING"),
    ),
)
def test_required_article_structure_errors(content: str, code: str) -> None:
    """Reject missing, multiple, misplaced, or empty required blocks."""
    with pytest.raises(ParsingError) as raised:
        parse(content)

    assert raised.value.code == code


def test_normalization_and_core_extraction_are_deterministic() -> None:
    """Normalize line endings, whitespace, blanks, headline, and body."""
    article = parse(
        "\r\n#  Headline text  \r\n\r\n\r\n\r\n"
        "First line.   \rSecond line.\t\r\n\r\n",
        target_word_count=6,
    )

    assert article.headline == "Headline text"
    assert article.body_markdown == "First line.\nSecond line."
    assert article.full_markdown == (
        "# Headline text\n\nFirst line.\nSecond line."
    )
    assert "\r" not in article.full_markdown
    assert not any(
        line.endswith((" ", "\t"))
        for line in article.full_markdown.split("\n")
    )


def test_headings_preserve_order_duplicates_and_ignore_h3() -> None:
    """Extract only non-empty H2 headings in discovery order."""
    article = parse(
        "# Headline\n\n## First\n\nText.\n\n### Ignored\n\n"
        "## First\n\nMore text.",
    )

    assert article.headings == ("First", "First")
    assert "### Ignored" in article.paragraphs
    assert all(not paragraph.startswith("## ") for paragraph in article.paragraphs)


def test_paragraphs_exclude_structural_blocks() -> None:
    """Extract prose blocks while excluding headings, lists, and tables."""
    article = parse(
        "# Headline\n\nParagraph one.\ncontinued.\n\n## Details\n\n"
        "- bullet\n- second\n\n1. numbered\n2. second\n\n"
        "| A | B |\n| --- | --- |\n| one | two |\n\nParagraph two.",
        target_word_count=15,
    )

    assert article.paragraphs == (
        "Paragraph one.\ncontinued.",
        "Paragraph two.",
    )


def test_bullets_preserve_marker_order_duplicates_and_ignore_empty() -> None:
    """Extract supported unordered bullet text without numbered items."""
    article = parse(
        "# Headline\n\n- First\n* Same\n+ Same\n-   \n1. Numbered\n\nText.",
        target_word_count=8,
    )

    assert article.bullet_items == ("First", "Same", "Same")


def test_tables_are_counted_once_and_pipe_prose_is_ignored() -> None:
    """Count header-separator pairs and ignore other pipe-containing text."""
    article = parse(
        "# Headline\n\nPipe | prose is not a table.\n\n"
        "| A | B |\n| :--- | ---: |\n| 1 | 2 |\n\n"
        "X | Y\n--- | ---\na | b",
        target_word_count=12,
    )

    assert article.table_count == 2


@pytest.mark.parametrize(
    ("body", "faq", "timeline"),
    (
        ("## الأسئلة الشائعة\n\nText.", True, False),
        ("What?\nهل هذا صحيح\nكيف يحدث ذلك", True, False),
        ("What?\nAnother line.", False, False),
        ("## Timeline\n\nText.", False, True),
        (
            "01/01/2026 event\n02-01-2026 event\n2026-01-03 event",
            False,
            True,
        ),
        ("01/01/2026 event\n02-01-2026 event", False, False),
    ),
)
def test_faq_and_timeline_detection(
    body: str,
    faq: bool,
    timeline: bool,
) -> None:
    """Detect semantic headings and three qualifying lines only."""
    article = parse(f"# Headline\n\n{body}", target_word_count=10)

    assert article.faq_detected is faq
    assert article.timeline_detected is timeline


@pytest.mark.parametrize(
    "content",
    (
        "# LEAD\n\nText.",
        "# Headline\n\n## internal article plan\n\nText.",
        "# Headline\n\nText.\n\nSTRUCTURED FACTS",
        "# Headline\n\nLEAD\n\nLEAD",
    ),
)
def test_internal_labels_add_one_warning(content: str) -> None:
    """Detect forbidden labels case-insensitively and warn only once."""
    article = parse(content, target_word_count=4)

    assert article.warnings.count("INTERNAL_LABEL_EXPOSED") == 1


@pytest.mark.parametrize(
    ("body", "warning"),
    (
        ("```text\ncontent\n```", "CODE_FENCE_DETECTED"),
        ('{"article": "text"}', "JSON_OUTPUT_DETECTED"),
        ("---\ntitle: text", "YAML_OUTPUT_DETECTED"),
        ("<article>text</article>", "XML_OUTPUT_DETECTED"),
        ("إليك المقال\n\nText.", "MODEL_COMMENTARY_DETECTED"),
        ("Here is the article\n\nText.", "MODEL_COMMENTARY_DETECTED"),
    ),
)
def test_disallowed_output_warnings(body: str, warning: str) -> None:
    """Detect disallowed wrappers and model commentary without removal."""
    article = parse(f"# Headline\n\n{body}", target_word_count=8)

    assert warning in article.warnings
    assert body in article.body_markdown


def test_disabled_structures_add_warnings_in_exact_stage_order() -> None:
    """Preserve structures while adding every disabled-structure warning."""
    planning_result = make_planning_result(
        use_headings=False,
        use_bullets=False,
        use_table=False,
        use_faq=False,
        use_timeline=False,
    )
    article = parse(
        "# LEAD\n\n```\nHere is the article\n```\n\n"
        "## FAQ Timeline\n\n- Item\n\n"
        "| A | B |\n| --- | --- |\n| one | two |",
        target_word_count=100,
        planning_result=planning_result,
    )

    assert article.warnings == (
        "CODE_FENCE_DETECTED",
        "MODEL_COMMENTARY_DETECTED",
        "INTERNAL_LABEL_EXPOSED",
        "HEADINGS_NOT_ALLOWED",
        "BULLETS_NOT_ALLOWED",
        "TABLE_NOT_ALLOWED",
        "FAQ_NOT_ALLOWED",
        "TIMELINE_NOT_ALLOWED",
        "ARTICLE_TOO_SHORT",
    )
    assert len(article.warnings) == len(set(article.warnings))


def test_allowed_structures_do_not_add_structure_warnings() -> None:
    """Omit structural warnings when every detected structure is allowed."""
    article = parse(
        "# Headline\n\n## FAQ Timeline\n\n- Item\n\n"
        "| A | B |\n| --- | --- |\n| one | two |",
        target_word_count=8,
    )

    for warning in (
        "HEADINGS_NOT_ALLOWED",
        "BULLETS_NOT_ALLOWED",
        "TABLE_NOT_ALLOWED",
        "FAQ_NOT_ALLOWED",
        "TIMELINE_NOT_ALLOWED",
    ):
        assert warning not in article.warnings


def test_word_count_includes_visible_text_and_excludes_markers() -> None:
    """Count headline, prose, list, heading, and table cells without syntax."""
    article = parse(
        "# Main headline\n\n## Key details\n\nParagraph **bold** text.\n\n"
        "- Bullet item\n\n1. Numbered item\n\n"
        "| Cell one | Cell two |\n| --- | --- |\n| Value one | Value two |",
        target_word_count=19,
    )

    assert article.word_count == 19


@pytest.mark.parametrize(
    ("target", "warning"),
    ((100, "ARTICLE_TOO_SHORT"), (1, "ARTICLE_TOO_LONG")),
)
def test_length_warnings(target: int, warning: str) -> None:
    """Add non-fatal short and long warnings outside the 20 percent range."""
    article = parse("# One two\n\nthree four", target_word_count=target)

    assert warning in article.warnings


def test_in_range_length_has_no_warning_and_reason_order_is_exact() -> None:
    """Omit length warnings within tolerance and return all reason codes."""
    article = parse("# One two\n\nthree four", target_word_count=4)

    assert "ARTICLE_TOO_SHORT" not in article.warnings
    assert "ARTICLE_TOO_LONG" not in article.warnings
    assert article.reason_codes == REASON_CODES


def test_identical_inputs_are_deterministic_and_unchanged() -> None:
    """Return identical values without mutating immutable inputs."""
    generation_result = make_generation_result("# Headline\n\nExact wording!")
    generation_prompt = make_prompt(4)
    planning_result = make_planning_result()
    original_result = replace(generation_result)
    original_prompt = replace(generation_prompt)
    parser = DeterministicArticleParser()

    first = parser.parse(
        generation_result=generation_result,
        generation_prompt=generation_prompt,
        planning_result=planning_result,
    )
    second = parser.parse(
        generation_result=generation_result,
        generation_prompt=generation_prompt,
        planning_result=planning_result,
    )

    assert first == second
    assert isinstance(first, ParsedArticle)
    assert first.body_markdown == "Exact wording!"
    assert generation_result == original_result
    assert generation_prompt == original_prompt
