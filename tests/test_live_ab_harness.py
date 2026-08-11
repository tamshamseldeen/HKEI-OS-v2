"""Tests for the reusable Live Editorial A/B pilot harness."""

from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

import examples.run_live_ab_pilot as harness


def case(case_id: str = "case_001", status: str = "UNSEEN", category: str = "politics") -> dict:
    return {
        "case_id": case_id,
        "status": status,
        "category": category,
        "subtype": "international_diplomacy",
        "language": "ar",
        "source_url": "",
        "source_text": "Synthetic source supplied only to unit tests.",
        "publication_datetime": "2026-08-11T00:00:00Z",
        "expected_topic": "POLITICS",
        "risk": {
            "time_sensitive": True,
            "legal": False,
            "medical": False,
            "financial": False,
            "political": True,
        },
    }


def manifest(target: int = 2) -> dict:
    value = harness.read_json(harness.MANIFEST_PATH)
    value["pilot_target_case_count"] = target
    value["current_unseen_case_count"] = target
    return value


def scores(dimensions: tuple[str, ...], value: int = 2) -> dict[str, int]:
    return {dimension: value for dimension in dimensions}


def adjudication(
    case_id: str,
    *,
    outcome: str = "X_WINS",
    candidate_side: str = "X",
    readiness: str = "PUBLISH_AS_IS",
    added_value: str = "AV3_SUBSTANTIAL_VALUE",
    critical: list[str] | None = None,
) -> tuple[dict, dict]:
    other = "Y" if candidate_side == "X" else "X"
    document = {
        "case_id": case_id,
        "outcome": outcome,
        "confidence": "HIGH",
        "reason_codes": ["CENTRAL_ANGLE_STRONGER"],
        "writer_packet_scores": {
            "X": scores(harness.WRITER_PACKET_DIMENSIONS),
            "Y": scores(harness.WRITER_PACKET_DIMENSIONS),
        },
        "final_article_scores": {
            "X": scores(harness.FINAL_ARTICLE_DIMENSIONS),
            "Y": scores(harness.FINAL_ARTICLE_DIMENSIONS),
        },
        "editorial_readiness": {"X": "MINOR_EDIT", "Y": "MINOR_EDIT"},
        "added_value": {"X": added_value, "Y": "AV1_MINIMAL_VALUE"},
        "critical_failures": {"X": [], "Y": []},
        "failures": [],
    }
    document["editorial_readiness"][candidate_side] = readiness
    document["critical_failures"][candidate_side] = critical or []
    mapping = {"case_id": case_id, candidate_side: "candidate_v1_1", other: "baseline"}
    return document, mapping


def test_all_schemas_are_valid_and_representative_case_validates() -> None:
    for name in ("case", "writer_packet", "final_article", "adjudication", "summary"):
        Draft202012Validator.check_schema(harness.schema(name))
    harness.validate_document(case(), "case")


def test_case_requires_at_least_one_source_input() -> None:
    invalid = case()
    invalid["source_text"] = ""
    with pytest.raises(harness.HarnessValidationError, match="case validation failed"):
        harness.validate_document(invalid, "case")
    valid = case()
    valid["source_text"] = ""
    valid["source_url"] = "https://example.invalid/source"
    harness.validate_document(valid, "case")


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(json.dumps(case()), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(case()), encoding="utf-8")
    with pytest.raises(harness.HarnessValidationError, match="duplicate case IDs"):
        harness.discover_cases(tmp_path)


def test_unseen_and_regression_cases_are_separated() -> None:
    unseen, regression = harness.split_cases([
        case("case_001", "UNSEEN"), case("case_002", "REGRESSION")
    ])
    assert [item["case_id"] for item in unseen] == ["case_001"]
    assert [item["case_id"] for item in regression] == ["case_002"]


def test_regression_cases_are_excluded_from_live_metrics() -> None:
    live = case("case_001", "UNSEEN")
    regression = case("case_002", "REGRESSION")
    live_result = adjudication("case_001")
    summary = harness.summarize(manifest(1), [live], [regression], [live_result])
    assert summary["total_regression_cases"] == 1
    assert summary["completed_cases"] == 1
    assert summary["candidate_wins"] == 1


def test_writer_packet_and_final_article_scoring() -> None:
    assert harness.writer_packet_score(scores(harness.WRITER_PACKET_DIMENSIONS)) == 16
    assert harness.final_article_score(scores(harness.FINAL_ARTICLE_DIMENSIONS)) == 24
    with pytest.raises(harness.HarnessValidationError):
        harness.writer_packet_score({"WP01_SOURCE_IDENTITY": 2})
    invalid = scores(harness.FINAL_ARTICLE_DIMENSIONS)
    invalid["FA01_CENTRAL_ANGLE_PRESERVATION"] = 3
    with pytest.raises(harness.HarnessValidationError):
        harness.final_article_score(invalid)


