"""Immutable collection of contextual editorial evidence."""

from dataclasses import dataclass

from .contextual_evidence_item import ContextualEvidenceItem


@dataclass(frozen=True)
class ContextualEvidence:
    """Store contextual evidence in source-section order.

    Attributes:
        headline_items: Evidence produced from the source headline.
        lead_items: Evidence produced from the source lead.
        body_items: Evidence produced from the remaining source body.
        metadata_items: Evidence produced from source metadata.
        user_instruction_items: Evidence produced from a user instruction.
        warnings: Ordered warnings associated with the evidence collection.
    """

    headline_items: tuple[ContextualEvidenceItem, ...]
    lead_items: tuple[ContextualEvidenceItem, ...]
    body_items: tuple[ContextualEvidenceItem, ...]
    metadata_items: tuple[ContextualEvidenceItem, ...]
    user_instruction_items: tuple[ContextualEvidenceItem, ...]
    warnings: tuple[str, ...]

    @property
    def all_items(self) -> tuple[ContextualEvidenceItem, ...]:
        """Return every evidence item in fixed source-section order."""
        return (
            self.headline_items
            + self.lead_items
            + self.body_items
            + self.metadata_items
            + self.user_instruction_items
        )
