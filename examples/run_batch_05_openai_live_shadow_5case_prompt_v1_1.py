"""Run one bounded five-case Prompt v1.1 live shadow A/B comparison."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import examples.run_batch_05_openai_live_shadow_5case as live_runner
from examples.run_openai_semantic_adjudication_live_canary import _configuration
from src.adjudication.openai_semantic_adjudication_provider import (
    OPENAI_ADJUDICATION_PROMPT_VERSION,
)
from src.adjudication.semantic_adjudication_reasoning_effort import (
    SemanticAdjudicationReasoningEffort,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
BASELINE_JSON = BATCH_ROOT / "openai_live_shadow_5case.json"
OUTPUT_JSON = BATCH_ROOT / "openai_live_shadow_5case_prompt_v1_1.json"
OUTPUT_MD = BATCH_ROOT / "openai_live_shadow_5case_prompt_v1_1.md"
COMPARISON_JSON = BATCH_ROOT / "openai_live_shadow_5case_ab_comparison.json"
COMPARISON_MD = BATCH_ROOT / "openai_live_shadow_5case_ab_comparison.md"
CASE_IDS = ("044", "045", "046", "048", "050")
PROMPT_VERSION = "1.1"
MAX_CALLS = 5


class ABRuntimeMismatchError(RuntimeError):
    """Raised before provider construction when the experiment is not isolated."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ABRuntimeMismatchError(f"{path.name} must contain a JSON object")
    return value


def verify_experiment(model: str, baseline: dict[str, Any]) -> None:
    """Require Prompt v1.1 and exact HKEI-149 runtime parity before any call."""
    if OPENAI_ADJUDICATION_PROMPT_VERSION != PROMPT_VERSION:
        raise ABRuntimeMismatchError("A_B_RUNTIME_MISMATCH: prompt version is not 1.1")
    config = _configuration(model)
    parity = (
        model == "gpt-5-mini"
        and config.provider == "openai"
        and config.model == "gpt-5-mini"
        and config.reasoning_effort is SemanticAdjudicationReasoningEffort.LOW
        and config.max_output_tokens == 1200
        and config.max_retries == 0
        and config.timeout_seconds == 30.0
        and config.temperature == 0.0
        and tuple(baseline.get("cases_selected", ())) == CASE_IDS
        and baseline.get("provider_calls") == MAX_CALLS
    )
    if not parity:
        raise ABRuntimeMismatchError("A_B_RUNTIME_MISMATCH")


def _case_correct(case: dict[str, Any]) -> bool:
    return (
        case["response_valid"]
        and (not case["topic_required"] or case["topic_match_expected"] is True)
        and (not case["format_required"] or case["format_match_expected"] is True)
    )


def _anchoring(cases: list[dict[str, Any]]) -> tuple[int, float, int]:
    required = [case for case in cases if case["format_required"]]
    preserved = sum(
        case["deterministic_format"] == case["adjudicated_format"] for case in required
    )
    wrong_preserved = sum(
        case["format_match_expected"] is False
        and case["deterministic_format"] == case["adjudicated_format"]
        for case in required
    )
    return preserved, live_runner._percentage(preserved, len(required)), wrong_preserved


def _delta(current: float | int | None, baseline: float | int | None) -> float | None:
    if current is None or baseline is None:
        return None
    return float(current) - float(baseline)


def _decorate_b_side(summary: dict[str, Any]) -> None:
    for case in summary["cases"]:
        case["provider_error"] = case.pop("provider_error_message_sanitized")
        case["topic_correct"] = case["topic_match_expected"]
        case["format_correct"] = case["format_match_expected"]
        case["candidate_compliant"] = (
            case["candidate_topic_compliant"] is True
            and case["candidate_format_compliant"] is True
        ) if case["response_valid"] else None
        case["fingerprint_valid"] = (
            case["input_fingerprint"] == case["provider_response_fingerprint"]
            == case["validated_response_fingerprint"]
        ) if case["response_valid"] else None


