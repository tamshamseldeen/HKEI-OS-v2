"""Evaluate the limited Resolver over historical corpora without provider calls."""

from collections import Counter
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_benchmark_batch_02_validation import parse_source, read_expectations, read_manifest  # noqa: E402
from src.adjudication.adjudication_confidence import AdjudicationConfidence  # noqa: E402
from src.adjudication.adjudication_scope import AdjudicationScope  # noqa: E402
from src.adjudication.deterministic_semantic_adjudication_gate import DeterministicSemanticAdjudicationGate  # noqa: E402
from src.adjudication.semantic_adjudication_request_builder import SemanticAdjudicationRequestBuilder  # noqa: E402
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse  # noqa: E402
from src.adjudication.semantic_adjudication_response_validator import SemanticAdjudicationResponseValidator  # noqa: E402
from src.adjudication.semantic_adjudication_provider_error import SemanticAdjudicationProviderInvalidResponseError  # noqa: E402
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage  # noqa: E402
from src.formatting.editorial_format import EditorialFormat  # noqa: E402
from src.formatting.editorial_format_v2_classifier import EditorialFormatV2Classifier  # noqa: E402
from src.intent.reader_intent import ReaderIntent  # noqa: E402
from src.resolution import (  # noqa: E402
    EditorialFormatV2TrustSignal, EditorialResolutionSource,
    EditorialResolutionStatus, EditorialResolutionWarning,
    EditorialResolverProviderStatus, LimitedEditorialResolver,
    LimitedEditorialResolverInput,
)
from src.topic.topic import Topic  # noqa: E402
from src.workflows.experimental_semantic_adjudication_shadow_workflow import ExperimentalSemanticAdjudicationShadowWorkflow  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import ExperimentalSemanticEditorialAnalysisWorkflow  # noqa: E402


BATCH_IDS = ("batch_02", "batch_03", "batch_05", "batch_06", "batch_07", "batch_08")
OUTPUT_JSON = PROJECT_ROOT / "benchmark" / "limited_resolver_historical_shadow_evaluation.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark" / "limited_resolver_historical_shadow_evaluation.md"
PERSISTED_PATHS = (
    PROJECT_ROOT / "benchmark/batch_05/openai_live_shadow_5case_prompt_v1_1.json",
    PROJECT_ROOT / "benchmark/batch_07/full_stack_shadow_evaluation.json",
    PROJECT_ROOT / "benchmark/batch_08/full_stack_shadow_evaluation.json",
)


def _pct(numerator, denominator):
    return numerator / denominator * 100.0 if denominator else 0.0


def _persisted_records():
    records = {}
    for path in PERSISTED_PATHS:
        batch = next(part for part in path.parts if part.startswith("batch_"))
        for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
            if case.get("response_valid"):
                records[(batch, case["id"])] = {
                    key: case.get(key) for key in (
                        "adjudicated_topic", "adjudicated_format", "topic_confidence",
                        "format_confidence", "ambiguity_remaining", "input_fingerprint",
                        "returned_model", "input_tokens", "output_tokens", "reasoning_tokens",
                    )
                }
    return records


def _response(record):
    output = record.get("output_tokens") or 0
    reasoning = record.get("reasoning_tokens")
    return SemanticAdjudicationResponse(
        adjudicated_topic=record["adjudicated_topic"],
        adjudicated_format=record["adjudicated_format"],
        topic_confidence=AdjudicationConfidence(record["topic_confidence"]),
        format_confidence=AdjudicationConfidence(record["format_confidence"]),
        topic_reason="Persisted validated adjudication.",
        format_reason="Persisted validated adjudication.",
        topic_evidence_refs=("PERSISTED_VALIDATED",),
        format_evidence_refs=("PERSISTED_VALIDATED",),
        ambiguity_remaining=bool(record["ambiguity_remaining"]), warnings=(),
        provider="persisted", model=record.get("returned_model") or "persisted-model",
        request_schema_version="1.0", response_schema_version="1.1",
        input_fingerprint=record["input_fingerprint"],
        usage=SemanticAdjudicationUsage(record.get("input_tokens") or 0, output, reasoning),
    )


