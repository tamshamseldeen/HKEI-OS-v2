"""Tests for immutable compositional semantic evidence models."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.semantics.semantic_component import SemanticComponent
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType


def make_relationship(
    *,
    subject_text: str = "وزارة الصحة",
    object_text: str = "الفحوصات الطبية",
    evidence_indexes: tuple[int, ...] = (1, 2),
    supports: tuple[str, ...] = ("PRIMARY_DOMAIN_HEALTH",),
    suppresses: tuple[str, ...] = ("PRIMARY_DOMAIN_GOVERNMENT",),
) -> SemanticRelationship:
    """Create one representative semantic relationship."""
    return SemanticRelationship(
        source_section=SourceSection.LEAD,
        sentence_index=0,
        relationship_type=SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT,
        subject_component=SemanticComponent.AUTHORITY,
        subject_text=subject_text,
        object_component=SemanticComponent.PRIMARY_SUBJECT,
        object_text=object_text,
        strength=EvidenceStrength.STRONG,
        reason_code="AUTHORITY_SUBJECT_COMPOSITION",
        evidence_indexes=evidence_indexes,
        supports=supports,
        suppresses=suppresses,
    )


def make_evidence(
    relationships: tuple[SemanticRelationship, ...] = (),
    *,
    primary: tuple[str, ...] = (),
    secondary: tuple[str, ...] = (),
    format_support: tuple[str, ...] = (),
    format_suppression: tuple[str, ...] = (),
    intent_support: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> CompositionalSemanticEvidence:
    """Create a semantic evidence collection with configurable tuples."""
    return CompositionalSemanticEvidence(
        relationships=relationships,
        primary_domain_candidates=primary,
        secondary_domain_candidates=secondary,
        format_support=format_support,
        format_suppression=format_suppression,
        intent_support=intent_support,
        warnings=warnings,
    )


def test_semantic_component_has_exact_values() -> None:
    """Expose only the specified conceptual semantic components in order."""
    assert tuple(component.value for component in SemanticComponent) == (
        "AUTHORITY",
        "ACTOR",
        "PRIMARY_SUBJECT",
        "SECONDARY_SUBJECT",
        "ACTION",
        "OBJECT",
        "METHOD",
        "TOOL",
        "DOMAIN",
        "EVENT",
        "INDICATOR",
        "OUTCOME",
        "AFFECTED_AUDIENCE",
        "RECOMMENDED_ACTION",
        "REQUIREMENT",
        "DEADLINE",
        "LOCATION",
        "ATTRIBUTION",
        "CLAIM",
        "PREDICTION",
        "UNCERTAINTY",
        "INTERPRETATION",
        "CONSEQUENCE",
    )


def test_semantic_relationship_type_has_exact_values() -> None:
    """Expose only the specified compositional relationship types in order."""
    assert tuple(value.value for value in SemanticRelationshipType) == (
        "AUTHORITY_ACTS_ON_SUBJECT",
        "ACTOR_PERFORMS_ACTION",
        "ACTION_TARGETS_OBJECT",
        "METHOD_APPLIED_TO_SUBJECT",
        "TOOL_USED_FOR_TASK",
        "EVENT_HAS_OUTCOME",
        "INDICATOR_DESCRIBES_DOMAIN",
        "SUBJECT_BELONGS_TO_DOMAIN",
        "INSTITUTION_BELONGS_TO_DOMAIN",
        "RECOMMENDATION_TARGETS_AUDIENCE",
        "REQUIREMENT_APPLIES_TO_AUDIENCE",
        "ACTION_HAS_DEADLINE",
        "CLAIM_ATTRIBUTED_TO_AUTHORITY",
        "PREDICTION_ABOUT_EVENT",
        "INTERPRETATION_OF_INDICATOR",
        "CONSEQUENCE_OF_EVENT",
    )


def test_models_have_exact_field_order() -> None:
    """Preserve the exact public field contracts for both dataclasses."""
    assert tuple(field.name for field in fields(SemanticRelationship)) == (
        "source_section",
        "sentence_index",
        "relationship_type",
        "subject_component",
        "subject_text",
        "object_component",
        "object_text",
        "strength",
        "reason_code",
        "evidence_indexes",
        "supports",
        "suppresses",
    )
    assert tuple(field.name for field in fields(CompositionalSemanticEvidence)) == (
        "relationships",
        "primary_domain_candidates",
        "secondary_domain_candidates",
        "format_support",
        "format_suppression",
        "intent_support",
        "warnings",
    )


def test_relationship_preserves_text_tuples_and_duplicates() -> None:
    """Store exact text and ordered tuple values without model validation."""
    relationship = make_relationship(
        subject_text="  subject text  ",
        object_text="object text",
        evidence_indexes=(2, 2, 1),
        supports=("SUPPORT", "SUPPORT"),
        suppresses=("SUPPRESS", "SUPPRESS"),
    )

    assert relationship.subject_text == "  subject text  "
    assert relationship.object_text == "object text"
    assert relationship.evidence_indexes == (2, 2, 1)
    assert relationship.supports == ("SUPPORT", "SUPPORT")
    assert relationship.suppresses == ("SUPPRESS", "SUPPRESS")
    assert isinstance(relationship.evidence_indexes, tuple)
    assert isinstance(relationship.supports, tuple)
    assert isinstance(relationship.suppresses, tuple)


def test_relationship_accepts_empty_support_and_suppression() -> None:
    """Accept empty symbolic evidence tuples without optional fields."""
    relationship = make_relationship(supports=(), suppresses=())

    assert relationship.supports == ()
    assert relationship.suppresses == ()


def test_relationship_is_immutable() -> None:
    """Prevent reassignment of semantic relationship fields."""
    relationship = make_relationship()

    with pytest.raises(FrozenInstanceError):
        relationship.subject_text = "changed"  # type: ignore[misc]


def test_evidence_preserves_relationship_and_candidate_tuple_order() -> None:
    """Store every collection as an ordered tuple with duplicates intact."""
    first = make_relationship(subject_text="first")
    second = make_relationship(subject_text="second")
    evidence = make_evidence(
        (first, second, first),
        primary=("HEALTH", "HEALTH"),
        secondary=("TECHNOLOGY", "TECHNOLOGY"),
        format_support=("FORMAT_SERVICE", "FORMAT_SERVICE"),
        format_suppression=("FORMAT_GUIDE", "FORMAT_GUIDE"),
        intent_support=("INTENT_KNOW_ACTION", "INTENT_KNOW_ACTION"),
        warnings=("WARNING", "WARNING"),
    )

    assert evidence.relationships == (first, second, first)
    assert evidence.primary_domain_candidates == ("HEALTH", "HEALTH")
    assert evidence.secondary_domain_candidates == ("TECHNOLOGY", "TECHNOLOGY")
    assert evidence.format_support == ("FORMAT_SERVICE", "FORMAT_SERVICE")
    assert evidence.format_suppression == ("FORMAT_GUIDE", "FORMAT_GUIDE")
    assert evidence.intent_support == ("INTENT_KNOW_ACTION", "INTENT_KNOW_ACTION")
    assert evidence.warnings == ("WARNING", "WARNING")
    assert all(
        isinstance(value, tuple)
        for value in (
            evidence.relationships,
            evidence.primary_domain_candidates,
            evidence.secondary_domain_candidates,
            evidence.format_support,
            evidence.format_suppression,
            evidence.intent_support,
            evidence.warnings,
        )
    )


def test_evidence_accepts_empty_tuples_and_is_immutable() -> None:
    """Accept an empty collection and prevent field reassignment."""
    evidence = make_evidence()

    assert evidence.relationships == ()
    assert evidence.warnings == ()
    with pytest.raises(FrozenInstanceError):
        evidence.warnings = ("changed",)  # type: ignore[misc]


def test_all_supports_preserves_required_order_without_deduplication() -> None:
    """Aggregate relationship and collection supports in contract order."""
    first = make_relationship(supports=("A", "D"), suppresses=())
    second = make_relationship(supports=("A", "B"), suppresses=())
    evidence = make_evidence(
        (first, second),
        primary=("P", "A"),
        secondary=("S",),
        format_support=("F",),
        intent_support=("I", "I"),
    )

    assert evidence.all_supports == (
        "A",
        "D",
        "A",
        "B",
        "P",
        "A",
        "S",
        "F",
        "I",
        "I",
    )
    assert isinstance(evidence.all_supports, tuple)


def test_all_suppressions_preserves_required_order_without_deduplication() -> None:
    """Aggregate relationship and format suppressions in contract order."""
    first = make_relationship(supports=(), suppresses=("A", "A"))
    second = make_relationship(supports=(), suppresses=("B",))
    evidence = make_evidence(
        (first, second),
        format_suppression=("A", "F"),
    )

    assert evidence.all_suppressions == ("A", "A", "B", "A", "F")
    assert isinstance(evidence.all_suppressions, tuple)


def test_models_exclude_final_classification_fields() -> None:
    """Keep both semantic models independent from final classifications."""
    forbidden = {
        "topic",
        "editorial_format",
        "reader_intent",
        "risk_level",
        "confidence",
        "final_decision",
        "primary_topic",
    }

    assert forbidden.isdisjoint(field.name for field in fields(SemanticRelationship))
    assert forbidden.isdisjoint(
        field.name for field in fields(CompositionalSemanticEvidence)
    )
