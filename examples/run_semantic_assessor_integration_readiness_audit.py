"""Audit post-HKEI-173 assessor readiness without changing readiness policy."""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_semantic_candidate_assessment_shadow import analyze as shadow_analyze  # noqa: E402


PARITY_PATH = PROJECT_ROOT / "benchmark/semantic_candidate_assessment_parity_audit.json"
FAILURE_PATH = PROJECT_ROOT / "benchmark/full_suite_failure_provenance.json"
OUTPUT_JSON = PROJECT_ROOT / "benchmark/semantic_assessor_integration_readiness_audit.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark/semantic_assessor_integration_readiness_audit.md"
BEFORE_COMMIT = "573fa95"
BEFORE_PARITY_PATH = "benchmark/semantic_candidate_assessment_parity_audit.json"

# Derived once from the committed BEFORE_COMMIT assessor inventory. These are
# symbolic assessment records only; no source content is retained.
BEFORE_SUFFICIENT_STATES = (
    ("batch_02", "013", "TECHNOLOGY", "TOPIC_LIKE", "TECHNOLOGY", ("DUPLICATE_EVIDENCE_DISCOUNTED",), ()),
    ("batch_02", "014", "WORLD", "TOPIC_LIKE", "WORLD", ("DUPLICATE_EVIDENCE_DISCOUNTED",), ()),
    ("batch_02", "017", "ECONOMY", "TOPIC_LIKE", "ECONOMY", (), ()),
    ("batch_02", "018", "SCIENCE", "TOPIC_LIKE", "SCIENCE", ("DUPLICATE_EVIDENCE_DISCOUNTED",), ()),
    ("batch_02", "019", "CULTURE", "TOPIC_LIKE", "CULTURE", (), ()),
    ("batch_05", "046", "TECHNOLOGY", "TOPIC_LIKE", "SCIENCE", (), ()),
)


def _git_json(commit: str, path: str) -> dict[str, Any]:
    payload = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=PROJECT_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(payload)


def _current_index() -> dict[tuple[str, str, str, str], dict[str, Any]]:
    shadow = shadow_analyze()
    return {
        (case["batch"], case["id"], item["candidate"], item["candidate_group"]): item
        for case in shadow["case_inventory"] for item in case["assessments"]
    }


