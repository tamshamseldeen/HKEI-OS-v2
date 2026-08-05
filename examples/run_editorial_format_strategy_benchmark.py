"""Run deterministic editorial format strategy adaptation benchmarks."""

from dataclasses import dataclass
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_editorial_format_benchmark import (
    BENCHMARK_CASES as FORMAT_BENCHMARK_CASES,
    EditorialFormatBenchmarkCase,
)
from src.formatting.editorial_format import EditorialFormat
from src.strategy.article_depth import ArticleDepth
from src.strategy.article_length import ArticleLength
from src.strategy.editorial_format_strategy_adapter import (
    EditorialFormatStrategyAdapter,
)
from src.strategy.editorial_strategy import EditorialStrategy
from src.strategy.writing_mode import WritingMode
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow
from src.workflows.editorial_strategy_workflow import EditorialStrategyWorkflow


@dataclass(frozen=True)
class ExpectedAdaptedStrategy:
    """Represent the required adapted fields for one benchmark case."""

    editorial_format: EditorialFormat
    article_length: ArticleLength
    article_depth: ArticleDepth
    writing_mode: WritingMode
    target_word_count: int
    required_reason_code: str
    use_headings: bool
    use_bullets: bool | None = None
    use_table: bool | None = None
    use_faq: bool | None = None
    use_timeline: bool | None = None
    use_background: bool | None = None
    include_reader_action: bool | None = None
    prohibited_warning: str | None = None


@dataclass(frozen=True)
class EditorialFormatStrategyBenchmarkCase:
    """Pair one existing format case with its adapted strategy expectation."""

    source_case: EditorialFormatBenchmarkCase
    expected: ExpectedAdaptedStrategy


STRATEGY_BENCHMARK_CASES: tuple[EditorialFormatStrategyBenchmarkCase, ...] = (
    EditorialFormatStrategyBenchmarkCase(
        source_case=FORMAT_BENCHMARK_CASES[0],
        expected=ExpectedAdaptedStrategy(
            editorial_format=EditorialFormat.SERVICE,
            article_length=ArticleLength.MEDIUM,
            article_depth=ArticleDepth.EXPLAINED,
            writing_mode=WritingMode.SERVICE,
            target_word_count=450,
            required_reason_code="FORMAT_SERVICE_STRATEGY_APPLIED",
            use_headings=True,
            use_bullets=True,
            use_table=True,
            include_reader_action=True,
        ),
    ),
    EditorialFormatStrategyBenchmarkCase(
        source_case=FORMAT_BENCHMARK_CASES[1],
        expected=ExpectedAdaptedStrategy(
            editorial_format=EditorialFormat.FEATURE,
            article_length=ArticleLength.LONG,
            article_depth=ArticleDepth.DETAILED,
            writing_mode=WritingMode.EXPLAINER,
            target_word_count=800,
            required_reason_code="FORMAT_FEATURE_STRATEGY_APPLIED",
            use_headings=True,
            use_background=True,
            prohibited_warning="FORMAT_FEATURE_RESTRICTED_BY_RISK",
        ),
    ),
    EditorialFormatStrategyBenchmarkCase(
        source_case=FORMAT_BENCHMARK_CASES[2],
        expected=ExpectedAdaptedStrategy(
            editorial_format=EditorialFormat.GUIDE,
            article_length=ArticleLength.MEDIUM,
            article_depth=ArticleDepth.EXPLAINED,
            writing_mode=WritingMode.SERVICE,
            target_word_count=450,
            required_reason_code="FORMAT_GUIDE_STRATEGY_APPLIED",
            use_headings=True,
            use_bullets=True,
            use_table=True,
            include_reader_action=True,
        ),
    ),
    EditorialFormatStrategyBenchmarkCase(
        source_case=FORMAT_BENCHMARK_CASES[3],
        expected=ExpectedAdaptedStrategy(
            editorial_format=EditorialFormat.RESULT_REPORT,
            article_length=ArticleLength.VERY_SHORT,
            article_depth=ArticleDepth.UPDATE,
            writing_mode=WritingMode.RESULT_REPORT,
            target_word_count=120,
            required_reason_code="FORMAT_RESULT_REPORT_STRATEGY_APPLIED",
            use_headings=False,
            use_bullets=False,
            use_table=False,
            use_faq=False,
            use_timeline=False,
            use_background=False,
        ),
    ),
)


