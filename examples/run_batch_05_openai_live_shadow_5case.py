"""Run a bounded five-case OpenAI adjudication shadow evaluation."""

import argparse
import json
from pathlib import Path
from statistics import mean, median
import sys
import time
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_05_editorial_validation import _source_fields
from examples.run_benchmark_batch_02_validation import (
    parse_source,
    read_expectations,
    read_manifest,
)
from examples.run_openai_semantic_adjudication_live_canary import (
    _SanitizedErrorCapturingProvider,
    _configuration,
    _create_openai_client,
)
from src.adjudication.openai_semantic_adjudication_provider import (
    OpenAISemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_config_validator import (
    SemanticAdjudicationProviderConfigValidator,
)
from src.adjudication.semantic_adjudication_runtime_context import (
    SemanticAdjudicationRuntimeContext,
)
from src.adjudication.semantic_adjudication_runtime_context_builder import (
    SemanticAdjudicationRuntimeContextBuilder,
)
from src.adjudication.semantic_adjudication_secret_resolver import (
    SemanticAdjudicationSecretResolver,
)
from src.adjudication.environment_semantic_adjudication_secret_resolver import (
    EnvironmentSemanticAdjudicationSecretResolver,
)
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
OUTPUT_JSON = BATCH_ROOT / "openai_live_shadow_5case.json"
OUTPUT_MD = BATCH_ROOT / "openai_live_shadow_5case.md"
CASE_IDS = ("044", "045", "046", "048", "050")
MAX_CALLS = 5


class _LimitedResponses:
    def __init__(self, responses: Any) -> None:
        self._responses = responses
        self.call_count = 0

    def create(self, **kwargs: Any) -> Any:
        if self.call_count >= MAX_CALLS:
            raise RuntimeError("five-case evaluation permits at most five calls")
        self.call_count += 1
        return self._responses.create(**kwargs)


class _LimitedClient:
    def __init__(self, client: Any) -> None:
        self.responses = _LimitedResponses(client.responses)


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _shadow_mutations(result: Any) -> tuple[bool, bool, bool]:
    request = result.request
    if request is None:
        return False, False, False
    editorial = result.editorial_result
    return (
        editorial.topic_classification.topic.value != request.deterministic_topic,
        editorial.format_classification.editorial_format.value
        != request.deterministic_format,
        False,
    )


def _error_fields(result: Any, sanitized: str | None) -> tuple[str | None, str | None]:
    error = result.provider_error
    if error is None:
        return None, None
    if sanitized is not None:
        return error, sanitized
    if isinstance(error, str) and error.endswith("Error"):
        return error, None
    return "SemanticAdjudicationProviderInvalidResponseError", error


def _unscored_case(case_id: str, result: Any, latency_ms: int, error: str | None) -> dict[str, Any]:
    request = result.request
    response = result.validated_response
    decision = result.adjudication_decision
    editorial = result.editorial_result
    usage = response.usage if response else None
    topic_mutated, format_mutated, intent_mutated = _shadow_mutations(result)
    error_category, error_message = _error_fields(result, error)
    return {
        "id": case_id,
        "gate_scope": decision.scope.value,
        "topic_required": decision.topic_required,
        "format_required": decision.format_required,
        "provider_called": result.provider_called,
        "response_valid": result.response_valid,
        "provider_error_category": error_category,
        "provider_error_message_sanitized": error_message,
        "deterministic_topic": (
            request.deterministic_topic
            if request else editorial.topic_classification.topic.value
        ),
        "adjudicated_topic": response.adjudicated_topic if response else None,
        "deterministic_format": (
            request.deterministic_format
            if request else editorial.format_classification.editorial_format.value
        ),
        "adjudicated_format": response.adjudicated_format if response else None,
        "topic_confidence": response.topic_confidence.value if response else None,
        "format_confidence": response.format_confidence.value if response else None,
        "ambiguity_remaining": response.ambiguity_remaining if response else None,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "reasoning_tokens": usage.reasoning_tokens if usage else None,
        "non_reasoning_output_tokens": (
            usage.output_tokens - usage.reasoning_tokens
            if usage and usage.reasoning_tokens is not None else None
        ),
        "latency_ms": latency_ms,
        "input_fingerprint": request.input_fingerprint if request else None,
        "provider_response_fingerprint": (
            result.provider_response.input_fingerprint
            if result.provider_response else None
        ),
        "validated_response_fingerprint": (
            response.input_fingerprint if response else None
        ),
        "candidate_topic_compliant": (
            response.adjudicated_topic in request.candidate_topics
            if response and request else None
        ),
        "candidate_format_compliant": (
            response.adjudicated_format in request.candidate_formats
            if response and request else None
        ),
        "returned_model": response.model if response else None,
        "shadow_topic_mutated": topic_mutated,
        "shadow_format_mutated": format_mutated,
        "shadow_intent_mutated": intent_mutated,
    }


def _score_cases(cases: list[dict[str, Any]], batch_root: Path) -> None:
    """Attach expected-label comparisons only after all provider work is complete."""
    expected_by_id = {item["id"]: item for item in read_expectations(batch_root)}
    for case in cases:
        expected = expected_by_id[case["id"]]
        case["expected_topic"] = expected["topic"]
        case["expected_format"] = expected["editorial_format"]
        case["topic_match_expected"] = (
            case["adjudicated_topic"] == expected["topic"]
            if case["topic_required"] and case["response_valid"] else None
        )
        case["format_match_expected"] = (
            case["adjudicated_format"] == expected["editorial_format"]
            if case["format_required"] and case["response_valid"] else None
        )
        case["topic_changed_vs_deterministic"] = (
            case["adjudicated_topic"] != case["deterministic_topic"]
            if case["response_valid"] else None
        )
        case["format_changed_vs_deterministic"] = (
            case["adjudicated_format"] != case["deterministic_format"]
            if case["response_valid"] else None
        )


def _summarize(cases: list[dict[str, Any]], provider_calls: int) -> dict[str, Any]:
    valid = [case for case in cases if case["response_valid"]]
    topic_cases = [case for case in cases if case["topic_required"]]
    format_cases = [case for case in cases if case["format_required"]]
    topic_correct = sum(case["topic_match_expected"] is True for case in topic_cases)
    format_correct = sum(case["format_match_expected"] is True for case in format_cases)
    full_correct = sum(
        case["response_valid"]
        and (not case["topic_required"] or case["topic_match_expected"] is True)
        and (not case["format_required"] or case["format_match_expected"] is True)
        for case in cases
    )
    topic_improvements = sum(
        case["topic_required"] and case["deterministic_topic"] != case["expected_topic"]
        and case["topic_match_expected"] is True for case in cases
    )
    topic_regressions = sum(
        case["topic_required"] and case["deterministic_topic"] == case["expected_topic"]
        and case["topic_match_expected"] is False for case in cases
    )
    format_improvements = sum(
        case["format_required"] and case["deterministic_format"] != case["expected_format"]
        and case["format_match_expected"] is True for case in cases
    )
    format_regressions = sum(
        case["format_required"] and case["deterministic_format"] == case["expected_format"]
        and case["format_match_expected"] is False for case in cases
    )
    ambiguity_true = sum(case["ambiguity_remaining"] is True for case in valid)
    reasoning = [case["reasoning_tokens"] for case in valid if case["reasoning_tokens"] is not None]
    non_reasoning = [case["non_reasoning_output_tokens"] for case in valid if case["non_reasoning_output_tokens"] is not None]
    latencies = [case["latency_ms"] for case in valid]
    compliance = [
        case["candidate_topic_compliant"] and case["candidate_format_compliant"]
        for case in valid
    ]
    fingerprints = [
        case["input_fingerprint"] == case["provider_response_fingerprint"]
        == case["validated_response_fingerprint"] for case in valid
    ]
    reasoning_shares = [
        case["reasoning_tokens"] / case["output_tokens"]
        for case in valid
        if case["reasoning_tokens"] is not None and case["output_tokens"]
    ]
    case_correct = lambda case: (
        (not case["topic_required"] or case["topic_match_expected"] is True)
        and (not case["format_required"] or case["format_match_expected"] is True)
    )
    ambiguity_false_cases = [case for case in valid if case["ambiguity_remaining"] is False]
    ambiguity_true_cases = [case for case in valid if case["ambiguity_remaining"] is True]
    summary = {
        "cases_selected": list(CASE_IDS),
        "provider_calls": provider_calls,
        "valid_responses": len(valid),
        "failed_responses": len(cases) - len(valid),
        "topic_adjudication_cases": len(topic_cases),
        "topic_correct": topic_correct,
        "topic_accuracy": _percentage(topic_correct, len(topic_cases)),
        "format_adjudication_cases": len(format_cases),
        "format_correct": format_correct,
        "format_accuracy": _percentage(format_correct, len(format_cases)),
        "full_correct_cases": full_correct,
        "topic_improvements": topic_improvements,
        "topic_regressions": topic_regressions,
        "format_improvements": format_improvements,
        "format_regressions": format_regressions,
        "ambiguity_true_cases": ambiguity_true,
        "ambiguity_rate": _percentage(ambiguity_true, len(valid)),
        "accuracy_when_ambiguity_false": _percentage(
            sum(case_correct(case) for case in ambiguity_false_cases),
            len(ambiguity_false_cases),
        ),
        "accuracy_when_ambiguity_true": _percentage(
            sum(case_correct(case) for case in ambiguity_true_cases),
            len(ambiguity_true_cases),
        ),
        "average_input_tokens": mean(case["input_tokens"] for case in valid) if valid else 0,
        "average_output_tokens": mean(case["output_tokens"] for case in valid) if valid else 0,
        "average_reasoning_tokens": mean(reasoning) if reasoning else None,
        "median_reasoning_tokens": median(reasoning) if reasoning else None,
        "average_non_reasoning_output_tokens": mean(non_reasoning) if non_reasoning else None,
        "average_reasoning_share": mean(reasoning_shares) if reasoning_shares else None,
        "average_latency_ms": mean(latencies) if latencies else 0,
        "median_latency_ms": median(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "candidate_compliance_rate": _percentage(sum(compliance), len(compliance)),
        "fingerprint_integrity_rate": _percentage(sum(fingerprints), len(fingerprints)),
        "shadow_topic_mutations": sum(case["shadow_topic_mutated"] for case in cases),
        "shadow_format_mutations": sum(case["shadow_format_mutated"] for case in cases),
        "shadow_intent_mutations": sum(case["shadow_intent_mutated"] for case in cases),
        "cases": cases,
    }
    summary["status"] = evaluation_status(summary)
    return summary


def evaluation_status(summary: dict[str, Any]) -> str:
    shadow_clean = not any(summary[key] for key in (
        "shadow_topic_mutations", "shadow_format_mutations", "shadow_intent_mutations"
    ))
    integrity = (
        summary["candidate_compliance_rate"] == 100.0
        and summary["fingerprint_integrity_rate"] == 100.0
        and shadow_clean
    )
    if (
        summary["valid_responses"] == summary["provider_calls"]
        and integrity
        and summary["topic_accuracy"] == 100.0
        and summary["format_accuracy"] == 100.0
    ):
        return "EXCELLENT"
    if (
        summary["valid_responses"] / len(CASE_IDS) >= 0.8
        and integrity
        and summary["topic_accuracy"] >= 80.0
        and summary["format_accuracy"] >= 75.0
    ):
        return "PASSED"
    return "FAILED"


def render_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n"


def render_markdown(summary: dict[str, Any]) -> str:
    percent = lambda value: f"{value:.2f}%"
    lines = [
        "# OpenAI Limited Live Shadow Evaluation — 5 Cases", "",
        "## Scope", "", "Cases: 044, 045, 046, 048, 050", "",
        "Provider: OpenAI", "", "Configured Model: gpt-5-mini", "",
        "Reasoning Effort: LOW", "", "Maximum Calls: 5", "",
        "## Reliability", "", f"Provider Calls: {summary['provider_calls']}", "",
        f"Valid Responses: {summary['valid_responses']}", "",
        f"Failed Responses: {summary['failed_responses']}", "",
        f"Candidate Compliance: {percent(summary['candidate_compliance_rate'])}", "",
        f"Fingerprint Integrity: {percent(summary['fingerprint_integrity_rate'])}", "",
        "## Editorial Accuracy", "", f"Topic Accuracy: {percent(summary['topic_accuracy'])}", "",
        f"Format Accuracy: {percent(summary['format_accuracy'])}", "",
        f"Fully Correct Cases: {summary['full_correct_cases']}/5", "",
        f"Topic Improvements: {summary['topic_improvements']}", "",
        f"Topic Regressions: {summary['topic_regressions']}", "",
        f"Format Improvements: {summary['format_improvements']}", "",
        f"Format Regressions: {summary['format_regressions']}", "",
        "## Ambiguity", "", f"Ambiguity True: {summary['ambiguity_true_cases']}", "",
        f"Ambiguity Rate: {percent(summary['ambiguity_rate'])}", "",
        "## Efficiency", "", f"Average Input Tokens: {summary['average_input_tokens']}", "",
        f"Average Output Tokens: {summary['average_output_tokens']}", "",
        f"Average Reasoning Tokens: {summary['average_reasoning_tokens']}", "",
        f"Average Non-Reasoning Output Tokens: {summary['average_non_reasoning_output_tokens']}", "",
        f"Average Reasoning Share: {percent((summary['average_reasoning_share'] or 0) * 100)}", "",
        f"Average Latency: {summary['average_latency_ms']} ms", "",
        f"Median Latency: {summary['median_latency_ms']} ms", "",
        f"Maximum Latency: {summary['max_latency_ms']} ms", "",
        "## Shadow Safety", "", f"Topic Mutations: {summary['shadow_topic_mutations']}", "",
        f"Format Mutations: {summary['shadow_format_mutations']}", "",
        f"Intent Mutations: {summary['shadow_intent_mutations']}", "",
        "## Case Table", "",
        "| ID | Scope | Valid | Det Topic | Adj Topic | Expected Topic | Topic Correct | Det Format | Adj Format | Expected Format | Format Correct | Ambiguity | Reasoning Tokens | Output Tokens | Latency |",
        "|---|---|---:|---|---|---|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for case in summary["cases"]:
        lines.append(
            "| {id} | {gate_scope} | {response_valid} | {deterministic_topic} | "
            "{adjudicated_topic} | {expected_topic} | {topic_match_expected} | "
            "{deterministic_format} | {adjudicated_format} | {expected_format} | "
            "{format_match_expected} | {ambiguity_remaining} | {reasoning_tokens} | "
            "{output_tokens} | {latency_ms} |".format(**case)
        )
    return "\n".join(lines) + "\n"


def run_evaluation(
    *,
    model: str,
    batch_root: Path = BATCH_ROOT,
    output_json: Path = OUTPUT_JSON,
    output_md: Path = OUTPUT_MD,
    secret_resolver: SemanticAdjudicationSecretResolver | None = None,
    client_factory: Callable[[SemanticAdjudicationRuntimeContext], Any] | None = None,
    adjudication_gate: Any = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    context = SemanticAdjudicationRuntimeContextBuilder(
        config_validator=SemanticAdjudicationProviderConfigValidator(),
        secret_resolver=secret_resolver or EnvironmentSemanticAdjudicationSecretResolver(),
    ).build(_configuration(model))
    raw_client = (client_factory or _create_openai_client)(context)
    guarded = _LimitedClient(raw_client)
    concrete = OpenAISemanticAdjudicationProvider(
        runtime_context=context,
        client=guarded,
    )
    manifest_by_id = {item["id"]: item for item in read_manifest(batch_root)}
    cases: list[dict[str, Any]] = []
    for case_id in CASE_IDS:
        item = manifest_by_id[case_id]
        source = parse_source(batch_root / item["source_file"])
        provider = _SanitizedErrorCapturingProvider(concrete)
        arguments: dict[str, Any] = {"provider": provider}
        if adjudication_gate is not None:
            arguments["adjudication_gate"] = adjudication_gate
        workflow = ExperimentalSemanticAdjudicationShadowWorkflow(**arguments)
        started = monotonic()
        result = workflow.analyze(**_source_fields(source))
        latency_ms = max(0, round((monotonic() - started) * 1000))
        cases.append(_unscored_case(
            case_id, result, latency_ms, provider.sanitized_error
        ))
    assert guarded.responses.call_count <= MAX_CALLS
    _score_cases(cases, batch_root)
    summary = _summarize(cases, guarded.responses.call_count)
    output_json.write_text(render_json(summary), encoding="utf-8")
    output_md.write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    arguments = parser.parse_args(argv)
    summary = run_evaluation(model=arguments.model)
    print(json.dumps({
        key: value for key, value in summary.items() if key != "cases"
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] in ("EXCELLENT", "PASSED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
