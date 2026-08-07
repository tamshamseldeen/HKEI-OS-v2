"""Immutable contextual editorial evidence item."""

from dataclasses import dataclass

from .evidence_level import EvidenceLevel
from .evidence_role import EvidenceRole
from .evidence_strength import EvidenceStrength
from .source_section import SourceSection


@dataclass(frozen=True)
class ContextualEvidenceItem:
    """Represent one contextual evidence item with exact provenance.

    Attributes:
        source_section: Section of supplied material that produced the evidence.
        sentence_index: Index of the sentence that produced the evidence.
        matched_text: Exact supplied text matched by the future evidence engine.
        evidence_level: Deterministic evidence hierarchy level.
        role: Editorial role represented by the evidence.
        strength: Deterministic strength assigned to the evidence.
        reason_code: Stable code explaining why the evidence exists.
        supports: Ordered symbolic downstream labels supported by the evidence.
        suppresses: Ordered symbolic downstream labels suppressed by the evidence.
    """

    source_section: SourceSection
    sentence_index: int
    matched_text: str
    evidence_level: EvidenceLevel
    role: EvidenceRole
    strength: EvidenceStrength
    reason_code: str
    supports: tuple[str, ...]
    suppresses: tuple[str, ...]
