"""Tests for the deterministic semantic adjudication gate."""

import copy
import inspect
import os
from pathlib import Path
import socket

import pytest

from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.contextual_evidence_item import ContextualEvidenceItem
from src.evidence.evidence_level import EvidenceLevel
from src.evidence.evidence_role import EvidenceRole
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.semantics.semantic_component import SemanticComponent
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence


def topic(
    value: Topic = Topic.ECONOMY,
    confidence: TopicConfidence = TopicConfidence.HIGH,
    *,
    reasons: tuple[str, ...] = ("TITLE_TOPIC_SIGNAL",),
    signals: tuple[str, ...] = ("TITLE_ECONOMY_SIGNAL",),
    warnings: tuple[str, ...] = (),
) -> TopicClassification:
    return TopicClassification(value, confidence, reasons, signals, warnings)


def editorial_format(
    value: EditorialFormat = EditorialFormat.STANDARD_NEWS,
    confidence: EditorialFormatConfidence = EditorialFormatConfidence.HIGH,
) -> EditorialFormatClassification:
    return EditorialFormatClassification(
        value,
        confidence,
        ("DEFAULT_STANDARD_NEWS_FORMAT",),
        ("EXISTING_CONTENT_TYPE_FALLBACK",),
        (),
    )


def contextual_item(
    *supports: str,
    role: EvidenceRole = EvidenceRole.CLAIM,
) -> ContextualEvidenceItem:
    return ContextualEvidenceItem(
        source_section=SourceSection.LEAD,
        sentence_index=0,
        matched_text="structured evidence only",
        evidence_level=EvidenceLevel.CONTEXT,
        role=role,
        strength=EvidenceStrength.STRONG,
        reason_code="STRUCTURED_TEST_EVIDENCE",
        supports=supports,
        suppresses=(),
    )


def context(*items: ContextualEvidenceItem) -> ContextualEvidence:
    return ContextualEvidence((), items, (), (), (), ())


def relationship(
    *,
    method: bool = False,
    supports: tuple[str, ...] = (),
    suppresses: tuple[str, ...] = (),
) -> SemanticRelationship:
    return SemanticRelationship(
        source_section=SourceSection.LEAD,
        sentence_index=0,
        relationship_type=(
            SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT
            if method
            else SemanticRelationshipType.ACTION_TARGETS_OBJECT
        ),
        subject_component=(
            SemanticComponent.METHOD if method else SemanticComponent.ACTION
        ),
        subject_text="structured subject",
        object_component=SemanticComponent.PRIMARY_SUBJECT,
        object_text="structured object",
        strength=EvidenceStrength.STRONG,
        reason_code="STRUCTURED_RELATIONSHIP",
        evidence_indexes=(0,),
        supports=supports,
        suppresses=suppresses,
    )


def semantics(
    *,
    relationships: tuple[SemanticRelationship, ...] = (),
    primary: tuple[str, ...] = (),
    secondary: tuple[str, ...] = (),
    format_support: tuple[str, ...] = (),
    format_suppression: tuple[str, ...] = (),
) -> CompositionalSemanticEvidence:
    return CompositionalSemanticEvidence(
        relationships=relationships,
        primary_domain_candidates=primary,
        secondary_domain_candidates=secondary,
        format_support=format_support,
        format_suppression=format_suppression,
        intent_support=(),
        warnings=(),
    )


def evaluate(
    *,
    topic_result: TopicClassification | None = None,
    format_result: EditorialFormatClassification | None = None,
    contextual: ContextualEvidence | None = None,
    semantic: CompositionalSemanticEvidence | None = None,
) -> SemanticAdjudicationDecision:
    return DeterministicSemanticAdjudicationGate().evaluate(
        topic_classification=topic_result or topic(),
        format_classification=format_result or editorial_format(),
        contextual_evidence=contextual or context(),
        semantic_evidence=semantic or semantics(),
    )


def test_gate_returns_decision_and_general_low_requires_topic() -> None:
    result = evaluate(
        topic_result=topic(
            Topic.GENERAL,
            TopicConfidence.LOW,
            reasons=("DEFAULT_GENERAL_TOPIC",),
            signals=("INSUFFICIENT_TOPIC_EVIDENCE",),
            warnings=("TOPIC_SIGNAL_INSUFFICIENT",),
        )
    )
    assert isinstance(result, SemanticAdjudicationDecision)
    assert result.scope is AdjudicationScope.TOPIC_REQUIRED
    assert result.topic_required is True
    assert result.format_required is False
    assert result.trigger_signals[:3] == (
        "TOPIC_LOW_CONFIDENCE",
        "TOPIC_GENERAL_FALLBACK",
        "NO_PRIMARY_SEMANTIC_DOMAIN",
    )


