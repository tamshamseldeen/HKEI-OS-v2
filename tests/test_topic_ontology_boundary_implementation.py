"""Focused tests for generic Topic ontology role boundaries (HKEI-223)."""

import json
from pathlib import Path

import pytest

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.evidence_strength import EvidenceStrength
from src.intake.normalized_source import NormalizedSource
from src.resolution.resolver_authority_mode import ResolverAuthorityMode
from src.resolution.topic_authority_runtime_config import TopicAuthorityRuntimeConfig
from src.semantics.deterministic_compositional_semantic_engine import DeterministicCompositionalSemanticEngine
from src.semantics.semantic_relationship_type import SemanticRelationshipType


DATA = json.loads(
    Path("tests/fixtures/topic_ontology_boundary_raw_arabic.json").read_text(encoding="utf-8")
)
FIXTURES = DATA["fixtures"]
EMPTY_CONTEXT = ContextualEvidence((), (), (), (), (), ())


def analyze(case):
    return DeterministicCompositionalSemanticEngine(
        topic_ontology_boundary_protection=True
    ).compose(
        source=NormalizedSource(case["title"], case["body"], "hkei-223", language="ar"),
        contextual_evidence=EMPTY_CONTEXT,
    )


def domains(evidence):
    return {
        support.removeprefix("PRIMARY_DOMAIN_")
        for support in evidence.primary_domain_candidates
    }


@pytest.mark.parametrize("case", FIXTURES, ids=lambda item: item["id"])
def test_each_new_arabic_fixture_obeys_ontology_contract(case):
    evidence = analyze(case)
    actual = domains(evidence)
    expected = set(case["expected_primary"])
    if expected:
        assert expected <= actual
    else:
        boundary_domains = {"WORLD", "BUSINESS", "ECONOMY"}
        assert not (actual & boundary_domains)
    if len(expected) > 1:
        relations = [r for r in evidence.relationships if r.reason_code == "TOPIC_BOUNDARY_COMPETING"]
        assert expected <= {r.object_text for r in relations}


def tagged(tag):
    return [case for case in FIXTURES if tag in case["tags"]]


@pytest.mark.parametrize("tag,minimum", [
    ("world_primary", 10), ("business_primary", 10), ("economy_primary", 8),
    ("owner_protection", 8), ("source_protection", 8), ("entity_protection", 8),
    ("boundary_competing", 8), ("cross_sentence", 15),
    ("arabic_variation", 15), ("negative_control", 15),
])
def test_required_fixture_distribution(tag, minimum):
    assert len(tagged(tag)) >= minimum


@pytest.mark.parametrize("role,relationship_type", [
    ("owner_protection", SemanticRelationshipType.OWNER_CONTROLS_OBJECT),
    ("source_protection", SemanticRelationshipType.SOURCE_REPORTS_EVENT),
    ("entity_protection", SemanticRelationshipType.ACTOR_PERFORMS_ACTION),
])
def test_context_roles_never_supply_primary_business(role, relationship_type):
    for case in tagged(role):
        matching = [r for r in analyze(case).relationships if r.relationship_type is relationship_type]
        assert matching
        assert all(r.strength is EvidenceStrength.WEAK for r in matching)
        assert all("PRIMARY_DOMAIN_BUSINESS" not in r.supports for r in matching)


@pytest.mark.parametrize("domain,tag", [
    ("WORLD", "world_primary"),
    ("BUSINESS", "business_primary"),
    ("ECONOMY", "economy_primary"),
])
def test_primary_event_and_subject_are_structurally_represented(domain, tag):
    for case in tagged(tag):
        matching = [r for r in analyze(case).relationships
                    if r.relationship_type is SemanticRelationshipType.EVENT_ORGANIZES_SUBJECT
                    and r.object_text == domain]
        assert matching
        assert all(r.supports == (f"PRIMARY_DOMAIN_{domain}",) for r in matching)


def test_fixture_corpus_is_new_and_large_enough():
    assert DATA["authorship"] == "NEWLY_AUTHORED_HKEI_223"
    assert DATA["case_count"] == len(FIXTURES) >= 50
    assert len({case["id"] for case in FIXTURES}) == len(FIXTURES)


def test_candidate_universe_is_not_shrunk():
    evidence = analyze(tagged("boundary_competing")[0])
    assert {"WORLD", "BUSINESS"} <= domains(evidence)


def test_existing_consequence_protection_remains_integrated():
    evidence = analyze({"title": "عاصفة تضرب الساحل", "body": "تستمر العاصفة. مما أدى إلى خسائر اقتصادية."})
    consequence = [r for r in evidence.relationships
                   if r.relationship_type is SemanticRelationshipType.CONSEQUENCE_OF_EVENT]
    assert consequence
    assert all(not any(s.startswith("PRIMARY_DOMAIN_") for s in r.supports) for r in consequence)


def test_existing_authority_actor_and_method_components_remain_available():
    text = Path("src/semantics/semantic_component.py").read_text(encoding="utf-8")
    for component in ("AUTHORITY", "ACTOR", "METHOD"):
        assert f'{component} = "{component}"' in text


def test_protected_runtime_modules_are_not_part_of_implementation_diff():
    protected = {"gate", "resolver", "authority_applicator", "provider", "prompt"}
    changed = {
        path.name.lower()
        for path in Path("src").rglob("*.py")
        if path.as_posix() in {
            "src/semantics/deterministic_compositional_semantic_engine.py",
            "src/semantics/semantic_relationship_type.py",
            "src/semantics/topic_ontology_boundary_protection.py",
        }
    }
    assert not any(any(word in name for word in protected) for name in changed)


def test_pilot_default_remains_shadow():
    assert TopicAuthorityRuntimeConfig().resolve() is ResolverAuthorityMode.SHADOW


def test_no_provider_fixture_or_runtime_dependency():
    combined = Path("src/semantics/topic_ontology_boundary_protection.py").read_text(encoding="utf-8")
    assert "openai" not in combined.lower()
    assert "CANARY2-002" not in combined
