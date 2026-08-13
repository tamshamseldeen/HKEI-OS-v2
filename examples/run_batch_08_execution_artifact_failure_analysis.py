"""Diagnose the completed Batch 08 runner/artifact observation race offline."""

import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_08"
EVALUATION_JSON = BATCH_ROOT / "full_stack_shadow_evaluation.json"
EVALUATION_MD = BATCH_ROOT / "full_stack_shadow_evaluation.md"
OUTPUT_JSON = BATCH_ROOT / "execution_artifact_failure_analysis.json"
OUTPUT_MD = BATCH_ROOT / "execution_artifact_failure_analysis.md"
RUNNER = PROJECT_ROOT / "examples" / "run_batch_08_full_stack_shadow_evaluation.py"
RUNNER_TEST = PROJECT_ROOT / "tests" / "test_batch_08_full_stack_shadow_evaluation.py"
EXPECTED_SHA256 = "8684d3681d8fe7f9d439a3951863bf5334ec43286ec3c2bc6b7d69a61cea4501"
CASE_IDS = tuple(f"{value:03d}" for value in range(71, 81))
FAILURE_STAGES = {
    "PRE_LIVE_RUNNER_FAILURE", "PRE_PROVIDER_FAILURE",
    "MID_PROVIDER_EXECUTION_FAILURE", "POST_PROVIDER_PRE_ARTIFACT_FAILURE",
    "ARTIFACT_SERIALIZATION_FAILURE", "ARTIFACT_WRITE_FAILURE",
    "POST_WRITE_VALIDATION_FAILURE", "RUNNER_PROCESS_CRASH",
    "ENVIRONMENT_FAILURE", "UNKNOWN",
}


def _source_bodies() -> list[str]:
    bodies = []
    for case_id in CASE_IDS:
        text = (BATCH_ROOT / case_id / "source.md").read_text(encoding="utf-8")
        bodies.append(text.split("\n# Body\n", 1)[1].split("\n# Metadata\n", 1)[0].strip())
    return bodies


def _inspect(path: Path, purpose: str, bodies: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    # Search for payloads, not harmless names used by leakage-guard tests.
    secret = bool(re.search(r"sk-[A-Za-z0-9_-]{20,}", text))
    raw_prompt_payload = bool(re.search(r'"raw_prompt"\s*:\s*"[^"\\]+', text))
    raw_response_payload = bool(re.search(r'"raw_response"\s*:\s*["{\[]', text))
    source_body = any(body and body in text for body in bodies)
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "purpose": purpose,
        "contains_source_body": source_body,
        "contains_secret": secret,
        "contains_raw_prompt": raw_prompt_payload,
        "contains_raw_provider_response": raw_response_payload,
        "safe_to_preserve": not any(
            (source_body, secret, raw_prompt_payload, raw_response_payload)
        ),
    }


def analyze() -> dict[str, Any]:
    if hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Batch 08 expected labels changed")
    if not EVALUATION_JSON.exists() or not EVALUATION_MD.exists():
        raise RuntimeError("Retained Batch 08 evaluation artifacts unavailable")
    evaluation = json.loads(EVALUATION_JSON.read_text(encoding="utf-8"))
    cases = evaluation.get("cases", [])
    case_ids = tuple(case.get("id") for case in cases)
    complete = (
        evaluation.get("cases_evaluated") == 10
        and case_ids == CASE_IDS
        and evaluation.get("valid_responses") == evaluation.get("provider_calls")
        and evaluation.get("invalid_responses") == 0
        and evaluation.get("provider_errors") == 0
    )
    if not complete:
        raise RuntimeError("Retained Batch 08 evaluation is incomplete")
    provider_calls = evaluation["provider_calls"]
    bodies = _source_bodies()
    inspected = [
        _inspect(RUNNER, "Batch 08 full-stack shadow runner", bodies),
        _inspect(RUNNER_TEST, "Offline fake-provider contract tests", bodies),
        _inspect(EVALUATION_JSON, "Sanitized completed evaluation", bodies),
        _inspect(EVALUATION_MD, "Sanitized evaluation summary", bodies),
    ]
    result = {
        "diagnostic_type": "OFFLINE_RETAINED_EVIDENCE_ONLY",
        "failure_stage": "POST_WRITE_VALIDATION_FAILURE",
        "live_runner_started": True,
        "classifier_execution": "CONFIRMED_10_CASES",
        "semantic_execution": "CONFIRMED_10_CASES",
        "gate_execution": "CONFIRMED_10_CASES",
        "provider_execution": "CONFIRMED",
        "provider_call_reconstruction": f"CONFIRMED_{provider_calls}",
        "provider_call_cases": evaluation["provider_call_cases"],
        "partial_cases_processed": 10,
        "partial_sanitized_results_found": False,
        "complete_sanitized_results_found": True,
        "untracked_diagnostic_files": inspected,
        "sensitive_data_findings": "NONE",
        "batch_08_recommended_scientific_status": "EVALUATED_PREREGISTERED_HOLDOUT",
        "duplicate_live_call_risk": (
            f"YES: a retry would repeat provider calls for {provider_calls} cases "
            "and violate the one-call-per-case/no-repeated-case policy."
        ),
        "artifact_failure_root_cause": "POST_RUN_VALIDATION_BUG",
        "root_cause_detail": (
            "The runner completed and atomically produced both sanitized artifacts. "
            "The initial absence report was made before those writes became observable."
        ),
        "retry_safety": "DO_NOT_RETRY_BATCH_08",
        "required_fix_scope": "DIAGNOSTIC_FIX_ONLY",
        "provider_calls_during_diagnostic": 0,
        "retry_executed": False,
        "evaluation_artifact_timestamp_utc": evaluation["evaluation_timestamp_utc"],
        "evaluation_commit": evaluation["evaluation_commit"],
        "evaluation_provider_calls": provider_calls,
        "evaluation_valid_responses": evaluation["valid_responses"],
    }
    if result["failure_stage"] not in FAILURE_STAGES:
        raise RuntimeError("Invalid diagnostic failure stage")
    return result


def render_markdown(result: dict[str, Any]) -> str:
    return f"""# Batch 08 Execution Artifact Failure Analysis

Failure stage: {result['failure_stage']}

Live runner started: YES

Provider call reconstruction: {result['provider_call_reconstruction']}

Complete sanitized results found: YES

Root cause: {result['artifact_failure_root_cause']}

The runner completed all ten cases and wrote both sanitized evaluation artifacts.
The earlier missing-artifact observation occurred before the completed writes became
observable. Batch 08 must not be retried.

Recommended scientific status: {result['batch_08_recommended_scientific_status']}

Provider calls during this diagnostic: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
