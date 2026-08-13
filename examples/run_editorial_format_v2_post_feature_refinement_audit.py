"""Re-audit Editorial Format V2 after the isolated HKEI-192 extractor change."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples import run_editorial_format_v2_cross_batch_audit as baseline_runner  # noqa: E402
from src.formatting.editorial_format import EditorialFormat  # noqa: E402
from src.formatting.editorial_treatment_feature import EditorialTreatmentFeature  # noqa: E402


BASELINE_PATH = PROJECT_ROOT / "benchmark" / "editorial_format_v2_cross_batch_audit.json"
OUTPUT_JSON = PROJECT_ROOT / "benchmark" / "editorial_format_v2_post_feature_refinement_audit.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark" / "editorial_format_v2_post_feature_refinement_audit.md"
FROZEN_DIGESTS = {
    "src/formatting/editorial_format_profile_evaluator.py": "93630fb95333c17b0f629eeb35eac5d42d3986637146e6b769cd48b2fadfea92",
    "src/formatting/editorial_format_v2_classifier.py": "93e091d3c6ecc1fec67ea5e4bc432f184e65fb4cbdf885c78ce1c32f7dc69f1a",
    "src/formatting/deterministic_editorial_format_classifier.py": "a332c14f12c7cb6bad0fab214d1ff44512ccc9bbacd6f9ef9f86f262c278c117",
}


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _load_baseline() -> dict[str, Any]:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    required = {
        "cases_evaluated": 60,
        "v1_accuracy": 55.00000000000001,
        "v2_accuracy": 41.66666666666667,
        "v2_improvements": 12,
        "v2_regressions": 20,
        "wrong_to_wrong_changes": 12,
        "expected_profile_complete_rate": 30.0,
        "expected_profile_partial_rate": 0.0,
        "expected_profile_incomplete_rate": 70.0,
    }
    if any(baseline.get(key) != value for key, value in required.items()):
        raise RuntimeError("HKEI-191 baseline does not match the frozen contract")
    return baseline


def _verify_frozen_production() -> None:
    for relative, expected in FROZEN_DIGESTS.items():
        actual = hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"UNEXPECTED_PRODUCTION_DIFFERENCE: {relative}")


def _indexed(cases: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(case["batch"], case["id"]): case for case in cases}


def _generality(batch: dict[str, Any]) -> str:
    gains = sum(item["newly_correct"] > item["newly_wrong"] for item in batch.values())
    losses = sum(item["newly_wrong"] > item["newly_correct"] for item in batch.values())
    net = sum(item["newly_correct"] - item["newly_wrong"] for item in batch.values())
    if net < 0:
        return "REGRESSION"
    if net == 0 and gains == 0:
        return "NO_IMPROVEMENT"
    if gains >= 4 and losses == 0:
        return "BROAD_GENERALIZED_IMPROVEMENT"
    if gains >= 2 and losses <= 1:
        return "MULTI_BATCH_IMPROVEMENT"
    if gains == 1 and losses == 0:
        return "BATCH_CONCENTRATED_IMPROVEMENT"
    return "MIXED"


def _assessment(summary: dict[str, Any]) -> str:
    accuracy = summary["current_v2_accuracy"]
    improvements = summary["current_v2_improvements"]
    regressions = summary["current_v2_regressions"]
    if accuracy >= 80 and summary["cross_batch_generality"] == "BROAD_GENERALIZED_IMPROVEMENT" and regressions <= 3:
        return "EXCELLENT"
    if accuracy >= 70 and improvements > regressions and summary["expected_profile_complete_rate_after"] > 30:
        return "STRONG"
    if accuracy > summary["previous_v2_accuracy"] and regressions <= improvements:
        return "PROMISING"
    if summary["net_case_gain"] > 0:
        return "MIXED"
    if accuracy < summary["previous_v2_accuracy"]:
        return "REGRESSION"
    return "WEAK"


def _readiness(summary: dict[str, Any]) -> str:
    if summary["offline_assessment"] in {"EXCELLENT", "STRONG"}:
        return "READY_FOR_NEW_UNTOUCHED_HOLDOUT"
    owners = summary["failure_ownership_after"]
    dominant = max(owners, key=owners.get) if any(owners.values()) else "OTHER"
    if dominant == "FEATURE_EXTRACTION":
        return "V2_NOT_READY_FOR_HOLDOUT"
    if dominant == "PROFILE_EVALUATION":
        return "ONE_GENERIC_PROFILE_REFINEMENT_JUSTIFIED"
    if dominant in {"CANDIDATE_COMPETITION", "FINAL_SELECTION"}:
        return "ONE_GENERIC_SELECTION_REFINEMENT_JUSTIFIED"
    return "KEEP_V2_DIAGNOSTIC_ONLY"


def analyze() -> dict[str, Any]:
    _verify_frozen_production()
    previous = _load_baseline()
    current = baseline_runner.analyze()
    old_cases, new_cases = _indexed(previous["cases"]), _indexed(current["cases"])
    if set(old_cases) != set(new_cases):
        raise RuntimeError("HKEI-191 evaluable case set changed")

    newly_correct = [key for key in new_cases if not old_cases[key]["v2_correct"] and new_cases[key]["v2_correct"]]
    newly_wrong = [key for key in new_cases if old_cases[key]["v2_correct"] and not new_cases[key]["v2_correct"]]
    batch_metrics: dict[str, Any] = {}
    for batch_id in baseline_runner.BATCH_IDS:
        old = previous["batch_metrics"][batch_id]
        now = current["batch_metrics"][batch_id]
        keys = [key for key in new_cases if key[0] == batch_id]
        batch_metrics[batch_id] = {
            "case_count": now["case_count"],
            "v1_accuracy": now["v1_accuracy"],
            "previous_v2_accuracy": old["v2_accuracy"],
            "current_v2_accuracy": now["v2_accuracy"],
            "delta_vs_v1": now["v2_accuracy"] - now["v1_accuracy"],
            "delta_vs_previous_v2": now["v2_accuracy"] - old["v2_accuracy"],
            "improvements_vs_v1": now["improvements"],
            "regressions_vs_v1": now["regressions"],
            "newly_correct": sum(key in newly_correct for key in keys),
            "newly_wrong": sum(key in newly_wrong for key in keys),
        }

    format_metrics: dict[str, Any] = {}
    for label in EditorialFormat:
        old = previous["format_metrics"][label.value]
        now = current["format_metrics"][label.value]
        format_metrics[label.value] = {
            "support": now["support"], "v1_correct": now["v1_correct"],
            "previous_v2_correct": old["v2_correct"], "current_v2_correct": now["v2_correct"],
            "current_v2_accuracy": now["v2_accuracy"],
            "delta_vs_previous_v2": now["v2_accuracy"] - old["v2_accuracy"],
            "delta_vs_v1": now["v2_accuracy"] - now["v1_accuracy"],
        }

    feature_delta = {}
    for feature in EditorialTreatmentFeature:
        old_count = previous["feature_coverage"][feature.value]["cases"]
        new_count = current["feature_coverage"][feature.value]["cases"]
        activated = [key for key in new_cases if feature.value not in old_cases[key]["treatment_features"] and feature.value in new_cases[key]["treatment_features"]]
        feature_delta[feature.value] = {
            "previous_cases_detected": old_count,
            "current_cases_detected": new_count,
            "delta": new_count - old_count,
            "new_activation_correct_profile": sum(new_cases[key]["expected_profile_completeness"] != "INCOMPLETE" for key in activated),
            "new_activation_wrong_profile": sum(new_cases[key]["expected_profile_completeness"] == "INCOMPLETE" for key in activated),
            "new_activation_improvements": sum(key in newly_correct for key in activated),
            "new_activation_regressions": sum(key in newly_wrong for key in activated),
        }

    analysis_cases = [case for case in current["cases"] if case["v2_format"] == "ANALYSIS"]
    false_analysis = Counter(case["expected_format"] for case in analysis_cases if not case["v2_correct"])
    expected_completeness = Counter(case["expected_profile_completeness"] for case in current["cases"])
    current_confusion = current["v2_confusion_matrix"]
    summary = {
        "audit_type": "OFFLINE_POST_HKEI_192_SHADOW_AUDIT",
        "baseline_commit": "HKEI-191_PERSISTED",
        "changed_commit": "f960e0b03c328a4d7603d0855c916f96df0cc205",
        "cases_evaluated": current["cases_evaluated"],
        "v1_accuracy": current["v1_accuracy"],
        "previous_v2_accuracy": previous["v2_accuracy"],
        "current_v2_accuracy": current["v2_accuracy"],
        "v2_delta_vs_previous": current["v2_accuracy"] - previous["v2_accuracy"],
        "v2_delta_vs_v1": current["v2_accuracy"] - current["v1_accuracy"],
        "previous_v2_improvements": previous["v2_improvements"],
        "current_v2_improvements": current["v2_improvements"],
        "previous_v2_regressions": previous["v2_regressions"],
        "current_v2_regressions": current["v2_regressions"],
        "previous_wrong_to_wrong_changes": previous["wrong_to_wrong_changes"],
        "current_wrong_to_wrong_changes": current["wrong_to_wrong_changes"],
        "unchanged_correct": current["unchanged_correct"],
        "unchanged_wrong": current["unchanged_wrong"],
        "newly_correct_cases_after_hkei_192": len(newly_correct),
        "newly_wrong_cases_after_hkei_192": len(newly_wrong),
        "net_case_gain": len(newly_correct) - len(newly_wrong),
        "batch_metrics": batch_metrics,
        "format_metrics": format_metrics,
        "cross_batch_generality": _generality(batch_metrics),
        "expected_profile_complete_rate_before": previous["expected_profile_complete_rate"],
        "expected_profile_complete_rate_after": _percentage(expected_completeness["COMPLETE"], len(new_cases)),
        "expected_profile_partial_rate": _percentage(expected_completeness["PARTIAL"], len(new_cases)),
        "expected_profile_incomplete_rate_before": previous["expected_profile_incomplete_rate"],
        "expected_profile_incomplete_rate_after": _percentage(expected_completeness["INCOMPLETE"], len(new_cases)),
        "selected_completeness_distribution": current["selected_completeness_distribution"],
        "feature_coverage_deltas": feature_delta,
        "standard_news_accuracy": format_metrics["STANDARD_NEWS"]["current_v2_accuracy"],
        "standard_news_to_analysis_count": current_confusion["STANDARD_NEWS"]["ANALYSIS"],
        "previous_standard_news_to_analysis_count": previous["v2_confusion_matrix"]["STANDARD_NEWS"]["ANALYSIS"],
        "analysis_predictions": len(analysis_cases),
        "correct_analysis_predictions": sum(case["v2_correct"] for case in analysis_cases),
        "false_analysis_predictions": len(analysis_cases) - sum(case["v2_correct"] for case in analysis_cases),
        "false_analysis_by_expected_format": dict(sorted(false_analysis.items())),
        "result_report": {
            "expected": format_metrics["RESULT_REPORT"]["support"],
            "correct": format_metrics["RESULT_REPORT"]["current_v2_correct"],
            "missed": format_metrics["RESULT_REPORT"]["support"] - format_metrics["RESULT_REPORT"]["current_v2_correct"],
            "false_positive": sum(current_confusion[label.value]["RESULT_REPORT"] for label in EditorialFormat if label.value != "RESULT_REPORT"),
            "trend_update_boundary": current["result_report_trend_update_boundary"],
        },
        "fact_check": {
            "expected": format_metrics["FACT_CHECK"]["support"],
            "correct": format_metrics["FACT_CHECK"]["current_v2_correct"],
            "missed": current["fact_check_boundary"]["v2_missed"],
            "false_positive": current["fact_check_boundary"]["v2_false"],
        },
        "ambiguity_distribution": current["ambiguity_distribution"],
        "previous_ambiguity_distribution": previous["ambiguity_distribution"],
        "confidence_distribution": current["confidence_distribution"],
        "false_high_confidence_cases": current["false_high_confidence_cases"],
        "failure_ownership_before": previous["failure_ownership_counts"],
        "failure_ownership_after": current["failure_ownership_counts"],
        "regression_feature_concentration": {
            feature.value: sum(feature.value in new_cases[key]["treatment_features"] for key in newly_wrong)
            for feature in EditorialTreatmentFeature
        },
        "v1_format_mutated": False,
        "reader_intent_mutated": False,
        "gate_mutated": False,
        "provider_calls": 0,
        "case_keys": [f"{key[0]}:{key[1]}" for key in sorted(new_cases)],
    }
    summary["offline_assessment"] = _assessment(summary)
    summary["holdout_readiness"] = _readiness(summary)
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    batches = "\n".join(
        f"| {name} | {item['case_count']} | {item['v1_accuracy']:.2f}% | {item['previous_v2_accuracy']:.2f}% | {item['current_v2_accuracy']:.2f}% |"
        for name, item in summary["batch_metrics"].items()
    )
    return f"""# Editorial Format V2 Post-Feature-Refinement Audit

Offline assessment: {summary['offline_assessment']}

Holdout readiness: {summary['holdout_readiness']}

Cases: {summary['cases_evaluated']}

V1 / previous V2 / current V2: {summary['v1_accuracy']:.2f}% / {summary['previous_v2_accuracy']:.2f}% / {summary['current_v2_accuracy']:.2f}%

| Batch | Cases | V1 | Previous V2 | Current V2 |
|---|---:|---:|---:|---:|
{batches}

This is an offline historical shadow audit. No source body is persisted, no
provider was called, and no benchmark result was used to tune production logic.
"""


def main() -> int:
    summary = analyze()
    OUTPUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
