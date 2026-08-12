"""Tests for deterministic candidate-relative semantic assessment."""

from dataclasses import replace
from pathlib import Path

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import DeterministicContextualEvidenceEngine
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.evidence_level import EvidenceLevel
from src.evidence.contextual_evidence_item import ContextualEvidenceItem
from src.evidence.evidence_role import EvidenceRole
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource
from src.semantics.compositional_semantic_evidence import CompositionalSemanticEvidence
from src.semantics.deterministic_compositional_semantic_engine import DeterministicCompositionalSemanticEngine
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor
from src.semantics.semantic_component import SemanticComponent
from src.semantics.semantic_evidence_direction import SemanticEvidenceDirection
from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength
from src.semantics.semantic_evidence_sufficiency import SemanticEvidenceSufficiency
from src.semantics.semantic_relationship import SemanticRelationship
from src.semantics.semantic_relationship_type import SemanticRelationshipType


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def relation(
    *,
    supports: tuple[str, ...] = (),
    suppresses: tuple[str, ...] = (),
    relationship_type: SemanticRelationshipType = SemanticRelationshipType.SUBJECT_BELONGS_TO_DOMAIN,
    subject: SemanticComponent = SemanticComponent.PRIMARY_SUBJECT,
    object_: SemanticComponent = SemanticComponent.DOMAIN,
    sentence_index: int = 0,
    reason_code: str = "GENERIC_TEST_RELATIONSHIP",
    strength: EvidenceStrength = EvidenceStrength.STRONG,
    object_text: str = "DOMAIN",
) -> SemanticRelationship:
    return SemanticRelationship(
        source_section=SourceSection.LEAD,
        sentence_index=sentence_index,
        relationship_type=relationship_type,
        subject_component=subject,
        subject_text="symbolic-subject",
        object_component=object_,
        object_text=object_text,
        strength=strength,
        reason_code=reason_code,
        evidence_indexes=(),
        supports=supports,
        suppresses=suppresses,
    )


def evidence(*relationships: SemanticRelationship, **changes: object) -> CompositionalSemanticEvidence:
    values = {
        "relationships": relationships,
        "primary_domain_candidates": (),
        "secondary_domain_candidates": (),
        "format_support": (),
        "format_suppression": (),
        "intent_support": (),
        "warnings": (),
    }
    values.update(changes)
    return CompositionalSemanticEvidence(**values)  # type: ignore[arg-type]


def assess(*relationships: SemanticRelationship, **changes: object):
    return DeterministicSemanticCandidateAssessor().assess(
        semantic_evidence=evidence(*relationships, **changes)
    )


def one(*relationships: SemanticRelationship, **changes: object):
    values = assess(*relationships, **changes)
    assert len(values) == 1
    return values[0]


def test_support_only_direction() -> None:
    assert one(relation(supports=("PRIMARY_DOMAIN_HEALTH",))).direction is SemanticEvidenceDirection.SUPPORT


def test_suppression_only_direction() -> None:
    assert one(relation(suppresses=("PRIMARY_DOMAIN_HEALTH",))).direction is SemanticEvidenceDirection.SUPPRESS


def test_neutral_direction_from_related_nondiscriminating_relationship() -> None:
    result = one(relation(object_text="PRIMARY_DOMAIN_HEALTH"))
    assert result.direction is SemanticEvidenceDirection.NEUTRAL
    assert result.strength is SemanticEvidenceStrength.WEAK
    assert result.sufficiency is SemanticEvidenceSufficiency.INSUFFICIENT


def test_support_and_suppression_are_conflicted() -> None:
    result = one(relation(
        supports=("FORMAT_TREND_UPDATE",), suppresses=("FORMAT_TREND_UPDATE",)
    ))
    assert result.direction is SemanticEvidenceDirection.CONFLICTING
    assert result.sufficiency is SemanticEvidenceSufficiency.CONFLICTED
    assert "SUPPORT_SUPPRESSION_CONFLICT" in result.warnings


def test_isolated_noncentral_evidence_is_weak_and_insufficient() -> None:
    result = one(relation(
        supports=("PRIMARY_DOMAIN_GOVERNMENT",),
        subject=SemanticComponent.AUTHORITY, object_=SemanticComponent.ACTION,
    ))
    assert (result.strength, result.sufficiency) == (
        SemanticEvidenceStrength.WEAK, SemanticEvidenceSufficiency.INSUFFICIENT,
    )


