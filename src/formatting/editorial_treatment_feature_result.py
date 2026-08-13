"""Immutable symbolic document-treatment feature result for Format V2."""

from dataclasses import dataclass

from .editorial_treatment_feature import EditorialTreatmentFeature


@dataclass(frozen=True)
class EditorialTreatmentFeatureResult:
    """Store symbolic features only; never source text or matched excerpts."""

    features: tuple[EditorialTreatmentFeature, ...]
    headline_features: tuple[EditorialTreatmentFeature, ...]
    lead_features: tuple[EditorialTreatmentFeature, ...]
    body_features: tuple[EditorialTreatmentFeature, ...]
    cross_section_features: tuple[EditorialTreatmentFeature, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "features", "headline_features", "lead_features", "body_features",
            "cross_section_features",
        ):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise ValueError(f"{name} must be a tuple")
            if any(not isinstance(item, EditorialTreatmentFeature) for item in value):
                raise ValueError(f"{name} contains an invalid member")
            if len(value) != len(set(value)):
                raise ValueError(f"{name} must not contain duplicates")
        if not isinstance(self.warnings, tuple):
            raise ValueError("warnings must be a tuple")
        if any(
            not isinstance(item, str) or not item or item != item.strip()
            for item in self.warnings
        ):
            raise ValueError("warnings contains an invalid member")
        if len(self.warnings) != len(set(self.warnings)):
            raise ValueError("warnings must not contain duplicates")