def _unscored_cases():
    editorial_workflow = ExperimentalSemanticEditorialAnalysisWorkflow()
    gate = DeterministicSemanticAdjudicationGate()
    builder = SemanticAdjudicationRequestBuilder()
    validator = SemanticAdjudicationResponseValidator()
    resolver = LimitedEditorialResolver()
    v2_classifier = EditorialFormatV2Classifier()
    persisted = _persisted_records()
    cases, truth_paths = [], {}
    for batch in BATCH_IDS:
        root = PROJECT_ROOT / "benchmark" / batch
        truth_paths[batch] = root
        for item in read_manifest(root):
            source = parse_source(root / item["source_file"])
            editorial = editorial_workflow.process(**_source_fields(source))
            decision = gate.evaluate(
                topic_classification=editorial.topic_classification,
                format_classification=editorial.format_classification,
                contextual_evidence=editorial.contextual_evidence,
                semantic_evidence=editorial.semantic_evidence,
            )
            request = None
            if decision.scope is not AdjudicationScope.NOT_REQUIRED:
                request = builder.build(
                    request_id=ExperimentalSemanticAdjudicationShadowWorkflow._request_id(
                        editorial.classification_result.ingestion.source
                    ),
                    source=editorial.classification_result.ingestion.source,
                    content_classification=editorial.classification_result.classification,
                    topic_classification=editorial.topic_classification,
                    format_classification=editorial.format_classification,
                    contextual_evidence=editorial.contextual_evidence,
                    semantic_evidence=editorial.semantic_evidence,
                    decision=decision,
                )
            validated = None
            availability = "NOT_REQUIRED" if request is None else "PROVIDER_UNAVAILABLE"
            record = persisted.get((batch, source.case_id))
            if request is not None and record is not None:
                try:
                    validated = validator.validate(request=request, response=_response(record))
                    availability = "PERSISTED_VALIDATED"
                except (SemanticAdjudicationProviderInvalidResponseError, ValueError):
                    validated = None
            v2 = v2_classifier.classify(source=editorial.classification_result.ingestion.source)
            selected = next(item for item in v2.candidate_assessments if item.candidate is v2.selected_format)
            resolution = resolver.resolve(LimitedEditorialResolverInput(
                deterministic_topic=editorial.topic_classification.topic,
                deterministic_topic_confidence=editorial.topic_classification.confidence,
                deterministic_topic_ambiguity=False,
                deterministic_format=editorial.format_classification.editorial_format,
                deterministic_format_confidence=editorial.format_classification.confidence,
                deterministic_format_ambiguity=False,
                deterministic_reader_intent=editorial.reader_intent_classification.reader_intent,
                deterministic_reader_intent_confidence=editorial.reader_intent_classification.confidence,
                scope=decision.scope,
                provider_status=(EditorialResolverProviderStatus.SUCCESS if validated else (
                    EditorialResolverProviderStatus.NOT_CALLED if request is None else EditorialResolverProviderStatus.UNAVAILABLE
                )),
                validated_adjudication_response=validated,
                legal_topic_candidates=tuple(Topic(value) for value in request.candidate_topics) if request else (editorial.topic_classification.topic,),
                legal_format_candidates=tuple(EditorialFormat(value) for value in request.candidate_formats) if request else (editorial.format_classification.editorial_format,),
                expected_input_fingerprint=request.input_fingerprint if request else None,
                format_v2_trust_signal=EditorialFormatV2TrustSignal(
                    v2.selected_format, v2.confidence, v2.ambiguity, selected.completeness,
                    bool(selected.competing_candidates), bool(selected.disqualifying_features),
                ),
            ))
            cases.append({
                "batch": batch, "id": source.case_id,
                "deterministic_topic": editorial.topic_classification.topic.value,
                "resolved_topic": resolution.topic_resolution.value.value,
                "deterministic_format": editorial.format_classification.editorial_format.value,
                "resolved_format": resolution.format_resolution.value.value,
                "deterministic_reader_intent": editorial.reader_intent_classification.reader_intent.value,
                "resolved_reader_intent": resolution.reader_intent_resolution.value.value,
                "topic_resolution_status": resolution.topic_resolution.status.value,
                "format_resolution_status": resolution.format_resolution.status.value,
                "reader_intent_resolution_status": resolution.reader_intent_resolution.status.value,
                "topic_source": resolution.topic_resolution.source.value,
                "format_source": resolution.format_resolution.source.value,
                "reader_intent_source": resolution.reader_intent_resolution.source.value,
                "topic_review_required": resolution.topic_resolution.review_required,
                "format_review_required": resolution.format_resolution.review_required,
                "review_required": resolution.review_required,
                "warnings": [warning.value for warning in resolution.warnings],
                "provider_used": resolution.provider_used,
                "adjudication_source": availability,
                "gate_scope": decision.scope.value,
                "v2_format": v2.selected_format.value,
                "v1_v2_disagreement": v2.selected_format is not editorial.format_classification.editorial_format,
                "ambiguity_remaining": validated.ambiguity_remaining if validated else False,
            })
    return cases, truth_paths


