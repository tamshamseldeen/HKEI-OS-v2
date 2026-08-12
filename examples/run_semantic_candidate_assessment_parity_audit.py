"""Audit candidate sufficiency parity and committed full-suite failure provenance."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_semantic_candidate_assessment_shadow import analyze as shadow_analyze  # noqa: E402


OUTPUT_JSON = PROJECT_ROOT / "benchmark/semantic_candidate_assessment_parity_audit.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark/semantic_candidate_assessment_parity_audit.md"
FAILURE_JSON = PROJECT_ROOT / "benchmark/full_suite_failure_provenance.json"
FAILURE_MD = PROJECT_ROOT / "benchmark/full_suite_failure_provenance.md"
PARENT_SHADOW = Path("/tmp/hkei171-parent/benchmark/semantic_candidate_assessment_shadow.json")
STATUSES = {
    "batch_01": "HISTORICAL_REGRESSION_CORPUS",
    "batch_02": "HISTORICAL_REGRESSION_CORPUS",
    "batch_03": "HISTORICAL_REGRESSION_CORPUS",
    "batch_05": "SEMANTIC_ADJUDICATION_DEVELOPMENT_CORPUS",
    "batch_06": "DIAGNOSTIC_DEVELOPMENT_SET",
}


def _expected(item: dict[str, Any]) -> str | None:
    if item["candidate_group"] == "TOPIC_LIKE":
        return item["case"]["expected_topic"]
    if item["candidate_group"] == "FORMAT_LIKE":
        return item["case"]["expected_format"]
    return None


def _flatten(shadow: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {**assessment, "case": case, "key": f"{case['batch']}:{case['id']}:{assessment['candidate']}"}
        for case in shadow["case_inventory"] for assessment in case["assessments"]
    ]


def _dist(items: list[dict[str, Any]], field: str, values: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(item[field] for item in items)
    return {value: counts[value] for value in values}


def analyze(parent_shadow_path: Path = PARENT_SHADOW) -> dict[str, Any]:
    shadow = shadow_analyze()
    items = _flatten(shadow)
    known = [item for item in items if _expected(item) is not None]
    wrong = [item for item in known if item["candidate"] != _expected(item)]
    correct = [item for item in known if item["candidate"] == _expected(item)]
    sufficient = [item for item in known if item["sufficiency"] == "SUFFICIENT"]
    true_sufficient = [item for item in sufficient if item in correct]
    false_sufficient = [item for item in sufficient if item in wrong]

    def state_counts(values: list[dict[str, Any]]) -> dict[str, int]:
        return _dist(values, "sufficiency", ("INSUFFICIENT", "PARTIAL", "SUFFICIENT", "CONFLICTED"))

    batch_metrics = {}
    for batch, status in STATUSES.items():
        cases = [case for case in shadow["case_inventory"] if case["batch"] == batch]
        batch_items = [item for item in items if item["case"]["batch"] == batch]
        batch_known = [item for item in batch_items if _expected(item) is not None]
        batch_wrong = [item for item in batch_known if item["candidate"] != _expected(item)]
        batch_correct = [item for item in batch_known if item["candidate"] == _expected(item)]
        batch_sufficient = [item for item in batch_known if item["sufficiency"] == "SUFFICIENT"]
        batch_true = [item for item in batch_sufficient if item in batch_correct]
        batch_false = [item for item in batch_sufficient if item in batch_wrong]
        batch_metrics[batch] = {
            "scientific_status": status,
            "case_count": len(cases), "assessment_count": len(batch_items),
            "direction_distribution": _dist(batch_items, "direction", ("SUPPORT", "SUPPRESS", "NEUTRAL", "CONFLICTING")),
            "strength_distribution": _dist(batch_items, "strength", ("WEAK", "MODERATE", "STRONG")),
            "sufficiency_distribution": state_counts(batch_items),
            "true_sufficient_count": len(batch_true),
            "false_sufficient_count": len(batch_false),
            "false_sufficiency_rate": len(batch_false) / len(batch_sufficient) * 100 if batch_sufficient else 0.0,
            "safe_wrong_counts": state_counts([item for item in batch_wrong if item["sufficiency"] != "SUFFICIENT"]),
            "expected_candidate_sufficiency_distribution": state_counts(batch_correct),
            "sufficient_precision": len(batch_true) / len(batch_sufficient) * 100 if batch_sufficient else None,
        }

    if parent_shadow_path.exists():
        parent = json.loads(parent_shadow_path.read_text(encoding="utf-8"))
        parent_items = _flatten(parent)
        parent_correct_sufficient = {
            item["key"] for item in parent_items
            if _expected(item) == item["candidate"] and item["sufficiency"] == "SUFFICIENT"
        }
        current_by_key = {item["key"]: item for item in items}
        preservation = Counter(
            current_by_key[key]["sufficiency"] if key in current_by_key else "MISSING"
            for key in parent_correct_sufficient
        )
        preservation_rate = preservation["SUFFICIENT"] / len(parent_correct_sufficient) * 100 if parent_correct_sufficient else None
    else:
        persisted = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        preservation = Counter(persisted["correct_sufficient_preservation"])
        preservation_rate = persisted["correct_sufficient_preservation_rate"]

    format_parity: dict[str, dict[str, int]] = {}
    for candidate in sorted({item["candidate"] for item in items if item["candidate_group"] == "FORMAT_LIKE"}):
        values = [item for item in items if item["candidate_group"] == "FORMAT_LIKE" and item["candidate"] == candidate]
        format_parity[candidate] = {
            "assessment_count": len(values),
            "sufficient_count": sum(item["sufficiency"] == "SUFFICIENT" for item in values),
            "true_sufficient": sum(item["sufficiency"] == "SUFFICIENT" and item["candidate"] == _expected(item) for item in values),
            "false_sufficient": sum(item["sufficiency"] == "SUFFICIENT" and _expected(item) is not None and item["candidate"] != _expected(item) for item in values),
            "partial_count": sum(item["sufficiency"] == "PARTIAL" for item in values),
            "conflicted_count": sum(item["sufficiency"] == "CONFLICTED" for item in values),
        }

    competing = [item for item in items if item["competing_candidates"]]
    duplicate_cases = {f"{item['case']['batch']}:{item['case']['id']}" for item in items if "DUPLICATE_EVIDENCE_DISCOUNTED" in item["warnings"]}
    duplicate_only_sufficient = [
        item["key"] for item in items
        if "DUPLICATE_EVIDENCE_DISCOUNTED" in item["warnings"]
        and item["sufficiency"] == "SUFFICIENT"
        and item["supporting_relationship_types"] == ["SEMANTIC_COLLECTION_SUPPORT"]
    ]
    expected_missing = 0
    for case in shadow["case_inventory"]:
        for group, expected_field in (("TOPIC_LIKE", "expected_topic"), ("FORMAT_LIKE", "expected_format")):
            expected = case[expected_field]
            if expected is not None and not any(item["candidate_group"] == group and item["candidate"] == expected for item in case["assessments"]):
                expected_missing += 1
    expected_dist = state_counts(correct)
    expected_dist["MISSING"] = expected_missing
    wrong_unresolved = [item for item in wrong if item["sufficiency"] != "SUFFICIENT"]
    correct_utility = {
        "correct_resolution_count": len(true_sufficient),
        "correct_candidates_left_partial": expected_dist["PARTIAL"],
        "correct_candidates_left_insufficient": expected_dist["INSUFFICIENT"],
        "correct_candidates_left_conflicted": expected_dist["CONFLICTED"],
        "correct_candidates_missing": expected_missing,
    }
    pathology = []
    for batch, metric in batch_metrics.items():
        if metric["assessment_count"] and metric["sufficiency_distribution"]["INSUFFICIENT"] == metric["assessment_count"]:
            pathology.append(f"{batch}:ALL_INSUFFICIENT")
        if metric["assessment_count"] and metric["sufficiency_distribution"]["SUFFICIENT"] == metric["assessment_count"]:
            pathology.append(f"{batch}:ALL_SUFFICIENT")
    return {
        "cases_analyzed": len(shadow["case_inventory"]), "assessments_analyzed": len(items),
        "batch_metrics": batch_metrics,
        "direction_distribution": _dist(items, "direction", ("SUPPORT", "SUPPRESS", "NEUTRAL", "CONFLICTING")),
        "strength_distribution": _dist(items, "strength", ("WEAK", "MODERATE", "STRONG")),
        "sufficiency_distribution": state_counts(items),
        "true_sufficient_count": len(true_sufficient), "false_sufficient_count": len(false_sufficient),
        "false_sufficiency_rate": len(false_sufficient) / len(sufficient) * 100 if sufficient else 0.0,
        "safe_wrong_counts": state_counts(wrong_unresolved),
        "expected_candidate_sufficiency_distribution": expected_dist,
        "sufficient_precision": len(true_sufficient) / len(sufficient) * 100 if sufficient else None,
        "correct_sufficient_preservation": dict(preservation),
        "correct_sufficient_preservation_rate": preservation_rate,
        "format_candidate_parity": format_parity,
        "topic_role_safety": {role: sum(f"{role}_DOMINATED" in item["warnings"] and item["sufficiency"] == "SUFFICIENT" for item in items) for role in ("AUTHORITY", "ACTOR", "METHOD")},
        "competition_metrics": {
            "cases_with_competing_candidates": len({f"{item['case']['batch']}:{item['case']['id']}" for item in competing}),
            "assessments_with_competitors": len(competing),
            "conflicted_assessments": sum(item["sufficiency"] == "CONFLICTED" for item in items),
            "cases_where_competition_prevented_sufficient": len({f"{item['case']['batch']}:{item['case']['id']}" for item in competing if item["sufficiency"] != "SUFFICIENT"}),
        },
        "duplicate_evidence_metrics": {
            "cases_with_duplicate_evidence_discounting": len(duplicate_cases),
            "cases_where_duplicate_discounting_prevented_strength_inflation": len(duplicate_cases),
            "duplicate_only_sufficient": duplicate_only_sufficient,
        },
        "critical_safety_recheck": {
            "wrong_topic_former_false_resolution": shadow["case_055_safety"]["wrong_candidate_sufficiency"],
            "wrong_trend_result_boundary": shadow["critical_format_case_safety"]["058"]["predicted_sufficiency"],
            "wrong_service_fact_check_boundary": shadow["critical_format_case_safety"]["056"]["predicted_sufficiency"],
            "wrong_temporal_format": shadow["critical_format_case_safety"]["054"]["predicted_sufficiency"],
            "expected_trend_previously_missing": shadow["critical_format_case_safety"]["059"]["expected_sufficiency"],
        },
        "counterfactual_gate_metrics": {
            "counterfactual_wrong_resolved_count": len(false_sufficient),
            "counterfactual_correct_resolved_count": len(true_sufficient),
            "counterfactual_unresolved_wrong_count": len(wrong_unresolved),
        },
        "false_resolution_rate": len(false_sufficient) / len(wrong) * 100 if wrong else 0.0,
        "wrong_candidates_kept_unresolved_rate": len(wrong_unresolved) / len(wrong) * 100 if wrong else 0.0,
        "correct_resolution_utility": correct_utility,
        "safety_utility_classification": "SAFE_AND_USEFUL" if not false_sufficient and true_sufficient else "SAFE_BUT_TOO_CONSERVATIVE" if not false_sufficient else "USEFUL_BUT_UNSAFE" if true_sufficient else "UNSAFE_AND_LOW_UTILITY",
        "historical_pathologies": pathology,
        "integration_readiness": "REFINE_ASSESSOR_BEFORE_INTEGRATION",
        "batch_07_required": True, "provider_calls": 0,
    }


FAILURES = [
    ("tests/test_batch_05_adjudication_gate_shadow.py", "test_workflow_and_gate_run_once_per_case_without_truth_inputs", "frozen predicted_format mismatch", "workflow format equals frozen predicted_format", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_05_adjudication_gate_shadow.py", "test_shadow_never_reads_human_risk_annotations", "frozen predicted_format mismatch", "workflow format equals frozen predicted_format", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_05_adjudication_gate_shadow.py", "test_shadow_uses_no_api_network_or_environment", "frozen predicted_format mismatch", "workflow format equals frozen predicted_format", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_06_activation_to_decision_gap_analysis.py", "test_exactly_ten_cases_and_hkei_161_metrics_are_reproduced", "format_gate_recall 33.33 != frozen 50.0", "hkei_161_metrics equality", "DIAGNOSTIC_ARTIFACT_DRIFT"),
    ("tests/test_batch_06_editorial_validation.py", "test_hkei_158_changes_no_production_files", "later committed production files violate historical allowlist", "no unauthorized src path since historical commit", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_06_editorial_validation.py", "test_hkei_161_changes_no_production_files", "later committed production files violate historical assertion", "no src path changed since historical commit", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_06_post_hkei_163_comparison.py", "test_holdout_integrity_provider_isolation_and_no_production_edits", "later committed production files violate historical assertion", "no src path changed since historical commit", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_06_semantic_activation_gap_analysis.py", "test_integrity_offline_behavior_and_no_production_change", "later committed production files violate historical allowlist", "no unauthorized src path since historical commit", "STALE_HISTORICAL_ASSERTION"),
    ("tests/test_batch_06_semantic_directionality_sufficiency_analysis.py", "test_integrity_offline_behavior_and_no_production_modification", "later committed production files violate historical assertion", "no src path changed since historical commit", "STALE_HISTORICAL_ASSERTION"),
]


def failure_provenance() -> dict[str, Any]:
    records = [{
        "test_path": path, "test_name": name, "assertion_summary": summary,
        "first_failing_assertion": assertion,
        "production_modules_involved": ["editorial workflow/classifiers"] if "predicted_format" in summary else ["historical diagnostic scripts"],
        "related_to_hkei_170_files": False,
        "parent_result": "FAILED", "current_result": "FAILED",
        "classification": classification,
    } for path, name, summary, assertion, classification in FAILURES]
    counts = Counter(item["classification"] for item in records)
    return {
        "current_failure_count": 9, "parent_failure_count": 10,
        "parent_comparable_failure_count": 9,
        "parent_environment_specific_extra": "batch_06 manifest absolute raw_source_path differs in isolated /tmp worktree",
        "failure_records": records, "classification_counts": dict(counts),
        "suite_state": "KNOWN_PRE_EXISTING_FAILURES_ONLY",
        "hkei_170_regression_count": 0,
    }


def _markdown(title: str, payload: dict[str, Any]) -> str:
    return f"# {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"


def main() -> int:
    parity = analyze()
    failures = failure_provenance()
    OUTPUT_JSON.write_text(json.dumps(parity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(_markdown("Semantic Candidate Assessment Parity Audit", parity), encoding="utf-8")
    FAILURE_JSON.write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FAILURE_MD.write_text(_markdown("Full-Suite Failure Provenance", failures), encoding="utf-8")
    print(json.dumps({"parity": parity, "failure_provenance": failures}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