def test_critical_failure_blocks_publish_as_is() -> None:
    document, _ = adjudication(
        "case_001", critical=["CF01_HALLUCINATED_MATERIAL_FACT"]
    )
    with pytest.raises(harness.HarnessValidationError, match="incompatible"):
        harness.validate_adjudication(document)


def test_blind_mapping_is_deterministic_and_contains_no_prompt_label() -> None:
    first = harness.blind_mapping("case_001", 151)
    assert first == harness.blind_mapping("case_001", 151)
    assert {first["X"], first["Y"]} == {"baseline", "candidate_v1_1"}
    assert set(first) == {"case_id", "X", "Y"}


def test_decisive_win_rate_excludes_ties_and_both_fail() -> None:
    cases = [case(f"case_{index:03d}") for index in range(1, 5)]
    completed = [
        adjudication("case_001", outcome="X_WINS"),
        adjudication("case_002", outcome="Y_WINS", candidate_side="Y"),
        adjudication("case_003", outcome="TIE"),
        adjudication("case_004", outcome="BOTH_FAIL", readiness="MINOR_EDIT"),
    ]
    summary = harness.summarize(manifest(4), cases, [], completed)
    assert summary["candidate_wins"] == 2
    assert summary["ties"] == 1
    assert summary["both_fail"] == 1
    assert summary["decisive_comparisons"] == 2
    assert summary["candidate_decisive_win_rate"] == 1.0


def test_added_value_scoring_uses_operational_scale() -> None:
    completed = [adjudication("case_001", added_value="AV2_MODERATE_VALUE")]
    summary = harness.summarize(manifest(1), [case()], [], completed)
    assert summary["average_added_value_score"] == 2.0


def test_failure_taxonomy_accepts_multiple_and_rejects_unknown_values() -> None:
    document, _ = adjudication("case_001", readiness="MINOR_EDIT")
    document["failures"] = [
        {"side": "X", "origin": "ANALYSIS", "type": "ANGLE"},
        {"side": "X", "origin": "SEO_METADATA", "type": "SEO"},
    ]
    harness.validate_adjudication(document)
    with pytest.raises(harness.HarnessValidationError):
        harness.validate_failure("MODEL", "FACT")


def test_systematic_category_failure_detection() -> None:
    cases = [case("case_001", category="legal"), case("case_002", category="legal")]
    completed = [
        adjudication("case_001", readiness="MAJOR_EDIT"),
        adjudication("case_002", readiness="MINOR_EDIT"),
    ]
    flagged = harness.systematic_category_failures(
        completed, {item["case_id"]: item for item in cases},
        minimum_cases=2, failure_rate=0.5,
    )
    assert flagged == ["legal"]


def test_gate_pass_fail_and_incomplete() -> None:
    cases = [case("case_001", category="politics"), case("case_002", category="economy")]
    passing = harness.summarize(
        manifest(2), cases, [],
        [adjudication("case_001"), adjudication("case_002")],
    )
    assert passing["gate_result"] == "PASS_TO_50_CASE_VALIDATION"
    failing_pair = adjudication(
        "case_002", outcome="Y_WINS", readiness="REJECT",
        added_value="AV0_NO_ADDED_VALUE",
        critical=["CF03_MATERIAL_NUMBER_DISTORTION"],
    )
    failing = harness.summarize(
        manifest(2), cases, [], [adjudication("case_001"), failing_pair]
    )
    assert failing["gate_result"] == "FAIL_ROOT_CAUSE_ANALYSIS"
    incomplete_manifest = manifest(2)
    incomplete = harness.summarize(incomplete_manifest, cases, [], [])
    assert incomplete["gate_result"] == "INCOMPLETE"


def test_empty_benchmark_has_no_fabricated_metrics() -> None:
    empty_manifest = manifest(20)
    empty_manifest["current_unseen_case_count"] = 0
    summary = harness.summarize(empty_manifest, [], [], [])
    assert summary["status"] == "INCOMPLETE"
    assert summary["gate_result"] == "INCOMPLETE"
    assert summary["completed_cases"] == 0
    assert summary["candidate_decisive_win_rate"] is None
    assert summary["average_added_value_score"] is None


def test_manifest_is_frozen_to_audited_candidate() -> None:
    current = harness.read_json(harness.MANIFEST_PATH)
    harness.validate_manifest(current)
    assert current["candidate_prompt_version"] == "1.1"
    assert current["frozen_candidate_commit"] == harness.FROZEN_CANDIDATE_COMMIT
    changed = deepcopy(current)
    changed["frozen_candidate_commit"] = "0" * 40
    with pytest.raises(harness.HarnessValidationError, match="inconsistent"):
        harness.validate_manifest(changed)
