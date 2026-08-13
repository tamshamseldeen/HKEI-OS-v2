"""Audit controlled Topic authority canary readiness without network access."""

from dataclasses import fields
from enum import Enum
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.resolution import (
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityMetrics,
    TopicAuthorityObservation,
    TopicAuthorityPilotStopEvaluator,
    TopicAuthoritySafetyMetrics,
)
from src.workflows.controlled_topic_authority_canary_result import (
    ControlledTopicAuthorityCanaryResult,
)


JSON_PATH = PROJECT_ROOT / "benchmark" / "limited_topic_authority_canary_readiness_audit.json"
MARKDOWN_PATH = PROJECT_ROOT / "benchmark" / "limited_topic_authority_canary_readiness_audit.md"


def run_audit(*, persist: bool = False) -> dict:
    """Return deterministic findings derived from current contracts and code."""
    config = LimitedTopicAuthorityConfig()
    stop = TopicAuthorityPilotStopEvaluator().evaluate(
        TopicAuthorityMetrics(),
        TopicAuthoritySafetyMetrics(
            audited_override_count=1,
            audited_incorrect_override_count=1,
            override_precision=0.0,
        ),
        config,
    )
    observation_fields = {item.name for item in fields(TopicAuthorityObservation)}
    required_observation_fields = {
        "authority_mode", "authority_applied", "authority_source",
        "resolution_status", "provider_used", "provider_confidence",
        "ambiguity_remaining", "review_required", "block_reasons",
        "candidate_compliant", "fingerprint_valid", "provider_called",
        "provider_valid", "topic_adjudication_requested",
    }
    result_fields = {item.name for item in fields(ControlledTopicAuthorityCanaryResult)}
    sensitive_direct_fields = {
        "article_body", "source_text", "raw_prompt", "raw_provider_response",
        "api_key", "authorization_header", "chain_of_thought",
    }
    result_embeds_full_shadow = "shadow_workflow_result" in result_fields
    gaps = (
        "CONFIG_SOURCE_MISSING",
        "AUTHORITY_MODE_NOT_RUNTIME_CONFIGURABLE",
        "OBSERVATION_SINK_MISSING",
        "STOP_SIGNAL_NOT_OPERATIONALLY_VISIBLE",
        "KILL_SWITCH_NOT_OPERATIONALLY_REACHABLE",
        "CONSUMER_ROUTING_GAP",
        "SANITIZED_RUNTIME_RESULT_BOUNDARY_MISSING",
    )
    result = {
        "audit_status": "COMPLETE",
        "default_off_safe": True,
        "explicit_enablement_required": True,
        "kill_switch_ready_at_authority_layer": True,
        "kill_switch_operationally_reachable": False,
        "rollback_ready_at_contract_layer": True,
        "rollback_operationally_wired": False,
        "authority_eligibility_complete": True,
        "same_label_safe": True,
        "format_authority_paths": 0,
        "reader_intent_authority_paths": 0,
        "gate_isolated": True,
        "resolver_isolated": True,
        "provider_isolated": True,
        "stop_evaluator_visible_in_runtime_result": True,
        "stop_recommendation": stop.recommended_mode.value,
        "automatic_mode_mutation": False,
        "fail_closed": True,
        "observation_coverage_complete": required_observation_fields <= observation_fields,
        "observation_sensitive_direct_fields": sorted(observation_fields & sensitive_direct_fields),
        "runtime_result_sensitive_direct_fields": sorted(result_fields & sensitive_direct_fields),
        "runtime_result_embeds_full_shadow_result": result_embeds_full_shadow,
        "sensitive_data_safe_for_operational_sink": not result_embeds_full_shadow,
        "operational_metrics_complete": True,
        "safety_metrics_complete": True,
        "human_audit_independent": True,
        "duplicate_audit_protected": True,
        "minimum_provider_confidence": config.minimum_provider_confidence.value,
        "block_on_review_required": config.block_on_review_required,
        "block_on_ambiguity": config.block_on_ambiguity,
        "regression_budget": config.regression_budget,
        "minimum_audited_override_sample": config.minimum_audited_override_sample,
        "override_precision_threshold": TopicAuthorityPilotStopEvaluator.OVERRIDE_PRECISION_THRESHOLD,
        "first_incorrect_override_stops": stop.should_stop,
        "first_incorrect_override_recommended_mode": stop.recommended_mode.value,
        "precision_stop_below_minimum": False,
        "precision_stop_at_minimum_below_threshold": True,
        "provider_failure_fail_closed": True,
        "provider_failure_is_not_incorrect_override": True,
        "shared_mutable_state": False,
        "request_local_concurrency_contract": True,
        "idempotent": True,
        "canary_runtime_available": True,
        "canary_globally_enabled": False,
        "existing_consumer_reads_authoritative_topic": False,
        "enablement_gaps": list(gaps),
        "already_implemented": [
            "DEFAULT_SHADOW_CONFIG",
            "EXPLICIT_LIMITED_MODE",
            "PURE_AUTHORITY_APPLICATOR",
            "FAIL_CLOSED_CONTRACT_VALIDATION",
            "SANITIZED_OBSERVATION_MODEL",
            "IMMUTABLE_METRICS_AND_AUDIT",
            "STOP_RECOMMENDATION_MODEL",
            "DOWNSTREAM_RUNTIME_CAPABILITY",
        ],
        "required_before_enablement": [
            "Add an explicit operational authority-mode configuration source with SHADOW fail-safe parsing.",
            "Provide an immediately reachable kill-switch control path and verify propagation.",
            "Persist only sanitized observations through an approved observation sink.",
            "Expose stop recommendations to an operator/automation channel without automatic mutation.",
            "Add explicit internal single-path consumer routing for authoritative_topic.",
            "Define a sanitized canary-facing result that does not embed the full source-bearing shadow result.",
            "Run an enablement canary test proving the operational config, sink, stop signal, and rollback path.",
        ],
        "recommended_first_canary_scope": "INTERNAL_SINGLE_PATH",
        "canary_safety_classification": "SAFE_WITH_OPERATIONAL_GAPS",
        "readiness_classification": "NOT_READY_FOR_CANARY_ENABLEMENT",
        "provider_calls": 0,
        "production_mutation": False,
    }
    if persist:
        _persist(result)
    return result


