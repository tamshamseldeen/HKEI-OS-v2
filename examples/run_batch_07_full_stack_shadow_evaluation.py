"""Run the preregistered Batch 07 full-stack evaluation in shadow mode."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean, median
import subprocess
import sys
import time
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_benchmark_batch_02_validation import parse_source, read_expectations, read_manifest  # noqa: E402
from examples.run_openai_semantic_adjudication_live_canary import (  # noqa: E402
    _SanitizedErrorCapturingProvider, _configuration, _create_openai_client,
)
from examples.run_semantic_candidate_assessment_shadow import _assessment_record, _candidate_groups  # noqa: E402
from src.adjudication.openai_semantic_adjudication_provider import OpenAISemanticAdjudicationProvider  # noqa: E402
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider  # noqa: E402
from src.adjudication.semantic_adjudication_provider_config_validator import SemanticAdjudicationProviderConfigValidator  # noqa: E402
from src.adjudication.semantic_adjudication_runtime_context import SemanticAdjudicationRuntimeContext  # noqa: E402
from src.adjudication.semantic_adjudication_runtime_context_builder import SemanticAdjudicationRuntimeContextBuilder  # noqa: E402
from src.adjudication.semantic_adjudication_secret_resolver import SemanticAdjudicationSecretResolver  # noqa: E402
from src.adjudication.environment_semantic_adjudication_secret_resolver import EnvironmentSemanticAdjudicationSecretResolver  # noqa: E402
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor  # noqa: E402
from src.workflows.experimental_semantic_adjudication_shadow_workflow import ExperimentalSemanticAdjudicationShadowWorkflow  # noqa: E402
from src.workflows.experimental_semantic_editorial_analysis_workflow import ExperimentalSemanticEditorialAnalysisWorkflow  # noqa: E402


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_07"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_07_raw.txt"
OUTPUT_JSON = BATCH_ROOT / "full_stack_shadow_evaluation.json"
OUTPUT_MD = BATCH_ROOT / "full_stack_shadow_evaluation.md"
CASE_IDS = tuple(f"{value:03d}" for value in range(61, 71))
RAW_SHA256 = "7a8ab6b9155276eeabbb4459590fa9c10528cfd3c9a5fc517f8d0abed5d39be3"
EXPECTED_SHA256 = "cafddc7533a80dc834abe96606ae770a458d462893086be16fcea95554c6c036"
RISK_SHA256 = "adc5ddf9a7e1e723c35b869a281f1c96b7de59f6d5e2cea6f7bef8a83515f335"
MAX_CALLS = 10


class _LimitedProvider(SemanticAdjudicationProvider):
    def __init__(self, provider: SemanticAdjudicationProvider) -> None:
        self._provider = provider
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def adjudicate(self, request: Any) -> Any:
        if self.call_count >= MAX_CALLS:
            raise RuntimeError("Batch 07 evaluation permits at most ten calls")
        self.call_count += 1
        return self._provider.adjudicate(request)


class _AssessingEditorialWorkflow:
    """Capture deterministic assessments without changing editorial results."""

    def __init__(self, assessor: Any | None = None) -> None:
        self._workflow = ExperimentalSemanticEditorialAnalysisWorkflow()
        self._assessor = assessor or DeterministicSemanticCandidateAssessor()
        self.last_assessments: list[dict[str, Any]] = []

    def process(self, **kwargs: Any) -> Any:
        result = self._workflow.process(**kwargs)
        groups = _candidate_groups(result.semantic_evidence, result.contextual_evidence)
        self.last_assessments = [
            _assessment_record(item, groups.get(item.candidate, "CANDIDATE_TYPE_NOT_EXPLICIT"))
            for item in self._assessor.assess(
                semantic_evidence=result.semantic_evidence,
                contextual_evidence=result.contextual_evidence,
            )
        ]
        return result


def _percentage(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _verify_registration() -> None:
    manifest = json.loads((BATCH_ROOT / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() != RAW_SHA256:
        raise RuntimeError("Batch 07 raw source integrity failure")
    if hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Batch 07 expected labels are not frozen")
    if hashlib.sha256((BATCH_ROOT / "human_risk_annotations.json").read_bytes()).hexdigest() != RISK_SHA256:
        raise RuntimeError("Batch 07 risk annotations are not frozen")
    if manifest["scientific_status"] != "UNTOUCHED_PREREGISTERED_HOLDOUT":
        raise RuntimeError("Batch 07 is not an untouched preregistered holdout")
    if tuple(manifest["case_ids"]) != CASE_IDS or manifest["validation_status"] != "NOT_RUN":
        raise RuntimeError("Batch 07 registration contract mismatch")


def _unscored_case(case_id: str, result: Any, assessments: list[dict[str, Any]], latency_ms: int, sanitized_error: str | None) -> dict[str, Any]:
    editorial = result.editorial_result
    decision = result.adjudication_decision
    request = result.request
    response = result.validated_response
    usage = response.usage if response else None
    deterministic_topic = editorial.topic_classification.topic.value
    deterministic_format = editorial.format_classification.editorial_format.value
    deterministic_intent = editorial.reader_intent_classification.reader_intent.value
    reasoning = usage.reasoning_tokens if usage else None
    return {
        "id": case_id,
        "deterministic_topic": deterministic_topic,
        "deterministic_format": deterministic_format,
        "deterministic_reader_intent": deterministic_intent,
        "deterministic_topic_confidence": editorial.topic_classification.confidence.value,
        "deterministic_format_confidence": editorial.format_classification.confidence.value,
        "candidate_assessment_summary": assessments,
        "gate_scope": decision.scope.value,
        "topic_required": decision.topic_required,
        "format_required": decision.format_required,
        "trigger_signals": list(decision.trigger_signals),
        "provider_called": result.provider_called,
        "provider_error": sanitized_error or result.provider_error,
        "provider_error_category": result.provider_error,
        "response_valid": result.response_valid,
        "adjudicated_topic": response.adjudicated_topic if response else None,
        "adjudicated_format": response.adjudicated_format if response else None,
        "topic_confidence": response.topic_confidence.value if response else None,
        "format_confidence": response.format_confidence.value if response else None,
        "ambiguity_remaining": response.ambiguity_remaining if response else None,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "reasoning_tokens": reasoning,
        "non_reasoning_output_tokens": usage.output_tokens - reasoning if usage and reasoning is not None else None,
        "latency_ms": latency_ms,
        "returned_model": response.model if response else None,
        "input_fingerprint": request.input_fingerprint if request else None,
        "candidate_compliant": (
            response.adjudicated_topic in request.candidate_topics
            and response.adjudicated_format in request.candidate_formats
            if response and request else None
        ),
        "fingerprint_valid": response.input_fingerprint == request.input_fingerprint if response and request else None,
        "shadow_topic_mutated": bool(request and deterministic_topic != request.deterministic_topic),
        "shadow_format_mutated": bool(request and deterministic_format != request.deterministic_format),
        "shadow_intent_mutated": False,
        "actual_confidence_mutated": bool(
            request and (
                request.topic_confidence != editorial.topic_classification.confidence.value
                or request.format_confidence != editorial.format_classification.confidence.value
            )
        ),
        "gate_mutated": False,
    }


def _assessment_state(case: dict[str, Any], dimension: str) -> str:
    group = "TOPIC_LIKE" if dimension == "topic" else "FORMAT_LIKE"
    expected = case[f"expected_{dimension}"]
    states = [
        item["sufficiency"] for item in case["candidate_assessment_summary"]
        if item["candidate_group"] == group and item["candidate"] == expected
    ]
    return states[0] if states else "MISSING"


def _effective_label(case: dict[str, Any], dimension: str) -> str:
    if case[f"{dimension}_required"] and case["response_valid"]:
        return case[f"adjudicated_{dimension}"]
    return case[f"deterministic_{dimension}"]


def _score_cases(cases: list[dict[str, Any]]) -> None:
    """Join frozen labels and risk metadata only after every provider call."""
    expected = {item["id"]: item for item in read_expectations(BATCH_ROOT)}
    risks = json.loads((BATCH_ROOT / "human_risk_annotations.json").read_text(encoding="utf-8"))["annotations"]
    if tuple(expected) != CASE_IDS or tuple(item["id"] for item in risks) != CASE_IDS:
        raise RuntimeError("Batch 07 evaluation metadata mismatch")
    for case in cases:
        truth = expected[case["id"]]
        case["expected_topic"] = truth["topic"]
        case["expected_format"] = truth["editorial_format"]
        case["expected_reader_intent"] = truth["reader_intent"]
        case["topic_match_before"] = case["deterministic_topic"] == case["expected_topic"]
        case["format_match_before"] = case["deterministic_format"] == case["expected_format"]
        case["intent_match"] = case["deterministic_reader_intent"] == case["expected_reader_intent"]
        case["effective_shadow_topic"] = _effective_label(case, "topic")
        case["effective_shadow_format"] = _effective_label(case, "format")
        case["effective_shadow_reader_intent"] = case["deterministic_reader_intent"]
        case["topic_match_after"] = case["effective_shadow_topic"] == case["expected_topic"]
        case["format_match_after"] = case["effective_shadow_format"] == case["expected_format"]
        case["full_match_before"] = case["topic_match_before"] and case["format_match_before"] and case["intent_match"]
        case["full_match_after"] = case["topic_match_after"] and case["format_match_after"] and case["intent_match"]
        case["topic_improvement"] = not case["topic_match_before"] and case["topic_match_after"]
        case["topic_regression"] = case["topic_match_before"] and not case["topic_match_after"]
        case["format_improvement"] = not case["format_match_before"] and case["format_match_after"]
        case["format_regression"] = case["format_match_before"] and not case["format_match_after"]


def _confusion(cases: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    pairs = [(case[f"{dimension}_required"], not case[f"{dimension}_match_before"]) for case in cases]
    tp = sum(predicted and actual for predicted, actual in pairs)
    fp = sum(predicted and not actual for predicted, actual in pairs)
    tn = sum(not predicted and not actual for predicted, actual in pairs)
    fn = sum(not predicted and actual for predicted, actual in pairs)
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": _percentage(tp, tp + fp), "recall": _percentage(tp, tp + fn)}


def _dimension_metrics(cases: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    before = sum(case[f"{dimension}_match_before"] for case in cases)
    after = sum(case[f"{dimension}_match_after"] for case in cases)
    changed = [case for case in cases if case[f"effective_shadow_{dimension}"] != case[f"deterministic_{dimension}"]]
    correct_changes = sum(case[f"{dimension}_match_after"] for case in changed)
    return {
        "deterministic_correct": before,
        "deterministic_accuracy": _percentage(before, len(cases)),
        "effective_correct": after,
        "effective_accuracy": _percentage(after, len(cases)),
        "delta": after - before,
        "improvements": sum(case[f"{dimension}_improvement"] for case in cases),
        "regressions": sum(case[f"{dimension}_regression"] for case in cases),
        "wrong_to_wrong_changes": sum(
            not case[f"{dimension}_match_before"] and not case[f"{dimension}_match_after"]
            and case[f"effective_shadow_{dimension}"] != case[f"deterministic_{dimension}"]
            for case in cases
        ),
        "unchanged_correct": sum(case[f"{dimension}_match_before"] and case not in changed for case in cases),
        "unchanged_wrong": sum(not case[f"{dimension}_match_before"] and case not in changed for case in cases),
        "changed_decisions": len(changed),
        "correct_changes": correct_changes,
        "incorrect_changes": len(changed) - correct_changes,
        "change_precision": _percentage(correct_changes, len(changed)),
    }


def _summarize(cases: list[dict[str, Any]], provider_calls: int, *, evaluated_at: str, evaluation_commit: str) -> dict[str, Any]:
    topic = _dimension_metrics(cases, "topic")
    format_ = _dimension_metrics(cases, "format")
    called = [case for case in cases if case["provider_called"]]
    valid = [case for case in called if case["response_valid"]]
    invalid = [case for case in called if not case["response_valid"] and case["provider_error_category"] and "InvalidResponse" in case["provider_error_category"]]
    errors = [case for case in called if not case["response_valid"] and case not in invalid]
    sufficient = [
        (case, item) for case in cases for item in case["candidate_assessment_summary"]
        if item["sufficiency"] == "SUFFICIENT"
    ]
    labeled_sufficient = [
        (case, item) for case, item in sufficient
        if item["candidate_group"] in {"TOPIC_LIKE", "FORMAT_LIKE"}
    ]
    true_sufficient = sum(
        item["candidate"] == (case["expected_topic"] if item["candidate_group"] == "TOPIC_LIKE" else case["expected_format"] if item["candidate_group"] == "FORMAT_LIKE" else None)
        for case, item in labeled_sufficient
    )
    states = ("SUFFICIENT", "PARTIAL", "INSUFFICIENT", "CONFLICTED", "MISSING")
    correlation = {state: Counter() for state in states}
    confidence = Counter()
    for case in called:
        for dimension in ("topic", "format"):
            if not case[f"{dimension}_required"]:
                continue
            state = _assessment_state(case, dimension)
            correlation[state]["dimensions"] += 1
            correlation[state]["deterministic_correct" if case[f"{dimension}_match_before"] else "deterministic_wrong"] += 1
            if case["response_valid"]:
                correlation[state]["provider_correct" if case[f"{dimension}_match_after"] else "provider_wrong"] += 1
                correlation[state]["ambiguity_true" if case["ambiguity_remaining"] else "ambiguity_false"] += 1
                confidence[f"{'correct' if case[f'{dimension}_match_after'] else 'wrong'}_{case[f'{dimension}_confidence']}"] += 1
    ambiguity_true = [case for case in valid if case["ambiguity_remaining"] is True]
    ambiguity_false = [case for case in valid if case["ambiguity_remaining"] is False]
    provider_case_correct = lambda case: (
        (not case["topic_required"] or case["topic_match_after"])
        and (not case["format_required"] or case["format_match_after"])
    )
    reasoning = [case["reasoning_tokens"] for case in valid if case["reasoning_tokens"] is not None]
    non_reasoning = [case["non_reasoning_output_tokens"] for case in valid if case["non_reasoning_output_tokens"] is not None]
    latencies = [case["latency_ms"] for case in called]
    full_before = sum(case["full_match_before"] for case in cases)
    full_after = sum(case["full_match_after"] for case in cases)
    summary = {
        "cases_evaluated": len(cases),
        "case_ids": list(CASE_IDS),
        "provider_call_cases": [case["id"] for case in called],
        "provider_calls": provider_calls,
        "provider_call_rate": _percentage(provider_calls, len(cases)),
        "valid_responses": len(valid),
        "invalid_responses": len(invalid),
        "provider_errors": len(errors),
        "retry_attempts": 0,
        "candidate_compliance": _percentage(sum(case["candidate_compliant"] is True for case in valid), len(valid)),
        "fingerprint_integrity": _percentage(sum(case["fingerprint_valid"] is True for case in valid), len(valid)),
        "topic": topic,
        "format": format_,
        "reader_intent_accuracy": _percentage(sum(case["intent_match"] for case in cases), len(cases)),
        "deterministic_full_case_accuracy": _percentage(full_before, len(cases)),
        "effective_full_case_accuracy": _percentage(full_after, len(cases)),
        "full_case_delta": full_after - full_before,
        "fully_correct_cases": full_after,
        "topic_gate": _confusion(cases, "topic"),
        "format_gate": _confusion(cases, "format"),
        "cases_with_any_sufficient_assessment": len({case["id"] for case, _ in sufficient}),
        "cases_with_topic_sufficient": len({case["id"] for case, item in sufficient if item["candidate_group"] == "TOPIC_LIKE"}),
        "cases_with_format_sufficient": len({case["id"] for case, item in sufficient if item["candidate_group"] == "FORMAT_LIKE"}),
        "true_sufficient_count": true_sufficient,
        "false_sufficient_count": len(labeled_sufficient) - true_sufficient,
        "sufficiency_correlation": {state: dict(values) for state, values in correlation.items()},
        "confidence_calibration": {f"{correctness}_{level}": confidence[f"{correctness}_{level}"] for correctness in ("correct", "wrong") for level in ("HIGH", "MEDIUM", "LOW")},
        "ambiguity_true_count": len(ambiguity_true),
        "ambiguity_false_count": len(ambiguity_false),
        "ambiguity_rate": _percentage(len(ambiguity_true), len(valid)),
        "correct_when_ambiguity_true": sum(provider_case_correct(case) for case in ambiguity_true),
        "wrong_when_ambiguity_true": sum(not provider_case_correct(case) for case in ambiguity_true),
        "correct_when_ambiguity_false": sum(provider_case_correct(case) for case in ambiguity_false),
        "wrong_when_ambiguity_false": sum(not provider_case_correct(case) for case in ambiguity_false),
        "average_input_tokens": mean(case["input_tokens"] for case in valid) if valid else 0,
        "average_output_tokens": mean(case["output_tokens"] for case in valid) if valid else 0,
        "average_reasoning_tokens": mean(reasoning) if reasoning else None,
        "average_non_reasoning_output_tokens": mean(non_reasoning) if non_reasoning else None,
        "average_reasoning_share": mean(case["reasoning_tokens"] / case["output_tokens"] for case in valid if case["reasoning_tokens"] is not None and case["output_tokens"]) if reasoning else None,
        "average_latency_ms": mean(latencies) if latencies else 0,
        "median_latency_ms": median(latencies) if latencies else 0,
        "maximum_latency_ms": max(latencies) if latencies else 0,
        "shadow_topic_mutated": any(case["shadow_topic_mutated"] for case in cases),
        "shadow_format_mutated": any(case["shadow_format_mutated"] for case in cases),
        "shadow_intent_mutated": any(case["shadow_intent_mutated"] for case in cases),
        "actual_confidence_mutated": any(case["actual_confidence_mutated"] for case in cases),
        "gate_mutated": any(case["gate_mutated"] for case in cases),
        "resolver_used": False,
        "scientific_status_before": "UNTOUCHED_PREREGISTERED_HOLDOUT",
        "scientific_status_after": "EVALUATED_PREREGISTERED_HOLDOUT",
        "evaluation_timestamp_utc": evaluated_at,
        "evaluation_commit": evaluation_commit,
        "cases": cases,
    }
    summary["evaluation_status"] = evaluation_status(summary)
    summary["product_readiness_decision"] = product_readiness(summary)
    return summary


def _reliability(summary: dict[str, Any]) -> bool:
    return (
        summary["valid_responses"] == summary["provider_calls"]
        and summary["candidate_compliance"] == 100.0
        and summary["fingerprint_integrity"] == 100.0
        and not any(summary[key] for key in ("shadow_topic_mutated", "shadow_format_mutated", "shadow_intent_mutated", "actual_confidence_mutated", "gate_mutated"))
    )


def evaluation_status(summary: dict[str, Any]) -> str:
    if not _reliability(summary):
        return "FAILED"
    total_regressions = summary["topic"]["regressions"] + summary["format"]["regressions"]
    if (
        summary["topic"]["effective_accuracy"] >= 90
        and summary["format"]["effective_accuracy"] >= 80
        and total_regressions == 0
        and summary["effective_full_case_accuracy"] >= 70
    ):
        return "EXCELLENT"
    if (
        summary["topic"]["effective_accuracy"] >= 80
        and summary["format"]["effective_accuracy"] >= 70
        and total_regressions <= 1
        and summary["effective_full_case_accuracy"] >= 60
    ):
        return "STRONG"
    if summary["topic"]["effective_accuracy"] < 60 or summary["format"]["effective_accuracy"] < 60:
        return "WEAK"
    return "MIXED"


def product_readiness(summary: dict[str, Any]) -> str:
    status = summary["evaluation_status"]
    if status in {"EXCELLENT", "STRONG"}:
        return "READY_TO_DESIGN_RESOLVER"
    if status == "FAILED":
        return "NOT_READY_FOR_RESOLVER"
    if summary["provider_errors"] or summary["invalid_responses"]:
        return "REFINE_PROVIDER_PROMPT_BEFORE_RESOLVER"
    if summary["topic_gate"]["recall"] < 80 or summary["format_gate"]["recall"] < 80:
        return "REFINE_GATE_BEFORE_RESOLVER"
    return "ANALYZE_FULL_STACK_FAILURES_BEFORE_RESOLVER"


def render_markdown(summary: dict[str, Any]) -> str:
    return f"""# Batch 07 Full-Stack Shadow Evaluation

