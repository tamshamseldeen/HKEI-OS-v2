"""Run the preregistered Batch 08 full-stack evaluation in shadow mode."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import examples.run_batch_07_full_stack_shadow_evaluation as base  # noqa: E402


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_08"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_08_raw.txt"
OUTPUT_JSON = BATCH_ROOT / "full_stack_shadow_evaluation.json"
OUTPUT_MD = BATCH_ROOT / "full_stack_shadow_evaluation.md"
CASE_IDS = tuple(f"{value:03d}" for value in range(71, 81))
RAW_SHA256 = "451ddb4c75b6b637f0a2b80e47fc51924fa0f30e1c2f139d6c7118bba99c7d32"
EXPECTED_SHA256 = "8684d3681d8fe7f9d439a3951863bf5334ec43286ec3c2bc6b7d69a61cea4501"
RISK_SHA256 = "25dc9eaf520472e003885ab7b6cd180b1f955b2551dd8adffa66e79b6f06e252"
MAX_CALLS = 10
REACHABILITY = {
    "NO_SIGNAL", "COMPONENT_ONLY", "RELATIONSHIP_PRESENT",
    "SEMANTIC_SUPPORT_PRESENT", "CANDIDATE_INSUFFICIENT",
    "CANDIDATE_PARTIAL", "CANDIDATE_SUFFICIENT", "CANDIDATE_CONFLICTED",
    "CLASSIFIER_RECEIVED_BUT_NOT_SELECTED",
}
RECOVERED_PROVIDER_CALLS = 6


def _verify_registration() -> None:
    manifest = json.loads((BATCH_ROOT / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() != RAW_SHA256:
        raise RuntimeError("Batch 08 raw source integrity failure")
    if hashlib.sha256((BATCH_ROOT / "expected.json").read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Batch 08 expected labels are not frozen")
    if hashlib.sha256((BATCH_ROOT / "human_risk_annotations.json").read_bytes()).hexdigest() != RISK_SHA256:
        raise RuntimeError("Batch 08 risk annotations are not frozen")
    if manifest["scientific_status"] != "UNTOUCHED_PREREGISTERED_HOLDOUT":
        raise RuntimeError("Batch 08 is not an untouched preregistered holdout")
    if tuple(manifest["case_ids"]) != CASE_IDS or manifest["validation_status"] != "NOT_RUN":
        raise RuntimeError("Batch 08 registration contract mismatch")
    if manifest["expected_labels_status"] != "PREREGISTERED_FROZEN":
        raise RuntimeError("Batch 08 expected-label status mismatch")


def _format_assessments(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in case["candidate_assessment_summary"]
        if item["candidate_group"] == "FORMAT_LIKE"
    ]


def _format_trace(case: dict[str, Any]) -> dict[str, Any]:
    assessments = _format_assessments(case)
    expected = next(
        (item for item in assessments if item["candidate"] == case["expected_format"]),
        None,
    )
    selected = next(
        (item for item in assessments if item["candidate"] == case["deterministic_format"]),
        None,
    )
    has_relationship = any(
        item["supporting_relationship_types"] or item["suppressing_relationship_types"]
        for item in assessments
    )
    expected_support = bool(expected and expected["supporting_relationship_types"])
    wrong_support = bool(
        not case["format_match_before"]
        and selected and selected["supporting_relationship_types"]
    )
    if expected:
        reachability = f"CANDIDATE_{expected['sufficiency']}"
        if expected_support and case["deterministic_format"] != case["expected_format"]:
            reachability = "CLASSIFIER_RECEIVED_BUT_NOT_SELECTED"
        elif expected_support and expected["sufficiency"] not in {
            "INSUFFICIENT", "PARTIAL", "SUFFICIENT", "CONFLICTED",
        }:
            reachability = "SEMANTIC_SUPPORT_PRESENT"
    elif has_relationship:
        reachability = "RELATIONSHIP_PRESENT"
    elif assessments:
        reachability = "COMPONENT_ONLY"
    else:
        reachability = "NO_SIGNAL"
    return {
        "format_component_present": bool(assessments),
        "semantic_format_relationship_present": has_relationship,
        "semantic_format_support_present": any(
            item["supporting_relationship_types"] for item in assessments
        ),
        "semantic_format_suppression_present": any(
            item["suppressing_relationship_types"] for item in assessments
        ),
        "expected_format_received_support": expected_support,
        "wrong_format_received_support": wrong_support,
        "expected_format_reachability": reachability if not case["format_match_before"] else None,
    }


def _percentage(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def format_generalization_decision(summary: dict[str, Any]) -> str:
    if not summary["format_mismatch_cases"]:
        return "INSUFFICIENT_EVIDENCE_TO_JUDGE"
    if (
        summary["expected_format_semantic_reachability_rate"] >= 70
        and summary["format"]["effective_accuracy"] > summary["format"]["deterministic_accuracy"]
        and summary["format"]["regressions"] == 0
    ):
        return "FORMAT_FIX_GENERALIZED"
    if summary["expected_format_semantic_support_cases"] and summary["format"]["delta"] <= 0:
        return "FORMAT_EVIDENCE_IMPROVED_BUT_FINAL_CLASSIFICATION_DID_NOT"
    if summary["cases_with_semantic_format_relationships"] and summary["expected_format_reachable_cases"]:
        return "FORMAT_FIX_PARTIALLY_GENERALIZED"
    return "FORMAT_FIX_DID_NOT_GENERALIZE"


def product_decision(summary: dict[str, Any]) -> str:
    if summary["evaluation_status"] == "FAILED":
        return "NOT_READY_FOR_RESOLVER"
    if summary["evaluation_status"] == "EXCELLENT":
        return "READY_TO_DESIGN_RESOLVER"
    if summary["evaluation_status"] == "STRONG":
        return "BEGIN_LIMITED_RESOLVER_DESIGN_WITH_FORMAT_GUARDRAILS"
    if summary["format"]["effective_accuracy"] < 40:
        return "REDESIGN_FORMAT_SUBSYSTEM"
    return "ANALYZE_BATCH_08_FULL_STACK_FAILURES_ONCE"


def _add_format_diagnostics(summary: dict[str, Any]) -> None:
    mismatch_cases = [case for case in summary["cases"] if not case["format_match_before"]]
    for case in summary["cases"]:
        case.update(_format_trace(case))
    components = sum(case["format_component_present"] for case in summary["cases"])
    relationships = sum(case["semantic_format_relationship_present"] for case in summary["cases"])
    support = sum(case["semantic_format_support_present"] for case in summary["cases"])
    reachable = sum(
        case["expected_format_reachability"] not in {None, "NO_SIGNAL", "COMPONENT_ONLY"}
        for case in mismatch_cases
    )
    summary.update({
        "format_mismatch_cases": [case["id"] for case in mismatch_cases],
        "format_reachability": {
            case["id"]: case["expected_format_reachability"] for case in mismatch_cases
        },
        "cases_with_semantic_format_relationships": relationships,
        "cases_with_semantic_format_support": support,
        "cases_with_semantic_format_suppression": sum(
            case["semantic_format_suppression_present"] for case in summary["cases"]
        ),
        "expected_format_semantic_support_cases": [
            case["id"] for case in summary["cases"]
            if case["expected_format_received_support"]
        ],
        "wrong_format_semantic_support_cases": [
            case["id"] for case in summary["cases"]
            if case["wrong_format_received_support"]
        ],
        "format_component_to_relationship_conversion": _percentage(relationships, components),
        "format_relationship_to_support_conversion": _percentage(support, relationships),
        "expected_format_reachable_cases": reachable,
        "expected_format_semantic_reachability_rate": _percentage(reachable, len(mismatch_cases)),
        "batch_07_failure_pattern_comparison": "POST_HOC_AGGREGATE_ONLY_NO_CAUSAL_CLAIM",
    })
    summary["format_generalization_decision"] = format_generalization_decision(summary)
    summary["product_decision"] = product_decision(summary)


def render_markdown(summary: dict[str, Any]) -> str:
    return f"""# Batch 08 Full-Stack Shadow Evaluation

