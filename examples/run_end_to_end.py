"""Run one Arabic news source through the complete HKEI OS v2 pipeline."""

import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_error import GenerationError
from src.generation.finish_reason import FinishReason
from src.generation.generation_result import GenerationResult
from src.generation.generation_service import GenerationService
from src.generation.openai_provider import OpenAIProvider
from src.intake.source_intake import SourceValidationError
from src.parsing.deterministic_article_parser import DeterministicArticleParser
from src.parsing.parsed_article import ParsedArticle
from src.parsing.parsing_error import ParsingError
from src.prompting.deterministic_prompt_builder import PromptConfigurationError
from src.workflows.editorial_generation_workflow import (
    EditorialGenerationWorkflow,
)
from src.workflows.editorial_generation_result import EditorialGenerationResult
from src.workflows.editorial_prompt_workflow import EditorialPromptWorkflow


EDITORIAL_POLICY = """- Accuracy before fluency.
- Use only supplied facts.
- Preserve attribution and uncertainty.
- Write natural modern Arabic.
- Avoid clickbait and filler.
- Do not add unsupported background.
- Human review is required before publication."""

TITLE = "المرور السعودي يضاعف غرامات المراوغة بين المركبات بسرعة"
BODY = """تواصل السلطات الأمنية في المملكة العربية السعودية رفع مستويات الأمان على الطرقات عبر التصدي للأنماط القيادية الطائشة. وفي هذا السياق، وجهت الجهات المختصة في المرور السعودي تنبيهاً شديد اللهجة لكافة مستخدمي الطريق، مسلطة الضوء على مخاطر القيادة والمراوغة بين المركبات أثناء السير بسرعة.

أوضحت منصة المرور الرسمية عبر شبكة X أن المراوغة بين المركبات تصنف كمخالفة مرورية شديدة الخطورة، ويواجه مرتكبها غرامة تبدأ من 3,000 ريال سعودي وتصل إلى 6,000 ريال سعودي.

تشمل المخاطر المحتملة فقدان السيطرة على المركبة ووقوع تصادمات وتعريض مستخدمي الطريق للخطر. وينصح بالالتزام بالمسار المحدد وضبط السرعة وترك مسافة أمان كافية."""
USER_INSTRUCTION = (
    "اكتب خبرًا خدميًا واضحًا ودقيقًا للقارئ العام، مع الحفاظ على "
    "الغرامات والأرقام كما وردت في المصدر."
)


def _render_items(values: tuple[str, ...]) -> str:
    """Render tuple values as an ordered list or None."""
    return "\n".join(f"- {value}" for value in values) if values else "None"


def _require_complete_generation(result: GenerationResult) -> None:
    """Reject any result that is not safe to parse and save as complete."""
    if (
        result.finish_reason is not FinishReason.COMPLETED
        or "OUTPUT_TRUNCATED" in result.warnings
    ):
        raise GenerationError("GENERATION_INTERRUPTED")


def _parse_and_save(
    *,
    result: EditorialGenerationResult,
    parser: DeterministicArticleParser,
    output_path: Path,
) -> ParsedArticle:
    """Parse and save only one explicitly completed generation result."""
    generation_result = result.generation_result
    _require_complete_generation(generation_result)
    prompt_result = result.prompt_result
    parsed_article = parser.parse(
        generation_result=generation_result,
        generation_prompt=prompt_result.generation_prompt,
        planning_result=prompt_result.planning_result,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(parsed_article.full_markdown, encoding="utf-8")
    return parsed_article


def main() -> int:
    """Run one provider-backed generation and parse its Markdown output."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None or not api_key.strip():
        print("OpenAI configuration not found. Set OPENAI_API_KEY.")
        return 1

    model = os.getenv("OPENAI_MODEL", "gpt-5")
    configuration = GenerationConfiguration(
        model=model,
        max_output_tokens=4000,
        temperature=None,
        reasoning_effort="low",
        timeout_seconds=60.0,
        request_metadata=(),
    )
    prompt_workflow = EditorialPromptWorkflow(
        editorial_policy=EDITORIAL_POLICY,
    )
    generation_service = GenerationService(
        OpenAIProvider(api_key=api_key),
    )
    workflow = EditorialGenerationWorkflow(
        prompt_workflow=prompt_workflow,
        generation_service=generation_service,
        generation_configuration=configuration,
    )

    try:
        result = workflow.process(
            title=TITLE,
            body=BODY,
            source_name="المرور السعودي",
            source_url="https://x.com/eMoroor",
            published_at="2026-08-04T21:34:00+03:00",
            language="ar",
            country="Saudi Arabia",
            category="public service",
            tags=("المرور", "السعودية", "غرامات", "السلامة المرورية"),
            user_instruction=USER_INSTRUCTION,
        )
        output_path = PROJECT_ROOT / "outputs" / "end_to_end_article_v1.md"
        parsed_article = _parse_and_save(
            result=result,
            parser=DeterministicArticleParser(),
            output_path=output_path,
        )
        prompt_result = result.prompt_result
        planning_result = prompt_result.planning_result
    except (
        SourceValidationError,
        PromptConfigurationError,
        GenerationError,
        ParsingError,
    ) as error:
        print(f"HKEI error: {error.code}")
        return 1

    strategy_result = planning_result.strategy_result
    intent_result = strategy_result.intent_result
    classification_result = intent_result.classification_result
    classification = classification_result.classification
    reader_intent = intent_result.reader_intent
    strategy = strategy_result.strategy
    generation_result = result.generation_result

    print("=== CLASSIFICATION ===")
    print()
    print("Content Type:")
    print(classification.content_type.value)
    print()
    print("Classification Confidence:")
    print(classification.confidence.value)
    print()
    print("Reader Intent:")
    print(reader_intent.reader_intent.value)
    print()
    print("Reader Intent Confidence:")
    print(reader_intent.confidence.value)
    print()
    print("=== STRATEGY ===")
    print()
    print("Article Length:")
    print(strategy.article_length.value)
    print()
    print("Article Depth:")
    print(strategy.article_depth.value)
    print()
    print("Writing Mode:")
    print(strategy.writing_mode.value)
    print()
    print("Target Word Count:")
    print(strategy.target_word_count)
    print()
    print("=== GENERATION ===")
    print()
    print("Provider:")
    print(generation_result.provider_name)
    print()
    print("Model:")
    print(generation_result.model_name)
    print()
    print("Finish Reason:")
    print(generation_result.finish_reason.value)
    print()
    print("Input Tokens:")
    print(generation_result.input_tokens)
    print()
    print("Output Tokens:")
    print(generation_result.output_tokens)
    print()
    print("Total Tokens:")
    print(generation_result.total_tokens)
    print()
    print("Generation Warnings:")
    print(_render_items(generation_result.warnings))
    print()
    print("=== PARSING ===")
    print()
    print("Headline:")
    print(parsed_article.headline)
    print()
    print("Word Count:")
    print(parsed_article.word_count)
    print()
    print("Parsing Warnings:")
    print(_render_items(parsed_article.warnings))
    print()
    print("=== ARTICLE ===")
    print()
    print(parsed_article.full_markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
