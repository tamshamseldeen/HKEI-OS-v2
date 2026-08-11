"""Evaluate counterfactual semantic adjudication candidate-universe policies."""

import json
from pathlib import Path
from statistics import median
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_adjudication_unresolved_evidence_trigger_analysis import (
    BATCHES,
    BENCHMARK_ROOT,
    _expected_topics,
    parse_batch_01_source,
    parse_source,
    read_manifest,
)
from examples.run_batch_04_editorial_validation import _source_fields
from examples.run_benchmark_batch_02_validation import read_expectations
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


OUTPUT_JSON = BENCHMARK_ROOT / "adjudication_candidate_universe_analysis.json"
OUTPUT_MD = BENCHMARK_ROOT / "adjudication_candidate_universe_analysis.md"
CURRENT = "CURRENT_STRUCTURED_ONLY"
FULL = "FULL_ENUM_FOR_REQUIRED_SCOPE"
THIN = "FULL_ENUM_FALLBACK_WHEN_EVIDENCE_THIN"
NO_DOMAIN = "FULL_ENUM_FALLBACK_WHEN_NO_SEMANTIC_DOMAIN"
STRATEGY_NAMES = (CURRENT, FULL, THIN, NO_DOMAIN)


def _deduplicate(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _append_enum(values: tuple[str, ...], enum_values: tuple[str, ...]) -> tuple[str, ...]:
    return _deduplicate((*values, *enum_values))


def construct_strategies(
    *,
    deterministic_topic: str,
    deterministic_format: str,
    structured_topics: tuple[str, ...],
    structured_formats: tuple[str, ...],
    topic_required: bool,
    format_required: bool,
    primary_domain_candidates: tuple[str, ...],
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Construct all policies without benchmark truth inputs."""
    topic_enum = tuple(item.value for item in Topic)
    format_enum = tuple(item.value for item in EditorialFormat)
    deterministic_topics = (deterministic_topic,)
    deterministic_formats = (deterministic_format,)

    def topics_or_deterministic(values: tuple[str, ...]) -> tuple[str, ...]:
        return values if topic_required else deterministic_topics

    def formats_or_deterministic(values: tuple[str, ...]) -> tuple[str, ...]:
        return values if format_required else deterministic_formats

    full_topics = _append_enum(structured_topics, topic_enum)
    full_formats = _append_enum(structured_formats, format_enum)
    thin_topics = (
        full_topics if topic_required and len(set(structured_topics)) <= 2
        else structured_topics
    )
    thin_formats = (
        full_formats if format_required and len(set(structured_formats)) <= 2
        else structured_formats
    )
    no_domain_topics = (
        full_topics
        if topic_required and not primary_domain_candidates
        else structured_topics
    )
    return {
        CURRENT: {
            "candidate_topics": topics_or_deterministic(structured_topics),
            "candidate_formats": formats_or_deterministic(structured_formats),
        },
        FULL: {
            "candidate_topics": topics_or_deterministic(full_topics),
            "candidate_formats": formats_or_deterministic(full_formats),
        },
        THIN: {
            "candidate_topics": topics_or_deterministic(thin_topics),
            "candidate_formats": formats_or_deterministic(thin_formats),
        },
        NO_DOMAIN: {
            "candidate_topics": topics_or_deterministic(no_domain_topics),
            "candidate_formats": formats_or_deterministic(structured_formats),
        },
    }


def _expected_formats(batch_root: Path) -> dict[str, str]:
    path = batch_root / "expected.json"
    if not path.exists():
        return {}
    return {
        item["id"]: item["editorial_format"]
        for item in read_expectations(batch_root)
    }


def _percentage(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def _average(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _coverage(cases: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    required = [
        case for case in cases
        if case[f"{dimension}_required"]
        and case[f"expected_{dimension}"] is not None
    ]
    available = sum(
        case[f"expected_{dimension}_available"] for case in required
    )
    counts = [len(case[f"candidate_{dimension}s"]) for case in required]
    return {
        f"{dimension}_required_cases": len(required),
        f"expected_{dimension}_available_cases": available,
        f"{dimension}_candidate_coverage": _percentage(available, len(required)),
        f"average_{dimension}_candidate_count": _average(counts),
        f"median_{dimension}_candidate_count": median(counts) if counts else 0.0,
        f"max_{dimension}_candidate_count": max(counts, default=0),
    }


def _batch_coverage(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for batch in BATCHES:
        batch_cases = [case for case in cases if case["batch"] == batch]
        topic = _coverage(batch_cases, "topic")
        editorial_format = _coverage(batch_cases, "format")
        result[batch] = {
            "topic_required_cases": topic["topic_required_cases"],
            "topic_candidate_coverage": topic["topic_candidate_coverage"],
            "format_required_cases": editorial_format["format_required_cases"],
            "format_candidate_coverage": editorial_format[
                "format_candidate_coverage"
            ],
        }
    return result


def analyze_candidate_universes(
    *,
    benchmark_root: Path = BENCHMARK_ROOT,
    workflow: Any | None = None,
    gate: Any | None = None,
    builder: Any | None = None,
) -> dict[str, Any]:
    """Build strategies first, then join persisted editorial truth for scoring."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    active_builder = builder or SemanticAdjudicationRequestBuilder()
    cases: list[dict[str, Any]] = []

    for batch in BATCHES:
        batch_root = benchmark_root / batch
        for manifest_case in read_manifest(batch_root):
            source_path = batch_root / manifest_case["source_file"]
            parsed_source = (
                parse_batch_01_source(source_path)
                if batch == "batch_01"
                else parse_source(source_path)
            )
            result = active_workflow.process(**_source_fields(parsed_source))
            decision = active_gate.evaluate(
                topic_classification=result.topic_classification,
                format_classification=result.format_classification,
                contextual_evidence=result.contextual_evidence,
                semantic_evidence=result.semantic_evidence,
            )
            case: dict[str, Any] = {
                "batch": batch,
                "id": parsed_source.case_id,
                "gate_scope": decision.scope.value,
                "topic_required": decision.topic_required,
                "format_required": decision.format_required,
                "deterministic_topic": result.topic_classification.topic.value,
                "deterministic_format": (
                    result.format_classification.editorial_format.value
                ),
                "primary_domain_candidates": list(
                    result.semantic_evidence.primary_domain_candidates
                ),
                "expected_topic": None,
                "expected_format": None,
                "strategies": None,
            }
            if decision.scope is not AdjudicationScope.NOT_REQUIRED:
                request = active_builder.build(
                    request_id=f"{batch}_{parsed_source.case_id}",
                    source=result.classification_result.ingestion.source,
                    content_classification=(
                        result.classification_result.classification
                    ),
                    topic_classification=result.topic_classification,
                    format_classification=result.format_classification,
                    contextual_evidence=result.contextual_evidence,
                    semantic_evidence=result.semantic_evidence,
                    decision=decision,
                )
                constructed = construct_strategies(
                    deterministic_topic=request.deterministic_topic,
                    deterministic_format=request.deterministic_format,
                    structured_topics=request.candidate_topics,
                    structured_formats=request.candidate_formats,
                    topic_required=decision.topic_required,
                    format_required=decision.format_required,
                    primary_domain_candidates=(
                        request.primary_domain_candidates
                    ),
                )
                case["strategies"] = {
                    name: {
                        "candidate_topics": list(values["candidate_topics"]),
                        "candidate_formats": list(values["candidate_formats"]),
                        "expected_topic_available": None,
                        "expected_format_available": None,
                    }
                    for name, values in constructed.items()
                }
            cases.append(case)

    # Truth is loaded only after every counterfactual candidate set is frozen.
    expected_topics: dict[tuple[str, str], str] = {}
    expected_formats: dict[tuple[str, str], str] = {}
    for batch in BATCHES:
        batch_root = benchmark_root / batch
        expected_topics.update({
            (batch, case_id): value
            for case_id, value in _expected_topics(batch_root).items()
        })
        expected_formats.update({
            (batch, case_id): value
            for case_id, value in _expected_formats(batch_root).items()
        })
    for case in cases:
        key = (case["batch"], case["id"])
        case["expected_topic"] = expected_topics.get(key)
        case["expected_format"] = expected_formats.get(key)
        if case["strategies"] is None:
            continue
        for values in case["strategies"].values():
            values["expected_topic_available"] = (
                case["expected_topic"] in values["candidate_topics"]
                if case["topic_required"] and case["expected_topic"] is not None
                else None
            )
            values["expected_format_available"] = (
                case["expected_format"] in values["candidate_formats"]
                if case["format_required"] and case["expected_format"] is not None
                else None
            )

    strategy_metrics: dict[str, dict[str, Any]] = {}
    for name in STRATEGY_NAMES:
        strategy_cases: list[dict[str, Any]] = []
        scope_violations: list[str] = []
        payload_sizes: list[int] = []
        for case in cases:
            if case["strategies"] is None:
                continue
            values = case["strategies"][name]
            strategy_case = {
                **case,
                **values,
            }
            strategy_cases.append(strategy_case)
            payload_sizes.append(
                len(json.dumps(
                    {
                        "candidate_topics": values["candidate_topics"],
                        "candidate_formats": values["candidate_formats"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ))
            )
            if (
                not case["topic_required"]
                and values["candidate_topics"] != [case["deterministic_topic"]]
            ) or (
                not case["format_required"]
                and values["candidate_formats"] != [case["deterministic_format"]]
            ):
                scope_violations.append(f'{case["batch"]}/{case["id"]}')
        topic = _coverage(strategy_cases, "topic")
        editorial_format = _coverage(strategy_cases, "format")
        coverage_by_batch = _batch_coverage(strategy_cases)
        quality = (
            "EXCELLENT"
            if topic["topic_candidate_coverage"] == 100.0
            and editorial_format["format_candidate_coverage"] == 100.0
            and not scope_violations
            else "ACCEPTABLE"
            if topic["topic_candidate_coverage"] >= 95.0
            and editorial_format["format_candidate_coverage"] >= 95.0
            and not scope_violations
            else "POOR"
        )
        strategy_metrics[name] = {
            **topic,
            **editorial_format,
            "average_candidate_payload_chars": _average(payload_sizes),
            "max_candidate_payload_chars": max(payload_sizes, default=0),
            "coverage_by_batch": coverage_by_batch,
            "scope_violations": scope_violations,
            "quality": quality,
        }
    return {
        "cases_analyzed": len(cases),
        "requests_analyzed": sum(case["strategies"] is not None for case in cases),
        "strategies": strategy_metrics,
        "recommendation": "USE_FULL_ENUM_FOR_REQUIRED_SCOPE",
        "cases": cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def render_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Semantic Adjudication Candidate-Universe Analysis", "",
        "## Problem", "",
        "Current Batch 05 shadow request coverage:", "", "Topic:", "0.00%", "",
        "Format:", "25.00%", "",
        "Structurally valid requests can still be semantically incapable of correction when the target label is absent.", "",
        "## Strategy Comparison", "",
        "| Strategy | Topic Coverage | Avg Topic Candidates | Format Coverage | Avg Format Candidates | Avg Payload Chars | Scope Violations | Quality |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name in STRATEGY_NAMES:
        metrics = analysis["strategies"][name]
        lines.append(
            f'| {name} | {metrics["topic_candidate_coverage"]:.2f}% | '
            f'{metrics["average_topic_candidate_count"]:.2f} | '
            f'{metrics["format_candidate_coverage"]:.2f}% | '
            f'{metrics["average_format_candidate_count"]:.2f} | '
            f'{metrics["average_candidate_payload_chars"]:.2f} | '
            f'{len(metrics["scope_violations"])} | {metrics["quality"]} |'
        )
    lines.extend(["", "## Batch-by-Batch Coverage", ""])
    for name in STRATEGY_NAMES:
        lines.extend([
            f"### {name}", "",
            "| Batch | Topic Required | Topic Coverage | Format Required | Format Coverage |",
            "|---|---:|---:|---:|---:|",
        ])
        for batch, metrics in analysis["strategies"][name][
            "coverage_by_batch"
        ].items():
            lines.append(
                f'| {batch} | {metrics["topic_required_cases"]} | '
                f'{metrics["topic_candidate_coverage"]:.2f}% | '
                f'{metrics["format_required_cases"]} | '
                f'{metrics["format_candidate_coverage"]:.2f}% |'
            )
        lines.append("")
    lines.extend([
        "## Candidate-Universe Architecture", "",
        "The Gate controls when external semantic adjudication is allowed. The candidate universe controls what legal decisions the adjudicator may return. It must not become a second deterministic classifier.", "",
        "A narrow set lowers ambiguity but can make correction impossible. A full enum gives broader semantic freedom while remaining schema-safe because every label is bounded by the current enums.", "",
        "The provider may select only from the supplied enum-bounded universe, and a later Resolver must validate and apply the response. Non-required dimensions remain deterministic-only.", "",
        "## Recommendation", "", analysis["recommendation"], "",
        "This policy maximizes correction possibility, preserves schema restriction and scope isolation, avoids benchmark-specific mappings, and is simple to audit.", "",
        "Batch 01 has no persisted EditorialFormat expectation, so its Format-required cases are included in request-size and scope analysis but excluded from Format coverage denominators.", "",
    ])
    return "\n".join(lines)


def main() -> None:
    analysis = analyze_candidate_universes()
    OUTPUT_JSON.write_text(render_json(analysis), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(analysis), encoding="utf-8")
    print("=== SEMANTIC ADJUDICATION CANDIDATE-UNIVERSE ANALYSIS ===")
    print(f'Cases: {analysis["cases_analyzed"]}')
    print(f'Requests: {analysis["requests_analyzed"]}')
    for name in STRATEGY_NAMES:
        metrics = analysis["strategies"][name]
        print(
            f'{name}: Topic={metrics["topic_candidate_coverage"]:.2f}% '
            f'Format={metrics["format_candidate_coverage"]:.2f}% '
            f'Quality={metrics["quality"]}'
        )
    print(f'Recommendation: {analysis["recommendation"]}')


if __name__ == "__main__":
    main()