def comparison_status(comparison: dict[str, Any]) -> str:
    b = comparison["b_side"]
    reliable = (
        b["valid_responses"] == b["provider_calls"]
        and b["candidate_compliance_rate"] == 100.0
        and b["fingerprint_integrity_rate"] == 100.0
        and b["shadow_mutations"] == 0
    )
    if not reliable:
        return "FAILED"
    if (
        comparison["b_topic_accuracy"] >= comparison["a_topic_accuracy"]
        and comparison["b_format_accuracy"] > comparison["a_format_accuracy"]
        and comparison["b_fully_correct_cases"] > comparison["a_fully_correct_cases"]
        and b["topic_regressions"] == 0
        and comparison["b_wrong_format_with_deterministic_preserved"]
        < comparison["a_wrong_format_with_deterministic_preserved"]
    ):
        return "EXCELLENT"
    if (
        comparison["b_format_accuracy"] > comparison["a_format_accuracy"]
        and comparison["b_topic_accuracy"] >= comparison["a_topic_accuracy"]
    ):
        return "PROMISING"
    improvements = (
        comparison["topic_accuracy_delta_percentage_points"] > 0
        or comparison["format_accuracy_delta_percentage_points"] > 0
        or comparison["fully_correct_delta"] > 0
    )
    regressions = (
        comparison["topic_accuracy_delta_percentage_points"] < 0
        or comparison["format_accuracy_delta_percentage_points"] < 0
        or comparison["fully_correct_delta"] < 0
    )
    if improvements and regressions:
        return "MIXED"
    if (
        comparison["b_format_accuracy"] == 0.0
        or comparison["b_format_anchoring_rate"] == comparison["a_format_anchoring_rate"]
    ):
        return "NO_IMPROVEMENT"
    return "MIXED"