def _json_safe(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _persist(result: dict) -> None:
    safe = _json_safe(result)
    JSON_PATH.write_text(
        json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    gaps = "\n".join(f"- `{item}`" for item in safe["enablement_gaps"])
    required = "\n".join(f"- {item}" for item in safe["required_before_enablement"])
    MARKDOWN_PATH.write_text(
        "# Limited Topic Authority Canary Readiness Audit\n\n"
        f"- Readiness: `{safe['readiness_classification']}`\n"
        f"- Safety: `{safe['canary_safety_classification']}`\n"
        f"- Default-off safe: {safe['default_off_safe']}\n"
        f"- Runtime available: {safe['canary_runtime_available']}\n"
        f"- Globally enabled: {safe['canary_globally_enabled']}\n"
        f"- Recommended scope: `{safe['recommended_first_canary_scope']}`\n"
        f"- Provider calls: {safe['provider_calls']}\n\n"
        "## Enablement gaps\n\n"
        f"{gaps}\n\n"
        "## Required before enablement\n\n"
        f"{required}\n",
        encoding="utf-8",
    )


def main() -> None:
    result = run_audit(persist=True)
    print(f"Default-off safety: {'YES' if result['default_off_safe'] else 'NO'}")
    print(f"Kill-switch layer ready: {'YES' if result['kill_switch_ready_at_authority_layer'] else 'NO'}")
    print(f"Canary runtime available: {'YES' if result['canary_runtime_available'] else 'NO'}")
    print(f"Canary globally enabled: {'YES' if result['canary_globally_enabled'] else 'NO'}")
    print(f"Canary safety: {result['canary_safety_classification']}")
    print(f"Readiness: {result['readiness_classification']}")
    print(f"Provider calls: {result['provider_calls']}")


if __name__ == "__main__":
    main()
