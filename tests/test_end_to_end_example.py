"""Safety tests for the first end-to-end generation example."""

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from examples.run_end_to_end import _parse_and_save
from src.generation.finish_reason import FinishReason
from src.generation.generation_error import GenerationError
from src.generation.generation_result import GenerationResult
from src.parsing.deterministic_article_parser import DeterministicArticleParser
from src.parsing.parsed_article import ParsedArticle
from src.workflows.editorial_generation_result import EditorialGenerationResult


def make_result(
    *,
    finish_reason: FinishReason = FinishReason.COMPLETED,
    warnings: tuple[str, ...] = (),
) -> EditorialGenerationResult:
    """Create an example workflow result with configurable completion state."""
    result = MagicMock()
    result.generation_result = GenerationResult(
        content="# Headline\n\nComplete article.",
        provider_name="provider-id",
        model_name="model-id",
        input_tokens=10,
        output_tokens=10,
        total_tokens=20,
        finish_reason=finish_reason,
        request_id="request-id",
        warnings=warnings,
    )
    return cast(EditorialGenerationResult, result)


@pytest.mark.parametrize(
    "result",
    (
        make_result(finish_reason=FinishReason.LENGTH_LIMIT),
        make_result(warnings=("OUTPUT_TRUNCATED",)),
    ),
)
def test_truncated_result_is_not_parsed_or_saved(
    result: EditorialGenerationResult,
    tmp_path: Path,
) -> None:
    """Stop truncated output before parser or filesystem output calls."""
    parser = MagicMock(spec=DeterministicArticleParser)
    output_path = tmp_path / "outputs" / "article.md"

    with pytest.raises(GenerationError) as raised:
        _parse_and_save(
            result=result,
            parser=parser,
            output_path=output_path,
        )

    assert raised.value.code == "GENERATION_INTERRUPTED"
    assert parser.mock_calls == []
    assert not output_path.exists()


def test_completed_result_is_parsed_then_saved(tmp_path: Path) -> None:
    """Continue normally and save only after completed output parses."""
    result = make_result()
    parsed = MagicMock(spec=ParsedArticle)
    parsed.full_markdown = "# Headline\n\nComplete article."
    parser = MagicMock(spec=DeterministicArticleParser)
    parser.parse.return_value = parsed
    output_path = tmp_path / "outputs" / "article.md"

    actual = _parse_and_save(
        result=result,
        parser=parser,
        output_path=output_path,
    )

    assert actual is parsed
    parser.parse.assert_called_once_with(
        generation_result=result.generation_result,
        generation_prompt=result.prompt_result.generation_prompt,
        planning_result=result.prompt_result.planning_result,
    )
    assert output_path.read_text(encoding="utf-8") == parsed.full_markdown
