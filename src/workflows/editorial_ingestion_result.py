"""Immutable result of the editorial ingestion workflow."""

from dataclasses import dataclass

from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.facts.extracted_facts import ExtractedFacts
from src.intake.normalized_source import NormalizedSource


@dataclass(frozen=True)
class EditorialIngestionResult:
    """Represent the complete result of editorial ingestion.

    Attributes:
        source: Validated and normalized source material.
        assessment: Risk assessment of the normalized source.
        facts: Facts extracted from the normalized source.
    """

    source: NormalizedSource
    assessment: SourceRiskAssessment
    facts: ExtractedFacts
