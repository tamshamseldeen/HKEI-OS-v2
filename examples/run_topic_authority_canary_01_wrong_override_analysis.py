"""Analyze CANARY-003's historical wrong Topic override without provider access."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.run_topic_authority_canary_01 import _parse_cases  # noqa: E402
from src.adjudication.deterministic_semantic_adjudication_gate import (  # noqa: E402
    DeterministicSemanticAdjudicationGate,
)
from src.adjudication.semantic_adjudication_request_builder import (  # noqa: E402
    SemanticAdjudicationRequestBuilder,
)
from src.workflows.experimental_semantic_adjudication_shadow_workflow import (  # noqa: E402
    ExperimentalSemanticAdjudicationShadowWorkflow,
)
from src.workflows.experimental_semantic_editorial_analysis_workflow import (  # noqa: E402
    ExperimentalSemanticEditorialAnalysisWorkflow,
)


CANARY_JSON = ROOT / "benchmark/internal_canary/topic_authority_canary_01.json"
AUDIT_JSON = ROOT / "benchmark/internal_canary/topic_authority_canary_01_human_audit.json"
AUDIT_RESULT_JSON = ROOT / "benchmark/internal_canary/topic_authority_canary_01_human_audit_result.json"
OUTPUT_JSON = ROOT / "benchmark/internal_canary/topic_authority_canary_01_wrong_override_analysis.json"
OUTPUT_MD = ROOT / "benchmark/internal_canary/topic_authority_canary_01_wrong_override_analysis.md"
CASE_ID = "CANARY-003"


def _case(items: list[dict], case_id: str) -> dict:
    return next(item for item in items if item["canary_id"] == case_id)


def _reconstruct_structured_metadata() -> dict:
    """Rebuild local metadata and prove identity against the persisted request."""
    fields = next(fields for case_id, fields in _parse_cases() if case_id == CASE_ID)
    editorial = ExperimentalSemanticEditorialAnalysisWorkflow().process(**fields)
    gate = DeterministicSemanticAdjudicationGate().evaluate(
        topic_classification=editorial.topic_classification,
        format_classification=editorial.format_classification,
        contextual_evidence=editorial.contextual_evidence,
        semantic_evidence=editorial.semantic_evidence,
    )
    source = editorial.classification_result.ingestion.source
    request = SemanticAdjudicationRequestBuilder().build(
        request_id=ExperimentalSemanticAdjudicationShadowWorkflow._request_id(source),
        source=source,
        content_classification=editorial.classification_result.classification,
        topic_classification=editorial.topic_classification,
        format_classification=editorial.format_classification,
        contextual_evidence=editorial.contextual_evidence,
        semantic_evidence=editorial.semantic_evidence,
        decision=gate,
    )
    return {
        "deterministic_topic": editorial.topic_classification.topic.value,
        "deterministic_confidence": editorial.topic_classification.confidence.value,
        "topic_reason_codes": list(editorial.topic_classification.reason_codes),
        "topic_supporting_signals": list(editorial.topic_classification.supporting_signals),
        "topic_warnings": list(editorial.topic_classification.warnings),
        "contextual_roles": [item.role.value for item in editorial.contextual_evidence.all_items],
        "contextual_supports": list(request.contextual_support_labels),
        "semantic_relationships": list(request.semantic_relationship_summary),
        "primary_domain_candidates": list(request.primary_domain_candidates),
        "secondary_domain_candidates": list(request.secondary_domain_candidates),
        "gate_scope": gate.scope.value,
        "gate_triggers": list(gate.trigger_signals),
        "candidate_topics": list(request.candidate_topics),
        "input_fingerprint": request.input_fingerprint,
    }


def build_analysis() -> dict:
    historical = json.loads(CANARY_JSON.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    audit_result = json.loads(AUDIT_RESULT_JSON.read_text(encoding="utf-8"))
    historical_case = _case(historical["cases"], CASE_ID)
    human_case = _case(audit["records"], CASE_ID)
    metadata = _reconstruct_structured_metadata()

    if metadata["input_fingerprint"] != historical_case["input_fingerprint"]:
        raise RuntimeError("CANARY-003 reconstruction does not match historical input")
    if human_case["human_expected_topic"] != "CRIME":
        raise RuntimeError("frozen human judgment changed")
    if not audit_result["regression_budget_exceeded"]:
        raise RuntimeError("pilot stop state changed")

    return {
        "analysis_id": "topic_authority_canary_01_wrong_override_analysis",
        "analysis_type": "ONE_TIME_OFFLINE_DIAGNOSTIC",
        "case_analyzed": CASE_ID,
        "provider_calls": 0,
        "source_or_prediction_mutation": False,
        "human_expected_topic": human_case["human_expected_topic"],
        "human_correctness": human_case["human_correctness"],
        "deterministic_topic": historical_case["deterministic_topic"],
        "authoritative_topic": historical_case["authoritative_topic"],
        "deterministic_confidence": metadata["deterministic_confidence"],
        "deterministic_evidence": {
            "reason_codes": metadata["topic_reason_codes"],
            "supporting_signals": metadata["topic_supporting_signals"],
            "warnings": metadata["topic_warnings"],
            "central_enforcement_event_recognized": True,
            "health_evidence_explicitly_represented": False,
        },
        "candidate_universe": metadata["candidate_topics"],
        "candidate_universe_assessment": [
            "EXPECTED_CANDIDATE_PRESENT",
            "CANDIDATE_UNIVERSE_OVERBROAD",
        ],
        "expected_candidate_present": "CRIME" in metadata["candidate_topics"],
        "stronger_structured_candidate_present": False,
        "semantic_evidence": {
            "contextual_roles": metadata["contextual_roles"],
            "contextual_supports": metadata["contextual_supports"],
            "relationships": metadata["semantic_relationships"],
            "primary_domain_candidates": metadata["primary_domain_candidates"],
            "secondary_domain_candidates": metadata["secondary_domain_candidates"],
            "subject_consequence_distinction": "NOT_REPRESENTED",
        },
        "gate": {
            "scope": metadata["gate_scope"],
            "triggers": metadata["gate_triggers"],
            "assessment": "GATE_APPROPRIATE",
        },
        "prompt_input_audit": {
            "fingerprint_matches_historical_request": True,
            "central_event_role_emphasized": False,
            "authority_enforcement_emphasized": False,
            "food_safety_consequence_emphasized": False,
            "candidate_definitions_present": True,
            "raw_prompt_inspected_or_persisted": False,
        },
        "subject_role_assessment": [
            "SUBJECT_ROLE_MISASSIGNED",
            "CONSEQUENCE_PROMOTED_TO_SUBJECT",
            "AUTHORITY_ACTION_UNDERWEIGHTED",
        ],
        "label_semantics_assessment": "LABEL_SEMANTICS_OVERLAP",
        "consequence_subject_protection": "PROTECTION_MISSING",
        "provider": {
            "adjudicated_topic": historical_case["resolved_topic"],
            "confidence": historical_case["provider_confidence"],
            "ambiguity_remaining": historical_case["ambiguity_remaining"],
            "candidate_compliant": historical_case["candidate_compliant"],
            "response_valid": historical_case["response_valid"],
        },
        "confidence_policy_assessment": "CONFIDENCE_POLICY_CONTRIBUTING",
        "resolver_assessment": "RESOLVER_BEHAVIOR_CORRECT_BY_CONTRACT",
        "applicator_assessment": "APPLICATOR_CORRECT_BY_CONTRACT",
        "authority_eligibility": {
            "resolution_status": human_case["resolution_status"],
            "source": historical_case["authority_source"],
            "response_valid": historical_case["response_valid"],
            "candidate_compliant": historical_case["candidate_compliant"],
            "fingerprint_valid": historical_case["fingerprint_valid"],
            "provider_available": historical_case["provider_status"] == "SUCCESS",
            "review_required": historical_case["review_required"],
            "ambiguity_remaining": historical_case["ambiguity_remaining"],
            "topic_changed": historical_case["deterministic_topic"] != historical_case["resolved_topic"],
            "observation_succeeded": not historical_case["warnings"],
        },
        "earliest_failure_stage": "TOPIC_ROLE_ASSIGNMENT",
        "primary_failure_class": "CONSEQUENCE_PROMOTED_TO_SUBJECT",
        "secondary_failure_classes": [
            "CENTRAL_EVENT_UNDERWEIGHTED",
            "STRUCTURED_EVIDENCE_INCOMPLETE",
            "PROVIDER_OVERRULED_CORRECT_BASELINE",
            "FALSE_CONFIDENCE",
            "AMBIGUITY_FALSE_NEGATIVE",
            "CRIME_HEALTH_BOUNDARY_UNDERSPECIFIED",
            "CANDIDATE_SET_TOO_BROAD",
        ],
        "safest_generic_counterfactual": "A. consequence-vs-subject semantic protection",
        "counterfactual_rationale": (
            "Represent consequence separately from the primary subject and require central-event "
            "evidence before promoting a consequence domain. This preserves HEALTH when the hazard, "
            "disease, or public-health response is itself central."
        ),
        "overcorrection_risk": "LOW",
        "historical_similar_cases": {"count": 0, "case_ids": []},
        "pilot_implication": "ONE_GENERIC_SEMANTIC_FIX_REQUIRED_BEFORE_NEW_CANARY",
        "pilot_stopped": True,
        "new_holdout_required_after_any_fix": True,
        "source_specific_fix_proposed": False,
    }


def render_markdown(analysis: dict) -> str:
    return f"""# CANARY-003 Wrong Topic Override Analysis