def recommendation(status: str, comparison: dict[str, Any]) -> str:
    if status in ("EXCELLENT", "PROMISING"):
        return "PROMOTE_PROMPT_V1_1_FOR_BROADER_SHADOW_EVALUATION"
    if status == "FAILED":
        return (
            "INVESTIGATE_MODEL_BEHAVIOR"
            if comparison["b_side"]["failed_responses"]
            else "INVESTIGATE_REQUEST_EVIDENCE"
        )
    if status == "NO_IMPROVEMENT":
        return "REFINE_PROMPT_BEFORE_MORE_LIVE_CALLS"
    return "INVESTIGATE_REQUEST_EVIDENCE"


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_by_id = {case["id"]: case for case in a["cases"]}
    b_by_id = {case["id"]: case for case in b["cases"]}
    a_preserved, a_anchor_rate, a_wrong_preserved = _anchoring(a["cases"])
    b_preserved, b_anchor_rate, b_wrong_preserved = _anchoring(b["cases"])
    b_ambiguous = [case for case in b["cases"] if case["ambiguity_remaining"] is True]
    valid_b = [case for case in b["cases"] if case["response_valid"]]
    per_case = []
    for case_id in CASE_IDS:
        old, new = a_by_id[case_id], b_by_id[case_id]
        per_case.append({
            "id": case_id,
            "a_adjudicated_topic": old["adjudicated_topic"],
            "b_adjudicated_topic": new["adjudicated_topic"],
            "a_topic_correct": old["topic_match_expected"],
            "b_topic_correct": new["topic_match_expected"],
            "a_adjudicated_format": old["adjudicated_format"],
            "b_adjudicated_format": new["adjudicated_format"],
            "a_format_correct": old["format_match_expected"],
            "b_format_correct": new["format_match_expected"],
            "a_topic_confidence": old["topic_confidence"],
            "b_topic_confidence": new["topic_confidence"],
            "a_format_confidence": old["format_confidence"],
            "b_format_confidence": new["format_confidence"],
            "a_ambiguity": old["ambiguity_remaining"],
            "b_ambiguity": new["ambiguity_remaining"],
            "a_reasoning_tokens": old["reasoning_tokens"],
            "b_reasoning_tokens": new["reasoning_tokens"],
            "a_output_tokens": old["output_tokens"],
            "b_output_tokens": new["output_tokens"],
            "a_latency_ms": old["latency_ms"],
            "b_latency_ms": new["latency_ms"],
            "a_deterministic_format_preserved": old["deterministic_format"] == old["adjudicated_format"],
            "b_deterministic_format_preserved": new["deterministic_format"] == new["adjudicated_format"],
        })
    b_shadow = sum(
        b[key] for key in (
            "shadow_topic_mutations", "shadow_format_mutations", "shadow_intent_mutations"
        )
    )
    result = {
        "prompt_version": PROMPT_VERSION,
        "cases": list(CASE_IDS),
        "a_topic_accuracy": a["topic_accuracy"],
        "b_topic_accuracy": b["topic_accuracy"],
        "topic_accuracy_delta_percentage_points": b["topic_accuracy"] - a["topic_accuracy"],
        "a_format_accuracy": a["format_accuracy"],
        "b_format_accuracy": b["format_accuracy"],
        "format_accuracy_delta_percentage_points": b["format_accuracy"] - a["format_accuracy"],
        "a_fully_correct_cases": a["full_correct_cases"],
        "b_fully_correct_cases": b["full_correct_cases"],
        "fully_correct_delta": b["full_correct_cases"] - a["full_correct_cases"],
        "a_format_deterministic_preserved": a_preserved,
        "b_format_deterministic_preserved": b_preserved,
        "a_format_anchoring_rate": a_anchor_rate,
        "b_format_anchoring_rate": b_anchor_rate,
        "format_anchoring_rate_delta_percentage_points": b_anchor_rate - a_anchor_rate,
        "a_wrong_format_with_deterministic_preserved": a_wrong_preserved,
        "b_wrong_format_with_deterministic_preserved": b_wrong_preserved,
        "wrong_format_with_deterministic_preserved_delta": b_wrong_preserved - a_wrong_preserved,
        "a_ambiguity_rate": a["ambiguity_rate"],
        "b_ambiguity_rate": b["ambiguity_rate"],
        "ambiguity_rate_delta_percentage_points": b["ambiguity_rate"] - a["ambiguity_rate"],
        "b_correct_when_ambiguity_true": sum(_case_correct(case) for case in b_ambiguous),
        "b_wrong_when_ambiguity_true": sum(not _case_correct(case) for case in b_ambiguous),
        "average_input_token_delta": _delta(b["average_input_tokens"], a["average_input_tokens"]),
        "average_input_token_delta_percent": (
            (b["average_input_tokens"] - a["average_input_tokens"])
            / a["average_input_tokens"] * 100.0 if a["average_input_tokens"] else None
        ),
        "average_output_token_delta": _delta(b["average_output_tokens"], a["average_output_tokens"]),
        "average_reasoning_token_delta": _delta(b["average_reasoning_tokens"], a["average_reasoning_tokens"]),
        "average_non_reasoning_output_token_delta": _delta(b["average_non_reasoning_output_tokens"], a["average_non_reasoning_output_tokens"]),
        "average_latency_delta_ms": _delta(b["average_latency_ms"], a["average_latency_ms"]),
        "median_latency_delta_ms": _delta(b["median_latency_ms"], a["median_latency_ms"]),
        "max_latency_delta_ms": _delta(b["max_latency_ms"], a["max_latency_ms"]),
        "b_side": {
            "provider_calls": b["provider_calls"],
            "valid_responses": b["valid_responses"],
            "failed_responses": b["failed_responses"],
            "topic_adjudication_cases": b["topic_adjudication_cases"],
            "topic_correct": b["topic_correct"],
            "topic_improvements": b["topic_improvements"],
            "topic_regressions": b["topic_regressions"],
            "format_adjudication_cases": b["format_adjudication_cases"],
            "format_correct": b["format_correct"],
            "format_improvements": b["format_improvements"],
            "format_regressions": b["format_regressions"],
            "candidate_compliance_rate": b["candidate_compliance_rate"],
            "fingerprint_integrity_rate": b["fingerprint_integrity_rate"],
            "shadow_mutations": b_shadow,
            "average_input_tokens": b["average_input_tokens"],
            "average_output_tokens": b["average_output_tokens"],
            "average_reasoning_tokens": b["average_reasoning_tokens"],
            "average_non_reasoning_output_tokens": b["average_non_reasoning_output_tokens"],
            "average_reasoning_share": b["average_reasoning_share"],
            "average_latency_ms": b["average_latency_ms"],
            "median_latency_ms": b["median_latency_ms"],
            "max_latency_ms": b["max_latency_ms"],
        },
        "per_case": per_case,
    }
    result["comparison_status"] = comparison_status(result)
    result["recommended_next_step"] = recommendation(result["comparison_status"], result)
    return result


