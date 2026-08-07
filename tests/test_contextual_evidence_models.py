"""Tests for immutable contextual editorial evidence models."""

from dataclasses import FrozenInstanceError, fields
from typing import get_type_hints

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.contextual_evidence_item import ContextualEvidenceItem
from src.evidence.evidence_level import EvidenceLevel
from src.evidence.evidence_role import EvidenceRole
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection


def make_item(
    matched_text: str,
    *,
    source_section: SourceSection = SourceSection.BODY,
    sentence_index: int = 0,
    supports: tuple[str, ...] = (),
    suppresses: tuple[str, ...] = (),
) -> ContextualEvidenceItem:
    """Create one evidence item with configurable identity and provenance."""
    return ContextualEvidenceItem(
        source_section=source_section,
        sentence_index=sentence_index,
        matched_text=matched_text,
        evidence_level=EvidenceLevel.CONTEXT,
        role=EvidenceRole.SUBJECT,
        strength=EvidenceStrength.STRONG,
        reason_code="CONTEXTUAL_SUBJECT_SIGNAL",
        supports=supports,
        suppresses=suppresses,
    )


def test_evidence_level_has_exact_values() -> None:
    """Expose evidence levels in exact specification order."""
    assert tuple(value.value for value in EvidenceLevel) == (
        "TOKEN",
        "PHRASE",
        "CONTEXT",
        "STRUCTURAL",
    )


def test_evidence_strength_has_exact_values() -> None:
    """Expose evidence strengths in exact specification order."""
    assert tuple(value.value for value in EvidenceStrength) == (
        "STRONG",
        "MEDIUM",
        "WEAK",
    )


def test_evidence_role_has_exact_values() -> None:
    """Expose all target roles in exact specification order."""
    assert tuple(value.value for value in EvidenceRole) == (
        "SUBJECT",
        "ACTOR",
        "ACTION",
        "AUTHORITY",
        "AFFECTED_AUDIENCE",
        "REQUIREMENT",
        "DEADLINE",
        "RESULT",
        "CONSEQUENCE",
        "WARNING",
        "NUMBER",
        "DATE",
        "LOCATION",
        "ATTRIBUTION",
        "CLAIM",
        "PREDICTION",
        "UNCERTAINTY",
        "EXPLANATION",
        "COMPARISON",
        "BACKGROUND",
        "INTERPRETATION",
    )


def test_source_section_has_exact_values() -> None:
    """Expose source sections in exact specification order."""
    assert tuple(value.value for value in SourceSection) == (
        "HEADLINE",
        "LEAD",
        "BODY",
        "METADATA",
        "USER_INSTRUCTION",
    )


def test_contextual_evidence_item_fields_and_types_are_exact() -> None:
    """Define only the required item fields in exact order and types."""
    assert tuple(field.name for field in fields(ContextualEvidenceItem)) == (
        "source_section",
        "sentence_index",
        "matched_text",
        "evidence_level",
        "role",
        "strength",
        "reason_code",
        "supports",
        "suppresses",
    )
    assert get_type_hints(ContextualEvidenceItem) == {
        "source_section": SourceSection,
        "sentence_index": int,
        "matched_text": str,
        "evidence_level": EvidenceLevel,
        "role": EvidenceRole,
        "strength": EvidenceStrength,
        "reason_code": str,
        "supports": tuple[str, ...],
        "suppresses": tuple[str, ...],
    }


def test_contextual_evidence_fields_and_types_are_exact() -> None:
    """Define only required collection fields in exact order and types."""
    assert tuple(field.name for field in fields(ContextualEvidence)) == (
        "headline_items",
        "lead_items",
        "body_items",
        "metadata_items",
        "user_instruction_items",
        "warnings",
    )
    assert get_type_hints(ContextualEvidence) == {
        "headline_items": tuple[ContextualEvidenceItem, ...],
        "lead_items": tuple[ContextualEvidenceItem, ...],
        "body_items": tuple[ContextualEvidenceItem, ...],
        "metadata_items": tuple[ContextualEvidenceItem, ...],
        "user_instruction_items": tuple[ContextualEvidenceItem, ...],
        "warnings": tuple[str, ...],
    }


