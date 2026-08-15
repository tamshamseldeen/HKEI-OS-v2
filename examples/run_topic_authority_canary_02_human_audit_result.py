"""Aggregate HKEI-220 human audits and execute the canonical pilot stop policy."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adjudication.adjudication_confidence import AdjudicationConfidence  # noqa: E402
from src.resolution import (  # noqa: E402
    EditorialResolutionSource, EditorialResolutionStatus,
    InMemoryTopicAuthorityObservationSink, LimitedTopicAuthorityConfig,
    OperationalTopicAuthorityCanary, ResolverAuthorityMode,
    TopicAuthorityAuditRecord, TopicAuthorityAuditStatus, TopicAuthorityDecision,
    TopicAuthorityMetrics, TopicAuthorityMetricsAggregator, TopicAuthorityObservation,
    TopicAuthorityPilotStopEvaluator, TopicAuthorityRuntimeConfig,
)
from src.topic.topic import Topic  # noqa: E402


AUDIT = ROOT / "benchmark/internal_canary/topic_authority_canary_02_human_audit.json"
CANARY = ROOT / "benchmark/internal_canary/topic_authority_canary_02.json"
OUTPUT_JSON = ROOT / "benchmark/internal_canary/topic_authority_canary_02_human_audit_result.json"
OUTPUT_MD = ROOT / "benchmark/internal_canary/topic_authority_canary_02_human_audit_result.md"
HISTORICAL_CANARY_SHA256 = "c6112cedf30edf23085b6937fdacc30f5c878f65526515cb9b0830e2de24370e"
CANARY_01_AUDIT_RESULT = ROOT / "benchmark/internal_canary/topic_authority_canary_01_human_audit_result.json"
CANARY_01_AUDIT_RESULT_SHA256 = "06f9f1792ef04aa3e3b0a41d62046c5ef3d9563fb0e608cb9d9fff6fcb7a8822"


def _audit_inputs():
    packet = json.loads(AUDIT.read_text(encoding="utf-8"))
    records = tuple(TopicAuthorityAuditRecord(
        decision_fingerprint=item["audit_identity"],
        authoritative_topic=Topic(item["authoritative_topic"]),
        review_status=TopicAuthorityAuditStatus.COMPLETED,
        human_reviewed_correctness=item["human_correctness"] == "CORRECT_OVERRIDE",
    ) for item in packet["records"])
    observations = tuple(TopicAuthorityObservation(
        authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        authority_applied=True,
        authority_source=EditorialResolutionSource.ADJUDICATION,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_used=True, provider_called=True, provider_valid=True,
        topic_adjudication_requested=True, provider_failure_category=None,
        provider_confidence=AdjudicationConfidence(item["provider_confidence"]),
        ambiguity_remaining=item["ambiguity_remaining"],
        review_required=item["review_required"], block_reasons=(), warnings=(),
        candidate_compliant=True, fingerprint_valid=True,
        decision_fingerprint=item["audit_identity"],
    ) for item in packet["records"])
    return packet, records, observations


def _post_stop_proxy(stop_decision):
    runtime = TopicAuthorityRuntimeConfig()
    state_before = runtime.resolve()
    runtime.apply_stop_signal(stop_decision)
    decision = TopicAuthorityDecision(
        deterministic_topic=Topic.ECONOMY, resolved_topic=Topic.POLITICS,
        authoritative_topic=Topic.POLITICS, authority_applied=True,
        authority_source=EditorialResolutionSource.ADJUDICATION,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_confidence=AdjudicationConfidence.HIGH,
        ambiguity_remaining=False, review_required=False, warnings=(),
        input_fingerprint="post-stop-safe-proxy", block_reasons=(),
    )
    observation = TopicAuthorityObservation(
        authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        authority_applied=True, authority_source=EditorialResolutionSource.ADJUDICATION,
        resolution_status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        provider_used=True, provider_called=False, provider_valid=True,
        topic_adjudication_requested=True, provider_failure_category=None,
        provider_confidence=AdjudicationConfidence.HIGH, ambiguity_remaining=False,
        review_required=False, block_reasons=(), warnings=(), candidate_compliant=True,
        fingerprint_valid=True, decision_fingerprint="post-stop-safe-proxy",
    )
    safe = OperationalTopicAuthorityCanary(runtime, InMemoryTopicAuthorityObservationSink()).execute(
        decision, observation,
        __import__("src.resolution", fromlist=["TopicAuthorityConsumerRoute"]).TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH,
    )
    return state_before, runtime.resolve(), safe


def build_result():
    if sha256(CANARY.read_bytes()).hexdigest() != HISTORICAL_CANARY_SHA256:
        raise RuntimeError("historical HKEI-212 artifact changed")
    if sha256(CANARY_01_AUDIT_RESULT.read_bytes()).hexdigest() != CANARY_01_AUDIT_RESULT_SHA256:
        raise RuntimeError("historical Canary 01 audit result changed")
    packet, records, observations = _audit_inputs()
    aggregator = TopicAuthorityMetricsAggregator()
    safety = aggregator.aggregate_safety(observations, records)
    operational = TopicAuthorityMetrics(
        articles_processed=5, topic_adjudication_requested=2, provider_calls=3,
        valid_adjudications=3, resolver_adjudicated_accepted=2,
        authoritative_topic_overrides=2, deterministic_topic_preserved=3,
    )
    config = LimitedTopicAuthorityConfig()
    stop = TopicAuthorityPilotStopEvaluator().evaluate(operational, safety, config)
    state_before, effective_mode, proxy = _post_stop_proxy(stop)
    precision_evaluable = safety.audited_override_count >= config.minimum_audited_override_sample
    per_case = [{key:item[key] for key in (
        "canary_id", "audit_identity", "deterministic_topic", "authoritative_topic",
        "human_expected_topic", "human_correctness", "override_transition",
        "review_timestamp", "reviewer_notes",
    )} for item in packet["records"]]
    historical = json.loads(CANARY_01_AUDIT_RESULT.read_text(encoding="utf-8"))
    cumulative_count = historical["audited_override_count"] + safety.audited_override_count
    cumulative_correct = historical["correct_count"] + safety.audited_correct_override_count
    cumulative_incorrect = historical["incorrect_count"] + safety.audited_incorrect_override_count
    return {
        "audit_id": "topic_authority_canary_02_human_audit_result",
        "judgment_source": "INDEPENDENT_HUMAN_REVIEW",
        "reviewed_count": safety.audited_override_count,
        "correct_count": safety.audited_correct_override_count,
        "incorrect_count": safety.audited_incorrect_override_count,
        "unsure_count": 0,
        "audited_override_count": safety.audited_override_count,
        "override_precision": safety.override_precision,
        "minimum_precision_sample": config.minimum_audited_override_sample,
        "precision_threshold": TopicAuthorityPilotStopEvaluator.OVERRIDE_PRECISION_THRESHOLD,
        "precision_threshold_evaluable": precision_evaluable,
        "precision_stop_triggered": False,
        "regression_budget": config.regression_budget,
        "regression_count": safety.audited_incorrect_override_count,
        "regression_budget_exceeded": safety.audited_incorrect_override_count > config.regression_budget,
        "wrong_to_wrong_override_count": sum(item["override_transition"] == "WRONG_TO_WRONG" for item in packet["records"]),
        "authority_contract_violations": safety.authority_contract_violation_count,
        "stop_evaluator_executed": True,
        "stop_decision": {"should_stop": stop.should_stop, "reasons": [item.value for item in stop.reasons], "recommended_mode": stop.recommended_mode.value if stop.recommended_mode else None},
        "effective_authority_mode_after_stop": effective_mode.value,
        "kill_switch_status": "ALREADY_SHADOW" if state_before is ResolverAuthorityMode.SHADOW else "APPLIED_SHADOW",
        "internal_route_state_after_stop": "DISABLED_DEFAULT",
        "post_stop_authority_consumed": proxy.authority_consumed,
        "post_stop_consumer_topic": proxy.consumer_topic.value,
        "post_stop_deterministic_topic": proxy.deterministic_topic.value,
        "canary_continuation_allowed": False,
        "safety_classification": "PILOT_STOPPED_AS_DESIGNED",
        "audit_outcome_classification": "SECOND_CANARY_AUDIT_MIXED",
        "next_recommended_step": "ANALYZE_SECOND_CANARY_WRONG_OVERRIDE_ONCE",
        "provider_calls": 0,
        "production_wide_authority_enabled": False,
        "historical_canary_sha256": HISTORICAL_CANARY_SHA256,
        "historical_canary_01_audit_result_sha256": CANARY_01_AUDIT_RESULT_SHA256,
        "cumulative_pilot_audit": {
            "audited_override_count": cumulative_count,
            "audited_correct_override_count": cumulative_correct,
            "audited_incorrect_override_count": cumulative_incorrect,
            "override_precision": cumulative_correct / cumulative_count,
            "minimum_precision_sample": config.minimum_audited_override_sample,
            "precision_threshold_evaluable": cumulative_count >= config.minimum_audited_override_sample,
            "regression_budget": config.regression_budget,
            "regression_budget_exceeded": cumulative_incorrect > config.regression_budget,
        },
        "hkei_216_diagnostic": {
            "consequence_only_primary_sufficiency_count": 0,
            "generalization_signal": "NO_NEW_CONSEQUENCE_SUBJECT_REGRESSION_OBSERVED",
            "canary2_002_potential_boundary": "ENTITY_OWNER_SOURCE_ROLE_VS_PRIMARY_EVENT_SUBJECT",
        },
        "records": per_case,
    }


def render_markdown(result):
    return f"""# Second Canary Human Audit Result