def render_comparison_markdown(result: dict[str, Any]) -> str:
    return f"""# OpenAI Prompt v1.1 Five-Case A/B Comparison

Prompt Version: {result['prompt_version']}

Comparison Status: {result['comparison_status']}

Cases: 044, 045, 046, 048, 050

## Accuracy

A Topic Accuracy: {result['a_topic_accuracy']:.2f}%

B Topic Accuracy: {result['b_topic_accuracy']:.2f}%

A Format Accuracy: {result['a_format_accuracy']:.2f}%

B Format Accuracy: {result['b_format_accuracy']:.2f}%

A Fully Correct: {result['a_fully_correct_cases']}

B Fully Correct: {result['b_fully_correct_cases']}

## Format Anchoring

A Rate: {result['a_format_anchoring_rate']:.2f}%

B Rate: {result['b_format_anchoring_rate']:.2f}%

A Wrong Format Preserved: {result['a_wrong_format_with_deterministic_preserved']}

B Wrong Format Preserved: {result['b_wrong_format_with_deterministic_preserved']}

## Reliability and Efficiency

Valid Responses: {result['b_side']['valid_responses']}/{result['b_side']['provider_calls']}

Candidate Compliance: {result['b_side']['candidate_compliance_rate']:.2f}%

Fingerprint Integrity: {result['b_side']['fingerprint_integrity_rate']:.2f}%

Average Input Token Delta: {result['average_input_token_delta']}

Average Latency Delta: {result['average_latency_delta_ms']} ms

## Statistical Restraint

These five cases show observed changes only; they do not establish statistical significance.

## Recommended Next Step

{result['recommended_next_step']}
"""


def run_comparison(
    *,
    model: str,
    batch_root: Path = BATCH_ROOT,
    baseline_json: Path = BASELINE_JSON,
    output_json: Path = OUTPUT_JSON,
    output_md: Path = OUTPUT_MD,
    comparison_json: Path = COMPARISON_JSON,
    comparison_md: Path = COMPARISON_MD,
    **evaluation_kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline = _read(baseline_json)
    verify_experiment(model, baseline)
    b_side = live_runner.run_evaluation(
        model=model,
        batch_root=batch_root,
        output_json=output_json,
        output_md=output_md,
        **evaluation_kwargs,
    )
    if b_side["provider_calls"] > MAX_CALLS:
        raise RuntimeError("five-case Prompt v1.1 comparison exceeded five calls")
    _decorate_b_side(b_side)
    output_json.write_text(live_runner.render_json(b_side), encoding="utf-8")
    output_md.write_text(live_runner.render_markdown(b_side), encoding="utf-8")
    result = compare(baseline, b_side)
    comparison_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    comparison_md.write_text(render_comparison_markdown(result), encoding="utf-8")
    return b_side, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    arguments = parser.parse_args(argv)
    _, result = run_comparison(model=arguments.model)
    print(json.dumps({key: value for key, value in result.items() if key != "per_case"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
