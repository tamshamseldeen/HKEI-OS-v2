import copy
import inspect
import re
import socket

import pytest

from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_decision import (
    SemanticAdjudicationDecision,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_request_builder import (
    SemanticAdjudicationNotRequiredError,
    SemanticAdjudicationRequestBuilder,
)
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import ContentTypeClassification
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
from src.intake.normalized_source import NormalizedSource
from src.semantics.compositional_semantic_evidence import (
    CompositionalSemanticEvidence,
)
from src.semantics.semantic_component import SemanticComponent
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType
from src.topic.topic import Topic
from src.topic.topic_classification import TopicClassification
from src.topic.topic_confidence import TopicConfidence


def source(*, title: str | None = "عنوان عربي", body: str = "مقدمة. تفاصيل.") -> NormalizedSource:
    return NormalizedSource(title=title, body=body, source_name="مصدر")  # type: ignore[arg-type]


def content() -> ContentTypeClassification:
    return ContentTypeClassification(
        ContentType.STANDARD_NEWS,
        ClassificationConfidence.HIGH,
        ("CONTENT_REASON",),
        ("CONTENT_SIGNAL",),
        (),
    )


def topic() -> TopicClassification:
    return TopicClassification(
        Topic.EDUCATION,
        TopicConfidence.HIGH,
        ("TOPIC_REASON", "TOPIC_REASON"),
        ("TITLE_EDUCATION_SIGNAL",),
        ("TOPIC_WARNING",),
    )


def editorial_format() -> EditorialFormatClassification:
    return EditorialFormatClassification(
        EditorialFormat.STANDARD_NEWS,
        EditorialFormatConfidence.LOW,
        ("FORMAT_REASON",),
        ("FORMAT_SIGNAL",),
        ("FORMAT_WARNING",),
    )


def item(
    index: int,
    *supports: str,
    suppresses: tuple[str, ...] = (),
    strength: EvidenceStrength = EvidenceStrength.STRONG,
) -> ContextualEvidenceItem:
    return ContextualEvidenceItem(
        SourceSection.BODY,
        index,
        "structured match",
        EvidenceLevel.CONTEXT,
        EvidenceRole.CLAIM,
        strength,
        "STRUCTURED_REASON",
        supports,
        suppresses,
    )


def context(*items: ContextualEvidenceItem) -> ContextualEvidence:
    return ContextualEvidence((), (), items, (), (), ())


def relationship(
    index: int,
    *,
    strength: EvidenceStrength = EvidenceStrength.STRONG,
    suppresses: tuple[str, ...] = (),
) -> SemanticRelationship:
    return SemanticRelationship(
        SourceSection.BODY,
        index,
        SemanticRelationshipType.ACTION_TARGETS_OBJECT,
        SemanticComponent.ACTION,
        "short subject",
        SemanticComponent.PRIMARY_SUBJECT,
        "short object",
        strength,
        "RELATIONSHIP_REASON",
        (),
        ("PRIMARY_DOMAIN_EDUCATION",),
        suppresses,
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
        relationships,
        primary,
        secondary,
        format_support,
        format_suppression,
        (),
        (),
    )


def decision(scope: AdjudicationScope) -> SemanticAdjudicationDecision:
    return SemanticAdjudicationDecision(
        scope,
        ("FORMAT_LOW_CONFIDENCE",),
        scope in (
            AdjudicationScope.TOPIC_REQUIRED,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        ),
        scope in (
            AdjudicationScope.FORMAT_REQUIRED,
            AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
        ),
        ("ADJUDICATION_REQUIRED",),
        (),
    )


def build(
    *,
    scope: AdjudicationScope = AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED,
    source_value: NormalizedSource | None = None,
    contextual: ContextualEvidence | None = None,
    semantic: CompositionalSemanticEvidence | None = None,
) -> SemanticAdjudicationRequest:
    return SemanticAdjudicationRequestBuilder().build(
        request_id="request-1",
        source=source_value or source(),
        content_classification=content(),
        topic_classification=topic(),
        format_classification=editorial_format(),
        contextual_evidence=contextual or context(),
        semantic_evidence=semantic or semantics(),
        decision=decision(scope),
    )


def test_builder_returns_request_and_rejects_not_required() -> None:
    assert isinstance(build(), SemanticAdjudicationRequest)
    with pytest.raises(SemanticAdjudicationNotRequiredError):
        build(scope=AdjudicationScope.NOT_REQUIRED)


@pytest.mark.parametrize(
    ("scope", "topic_expanded", "format_expanded"),
    (
        (AdjudicationScope.TOPIC_REQUIRED, True, False),
        (AdjudicationScope.FORMAT_REQUIRED, False, True),
        (AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED, True, True),
    ),
)
def test_scope_expands_only_required_candidates(
    scope: AdjudicationScope,
    topic_expanded: bool,
    format_expanded: bool,
) -> None:
    request = build(
        scope=scope,
        contextual=context(
            item(0, "TOPIC_SCIENCE", "TOPIC_UNKNOWN", "FORMAT_EXPLAINER")
        ),
        semantic=semantics(
            primary=("PRIMARY_DOMAIN_HEALTH", "PRIMARY_DOMAIN_HEALTH"),
            secondary=("SECONDARY_DOMAIN_SCIENCE",),
            format_support=("FORMAT_ANALYSIS", "FORMAT_ANALYSIS"),
        ),
    )
    if topic_expanded:
        assert request.candidate_topics[:3] == (
            "EDUCATION", "HEALTH", "SCIENCE"
        )
        assert set(request.candidate_topics) == {value.value for value in Topic}
        assert len(request.candidate_topics) == len(Topic)
        assert request.candidate_topics.count("GENERAL") == 1
    else:
        assert request.candidate_topics == ("EDUCATION",)
    if format_expanded:
        assert request.candidate_formats[:3] == (
            "STANDARD_NEWS", "ANALYSIS", "EXPLAINER"
        )
        assert set(request.candidate_formats) == {
            value.value for value in EditorialFormat
        }
        assert len(request.candidate_formats) == len(EditorialFormat)
    else:
        assert request.candidate_formats == ("STANDARD_NEWS",)


def test_text_is_preserved_bounded_and_missing_title_is_empty() -> None:
    body = "  هذه مقدمة عربية محفوظة.  \n\n" + "تفاصيل " * 500
    request = build(source_value=source(title=None, body=body))
    assert request.title == ""
    assert request.lead.startswith("هذه مقدمة عربية محفوظة")
    assert "هذه مقدمة عربية محفوظة" in request.body_excerpt
    assert len(request.lead) <= 500
    assert len(request.body_excerpt) <= 1800
    assert request.body_excerpt != body


def test_relationship_sentence_has_priority_and_context_is_bounded() -> None:
    filler = "س" * 700
    body = f"{filler}. سياق قبل. دليل دلالي قوي. سياق بعد. {filler}."
    request = build(
        source_value=source(body=body),
        contextual=context(item(4, "TOPIC_HEALTH")),
        semantic=semantics(relationships=(relationship(2),)),
    )
    assert "دليل دلالي قوي" in request.body_excerpt
    assert "سياق قبل" in request.body_excerpt
    assert "سياق بعد" in request.body_excerpt
    assert request.body_excerpt.count("دليل دلالي قوي") == 1
    assert request.body_excerpt.index("سياق قبل") < request.body_excerpt.index(
        "دليل دلالي قوي"
    ) < request.body_excerpt.index("سياق بعد")


def test_contextual_evidence_sentence_is_preferred_to_early_fallback() -> None:
    body = "أول. ثان. ثالث. جملة إشارة التحكيم. خامس. سادس."
    request = build(
        source_value=source(body=body),
        contextual=context(item(3, "ADJUDICATION_ANALYTICAL_CONSTRAINT")),
    )
    assert request.body_excerpt == "ثالث. جملة إشارة التحكيم. خامس."


def test_duplicate_selected_sentence_text_is_included_once() -> None:
    request = build(
        source_value=source(body="جملة مكررة. وسط. جملة مكررة."),
        contextual=context(item(0, "TOPIC_HEALTH"), item(2, "FORMAT_ANALYSIS")),
    )
    assert request.body_excerpt.count("جملة مكررة") == 1


def test_structured_evidence_and_classification_fields_are_preserved() -> None:
    contextual = context(
        item(
            0,
            "TOPIC_HEALTH",
            "TOPIC_HEALTH",
            "ADJUDICATION_HINT",
            suppresses=("FORMAT_GUIDE", "FORMAT_GUIDE"),
        )
    )
    semantic = semantics(
        relationships=(relationship(0),),
        primary=("PRIMARY_DOMAIN_HEALTH", "PRIMARY_DOMAIN_HEALTH"),
        secondary=("SECONDARY_DOMAIN_SCIENCE",),
        format_support=("FORMAT_ANALYSIS",),
        format_suppression=("FORMAT_GUIDE",),
    )
    request = build(contextual=contextual, semantic=semantic)
    assert request.contextual_support_labels == (
        "TOPIC_HEALTH",
        "ADJUDICATION_HINT",
    )
    assert request.contextual_suppressions == ("FORMAT_GUIDE",)
    assert request.semantic_relationship_summary == (
        "ACTION_TARGETS_OBJECT|ACTION|PRIMARY_SUBJECT|STRONG|RELATIONSHIP_REASON",
    )
    assert request.primary_domain_candidates == ("PRIMARY_DOMAIN_HEALTH",)
    assert request.secondary_domain_candidates == ("SECONDARY_DOMAIN_SCIENCE",)
    assert request.semantic_format_support == ("FORMAT_ANALYSIS",)
    assert request.semantic_format_suppression == ("FORMAT_GUIDE",)
    assert request.topic_reason_codes == ("TOPIC_REASON", "TOPIC_REASON")
    assert request.topic_warnings == ("TOPIC_WARNING",)
    assert request.format_reason_codes == ("FORMAT_REASON",)
    assert request.format_warnings == ("FORMAT_WARNING",)
    assert request.content_type == "STANDARD_NEWS"


def test_suppressed_format_remains_in_full_legal_universe() -> None:
    request = build(
        contextual=context(item(0, "FORMAT_GUIDE", "FORMAT_ANALYSIS")),
        semantic=semantics(format_suppression=("FORMAT_GUIDE",)),
    )
    assert "GUIDE" in request.candidate_formats
    assert request.semantic_format_suppression == ("FORMAT_GUIDE",)
    assert len(request.candidate_formats) == len(EditorialFormat)


def test_strong_relationship_suppression_does_not_prohibit_legal_format() -> None:
    request = build(
        contextual=context(
            item(0, "FORMAT_GUIDE", strength=EvidenceStrength.WEAK)
        ),
        semantic=semantics(
            relationships=(relationship(0, suppresses=("FORMAT_GUIDE",)),)
        ),
    )
    assert "GUIDE" in request.candidate_formats
    assert len(request.candidate_formats) == len(EditorialFormat)


def test_fingerprint_is_deterministic_sha256_and_changes_with_payload() -> None:
    first = build()
    second = build()
    changed_title = build(source_value=source(title="عنوان مختلف"))
    changed_candidates = build(
        contextual=context(item(0, "TOPIC_HEALTH"))
    )
    assert first == second
    assert re.fullmatch(r"[0-9a-f]{64}", first.input_fingerprint)
    assert changed_title.input_fingerprint != first.input_fingerprint
    assert changed_candidates.input_fingerprint != first.input_fingerprint


def test_inputs_are_not_mutated() -> None:
    values = (
        source(),
        content(),
        topic(),
        editorial_format(),
        context(item(0, "TOPIC_HEALTH")),
        semantics(relationships=(relationship(0),)),
        decision(AdjudicationScope.TOPIC_AND_FORMAT_REQUIRED),
    )
    snapshots = copy.deepcopy(values)
    SemanticAdjudicationRequestBuilder().build(
        request_id="immutable",
        source=values[0],
        content_classification=values[1],
        topic_classification=values[2],
        format_classification=values[3],
        contextual_evidence=values[4],
        semantic_evidence=values[5],
        decision=values[6],
    )
    assert values == snapshots


def test_request_excludes_risk_reader_intent_provider_and_secrets() -> None:
    fields = SemanticAdjudicationRequest.__dataclass_fields__
    forbidden = {
        "risk_level",
        "attribution_required",
        "uncertainty_present",
        "sensitive_context",
        "reader_intent",
        "provider",
        "model",
        "api_key",
    }
    assert forbidden.isdisjoint(fields)
    request = build()
    assert "OPENAI_API_KEY" not in repr(request)


def test_builder_is_standard_library_plus_domain_models_and_has_no_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.adjudication.semantic_adjudication_request_builder as module

    source_text = inspect.getsource(module)
    assert "benchmark" not in source_text.casefold()
    assert "provider" not in "\n".join(
        line for line in source_text.splitlines() if line.startswith(("from ", "import "))
    ).casefold()
    assert "openai" not in source_text.casefold()
    assert "os.environ" not in source_text
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("network"))
    assert build().request_id == "request-1"
