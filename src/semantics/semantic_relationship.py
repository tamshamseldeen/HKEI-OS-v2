"""Immutable compositional semantic relationship model."""

from dataclasses import dataclass

from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection

from .semantic_component import SemanticComponent
from .semantic_relationship_type import SemanticRelationshipType


@dataclass(frozen=True)
class SemanticRelationship:
    """Store one provenance-preserving relationship between components.

    Attributes:
        source_section: Structural source section containing the relationship.
        sentence_index: Zero-based local sentence index.
        relationship_type: Reusable semantic relationship type.
        subject_component: Conceptual role of the relationship subject.
        subject_text: Exact supplied subject text.
        object_component: Conceptual role of the relationship object.
        object_text: Exact supplied object text.
        strength: Deterministic evidence strength.
        reason_code: Stable reason describing the relationship.
        evidence_indexes: Zero-based indexes into ContextualEvidence.all_items.
        supports: Ordered generic symbolic support labels.
        suppresses: Ordered generic symbolic suppression labels.
    """

    source_section: SourceSection
    sentence_index: int
    relationship_type: SemanticRelationshipType
    subject_component: SemanticComponent
    subject_text: str
    object_component: SemanticComponent
    object_text: str
    strength: EvidenceStrength
    reason_code: str
    evidence_indexes: tuple[int, ...]
    supports: tuple[str, ...]
    suppresses: tuple[str, ...]
