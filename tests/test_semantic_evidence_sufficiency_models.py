"""Tests for provider-neutral semantic sufficiency domain models."""

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from src.semantics.semantic_candidate_assessment import SemanticCandidateAssessment
from src.semantics.semantic_evidence_direction import SemanticEvidenceDirection
from src.semantics.semantic_evidence_strength import SemanticEvidenceStrength
from src.semantics.semantic_evidence_sufficiency import SemanticEvidenceSufficiency


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def assessment(**changes: object) -> SemanticCandidateAssessment:
    values = {
        "candidate": "HEALTH",
        "direction": SemanticEvidenceDirection.SUPPORT,
        "strength": SemanticEvidenceStrength.WEAK,
        "sufficiency": SemanticEvidenceSufficiency.INSUFFICIENT,
        "supporting_relationship_types": ("SUBJECT_BELONGS_TO_DOMAIN",),
        "suppressing_relationship_types": (),
        "role_basis": ("SUBJECT",),
        "competing_candidates": (),
        "warnings": (),
    }
    values.update(changes)
    return SemanticCandidateAssessment(**values)  # type: ignore[arg-type]


def test_enum_values_exactly_match_specification_contract() -> None:
    assert tuple(item.value for item in SemanticEvidenceDirection) == (
        "SUPPORT", "SUPPRESS", "NEUTRAL", "CONFLICTING",
    )
    assert tuple(item.value for item in SemanticEvidenceStrength) == (
        "WEAK", "MODERATE", "STRONG",
    )
    assert tuple(item.value for item in SemanticEvidenceSufficiency) == (
        "INSUFFICIENT", "PARTIAL", "SUFFICIENT", "CONFLICTED",
    )
    specification = (
        PROJECT_ROOT / "docs/SEMANTIC_EVIDENCE_SUFFICIENCY_SPECIFICATION.md"
    ).read_text(encoding="utf-8")
    for value in (
        *SemanticEvidenceDirection,
        *SemanticEvidenceStrength,
        *SemanticEvidenceSufficiency,
    ):
        assert f"`{value.value}`" in specification


def test_candidate_assessment_is_frozen_with_exact_field_order() -> None:
    model = assessment()
    assert tuple(field.name for field in fields(model)) == (
        "candidate", "direction", "strength", "sufficiency",
        "supporting_relationship_types", "suppressing_relationship_types",
        "role_basis", "competing_candidates", "warnings",
    )
    with pytest.raises(FrozenInstanceError):
        model.candidate = "ECONOMY"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("direction", "strength", "sufficiency"),
    (
        (SemanticEvidenceDirection.SUPPORT, SemanticEvidenceStrength.WEAK, SemanticEvidenceSufficiency.INSUFFICIENT),
        (SemanticEvidenceDirection.SUPPORT, SemanticEvidenceStrength.MODERATE, SemanticEvidenceSufficiency.PARTIAL),
        (SemanticEvidenceDirection.SUPPORT, SemanticEvidenceStrength.STRONG, SemanticEvidenceSufficiency.SUFFICIENT),
        (SemanticEvidenceDirection.CONFLICTING, SemanticEvidenceStrength.STRONG, SemanticEvidenceSufficiency.CONFLICTED),
        (SemanticEvidenceDirection.SUPPRESS, SemanticEvidenceStrength.WEAK, SemanticEvidenceSufficiency.INSUFFICIENT),
        (SemanticEvidenceDirection.NEUTRAL, SemanticEvidenceStrength.WEAK, SemanticEvidenceSufficiency.INSUFFICIENT),
        (SemanticEvidenceDirection.SUPPRESS, SemanticEvidenceStrength.MODERATE, SemanticEvidenceSufficiency.PARTIAL),
    ),
)
def test_valid_consistency_combinations(
    direction: SemanticEvidenceDirection,
    strength: SemanticEvidenceStrength,
    sufficiency: SemanticEvidenceSufficiency,
) -> None:
    assert assessment(
        direction=direction, strength=strength, sufficiency=sufficiency
    ).sufficiency is sufficiency


@pytest.mark.parametrize(
    ("direction", "sufficiency"),
    (
        (SemanticEvidenceDirection.CONFLICTING, SemanticEvidenceSufficiency.INSUFFICIENT),
        (SemanticEvidenceDirection.CONFLICTING, SemanticEvidenceSufficiency.PARTIAL),
        (SemanticEvidenceDirection.SUPPORT, SemanticEvidenceSufficiency.CONFLICTED),
        (SemanticEvidenceDirection.SUPPRESS, SemanticEvidenceSufficiency.CONFLICTED),
        (SemanticEvidenceDirection.SUPPRESS, SemanticEvidenceSufficiency.SUFFICIENT),
        (SemanticEvidenceDirection.NEUTRAL, SemanticEvidenceSufficiency.SUFFICIENT),
        (SemanticEvidenceDirection.NEUTRAL, SemanticEvidenceSufficiency.PARTIAL),
    ),
)
def test_invalid_consistency_combinations_are_rejected(
    direction: SemanticEvidenceDirection,
    sufficiency: SemanticEvidenceSufficiency,
) -> None:
    with pytest.raises(ValueError):
        assessment(direction=direction, sufficiency=sufficiency)


@pytest.mark.parametrize("candidate", ("", " ", " HEALTH", "HEALTH ", 1, None))
def test_candidate_must_be_non_empty_stripped_string(candidate: object) -> None:
    with pytest.raises(ValueError):
        assessment(candidate=candidate)


def test_candidate_cannot_compete_with_itself() -> None:
    with pytest.raises(ValueError, match="compete with itself"):
        assessment(competing_candidates=("HEALTH",))


@pytest.mark.parametrize(
    "field_name",
    (
        "supporting_relationship_types", "suppressing_relationship_types",
        "role_basis", "competing_candidates", "warnings",
    ),
)
def test_symbolic_provenance_requires_tuple_of_nonempty_stripped_strings(
    field_name: str,
) -> None:
    for invalid in (["VALUE"], ("",), (" VALUE",), (1,)):
        with pytest.raises(ValueError):
            assessment(**{field_name: invalid})


def test_duplicate_tuple_members_are_rejected_without_normalization() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        assessment(role_basis=("SUBJECT", "SUBJECT"))


def test_model_is_candidate_neutral_and_contains_no_downstream_fields() -> None:
    field_names = {field.name for field in fields(SemanticCandidateAssessment)}
    forbidden_fields = {
        "confidence", "resolved", "is_resolved", "adjudication_required",
        "raw_source", "source_text", "benchmark", "benchmark_id",
    }
    assert not field_names & forbidden_fields

    path = PROJECT_ROOT / "src/semantics/semantic_candidate_assessment.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden_imports = (
        "topic", "editorial_format", "openai", "provider",
        "semantic_adjudication_response",
    )
    assert not any(term in module.casefold() for module in imports for term in forbidden_imports)