This one-time offline diagnostic preserves the frozen historical result:
deterministic `{analysis['deterministic_topic']}`, authoritative
`{analysis['authoritative_topic']}`, and human expected
`{analysis['human_expected_topic']}`.

The earliest failure stage is `{analysis['earliest_failure_stage']}`. CRIME was
detected but remained LOW confidence; the fingerprint-matched structured request
contained no semantic relationships or domain candidates. The Gate appropriately
requested Topic adjudication, but the all-label candidate universe and missing
subject-versus-consequence representation allowed food-safety context to become
HEALTH/HIGH with ambiguity false.

Resolver and authority applicator behavior were correct by contract. This was an
editorial semantic regression, not an authority-contract violation.

Safest generic counterfactual: `{analysis['safest_generic_counterfactual']}`.
Overcorrection risk: `{analysis['overcorrection_risk']}`. The protection must
preserve HEALTH where disease, food poisoning, unsafe products, or a public-health
hazard is the central subject rather than a consequence of another central event.

Pilot implication: `{analysis['pilot_implication']}`. The pilot remains stopped;
any future generic change requires generic fixtures and a new internal canary.
No provider call, source-specific tuning, or production mutation occurred.
"""


def run_analysis(*, output_json: Path = OUTPUT_JSON, output_md: Path = OUTPUT_MD) -> dict:
    analysis = build_analysis()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(analysis), encoding="utf-8")
    return analysis


def main() -> int:
    analysis = run_analysis()
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
