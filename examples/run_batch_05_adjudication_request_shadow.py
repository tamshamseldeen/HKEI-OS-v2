"""Evaluate Batch 05 semantic adjudication request payloads in shadow mode."""

from dataclasses import asdict
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields
from examples.run_benchmark_batch_02_validation import (
    parse_source,
    read_expectations,
    read_manifest,
)
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.deterministic_semantic_adjudication_gate import (
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_request_builder import (
    SemanticAdjudicationRequestBuilder,
)
from src.formatting.editorial_format import EditorialFormat
from src.topic.topic import Topic
from src.workflows.experimental_semantic_editorial_analysis_workflow import (
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
OUTPUT_JSON = BATCH_ROOT / "adjudication_request_shadow.json"
OUTPUT_MD = BATCH_ROOT / "adjudication_request_shadow.md"
CASE_IDS = tuple(f"{case_id:03d}" for case_id in range(41, 51))
_FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
_FORBIDDEN_RISK = (
    "risk",
    "risk_band",
    "attribution_required",
    "uncertainty_present",
    "sensitive_context",
    "human_risk_annotations",
)
_FORBIDDEN_API = ("api_key", "openai_api_key", "credential")


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _average(values: list[float | int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _contains_forbidden_key(value: dict[str, Any], needles: tuple[str, ...]) -> bool:
    return any(
        needle in key.casefold()
        for key in value
        for needle in needles
    )


def _source_text_only(title: str, lead: str, excerpt: str, body: str) -> bool:
    normalized_body = " ".join(body.split())
    return (
        bool(title or title == "")
        and " ".join(lead.split()) in normalized_body
        and " ".join(excerpt.split()) in normalized_body
    )


def analyze_request_shadow(
    *,
    batch_root: Path = BATCH_ROOT,
    workflow: Any | None = None,
    gate: Any | None = None,
    builder: Any | None = None,
) -> dict[str, Any]:
    """Build and validate requests before using expectations for coverage only."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    active_builder = builder or SemanticAdjudicationRequestBuilder()
    built_cases: list[dict[str, Any]] = []

    for manifest_case in read_manifest(batch_root):
        parsed_source = parse_source(batch_root / manifest_case["source_file"])
        result = active_workflow.process(**_source_fields(parsed_source))
        normalized_source = result.classification_result.ingestion.source
        content_classification = result.classification_result.classification
        decision = active_gate.evaluate(
            topic_classification=result.topic_classification,
            format_classification=result.format_classification,
            contextual_evidence=result.contextual_evidence,
            semantic_evidence=result.semantic_evidence,
        )
        required = decision.scope is not AdjudicationScope.NOT_REQUIRED
        request = None
        stable = True
        if required:
            arguments = {
                "request_id": f"batch_05_{parsed_source.case_id}",
                "source": normalized_source,
                "content_classification": content_classification,
                "topic_classification": result.topic_classification,
                "format_classification": result.format_classification,
                "contextual_evidence": result.contextual_evidence,
                "semantic_evidence": result.semantic_evidence,
                "decision": decision,
            }
            request = active_builder.build(**arguments)
            rebuilt = active_builder.build(**arguments)
            stable = request == rebuilt and (
                request.input_fingerprint == rebuilt.input_fingerprint
            )

        errors: list[str] = []
        if required != (request is not None):
            errors.append("REQUEST_GATE_SCOPE_MISMATCH")
        request_dict = asdict(request) if request is not None else {}
        risk_present = _contains_forbidden_key(request_dict, _FORBIDDEN_RISK)
        reader_intent_present = "reader_intent" in request_dict
        provider_present = any(label in request_dict for label in ("provider", "model"))
        api_present = _contains_forbidden_key(request_dict, _FORBIDDEN_API)

        if request is not None:
            if request.title != (normalized_source.title or "").strip():
                errors.append("TITLE_INVALID")
            if len(request.lead) > 500:
                errors.append("LEAD_LIMIT_EXCEEDED")
            if len(request.body_excerpt) > 1800:
                errors.append("EXCERPT_LIMIT_EXCEEDED")
            if not _FINGERPRINT.fullmatch(request.input_fingerprint):
                errors.append("FINGERPRINT_INVALID")
            if not stable:
                errors.append("FINGERPRINT_UNSTABLE")
            if not request.deterministic_topic:
                errors.append("DETERMINISTIC_TOPIC_MISSING")
            if not request.deterministic_format:
                errors.append("DETERMINISTIC_FORMAT_MISSING")
            if not request.candidate_topics:
                errors.append("CANDIDATE_TOPICS_EMPTY")
            if not request.candidate_formats:
                errors.append("CANDIDATE_FORMATS_EMPTY")
            if request.candidate_topics[0] != request.deterministic_topic:
                errors.append("DETERMINISTIC_TOPIC_NOT_FIRST")
            if request.candidate_formats[0] != request.deterministic_format:
                errors.append("DETERMINISTIC_FORMAT_NOT_FIRST")
            if not set(request.candidate_topics) <= {item.value for item in Topic}:
                errors.append("INVALID_TOPIC_CANDIDATE")
            if not set(request.candidate_formats) <= {
                item.value for item in EditorialFormat
            }:
                errors.append("INVALID_FORMAT_CANDIDATE")
            if not decision.topic_required and len(request.candidate_topics) != 1:
                errors.append("TOPIC_SCOPE_NOT_RESPECTED")
            if not decision.format_required and len(request.candidate_formats) != 1:
                errors.append("FORMAT_SCOPE_NOT_RESPECTED")
            if not _source_text_only(
                request.title,
                request.lead,
                request.body_excerpt,
                normalized_source.body,
            ):
                errors.append("REQUEST_TEXT_NOT_SOURCE_ONLY")
        if risk_present:
            errors.append("RISK_METADATA_PRESENT")
        if reader_intent_present:
            errors.append("READER_INTENT_PRESENT")
        if provider_present:
            errors.append("PROVIDER_METADATA_PRESENT")
        if api_present:
            errors.append("API_CREDENTIAL_PRESENT")

        body_length = len(normalized_source.body)
        excerpt_length = len(request.body_excerpt) if request else 0
        case = {
            "id": parsed_source.case_id,
            "gate_scope": decision.scope.value,
            "topic_required": decision.topic_required,
            "format_required": decision.format_required,
            "request_created": request is not None,
            "request_id": request.request_id if request else None,
            "title_length": len(request.title) if request else 0,
            "lead_length": len(request.lead) if request else 0,
            "body_excerpt_length": excerpt_length,
            "body_source_length": body_length,
            "excerpt_ratio": excerpt_length / body_length if body_length else 0.0,
            "contextual_support_count": (
                len(request.contextual_support_labels) if request else 0
            ),
            "contextual_suppression_count": (
                len(request.contextual_suppressions) if request else 0
            ),
            "semantic_relationship_summary_count": (
                len(request.semantic_relationship_summary) if request else 0
            ),
            "primary_candidate_count": (
                len(request.primary_domain_candidates) if request else 0
            ),
            "secondary_candidate_count": (
                len(request.secondary_domain_candidates) if request else 0
            ),
            "candidate_topics": list(request.candidate_topics) if request else [],
            "candidate_formats": list(request.candidate_formats) if request else [],
            "candidate_topic_count": len(request.candidate_topics) if request else 0,
            "candidate_topic_diversity": (
                len(set(request.candidate_topics)) if request else 0
            ),
            "candidate_format_count": len(request.candidate_formats) if request else 0,
            "input_fingerprint": request.input_fingerprint if request else None,
            "full_body_identical_to_excerpt": (
                request.body_excerpt == normalized_source.body if request else False
            ),
            "request_contains_expected_body_only": (
                _source_text_only(
                    request.title,
                    request.lead,
                    request.body_excerpt,
                    normalized_source.body,
                ) if request else True
            ),
            "request_contains_risk_metadata": risk_present,
            "request_contains_reader_intent": reader_intent_present,
            "request_contains_provider_metadata": provider_present,
            "request_contains_api_credentials": api_present,
            "fingerprint_stable": stable,
            "request_valid": not errors,
            "validation_errors": errors,
        }
        built_cases.append(case)

    # Expectations are joined only after every request has been constructed.
    expected_by_id = {
        item["id"]: item for item in read_expectations(batch_root)
    }
    for case in built_cases:
        expected = expected_by_id[case["id"]]
        case["expected_topic_available_in_candidates"] = (
            expected["topic"] in case["candidate_topics"]
            if case["topic_required"] else None
        )
        case["expected_format_available_in_candidates"] = (
            expected["editorial_format"] in case["candidate_formats"]
            if case["format_required"] else None
        )

    requests = [case for case in built_cases if case["request_created"]]
    topic_required = [case for case in built_cases if case["topic_required"]]
    format_required = [case for case in built_cases if case["format_required"]]
    lead_lengths = [case["lead_length"] for case in requests]
    excerpt_lengths = [case["body_excerpt_length"] for case in requests]
    excerpt_ratios = [case["excerpt_ratio"] for case in requests]
    topic_available = sum(
        case["expected_topic_available_in_candidates"] for case in topic_required
    )
    format_available = sum(
        case["expected_format_available_in_candidates"] for case in format_required
    )
    return {
        "batch": "batch_05",
        "case_count": len(built_cases),
        "requests_created": len(requests),
        "requests_avoided": len(built_cases) - len(requests),
        "topic_required_cases": len(topic_required),
        "expected_topic_available_cases": topic_available,
        "expected_topic_candidate_coverage": _percentage(
            topic_available, len(topic_required)
        ),
        "format_required_cases": len(format_required),
        "expected_format_available_cases": format_available,
        "expected_format_candidate_coverage": _percentage(
            format_available, len(format_required)
        ),
        "average_lead_length": _average(lead_lengths),
        "max_lead_length": max(lead_lengths, default=0),
        "average_excerpt_length": _average(excerpt_lengths),
        "max_excerpt_length": max(excerpt_lengths, default=0),
        "average_excerpt_ratio": _average(excerpt_ratios),
        "max_excerpt_ratio": max(excerpt_ratios, default=0.0),
        "requests_using_full_body": sum(
            case["full_body_identical_to_excerpt"] for case in requests
        ),
        "requests_truncated_or_selected": sum(
            not case["full_body_identical_to_excerpt"] for case in requests
        ),
        "invalid_requests": sum(not case["request_valid"] for case in requests),
        "stable_requests": sum(case["fingerprint_stable"] for case in requests),
        "cases_missing_expected_topic_candidate": [
            case["id"] for case in topic_required
            if not case["expected_topic_available_in_candidates"]
        ],
        "cases_missing_expected_format_candidate": [
            case["id"] for case in format_required
            if not case["expected_format_available_in_candidates"]
        ],
        "risk_metadata_present": any(
            case["request_contains_risk_metadata"] for case in requests
        ),
        "reader_intent_present": any(
            case["request_contains_reader_intent"] for case in requests
        ),
        "provider_metadata_present": any(
            case["request_contains_provider_metadata"] for case in requests
        ),
        "api_credentials_present": any(
            case["request_contains_api_credentials"] for case in requests
        ),
        "cases": built_cases,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    structurally_valid = (
        analysis["invalid_requests"] == 0
        and analysis["requests_created"] == 9
        and analysis["requests_avoided"] == 1
        and analysis["stable_requests"] == analysis["requests_created"]
        and not any(
            analysis[key]
            for key in (
                "risk_metadata_present",
                "reader_intent_present",
                "provider_metadata_present",
                "api_credentials_present",
            )
        )
    )
    if (
        structurally_valid
        and analysis["expected_topic_candidate_coverage"] == 100.0
        and analysis["expected_format_candidate_coverage"] == 100.0
    ):
        return "EXCELLENT"
    if (
        structurally_valid
        and analysis["expected_topic_candidate_coverage"] >= 75.0
        and analysis["expected_format_candidate_coverage"] >= 75.0
    ):
        return "PASSED"
    return "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[str]) -> str:
    return ", ".join(values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    cases = analysis["cases"]
    requests = [case for case in cases if case["request_created"]]
    largest = max(requests, key=lambda case: case["body_excerpt_length"])
    smallest = min(requests, key=lambda case: case["body_excerpt_length"])
    full_body = [
        case["id"] for case in requests if case["full_body_identical_to_excerpt"]
    ]
    exceeded = [
        case["id"] for case in requests
        if case["lead_length"] > 500 or case["body_excerpt_length"] > 1800
    ]
    lines = [
        "# Batch 05 Semantic Adjudication Request Shadow Diagnostic", "",
        "## Summary", "", "Cases:", str(analysis["case_count"]), "",
        "Requests Created:", str(analysis["requests_created"]), "",
        "Requests Avoided:", str(analysis["requests_avoided"]), "",
        "Topic-Required Cases:", str(analysis["topic_required_cases"]), "",
        "Format-Required Cases:", str(analysis["format_required_cases"]), "",
        "Topic Candidate Coverage:",
        f'{analysis["expected_topic_candidate_coverage"]:.2f}%', "",
        "Format Candidate Coverage:",
        f'{analysis["expected_format_candidate_coverage"]:.2f}%', "",
        "Average Lead Length:", f'{analysis["average_lead_length"]:.2f}', "",
        "Maximum Lead Length:", str(analysis["max_lead_length"]), "",
        "Average Excerpt Length:",
        f'{analysis["average_excerpt_length"]:.2f}', "",
        "Maximum Excerpt Length:", str(analysis["max_excerpt_length"]), "",
        "Average Excerpt Ratio:",
        f'{analysis["average_excerpt_ratio"] * 100:.2f}%', "",
        "Requests Using Full Body:", str(analysis["requests_using_full_body"]), "",
        "Invalid Requests:", str(analysis["invalid_requests"]), "",
        "## Case Table", "",
        "| ID | Gate Scope | Request Created | Lead Length | Excerpt Length | Excerpt Ratio | Topic Candidates | Format Candidates | Expected Topic Available | Expected Format Available | Valid |",
        "|---|---|---|---:|---:|---:|---|---|---|---|---|",
    ]
    for case in cases:
        topic_available = case["expected_topic_available_in_candidates"]
        format_available = case["expected_format_available_in_candidates"]
        lines.append(
            f'| {case["id"]} | {case["gate_scope"]} | '
            f'{"YES" if case["request_created"] else "NO"} | '
            f'{case["lead_length"]} | {case["body_excerpt_length"]} | '
            f'{case["excerpt_ratio"] * 100:.2f}% | '
            f'{_display(case["candidate_topics"])} | '
            f'{_display(case["candidate_formats"])} | '
            f'{"N/A" if topic_available is None else "YES" if topic_available else "NO"} | '
            f'{"N/A" if format_available is None else "YES" if format_available else "NO"} | '
            f'{"YES" if case["request_valid"] else "NO"} |'
        )
    lines.extend([
        "", "## Minimal Text Review", "",
        f'- Largest excerpt case: {largest["id"]} ({largest["body_excerpt_length"]})',
        f'- Smallest excerpt case: {smallest["id"]} ({smallest["body_excerpt_length"]})',
        f'- Full-body requests: {_display(full_body)}',
        f'- Requests exceeding limits: {_display(exceeded)}', "",
        "## Candidate Coverage", "",
        "Topic-required cases missing expected Topic:",
        _display(analysis["cases_missing_expected_topic_candidate"]), "",
        "Format-required cases missing expected Format:",
        _display(analysis["cases_missing_expected_format_candidate"]), "",
        "## Isolation Checks", "",
        f'Risk metadata present: {"YES" if analysis["risk_metadata_present"] else "NO"}', "",
        f'Reader Intent present: {"YES" if analysis["reader_intent_present"] else "NO"}', "",
        f'Provider metadata present: {"YES" if analysis["provider_metadata_present"] else "NO"}', "",
        f'API credentials present: {"YES" if analysis["api_credentials_present"] else "NO"}', "",
        "## Fingerprint Stability", "",
        f'Stable requests: {analysis["stable_requests"]}/{analysis["requests_created"]}', "",
    ])
    return "\n".join(lines)


def main() -> None:
    analysis = analyze_request_shadow()
    OUTPUT_JSON.write_text(render_json(analysis), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(analysis), encoding="utf-8")
    print("=== BATCH 05 SEMANTIC ADJUDICATION REQUEST SHADOW ===")
    print(f'Status: {diagnostic_status(analysis)}')
    print(f'Cases: {analysis["case_count"]}')
    print(f'Requests: {analysis["requests_created"]}/{analysis["case_count"]}')
    print(
        "Topic candidate coverage: "
        f'{analysis["expected_topic_candidate_coverage"]:.2f}%'
    )
    print(
        "Format candidate coverage: "
        f'{analysis["expected_format_candidate_coverage"]:.2f}%'
    )
    print(f'Invalid requests: {analysis["invalid_requests"]}')


if __name__ == "__main__":
    main()
