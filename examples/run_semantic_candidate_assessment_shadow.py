"""Evaluate deterministic semantic candidate assessments in shadow only."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_adjudication_unresolved_evidence_trigger_analysis import (  # noqa: E402
    _expected_topics, parse_batch_01_source, parse_source, read_manifest,
)
from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_benchmark_batch_02_validation import read_expectations  # noqa: E402
from src.adjudication.deterministic_semantic_adjudication_gate import (  # noqa: E402
    DeterministicSemanticAdjudicationGate,
)
from src.semantics.deterministic_semantic_candidate_assessor import (  # noqa: E402
    DeterministicSemanticCandidateAssessor,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (  # noqa: E402
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


BENCHMARK_ROOT = PROJECT_ROOT / "benchmark"
BATCHES = ("batch_01", "batch_02", "batch_03", "batch_05", "batch_06")
OUTPUT_JSON = BENCHMARK_ROOT / "semantic_candidate_assessment_shadow.json"
OUTPUT_MD = BENCHMARK_ROOT / "semantic_candidate_assessment_shadow.md"
SUFFICIENCIES = ("INSUFFICIENT", "PARTIAL", "SUFFICIENT", "CONFLICTED")
STRENGTHS = ("WEAK", "MODERATE", "STRONG")
DIRECTIONS = ("SUPPORT", "SUPPRESS", "NEUTRAL", "CONFLICTING")


def _expected(batch_root: Path) -> dict[str, dict[str, str | None]]:
    """Load truth only after all assessment construction has completed."""
    topics = _expected_topics(batch_root)
    expected_path = batch_root / "expected.json"
    if not expected_path.exists():
        return {
            case_id: {"topic": topic, "format": None, "intent": None}
            for case_id, topic in topics.items()
        }
    return {
        item["id"]: {
            "topic": item["topic"],
            "format": item["editorial_format"],
            "intent": item["reader_intent"],
        }
        for item in read_expectations(batch_root)
    }


def _candidate_groups(semantic: Any, contextual: Any) -> dict[str, str]:
    groups: dict[str, str] = {}
    labels = [
        label
        for relationship in semantic.relationships
        for label in relationship.supports + relationship.suppresses
    ] + list(
        semantic.primary_domain_candidates
        + semantic.secondary_domain_candidates
        + semantic.format_support
        + semantic.format_suppression
    ) + [
        label
        for item in contextual.all_items
        for label in item.supports + item.suppresses
    ]
    for label in labels:
        for prefix in ("PRIMARY_DOMAIN_", "SECONDARY_DOMAIN_", "TOPIC_"):
            if label.startswith(prefix):
                groups[label.removeprefix(prefix)] = "TOPIC_LIKE"
        if label.startswith("FORMAT_"):
            groups[label.removeprefix("FORMAT_")] = "FORMAT_LIKE"
    return groups


def _assessment_record(item: Any, group: str) -> dict[str, Any]:
    return {
        "candidate": item.candidate,
        "candidate_group": group,
        "direction": item.direction.value,
        "strength": item.strength.value,
        "sufficiency": item.sufficiency.value,
        "supporting_relationship_types": list(item.supporting_relationship_types),
        "suppressing_relationship_types": list(item.suppressing_relationship_types),
        "role_basis": list(item.role_basis),
        "competing_candidates": list(item.competing_candidates),
        "warnings": list(item.warnings),
    }


def _distribution(cases: list[dict[str, Any]], field: str, values: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(
        assessment[field] for case in cases for assessment in case["assessments"]
    )
    return {value: counts[value] for value in values}


def _state(assessments: list[dict[str, Any]], candidate: str, group: str) -> str:
    return next(
        (
            item["sufficiency"] for item in assessments
            if item["candidate"] == candidate and item["candidate_group"] == group
        ),
        "NONE",
    )


def analyze(
    *,
    workflow: Any | None = None,
    gate: Any | None = None,
    assessor: Any | None = None,
) -> dict[str, Any]:
    """Run candidate assessment after current evidence and before truth access."""
    active_workflow = workflow or ExperimentalSemanticEditorialAnalysisWorkflow()
    active_gate = gate or DeterministicSemanticAdjudicationGate()
    active_assessor = assessor or DeterministicSemanticCandidateAssessor()
    cases: list[dict[str, Any]] = []
    for batch in BATCHES:
        batch_root = BENCHMARK_ROOT / batch
        for manifest_case in read_manifest(batch_root):
            source = (
                parse_batch_01_source(batch_root / manifest_case["source_file"])
                if batch == "batch_01"
                else parse_source(batch_root / manifest_case["source_file"])
            )
            pipeline = active_workflow.process(**_source_fields(source))
            decision = active_gate.evaluate(
                topic_classification=pipeline.topic_classification,
                format_classification=pipeline.format_classification,
                contextual_evidence=pipeline.contextual_evidence,
                semantic_evidence=pipeline.semantic_evidence,
            )
            assessments = active_assessor.assess(
                semantic_evidence=pipeline.semantic_evidence,
                contextual_evidence=pipeline.contextual_evidence,
            )
            groups = _candidate_groups(
                pipeline.semantic_evidence, pipeline.contextual_evidence
            )
            cases.append({
                "batch": batch,
                "id": source.case_id,
                "topic": pipeline.topic_classification.topic.value,
                "topic_confidence": pipeline.topic_classification.confidence.value,
                "format": pipeline.format_classification.editorial_format.value,
                "format_confidence": pipeline.format_classification.confidence.value,
                "intent": pipeline.reader_intent_classification.reader_intent.value,
                "gate_scope": decision.scope.value,
                "topic_required": decision.topic_required,
                "format_required": decision.format_required,
                "assessments": [
                    _assessment_record(
                        item, groups.get(item.candidate, "CANDIDATE_TYPE_NOT_EXPLICIT")
                    )
                    for item in assessments
                ],
            })

    # Post-hoc truth joins only after predictions, gates, and assessments freeze.
    truth = {
        batch: _expected(BENCHMARK_ROOT / batch) for batch in BATCHES
    }
    for case in cases:
        expected = truth[case["batch"]][case["id"]]
        case["expected_topic"] = expected["topic"]
        case["expected_format"] = expected["format"]
        case["expected_intent"] = expected["intent"]
        case["topic_match"] = case["topic"] == expected["topic"]
        case["format_match"] = (
            None if expected["format"] is None else case["format"] == expected["format"]
        )
        case["intent_match"] = (
            None if expected["intent"] is None else case["intent"] == expected["intent"]
        )

    analyzed = [case for case in cases if case["assessments"]]
    by_batch = {
        batch: [case for case in analyzed if case["batch"] == batch]
        for batch in BATCHES
    }
    batch_distribution = {
        batch: {
            "cases": len(values),
            "assessments": sum(len(case["assessments"]) for case in values),
            "sufficiency": _distribution(values, "sufficiency", SUFFICIENCIES),
            "strength": _distribution(values, "strength", STRENGTHS),
            "direction": _distribution(values, "direction", DIRECTIONS),
        }
        for batch, values in by_batch.items()
    }

    false_sufficient: list[str] = []
    true_sufficient: list[str] = []
    safe_wrong: list[str] = []
    for case in analyzed:
        for item in case["assessments"]:
            expected = (
                case["expected_topic"] if item["candidate_group"] == "TOPIC_LIKE"
                else case["expected_format"] if item["candidate_group"] == "FORMAT_LIKE"
                else None
            )
            if expected is None:
                continue
            key = f"{case['batch']}:{case['id']}:{item['candidate']}"
            if item["candidate"] == expected and item["sufficiency"] == "SUFFICIENT":
                true_sufficient.append(key)
            elif item["candidate"] != expected and item["sufficiency"] == "SUFFICIENT":
                false_sufficient.append(key)
            elif item["candidate"] != expected:
                safe_wrong.append(key)

    batch_06 = {case["id"]: case for case in cases if case["batch"] == "batch_06"}
    topic_mismatch_ids = ("051", "053", "054", "055", "056", "060")
    format_mismatch_ids = ("052", "054", "056", "057", "058", "059")

    def mismatch_record(case_id: str, dimension: str) -> dict[str, Any]:
        case = batch_06[case_id]
        group = "TOPIC_LIKE" if dimension == "topic" else "FORMAT_LIKE"
        expected = case[f"expected_{dimension}"]
        predicted = case[dimension]
        relevant = [
            item for item in case["assessments"] if item["candidate_group"] == group
        ]
        return {
            "expected": expected,
            "predicted": predicted,
            "assessments": relevant,
            "expected_sufficiency": _state(relevant, expected, group),
            "predicted_sufficiency": _state(relevant, predicted, group),
            "warnings": list(dict.fromkeys(
                warning for item in relevant for warning in item["warnings"]
            )),
            "competition": {
                item["candidate"]: item["competing_candidates"] for item in relevant
                if item["competing_candidates"]
            },
            "required": case[f"{dimension}_required"],
        }

    topic_mismatches = {
        case_id: mismatch_record(case_id, "topic") for case_id in topic_mismatch_ids
    }
    format_mismatches = {
        case_id: mismatch_record(case_id, "format") for case_id in format_mismatch_ids
    }

    case_055_relevant = topic_mismatches["055"]["assessments"]
    wrong_055 = next(
        (item for item in case_055_relevant if item["candidate"] != "WORLD"), None
    )
    case_055 = {
        **topic_mismatches["055"],
        "wrong_semantic_candidate": wrong_055["candidate"] if wrong_055 else None,
        "wrong_candidate_sufficiency": wrong_055["sufficiency"] if wrong_055 else "NONE",
        "counterfactual_unresolved": not wrong_055 or wrong_055["sufficiency"] != "SUFFICIENT",
    }
    critical = {}
    for case_id in ("054", "056", "058", "059"):
        item = format_mismatches[case_id]
        predicted_state = item["predicted_sufficiency"]
        critical[case_id] = {
            **item,
            "counterfactual_unresolved": predicted_state != "SUFFICIENT",
        }

    divergence = []
    for case_id in topic_mismatch_ids:
        case = batch_06[case_id]
        item = topic_mismatches[case_id]
        if case["topic_confidence"] == "HIGH" and item["predicted_sufficiency"] in {
            "NONE", "PARTIAL", "INSUFFICIENT", "CONFLICTED",
        }:
            divergence.append(f"{case_id}:TOPIC")
    for case_id in format_mismatch_ids:
        case = batch_06[case_id]
        item = format_mismatches[case_id]
        if case["format_confidence"] == "HIGH" and item["predicted_sufficiency"] in {
            "NONE", "PARTIAL", "INSUFFICIENT", "CONFLICTED",
        }:
            divergence.append(f"{case_id}:FORMAT")

    duplicate_cases = sorted({
        f"{case['batch']}:{case['id']}" for case in analyzed
        if any("DUPLICATE_EVIDENCE_DISCOUNTED" in item["warnings"] for item in case["assessments"])
    })
    dominated = {
        role: sorted({
            f"{case['batch']}:{case['id']}:{item['candidate']}"
            for case in analyzed for item in case["assessments"]
            if f"{role}_DOMINATED" in item["warnings"]
        })
        for role in ("AUTHORITY", "ACTOR", "METHOD")
    }
    dominated_sufficient = {
        role: sorted({
            f"{case['batch']}:{case['id']}:{item['candidate']}"
            for case in analyzed for item in case["assessments"]
            if f"{role}_DOMINATED" in item["warnings"]
            and item["sufficiency"] == "SUFFICIENT"
        })
        for role in ("AUTHORITY", "ACTOR", "METHOD")
    }
    competing_cases = sorted({
        f"{case['batch']}:{case['id']}" for case in analyzed
        if any(item["competing_candidates"] for item in case["assessments"])
    })
    conflicted = sorted(
        f"{case['batch']}:{case['id']}:{item['candidate']}"
        for case in analyzed for item in case["assessments"]
        if item["sufficiency"] == "CONFLICTED"
    )
    competition_prevented = sorted(
        f"{case['batch']}:{case['id']}:{item['candidate']}"
        for case in analyzed for item in case["assessments"]
        if item["competing_candidates"] and item["sufficiency"] != "SUFFICIENT"
    )

    b6_false = [key for key in false_sufficient if key.startswith("batch_06:")]
    b6_true = [key for key in true_sufficient if key.startswith("batch_06:")]
    b6_safe = [key for key in safe_wrong if key.startswith("batch_06:")]
    mismatch_records = list(topic_mismatches.values()) + list(format_mismatches.values())
    expected_states = [item["expected_sufficiency"] for item in mismatch_records]
    historical = [case for case in analyzed if case["batch"] != "batch_06"]
    historical_assessments = [item for case in historical for item in case["assessments"]]
    historical_safety = {
        "cases": len(historical),
        "assessments": len(historical_assessments),
        "conflicted_count": sum(item["sufficiency"] == "CONFLICTED" for item in historical_assessments),
        "insufficient_count": sum(item["sufficiency"] == "INSUFFICIENT" for item in historical_assessments),
        "false_sufficient_count": sum(not key.startswith("batch_06:") for key in false_sufficient),
        "dominated_sufficient_count": sum(len(values) for values in dominated_sufficient.values()),
    }
    critical_wrong_states = [
        critical[key]["predicted_sufficiency"] for key in ("054", "056", "058")
    ]
    if (
        not b6_false and case_055["wrong_candidate_sufficiency"] != "SUFFICIENT"
        and all(state != "SUFFICIENT" for state in critical_wrong_states)
        and not any(dominated_sufficient.values())
        and historical_safety["false_sufficient_count"] == 0
    ):
        quality = "EXCELLENT"
    elif (
        case_055["wrong_candidate_sufficiency"] != "SUFFICIENT"
        and all(state != "SUFFICIENT" for state in critical_wrong_states)
    ):
        quality = "STRONG" if len(b6_false) <= 1 else "MIXED"
    else:
        quality = "WEAK"
    recommendation = (
        "READY_FOR_TOPIC_FORMAT_SHADOW_CONSUMPTION"
        if quality == "EXCELLENT"
        else "REFINE_FORMAT_DIRECTIONAL_ASSESSMENT"
        if any(state == "SUFFICIENT" for state in critical_wrong_states)
        else "REFINE_ASSESSOR_STRENGTH_LOGIC"
    )
    return {
        "batch_06_scientific_status": "DIAGNOSTIC_DEVELOPMENT_SET",
        "cases_analyzed": len(analyzed),
        "case_inventory": analyzed,
        "batch_distribution": batch_distribution,
        "direction_distribution": _distribution(analyzed, "direction", DIRECTIONS),
        "strength_distribution": _distribution(analyzed, "strength", STRENGTHS),
        "sufficiency_distribution": _distribution(analyzed, "sufficiency", SUFFICIENCIES),
        "batch_06_topic_mismatch_assessments": topic_mismatches,
        "batch_06_format_mismatch_assessments": format_mismatches,
        "case_055_safety": case_055,
        "critical_format_case_safety": critical,
        "confidence_sufficiency_divergence": divergence,
        "counterfactual_topic_unresolved": {
            key: all(
                item["sufficiency"] != "SUFFICIENT"
                for item in value["assessments"] if item["candidate"] != value["expected"]
            ) for key, value in topic_mismatches.items()
        },
        "counterfactual_format_unresolved": {
            key: value["counterfactual_unresolved"] for key, value in critical.items()
        },
        "duplicate_evidence_findings": duplicate_cases,
        "authority_actor_method_findings": {
            "dominated": dominated, "dominated_sufficient": dominated_sufficient,
        },
        "competition_findings": {
            "cases_with_competing_candidates": competing_cases,
            "conflicted_assessments": conflicted,
            "competition_prevented_sufficient": competition_prevented,
        },
        "sufficiency_quality_metrics": {
            "true_sufficient_count": len(b6_true),
            "false_sufficient_count": len(b6_false),
            "safe_wrong_partial_count": len(b6_safe),
            "expected_candidate_sufficient_count": expected_states.count("SUFFICIENT"),
            "expected_candidate_partial_count": expected_states.count("PARTIAL"),
            "expected_candidate_missing_count": expected_states.count("NONE"),
            "false_sufficiency_rate": len(b6_false) / (len(b6_true) + len(b6_false)) * 100.0 if b6_true or b6_false else 0.0,
        },
        "historical_corpus_safety": historical_safety,
        "diagnostic_quality": quality,
        "recommended_next_step": recommendation,
        "provider_calls": 0,
    }


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    quality = result["sufficiency_quality_metrics"]
    return f"""# Semantic Candidate Assessment Shadow Diagnostic

Batch 06 status: {result['batch_06_scientific_status']}

Cases analyzed: {result['cases_analyzed']}

Diagnostic quality: {result['diagnostic_quality']}

Sufficiency distribution: {json.dumps(result['sufficiency_distribution'])}

Batch 06 true sufficient: {quality['true_sufficient_count']}

Batch 06 false sufficient: {quality['false_sufficient_count']}

Recommended next step: {result['recommended_next_step']}

Provider calls: 0
"""


def main() -> int:
    result = analyze()
    OUTPUT_JSON.write_text(render_json(result), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "case_inventory"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
