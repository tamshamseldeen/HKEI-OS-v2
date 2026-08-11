"""Validate Batch 05 semantic adjudication shadow plumbing offline."""

from dataclasses import replace
import json
from pathlib import Path
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
from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.adjudication_scope import AdjudicationScope
from src.adjudication.semantic_adjudication_provider import (
    SemanticAdjudicationProvider,
)
from src.adjudication.semantic_adjudication_provider_error import (
    SemanticAdjudicationProviderUnavailableError,
)
from src.adjudication.semantic_adjudication_request import (
    SemanticAdjudicationRequest,
)
from src.adjudication.semantic_adjudication_response import (
    SemanticAdjudicationResponse,
)
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (
    ExperimentalSemanticAdjudicationShadowWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_05"
OUTPUT_JSON = BATCH_ROOT / "adjudication_shadow_plumbing.json"
OUTPUT_MD = BATCH_ROOT / "adjudication_shadow_plumbing.md"
CASE_IDS = tuple(f"{case_id:03d}" for case_id in range(41, 51))


class OfflineOracleProvider(SemanticAdjudicationProvider):
    """Return benchmark-selected responses solely after receiving a request."""

    def __init__(self, expected_topic: str, expected_format: str) -> None:
        self.expected_topic = expected_topic
        self.expected_format = expected_format
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "offline-oracle"

    @property
    def model_name(self) -> str:
        return "diagnostic-v1"

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        self.calls += 1
        topic_required = len(request.candidate_topics) > 1
        format_required = len(request.candidate_formats) > 1
        if topic_required and self.expected_topic not in request.candidate_topics:
            raise AssertionError("expected Topic is outside request candidates")
        if format_required and self.expected_format not in request.candidate_formats:
            raise AssertionError("expected Format is outside request candidates")
        return SemanticAdjudicationResponse(
            adjudicated_topic=(
                self.expected_topic if topic_required else request.deterministic_topic
            ),
            adjudicated_format=(
                self.expected_format if format_required else request.deterministic_format
            ),
            topic_confidence=(
                AdjudicationConfidence.HIGH
                if topic_required else AdjudicationConfidence.MEDIUM
            ),
            format_confidence=(
                AdjudicationConfidence.HIGH
                if format_required else AdjudicationConfidence.MEDIUM
            ),
            topic_reason="offline plumbing oracle topic selection",
            format_reason="offline plumbing oracle format selection",
            topic_evidence_refs=("HEADLINE",) if topic_required else (),
            format_evidence_refs=("LEAD",) if format_required else (),
            ambiguity_remaining=False,
            warnings=(),
            provider=self.provider_name,
            model=self.model_name,
            request_schema_version="1.0",
            response_schema_version="1.0",
            input_fingerprint=request.input_fingerprint,
            usage_input_tokens=0,
            usage_output_tokens=0,
        )


class InvalidFingerprintProvider(OfflineOracleProvider):
    """Return one structurally valid response with a wrong fingerprint."""

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        response = super().adjudicate(request)
        return replace(response, input_fingerprint="0" * 64)


class UnavailableProvider(OfflineOracleProvider):
    """Raise the provider-neutral unavailable error for failure plumbing."""

    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        self.calls += 1
        raise SemanticAdjudicationProviderUnavailableError("offline probe")


def _shadow_mutations(result: Any) -> tuple[bool, bool, bool]:
    request = result.request
    if request is None:
        return False, False, False
    return (
        result.editorial_result.topic_classification.topic.value
        != request.deterministic_topic,
        result.editorial_result.format_classification.editorial_format.value
        != request.deterministic_format,
        False,
    )


def _run_probe(
    source_fields: dict[str, Any],
    provider: SemanticAdjudicationProvider,
    *,
    invalid: bool,
) -> bool:
    result = ExperimentalSemanticAdjudicationShadowWorkflow(
        provider=provider
    ).analyze(**source_fields)
    unchanged = not any(_shadow_mutations(result))
    if invalid:
        return (
            result.request is not None
            and result.provider_called
            and result.provider_response is not None
            and result.validated_response is None
            and not result.response_valid
            and unchanged
        )
    return (
        result.request is not None
        and result.provider_called
        and result.provider_response is None
        and result.validated_response is None
        and not result.response_valid
        and result.provider_error == "SemanticAdjudicationProviderUnavailableError"
        and unchanged
    )


def analyze_shadow_plumbing(*, batch_root: Path = BATCH_ROOT) -> dict[str, Any]:
    """Exercise the complete shadow contract without resolving classifications."""
    expected_by_id = {item["id"]: item for item in read_expectations(batch_root)}
    cases: list[dict[str, Any]] = []
    first_required_fields: dict[str, Any] | None = None
    first_required_expected: dict[str, str] | None = None

    for manifest_case in read_manifest(batch_root):
        parsed = parse_source(batch_root / manifest_case["source_file"])
        source_fields = _source_fields(parsed)
        expected = expected_by_id[parsed.case_id]
        provider = OfflineOracleProvider(
            expected["topic"], expected["editorial_format"]
        )
        result = ExperimentalSemanticAdjudicationShadowWorkflow(
            provider=provider
        ).analyze(**source_fields)
        request = result.request
        response = result.validated_response
        decision = result.adjudication_decision
        if request is not None and first_required_fields is None:
            first_required_fields = source_fields
            first_required_expected = expected

        topic_mutated, format_mutated, intent_mutated = _shadow_mutations(result)
        topic_available = (
            expected["topic"] in request.candidate_topics
            if request is not None and decision.topic_required else None
        )
        format_available = (
            expected["editorial_format"] in request.candidate_formats
            if request is not None and decision.format_required else None
        )
        cases.append({
            "id": parsed.case_id,
            "gate_scope": decision.scope.value,
            "request_created": request is not None,
            "provider_called": result.provider_called,
            "response_valid": result.response_valid,
            "deterministic_topic": (
                request.deterministic_topic
                if request else result.editorial_result.topic_classification.topic.value
            ),
            "oracle_topic": response.adjudicated_topic if response else None,
            "deterministic_format": (
                request.deterministic_format
                if request else result.editorial_result.format_classification.editorial_format.value
            ),
            "oracle_format": response.adjudicated_format if response else None,
            "topic_changed_in_shadow": topic_mutated,
            "format_changed_in_shadow": format_mutated,
            "intent_changed_in_shadow": intent_mutated,
            "candidate_topic_count": len(request.candidate_topics) if request else 0,
            "candidate_format_count": len(request.candidate_formats) if request else 0,
            "expected_topic_available": topic_available,
            "expected_format_available": format_available,
            "fingerprint_valid": (
                response.input_fingerprint == request.input_fingerprint
                if response and request else None
            ),
            "provider_error": result.provider_error,
        })

    assert first_required_fields is not None and first_required_expected is not None
    invalid_probe_passed = _run_probe(
        first_required_fields,
        InvalidFingerprintProvider(
            first_required_expected["topic"],
            first_required_expected["editorial_format"],
        ),
        invalid=True,
    )
    provider_error_probe_passed = _run_probe(
        first_required_fields,
        UnavailableProvider(
            first_required_expected["topic"],
            first_required_expected["editorial_format"],
        ),
        invalid=False,
    )

    required = [case for case in cases if case["request_created"]]
    topic_required = [
        case for case in cases
        if case["gate_scope"] in ("TOPIC_REQUIRED", "TOPIC_AND_FORMAT_REQUIRED")
    ]
    format_required = [
        case for case in cases
        if case["gate_scope"] in ("FORMAT_REQUIRED", "TOPIC_AND_FORMAT_REQUIRED")
    ]
    topic_coverage = sum(case["expected_topic_available"] for case in topic_required)
    format_coverage = sum(case["expected_format_available"] for case in format_required)
    return {
        "batch": "batch_05",
        "case_count": len(cases),
        "requests_created": len(required),
        "requests_avoided": len(cases) - len(required),
        "provider_calls": sum(case["provider_called"] for case in cases),
        "validated_responses": sum(case["response_valid"] for case in cases),
        "invalid_responses": sum(
            case["provider_called"] and not case["response_valid"]
            and case["provider_error"] is None for case in cases
        ),
        "provider_errors": sum(case["provider_error"] is not None for case in cases),
        "topic_required_cases": len(topic_required),
        "format_required_cases": len(format_required),
        "oracle_expected_topic_in_candidates": topic_coverage,
        "oracle_expected_format_in_candidates": format_coverage,
        "validated_topic_matches_expected": sum(
            case["oracle_topic"] == expected_by_id[case["id"]]["topic"]
            for case in topic_required
        ),
        "validated_format_matches_expected": sum(
            case["oracle_format"] == expected_by_id[case["id"]]["editorial_format"]
            for case in format_required
        ),
        "expected_topic_candidate_coverage": (
            topic_coverage / len(topic_required) * 100.0 if topic_required else 0.0
        ),
        "expected_format_candidate_coverage": (
            format_coverage / len(format_required) * 100.0 if format_required else 0.0
        ),
        "shadow_topic_mutations": sum(case["topic_changed_in_shadow"] for case in cases),
        "shadow_format_mutations": sum(case["format_changed_in_shadow"] for case in cases),
        "shadow_intent_mutations": sum(case["intent_changed_in_shadow"] for case in cases),
        "invalid_probe_passed": invalid_probe_passed,
        "provider_error_probe_passed": provider_error_probe_passed,
        "cases": cases,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    normal_valid = (
        analysis["validated_responses"] == analysis["requests_created"]
        and analysis["invalid_responses"] == 0
        and analysis["provider_errors"] == 0
        and analysis["shadow_topic_mutations"] == 0
        and analysis["shadow_format_mutations"] == 0
        and analysis["shadow_intent_mutations"] == 0
    )
    excellent = normal_valid and all((
        analysis["requests_created"] == 9,
        analysis["requests_avoided"] == 1,
        analysis["provider_calls"] == 9,
        analysis["expected_topic_candidate_coverage"] == 100.0,
        analysis["expected_format_candidate_coverage"] == 100.0,
        analysis["invalid_probe_passed"],
        analysis["provider_error_probe_passed"],
    ))
    return "EXCELLENT" if excellent else "PASSED" if normal_valid else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Batch 05 Semantic Adjudication Shadow Plumbing Validation", "",
        "## Summary", "", "Cases:", str(analysis["case_count"]), "",
        "Requests Created:", str(analysis["requests_created"]), "",
        "Requests Avoided:", str(analysis["requests_avoided"]), "",
        "Provider Calls:", str(analysis["provider_calls"]), "",
        "Validated Responses:", str(analysis["validated_responses"]), "",
        "Invalid Responses:", str(analysis["invalid_responses"]), "",
        "Provider Errors:", str(analysis["provider_errors"]), "",
        "Topic Candidate Coverage:",
        f'{analysis["expected_topic_candidate_coverage"]:.2f}%', "",
        "Format Candidate Coverage:",
        f'{analysis["expected_format_candidate_coverage"]:.2f}%', "",
        "Shadow Topic Mutations:", str(analysis["shadow_topic_mutations"]), "",
        "Shadow Format Mutations:", str(analysis["shadow_format_mutations"]), "",
        "Shadow Intent Mutations:", str(analysis["shadow_intent_mutations"]), "",
        "## Case Table", "",
        "| ID | Scope | Request | Provider Called | Validated | Deterministic Topic | Oracle Topic | Deterministic Format | Oracle Format | Shadow Mutation |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for case in analysis["cases"]:
        mutation = any((case["topic_changed_in_shadow"], case["format_changed_in_shadow"], case["intent_changed_in_shadow"]))
        lines.append(
            f'| {case["id"]} | {case["gate_scope"]} | '
            f'{"YES" if case["request_created"] else "NO"} | '
            f'{"YES" if case["provider_called"] else "NO"} | '
            f'{"YES" if case["response_valid"] else "NO"} | '
            f'{case["deterministic_topic"]} | {case["oracle_topic"] or "N/A"} | '
            f'{case["deterministic_format"]} | {case["oracle_format"] or "N/A"} | '
            f'{"YES" if mutation else "NO"} |'
        )
    lines.extend([
        "", "## Invalid Response Probe", "",
        "PASS" if analysis["invalid_probe_passed"] else "FAIL", "",
        "## Provider Failure Probe", "",
        "PASS" if analysis["provider_error_probe_passed"] else "FAIL", "",
    ])
    return "\n".join(lines)


def main() -> None:
    analysis = analyze_shadow_plumbing()
    OUTPUT_JSON.write_text(render_json(analysis), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(analysis), encoding="utf-8")
    print(f"Status: {diagnostic_status(analysis)}")
    print(f'Cases: {analysis["case_count"]}')
    print(f'Requests: {analysis["requests_created"]}')
    print(f'Validated responses: {analysis["validated_responses"]}')


if __name__ == "__main__":
    main()