Evaluation status: {summary['evaluation_status']}

Format generalization: {summary['format_generalization_decision']}

Product decision: {summary['product_decision']}

Cases evaluated: {summary['cases_evaluated']}

Provider calls: {summary['provider_calls']}

Deterministic / effective Topic accuracy: {summary['topic']['deterministic_accuracy']} / {summary['topic']['effective_accuracy']}

Deterministic / effective Format accuracy: {summary['format']['deterministic_accuracy']} / {summary['format']['effective_accuracy']}

Deterministic / effective full-case accuracy: {summary['deterministic_full_case_accuracy']} / {summary['effective_full_case_accuracy']}

Format component-to-relationship conversion: {summary['format_component_to_relationship_conversion']}

Format relationship-to-support conversion: {summary['format_relationship_to_support_conversion']}

Expected Format semantic reachability rate: {summary['expected_format_semantic_reachability_rate']}

Scientific status after evaluation: EVALUATED_PREREGISTERED_HOLDOUT

This is a single-batch generalization observation, not causal proof. No production
classification, confidence, Gate decision, or registration artifact was mutated.
"""


def validate_persisted_evaluation(
    output_json: Path = OUTPUT_JSON, output_md: Path = OUTPUT_MD,
) -> dict[str, Any]:
    """Acknowledge completion only after sanitized artifacts are readable."""
    _verify_registration()
    if not output_json.is_file() or not output_md.is_file():
        raise RuntimeError("Batch 08 evaluation artifacts are not observable")
    summary = json.loads(output_json.read_text(encoding="utf-8"))
    cases = summary.get("cases", [])
    required_case_fields = {
        "id", "deterministic_topic", "deterministic_format",
        "deterministic_reader_intent", "candidate_assessment_summary",
        "gate_scope", "topic_required", "format_required", "provider_called",
        "response_valid", "input_fingerprint", "expected_topic",
        "expected_format", "expected_reader_intent", "effective_shadow_topic",
        "effective_shadow_format", "effective_shadow_reader_intent",
    }
    if summary.get("cases_evaluated") != 10 or tuple(
        case.get("id") for case in cases
    ) != CASE_IDS:
        raise RuntimeError("Batch 08 persisted case inventory mismatch")
    if any(not required_case_fields <= set(case) for case in cases):
        raise RuntimeError("Batch 08 persisted case record is incomplete")
    if not (
        summary.get("provider_calls") == RECOVERED_PROVIDER_CALLS
        and summary.get("valid_responses") == RECOVERED_PROVIDER_CALLS
        and summary.get("invalid_responses") == 0
        and summary.get("provider_errors") == 0
        and summary.get("retry_attempts") == 0
        and summary.get("candidate_compliance") == 100.0
        and summary.get("fingerprint_integrity") == 100.0
    ):
        raise RuntimeError("Batch 08 persisted provider contract mismatch")
    if any(
        summary.get(key) for key in (
            "shadow_topic_mutated", "shadow_format_mutated",
            "shadow_intent_mutated", "actual_confidence_mutated", "gate_mutated",
        )
    ) or summary.get("resolver_used") is not False:
        raise RuntimeError("Batch 08 persisted shadow-safety mismatch")
    if not (
        summary.get("scientific_status_before") == "UNTOUCHED_PREREGISTERED_HOLDOUT"
        and summary.get("scientific_status_after") == "EVALUATED_PREREGISTERED_HOLDOUT"
    ):
        raise RuntimeError("Batch 08 scientific-status transition mismatch")
    persisted = output_json.read_text(encoding="utf-8") + output_md.read_text(encoding="utf-8")
    forbidden_payload = (
        re.search(r"sk-[A-Za-z0-9_-]{20,}", persisted)
        or re.search(r'"raw_prompt"\s*:', persisted)
        or re.search(r'"raw_response"\s*:', persisted)
        or "chain-of-thought" in persisted.casefold()
    )
    if forbidden_payload:
        raise RuntimeError("Batch 08 persisted sensitive payload detected")
    for case_id in CASE_IDS:
        source = (BATCH_ROOT / case_id / "source.md").read_text(encoding="utf-8")
        body = source.split("\n# Body\n", 1)[1].split("\n# Metadata\n", 1)[0].strip()
        if body and body in persisted:
            raise RuntimeError("Batch 08 source body persisted")
    return summary


def run_evaluation(*, model: str, output_json: Path = OUTPUT_JSON,
                   output_md: Path = OUTPUT_MD, **kwargs: Any) -> dict[str, Any]:
    _verify_registration()
    replacements = {
        "BATCH_ROOT": BATCH_ROOT, "RAW_SOURCE": RAW_SOURCE,
        "CASE_IDS": CASE_IDS, "RAW_SHA256": RAW_SHA256,
        "EXPECTED_SHA256": EXPECTED_SHA256, "RISK_SHA256": RISK_SHA256,
        "MAX_CALLS": MAX_CALLS,
    }
    previous = {name: getattr(base, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(base, name, value)
        summary = base.run_evaluation(
            model=model, output_json=output_json, output_md=output_md, **kwargs,
        )
    finally:
        for name, value in previous.items():
            setattr(base, name, value)
    _add_format_diagnostics(summary)
    output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    output_md.write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    summary = run_evaluation(model=args.model)
    # Prevent an external observer from treating process completion as success
    # before both final artifacts are readable and fully validated.
    validate_persisted_evaluation()
    print(json.dumps(
        {key: value for key, value in summary.items() if key != "cases"},
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