def _source_fields(case: EditorialFormatBenchmarkCase) -> dict[str, object]:
    """Build the shared raw workflow fields for one existing source case."""
    return {
        "title": case.title,
        "body": case.body,
        "source_name": case.source_name,
        "source_url": case.source_url,
        "category": case.category,
        "tags": case.tags,
        "user_instruction": case.user_instruction,
    }


def _matches_expected(
    *,
    strategy: EditorialStrategy,
    editorial_format: EditorialFormat,
    expected: ExpectedAdaptedStrategy,
) -> bool:
    """Compare the explicitly specified strategy and classification fields."""
    required_values_match = (
        editorial_format is expected.editorial_format
        and strategy.article_length is expected.article_length
        and strategy.article_depth is expected.article_depth
        and strategy.writing_mode is expected.writing_mode
        and strategy.target_word_count == expected.target_word_count
        and expected.required_reason_code in strategy.reason_codes
    )
    optional_fields = (
        ("use_headings", expected.use_headings),
        ("use_bullets", expected.use_bullets),
        ("use_table", expected.use_table),
        ("use_faq", expected.use_faq),
        ("use_timeline", expected.use_timeline),
        ("use_background", expected.use_background),
        ("include_reader_action", expected.include_reader_action),
    )
    optional_values_match = all(
        expected_value is None or getattr(strategy, field) is expected_value
        for field, expected_value in optional_fields
    )
    warning_is_absent = (
        expected.prohibited_warning is None
        or expected.prohibited_warning not in strategy.warnings
    )
    return required_values_match and optional_values_match and warning_is_absent


def _print_items(label: str, values: tuple[str, ...]) -> None:
    """Print one tuple as bullet items or ``None``."""
    print(label)
    if values:
        for value in values:
            print(f"- {value}")
    else:
        print("None")
    print()


def run_benchmark(
    cases: tuple[
        EditorialFormatStrategyBenchmarkCase, ...
    ] = STRATEGY_BENCHMARK_CASES,
) -> int:
    """Run real workflows and return zero only when all adaptations match.

    Args:
        cases: Ordered strategy benchmark cases.

    Returns:
        Zero when every adapted strategy matches, otherwise one.
    """
    strategy_workflow = EditorialStrategyWorkflow()
    format_workflow = EditorialFormatWorkflow()
    adapter = EditorialFormatStrategyAdapter()
    matched = 0

    for benchmark_case in cases:
        case = benchmark_case.source_case
        fields = _source_fields(case)
        strategy_result = strategy_workflow.process(**fields)
        format_result = format_workflow.process(**fields)
        base_strategy = strategy_result.strategy
        ingestion = strategy_result.intent_result.classification_result.ingestion
        adapted_strategy = adapter.adapt(
            strategy=base_strategy,
            format_classification=format_result.format_classification,
            facts=ingestion.facts,
            assessment=ingestion.assessment,
        )
        is_match = _matches_expected(
            strategy=adapted_strategy,
            editorial_format=format_result.format_classification.editorial_format,
            expected=benchmark_case.expected,
        )
        matched += int(is_match)

        print(f"=== {case.name} ===")
        print()
        print("Format:")
        print(format_result.format_classification.editorial_format.value)
        print()
        print("Base Strategy:")
        print(_strategy_summary(base_strategy))
        print()
        print("Adapted Strategy:")
        print(_strategy_summary(adapted_strategy))
        print()
        print("Expected Match:")
        print("YES" if is_match else "NO")
        print()
        _print_items("Reason Codes:", adapted_strategy.reason_codes)
        _print_items("Warnings:", adapted_strategy.warnings)

    total = len(cases)
    mismatched = total - matched
    accuracy = matched / total * 100.0 if total else 0.0
    print("=== SUMMARY ===")
    print()
    print("Total Cases:")
    print(total)
    print()
    print("Matched:")
    print(matched)
    print()
    print("Mismatched:")
    print(mismatched)
    print()
    print("Accuracy:")
    print(f"{accuracy:.2f}%")
    return 0 if mismatched == 0 else 1


def _strategy_summary(strategy: EditorialStrategy) -> str:
    """Render the four primary strategy values in the required order."""
    return " / ".join(
        (
            strategy.article_length.value,
            strategy.article_depth.value,
            strategy.writing_mode.value,
            str(strategy.target_word_count),
        )
    )


def main() -> int:
    """Run the fixed editorial format strategy benchmark."""
    return run_benchmark()


if __name__ == "__main__":
    raise SystemExit(main())
