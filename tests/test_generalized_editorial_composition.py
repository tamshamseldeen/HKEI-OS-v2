"""Generalized domain and editorial-structure composition tests."""

from pathlib import Path

import pytest

from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.normalized_source import NormalizedSource
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)


def compose(body: str):
    source = NormalizedSource(
        title="General report",
        body=body,
        source_name="Synthetic",
        source_url="https://example.com/synthetic",
        language="en",
    )
    contextual = DeterministicContextualEvidenceEngine().analyze(source=source)
    return DeterministicCompositionalSemanticEngine().compose(
        source=source,
        contextual_evidence=contextual,
    )


@pytest.mark.parametrize(
    ("body", "support"),
    (
        ("The ministry announced a campaign. It promotes disease prevention.", "PRIMARY_DOMAIN_HEALTH"),
        ("The agency announced new figures. The price increased.", "PRIMARY_DOMAIN_ECONOMY"),
        ("The sports authority announced details. The match schedule is available.", "PRIMARY_DOMAIN_SPORTS"),
    ),
)
def test_adjacent_subject_promotes_domain(body: str, support: str) -> None:
    assert support in compose(body).primary_domain_candidates


@pytest.mark.parametrize(
    ("body", "support"),
    (
        ("The event began. Because of a constraint, it led to wider impact.", "FORMAT_ANALYSIS"),
        ("The system changed. It explains how it works to understand the process.", "FORMAT_EXPLAINER"),
        ("The match was announced. Its schedule and location are available.", "FORMAT_SERVICE"),
        ("Users should avoid exposure. First follow these prevention steps.", "FORMAT_GUIDE"),
        ("The match ended. The final score confirmed who won.", "FORMAT_RESULT_REPORT"),
        ("The current level stands at 8. It rose since last month.", "FORMAT_TREND_UPDATE"),
        ("A claim circulated. Reviewers checked it and concluded it was false.", "FORMAT_FACT_CHECK"),
    ),
)
def test_adjacent_sentences_support_editorial_structure(body: str, support: str) -> None:
    assert support in compose(body).format_support


def test_adjacent_window_is_bounded() -> None:
    evidence = compose(
        "The event began. Neutral background without a structural component. "
        "Because of a constraint, it led to wider impact."
    )
    assert "FORMAT_ANALYSIS" not in evidence.format_support


@pytest.mark.parametrize(
    ("body", "absent"),
    (
        ("The ministry published a notice.", "PRIMARY_DOMAIN_GOVERNMENT"),
        ("A company attended the meeting.", "PRIMARY_DOMAIN_BUSINESS"),
        ("The team used software as a method.", "PRIMARY_DOMAIN_TECHNOLOGY"),
        ("The price is 8.", "FORMAT_TREND_UPDATE"),
        ("Experts offered general advice.", "FORMAT_GUIDE"),
        ("A claim appeared as a question.", "FORMAT_FACT_CHECK"),
        ("The match schedule is tomorrow.", "FORMAT_RESULT_REPORT"),
        ("Because conditions changed.", "FORMAT_ANALYSIS"),
    ),
)
def test_incomplete_components_are_negative_controls(body: str, absent: str) -> None:
    evidence = compose(body)
    assert absent not in evidence.primary_domain_candidates
    assert absent not in evidence.format_support


def test_static_value_suppresses_no_trend_and_result_suppresses_trend() -> None:
    static = compose("The price is 8 today.")
    result = compose("The match ended. The final score was confirmed.")
    assert "FORMAT_TREND_UPDATE" not in static.format_support
    assert "FORMAT_TREND_UPDATE" in result.format_suppression


def test_instructional_and_service_structures_are_distinct() -> None:
    guide = compose("Users must apply. First follow the registration steps.")
    service = compose("The service launched. Its deadline and location are available.")
    assert "FORMAT_GUIDE" in guide.format_support
    assert "FORMAT_SERVICE" in service.format_support
    assert "FORMAT_GUIDE" in service.format_suppression


def test_factual_announcement_supports_standard_news() -> None:
    evidence = compose("The authority announced a decision. The statement confirmed details.")
    assert "FORMAT_STANDARD_NEWS" in evidence.format_support


def test_new_code_has_no_holdout_identifiers() -> None:
    paths = (
        Path("src/semantics/deterministic_compositional_semantic_engine.py"),
        Path("src/evidence/deterministic_contextual_evidence_engine.py"),
        Path("src/formatting/deterministic_editorial_format_classifier.py"),
        Path(__file__),
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for value in range(51, 61):
        assert f"{value:03d}" not in combined
