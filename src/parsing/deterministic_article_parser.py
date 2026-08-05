"""Deterministic parsing and structural validation of generated Markdown."""

import re

from src.generation.generation_result import GenerationResult
from src.prompting.generation_prompt import GenerationPrompt
from src.workflows.editorial_planning_result import EditorialPlanningResult

from .parsed_article import ParsedArticle
from .parsing_error import ParsingError


_FORBIDDEN_LABELS = frozenset(
    value.casefold()
    for value in (
        "LEAD",
        "CORE_UPDATE",
        "RESULT",
        "KEY_DETAILS",
        "OFFICIAL_INFORMATION",
        "CLAIM",
        "EVIDENCE",
        "VERDICT",
        "REQUIREMENTS",
        "PROCEDURE",
        "FEES",
        "DEADLINES",
        "READER_ACTION",
        "IMPACT",
        "EXPLANATION",
        "BACKGROUND",
        "TIMELINE",
        "COMPARISON",
        "QUOTES",
        "MISSING_INFORMATION",
        "CLOSING",
        "EDITORIAL STRATEGY",
        "INTERNAL ARTICLE PLAN",
        "STRUCTURED FACTS",
        "CLAIMS AND ATTRIBUTION",
        "PROHIBITED CLAIMS",
        "ORIGINAL SOURCE MATERIAL",
        "FINAL GENERATION COMMAND",
    )
)
_REASON_CODES = (
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
_BULLET_PATTERN = re.compile(r"^[-*+] (.*)$")
_NUMBERED_PATTERN = re.compile(r"^\s*\d+[.)]\s+")
_DATE_LED_PATTERN = re.compile(
    r"^(?:\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})"
)
_TABLE_SEPARATOR_PATTERN = re.compile(r"^[ |:\-]+$")
_QUESTION_PREFIXES = (
    "ما ",
    "ماذا ",
    "متى ",
    "أين ",
    "كيف ",
    "هل ",
    "لماذا ",
    "من ",
)
_COMMENTARY_PHRASES = (
    "إليك المقال",
    "بالطبع",
    "سأقوم",
    "تم إنشاء المقال",
    "here is the article",
)


class DeterministicArticleParser:
    """Parse generated Markdown using deterministic structural rules."""

    def parse(
        self,
        *,
        generation_result: GenerationResult,
        generation_prompt: GenerationPrompt,
        planning_result: EditorialPlanningResult,
    ) -> ParsedArticle:
        """Parse and structurally validate one generated article.

        Args:
            generation_result: Raw provider generation result.
            generation_prompt: Prompt containing the target word count.
            planning_result: Planning result containing structural strategy.

        Returns:
            One immutable parsed article.

        Raises:
            ParsingError: If required article content is missing or invalid.
        """
        content = generation_result.content
        if not content.strip():
            raise ParsingError("GENERATED_CONTENT_EMPTY")

        normalized = self._normalize_markdown(content)
        lines = normalized.split("\n")
        h1_indices = [
            index
            for index, line in enumerate(lines)
            if line == "#" or line.startswith("# ")
        ]
        if not h1_indices:
            raise ParsingError("ARTICLE_HEADLINE_MISSING")
        if len(h1_indices) > 1:
            raise ParsingError("ARTICLE_HEADLINE_MULTIPLE")
        h1_index = h1_indices[0]
        if h1_index != 0:
            raise ParsingError("ARTICLE_HEADLINE_MISSING")
        headline = lines[h1_index][2:].strip()
        if not headline:
            raise ParsingError("ARTICLE_HEADLINE_MISSING")

        body_lines = lines[h1_index + 1 :]
        while body_lines and not body_lines[0]:
            body_lines.pop(0)
        while body_lines and not body_lines[-1]:
            body_lines.pop()
        body_markdown = "\n".join(body_lines)
        if not body_markdown.strip():
            raise ParsingError("ARTICLE_BODY_MISSING")
        full_markdown = f"# {headline}\n\n{body_markdown}"

        headings = tuple(
            heading
            for line in body_lines
            if line.startswith("## ")
            for heading in (line[3:].strip(),)
            if heading
        )
        bullet_items = tuple(
            item
            for line in body_lines
            for match in (_BULLET_PATTERN.match(line),)
            if match is not None
            for item in (match.group(1).strip(),)
            if item
        )
        table_count = self._count_tables(body_lines)
        paragraphs = self._extract_paragraphs(body_markdown)
        faq_detected = self._detect_faq(headings, body_lines)
        timeline_detected = self._detect_timeline(headings, body_lines)
        word_count = self._count_words(headline, body_lines)

        warnings = self._detect_disallowed_output(
            normalized,
            body_markdown,
            h1_index,
        )
        if self._has_internal_label(headline, headings, lines):
            self._add_warning(warnings, "INTERNAL_LABEL_EXPOSED")

        strategy = planning_result.strategy_result.strategy
        if headings and not strategy.use_headings:
            self._add_warning(warnings, "HEADINGS_NOT_ALLOWED")
        if bullet_items and not strategy.use_bullets:
            self._add_warning(warnings, "BULLETS_NOT_ALLOWED")
        if table_count > 0 and not strategy.use_table:
            self._add_warning(warnings, "TABLE_NOT_ALLOWED")
        if faq_detected and not strategy.use_faq:
            self._add_warning(warnings, "FAQ_NOT_ALLOWED")
        if timeline_detected and not strategy.use_timeline:
            self._add_warning(warnings, "TIMELINE_NOT_ALLOWED")

        target = generation_prompt.target_word_count
        if word_count < target * 0.80:
            self._add_warning(warnings, "ARTICLE_TOO_SHORT")
        if word_count > target * 1.20:
            self._add_warning(warnings, "ARTICLE_TOO_LONG")

        return ParsedArticle(
            headline=headline,
            body_markdown=body_markdown,
            full_markdown=full_markdown,
            headings=headings,
            paragraphs=paragraphs,
            bullet_items=bullet_items,
            table_count=table_count,
            faq_detected=faq_detected,
            timeline_detected=timeline_detected,
            word_count=word_count,
            warnings=tuple(warnings),
            reason_codes=_REASON_CODES,
        )

    @staticmethod
    def _normalize_markdown(content: str) -> str:
        """Apply harmless Markdown normalization in the required order."""
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in normalized.split("\n")]
        collapsed: list[str] = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    collapsed.append(line)
            else:
                blank_count = 0
                collapsed.append(line)
        while collapsed and not collapsed[0]:
            collapsed.pop(0)
        while collapsed and not collapsed[-1]:
            collapsed.pop()
        return "\n".join(collapsed)

    @staticmethod
    def _extract_paragraphs(body_markdown: str) -> tuple[str, ...]:
        """Extract paragraph blocks while excluding structural blocks."""
        paragraphs: list[str] = []
        for block in re.split(r"\n{2,}", body_markdown):
            block_lines = block.split("\n")
            if any(line.startswith("## ") for line in block_lines):
                continue
            if any(_BULLET_PATTERN.match(line) for line in block_lines):
                continue
            if any(_NUMBERED_PATTERN.match(line) for line in block_lines):
                continue
            if DeterministicArticleParser._count_tables(block_lines):
                continue
            paragraphs.append(block)
        return tuple(paragraphs)

    @staticmethod
    def _is_table_separator(line: str) -> bool:
        """Return whether a line is a supported Markdown table separator."""
        return (
            "|" in line
            and line.count("-") >= 3
            and _TABLE_SEPARATOR_PATTERN.fullmatch(line) is not None
        )

    @staticmethod
    def _count_tables(lines: list[str]) -> int:
        """Count each Markdown header and separator pair once."""
        return sum(
            1
            for index in range(len(lines) - 1)
            if lines[index]
            and "|" in lines[index]
            and DeterministicArticleParser._is_table_separator(lines[index + 1])
        )

    @staticmethod
    def _detect_faq(headings: tuple[str, ...], lines: list[str]) -> bool:
        """Detect FAQ headings or three question-like lines."""
        if any(
            any(term.casefold() in heading.casefold() for term in terms)
            for heading in headings
            for terms in (("الأسئلة الشائعة", "أسئلة شائعة", "faq"),)
        ):
            return True
        question_count = sum(
            1
            for line in lines
            if DeterministicArticleParser._is_question_line(line)
        )
        return question_count >= 3

    @staticmethod
    def _is_question_line(line: str) -> bool:
        """Return whether one line has a supported question-like form."""
        stripped = line.strip()
        return bool(
            stripped
            and not DeterministicArticleParser._is_table_separator(stripped)
            and (
                stripped.endswith(("؟", "?"))
                or stripped.startswith(_QUESTION_PREFIXES)
            )
        )

    @staticmethod
    def _detect_timeline(headings: tuple[str, ...], lines: list[str]) -> bool:
        """Detect timeline headings or three deterministic date-led lines."""
        if any(
            any(term.casefold() in heading.casefold() for term in terms)
            for heading in headings
            for terms in (("الخط الزمني", "التسلسل الزمني", "timeline"),)
        ):
            return True
        return (
            sum(bool(_DATE_LED_PATTERN.match(line.strip())) for line in lines)
            >= 3
        )

    @staticmethod
    def _count_words(headline: str, body_lines: list[str]) -> int:
        """Count deterministic visible words after removing Markdown syntax."""
        visible_lines = [headline]
        for line in body_lines:
            if DeterministicArticleParser._is_table_separator(line):
                continue
            visible = re.sub(r"^#{1,6}\s+", "", line)
            visible = re.sub(r"^\s*[-*+]\s+", "", visible)
            visible = _NUMBERED_PATTERN.sub("", visible)
            visible = visible.replace("|", " ")
            visible = re.sub(r"[*_`]", "", visible)
            visible_lines.append(visible)
        return len("\n".join(visible_lines).split())

    @staticmethod
    def _has_internal_label(
        headline: str,
        headings: tuple[str, ...],
        lines: list[str],
    ) -> bool:
        """Detect forbidden labels in headings or standalone lines."""
        candidates = [headline, *headings]
        candidates.extend(line.strip() for line in lines if line.strip())
        return any(value.casefold() in _FORBIDDEN_LABELS for value in candidates)

    @staticmethod
    def _detect_disallowed_output(
        normalized: str,
        body_markdown: str,
        h1_index: int,
    ) -> list[str]:
        """Detect disallowed wrappers and model commentary in stage order."""
        warnings: list[str] = []
        lines = normalized.split("\n")
        if any(line.startswith("```") for line in lines):
            warnings.append("CODE_FENCE_DETECTED")

        stripped = normalized.strip()
        body_stripped = body_markdown.strip()
        if (
            (stripped.startswith("{") and stripped.endswith("}"))
            or (body_stripped.startswith("{") and body_stripped.endswith("}"))
        ):
            warnings.append("JSON_OUTPUT_DETECTED")
        if stripped.startswith("---") or body_stripped.startswith("---"):
            warnings.append("YAML_OUTPUT_DETECTED")
        if (
            (stripped.startswith("<") and stripped.endswith(">"))
            or (body_stripped.startswith("<") and body_stripped.endswith(">"))
        ):
            warnings.append("XML_OUTPUT_DETECTED")

        folded = normalized.casefold()
        commentary_before_h1 = any(line for line in lines[:h1_index])
        if commentary_before_h1 or any(
            phrase.casefold() in folded for phrase in _COMMENTARY_PHRASES
        ):
            warnings.append("MODEL_COMMENTARY_DETECTED")
        return warnings

    @staticmethod
    def _add_warning(warnings: list[str], warning: str) -> None:
        """Append a warning only at its first stage occurrence."""
        if warning not in warnings:
            warnings.append(warning)
