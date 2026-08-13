"""Immutable resolution contract for one editorial dimension."""

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.topic.topic import Topic

from .editorial_resolution_source import EditorialResolutionSource
from .editorial_resolution_status import EditorialResolutionStatus
from .editorial_resolution_warning import EditorialResolutionWarning


class EditorialResolutionDimension(str, Enum):
    """Identify the dimension whose authority is represented."""

    TOPIC = "TOPIC"
    FORMAT = "FORMAT"
    READER_INTENT = "READER_INTENT"


ResolutionValue = TypeVar("ResolutionValue", Topic, EditorialFormat, ReaderIntent)


@dataclass(frozen=True)
class EditorialDimensionResolution(Generic[ResolutionValue]):
    """Store a caller-produced dimension result without selection behavior."""

    dimension: EditorialResolutionDimension
    value: ResolutionValue | None
    status: EditorialResolutionStatus
    source: EditorialResolutionSource
    confidence: str | None
    confidence_source: EditorialResolutionSource
    ambiguity: bool
    review_required: bool
    warnings: tuple[EditorialResolutionWarning, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, EditorialResolutionDimension):
            raise ValueError("dimension must be an EditorialResolutionDimension")
        if not isinstance(self.status, EditorialResolutionStatus):
            raise ValueError("status must be an EditorialResolutionStatus")
        if not isinstance(self.source, EditorialResolutionSource):
            raise ValueError("source must be an EditorialResolutionSource")
        if not isinstance(self.confidence_source, EditorialResolutionSource):
            raise ValueError("confidence_source must be an EditorialResolutionSource")
        if not isinstance(self.ambiguity, bool) or not isinstance(self.review_required, bool):
            raise ValueError("ambiguity and review_required must be booleans")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, EditorialResolutionWarning) for item in self.warnings
        ):
            raise ValueError("warnings must be a tuple of EditorialResolutionWarning")
        if len(self.warnings) != len(set(self.warnings)):
            raise ValueError("warnings must not contain duplicates")

        expected_type = {
            EditorialResolutionDimension.TOPIC: Topic,
            EditorialResolutionDimension.FORMAT: EditorialFormat,
            EditorialResolutionDimension.READER_INTENT: ReaderIntent,
        }[self.dimension]
        if self.value is not None and not isinstance(self.value, expected_type):
            raise ValueError(f"value is incompatible with {self.dimension.value}")

        if self.dimension is EditorialResolutionDimension.TOPIC and self.source is EditorialResolutionSource.FORMAT_V2_SHADOW:
            raise ValueError("Topic resolution cannot use FORMAT_V2_SHADOW")
        if self.dimension is EditorialResolutionDimension.READER_INTENT and self.source is EditorialResolutionSource.ADJUDICATION:
            raise ValueError("Reader Intent cannot use ADJUDICATION in the MVP")

        required_sources = {
            EditorialResolutionStatus.DETERMINISTIC_ACCEPTED: EditorialResolutionSource.DETERMINISTIC_V1,
            EditorialResolutionStatus.ADJUDICATED_ACCEPTED: EditorialResolutionSource.ADJUDICATION,
            EditorialResolutionStatus.FALLBACK_ACCEPTED: EditorialResolutionSource.FALLBACK,
            EditorialResolutionStatus.UNRESOLVED: EditorialResolutionSource.NONE,
        }
        required = required_sources.get(self.status)
        if required is not None and self.source is not required:
            raise ValueError(f"{self.status.value} requires source {required.value}")
        if self.status is EditorialResolutionStatus.UNRESOLVED:
            if self.value is not None:
                raise ValueError("UNRESOLVED requires value None")
            if not self.review_required:
                raise ValueError("UNRESOLVED requires review_required")
        elif self.value is None:
            raise ValueError("a resolved status requires a value")
        if self.status is EditorialResolutionStatus.REVIEW_REQUIRED and not self.review_required:
            raise ValueError("REVIEW_REQUIRED status requires review_required")

        if self.confidence is None:
            if self.confidence_source is not EditorialResolutionSource.NONE:
                raise ValueError("missing confidence requires confidence_source NONE")
        else:
            if not isinstance(self.confidence, str) or not self.confidence or self.confidence != self.confidence.strip():
                raise ValueError("confidence must be a non-empty normalized string")
            if self.confidence_source is EditorialResolutionSource.NONE:
                raise ValueError("confidence requires explicit provenance")
