"""End-to-end orchestration of provider-backed article generation."""

from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_error import GenerationError
from src.generation.generation_service import GenerationService

from .editorial_generation_result import EditorialGenerationResult
from .editorial_prompt_workflow import EditorialPromptWorkflow


class EditorialGenerationWorkflow:
    """Coordinate prompt preparation and eligible article generation."""

    def __init__(
        self,
        prompt_workflow: EditorialPromptWorkflow,
        generation_service: GenerationService,
        generation_configuration: GenerationConfiguration,
    ) -> None:
        """Initialize the editorial generation workflow.

        Args:
            prompt_workflow: Workflow used to prepare a generation prompt.
            generation_service: Provider-agnostic generation service.
            generation_configuration: Configuration for the provider request.
        """
        self.prompt_workflow = prompt_workflow
        self.generation_service = generation_service
        self.generation_configuration = generation_configuration

    def process(
        self,
        *,
        title: str | None,
        body: str | None,
        source_name: str | None,
        source_url: str | None = None,
        published_at: str | None = None,
        language: str | None = None,
        country: str | None = None,
        author: str | None = None,
        images: tuple[str, ...] = (),
        attachments: tuple[str, ...] = (),
        category: str | None = None,
        tags: tuple[str, ...] = (),
        user_instruction: str | None = None,
    ) -> EditorialGenerationResult:
        """Prepare a prompt and generate an eligible article.

        Args:
            title: Raw source title.
            body: Raw source body.
            source_name: Raw source name.
            source_url: Optional raw source URL.
            published_at: Optional publication timestamp.
            language: Optional source language code.
            country: Optional country associated with the source.
            author: Optional source author.
            images: Image references associated with the source.
            attachments: Attachment references associated with the source.
            category: Optional source category.
            tags: Tags associated with the source.
            user_instruction: Optional explicit editorial instruction.

        Returns:
            The exact prompt result and normalized generation result.

        Raises:
            GenerationError: If the assessment does not permit generation.
        """
        prompt_result = self.prompt_workflow.process(
            title=title,
            body=body,
            source_name=source_name,
            source_url=source_url,
            published_at=published_at,
            language=language,
            country=country,
            author=author,
            images=images,
            attachments=attachments,
            category=category,
            tags=tags,
            user_instruction=user_instruction,
        )
        assessment = (
            prompt_result.planning_result.strategy_result.intent_result
            .classification_result.ingestion.assessment
        )
        if not assessment.generation_allowed:
            raise GenerationError("GENERATION_INTERRUPTED")
        generation_result = self.generation_service.generate(
            prompt=prompt_result.generation_prompt,
            configuration=self.generation_configuration,
        )
        return EditorialGenerationResult(
            prompt_result=prompt_result,
            generation_result=generation_result,
        )
