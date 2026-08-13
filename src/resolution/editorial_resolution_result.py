"""Immutable final limited editorial resolution result contract."""

from dataclasses import dataclass

from .editorial_dimension_resolution import (
    EditorialDimensionResolution,
    EditorialResolutionDimension,
)
from .editorial_resolution_warning import EditorialResolutionWarning


@dataclass(frozen=True)
class EditorialResolutionResult:
    """Collect three independently produced dimension resolutions."""

    topic_resolution: EditorialDimensionResolution
    format_resolution: EditorialDimensionResolution
    reader_intent_resolution: EditorialDimensionResolution
    review_required: bool
    warnings: tuple[EditorialResolutionWarning, ...]
    provider_used: bool
    input_fingerprint: str | None

    def __post_init__(self) -> None:
        expected = (
            (self.topic_resolution, EditorialResolutionDimension.TOPIC),
            (self.format_resolution, EditorialResolutionDimension.FORMAT),
            (self.reader_intent_resolution, EditorialResolutionDimension.READER_INTENT),
        )
        if any(
            not isinstance(item, EditorialDimensionResolution) or item.dimension is not dimension
            for item, dimension in expected
        ):
            raise ValueError("dimension resolutions are missing or out of position")
        if not isinstance(self.review_required, bool) or not isinstance(self.provider_used, bool):
            raise ValueError("review_required and provider_used must be booleans")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, EditorialResolutionWarning) for item in self.warnings
        ):
            raise ValueError("warnings must be a tuple of EditorialResolutionWarning")
        if len(self.warnings) != len(set(self.warnings)):
            raise ValueError("warnings must not contain duplicates")
        if self.input_fingerprint is not None and (
            not isinstance(self.input_fingerprint, str)
            or not self.input_fingerprint
            or self.input_fingerprint != self.input_fingerprint.strip()
        ):
            raise ValueError("input_fingerprint must be a normalized string or None")
