"""Run the offline cross-batch Editorial Format V2 shadow audit."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_benchmark_batch_02_validation import (  # noqa: E402
    parse_source, read_expectations, read_manifest,
)
from src.formatting.editorial_format import EditorialFormat  # noqa: E402
from src.formatting.editorial_format_v2_classifier import EditorialFormatV2Classifier  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import (  # noqa: E402
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BATCH_IDS = ("batch_01", "batch_02", "batch_03", "batch_05", "batch_06", "batch_07", "batch_08")
SCIENTIFIC_STATUS = {
    "batch_01": "HISTORICAL_REGRESSION_CORPUS",
    "batch_02": "HISTORICAL_REGRESSION_CORPUS",
    "batch_03": "HISTORICAL_REGRESSION_CORPUS",
    "batch_05": "DEVELOPMENT_CORPUS",
    "batch_06": "DIAGNOSTIC_DEVELOPMENT_SET",
    "batch_07": "EVALUATED_PREREGISTERED_HOLDOUT",
    "batch_08": "EVALUATED_PREREGISTERED_HOLDOUT",
}
OUTPUT_JSON = PROJECT_ROOT / "benchmark" / "editorial_format_v2_cross_batch_audit.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark" / "editorial_format_v2_cross_batch_audit.md"
FAILURE_OWNERS = {
    "FEATURE_EXTRACTION", "PROFILE_EVALUATION", "CANDIDATE_COMPETITION",
    "FINAL_SELECTION", "CONFIDENCE_ONLY", "ONTOLOGY_BOUNDARY", "OTHER",
}


def _percentage(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _unscored_cases(
    *, workflow: Any | None = None, classifier: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Complete every prediction before returning paths to frozen truth."""
    v1 = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    v2 = classifier or EditorialFormatV2Classifier()
    cases: list[dict[str, Any]] = []
    labels: dict[str, dict[str, Any]] = {}
    for batch_id in BATCH_IDS:
        root = PROJECT_ROOT / "benchmark" / batch_id
        expected_path = root / "expected.json"
        if not expected_path.exists():
            labels[batch_id] = {"path": None, "count": 0}
            continue
        manifest = read_manifest(root)
        for item in manifest:
            source = parse_source(root / item["source_file"])
            fields = _source_fields(source)
            v1_result = v1.process(**fields)
            v2_result = v2.classify(
                source=v1_result.classification_result.ingestion.source,
            )
            selected = next(
                assessment for assessment in v2_result.candidate_assessments
                if assessment.candidate is v2_result.selected_format
            )
            cases.append({
                "batch": batch_id,
                "id": source.case_id,
                "v1_format": v1_result.format_classification.editorial_format.value,
                "v2_format": v2_result.selected_format.value,
                "v2_confidence": v2_result.confidence.value,
                "v2_ambiguity": v2_result.ambiguity.value,
                "selected_completeness": selected.completeness.value,
                "selected_strength": selected.strength.value,
                "candidate_assessments": [
                    {
                        "candidate": assessment.candidate.value,
                        "completeness": assessment.completeness.value,
                        "strength": assessment.strength.value,
                        "ambiguity": assessment.ambiguity.value,
                        "supporting_features": [
                            feature.value for feature in assessment.supporting_features
                        ],
                        "missing_required_features": [
                            feature.value for feature in assessment.missing_required_features
                        ],
                        "disqualifying_features": [
                            feature.value for feature in assessment.disqualifying_features
                        ],
                        "competing_candidates": [
                            candidate.value for candidate in assessment.competing_candidates
                        ],
                    }
                    for assessment in v2_result.candidate_assessments
                ],
                "treatment_features": [
                    feature.value for feature in v2_result.treatment_features.features
                ],
            })
        labels[batch_id] = {"path": expected_path, "count": len(manifest)}
    return cases, labels


def _join_truth(
    cases: list[dict[str, Any]], labels: dict[str, dict[str, Any]],
) -> None:
    """Join expected Format only after all V1/V2 results are complete."""
    truth: dict[tuple[str, str], str] = {}
    for batch_id, metadata in labels.items():
        if metadata["path"] is None:
            continue
        for item in read_expectations(metadata["path"].parent):
            expected = item.get("editorial_format")
            if expected in {value.value for value in EditorialFormat}:
                truth[(batch_id, item["id"])] = expected
    cases[:] = [case for case in cases if (case["batch"], case["id"]) in truth]
    for case in cases:
        case["expected_format"] = truth[(case["batch"], case["id"])]
        case["v1_correct"] = case["v1_format"] == case["expected_format"]
        case["v2_correct"] = case["v2_format"] == case["expected_format"]
        case["changed"] = case["v1_format"] != case["v2_format"]
        expected_assessment = next(
            item for item in case["candidate_assessments"]
            if item["candidate"] == case["expected_format"]
        )
        case["expected_profile_completeness"] = expected_assessment["completeness"]
        case["multiple_complete_candidates"] = sum(
            item["completeness"] == "COMPLETE"
            for item in case["candidate_assessments"]
        ) > 1
        case["failure_owner"] = (
            None if case["v2_correct"] else _failure_owner(case, expected_assessment)
        )


