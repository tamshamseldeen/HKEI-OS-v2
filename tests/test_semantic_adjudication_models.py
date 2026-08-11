"""Tests for provider-agnostic semantic adjudication domain models."""

from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import get_type_hints

import pytest

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)


DECISION_FIELDS = (
    "scope",
    "trigger_signals",
    "topic_required",
    "format_required",
    "reason_codes",
    "warnings",
)
REQUEST_FIELDS = (
    "request_id",
    "title",
    "lead",
    "body_excerpt",
    "deterministic_topic",
    "topic_confidence",
    "deterministic_format",
    "format_confidence",
    "content_type",
    "contextual_support_labels",
    "contextual_suppressions",
    "semantic_relationship_summary",
    "primary_domain_candidates",
    "secondary_domain_candidates",
    "semantic_format_support",
    "semantic_format_suppression",
    "topic_reason_codes",
    "topic_warnings",
    "format_reason_codes",
    "format_warnings",
    "candidate_topics",
    "candidate_formats",
    "input_fingerprint",
)
RESPONSE_FIELDS = (
    "adjudicated_topic",
    "adjudicated_format",
    "topic_confidence",
    "format_confidence",
    "topic_reason",
    "format_reason",
    "topic_evidence_refs",
    "format_evidence_refs",
    "ambiguity_remaining",
    "warnings",
    "provider",
    "model",
    "request_schema_version",
    "response_schema_version",
    "input_fingerprint",
    "usage_input_tokens",
    "usage_output_tokens",
)


def make_decision() -> SemanticAdjudicationDecision:
    """Create a decision with ordered duplicate symbolic evidence."""
    return SemanticAdjudicationDecision(
        scope=AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        trigger_signals=("TOPIC_LOW_CONFIDENCE", "TOPIC_LOW_CONFIDENCE"),
        topic_required=True,
        format_required=True,
        reason_codes=("COMBINED_TRIGGER", "COMBINED_TRIGGER"),
        warnings=("GATE_WARNING", "GATE_WARNING"),
    )


def make_request() -> SemanticAdjudicationRequest:
    """Create a representative minimal-text adjudication request."""
    return SemanticAdjudicationRequest(
        request_id="request-001",
        title="Headline",
        lead="Lead",
        body_excerpt="Selected sentence.",
        deterministic_topic="GENERAL",
        topic_confidence="LOW",
        deterministic_format="STANDARD_NEWS",
        format_confidence="LOW",
        content_type="NEWS",
        contextual_support_labels=("CLAIM_ATTRIBUTED", "CLAIM_ATTRIBUTED"),
        contextual_suppressions=("FORMAT_GUIDE", "FORMAT_GUIDE"),
        semantic_relationship_summary=(
            "AUTHORITY_ACTS_ON_SUBJECT",
            "AUTHORITY_ACTS_ON_SUBJECT",
        ),
        primary_domain_candidates=("PRIMARY_DOMAIN_POLITICS",) * 2,
        secondary_domain_candidates=("SECONDARY_DOMAIN_WORLD",) * 2,
        semantic_format_support=("FORMAT_ANALYSIS",) * 2,
        semantic_format_suppression=("FORMAT_STANDARD_NEWS",) * 2,
        topic_reason_codes=("DEFAULT_GENERAL_TOPIC",) * 2,
        topic_warnings=("LOW_TOPIC_CONFIDENCE",) * 2,
        format_reason_codes=("DEFAULT_STANDARD_NEWS_FORMAT",) * 2,
        format_warnings=("LOW_EDITORIAL_FORMAT_CONFIDENCE",) * 2,
        candidate_topics=("POLITICS", "WORLD", "POLITICS"),
        candidate_formats=("ANALYSIS", "STANDARD_NEWS", "ANALYSIS"),
        input_fingerprint="sha256:request-fingerprint",
    )


