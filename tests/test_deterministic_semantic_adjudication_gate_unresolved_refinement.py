"""Focused tests for bounded propagation of existing unresolved Gate signals."""

from pathlib import Path

from src.adjudication.adjudication_scope import AdjudicationScope
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType
from src.semantics.semantic_component import SemanticComponent
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.topic.topic import Topic
from src.topic.topic_confidence import TopicConfidence

from tests.test_deterministic_semantic_adjudication_gate import (
    context, contextual_item, editorial_format, evaluate, relationship,
    semantics, topic,
)


def test_topic_unresolved_signal_overrides_false_resolution() -> None:
    result = evaluate(
        topic_result=topic(Topic.HEALTH, TopicConfidence.LOW),
        semantic=semantics(
            relationships=(relationship(), relationship()),
        ),
    )
    assert "SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN" in result.trigger_signals
    assert result.topic_required is True
    assert result.scope is AdjudicationScope.TOPIC_REQUIRED


def test_format_unresolved_warning_overrides_false_high_confidence() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.HIGH,
            warnings=("FORMAT_STRUCTURE_INCOMPLETE",),
        ),
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert result.format_required is True
    assert result.scope is AdjudicationScope.FORMAT_REQUIRED


def test_conflicting_format_evidence_triggers_adjudication() -> None:
    result = evaluate(
        semantic=semantics(
            primary=("PRIMARY_DOMAIN_ECONOMY",),
            format_support=("FORMAT_ANALYSIS",),
            format_suppression=("FORMAT_ANALYSIS",),
        ),
    )
    assert "FORMAT_CONFLICT" in result.trigger_signals
    assert result.format_required is True


def test_clean_well_supported_high_confidence_topic_remains_not_required() -> None:
    result = evaluate(
        topic_result=topic(Topic.ECONOMY, TopicConfidence.HIGH),
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert result.topic_required is False
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_clean_well_supported_high_confidence_format_remains_not_required() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.HIGH,
        ),
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert result.format_required is False
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_matching_semantic_format_support_protects_high_confidence_control() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.RESULT_REPORT,
            EditorialFormatConfidence.HIGH,
        ),
        contextual=context(contextual_item("FORMAT_ANALYSIS")),
        semantic=semantics(
            primary=("PRIMARY_DOMAIN_BUSINESS",),
            format_support=("FORMAT_RESULT_REPORT",),
        ),
    )
    assert "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED" in result.trigger_signals
    assert result.format_required is False
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_generic_evidence_presence_alone_does_not_escalate() -> None:
    result = evaluate(
        contextual=context(contextual_item("CLAIM_ATTRIBUTED")),
        semantic=semantics(
            primary=("PRIMARY_DOMAIN_ECONOMY",),
            relationships=(relationship(),),
        ),
    )
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_medium_format_confidence_alone_does_not_escalate() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.MEDIUM,
        ),
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert result.format_required is False
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_high_confidence_unpromoted_format_target_is_bounded_contradiction() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.HIGH,
        ),
        contextual=context(contextual_item("FORMAT_GUIDE")),
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED" in result.trigger_signals
    assert result.format_required is True


def test_provider_scope_remains_bounded_without_unresolved_structure() -> None:
    result = evaluate(
        topic_result=topic(Topic.ECONOMY, TopicConfidence.LOW),
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.MEDIUM,
        ),
        contextual=context(contextual_item("TOPIC_ECONOMY")),
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert result.topic_required is False
    assert result.format_required is False
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_refinement_contains_no_holdout_ids_or_article_phrases() -> None:
    project = Path(__file__).resolve().parents[1]
    paths = (
        project / "src/adjudication/deterministic_semantic_adjudication_gate.py",
        Path(__file__),
    )
    forbidden_ids = {f"{value:03d}" for value in range(61, 69)}
    forbidden_phrases = (
        "أسعار الذهب " + "الثلاثاء",
        "استئناف علاقاتها " + "الدبلوماسية",
        "تفشي فيروس " + "إيبولا",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert not any(case_id in source for case_id in forbidden_ids)
        assert not any(phrase in source for phrase in forbidden_phrases)