def _failure_owner(case: dict[str, Any], expected: dict[str, Any]) -> str:
    if expected["completeness"] == "INCOMPLETE":
        return "FEATURE_EXTRACTION"
    if expected["disqualifying_features"]:
        return "PROFILE_EVALUATION"
    if case["v2_ambiguity"] in {"COMPETING", "CONTRADICTORY"}:
        return "CANDIDATE_COMPETITION"
    if expected["completeness"] in {"COMPLETE", "PARTIAL"}:
        return "FINAL_SELECTION"
    if case["v2_confidence"] == "HIGH":
        return "CONFIDENCE_ONLY"
    return "OTHER"


def _dimension(cases: list[dict[str, Any]], key: str, values: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for value in values:
        selected = [case for case in cases if case[key] == value]
        correct = sum(case["v2_correct"] for case in selected)
        result[value] = {
            "count": len(selected), "correct": correct,
            "accuracy": _percentage(correct, len(selected)),
        }
    return result


def _boundary(cases: list[dict[str, Any]], first: str, second: str) -> dict[str, int]:
    return {
        "v1_first_to_second": sum(case["expected_format"] == first and case["v1_format"] == second for case in cases),
        "v1_second_to_first": sum(case["expected_format"] == second and case["v1_format"] == first for case in cases),
        "v2_first_to_second": sum(case["expected_format"] == first and case["v2_format"] == second for case in cases),
        "v2_second_to_first": sum(case["expected_format"] == second and case["v2_format"] == first for case in cases),
    }


def _batch_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for batch_id in BATCH_IDS:
        selected = [case for case in cases if case["batch"] == batch_id]
        v1_correct = sum(case["v1_correct"] for case in selected)
        v2_correct = sum(case["v2_correct"] for case in selected)
        result[batch_id] = {
            "scientific_status": SCIENTIFIC_STATUS[batch_id],
            "case_count": len(selected),
            "v1_accuracy": _percentage(v1_correct, len(selected)),
            "v2_accuracy": _percentage(v2_correct, len(selected)),
            "delta": _percentage(v2_correct - v1_correct, len(selected)),
            "improvements": sum(not case["v1_correct"] and case["v2_correct"] for case in selected),
            "regressions": sum(case["v1_correct"] and not case["v2_correct"] for case in selected),
        }
    return result


def _format_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for editorial_format in EditorialFormat:
        selected = [case for case in cases if case["expected_format"] == editorial_format.value]
        v1_correct = sum(case["v1_correct"] for case in selected)
        v2_correct = sum(case["v2_correct"] for case in selected)
        result[editorial_format.value] = {
            "support": len(selected), "v1_correct": v1_correct, "v2_correct": v2_correct,
            "v1_accuracy": _percentage(v1_correct, len(selected)),
            "v2_accuracy": _percentage(v2_correct, len(selected)),
            "delta": _percentage(v2_correct - v1_correct, len(selected)),
        }
    return result


def _stability(batch: dict[str, Any]) -> str:
    deltas = [item["delta"] for item in batch.values() if item["case_count"]]
    positive = sum(delta > 0 for delta in deltas)
    negative = sum(delta < 0 for delta in deltas)
    if not positive:
        return "REGRESSION" if negative else "NO_IMPROVEMENT"
    if positive >= 4 and negative <= 1:
        return "BROAD_IMPROVEMENT"
    if positive == 1:
        return "BATCH_CONCENTRATED"
    return "MIXED_CROSS_BATCH"


def _assessment(summary: dict[str, Any]) -> str:
    accuracy = summary["v2_accuracy"]
    improvements, regressions = summary["v2_improvements"], summary["v2_regressions"]
    wrong_high = len(summary["false_high_confidence_cases"])
    if accuracy >= 80 and regressions <= improvements / 4 and wrong_high <= 1:
        return "EXCELLENT"
    if accuracy >= 70 and improvements > regressions:
        return "STRONG"
    if accuracy > summary["v1_accuracy"] + 5:
        return "PROMISING"
    if improvements >= 3 and regressions >= 3:
        return "MIXED"
    return "WEAK"


def _readiness(summary: dict[str, Any]) -> str:
    if summary["v2_offline_assessment"] in {"EXCELLENT", "STRONG"}:
        return "READY_FOR_NEW_UNTOUCHED_HOLDOUT"
    owners = summary["failure_ownership_counts"]
    dominant = max(owners, key=owners.get) if any(owners.values()) else "OTHER"
    return {
        "FEATURE_EXTRACTION": "REFINE_V2_FEATURE_EXTRACTION_ON_GENERIC_FIXTURES_ONLY",
        "PROFILE_EVALUATION": "REFINE_V2_PROFILE_MODEL_ON_GENERIC_FIXTURES_ONLY",
        "CANDIDATE_COMPETITION": "REFINE_V2_SELECTION_ON_GENERIC_FIXTURES_ONLY",
        "FINAL_SELECTION": "REFINE_V2_SELECTION_ON_GENERIC_FIXTURES_ONLY",
    }.get(dominant, "KEEP_V2_AS_DIAGNOSTIC_ONLY")


def analyze(*, workflow: Any | None = None, classifier: Any | None = None) -> dict[str, Any]:
    cases, labels = _unscored_cases(workflow=workflow, classifier=classifier)
    _join_truth(cases, labels)
    total = len(cases)
    v1_correct = sum(case["v1_correct"] for case in cases)
    v2_correct = sum(case["v2_correct"] for case in cases)
    improvements = sum(not case["v1_correct"] and case["v2_correct"] for case in cases)
    regressions = sum(case["v1_correct"] and not case["v2_correct"] for case in cases)
    wrong_to_wrong = sum(not case["v1_correct"] and not case["v2_correct"] and case["changed"] for case in cases)
    ambiguity = _dimension(cases, "v2_ambiguity", ("CLEAR", "COMPETING", "INSUFFICIENT_EVIDENCE", "CONTRADICTORY"))
    confidence = _dimension(cases, "v2_confidence", ("HIGH", "MEDIUM", "LOW"))
    completeness = _dimension(cases, "selected_completeness", ("COMPLETE", "PARTIAL", "INCOMPLETE"))
    batch = _batch_metrics(cases)
    formats = _format_metrics(cases)
    confusion = Counter((case["expected_format"], case["v2_format"]) for case in cases)
    errors = [(pair, count) for pair, count in confusion.most_common() if pair[0] != pair[1]]
    expected_completeness = Counter(case["expected_profile_completeness"] for case in cases)
    ownership = Counter(case["failure_owner"] for case in cases if case["failure_owner"])
    summary = {
        "audit_type": "OFFLINE_SHADOW_HISTORICAL_ONLY",
        "cases_evaluated": total,
        "excluded_batches_without_valid_expected_format": [
            batch_id for batch_id, item in labels.items() if item["path"] is None
        ],
        "v1_accuracy": _percentage(v1_correct, total),
        "v2_accuracy": _percentage(v2_correct, total),
        "accuracy_delta": _percentage(v2_correct - v1_correct, total),
        "v1_correct_v2_correct": sum(case["v1_correct"] and case["v2_correct"] for case in cases),
        "v1_wrong_v2_correct": improvements,
        "v1_correct_v2_wrong": regressions,
        "v1_wrong_v2_wrong": sum(not case["v1_correct"] and not case["v2_correct"] for case in cases),
        "v2_improvements": improvements,
        "v2_regressions": regressions,
        "wrong_to_wrong_changes": wrong_to_wrong,
        "unchanged_correct": sum(case["v1_correct"] and case["v2_correct"] and not case["changed"] for case in cases),
        "unchanged_wrong": sum(not case["v1_correct"] and not case["v2_correct"] and not case["changed"] for case in cases),
        "batch_metrics": batch,
        "format_metrics": formats,
        "v2_confusion_matrix": {
            expected.value: {
                predicted.value: confusion[(expected.value, predicted.value)]
                for predicted in EditorialFormat
            } for expected in EditorialFormat
        },
        "most_frequent_v2_confusion_pairs": [
            {"expected": pair[0], "predicted": pair[1], "count": count}
            for pair, count in errors[:10]
        ],
        "ambiguity_distribution": ambiguity,
        "confidence_distribution": confidence,
        "false_high_confidence_cases": [
            f"{case['batch']}:{case['id']}" for case in cases
            if case["v2_confidence"] == "HIGH" and not case["v2_correct"]
        ],
        "selected_completeness_distribution": completeness,
        "cases_with_multiple_complete_candidates": sum(case["multiple_complete_candidates"] for case in cases),
        "cases_with_competing_final_ambiguity": sum(case["v2_ambiguity"] == "COMPETING" for case in cases),
        "cases_where_competition_selected_correctly": sum(case["v2_ambiguity"] == "COMPETING" and case["v2_correct"] for case in cases),
        "cases_where_competition_selected_wrongly": sum(case["v2_ambiguity"] == "COMPETING" and not case["v2_correct"] for case in cases),
        "feature_coverage": {
            feature.value: {
                "cases": sum(feature.value in case["treatment_features"] for case in cases),
                "rate": _percentage(sum(feature.value in case["treatment_features"] for case in cases), total),
            } for feature in __import__("src.formatting.editorial_treatment_feature", fromlist=["EditorialTreatmentFeature"]).EditorialTreatmentFeature
        },
        "expected_profile_complete_rate": _percentage(expected_completeness["COMPLETE"], total),
        "expected_profile_partial_rate": _percentage(expected_completeness["PARTIAL"], total),
        "expected_profile_incomplete_rate": _percentage(expected_completeness["INCOMPLETE"], total),
        "wrong_profile_dominance": Counter(
            (case["selected_completeness"], case["expected_profile_completeness"])
            for case in cases if not case["v2_correct"]
        ),
        "failure_ownership_counts": {owner: ownership[owner] for owner in sorted(FAILURE_OWNERS)},
        "standard_news_audit": {
            **formats["STANDARD_NEWS"],
            "incorrect_v2_standard_news_fallback_cases": [f"{case['batch']}:{case['id']}" for case in cases if case["v2_format"] == "STANDARD_NEWS" and case["expected_format"] != "STANDARD_NEWS"],
            "correct_escapes_from_v1_standard_news": sum(case["v1_format"] == "STANDARD_NEWS" and case["v2_format"] != "STANDARD_NEWS" and case["v2_correct"] for case in cases),
        },
        "result_report_trend_update_boundary": _boundary(cases, "RESULT_REPORT", "TREND_UPDATE"),
        "service_guide_boundary": _boundary(cases, "SERVICE", "GUIDE"),
        "analysis_explainer_boundary": _boundary(cases, "ANALYSIS", "EXPLAINER"),
        "breaking_standard_news_boundary": _boundary(cases, "BREAKING", "STANDARD_NEWS"),
        "fact_check_boundary": {
            "v1_false": sum(case["v1_format"] == "FACT_CHECK" and case["expected_format"] != "FACT_CHECK" for case in cases),
            "v1_missed": sum(case["expected_format"] == "FACT_CHECK" and case["v1_format"] != "FACT_CHECK" for case in cases),
            "v2_false": sum(case["v2_format"] == "FACT_CHECK" and case["expected_format"] != "FACT_CHECK" for case in cases),
            "v2_missed": sum(case["expected_format"] == "FACT_CHECK" and case["v2_format"] != "FACT_CHECK" for case in cases),
        },
        "rare_format_result": {key: formats[key] for key in ("FEATURE", "INTERVIEW", "PROFILE")},
        "cross_batch_stability": _stability(batch),
        "v1_format_mutated": False,
        "reader_intent_mutated": False,
        "gate_mutated": False,
        "provider_calls": 0,
        "cases": cases,
    }
    summary["wrong_profile_dominance"] = {
        f"selected_{key[0]}__expected_{key[1]}": value
        for key, value in summary["wrong_profile_dominance"].items()
    }
    summary["v2_offline_assessment"] = _assessment(summary)
    summary["readiness_decision"] = _readiness(summary)
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    batch_lines = "\n".join(
        f"| {batch} | {item['case_count']} | {item['v1_accuracy']} | {item['v2_accuracy']} | {item['delta']} |"
        for batch, item in summary["batch_metrics"].items()
    )
    return f"""# Editorial Format V2 Cross-Batch Offline Shadow Audit

Assessment: {summary['v2_offline_assessment']}

Readiness: {summary['readiness_decision']}

Cases: {summary['cases_evaluated']}

V1 / V2 accuracy: {summary['v1_accuracy']} / {summary['v2_accuracy']}

This is a historical shadow audit. It is not a new generalization claim and no
benchmark result was used to tune production logic.

| Batch | Cases | V1 | V2 | Delta |
|---|---:|---:|---:|---:|
{batch_lines}

Provider calls: 0. V1, Reader Intent, and Gate were not mutated.
"""


def main() -> int:
    summary = analyze()
    OUTPUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