def test_confident_explicit_general_does_not_emit_fallback() -> None:
    result = evaluate(
        topic_result=topic(
            Topic.GENERAL,
            TopicConfidence.HIGH,
            reasons=("EXPLICIT_GENERAL_SUPPORT",),
            signals=("GENERAL_SCOPE_CONFIRMED",),
        )
    )
    assert "TOPIC_GENERAL_FALLBACK" not in result.trigger_signals
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_no_primary_domain_alone_is_supporting_only() -> None:
    result = evaluate()
    assert result.trigger_signals == ("NO_PRIMARY_SEMANTIC_DOMAIN",)
    assert result.scope is AdjudicationScope.NOT_REQUIRED
    assert result.reason_codes == ("DETERMINISTIC_RESULT_SUFFICIENT",)


def test_low_topic_and_no_primary_without_third_signal_is_insufficient() -> None:
    result = evaluate(
        topic_result=topic(Topic.HEALTH, TopicConfidence.LOW),
    )
    assert result.trigger_signals == (
        "TOPIC_LOW_CONFIDENCE",
        "NO_PRIMARY_SEMANTIC_DOMAIN",
    )
    assert result.topic_required is False


def test_context_without_relationship_alone_is_supporting_only() -> None:
    result = evaluate(contextual=context(contextual_item("CLAIM_ATTRIBUTED")))
    assert "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP" in (
        result.trigger_signals
    )
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_low_topic_plus_uncomposed_context_requires_topic() -> None:
    result = evaluate(
        topic_result=topic(Topic.HEALTH, TopicConfidence.LOW),
        contextual=context(contextual_item("CLAIM_ATTRIBUTED")),
    )
    assert result.scope is AdjudicationScope.TOPIC_REQUIRED


def test_multiple_primary_domains_create_semantic_conflict() -> None:
    result = evaluate(
        semantic=semantics(
            primary=("PRIMARY_DOMAIN_HEALTH", "PRIMARY_DOMAIN_TECHNOLOGY")
        )
    )
    assert "SEMANTIC_DOMAIN_CONFLICT" in result.trigger_signals
    assert result.scope is AdjudicationScope.TOPIC_REQUIRED


def test_supported_and_suppressed_same_domain_creates_conflict() -> None:
    relation = relationship(
        supports=("PRIMARY_DOMAIN_HEALTH",),
        suppresses=("PRIMARY_DOMAIN_HEALTH",),
    )
    result = evaluate(semantic=semantics(relationships=(relation,)))
    assert "SEMANTIC_DOMAIN_CONFLICT" in result.trigger_signals
    assert result.topic_required is True


def test_method_subject_ambiguity_uses_structured_evidence_only() -> None:
    relation = relationship(
        method=True,
        supports=("PRIMARY_DOMAIN_HEALTH",),
    )
    result = evaluate(
        topic_result=topic(Topic.TECHNOLOGY, TopicConfidence.MEDIUM),
        contextual=context(contextual_item("TOPIC_TECHNOLOGY")),
        semantic=semantics(
            relationships=(relation,),
            primary=("PRIMARY_DOMAIN_HEALTH",),
        ),
    )
    assert "METHOD_SUBJECT_AMBIGUITY" in result.trigger_signals
    assert result.scope is AdjudicationScope.TOPIC_REQUIRED


def test_multiple_competing_topic_signals_are_structurally_derived() -> None:
    relation = relationship(supports=("PRIMARY_DOMAIN_HEALTH",))
    result = evaluate(
        topic_result=topic(Topic.TECHNOLOGY, TopicConfidence.LOW),
        contextual=context(contextual_item("TOPIC_TECHNOLOGY")),
        semantic=semantics(relationships=(relation,)),
    )
    assert "MULTIPLE_COMPETING_TOPIC_SIGNALS" in result.trigger_signals
    assert result.topic_required is True


def test_contextual_analysis_support_requires_format_adjudication() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.MEDIUM,
        ),
        contextual=context(contextual_item("FORMAT_ANALYSIS")),
    )
    assert result.scope is AdjudicationScope.FORMAT_REQUIRED
    assert result.trigger_signals[-2:] == (
        "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK",
        "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED",
    )


def test_unpromoted_contextual_format_support_requires_format() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.MEDIUM,
        ),
        contextual=context(contextual_item("FORMAT_GUIDE")),
    )
    assert result.trigger_signals[-1] == (
        "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED"
    )
    assert result.format_required is True


def test_low_format_confidence_alone_does_not_adjudicate() -> None:
    result = evaluate(
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.LOW,
        ),
    )
    assert result.trigger_signals == ("FORMAT_LOW_CONFIDENCE",)
    assert result.scope is AdjudicationScope.NOT_REQUIRED


def test_prediction_and_uncertainty_alone_do_not_trigger_format() -> None:
    result = evaluate(
        semantic=semantics(primary=("PRIMARY_DOMAIN_WORLD",)),
        contextual=context(
            contextual_item("CLAIM_UNCERTAIN", role=EvidenceRole.PREDICTION),
            contextual_item("CLAIM_UNCERTAIN", role=EvidenceRole.UNCERTAINTY),
        ),
    )
    assert all("FORMAT" not in signal for signal in result.trigger_signals)
    assert result.format_required is False