Evaluation status: {summary['evaluation_status']}

Product readiness: {summary['product_readiness_decision']}

Cases evaluated: {summary['cases_evaluated']}

Provider calls: {summary['provider_calls']}

Valid responses: {summary['valid_responses']}

Deterministic Topic accuracy: {summary['topic']['deterministic_accuracy']}

Effective Topic accuracy: {summary['topic']['effective_accuracy']}

Deterministic Format accuracy: {summary['format']['deterministic_accuracy']}

Effective Format accuracy: {summary['format']['effective_accuracy']}

Reader Intent accuracy: {summary['reader_intent_accuracy']}

Effective full-case accuracy: {summary['effective_full_case_accuracy']}

Scientific status after evaluation: EVALUATED_PREREGISTERED_HOLDOUT

No production classifications, confidences, Gate decisions, or registration artifacts were mutated.
"""


def run_evaluation(
    *, model: str, output_json: Path = OUTPUT_JSON, output_md: Path = OUTPUT_MD,
    provider: SemanticAdjudicationProvider | None = None,
    secret_resolver: SemanticAdjudicationSecretResolver | None = None,
    client_factory: Callable[[SemanticAdjudicationRuntimeContext], Any] | None = None,
    adjudication_gate: Any = None, assessor: Any = None,
    monotonic: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    _verify_registration()
    if provider is None:
        context = SemanticAdjudicationRuntimeContextBuilder(
            config_validator=SemanticAdjudicationProviderConfigValidator(),
            secret_resolver=secret_resolver or EnvironmentSemanticAdjudicationSecretResolver(),
        ).build(_configuration(model))
        raw_client = (client_factory or _create_openai_client)(context)
        provider = OpenAISemanticAdjudicationProvider(runtime_context=context, client=raw_client)
    limited = _LimitedProvider(provider)
    assessing_workflow = _AssessingEditorialWorkflow(assessor)
    workflow_kwargs: dict[str, Any] = {"provider": limited, "editorial_workflow": assessing_workflow}
    if adjudication_gate is not None:
        workflow_kwargs["adjudication_gate"] = adjudication_gate
    workflow = ExperimentalSemanticAdjudicationShadowWorkflow(**workflow_kwargs)
    manifest = {item["id"]: item for item in read_manifest(BATCH_ROOT)}
    cases = []
    for case_id in CASE_IDS:
        source = parse_source(BATCH_ROOT / manifest[case_id]["source_file"])
        capturing = _SanitizedErrorCapturingProvider(limited)
        workflow.provider = capturing
        started = monotonic()
        result = workflow.analyze(**_source_fields(source))
        latency = max(0, round((monotonic() - started) * 1000))
        cases.append(_unscored_case(case_id, result, list(assessing_workflow.last_assessments), latency, capturing.sanitized_error))
    if limited.call_count > MAX_CALLS:
        raise RuntimeError("Batch 07 provider call limit exceeded")
    _score_cases(cases)
    summary = _summarize(
        cases, limited.call_count,
        evaluated_at=now().isoformat(),
        evaluation_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True).stdout.strip(),
    )
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    summary = run_evaluation(model=args.model)
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