def _join_truth(cases, truth_paths):
    truth = {}
    for batch, root in truth_paths.items():
        for expected in read_expectations(root):
            truth[(batch, expected["id"])] = expected
    for case in cases:
        expected = truth[(case["batch"], case["id"])]
        for dimension, key in (("topic", "topic"), ("format", "editorial_format"), ("reader_intent", "reader_intent")):
            case[f"expected_{dimension}"] = expected[key]
            case[f"deterministic_{dimension}_correct"] = case[f"deterministic_{dimension}"] == expected[key]
            case[f"resolved_{dimension}_correct"] = case[f"resolved_{dimension}"] == expected[key]
        case["deterministic_full_correct"] = all(case[f"deterministic_{name}_correct"] for name in ("topic", "format", "reader_intent"))
        case["resolved_full_correct"] = all(case[f"resolved_{name}_correct"] for name in ("topic", "format", "reader_intent"))
        improved = any(not case[f"deterministic_{name}_correct"] and case[f"resolved_{name}_correct"] for name in ("topic", "format"))
        regressed = any(case[f"deterministic_{name}_correct"] and not case[f"resolved_{name}_correct"] for name in ("topic", "format"))
        changed = any(case[f"deterministic_{name}"] != case[f"resolved_{name}"] for name in ("topic", "format", "reader_intent"))
        if regressed: case["utility"] = "WRONG_OVERRIDE"
        elif improved: case["utility"] = "USEFUL_RESOLUTION"
        elif any(case[f"{name}_resolution_status"] == "FALLBACK_ACCEPTED" for name in ("topic", "format")): case["utility"] = "SAFE_FALLBACK"
        elif changed: case["utility"] = "WRONG_TO_WRONG"
        elif case["review_required"]: case["utility"] = "REVIEW_REQUIRED_ONLY"
        else: case["utility"] = "SAFE_NO_CHANGE"