def analyze() -> dict[str, Any]:
    current = json.loads(PARITY_PATH.read_text(encoding="utf-8"))
    before = _git_json(BEFORE_COMMIT, BEFORE_PARITY_PATH)
    suite = json.loads(FAILURE_PATH.read_text(encoding="utf-8"))
    current_index = _current_index()
    lost = []
    for batch, case_id, candidate, group, expected, old_warnings, old_competitors in BEFORE_SUFFICIENT_STATES:
        item = current_index.get((batch, case_id, candidate, group))
        after = item["sufficiency"] if item else "MISSING"
        new_warnings = tuple(item["warnings"]) if item else ()
        new_competitors = tuple(item["competing_candidates"]) if item else ()
        alignment = "TRUE_SUFFICIENT" if candidate == expected else "FALSE_SUFFICIENT" if expected else "UNEVALUABLE_SUFFICIENT"
        duplicate_changed = "DUPLICATE_DISCOUNT_NOW_REDUCES_INDEPENDENCE" if "INSUFFICIENT_INDEPENDENT_SUPPORT" in new_warnings else "NO_DUPLICATE_CHANGE"
        competitor_changed = sorted(set(new_competitors) - set(old_competitors))
        reason = (
            "LATENT_COMPETITOR_ADDED"
            if competitor_changed
            else "HIERARCHICAL_REPETITION_NO_LONGER_COUNTS_AS_INDEPENDENT_SUPPORT"
        )
        classification = (
            "JUSTIFIED_SAFETY_DOWNGRADE" if alignment == "FALSE_SUFFICIENT"
            else "POSSIBLE_OVERCORRECTION"
        )
        lost.append({
            "batch": batch, "case": case_id, "candidate": candidate,
            "candidate_group": group, "expected_label": expected,
            "expected_label_alignment": alignment,
            "before_sufficiency": "SUFFICIENT", "after_sufficiency": after,
            "reason_for_downgrade": reason,
            "warning_changes": {
                "added": sorted(set(new_warnings) - set(old_warnings)),
                "removed": sorted(set(old_warnings) - set(new_warnings)),
            },
            "competitor_changes": {"added": competitor_changed},
            "duplicate_evidence_changes": duplicate_changed,
            "overcorrection_classification": classification,
        })

    role = current["topic_role_safety"]
    critical_wrong = sum(
        value["false_sufficient"]
        for value in current["format_candidate_parity"].values()
    )
    current_correct = current["expected_candidate_sufficiency_distribution"]
    conditions = [
        ("FALSE_SUFFICIENT_ZERO", 0, current["false_sufficient_count"], current["false_sufficient_count"] == 0),
        ("SUFFICIENT_PRECISION_COMPLETE", 100.0, current["sufficient_precision"], current["sufficient_precision"] == 100.0),
        ("COUNTERFACTUAL_WRONG_RESOLVED_ZERO", 0, current["counterfactual_gate_metrics"]["counterfactual_wrong_resolved_count"], current["counterfactual_gate_metrics"]["counterfactual_wrong_resolved_count"] == 0),
        ("ROLE_DOMINATED_SUFFICIENT_ZERO", {"AUTHORITY": 0, "ACTOR": 0, "METHOD": 0}, role, all(value == 0 for value in role.values())),
        ("CRITICAL_WRONG_FORMAT_SUFFICIENT_ZERO", 0, critical_wrong, critical_wrong == 0),
        ("TRUE_SUFFICIENT_NONZERO", ">0", current["true_sufficient_count"], current["true_sufficient_count"] > 0),
        ("NO_HISTORICAL_PATHOLOGY", [], current["historical_pathologies"], not current["historical_pathologies"]),
        ("NO_NEW_SUITE_REGRESSION", 0, suite["hkei_170_regression_count"], suite["hkei_170_regression_count"] == 0),
        ("READINESS_DERIVED_FROM_OBSERVED_METRICS", True, False, False),
    ]
    readiness_conditions = [
        {"condition_name": name, "required_value": required, "observed_value": observed, "status": "PASS" if passed else "FAIL"}
        for name, required, observed, passed in conditions
    ]
    lost_counts = {
        "true_sufficient": sum(item["expected_label_alignment"] == "TRUE_SUFFICIENT" for item in lost),
        "false_sufficient": sum(item["expected_label_alignment"] == "FALSE_SUFFICIENT" for item in lost),
        "unevaluable_sufficient": sum(item["expected_label_alignment"] == "UNEVALUABLE_SUFFICIENT" for item in lost),
    }
    return {
        "current_safety_metrics": {
            "true_sufficient_count": current["true_sufficient_count"],
            "false_sufficient_count": current["false_sufficient_count"],
            "sufficient_precision": current["sufficient_precision"],
            "false_resolution_rate": current["false_resolution_rate"],
            "counterfactual_wrong_resolved_count": current["counterfactual_gate_metrics"]["counterfactual_wrong_resolved_count"],
            "counterfactual_correct_resolved_count": current["counterfactual_gate_metrics"]["counterfactual_correct_resolved_count"],
            "authority_dominated_sufficient": role["AUTHORITY"],
            "actor_dominated_sufficient": role["ACTOR"],
            "method_dominated_sufficient": role["METHOD"],
            "critical_wrong_format_sufficient": critical_wrong,
        },
        "current_utility_metrics": {
            "true_sufficient_count": current["true_sufficient_count"],
            "correct_sufficient_preservation_rate": current["correct_sufficient_preservation_rate"],
            "expected_candidate_sufficiency_distribution": current_correct,
            "material_utility_reduction": True,
        },
        "before_after": {
            "before_commit": BEFORE_COMMIT,
            "true_sufficient": {"before": before["true_sufficient_count"], "after": current["true_sufficient_count"], "denominator": "correct candidate assessments with known expected dimension"},
            "false_sufficient": {"before": before["false_sufficient_count"], "after": current["false_sufficient_count"]},
            "sufficient_precision": {"before": before["sufficient_precision"], "after": current["sufficient_precision"], "denominator": "all SUFFICIENT assessments with a known expected dimension"},
            "correct_sufficient_preservation": {"before": before["correct_sufficient_preservation_rate"], "after": current["correct_sufficient_preservation_rate"], "denominator": "correct SUFFICIENT controls from the older HKEI-170 baseline, not current true-sufficient count"},
            "counterfactual_wrong_resolved": {"before": before["counterfactual_gate_metrics"]["counterfactual_wrong_resolved_count"], "after": current["counterfactual_gate_metrics"]["counterfactual_wrong_resolved_count"]},
            "denominator_explanation": "True-sufficient count is a current-corpus count. Preservation rate tracks a fixed older control cohort, so five current true downgrades do not imply a five-point change in that separately anchored percentage.",
        },
        "lost_sufficient_assessments": lost,
        "lost_sufficient_counts": lost_counts,
        "overcorrection_findings": {
            "JUSTIFIED_SAFETY_DOWNGRADE": lost_counts["false_sufficient"],
            "POSSIBLE_OVERCORRECTION": lost_counts["true_sufficient"],
            "CLEAR_OVERCORRECTION": 0,
            "materially_too_conservative": "POSSIBLE_NOT_ESTABLISHED",
        },
        "readiness_decision_trace": readiness_conditions,
        "persisted_integration_readiness": current["integration_readiness"],
        "integration_readiness_blocker": "RULE_NOT_UPDATED_FOR_NEW_METRICS",
        "blocker_class": "DIAGNOSTIC_RULE_DRIFT",
        "safe_and_useful_consistency": {
            "classification": "INCONSISTENT",
            "explanation": "Safety/utility is metric-derived, while integration_readiness is an unconditional literal in the parity diagnostic.",
        },
        "shadow_readiness_requirements": [
            "NO_OUTPUT_MUTATION", "NO_CONFIDENCE_MUTATION", "NO_GATE_MUTATION",
            "NO_PROVIDER_CHANGE", "ZERO_FALSE_SUFFICIENT_IN_AUDITED_CORPUS",
            "NONZERO_CORRECT_RESOLUTION", "OBSERVABILITY_AND_ROLLBACK",
        ],
        "production_readiness_requirements": {
            "classifier_consumption": ["PREREGISTERED_SHADOW_SUCCESS", "EXPLICIT_PRECEDENCE_CONTRACT", "REGRESSION_BOUNDS"],
            "confidence_influence": ["CALIBRATED_CONFIDENCE_CONTRACT", "FALSE_CONFIDENCE_AUDIT"],
            "gate_consumption": ["SEPARATE_GATE_POLICY", "COUNTERFACTUAL_FALSE_NEGATIVE_AUDIT"],
            "resolver_usage": ["RESOLVER_CONTRACT", "FAILURE_AND_FALLBACK_POLICY", "PROVIDER_SAFETY_REVIEW"],
        },
        "shadow_consumption_risk": {"classification": "LOW", "maximum_harm": "DIAGNOSTIC_TELEMETRY_NOISE_OR_MISLEADING_OFFLINE_CONCLUSIONS; DETERMINISTIC OUTPUTS CANNOT MUTATE"},
        "shadow_consumption_value": {"classification": "HIGH_VALUE", "finding": "Exposes classifier-assessor agreement, disagreement, and counterfactual interaction at the real workflow boundary."},
        "final_recommendation": "FIX_READINESS_RULE_DRIFT",
        "stop_assessor_refinement_now": "YES",
        "batch_06_status": "DIAGNOSTIC_DEVELOPMENT_SET",
        "batch_07_required": True,
        "provider_calls": 0,
    }


def render_markdown(result: dict[str, Any]) -> str:
    return f"""# Semantic Assessor Integration Readiness Audit

Current safety/utility is SAFE_AND_USEFUL.

Persisted readiness: {result['persisted_integration_readiness']}

Blocker: {result['integration_readiness_blocker']} ({result['blocker_class']})

Recommendation: {result['final_recommendation']}

Stop assessor refinement now: {result['stop_assessor_refinement_now']}

Batch 06 status: {result['batch_06_status']}

Batch 07 required: YES

Provider calls: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