def test_one_subject_bearing_relationship_is_moderate_partial() -> None:
    result = one(relation(supports=("PRIMARY_DOMAIN_HEALTH",)))
    assert (result.strength, result.sufficiency) == (
        SemanticEvidenceStrength.MODERATE, SemanticEvidenceSufficiency.PARTIAL,
    )


def test_multiple_independent_subject_relationships_are_strong_sufficient() -> None:
    first = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    second = replace(first, sentence_index=1, reason_code="INDEPENDENT_HEALTH_STATE")
    result = one(first, second)
    assert (result.strength, result.sufficiency) == (
        SemanticEvidenceStrength.STRONG, SemanticEvidenceSufficiency.SUFFICIENT,
    )


def test_exact_duplicate_evidence_does_not_inflate_strength() -> None:
    item = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    result = one(item, item)
    assert result.strength is SemanticEvidenceStrength.MODERATE
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert "DUPLICATE_EVIDENCE_DISCOUNTED" in result.warnings


@pytest.mark.parametrize(
    ("role", "warning"),
    (
        (SemanticComponent.AUTHORITY, "AUTHORITY_DOMINATED"),
        (SemanticComponent.ACTOR, "ACTOR_DOMINATED"),
        (SemanticComponent.METHOD, "METHOD_DOMINATED"),
    ),
)
def test_secondary_role_only_support_never_resolves(
    role: SemanticComponent, warning: str,
) -> None:
    result = one(relation(
        supports=("PRIMARY_DOMAIN_TECHNOLOGY",), subject=role, object_=role,
    ))
    assert result.strength is SemanticEvidenceStrength.WEAK
    assert result.sufficiency is SemanticEvidenceSufficiency.INSUFFICIENT
    assert warning in result.warnings


def test_subject_bearing_support_outranks_authority_role_risk() -> None:
    authority = relation(
        supports=("PRIMARY_DOMAIN_HEALTH",), subject=SemanticComponent.AUTHORITY,
        object_=SemanticComponent.ACTION,
    )
    subject = replace(
        authority, sentence_index=1, subject_component=SemanticComponent.PRIMARY_SUBJECT,
        object_component=SemanticComponent.DOMAIN, reason_code="CENTRAL_SUBJECT",
    )
    result = one(authority, subject)
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert "AUTHORITY_DOMINATED" not in result.warnings


def test_comparable_domain_candidates_are_recorded_and_prevent_sufficiency() -> None:
    health = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    economy = replace(
        health, supports=("PRIMARY_DOMAIN_ECONOMY",), sentence_index=1,
        reason_code="ECONOMY_SUBJECT",
    )
    results = {item.candidate: item for item in assess(health, economy)}
    assert results["HEALTH"].competing_candidates == ("ECONOMY",)
    assert results["ECONOMY"].competing_candidates == ("HEALTH",)
    assert all(item.sufficiency is SemanticEvidenceSufficiency.PARTIAL for item in results.values())


def test_weak_competitor_is_ignored() -> None:
    strong = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    strong_2 = replace(strong, sentence_index=1, reason_code="SECOND_HEALTH_SUPPORT")
    weak = relation(
        supports=("PRIMARY_DOMAIN_GOVERNMENT",), subject=SemanticComponent.AUTHORITY,
        object_=SemanticComponent.AUTHORITY, sentence_index=2,
    )
    results = {item.candidate: item for item in assess(strong, strong_2, weak)}
    assert results["HEALTH"].competing_candidates == ()
    assert results["HEALTH"].sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_candidate_is_never_listed_as_its_own_competitor() -> None:
    item = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    assert "HEALTH" not in one(item).competing_candidates


def test_candidates_are_sorted_lexically_and_not_full_enum_generated() -> None:
    results = assess(
        relation(supports=("FORMAT_TREND_UPDATE",)),
        relation(supports=("PRIMARY_DOMAIN_HEALTH",), sentence_index=1),
    )
    assert tuple(item.candidate for item in results) == ("HEALTH", "TREND_UPDATE")


def test_symbolic_provenance_is_unique_and_contains_no_source_text() -> None:
    result = one(relation(supports=("PRIMARY_DOMAIN_HEALTH",)))
    assert result.supporting_relationship_types == ("SUBJECT_BELONGS_TO_DOMAIN",)
    assert result.suppressing_relationship_types == ()
    assert result.role_basis == ("SUBJECT", "DOMAIN")