def test_item_stores_all_supplied_values_and_preserves_tuples() -> None:
    """Store exact provenance and preserve duplicate symbolic labels."""
    supports = ("TOPIC_SCIENCE", "TOPIC_SCIENCE")
    suppresses = ("TOPIC_SPORTS", "TOPIC_SPORTS")
    item = ContextualEvidenceItem(
        source_section=SourceSection.LEAD,
        sentence_index=2,
        matched_text="علماء الفلك",
        evidence_level=EvidenceLevel.PHRASE,
        role=EvidenceRole.ACTOR,
        strength=EvidenceStrength.STRONG,
        reason_code="SCIENCE_ACTOR_PHRASE",
        supports=supports,
        suppresses=suppresses,
    )

    assert item.source_section is SourceSection.LEAD
    assert item.sentence_index == 2
    assert item.matched_text == "علماء الفلك"
    assert item.evidence_level is EvidenceLevel.PHRASE
    assert item.role is EvidenceRole.ACTOR
    assert item.strength is EvidenceStrength.STRONG
    assert item.reason_code == "SCIENCE_ACTOR_PHRASE"
    assert item.supports is supports
    assert item.suppresses is suppresses
    assert isinstance(item.supports, tuple)
    assert isinstance(item.suppresses, tuple)


def test_item_accepts_empty_support_and_suppression_tuples() -> None:
    """Accept empty required symbolic-label collections."""
    item = make_item("نص", supports=(), suppresses=())

    assert item.supports == ()
    assert item.suppresses == ()


def test_models_are_immutable() -> None:
    """Prevent reassignment of fields on both frozen models."""
    item = make_item("نص")
    evidence = ContextualEvidence((item,), (), (), (), (), ())

    with pytest.raises(FrozenInstanceError):
        item.matched_text = "تغيير"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evidence.headline_items = ()  # type: ignore[misc]


def test_empty_evidence_collections_are_accepted() -> None:
    """Accept empty tuples for every required evidence collection."""
    evidence = ContextualEvidence((), (), (), (), (), ())

    assert evidence.all_items == ()
    assert isinstance(evidence.all_items, tuple)


def test_all_items_preserves_section_item_and_duplicate_order() -> None:
    """Concatenate sections without sorting or deduplicating their items."""
    headline_first = make_item("headline-first", source_section=SourceSection.HEADLINE)
    headline_second = make_item(
        "headline-second",
        source_section=SourceSection.HEADLINE,
    )
    lead = make_item("lead", source_section=SourceSection.LEAD)
    body = make_item("body", source_section=SourceSection.BODY)
    metadata = make_item("metadata", source_section=SourceSection.METADATA)
    instruction = make_item(
        "instruction",
        source_section=SourceSection.USER_INSTRUCTION,
    )
    headline_items = (headline_first, headline_second, headline_first)
    evidence = ContextualEvidence(
        headline_items=headline_items,
        lead_items=(lead,),
        body_items=(body,),
        metadata_items=(metadata,),
        user_instruction_items=(instruction,),
        warnings=(),
    )

    assert evidence.all_items == (
        headline_first,
        headline_second,
        headline_first,
        lead,
        body,
        metadata,
        instruction,
    )
    assert isinstance(evidence.all_items, tuple)
    assert evidence.headline_items is headline_items


def test_all_items_does_not_mutate_source_tuples() -> None:
    """Leave every source section tuple unchanged after aggregation."""
    item = make_item("evidence")
    sections = ((item,), (item,), (item,), (item,), (item,))
    evidence = ContextualEvidence(*sections, warnings=())

    first = evidence.all_items
    second = evidence.all_items

    assert first == second == (item,) * 5
    assert (
        evidence.headline_items,
        evidence.lead_items,
        evidence.body_items,
        evidence.metadata_items,
        evidence.user_instruction_items,
    ) == sections


def test_warnings_preserve_tuple_and_duplicates() -> None:
    """Store supplied warning tuples unchanged, including duplicates."""
    warnings = ("EVIDENCE_CONFLICT", "EVIDENCE_CONFLICT")
    evidence = ContextualEvidence((), (), (), (), (), warnings)

    assert evidence.warnings is warnings
    assert isinstance(evidence.warnings, tuple)


def test_models_do_not_contain_classification_decision_fields() -> None:
    """Keep evidence contracts independent from downstream decisions."""
    prohibited = {
        "topic",
        "primary_topic",
        "editorial_format",
        "reader_intent",
        "risk_level",
        "confidence",
        "final_decision",
    }

    assert prohibited.isdisjoint(
        field.name for field in fields(ContextualEvidenceItem)
    )
    assert prohibited.isdisjoint(field.name for field in fields(ContextualEvidence))