def make_response() -> SemanticAdjudicationResponse:
    """Create a representative structured adjudication response."""
    return SemanticAdjudicationResponse(
        adjudicated_topic="POLITICS",
        adjudicated_format="ANALYSIS",
        topic_confidence=AdjudicationConfidence.HIGH,
        format_confidence=AdjudicationConfidence.MEDIUM,
        topic_reason="Primary event is political.",
        format_reason="The source sustains cause and consequence analysis.",
        topic_evidence_refs=("HEADLINE", "CONTEXTUAL_ITEM_4", "HEADLINE"),
        format_evidence_refs=(
            "LEAD",
            "BODY_SENTENCE_2",
            "SEMANTIC_RELATIONSHIP_1",
        ),
        ambiguity_remaining=False,
        warnings=("PROVIDER_WARNING", "PROVIDER_WARNING"),
        provider="provider-adapter",
        model="provider-model",
        request_schema_version="1",
        response_schema_version="1",
        input_fingerprint="sha256:request-fingerprint",
        usage_input_tokens=123,
        usage_output_tokens=45,
    )


def test_adjudication_scope_has_exact_values() -> None:
    assert tuple(scope.value for scope in AdjudicationScope) == (
        "NOT_REQUIRED",
        "TOPIC_REQUIRED",
        "FORMAT_REQUIRED",
        "TOPIC_AND_FORMAT_REQUIRED",
    )


def test_adjudication_confidence_has_exact_values() -> None:
    assert tuple(confidence.value for confidence in AdjudicationConfidence) == (
        "HIGH",
        "MEDIUM",
        "LOW",
    )


def test_models_have_exact_field_order() -> None:
    assert tuple(field.name for field in fields(SemanticAdjudicationDecision)) == (
        DECISION_FIELDS
    )
    assert tuple(field.name for field in fields(SemanticAdjudicationRequest)) == (
        REQUEST_FIELDS
    )
    assert tuple(field.name for field in fields(SemanticAdjudicationResponse)) == (
        RESPONSE_FIELDS
    )