def test_collection_only_candidate_presence_is_not_sufficient() -> None:
    result = one(primary_domain_candidates=("PRIMARY_DOMAIN_HEALTH",))
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.strength is SemanticEvidenceStrength.WEAK
    assert result.sufficiency is SemanticEvidenceSufficiency.INSUFFICIENT


def test_effect_only_analysis_is_strong_but_structurally_partial() -> None:
    item = relation(
        supports=("FORMAT_ANALYSIS",),
        relationship_type=SemanticRelationshipType.CONSEQUENCE_OF_EVENT,
        subject=SemanticComponent.EVENT, object_=SemanticComponent.CONSEQUENCE,
    )
    result = one(item, replace(item, sentence_index=1, reason_code="SECOND_CAUSAL_CHAIN"))
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert "FORMAT_STRUCTURE_INCOMPLETE" in result.warnings


def test_static_measurement_is_not_sufficient_for_trend() -> None:
    result = one(relation(
        supports=("FORMAT_TREND_UPDATE",),
        relationship_type=SemanticRelationshipType.INTERPRETATION_OF_INDICATOR,
        subject=SemanticComponent.INDICATOR, object_=SemanticComponent.INTERPRETATION,
    ))
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL


def test_completed_result_relationship_is_structurally_sufficient() -> None:
    result = one(relation(
        supports=("FORMAT_RESULT_REPORT",),
        relationship_type=SemanticRelationshipType.EVENT_HAS_OUTCOME,
        subject=SemanticComponent.EVENT, object_=SemanticComponent.OUTCOME,
    ))
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_incomplete_fact_check_structure_is_not_sufficient() -> None:
    result = one(relation(
        supports=("FORMAT_FACT_CHECK",),
        relationship_type=SemanticRelationshipType.CLAIM_ATTRIBUTED_TO_AUTHORITY,
        subject=SemanticComponent.CLAIM, object_=SemanticComponent.AUTHORITY,
    ))
    assert result.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT


@pytest.mark.parametrize(
    ("candidate", "relationship_type", "subject", "object_"),
    (
        ("GUIDE", SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE, SemanticComponent.RECOMMENDED_ACTION, SemanticComponent.AFFECTED_AUDIENCE),
        ("SERVICE", SemanticRelationshipType.ACTION_HAS_DEADLINE, SemanticComponent.ACTION, SemanticComponent.DEADLINE),
    ),
)
def test_guide_and_service_keep_distinct_provenance(
    candidate: str,
    relationship_type: SemanticRelationshipType,
    subject: SemanticComponent,
    object_: SemanticComponent,
) -> None:
    result = one(relation(
        supports=(f"FORMAT_{candidate}",), relationship_type=relationship_type,
        subject=subject, object_=object_,
    ))
    assert result.candidate == candidate
    assert result.supporting_relationship_types == (relationship_type.value,)


def _raw_assess(body: str):
    source = NormalizedSource(
        title="عنوان عام", body=body, source_name="مصدر",
        source_url="https://example.com", language="ar",
    )
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    semantic = DeterministicCompositionalSemanticEngine().compose(
        source=source, contextual_evidence=contextual,
    )
    return DeterministicSemanticCandidateAssessor().assess(
        semantic_evidence=semantic, contextual_evidence=contextual,
    )


@pytest.mark.parametrize(
    ("body", "candidate"),
    (
        ("أعلنت وزارة الصحة تقديم الخدمات الطبية وعلاج الأمراض", "HEALTH"),
        ("أعلن البنك المركزي أن معدل البطالة تراجع مع تحسن سوق العمل", "ECONOMY"),
        ("فحص الأورام باستخدام الذكاء الاصطناعي لتحسين علاج الأمراض", "HEALTH"),
        ("بدأ الحدث بسبب نقص الموارد. أدى ذلك إلى تأثير واسع", "ANALYSIS"),
        ("انتهت المباراة بفوز الفريق. النتيجة النهائية هدفان", "RESULT_REPORT"),
        ("بلغ السعر مئة جنيه. ارتفع مقارنة بالشهر الماضي", "TREND_UPDATE"),
        ("أعلنت الجهة موعد التسجيل. تشمل الخدمة شروط الأهلية", "SERVICE"),
        ("انتشر ادعاء. تحقق الفريق من الأدلة وثبت أنه زائف", "FACT_CHECK"),
    ),
)
def test_raw_arabic_evidence_flows_into_candidate_assessment(
    body: str, candidate: str,
) -> None:
    results = {item.candidate: item for item in _raw_assess(body)}
    assert candidate in results
    assert results[candidate].supporting_relationship_types


