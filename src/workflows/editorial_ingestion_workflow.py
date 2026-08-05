"""End-to-end orchestration of editorial source ingestion."""

from src.assessment.source_risk_assessment_engine import (
    SourceRiskAssessmentEngine,
)
from src.facts.fact_extraction_service import FactExtractionService
from src.intake.source_intake import SourceIntake

from .editorial_ingestion_result import EditorialIngestionResult


class EditorialIngestionWorkflow:
    """Coordinate intake, risk assessment, and fact extraction."""

    def __init__(
        self,
        source_intake: SourceIntake | None = None,
        assessment_engine: SourceRiskAssessmentEngine | None = None,
        fact_extraction_service: FactExtractionService | None = None,
    ) -> None:
        """Initialize the editorial ingestion workflow.

        Args:
            source_intake: Intake service, or None to create the default.
            assessment_engine: Assessment engine, or None to create the default.
            fact_extraction_service: Fact service, or None to create the default.
        """
        self.source_intake = (
            source_intake if source_intake is not None else SourceIntake()
        )
        self.assessment_engine = (
            assessment_engine
            if assessment_engine is not None
            else SourceRiskAssessmentEngine()
        )
        self.fact_extraction_service = (
            fact_extraction_service
            if fact_extraction_service is not None
            else FactExtractionService()
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
    ) -> EditorialIngestionResult:
        """Ingest raw source fields through each workflow stage.

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

        Returns:
            The normalized source, its assessment, and extracted facts.
        """
        source = self.source_intake.process(
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
        )
        assessment = self.assessment_engine.assess(source)
        facts = self.fact_extraction_service.process(source)
        return EditorialIngestionResult(
            source=source,
            assessment=assessment,
            facts=facts,
        )