@pytest.mark.parametrize(
    ("instance", "field_name", "replacement"),
    (
        (make_decision(), "topic_required", False),
        (make_request(), "title", "Changed"),
        (make_response(), "adjudicated_topic", "WORLD"),
    ),
)
def test_models_are_immutable(
    instance: object,
    field_name: str,
    replacement: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(instance, field_name, replacement)


def test_decision_preserves_ordered_duplicate_tuples() -> None:
    decision = make_decision()
    assert decision.trigger_signals == (
        "TOPIC_LOW_CONFIDENCE",
        "TOPIC_LOW_CONFIDENCE",
    )
    assert decision.reason_codes == ("COMBINED_TRIGGER", "COMBINED_TRIGGER")
    assert decision.warnings == ("GATE_WARNING", "GATE_WARNING")
    assert all(
        isinstance(value, tuple)
        for value in (
            decision.trigger_signals,
            decision.reason_codes,
            decision.warnings,
        )
    )


def test_request_preserves_every_ordered_tuple() -> None:
    request = make_request()
    tuple_fields = (
        "contextual_support_labels",
        "contextual_suppressions",
        "semantic_relationship_summary",
        "primary_domain_candidates",
        "secondary_domain_candidates",
        "semantic_format_support",
        "semantic_format_suppression",
        "topic_reason_codes",
        "topic_warnings",
        "format_reason_codes",
        "format_warnings",
        "candidate_topics",
        "candidate_formats",
    )
    assert all(isinstance(getattr(request, name), tuple) for name in tuple_fields)
    assert request.contextual_support_labels == (
        "CLAIM_ATTRIBUTED",
        "CLAIM_ATTRIBUTED",
    )
    assert request.contextual_suppressions == ("FORMAT_GUIDE", "FORMAT_GUIDE")
    assert request.semantic_relationship_summary == (
        "AUTHORITY_ACTS_ON_SUBJECT",
        "AUTHORITY_ACTS_ON_SUBJECT",
    )
    assert request.primary_domain_candidates == ("PRIMARY_DOMAIN_POLITICS",) * 2
    assert request.secondary_domain_candidates == ("SECONDARY_DOMAIN_WORLD",) * 2
    assert request.semantic_format_support == ("FORMAT_ANALYSIS",) * 2
    assert request.semantic_format_suppression == ("FORMAT_STANDARD_NEWS",) * 2
    assert request.topic_reason_codes == ("DEFAULT_GENERAL_TOPIC",) * 2
    assert request.format_reason_codes == ("DEFAULT_STANDARD_NEWS_FORMAT",) * 2
    assert request.candidate_topics == ("POLITICS", "WORLD", "POLITICS")
    assert request.candidate_formats == (
        "ANALYSIS",
        "STANDARD_NEWS",
        "ANALYSIS",
    )
    assert request.input_fingerprint == "sha256:request-fingerprint"


def test_response_preserves_evidence_warnings_usage_and_fingerprint() -> None:
    response = make_response()
    assert response.topic_evidence_refs == (
        "HEADLINE",
        "CONTEXTUAL_ITEM_4",
        "HEADLINE",
    )
    assert response.format_evidence_refs == (
        "LEAD",
        "BODY_SENTENCE_2",
        "SEMANTIC_RELATIONSHIP_1",
    )
    assert response.warnings == ("PROVIDER_WARNING", "PROVIDER_WARNING")
    assert isinstance(response.topic_evidence_refs, tuple)
    assert isinstance(response.format_evidence_refs, tuple)
    assert isinstance(response.warnings, tuple)
    assert response.usage_input_tokens == 123
    assert response.usage_output_tokens == 45
    assert response.input_fingerprint == "sha256:request-fingerprint"


def test_all_multivalue_annotations_are_tuples() -> None:
    expected_tuple_fields = {
        SemanticAdjudicationDecision: {
            "trigger_signals",
            "reason_codes",
            "warnings",
        },
        SemanticAdjudicationRequest: {
            name
            for name in REQUEST_FIELDS
            if name
            in {
                "contextual_support_labels",
                "contextual_suppressions",
                "semantic_relationship_summary",
                "primary_domain_candidates",
                "secondary_domain_candidates",
                "semantic_format_support",
                "semantic_format_suppression",
                "topic_reason_codes",
                "topic_warnings",
                "format_reason_codes",
                "format_warnings",
                "candidate_topics",
                "candidate_formats",
            }
        },
        SemanticAdjudicationResponse: {
            "topic_evidence_refs",
            "format_evidence_refs",
            "warnings",
        },
    }
    for model, tuple_fields in expected_tuple_fields.items():
        hints = get_type_hints(model)
        assert all(hints[name] == tuple[str, ...] for name in tuple_fields)


def test_request_excludes_forbidden_fields() -> None:
    forbidden = {
        "full_body",
        "raw_article",
        "source_html",
        "attachments",
        "images",
        "risk",
        "attribution",
        "uncertainty",
        "benchmark_labels",
        "expected_topic",
        "expected_format",
        "api_key",
        "base_url",
        "temperature",
        "max_tokens",
        "timeout",
        "retries",
        "metadata",
    }
    assert forbidden.isdisjoint(REQUEST_FIELDS)
    assert set(REQUEST_FIELDS) == set(get_type_hints(SemanticAdjudicationRequest))


def test_response_excludes_resolution_intent_and_raw_provider_fields() -> None:
    forbidden = {
        "resolved_topic",
        "resolved_format",
        "final_topic",
        "final_format",
        "reader_intent",
        "risk",
        "attribution",
        "uncertainty",
        "generation_strategy",
        "raw_provider_response",
        "raw_response",
        "provider_payload",
        "timestamp",
        "retries",
        "metadata",
    }
    assert forbidden.isdisjoint(RESPONSE_FIELDS)
    assert set(RESPONSE_FIELDS) == set(get_type_hints(SemanticAdjudicationResponse))


def test_adjudication_package_has_only_allowed_imports() -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "adjudication"
    import_lines = [
        line
        for path in package_root.glob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith(("import ", "from "))
    ]
    forbidden = (
        "src.topic",
        "src.formatting",
        "src.intent",
        "src.assessment",
        "src.evidence",
        "src.semantics",
        "openai",
        "anthropic",
        "provider",
    )
    assert not any(
        value in line.casefold() for line in import_lines for value in forbidden
    )