def test_no_holdout_identifiers_in_assessor_or_tests() -> None:
    text = "\n".join(
        (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/semantics/deterministic_semantic_candidate_assessor.py",
            "tests/test_deterministic_semantic_candidate_assessor.py",
        )
    )
    forbidden = tuple(f'"{value:03d}"' for value in range(51, 61))
    assert not any(identifier in text for identifier in forbidden)


def test_empty_evidence_emits_no_full_candidate_universe() -> None:
    assert assess() == ()


def _context_item(
    *,
    supports: tuple[str, ...],
    reason: str,
    role: EvidenceRole = EvidenceRole.SUBJECT,
    strength: EvidenceStrength = EvidenceStrength.STRONG,
    section: SourceSection = SourceSection.BODY,
    sentence: int = 0,
) -> ContextualEvidenceItem:
    return ContextualEvidenceItem(
        source_section=section, sentence_index=sentence, matched_text="symbolic",
        evidence_level=EvidenceLevel.CONTEXT, role=role, strength=strength,
        reason_code=reason, supports=supports, suppresses=(),
    )


def _context(*items: ContextualEvidenceItem) -> ContextualEvidence:
    return ContextualEvidence(
        headline_items=tuple(item for item in items if item.source_section is SourceSection.HEADLINE),
        lead_items=tuple(item for item in items if item.source_section is SourceSection.LEAD),
        body_items=tuple(item for item in items if item.source_section is SourceSection.BODY),
        metadata_items=(), user_instruction_items=(), warnings=(),
    )


def _assess_context(
    relationships: tuple[SemanticRelationship, ...],
    *items: ContextualEvidenceItem,
):
    return DeterministicSemanticCandidateAssessor().assess(
        semantic_evidence=evidence(*relationships), contextual_evidence=_context(*items),
    )


def test_explicit_domain_competitor_prevents_sufficiency_without_conflict() -> None:
    first = relation(supports=("PRIMARY_DOMAIN_HEALTH",))
    first_2 = replace(first, sentence_index=1, reason_code="HEALTH_STATE")
    other = replace(first, supports=("PRIMARY_DOMAIN_SCIENCE",), sentence_index=2)
    other_2 = replace(other, sentence_index=3, reason_code="SCIENCE_STATE")
    results = {item.candidate: item for item in assess(first, first_2, other, other_2)}
    assert results["HEALTH"].sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert results["HEALTH"].direction is SemanticEvidenceDirection.SUPPORT
    assert results["HEALTH"].competing_candidates == ("SCIENCE",)


def test_latent_mapped_central_competitor_prevents_sufficiency() -> None:
    support = _context_item(supports=("TOPIC_TECHNOLOGY",), reason="TECH_CONTEXT")
    latent = _context_item(supports=("COMPONENT_HEALTH_SUBJECT",), reason="HEALTH_COMPONENT", strength=EvidenceStrength.MEDIUM)
    result = {item.candidate: item for item in _assess_context((), support, latent)}["TECHNOLOGY"]
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert result.competing_candidates == ("HEALTH",)
    assert "COMPETING_CANDIDATE" in result.warnings


def test_latent_unmapped_central_competitor_warns_and_prevents_sufficiency() -> None:
    support = _context_item(supports=("TOPIC_BUSINESS",), reason="BUSINESS_CONTEXT")
    latent = _context_item(supports=("COMPONENT_LEGAL_SUBJECT",), reason="LEGAL_COMPONENT")
    result = {item.candidate: item for item in _assess_context((), support, latent)}["BUSINESS"]
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert result.competing_candidates == ()
    assert "UNMAPPED_CENTRAL_COMPETITOR" in result.warnings


@pytest.mark.parametrize("role", (EvidenceRole.AUTHORITY, EvidenceRole.ACTOR, EvidenceRole.METHOD))
def test_secondary_latent_component_does_not_block_valid_candidate(role: EvidenceRole) -> None:
    support = _context_item(supports=("TOPIC_ECONOMY",), reason="ECONOMY_CONTEXT")
    corroboration = _context_item(supports=("TOPIC_ECONOMY",), reason="ECONOMY_OUTCOME", role=EvidenceRole.OUTCOME, sentence=1)
    secondary = _context_item(supports=("COMPONENT_LEGAL_SUBJECT",), reason="SECONDARY_COMPONENT", role=role)
    result = {item.candidate: item for item in _assess_context((), support, corroboration, secondary)}["ECONOMY"]
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT
    assert "UNMAPPED_CENTRAL_COMPETITOR" not in result.warnings