def test_semantic_format_conflict_requires_format_even_at_high_confidence() -> None:
    result = evaluate(
        semantic=semantics(
            primary=("PRIMARY_DOMAIN_ECONOMY",),
            format_support=("FORMAT_ANALYSIS", "FORMAT_GUIDE"),
        )
    )
    assert "FORMAT_CONFLICT" in result.trigger_signals
    assert result.scope is AdjudicationScope.FORMAT_REQUIRED


def test_explainer_support_is_not_inferred_from_raw_text() -> None:
    signature = inspect.signature(DeterministicSemanticAdjudicationGate.evaluate)
    assert tuple(signature.parameters) == (
        "self",
        "topic_classification",
        "format_classification",
        "contextual_evidence",
        "semantic_evidence",
    )
    assert {"title", "body", "lead", "source_url"}.isdisjoint(
        signature.parameters
    )
    result = evaluate(
        semantic=semantics(primary=("PRIMARY_DOMAIN_ECONOMY",)),
    )
    assert "EXPLAINER_STRUCTURE_UNRESOLVED" not in result.trigger_signals


def test_explicit_explainer_support_can_require_format() -> None:
    result = evaluate(
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.MEDIUM,
        ),
        contextual=context(contextual_item("FORMAT_EXPLAINER")),
    )
    assert "EXPLAINER_STRUCTURE_UNRESOLVED" in result.trigger_signals
    assert result.format_required is True


def test_topic_and_format_scope_and_trigger_order_are_exact() -> None:
    result = evaluate(
        topic_result=topic(
            Topic.GENERAL,
            TopicConfidence.LOW,
            reasons=("DEFAULT_GENERAL_TOPIC",),
        ),
        format_result=editorial_format(
            EditorialFormat.STANDARD_NEWS,
            EditorialFormatConfidence.LOW,
        ),
        contextual=context(
            contextual_item("FORMAT_ANALYSIS", "FORMAT_ANALYSIS")
        ),
    )
    assert result.scope is AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED
    assert result.topic_required is result.format_required is True
    assert result.trigger_signals == (
        "TOPIC_LOW_CONFIDENCE",
        "TOPIC_GENERAL_FALLBACK",
        "NO_PRIMARY_SEMANTIC_DOMAIN",
        "CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP",
        "FORMAT_LOW_CONFIDENCE",
        "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK",
        "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED",
    )
    assert len(result.trigger_signals) == len(set(result.trigger_signals))
    assert result.reason_codes == (
        "TOPIC_AND_FORMAT_ADJUDICATION_REQUIRED",
    )
    assert result.warnings == ()


@pytest.mark.parametrize(
    ("topic_required", "format_required", "scope", "reason"),
    (
        (True, False, AdjudicationScope.TOPIC_REQUIRED, "TOPIC_ADJUDICATION_REQUIRED"),
        (False, True, AdjudicationScope.FORMAT_REQUIRED, "FORMAT_ADJUDICATION_REQUIRED"),
        (
            True,
            True,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
            "TOPIC_AND_FORMAT_ADJUDICATION_REQUIRED",
        ),
        (
            False,
            False,
            AdjudicationScope.NOT_REQUIRED,
            "DETERMINISTIC_RESULT_SUFFICIENT",
        ),
    ),
)
def test_scope_resolution_is_consistent(
    topic_required: bool,
    format_required: bool,
    scope: AdjudicationScope,
    reason: str,
) -> None:
    resolved_scope, reasons = DeterministicSemanticAdjudicationGate._resolve_scope(
        topic_required=topic_required,
        format_required=format_required,
    )
    assert resolved_scope is scope
    assert reasons == (reason,)


def test_inputs_remain_unchanged_and_identical_inputs_are_deterministic() -> None:
    topic_result = topic(Topic.GENERAL, TopicConfidence.LOW, reasons=("FALLBACK",))
    format_result = editorial_format()
    contextual = context(contextual_item("CLAIM_ATTRIBUTED"))
    semantic = semantics()
    snapshots = copy.deepcopy((topic_result, format_result, contextual, semantic))
    first = evaluate(
        topic_result=topic_result,
        format_result=format_result,
        contextual=contextual,
        semantic=semantic,
    )
    second = evaluate(
        topic_result=topic_result,
        format_result=format_result,
        contextual=contextual,
        semantic=semantic,
    )
    assert first == second
    assert (topic_result, format_result, contextual, semantic) == snapshots


def test_gate_has_no_benchmark_provider_or_api_dependencies() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "adjudication"
        / "deterministic_semantic_adjudication_gate.py"
    )
    source = path.read_text(encoding="utf-8")
    import_lines = [
        line for line in source.splitlines()
        if line.startswith(("import ", "from "))
    ]
    forbidden_imports = ("benchmark", "provider", "openai", "anthropic")
    assert not any(
        forbidden in line.casefold()
        for line in import_lines
        for forbidden in forbidden_imports
    )
    assert not any(case_id in source for case_id in (
        "041", "042", "043", "044", "045",
        "046", "047", "048", "049", "050",
    ))


def test_gate_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert evaluate().scope is AdjudicationScope.NOT_REQUIRED
