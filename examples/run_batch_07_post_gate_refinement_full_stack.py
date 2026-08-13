"""Run the final Batch 07 shadow evaluation after the bounded Gate refinement."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_07_full_stack_shadow_evaluation import (  # noqa: E402
    BATCH_ROOT, CASE_IDS, _configuration, run_evaluation,
)
from src.adjudication.openai_semantic_adjudication_provider import (  # noqa: E402
    OPENAI_ADJUDICATION_PROMPT_VERSION,
)


BASELINE_JSON = BATCH_ROOT / "full_stack_shadow_evaluation.json"
OUTPUT_JSON = BATCH_ROOT / "post_gate_refinement_full_stack_evaluation.json"
OUTPUT_MD = BATCH_ROOT / "post_gate_refinement_full_stack_evaluation.md"
COMPARISON_JSON = BATCH_ROOT / "gate_refinement_comparison.json"
COMPARISON_MD = BATCH_ROOT / "gate_refinement_comparison.md"
BASELINE_COMMIT = "059dec46c55e60558ecc4bc3c85ce0477cb4ff7f"
REFINEMENT_COMMIT = "842a5128ffbf7e8f8b8cdc822ec42e4481029c53"
ALLOWED_RUNTIME_CHANGE = "src/adjudication/deterministic_semantic_adjudication_gate.py"


def verify_runtime(model: str) -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", REFINEMENT_COMMIT, "HEAD"],
        cwd=PROJECT_ROOT,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("EVALUATION_RUNTIME_MISMATCH")
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{BASELINE_COMMIT}..{REFINEMENT_COMMIT}"],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    material = [path for path in changed if path.startswith("src/") or path == "examples/run_batch_07_full_stack_shadow_evaluation.py"]
    if material != [ALLOWED_RUNTIME_CHANGE]:
        raise RuntimeError("EVALUATION_RUNTIME_MISMATCH")
    config = _configuration(model)
    if not (
        config.provider == "openai"
        and config.model == "gpt-5-mini"
        and config.reasoning_effort.value == "LOW"
        and config.max_output_tokens == 1200
        and config.max_retries == 0
        and config.timeout_seconds == 30.0
        and config.temperature == 0.0
        and OPENAI_ADJUDICATION_PROMPT_VERSION == "1.1"
    ):
        raise RuntimeError("EVALUATION_RUNTIME_MISMATCH")


def _gate_false_negatives(cases: list[dict[str, Any]], dimension: str) -> set[str]:
    return {
        case["id"] for case in cases
        if not case[f"{dimension}_required"] and not case[f"{dimension}_match_before"]
    }


def _gate_false_positives(cases: list[dict[str, Any]], dimension: str) -> set[str]:
    return {
        case["id"] for case in cases
        if case[f"{dimension}_required"] and case[f"{dimension}_match_before"]
    }


def _delta(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    return {key: current[key] - previous[key] for key in ("tp", "fp", "tn", "fn", "precision", "recall")}


def _new_call_utility(case: dict[str, Any]) -> str:
    if case["topic_regression"] or case["format_regression"]:
        return "WRONG_CHANGE"
    if case["topic_improvement"] or case["format_improvement"]:
        return "USEFUL_CORRECTION"
    changed_wrong = any(
        case[f"effective_shadow_{dimension}"] != case[f"deterministic_{dimension}"]
        and not case[f"{dimension}_match_after"]
        for dimension in ("topic", "format")
    )
    return "WRONG_TO_WRONG" if changed_wrong else "SAFE_NO_CHANGE"


def _product_evaluation(current: dict[str, Any]) -> str:
    reliable = (
        current["valid_responses"] == current["provider_calls"]
        and current["candidate_compliance"] == 100.0
        and current["fingerprint_integrity"] == 100.0
        and not any(current[key] for key in (
            "shadow_topic_mutated", "shadow_format_mutated",
            "shadow_intent_mutated", "actual_confidence_mutated", "gate_mutated",
        ))
    )
    if not reliable:
        return "FAILED"
    regressions = current["topic"]["regressions"] + current["format"]["regressions"]
    if (
        current["topic"]["effective_accuracy"] >= 90
        and current["format"]["effective_accuracy"] >= 80
        and current["effective_full_case_accuracy"] >= 70
        and regressions == 0
    ):
        return "EXCELLENT"
    if (
        current["topic"]["effective_accuracy"] >= 80
        and current["format"]["effective_accuracy"] >= 70
        and current["effective_full_case_accuracy"] >= 60
        and regressions <= 1
    ):
        return "STRONG"
    if current["topic"]["effective_accuracy"] < 60 or current["format"]["effective_accuracy"] < 60:
        return "WEAK"
    return "MIXED"


def compare(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    previous_cases = {case["id"]: case for case in baseline["cases"]}
    current_cases = {case["id"]: case for case in current["cases"]}
    if tuple(current_cases) != CASE_IDS or tuple(previous_cases) != CASE_IDS:
        raise RuntimeError("Batch 07 case inventory mismatch")
    previous_topic_fn = _gate_false_negatives(baseline["cases"], "topic")
    current_topic_fn = _gate_false_negatives(current["cases"], "topic")
    previous_format_fn = _gate_false_negatives(baseline["cases"], "format")
    current_format_fn = _gate_false_negatives(current["cases"], "format")
    captured_topic = previous_topic_fn - current_topic_fn
    captured_format = previous_format_fn - current_format_fn
    previous_fp = _gate_false_positives(baseline["cases"], "topic") | _gate_false_positives(baseline["cases"], "format")
    current_fp = _gate_false_positives(current["cases"], "topic") | _gate_false_positives(current["cases"], "format")
    new_call_ids = set(current["provider_call_cases"]) - set(baseline["provider_call_cases"])
    new_calls = []
    for case_id in sorted(new_call_ids):
        case = current_cases[case_id]
        previous = previous_cases[case_id]
        opened = [
            dimension.upper() for dimension in ("topic", "format")
            if case[f"{dimension}_required"] and not previous[f"{dimension}_required"]
        ]
        new_calls.append({
            "id": case_id,
            "new_gate_scope": case["gate_scope"],
            "dimensions_opened": opened,
            "provider_response_valid": case["response_valid"],
            "topic_effect": (
                "CORRECT" if case["topic_match_after"] else "WRONG"
            ) if "TOPIC" in opened else "NOT_OPENED",
            "format_effect": (
                "CORRECT" if case["format_match_after"] else "WRONG"
            ) if "FORMAT" in opened else "NOT_OPENED",
            "utility": _new_call_utility(case),
        })

    topic_delta = _delta(current["topic_gate"], baseline["topic_gate"])
    format_delta = _delta(current["format_gate"], baseline["format_gate"])
    reliability = (
        current["valid_responses"] == current["provider_calls"]
        and current["candidate_compliance"] == 100.0
        and current["fingerprint_integrity"] == 100.0
        and current["retry_attempts"] == 0
    )
    recalls_improved = topic_delta["recall"] > 0 or format_delta["recall"] > 0
    format_material = format_delta["recall"] >= 20
    regression_growth = (
        current["topic"]["regressions"] + current["format"]["regressions"]
        - baseline["topic"]["regressions"] - baseline["format"]["regressions"]
    )
    if reliability and not current_topic_fn and format_material and current["provider_calls"] <= 10 and regression_growth <= 0:
        refinement = "SUCCESSFUL"
    elif reliability and recalls_improved and regression_growth <= 1:
        refinement = "PARTIALLY_SUCCESSFUL"
    elif reliability and not format_material:
        refinement = "NO_MATERIAL_IMPROVEMENT"
    else:
        refinement = "REGRESSION"
    product = _product_evaluation(current)
    if product in {"EXCELLENT", "STRONG"}:
        decision = "READY_TO_DESIGN_RESOLVER"
    elif current["format"]["effective_accuracy"] < 60:
        decision = "ANALYZE_UPSTREAM_FORMAT_FAILURES"
    elif product == "MIXED":
        decision = "KEEP_CURRENT_GATE_AND_PROCEED_WITH_LIMITED_RESOLVER_DESIGN"
    else:
        decision = "NOT_READY_FOR_RESOLVER"
    return {
        "gate_refinement_assessment": refinement,
        "product_evaluation": product,
        "final_decision": decision,
        "previous_provider_calls": baseline["provider_calls"],
        "current_provider_calls": current["provider_calls"],
        "provider_call_delta": current["provider_calls"] - baseline["provider_calls"],
        "previous_provider_call_rate": baseline["provider_call_rate"],
        "current_provider_call_rate": current["provider_call_rate"],
        "topic_gate_delta": topic_delta,
        "format_gate_delta": format_delta,
        "previous_topic_fn": sorted(previous_topic_fn),
        "current_topic_fn": sorted(current_topic_fn),
        "previous_format_fn": sorted(previous_format_fn),
        "current_format_fn": sorted(current_format_fn),
        "previous_topic_fn_status": {case_id: "CAPTURED" if case_id in captured_topic else "STILL_MISSED" for case_id in sorted(previous_topic_fn)},
        "previous_format_fn_status": {case_id: "CAPTURED" if case_id in captured_format else "STILL_MISSED" for case_id in sorted(previous_format_fn)},
        "new_gate_false_positives": sorted(current_fp - previous_fp),
        "new_gate_false_positive_count": len(current_fp - previous_fp),
        "new_provider_calls": new_calls,
        "recovered_topic_fn_count": len(captured_topic),
        "recovered_topic_fn_corrected_by_provider": sum(current_cases[case_id]["topic_match_after"] for case_id in captured_topic),
        "recovered_format_fn_count": len(captured_format),
        "recovered_format_fn_corrected_by_provider": sum(current_cases[case_id]["format_match_after"] for case_id in captured_format),
        "previous_effective_topic_accuracy": baseline["topic"]["effective_accuracy"],
        "current_effective_topic_accuracy": current["topic"]["effective_accuracy"],
        "topic_accuracy_delta": current["topic"]["effective_accuracy"] - baseline["topic"]["effective_accuracy"],
        "previous_effective_format_accuracy": baseline["format"]["effective_accuracy"],
        "current_effective_format_accuracy": current["format"]["effective_accuracy"],
        "format_accuracy_delta": current["format"]["effective_accuracy"] - baseline["format"]["effective_accuracy"],
        "previous_effective_full_accuracy": baseline["effective_full_case_accuracy"],
        "current_effective_full_accuracy": current["effective_full_case_accuracy"],
        "full_accuracy_delta": current["effective_full_case_accuracy"] - baseline["effective_full_case_accuracy"],
        "batch_07_gate_refinement_budget_remaining": 0,
        "batch_07_scientific_status": "EVALUATED_PREREGISTERED_HOLDOUT",
        "additional_gate_tuning_recommended": False,
        "provider_calls": current["provider_calls"],
    }


def render_markdown(current: dict[str, Any], comparison: dict[str, Any]) -> str:
    return f"""# Batch 07 Post-Gate-Refinement Full-Stack Evaluation

