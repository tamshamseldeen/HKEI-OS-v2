"""Run the file-backed Live Editorial A/B pilot without generating content."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import sys
from typing import Any, Iterable

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LIVE_AB_ROOT = PROJECT_ROOT / "benchmark" / "live_ab"
MANIFEST_PATH = LIVE_AB_ROOT / "manifest.json"
SCHEMA_ROOT = LIVE_AB_ROOT / "schemas"
CASES_ROOT = LIVE_AB_ROOT / "cases"
ADJUDICATIONS_ROOT = LIVE_AB_ROOT / "adjudications"
REPORTS_ROOT = LIVE_AB_ROOT / "reports"
SUMMARY_JSON = REPORTS_ROOT / "pilot_20_summary.json"
SUMMARY_MD = REPORTS_ROOT / "pilot_20_summary.md"

FROZEN_CANDIDATE_COMMIT = "4b2b42472aa95f85d5cdf4a0a8c0377160921104"
WRITER_PACKET_DIMENSIONS = (
    "WP01_SOURCE_IDENTITY", "WP02_STORY_KERNEL", "WP03_MATERIAL_FACT_RECALL",
    "WP04_FACT_CLASSIFICATION", "WP05_SOURCE_ROLE_CLASSIFICATION",
    "WP06_TEMPORAL_CONTROL", "WP07_FORBIDDEN_INFERENCES",
    "WP08_CONTEXT_DISCIPLINE",
)
FINAL_ARTICLE_DIMENSIONS = (
    "FA01_CENTRAL_ANGLE_PRESERVATION", "FA02_FACTUAL_ACCURACY",
    "FA03_MATERIAL_FACT_RECALL", "FA04_NO_UNSUPPORTED_CLAIMS",
    "FA05_ATTRIBUTION_ACCURACY", "FA06_TEMPORAL_ACCURACY",
    "FA07_SOURCE_INDEPENDENCE", "FA08_EXTERNAL_CONTEXT_DISCIPLINE",
    "FA09_ARABIC_EDITORIAL_QUALITY", "FA10_READER_VALUE",
    "FA11_SEO_METADATA_ACCURACY", "FA12_PROPORTIONALITY",
)
CRITICAL_FAILURE_CODES = (
    "CF01_HALLUCINATED_MATERIAL_FACT", "CF02_WRONG_PERSON_OR_ENTITY",
    "CF03_MATERIAL_NUMBER_DISTORTION", "CF04_CENTRAL_ANGLE_DRIFT",
    "CF05_FALSE_ORIGINAL_ATTRIBUTION", "CF06_HISTORICAL_CURRENT_TIME_MIX",
    "CF07_SOURCE_SUBSTITUTION", "CF08_MATERIAL_LEGAL_OR_MEDICAL_MISSTATEMENT",
)
FAILURE_ORIGINS = (
    "SOURCE_EXTRACTION", "ANALYSIS", "VERIFICATION", "WRITER_PACKET",
    "WRITING", "SEO_METADATA", "FORMAT",
)
FAILURE_TYPES = (
    "FACT", "ANGLE", "ATTRIBUTION", "TEMPORAL", "CONTEXT", "LANGUAGE",
    "SEO", "PROPORTIONALITY",
)
READINESS = ("PUBLISH_AS_IS", "MINOR_EDIT", "MAJOR_EDIT", "REJECT")
ADDED_VALUE_SCORES = {
    "AV3_SUBSTANTIAL_VALUE": 3,
    "AV2_MODERATE_VALUE": 2,
    "AV1_MINIMAL_VALUE": 1,
    "AV0_NO_ADDED_VALUE": 0,
}


class HarnessValidationError(ValueError):
    """Raised when pilot inputs violate an explicit harness contract."""


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HarnessValidationError(f"{path}: expected a JSON object")
    return value


def schema(name: str, *, root: Path = SCHEMA_ROOT) -> dict[str, Any]:
    return read_json(root / f"{name}.schema.json")


def validate_document(document: dict[str, Any], schema_name: str) -> None:
    errors = sorted(
        Draft202012Validator(schema(schema_name)).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        location = ".".join(str(item) for item in errors[0].absolute_path) or "$"
        raise HarnessValidationError(
            f"{schema_name} validation failed at {location}: {errors[0].message}"
        )


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "benchmark_version", "candidate_prompt_version", "frozen_candidate_commit",
        "pilot_target_case_count", "current_unseen_case_count",
        "current_regression_case_count", "category_targets", "gate_thresholds",
        "randomization_seed", "created_at", "last_updated_at",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise HarnessValidationError(f"manifest missing fields: {', '.join(missing)}")
    if manifest["candidate_prompt_version"] != "1.1":
        raise HarnessValidationError("manifest candidate prompt version must be 1.1")
    if manifest["frozen_candidate_commit"] != FROZEN_CANDIDATE_COMMIT:
        raise HarnessValidationError("manifest frozen candidate commit is inconsistent")
    if not isinstance(manifest["randomization_seed"], int):
        raise HarnessValidationError("manifest randomization seed must be an integer")


def discover_cases(root: Path = CASES_ROOT) -> list[dict[str, Any]]:
    cases = [read_json(path) for path in sorted(root.glob("*.json"))]
    for case in cases:
        validate_document(case, "case")
    ids = [case["case_id"] for case in cases]
    duplicates = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise HarnessValidationError(f"duplicate case IDs: {', '.join(duplicates)}")
    return cases


def split_cases(cases: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    materialized = list(cases)
    return (
        [case for case in materialized if case["status"] == "UNSEEN"],
        [case for case in materialized if case["status"] == "REGRESSION"],
    )


def blind_mapping(case_id: str, seed: int) -> dict[str, str]:
    """Return a reproducible mapping stored separately from adjudication data."""
    choices = ["baseline", "candidate_v1_1"]
    random.Random(f"{seed}:{case_id}").shuffle(choices)
    return {"case_id": case_id, "X": choices[0], "Y": choices[1]}


def score_rubric(scores: dict[str, int], dimensions: tuple[str, ...]) -> int:
    if set(scores) != set(dimensions):
        raise HarnessValidationError("rubric score keys do not match required dimensions")
    if any(isinstance(value, bool) or value not in (0, 1, 2) for value in scores.values()):
        raise HarnessValidationError("rubric scores must be integers from 0 to 2")
    return sum(scores.values())


def writer_packet_score(scores: dict[str, int]) -> int:
    return score_rubric(scores, WRITER_PACKET_DIMENSIONS)


def final_article_score(scores: dict[str, int]) -> int:
    return score_rubric(scores, FINAL_ARTICLE_DIMENSIONS)


def validate_failure(origin: str, failure_type: str) -> None:
    if origin not in FAILURE_ORIGINS or failure_type not in FAILURE_TYPES:
        raise HarnessValidationError("failure taxonomy value is invalid")


def validate_adjudication(adjudication: dict[str, Any]) -> None:
    validate_document(adjudication, "adjudication")
    for side in ("X", "Y"):
        writer_packet_score(adjudication["writer_packet_scores"][side])
        final_article_score(adjudication["final_article_scores"][side])
        failures = adjudication["critical_failures"][side]
        if failures and adjudication["editorial_readiness"][side] == "PUBLISH_AS_IS":
            raise HarnessValidationError(
                "critical failure is incompatible with PUBLISH_AS_IS"
            )
    for failure in adjudication["failures"]:
        validate_failure(failure["origin"], failure["type"])


def load_completed(
    case_ids: set[str], root: Path = ADJUDICATIONS_ROOT
) -> list[tuple[dict[str, Any], dict[str, str]]]:
    completed = []
    for path in sorted(root.glob("*.adjudication.json")):
        adjudication = read_json(path)
        validate_adjudication(adjudication)
        mapping_path = path.with_name(path.name.replace(".adjudication.json", ".mapping.json"))
        if not mapping_path.exists():
            raise HarnessValidationError(f"missing blind mapping for {path.name}")
        mapping = read_json(mapping_path)
        if (
            mapping.get("case_id") != adjudication["case_id"]
            or {mapping.get("X"), mapping.get("Y")} != {"baseline", "candidate_v1_1"}
        ):
            raise HarnessValidationError(f"invalid blind mapping for {path.name}")
        if adjudication["case_id"] in case_ids:
            completed.append((adjudication, mapping))
    return completed


def _side(mapping: dict[str, str], system: str) -> str:
    return "X" if mapping["X"] == system else "Y"


def _candidate_won(adjudication: dict[str, Any], mapping: dict[str, str]) -> bool:
    return adjudication["outcome"] == f"{_side(mapping, 'candidate_v1_1')}_WINS"


def systematic_category_failures(
    completed: list[tuple[dict[str, Any], dict[str, str]]],
    cases_by_id: dict[str, dict[str, Any]],
    *,
    minimum_cases: int,
    failure_rate: float,
) -> list[str]:
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, str]]]] = defaultdict(list)
    for pair in completed:
        grouped[cases_by_id[pair[0]["case_id"]]["category"]].append(pair)
    flagged = []
    for category, pairs in sorted(grouped.items()):
        if len(pairs) < minimum_cases:
            continue
        serious = 0
        critical = 0
        for adjudication, mapping in pairs:
            side = _side(mapping, "candidate_v1_1")
            serious += adjudication["editorial_readiness"][side] in ("MAJOR_EDIT", "REJECT")
            critical += bool(adjudication["critical_failures"][side])
        if serious / len(pairs) >= failure_rate or critical / len(pairs) >= failure_rate:
            flagged.append(category)
    return flagged


def summarize(
    manifest: dict[str, Any],
    unseen: list[dict[str, Any]],
    regression: list[dict[str, Any]],
    completed: list[tuple[dict[str, Any], dict[str, str]]],
) -> dict[str, Any]:
    cases_by_id = {case["case_id"]: case for case in unseen}
    candidate_wins = baseline_wins = ties = both_fail = 0
    readiness = Counter({value: 0 for value in READINESS})
    critical = Counter({value: 0 for value in CRITICAL_FAILURE_CODES})
    origins = Counter({value: 0 for value in FAILURE_ORIGINS})
    types = Counter({value: 0 for value in FAILURE_TYPES})
    writer_scores: list[int] = []
    article_scores: list[int] = []
    added_values: list[int] = []
    category_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"completed": 0, "candidate_wins": 0})
    for adjudication, mapping in completed:
        outcome = adjudication["outcome"]
        candidate_wins += _candidate_won(adjudication, mapping)
        baseline_wins += outcome == f"{_side(mapping, 'baseline')}_WINS"
        ties += outcome == "TIE"
        both_fail += outcome == "BOTH_FAIL"
        side = _side(mapping, "candidate_v1_1")
        readiness[adjudication["editorial_readiness"][side]] += 1
        critical.update(adjudication["critical_failures"][side])
        writer_scores.append(writer_packet_score(adjudication["writer_packet_scores"][side]))
        article_scores.append(final_article_score(adjudication["final_article_scores"][side]))
        added_values.append(ADDED_VALUE_SCORES[adjudication["added_value"][side]])
        for failure in adjudication["failures"]:
            if failure["side"] == side:
                origins[failure["origin"]] += 1
                types[failure["type"]] += 1
        category = cases_by_id[adjudication["case_id"]]["category"]
        category_stats[category]["completed"] += 1
        category_stats[category]["candidate_wins"] += _candidate_won(adjudication, mapping)
    count = len(completed)
    decisive = candidate_wins + baseline_wins
    flagged = systematic_category_failures(
        completed,
        cases_by_id,
        minimum_cases=manifest["gate_thresholds"]["systematic_min_cases"],
        failure_rate=manifest["gate_thresholds"]["systematic_failure_rate"],
    )
    complete = len(unseen) >= manifest["pilot_target_case_count"] and count == len(unseen)
    result = {
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "total_unseen_cases": len(unseen),
        "total_regression_cases": len(regression),
        "completed_cases": count,
        "candidate_wins": candidate_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "both_fail": both_fail,
        "decisive_comparisons": decisive,
        "candidate_decisive_win_rate": candidate_wins / decisive if decisive else None,
        "publish_as_is_count": readiness["PUBLISH_AS_IS"],
        "publish_as_is_rate": readiness["PUBLISH_AS_IS"] / count if count else None,
        "minor_edit_count": readiness["MINOR_EDIT"],
        "minor_edit_rate": readiness["MINOR_EDIT"] / count if count else None,
        "major_edit_count": readiness["MAJOR_EDIT"],
        "major_edit_rate": readiness["MAJOR_EDIT"] / count if count else None,
        "reject_count": readiness["REJECT"],
        "reject_rate": readiness["REJECT"] / count if count else None,
        "critical_failures_by_code": dict(critical),
        "critical_failure_rate": (
            sum(bool(adjudication["critical_failures"][_side(mapping, "candidate_v1_1")]) for adjudication, mapping in completed) / count
            if count else None
        ),
        "average_writer_packet_score": sum(writer_scores) / count if count else None,
        "average_final_article_score": sum(article_scores) / count if count else None,
        "average_added_value_score": sum(added_values) / count if count else None,
        "category_level_performance": dict(category_stats),
        "failure_origin_distribution": dict(origins),
        "failure_type_distribution": dict(types),
        "systematic_category_failure_flags": flagged,
    }
    result["gate_result"] = evaluate_gate(result, manifest["gate_thresholds"])
    return result


def evaluate_gate(summary: dict[str, Any], thresholds: dict[str, Any]) -> str:
    if summary["status"] != "COMPLETE" or not summary["decisive_comparisons"]:
        return "INCOMPLETE"
    good_readiness = (
        summary["publish_as_is_count"] + summary["minor_edit_count"]
    ) / summary["completed_cases"]
    passes = (
        summary["candidate_decisive_win_rate"] >= thresholds["candidate_decisive_win_rate"]
        and summary["critical_failure_rate"] <= thresholds["critical_failure_rate"]
        and good_readiness >= thresholds["publish_as_is_plus_minor_edit_rate"]
        and summary["critical_failures_by_code"]["CF05_FALSE_ORIGINAL_ATTRIBUTION"] <= thresholds["false_original_attribution_critical_failures"]
        and summary["critical_failures_by_code"]["CF03_MATERIAL_NUMBER_DISTORTION"] <= thresholds["material_fact_distortion_critical_failures"]
        and summary["average_added_value_score"] >= thresholds["average_added_value_score"]
        and len(summary["systematic_category_failure_flags"]) <= thresholds["systematic_category_failures"]
    )
    return "PASS_TO_50_CASE_VALIDATION" if passes else "FAIL_ROOT_CAUSE_ANALYSIS"


def render_markdown(summary: dict[str, Any]) -> str:
    rate = summary["candidate_decisive_win_rate"]
    rendered_rate = "NONE" if rate is None else f"{rate:.2%}"
    return f"""# Live Editorial A/B Pilot Summary

Status: {summary['status']}

Gate result: {summary['gate_result']}

Unseen cases: {summary['total_unseen_cases']}

Completed cases: {summary['completed_cases']}

Candidate wins: {summary['candidate_wins']}

Baseline wins: {summary['baseline_wins']}

Ties: {summary['ties']}

Both fail: {summary['both_fail']}

Decisive comparisons: {summary['decisive_comparisons']}

Candidate decisive win rate: {rendered_rate}
"""


def run(root: Path = LIVE_AB_ROOT) -> dict[str, Any]:
    manifest = read_json(root / "manifest.json")
    validate_manifest(manifest)
    cases = discover_cases(root / "cases")
    unseen, regression = split_cases(cases)
    if len(unseen) != manifest["current_unseen_case_count"] or len(regression) != manifest["current_regression_case_count"]:
        raise HarnessValidationError("manifest case counts do not match discovered cases")
    completed = load_completed({case["case_id"] for case in unseen}, root / "adjudications")
    summary = summarize(manifest, unseen, regression, completed)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pilot_20_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (reports / "pilot_20_summary.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main() -> int:
    print(json.dumps(run(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