def test_weak_incidental_subject_does_not_block_valid_candidate() -> None:
    support = _context_item(supports=("TOPIC_ECONOMY",), reason="ECONOMY_CONTEXT")
    corroboration = _context_item(supports=("TOPIC_ECONOMY",), reason="ECONOMY_STATE", role=EvidenceRole.STATE, sentence=1)
    incidental = _context_item(supports=("COMPONENT_HEALTH_SUBJECT",), reason="INCIDENTAL", strength=EvidenceStrength.WEAK)
    result = {item.candidate: item for item in _assess_context((), support, corroboration, incidental)}["ECONOMY"]
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_action_targets_object_alone_does_not_establish_domain_centrality() -> None:
    result = one(relation(
        supports=("PRIMARY_DOMAIN_TECHNOLOGY",),
        relationship_type=SemanticRelationshipType.ACTION_TARGETS_OBJECT,
        subject=SemanticComponent.ACTION, object_=SemanticComponent.OBJECT,
    ))
    assert result.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT
    assert "SUBJECT_ROLE_UNRESOLVED" in result.warnings


def test_action_object_with_distinct_candidate_relationship_is_independent() -> None:
    action = relation(
        supports=("PRIMARY_DOMAIN_TECHNOLOGY",),
        relationship_type=SemanticRelationshipType.ACTION_TARGETS_OBJECT,
        subject=SemanticComponent.ACTION, object_=SemanticComponent.OBJECT,
    )
    audience = replace(
        action, sentence_index=1, reason_code="INDEPENDENT_AUDIENCE_ACTION",
        relationship_type=SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE,
    )
    result = one(action, audience)
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_headline_lead_body_same_context_family_is_discounted() -> None:
    items = tuple(
        _context_item(
            supports=("TOPIC_TECHNOLOGY",), reason="SAME_SIGNAL",
            section=section, strength=EvidenceStrength.MEDIUM,
        )
        for section in (SourceSection.HEADLINE, SourceSection.LEAD, SourceSection.BODY)
    )
    result = {item.candidate: item for item in _assess_context((), *items)}["TECHNOLOGY"]
    assert result.strength is SemanticEvidenceStrength.MODERATE
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert "DUPLICATE_EVIDENCE_DISCOUNTED" in result.warnings


def test_distinct_contextual_families_remain_independent() -> None:
    first = _context_item(supports=("TOPIC_HEALTH",), reason="HEALTH_SUBJECT", strength=EvidenceStrength.MEDIUM)
    second = _context_item(supports=("TOPIC_HEALTH",), reason="HEALTH_OUTCOME", role=EvidenceRole.OUTCOME, strength=EvidenceStrength.MEDIUM, sentence=1)
    result = {item.candidate: item for item in _assess_context((), first, second)}["HEALTH"]
    assert result.strength is SemanticEvidenceStrength.STRONG
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


@pytest.mark.parametrize(
    ("candidate", "alternative"),
    (("TECHNOLOGY", "HEALTH"), ("BUSINESS", "HEALTH"), ("GOVERNMENT", "ECONOMY"), ("SPORTS", "GOVERNMENT")),
)
def test_generic_prominent_signal_with_other_central_domain_stays_partial(
    candidate: str, alternative: str,
) -> None:
    repeated = tuple(
        _context_item(
            supports=(f"TOPIC_{candidate}",), reason=f"{candidate}_CONTEXT",
            section=section,
        ) for section in (SourceSection.HEADLINE, SourceSection.LEAD, SourceSection.BODY)
    )
    latent = _context_item(
        supports=(f"COMPONENT_{alternative}_SUBJECT",), reason="ALTERNATIVE_SUBJECT",
        strength=EvidenceStrength.MEDIUM, sentence=2,
    )
    result = {item.candidate: item for item in _assess_context((), *repeated, latent)}[candidate]
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL


def test_no_competitor_fabricated_from_unknown_component() -> None:
    support = _context_item(supports=("TOPIC_HEALTH",), reason="HEALTH_CONTEXT")
    latent = _context_item(supports=("COMPONENT_BIOLOGICAL_SUBJECT",), reason="BIO_SUBJECT")
    result = {item.candidate: item for item in _assess_context((), support, latent)}["HEALTH"]
    assert result.competing_candidates == ()
    assert "UNMAPPED_CENTRAL_COMPETITOR" in result.warnings


def test_candidate_own_component_is_not_a_competitor() -> None:
    support = _context_item(supports=("TOPIC_HEALTH",), reason="HEALTH_CONTEXT")
    corroboration = _context_item(supports=("TOPIC_HEALTH",), reason="HEALTH_OUTCOME", role=EvidenceRole.OUTCOME, sentence=1)
    own = _context_item(supports=("COMPONENT_HEALTH_SUBJECT",), reason="HEALTH_COMPONENT")
    result = {item.candidate: item for item in _assess_context((), support, corroboration, own)}["HEALTH"]
    assert result.competing_candidates == ()
    assert result.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT


def test_no_competitor_logic_leaks_benchmark_identifiers() -> None:
    text = (PROJECT_ROOT / "src/semantics/deterministic_semantic_candidate_assessor.py").read_text(encoding="utf-8")
    forbidden = ('"046"',) + tuple(f'"{value:03d}"' for value in range(51, 61))
    assert not any(value in text for value in forbidden)


def test_latent_mapped_competitor_is_not_fabricated_as_assessment() -> None:
    support = _context_item(supports=("TOPIC_BUSINESS",), reason="BUSINESS_CONTEXT")
    latent = _context_item(supports=("COMPONENT_HEALTH_SUBJECT",), reason="HEALTH_COMPONENT")
    results = _assess_context((), support, latent)
    assert tuple(item.candidate for item in results) == ("BUSINESS",)
    assert results[0].competing_candidates == ("HEALTH",)


def test_hierarchical_repetition_warning_does_not_change_direction() -> None:
    repeated = tuple(
        _context_item(
            supports=("TOPIC_WORLD",), reason="WORLD_SIGNAL", section=section,
            strength=EvidenceStrength.MEDIUM,
        ) for section in (SourceSection.HEADLINE, SourceSection.LEAD, SourceSection.BODY)
    )
    result = _assess_context((), *repeated)[0]
    assert result.direction is SemanticEvidenceDirection.SUPPORT
    assert result.sufficiency is SemanticEvidenceSufficiency.PARTIAL
    assert "DUPLICATE_EVIDENCE_DISCOUNTED" in result.warnings


@pytest.mark.parametrize(
    ("body", "candidate", "must_be_sufficient"),
    (
        ("استخدم الأطباء جهازا رقميا لفحص الأمراض. يساعد النظام الذكي في علاج المرضى.", "TECHNOLOGY", False),
        ("قالت الشركة إن علاج المرضى تحسن. طور الفريق أداة للمستشفى.", "BUSINESS", False),
        ("أعلنت الوزارة أن معدل البطالة تراجع. تحسن سوق العمل مقارنة بالشهر الماضي.", "GOVERNMENT", False),
        ("قال النادي إن القواعد القانونية الجديدة تنظم العقود. أعلنت الجهة تفاصيل القرار.", "SPORTS", False),
        ("نظام رقمي وتقنية حديثة. يكرر البيان معلومات النظام الرقمي والتقنية الحديثة.", "TECHNOLOGY", False),
        ("أعلن البنك المركزي أن معدل البطالة تراجع مع تحسن سوق العمل. ارتفع السعر مقارنة بالشهر الماضي.", "ECONOMY", True),
        ("ذكرت المستشفى تطبيقا رقميا عابرا. أعلنت المستشفى تقديم علاج الأمراض. تحسنت صحة المرضى بعد العلاج.", "HEALTH", True),
        ("أعلنت المستشفى تقديم علاج الأمراض. تحسنت صحة المرضى بعد العلاج.", "HEALTH", True),
    ),
)
def test_raw_arabic_competitor_and_independence_safety(
    body: str, candidate: str, must_be_sufficient: bool,
) -> None:
    results = {item.candidate: item for item in _raw_assess(body)}
    item = results.get(candidate)
    if must_be_sufficient:
        assert item is not None
        assert item.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT
    else:
        assert item is None or item.sufficiency is not SemanticEvidenceSufficiency.SUFFICIENT