Gate refinement assessment: {comparison['gate_refinement_assessment']}

Product evaluation: {comparison['product_evaluation']}

Final decision: {comparison['final_decision']}

Provider calls: {comparison['previous_provider_calls']} -> {comparison['current_provider_calls']}

Topic Gate recall: {current['topic_gate']['recall']}

Format Gate recall: {current['format_gate']['recall']}

Effective Topic accuracy: {current['topic']['effective_accuracy']}

Effective Format accuracy: {current['format']['effective_accuracy']}

Effective full-case accuracy: {current['effective_full_case_accuracy']}

Batch 07 Gate refinement budget remaining: 0

No additional Batch 07 Gate tuning is permitted.
"""


def run_final(
    *, model: str, output_json: Path = OUTPUT_JSON,
    output_md: Path = OUTPUT_MD,
    comparison_json: Path = COMPARISON_JSON,
    comparison_md: Path = COMPARISON_MD,
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    verify_runtime(model)
    current = run_evaluation(
        model=model, output_json=output_json, output_md=output_md, **kwargs,
    )
    # Load the truth-bearing baseline only after every current shadow result and
    # optional provider response has completed.
    baseline = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    comparison = compare(current, baseline)
    current["gate_refinement_comparison"] = {
        key: value for key, value in comparison.items()
        if key not in {"new_provider_calls"}
    }
    output_json.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(current, comparison), encoding="utf-8")
    comparison_json.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    comparison_md.write_text(render_markdown(current, comparison), encoding="utf-8")
    return current, comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    current, comparison = run_final(model=args.model)
    print(json.dumps({
        "cases_evaluated": current["cases_evaluated"],
        "provider_calls": current["provider_calls"],
        "valid_responses": current["valid_responses"],
        "invalid_responses": current["invalid_responses"],
        "provider_errors": current["provider_errors"],
        "topic_gate": current["topic_gate"],
        "format_gate": current["format_gate"],
        "topic": current["topic"],
        "format": current["format"],
        "reader_intent_accuracy": current["reader_intent_accuracy"],
        "effective_full_case_accuracy": current["effective_full_case_accuracy"],
        "fully_correct_cases": current["fully_correct_cases"],
        **comparison,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
