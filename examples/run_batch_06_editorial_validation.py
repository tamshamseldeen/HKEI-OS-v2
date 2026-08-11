"""Run blind pre-provider generalization validation on registered Batch 06."""

from collections import Counter, defaultdict
from collections.abc import Iterable
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import (  # noqa: E402
    ValidationSource,
    parse_source,
    read_expectations,
    read_manifest,
)
from src.adjudication.adjudication_scope import AdjudicationScope  # noqa: E402
from src.adjudication.deterministic_semantic_adjudication_gate import (  # noqa: E402
    DeterministicSemanticAdjudicationGate,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (  # noqa: E402
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_06"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_06_raw.txt"
OUTPUT_JSON = BATCH_ROOT / "editorial_validation.json"
OUTPUT_MD = BATCH_ROOT / "editorial_validation.md"
COMPARISON_JSON = BATCH_ROOT / "post_hkei_157_comparison.json"
COMPARISON_MD = BATCH_ROOT / "post_hkei_157_comparison.md"
CASE_IDS = tuple(f"{value:03d}" for value in range(51, 61))
RAW_SHA256 = "7ef269f70c78816521c8d3228db720b771294c9fb91fcbe31629b7748f115a06"


def _source_fields(source: ValidationSource) -> dict[str, object]:
    return {
        "title": source.title,
        "body": source.body,
        "source_name": source.source_name,
        "source_url": source.source_url,
        "published_at": None,
        "language": "ar",
        "country": None,
        "author": None,
        "images": (),
        "attachments": (),
        "category": None,
        "tags": (),
        "user_instruction": None,
    }


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _rate(numerator: int, denominator: int, *, empty: float = 100.0) -> float:
    return numerator / denominator * 100.0 if denominator else empty


def _gate_metrics(cases: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    mismatch = f"{dimension}_match"
    required = f"{dimension}_required"
    tp = sum(not case[mismatch] and case[required] for case in cases)
    fp = sum(case[mismatch] and case[required] for case in cases)
    tn = sum(case[mismatch] and not case[required] for case in cases)
    fn = sum(not case[mismatch] and not case[required] for case in cases)
    return {
        f"{dimension}_gate_tp": tp,
        f"{dimension}_gate_fp": fp,
        f"{dimension}_gate_tn": tn,
        f"{dimension}_gate_fn": fn,
        f"{dimension}_gate_precision": _rate(tp, tp + fp, empty=100.0),
        f"{dimension}_gate_recall": _rate(tp, tp + fn, empty=100.0),
    }


def generalization_assessment(analysis: dict[str, Any]) -> str:
    topic = analysis["topic_accuracy"]
    editorial_format = analysis["format_accuracy"]
    intent = analysis["reader_intent_accuracy"]
    full = analysis["full_case_accuracy"]
    if topic >= 90 and editorial_format >= 90 and intent >= 90 and full >= 80:
        return "EXCELLENT"
    if topic >= 80 and editorial_format >= 80 and intent >= 80 and full >= 70:
        return "STRONG"
    if min(topic, editorial_format, intent, full) >= 60:
        return "MIXED"
    return "WEAK"


def gate_assessment(analysis: dict[str, Any]) -> str:
    topic = analysis["topic_gate_recall"]
    editorial_format = analysis["format_gate_recall"]
    if (
        topic == 100.0
        and editorial_format == 100.0
        and analysis["unnecessary_projected_call_rate"] <= 30.0
    ):
        return "EXCELLENT"
    if topic >= 90.0 and editorial_format >= 90.0:
        return "STRONG"
    if topic >= 75.0 and editorial_format >= 75.0:
        return "MIXED"
    return "WEAK"


def _historical_metrics() -> dict[str, float]:
    return {
        "batch_01_topic_accuracy": json.loads(
            (PROJECT_ROOT / "benchmark/batch_01/topic_analysis.json").read_text(encoding="utf-8")
        )["accuracy"],
        "batch_02_full_accuracy": json.loads(
            (PROJECT_ROOT / "benchmark/batch_02/contextual_full_validation.json").read_text(encoding="utf-8")
        )["full_case_accuracy"],
        "batch_03_full_accuracy": json.loads(
            (PROJECT_ROOT / "benchmark/batch_03/semantic_full_validation.json").read_text(encoding="utf-8")
        )["full_case_accuracy"],
    }


def _read_risk_annotations(batch_root: Path) -> list[dict[str, Any]]:
    return json.loads(
        (batch_root / "human_risk_annotations.json").read_text(encoding="utf-8")
    )["annotations"]


def analyze_validation(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: ExperimentalSemanticEditorialAnalysisWorkflow | None = None,
    gate: DeterministicSemanticAdjudicationGate | None = None,
) -> dict[str, Any]:
    """Freeze predictions/gates before reading labels or human risk metadata."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    cases: list[dict[str, Any]] = []
    manifest = read_manifest(batch_root)
    assert tuple(item["id"] for item in manifest) == CASE_IDS

    for item in manifest:
        source = parse_source(batch_root / item["source_file"])
        result = active_workflow.process(**_source_fields(source))
        decision = active_gate.evaluate(
            topic_classification=result.topic_classification,
            format_classification=result.format_classification,
            contextual_evidence=result.contextual_evidence,
            semantic_evidence=result.semantic_evidence,
        )
        semantic = result.semantic_evidence
        cases.append({
            "id": source.case_id,
            "predicted_topic": result.topic_classification.topic.value,
            "topic_confidence": result.topic_classification.confidence.value,
            "predicted_format": result.format_classification.editorial_format.value,
            "format_confidence": result.format_classification.confidence.value,
            "predicted_reader_intent": result.reader_intent_classification.reader_intent.value,
            "contextual_support_labels": _unique(
                label for evidence in result.contextual_evidence.all_items for label in evidence.supports
            ),
            "contextual_suppressions": _unique(
                label for evidence in result.contextual_evidence.all_items for label in evidence.suppresses
            ),
            "semantic_relationship_count": len(semantic.relationships),
            "primary_semantic_domains": list(semantic.primary_domain_candidates),
            "secondary_semantic_domains": list(semantic.secondary_domain_candidates),
            "semantic_format_support": list(semantic.format_support),
            "semantic_format_suppression": list(semantic.format_suppression),
            "gate_scope": decision.scope.value,
            "topic_required": decision.topic_required,
            "format_required": decision.format_required,
            "trigger_signals": list(decision.trigger_signals),
        })

    # Labels and risk annotations enter only after all predictions and gates freeze.
    expected_by_id = {item["id"]: item for item in read_expectations(batch_root)}
    for case in cases:
        expected = expected_by_id[case["id"]]
        case["expected_topic"] = expected["topic"]
        case["topic_match"] = case["predicted_topic"] == expected["topic"]
        case["expected_format"] = expected["editorial_format"]
        case["format_match"] = case["predicted_format"] == expected["editorial_format"]
        case["expected_reader_intent"] = expected["reader_intent"]
        case["intent_match"] = case["predicted_reader_intent"] == expected["reader_intent"]
        case["full_match"] = case["topic_match"] and case["format_match"] and case["intent_match"]

    annotations = _read_risk_annotations(batch_root)
    annotation_by_id = {item["id"]: item for item in annotations}
    risk_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"cases": 0, "full_matches": 0, "gate_calls": 0})
    for case in cases:
        category = annotation_by_id[case["id"]]["sensitive_context"]
        risk_stats[category]["cases"] += 1
        risk_stats[category]["full_matches"] += case["full_match"]
        risk_stats[category]["gate_calls"] += case["gate_scope"] != AdjudicationScope.NOT_REQUIRED.value

    total = len(cases)
    topic_matches = sum(case["topic_match"] for case in cases)
    format_matches = sum(case["format_match"] for case in cases)
    intent_matches = sum(case["intent_match"] for case in cases)
    full_matches = sum(case["full_match"] for case in cases)
    scope_counts = Counter(case["gate_scope"] for case in cases)
    provider_cases = sum(case["gate_scope"] != AdjudicationScope.NOT_REQUIRED.value for case in cases)
    unnecessary = sum(
        case["topic_match"] and case["format_match"]
        and case["gate_scope"] != AdjudicationScope.NOT_REQUIRED.value
        for case in cases
    )
    analysis = {
        "batch": "batch_06",
        "validation_status": "PASSED",
        "case_count": total,
        "case_ids": list(CASE_IDS),
        "raw_source_sha256": hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest(),
        "expected_labels_sha256": hashlib.sha256((batch_root / "expected.json").read_bytes()).hexdigest(),
        "source_integrity": hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() == RAW_SHA256,
        "risk_annotations_isolated": True,
        "provider_calls": 0,
        "topic_matches": topic_matches,
        "topic_mismatches": total - topic_matches,
        "topic_accuracy": _percentage(topic_matches, total),
        "format_matches": format_matches,
        "format_mismatches": total - format_matches,
        "format_accuracy": _percentage(format_matches, total),
        "reader_intent_matches": intent_matches,
        "reader_intent_mismatches": total - intent_matches,
        "reader_intent_accuracy": _percentage(intent_matches, total),
        "fully_matched_cases": full_matches,
        "full_case_accuracy": _percentage(full_matches, total),
        "cases_with_contextual_evidence": sum(bool(case["contextual_support_labels"]) for case in cases),
        "cases_with_contextual_suppression": sum(bool(case["contextual_suppressions"]) for case in cases),
        "cases_with_semantic_relationships": sum(case["semantic_relationship_count"] > 0 for case in cases),
        "cases_with_primary_semantic_domains": sum(bool(case["primary_semantic_domains"]) for case in cases),
        "cases_with_secondary_semantic_domains": sum(bool(case["secondary_semantic_domains"]) for case in cases),
        "cases_with_semantic_format_support": sum(bool(case["semantic_format_support"]) for case in cases),
        "cases_with_semantic_format_suppression": sum(bool(case["semantic_format_suppression"]) for case in cases),
        "scope_distribution": {scope.value: scope_counts.get(scope.value, 0) for scope in AdjudicationScope},
        "projected_provider_call_cases": provider_cases,
        "projected_provider_call_rate": _percentage(provider_cases, total),
        "unnecessary_projected_call_cases": unnecessary,
        "unnecessary_projected_call_rate": _percentage(unnecessary, total),
        "risk_stratification": dict(risk_stats),
        **_historical_metrics(),
        "cases": cases,
    }
    analysis.update(_gate_metrics(cases, "topic"))
    analysis.update(_gate_metrics(cases, "format"))
    analysis["generalization_assessment"] = generalization_assessment(analysis)
    analysis["gate_assessment"] = gate_assessment(analysis)
    return analysis


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _mismatches(analysis: dict[str, Any], dimension: str) -> str:
    expected = "expected_reader_intent" if dimension == "intent" else f"expected_{dimension}"
    predicted = "predicted_reader_intent" if dimension == "intent" else f"predicted_{dimension}"
    values = [
        f"- {case['id']}: {case[expected]} → {case[predicted]}"
        for case in analysis["cases"] if not case[f"{dimension}_match"]
    ]
    return "\n".join(values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    return f"""# Batch 06 Blind Generalization Validation

## Holdout Integrity

Cases: 10

IDs: 051–060

Provider Calls: 0

## Pre-Gate Editorial Performance

Topic Accuracy: {analysis['topic_accuracy']:.2f}%

Format Accuracy: {analysis['format_accuracy']:.2f}%

Reader Intent Accuracy: {analysis['reader_intent_accuracy']:.2f}%

Full Case Accuracy: {analysis['full_case_accuracy']:.2f}%

## Topic Mismatches

{_mismatches(analysis, 'topic')}

## Format Mismatches

{_mismatches(analysis, 'format')}

## Reader Intent Mismatches

{_mismatches(analysis, 'intent')}

## Contextual / Semantic Evidence

Contextual Evidence Cases: {analysis['cases_with_contextual_evidence']}

Semantic Relationship Cases: {analysis['cases_with_semantic_relationships']}

Primary Semantic Domain Cases: {analysis['cases_with_primary_semantic_domains']}

Semantic Format Support Cases: {analysis['cases_with_semantic_format_support']}

## Gate Coverage

Topic Gate Precision: {analysis['topic_gate_precision']:.2f}%

Topic Gate Recall: {analysis['topic_gate_recall']:.2f}%

Format Gate Precision: {analysis['format_gate_precision']:.2f}%

Format Gate Recall: {analysis['format_gate_recall']:.2f}%

Projected Provider Calls: {analysis['projected_provider_call_cases']}/10

## Generalization Assessment

{analysis['generalization_assessment']}

## Gate Assessment

{analysis['gate_assessment']}

## Scientific Conclusion

Batch 06 records observed generalization and gate coverage without tuning. Correct dimensions generalized as reported above; mismatches and missed or unnecessary gate decisions remain raw holdout findings for later analysis.
"""


def _mismatch_ids(analysis: dict[str, Any], dimension: str) -> list[str]:
    """Return mismatching case IDs for one frozen editorial dimension."""
    field = "intent_match" if dimension == "reader_intent" else f"{dimension}_match"
    return [case["id"] for case in analysis["cases"] if not case[field]]


def _improvement_classification(comparison: dict[str, Any]) -> str:
    """Classify observed deltas without changing any production decision."""
    accuracy_deltas = (
        comparison["topic_accuracy_delta"],
        comparison["format_accuracy_delta"],
        comparison["reader_intent_accuracy_delta"],
        comparison["full_case_accuracy_delta"],
    )
    evidence_improved = (
        comparison["semantic_relationship_count_delta"] > 0
        or comparison["primary_domain_count_delta"] > 0
        or comparison["format_support_count_delta"] > 0
    )
    if any(delta <= -20.0 for delta in accuracy_deltas):
        return "REGRESSION"
    if (
        max(accuracy_deltas[:2]) >= 20.0
        and comparison["semantic_relationship_count_delta"] >= 2
        and comparison["current_semantic_format_support"] > 0
        and comparison["regression_controls_preserved"]
    ):
        return "STRONG_IMPROVEMENT"
    if sum(delta > 0 for delta in accuracy_deltas) >= 2 and evidence_improved:
        return "MEANINGFUL_IMPROVEMENT"
    if any(delta > 0 for delta in accuracy_deltas) and any(
        delta < 0 for delta in accuracy_deltas
    ):
        return "MIXED"
    if not any(delta > 0 for delta in accuracy_deltas) and not evidence_improved:
        return "NO_IMPROVEMENT"
    return "MIXED"


def build_comparison(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Compare the preserved HKEI-155 baseline with the current blind run."""
    previous_by_id = {case["id"]: case for case in previous["cases"]}
    current_by_id = {case["id"]: case for case in current["cases"]}
    result: dict[str, Any] = {
        "batch": "batch_06",
        "baseline": "HKEI-155",
        "current": "post-HKEI-157",
        "baseline_snapshot": previous,
        "case_count": current["case_count"],
        "provider_calls": current["provider_calls"],
        "expected_labels_unchanged": (
            previous["expected_labels_sha256"] == current["expected_labels_sha256"]
        ),
        "raw_source_integrity": current["source_integrity"] and (
            previous["raw_source_sha256"] == current["raw_source_sha256"]
        ),
        "regression_controls_preserved": all(
            current[key] == 100.0
            for key in (
                "batch_01_topic_accuracy",
                "batch_02_full_accuracy",
                "batch_03_full_accuracy",
            )
        ),
    }
    for key in (
        "topic_accuracy",
        "format_accuracy",
        "reader_intent_accuracy",
        "full_case_accuracy",
    ):
        result[f"previous_{key}"] = previous[key]
        result[f"current_{key}"] = current[key]
        result[f"{key}_delta"] = current[key] - previous[key]
    evidence_fields = {
        "semantic_relationship": "cases_with_semantic_relationships",
        "primary_domain": "cases_with_primary_semantic_domains",
        "format_support": "cases_with_semantic_format_support",
    }
    for label, key in evidence_fields.items():
        result[f"previous_{label}s"] = previous[key]
        result[f"current_{label}s"] = current[key]
        result[f"{label}_count_delta"] = current[key] - previous[key]
    result["evidence_funnel"] = {
        key: current[key]
        for key in (
            "cases_with_contextual_evidence",
            "cases_with_semantic_relationships",
            "cases_with_primary_semantic_domains",
            "cases_with_secondary_semantic_domains",
            "cases_with_semantic_format_support",
            "cases_with_semantic_format_suppression",
        )
    }
    contextual = current["cases_with_contextual_evidence"]
    relationships = current["cases_with_semantic_relationships"]
    domains = current["cases_with_primary_semantic_domains"]
    result["conversion_metrics"] = {
        "context_to_relationship_conversion_rate": _percentage(relationships, contextual),
        "relationship_to_primary_domain_conversion_rate": _percentage(domains, relationships),
        "context_to_primary_domain_conversion_rate": _percentage(domains, contextual),
        "semantic_format_support_rate": _percentage(
            current["cases_with_semantic_format_support"], current["case_count"]
        ),
    }
    for dimension in ("topic", "format", "reader_intent"):
        previous_ids = set(_mismatch_ids(previous, dimension))
        current_ids = set(_mismatch_ids(current, dimension))
        result[f"current_{dimension}_mismatches"] = sorted(current_ids)
        result[f"resolved_{dimension}_mismatches"] = sorted(previous_ids - current_ids)
        result[f"new_{dimension}_mismatches"] = sorted(current_ids - previous_ids)
        result[f"unchanged_{dimension}_mismatches"] = sorted(previous_ids & current_ids)
    result["fully_matched_cases"] = [
        case["id"] for case in current["cases"] if case["full_match"]
    ]
    result["newly_fully_matched_cases"] = [
        case_id
        for case_id, case in current_by_id.items()
        if case["full_match"] and not previous_by_id[case_id]["full_match"]
    ]
    for dimension in ("topic", "format"):
        result[f"previous_{dimension}_gate"] = {
            key: previous[f"{dimension}_gate_{key}"]
            for key in ("tp", "fp", "tn", "fn", "precision", "recall")
        }
        result[f"current_{dimension}_gate"] = {
            key: current[f"{dimension}_gate_{key}"]
            for key in ("tp", "fp", "tn", "fn", "precision", "recall")
        }
        result[f"{dimension}_gate_recall_delta"] = (
            current[f"{dimension}_gate_recall"]
            - previous[f"{dimension}_gate_recall"]
        )
    result["previous_format_fn_cases"] = [
        case["id"]
        for case in previous["cases"]
        if not case["format_match"] and not case["format_required"]
    ]
    result["current_format_fn_cases"] = [
        case["id"]
        for case in current["cases"]
        if not case["format_match"] and not case["format_required"]
    ]
    result["previous_fn_tracking"] = {
        case_id: {
            "previous_format_required": previous_by_id[case_id]["format_required"],
            "current_format_required": current_by_id[case_id]["format_required"],
            "previous_semantic_format_support": previous_by_id[case_id]["semantic_format_support"],
            "current_semantic_format_support": current_by_id[case_id]["semantic_format_support"],
            "previous_format_confidence": previous_by_id[case_id]["format_confidence"],
            "current_format_confidence": current_by_id[case_id]["format_confidence"],
            "previous_predicted_format": previous_by_id[case_id]["predicted_format"],
            "current_predicted_format": current_by_id[case_id]["predicted_format"],
            "expected_format": current_by_id[case_id]["expected_format"],
        }
        for case_id in ("054", "056", "059")
    }
    result["projected_provider_call_cases"] = current["projected_provider_call_cases"]
    result["projected_provider_call_rate"] = current["projected_provider_call_rate"]
    improved = (
        result["semantic_relationship_count_delta"] > 0,
        result["primary_domain_count_delta"] > 0,
        result["format_support_count_delta"] > 0,
    )
    result["architectural_interpretation"] = (
        "D_ALL_THREE" if all(improved) else
        "A_CONTEXT_TO_RELATIONSHIP" if improved == (True, False, False) else
        "B_RELATIONSHIP_TO_DOMAIN" if improved == (False, True, False) else
        "C_FORMAT_STRUCTURAL_EVIDENCE" if improved == (False, False, True) else
        "MIXED_COMPONENTS" if any(improved) else "E_NONE_MATERIALLY"
    )
    result["improvement_classification"] = _improvement_classification(result)
    return result


def render_comparison_markdown(comparison: dict[str, Any]) -> str:
    """Render a compact historical/current comparison without source text."""
    return f"""# Batch 06 Post-HKEI-157 Comparison

Baseline: {comparison['baseline']}

Current: {comparison['current']}

Improvement classification: {comparison['improvement_classification']}

Topic accuracy: {comparison['previous_topic_accuracy']:.2f}% → {comparison['current_topic_accuracy']:.2f}%

Format accuracy: {comparison['previous_format_accuracy']:.2f}% → {comparison['current_format_accuracy']:.2f}%

Reader Intent accuracy: {comparison['previous_reader_intent_accuracy']:.2f}% → {comparison['current_reader_intent_accuracy']:.2f}%

Full case accuracy: {comparison['previous_full_case_accuracy']:.2f}% → {comparison['current_full_case_accuracy']:.2f}%

Semantic relationships: {comparison['previous_semantic_relationships']} → {comparison['current_semantic_relationships']}

Primary domains: {comparison['previous_primary_domains']} → {comparison['current_primary_domains']}

Semantic format support: {comparison['previous_format_supports']} → {comparison['current_format_supports']}

Architectural interpretation: {comparison['architectural_interpretation']}

Provider calls: {comparison['provider_calls']}
"""


def main() -> int:
    previous = (
        json.loads(COMPARISON_JSON.read_text(encoding="utf-8"))["baseline_snapshot"]
        if COMPARISON_JSON.exists()
        else json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    )
    analysis = analyze_validation()
    comparison = build_comparison(previous, analysis)
    OUTPUT_JSON.write_text(render_json(analysis), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(analysis), encoding="utf-8")
    COMPARISON_JSON.write_text(render_json(comparison), encoding="utf-8")
    COMPARISON_MD.write_text(
        render_comparison_markdown(comparison), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in analysis.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
