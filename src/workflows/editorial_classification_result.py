"""Immutable result of the editorial classification workflow."""

from dataclasses import dataclass

from src.classification.content_type_classification import (
    ContentTypeClassification,
)

from .editorial_ingestion_result import EditorialIngestionResult


@dataclass(frozen=True)
class EditorialClassificationResult:
    """Represent ingestion and content type classification results.

    Attributes:
        ingestion: Complete editorial ingestion result.
        classification: Content type classification for the ingestion result.
    """

    ingestion: EditorialIngestionResult
    classification: ContentTypeClassification