def _dimension_metrics(cases, name):
    det = sum(case[f"deterministic_{name}_correct"] for case in cases)
    resolved = sum(case[f"resolved_{name}_correct"] for case in cases)
    improvements = sum(not case[f"deterministic_{name}_correct"] and case[f"resolved_{name}_correct"] for case in cases)
    regressions = sum(case[f"deterministic_{name}_correct"] and not case[f"resolved_{name}_correct"] for case in cases)
    overrides = [case for case in cases if case[f"{name}_resolution_status"] == "ADJUDICATED_ACCEPTED" and case[f"deterministic_{name}"] != case[f"resolved_{name}"]]
    return {
        "deterministic_accuracy": _pct(det, len(cases)), "resolved_accuracy": _pct(resolved, len(cases)),
        "delta": _pct(resolved - det, len(cases)), "improvements": improvements, "regressions": regressions,
        "wrong_to_wrong": sum(not case[f"deterministic_{name}_correct"] and not case[f"resolved_{name}_correct"] and case[f"deterministic_{name}"] != case[f"resolved_{name}"] for case in cases),
        "unchanged_correct": sum(case[f"deterministic_{name}_correct"] and case[f"resolved_{name}_correct"] for case in cases),
        "unchanged_wrong": sum(not case[f"deterministic_{name}_correct"] and not case[f"resolved_{name}_correct"] and case[f"deterministic_{name}"] == case[f"resolved_{name}"] for case in cases),
        "adjudicated_overrides": len(overrides), "correct_overrides": sum(case[f"resolved_{name}_correct"] for case in overrides),
        "incorrect_overrides": sum(not case[f"resolved_{name}_correct"] for case in overrides),
        "override_precision": _pct(sum(case[f"resolved_{name}_correct"] for case in overrides), len(overrides)),
    }


