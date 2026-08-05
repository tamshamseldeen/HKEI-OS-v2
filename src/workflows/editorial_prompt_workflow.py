"""End-to-end orchestration of deterministic prompt building."""

from src.prompting.deterministic_prompt_builder import (
    DeterministicPromptBuilder,
)

from .editorial_planning_workflow import EditorialPlanningWorkflow
from .editorial_prompt_result import EditorialPromptResult


class EditorialPromptWorkflow:
    """Coordinate editorial planning and deterministic prompt building."""

    def __init__(
        self,
        editorial_policy: str | None = None,
        planning_workflow: EditorialPlanningWorkflow | None = None,
        prompt_builder: DeterministicPromptBuilder | None = None,
    ) -> None:
        """Initialize the editorial prompt workflow.

        Args:
            editorial_policy: Policy used by a default prompt builder.
            planning_workflow: Planning workflow, or None for the default.
            prompt_builder: Prompt builder, or None for the default.
        """
        self.planning_workflow = (
            planning_workflow
            if planning_workflow is not None
            else EditorialPlanningWorkflow()
        )
        self.prompt_builder = (
            prompt_builder
            if prompt_builder is not None
            else DeterministicPromptBuilder(editorial_policy or "")
        )

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
    ) -> EditorialPromptResult:
        """Plan raw source fields and build a deterministic prompt.

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
            The editorial planning result and deterministic generation prompt.
        """
        planning_result = self.planning_workflow.process(
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
        generation_prompt = self.prompt_builder.build(
            planning_result=planning_result,
            user_instruction=user_instruction,
        )
        return EditorialPromptResult(
            planning_result=planning_result,
            generation_prompt=generation_prompt,
        )
