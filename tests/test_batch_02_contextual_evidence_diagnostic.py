"""Tests for the Batch 02 contextual evidence diagnostic benchmark."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from examples.run_batch_02_contextual_evidence_diagnostic import (
    BATCH_ROOT,
    DIAGNOSTIC_CASE_IDS,
    analyze_diagnostic,
    diagnostic_status,
    parse_source,
    read_manifest,
    render_console,
    render_json,
    render_markdown,
)
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.normalized_source import NormalizedSource


ITEM_KEYS = {
    "source_section",
    "sentence_index",
    "matched_text",
    "evidence_level",
    "role",
    "strength",
    "reason_code",
    "supports",
    "suppresses",
}
INPUT_DIGEST = "d6480ad14f4640a4c3dcf29268accbd848455fd01177416ba092aacb4189a755"


@pytest.fixture(scope="module")
def analysis() -> dict[str, object]:
    """Provide one real deterministic contextual evidence diagnostic."""
    return analyze_diagnostic()


def _source_paths() -> list[Path]:
    """Return frozen Batch 02 input paths in registered order."""
    return [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[
            BATCH_ROOT / case["source_file"] for case in read_manifest()
        ],
    ]


def _digest(paths: list[Path], root: Path) -> str:
    """Calculate one deterministic path-sensitive input digest."""
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_exact_six_cases_are_analyzed_in_required_order(
    analysis: dict[str, object],
) -> None:
    """Analyze only the six specified diagnostic cases in fixed order."""
    assert DIAGNOSTIC_CASE_IDS == ("011", "013", "015", "018", "019", "020")
    assert analysis["case_count"] == 6
    assert tuple(case["id"] for case in analysis["cases"]) == DIAGNOSTIC_CASE_IDS


def test_engine_receives_exact_category_free_sources() -> None:
    """Invoke only the evidence engine with exact source metadata and no category."""
    engine = Mock(wraps=DeterministicContextualEvidenceEngine())

    analyze_diagnostic(engine=engine)

    assert engine.analyze.call_count == 6
    manifest = {case["id"]: case for case in read_manifest()}
    for engine_call, case_id in zip(
        engine.analyze.call_args_list,
        DIAGNOSTIC_CASE_IDS,
    ):
        persisted = parse_source(
            BATCH_ROOT / manifest[case_id]["source_file"]
        )
        source = engine_call.kwargs["source"]
        assert isinstance(source, NormalizedSource)
        assert source == NormalizedSource(
            title=persisted.title,
            body=persisted.body,
            source_name=persisted.source_name,
            source_url=persisted.source_url,
            published_at=None,
            language="ar",
            country=None,
            author=None,
            images=(),
            attachments=(),
            category=None,
            tags=(),
        )
        assert engine_call.kwargs["user_instruction"] is None


def test_diagnostic_module_has_no_classifier_dependencies() -> None:
    """Keep Topic, Format, and Reader Intent classifiers outside this diagnostic."""
    runner = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "run_batch_02_contextual_evidence_diagnostic.py"
    ).read_text(encoding="utf-8")

    assert "DeterministicTopicClassifier" not in runner
    assert "DeterministicEditorialFormatClassifier" not in runner
    assert "DeterministicReaderIntentClassifier" not in runner


def test_items_preserve_engine_order_and_exact_provenance(
    analysis: dict[str, object],
) -> None:
    """Serialize exact item fields without reordering engine evidence."""
    engine = DeterministicContextualEvidenceEngine()
    manifest = {case["id"]: case for case in read_manifest()}
    for case in analysis["cases"]:
        persisted = parse_source(
            BATCH_ROOT / manifest[case["id"]]["source_file"]
        )
        source = NormalizedSource(
            title=persisted.title,
            body=persisted.body,
            source_name=persisted.source_name,
            source_url=persisted.source_url,
            language="ar",
        )
        actual = engine.analyze(source=source, user_instruction=None).all_items

        assert len(actual) == len(case["items"])
        assert tuple(item.matched_text for item in actual) == tuple(
            item["matched_text"] for item in case["items"]
        )
        assert all(set(item) == ITEM_KEYS for item in case["items"])
        assert all(item["source_section"] in {"HEADLINE", "LEAD", "BODY"} for item in case["items"])
        assert all(isinstance(item["sentence_index"], int) for item in case["items"])


def test_summary_counts_are_exact(analysis: dict[str, object]) -> None:
    """Count supports, suppressions, roles, strengths, and section totals exactly."""
    for case in analysis["cases"]:
        items = case["items"]
        expected_supports: dict[str, int] = {}
        expected_suppresses: dict[str, int] = {}
        expected_roles: dict[str, int] = {}
        for item in items:
            for label in item["supports"]:
                expected_supports[label] = expected_supports.get(label, 0) + 1
            for label in item["suppresses"]:
                expected_suppresses[label] = expected_suppresses.get(label, 0) + 1
            expected_roles[item["role"]] = expected_roles.get(item["role"], 0) + 1

        assert case["supports_summary"] == expected_supports
        assert case["suppresses_summary"] == expected_suppresses
        assert case["roles_summary"] == expected_roles
        assert case["strength_summary"] == {
            strength: sum(item["strength"] == strength for item in items)
            for strength in ("STRONG", "MEDIUM", "WEAK")
        }
        assert case["all_item_count"] == len(items)
        assert (
            case["headline_item_count"]
            + case["lead_item_count"]
            + case["body_item_count"]
        ) == len(items)


def test_required_topic_support_is_exposed_for_every_case(
    analysis: dict[str, object],
) -> None:
    """Expose all six required topic labels with strong support where required."""
    expected = {
        "011": "TOPIC_GOVERNMENT",
        "013": "TOPIC_TECHNOLOGY",
        "015": "TOPIC_GOVERNMENT",
        "018": "TOPIC_SCIENCE",
        "019": "TOPIC_CULTURE",
        "020": "TOPIC_TECHNOLOGY",
    }
    for case in analysis["cases"]:
        assert expected[case["id"]] in case["supports_summary"]
        assert case["has_required_topic_support"] is True


def test_case_015_exposes_service_intent_and_editorial_role(
    analysis: dict[str, object],
) -> None:
    """Expose government, service, know-action, and actionable-role evidence."""
    case = next(case for case in analysis["cases"] if case["id"] == "015")

    assert "TOPIC_GOVERNMENT" in case["supports_summary"]
    assert "FORMAT_SERVICE" in case["supports_summary"]
    assert "INTENT_KNOW_ACTION" in case["supports_summary"]
    assert {"REQUIREMENT", "DEADLINE", "AFFECTED_AUDIENCE"}.intersection(
        case["roles_summary"]
    )
    assert case["has_required_format_support"] is True
    assert case["has_required_intent_support"] is True


def test_case_018_weak_sports_is_contextually_suppressed(
    analysis: dict[str, object],
) -> None:
    """Accept weak team evidence only with local sports suppression and science."""
    case = next(case for case in analysis["cases"] if case["id"] == "018")
    sports_items = [
        item for item in case["items"] if "TOPIC_SPORTS" in item["supports"]
    ]

    assert "TOPIC_SCIENCE" in case["supports_summary"]
    assert all(item["strength"] == "WEAK" for item in sports_items)
    if sports_items:
        assert case["suppresses_summary"]["TOPIC_SPORTS"] >= 1
        assert case["has_contextual_suppression"] is True
    assert case["has_unexpected_sports_signal"] is False


def test_no_accidental_sports_signal_exists(analysis: dict[str, object]) -> None:
    """Reject all accidental or unsuppressed sports support in diagnostic cases."""
    assert analysis["unexpected_sports_signals"] == 0
    assert all(not case["has_unexpected_sports_signal"] for case in analysis["cases"])
    for case in analysis["cases"]:
        if case["id"] != "018":
            assert "TOPIC_SPORTS" not in case["supports_summary"]


def test_json_has_no_separate_full_source_body(
    analysis: dict[str, object],
) -> None:
    """Store matched evidence text without a separate source body field or content."""
    output = render_json(analysis)
    parsed = json.loads(output)

    assert all("body" not in case for case in parsed["cases"])
    manifest = {case["id"]: case for case in read_manifest()}
    for case_id in DIAGNOSTIC_CASE_IDS:
        source = parse_source(BATCH_ROOT / manifest[case_id]["source_file"])
        assert source.body not in output


def test_markdown_preserves_serialized_evidence_order(
    analysis: dict[str, object],
) -> None:
    """Render every evidence detail block in unchanged engine order."""
    markdown = render_markdown(analysis)
    for index, case in enumerate(analysis["cases"]):
        section = markdown.split(f"## Case {case['id']}\n", 1)[1]
        if index + 1 < len(analysis["cases"]):
            section = section.split(
                f"## Case {analysis['cases'][index + 1]['id']}\n",
                1,
            )[0]
        cursor = 0
        for item in case["items"]:
            detail = (
                f"[SECTION:{item['source_section']}] "
                f"[SENTENCE:{item['sentence_index']}] "
                f"[LEVEL:{item['evidence_level']}] "
                f"[ROLE:{item['role']}] "
                f"[STRENGTH:{item['strength']}] "
                f'"{item["matched_text"]}"\n'
                f"  Reason: {item['reason_code']}"
            )
            position = section.index(detail, cursor)
            assert position >= cursor
            cursor = position + len(detail)


def test_status_uses_all_required_quality_conditions(
    analysis: dict[str, object],
) -> None:
    """Pass complete clean metrics and fail when a quality condition regresses."""
    assert diagnostic_status(analysis) == "PASSED"
    passing = copy.deepcopy(analysis)
    passing["required_format_support_passed"] = passing[
        "required_format_support_applicable"
    ]
    passing["required_intent_support_passed"] = passing[
        "required_intent_support_applicable"
    ]
    assert diagnostic_status(passing) == "PASSED"
    passing["unexpected_sports_signals"] = 1
    assert diagnostic_status(passing) == "FAILED"


def test_outputs_are_deterministic_and_match_checked_in_reports(
    analysis: dict[str, object],
) -> None:
    """Keep JSON, Markdown, and console output byte-stable."""
    assert (BATCH_ROOT / "contextual_evidence_diagnostic.json").read_text(
        encoding="utf-8"
    ) == render_json(analysis)
    assert (BATCH_ROOT / "contextual_evidence_diagnostic.md").read_text(
        encoding="utf-8"
    ) == render_markdown(analysis)
    assert render_console(analysis) == render_console(copy.deepcopy(analysis))


def test_inputs_and_existing_classifier_files_remain_unchanged() -> None:
    """Protect benchmark inputs and all three existing classifier modules."""
    classifier_paths = [
        Path("src/topic/deterministic_topic_classifier.py"),
        Path("src/formatting/deterministic_editorial_format_classifier.py"),
        Path("src/intent/deterministic_reader_intent_classifier_v2.py"),
    ]
    classifiers_before = {path: path.read_bytes() for path in classifier_paths}

    analyze_diagnostic()

    assert _digest(_source_paths(), BATCH_ROOT) == INPUT_DIGEST
    assert {path: path.read_bytes() for path in classifier_paths} == classifiers_before


def test_diagnostic_requires_no_api_network_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run all six cases with external and environment access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert analyze_diagnostic()["case_count"] == 6