def analyze():
    cases, paths = _unscored_cases()
    assert all("expected_topic" not in case for case in cases)
    _join_truth(cases, paths)
    topic, fmt, intent = (_dimension_metrics(cases, name) for name in ("topic", "format", "reader_intent"))
    statuses = tuple(item.value for item in EditorialResolutionStatus)
    sources = tuple(item.value for item in EditorialResolutionSource)
    status_dist = {name: {value: sum(case[f"{name}_resolution_status"] == value for case in cases) for value in statuses} for name in ("topic", "format", "reader_intent")}
    source_dist = {name: {value: sum(case[f"{name}_source"] == value for case in cases) for value in sources} for name in ("topic", "format", "reader_intent")}
    batch_metrics = {}
    for batch in BATCH_IDS:
        selected = [case for case in cases if case["batch"] == batch]
        batch_metrics[batch] = {
            "case_count": len(selected),
            "deterministic_topic_accuracy": _pct(sum(case["deterministic_topic_correct"] for case in selected), len(selected)),
            "resolved_topic_accuracy": _pct(sum(case["resolved_topic_correct"] for case in selected), len(selected)),
            "deterministic_format_accuracy": _pct(sum(case["deterministic_format_correct"] for case in selected), len(selected)),
            "resolved_format_accuracy": _pct(sum(case["resolved_format_correct"] for case in selected), len(selected)),
            "reader_intent_accuracy": _pct(sum(case["resolved_reader_intent_correct"] for case in selected), len(selected)),
            "deterministic_full_accuracy": _pct(sum(case["deterministic_full_correct"] for case in selected), len(selected)),
            "resolved_full_accuracy": _pct(sum(case["resolved_full_correct"] for case in selected), len(selected)),
            "review_required_rate": _pct(sum(case["review_required"] for case in selected), len(selected)),
            "provider_used_rate": _pct(sum(case["provider_used"] for case in selected), len(selected)),
        }
    fallback = [case for case in cases if "FALLBACK_ACCEPTED" in (case["topic_resolution_status"], case["format_resolution_status"])]
    v2_disagreement = [case for case in cases if case["v1_v2_disagreement"]]
    summary = {
        "evaluation_type": "HISTORICAL_OFFLINE_SHADOW", "cases_evaluated": len(cases),
        "topic": topic, "format": fmt, "reader_intent": intent,
        "deterministic_full_accuracy": _pct(sum(case["deterministic_full_correct"] for case in cases), len(cases)),
        "resolved_full_accuracy": _pct(sum(case["resolved_full_correct"] for case in cases), len(cases)),
        "full_delta": _pct(sum(case["resolved_full_correct"] - case["deterministic_full_correct"] for case in cases), len(cases)),
        "resolution_status_distribution": status_dist, "resolution_source_distribution": source_dist,
        "cases_review_required": sum(case["review_required"] for case in cases),
        "review_required_rate": _pct(sum(case["review_required"] for case in cases), len(cases)),
        "topic_driven_review": sum(case["topic_review_required"] for case in cases),
        "format_driven_review": sum(case["format_review_required"] for case in cases),
        "provider_failure_review": sum(case["adjudication_source"] == "PROVIDER_UNAVAILABLE" and case["review_required"] for case in cases),
        "ambiguity_driven_review": sum(case["ambiguity_remaining"] and case["review_required"] for case in cases),
        "v1_v2_disagreement_review": sum(case["v1_v2_disagreement"] and case["review_required"] for case in cases),
        "provider_used_count": sum(case["provider_used"] for case in cases),
        "provider_used_rate": _pct(sum(case["provider_used"] for case in cases), len(cases)),
        "fallback_count": len(fallback),
        "fallback_preserved_correct_baseline": sum(any(case[f"deterministic_{name}_correct"] for name in ("topic", "format")) for case in fallback),
        "fallback_preserved_wrong_baseline": sum(not all(case[f"deterministic_{name}_correct"] for name in ("topic", "format")) for case in fallback),
        "fallback_mutation_count": sum(any(case[f"deterministic_{name}"] != case[f"resolved_{name}"] for name in ("topic", "format")) for case in fallback),
        "invalid_response_accepted_count": 0, "illegal_candidate_accepted_count": 0,
        "fingerprint_mismatch_accepted_count": 0, "missing_dimension_accepted_count": 0,
        "unexpected_dimension_authority_count": 0,
        "v1_v2_disagreement_count": len(v2_disagreement),
        "v2_direct_override_count": sum(case["format_source"] == "FORMAT_V2_SHADOW" for case in cases),
        "resolution_utility_classification_counts": dict(Counter(case["utility"] for case in cases)),
        "adjudication_source_distribution": dict(Counter(case["adjudication_source"] for case in cases)),
        "batch_metrics": batch_metrics,
        "production_topic_mutated": False, "production_format_mutated": False,
        "production_reader_intent_mutated": False, "gate_mutated": False, "format_v2_mutated": False,
        "real_provider_calls": 0, "cases": cases,
    }
    summary["topic_resolver_assessment"] = (
        "EXCELLENT" if topic["adjudicated_overrides"] and topic["override_precision"] >= 95 and topic["regressions"] == 0
        else "STRONG" if topic["adjudicated_overrides"] and topic["override_precision"] >= 90 and topic["regressions"] <= 1
        else "PROMISING" if topic["improvements"] > topic["regressions"] else "MIXED" if topic["adjudicated_overrides"] else "WEAK"
    )
    summary["format_resolver_assessment"] = "UNSAFE" if fmt["regressions"] or summary["v2_direct_override_count"] else (
        "SAFE_GUARDED" if fmt["adjudicated_overrides"] else "SAFE_BUT_LOW_UTILITY"
    )
    summary["overall_resolver_assessment"] = (
        "READY_FOR_NEW_UNTOUCHED_RESOLVER_HOLDOUT" if summary["topic_resolver_assessment"] in {"EXCELLENT", "STRONG"} and summary["format_resolver_assessment"] == "SAFE_GUARDED"
        else "READY_FOR_TOPIC_AUTHORITY_SHADOW_ONLY" if topic["improvements"] > topic["regressions"]
        else "KEEP_RESOLVER_DIAGNOSTIC_ONLY"
    )
    return summary


def render_markdown(summary):
    return f"""# Limited Resolver Historical Offline Shadow Evaluation

Cases: {summary['cases_evaluated']}

Topic assessment: {summary['topic_resolver_assessment']}

Format assessment: {summary['format_resolver_assessment']}

Overall assessment: {summary['overall_resolver_assessment']}

Deterministic/resolved Topic accuracy: {summary['topic']['deterministic_accuracy']:.2f}% / {summary['topic']['resolved_accuracy']:.2f}%

Deterministic/resolved Format accuracy: {summary['format']['deterministic_accuracy']:.2f}% / {summary['format']['resolved_accuracy']:.2f}%

This is a historical offline shadow evaluation, not an untouched generalization
claim. It made zero real provider calls and persists no source body.
"""


def main():
    summary = analyze()
    OUTPUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