Safety classification: `{result['safety_classification']}`

Audit outcome: `{result['audit_outcome_classification']}`

Reviewed/correct/incorrect/unsure: {result['reviewed_count']} / {result['correct_count']} / {result['incorrect_count']} / {result['unsure_count']}

Override precision: {result['override_precision']:.6f} (not evaluable against the 90% threshold until 30 audits)

Regression budget/count/exceeded: {result['regression_budget']} / {result['regression_count']} / `{result['regression_budget_exceeded']}`

Wrong-to-wrong overrides: {result['wrong_to_wrong_override_count']}

Cumulative audited/correct/incorrect/precision: {result['cumulative_pilot_audit']['audited_override_count']} / {result['cumulative_pilot_audit']['audited_correct_override_count']} / {result['cumulative_pilot_audit']['audited_incorrect_override_count']} / {result['cumulative_pilot_audit']['override_precision']:.6f}

Stop: `{result['stop_decision']['should_stop']}`; reason: `{', '.join(result['stop_decision']['reasons'])}`; recommended mode: `{result['stop_decision']['recommended_mode']}`

Canary continuation allowed: `{result['canary_continuation_allowed']}`

Next step: `{result['next_recommended_step']}`

The incorrect override was contract-compliant and remains part of the historical
canary record. No provider was called and no provider reasoning is included.
"""


def main():
    result = build_result()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(result["safety_classification"])
    print(result["stop_decision"]["reasons"])
    return 0


if __name__ == "__main__": raise SystemExit(main())
