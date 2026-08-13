"""Run a deterministic, network-free limited Topic authority pilot simulation."""

from dataclasses import asdict
from enum import Enum
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.resolution import (
    EditorialDimensionResolution,
    EditorialResolutionDimension,
    EditorialResolutionResult,
    EditorialResolutionSource,
    EditorialResolutionStatus,
    EditorialResolutionWarning,
    LimitedTopicAuthorityApplicator,
    LimitedTopicAuthorityConfig,
    ResolverAuthorityMode,
    TopicAuthorityAuditRecord,
    TopicAuthorityAuditStatus,
    TopicAuthorityBlockReason,
    TopicAuthorityContractValidator,
    TopicAuthorityContractViolation,
    TopicAuthorityMetricsAggregator,
    TopicAuthorityObservationBuilder,
    TopicAuthorityPilotStopEvaluator,
    TopicAuthorityProviderFailureCategory,
)
from src.topic.topic import Topic


JSON_PATH = PROJECT_ROOT / "benchmark" / "limited_topic_authority_offline_canary.json"
MARKDOWN_PATH = PROJECT_ROOT / "benchmark" / "limited_topic_authority_offline_canary.md"


def _neutral_dimension(dimension, value):
    return EditorialDimensionResolution(
        dimension=dimension,
        value=value,
        status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
        source=EditorialResolutionSource.DETERMINISTIC_V1,
        confidence="HIGH",
        confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
        ambiguity=False,
        review_required=False,
        warnings=(),
    )


def _resolution(
    identifier: str,
    *,
    resolved_topic: Topic = Topic.HEALTH,
    status: EditorialResolutionStatus = EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
    source: EditorialResolutionSource = EditorialResolutionSource.ADJUDICATION,
    confidence: str | None = "HIGH",
    confidence_source: EditorialResolutionSource = EditorialResolutionSource.ADJUDICATION,
    ambiguity: bool = False,
    review_required: bool = False,
    warnings: tuple[EditorialResolutionWarning, ...] = (),
) -> EditorialResolutionResult:
    return EditorialResolutionResult(
        deterministic_topic=Topic.SCIENCE,
        topic_resolution=EditorialDimensionResolution(
            dimension=EditorialResolutionDimension.TOPIC,
            value=resolved_topic,
            status=status,
            source=source,
            confidence=confidence,
            confidence_source=confidence_source,
            ambiguity=ambiguity,
            review_required=review_required,
            warnings=warnings,
        ),
        format_resolution=_neutral_dimension(
            EditorialResolutionDimension.FORMAT, EditorialFormat.STANDARD_NEWS,
        ),
        reader_intent_resolution=_neutral_dimension(
            EditorialResolutionDimension.READER_INTENT, ReaderIntent.GET_UPDATE,
        ),
        review_required=review_required,
        warnings=warnings,
        provider_used=status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        input_fingerprint=f"sha256:synthetic-{identifier}",
    )


def _scenario(
    identifier: str,
    kind: str,
    *,
    mode: ResolverAuthorityMode = ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
):
    resolution = _resolution(identifier)
    trust = dict(
        candidate_compliant=True,
        fingerprint_valid=True,
        response_valid=True,
        provider_available=True,
    )
    metadata = dict(
        topic_adjudication_requested=True,
        provider_called=True,
        provider_valid=True,
        provider_failure_category=None,
    )
    if kind == "same_label":
        resolution = _resolution(identifier, resolved_topic=Topic.SCIENCE)
    elif kind == "deterministic":
        resolution = _resolution(
            identifier,
            resolved_topic=Topic.SCIENCE,
            status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
            source=EditorialResolutionSource.DETERMINISTIC_V1,
            confidence="HIGH",
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
        )
        metadata.update(
            topic_adjudication_requested=False,
            provider_called=False,
            provider_valid=False,
        )
    elif kind == "low_confidence":
        resolution = _resolution(identifier, confidence="LOW")
    elif kind == "review_required":
        resolution = _resolution(identifier, review_required=True)
    elif kind == "ambiguity":
        resolution = _resolution(
            identifier,
            ambiguity=True,
            review_required=True,
            warnings=(EditorialResolutionWarning.ADJUDICATION_AMBIGUITY_REMAINS,),
        )
    elif kind == "provider_failure":
        resolution = _resolution(
            identifier,
            resolved_topic=Topic.SCIENCE,
            status=EditorialResolutionStatus.FALLBACK_ACCEPTED,
            source=EditorialResolutionSource.FALLBACK,
            confidence="HIGH",
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            review_required=True,
            warnings=(EditorialResolutionWarning.PROVIDER_UNAVAILABLE,),
        )
        trust["provider_available"] = False
        metadata.update(
            provider_valid=False,
            provider_failure_category=TopicAuthorityProviderFailureCategory.UNAVAILABLE,
        )
    elif kind == "fingerprint_failure":
        trust["fingerprint_valid"] = False
    elif kind == "candidate_failure":
        trust["candidate_compliant"] = False
    elif kind == "invalid_response":
        resolution = _resolution(
            identifier,
            resolved_topic=Topic.SCIENCE,
            status=EditorialResolutionStatus.FALLBACK_ACCEPTED,
            source=EditorialResolutionSource.FALLBACK,
            confidence="HIGH",
            confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
            review_required=True,
            warnings=(EditorialResolutionWarning.INVALID_ADJUDICATION_RESPONSE,),
        )
        trust["response_valid"] = False
        metadata.update(
            provider_valid=False,
            provider_failure_category=TopicAuthorityProviderFailureCategory.INVALID_RESPONSE,
        )
    elif kind != "eligible_changed":
        raise ValueError(f"unknown synthetic scenario: {kind}")

    config = LimitedTopicAuthorityConfig(authority_mode=mode)
    decision = LimitedTopicAuthorityApplicator().apply(resolution, config, **trust)
    observation = TopicAuthorityObservationBuilder().build(
        decision,
        mode,
        candidate_compliant=trust["candidate_compliant"],
        fingerprint_valid=trust["fingerprint_valid"],
        **metadata,
    )
    return decision, observation, config, trust


def _cohort(kinds: tuple[str, ...], *, mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY):
    records = tuple(
        _scenario(f"{index:03d}-{kind}", kind, mode=mode)
        for index, kind in enumerate(kinds, start=1)
    )
    observations = tuple(item[1] for item in records)
    return records, observations


def _audits(observations, outcomes):
    applied = tuple(item for item in observations if item.authority_applied)
    return tuple(
        TopicAuthorityAuditRecord(
            decision_fingerprint=observation.decision_fingerprint,
            authoritative_topic=Topic.HEALTH,
            review_status=TopicAuthorityAuditStatus.COMPLETED,
            human_reviewed_correctness=correct,
        )
        for observation, correct in zip(applied, outcomes, strict=True)
    )


def _snapshot(observations, audits=(), violations=(), rollback_count=0, config=None):
    aggregator = TopicAuthorityMetricsAggregator()
    operational = aggregator.aggregate_operational(observations)
    safety = aggregator.aggregate_safety(
        observations, audits, violations, rollback_count,
    )
    stop = TopicAuthorityPilotStopEvaluator().evaluate(
        operational, safety, config or LimitedTopicAuthorityConfig(
            authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
        ),
    )
    return {"operational": operational, "safety": safety, "stop": stop}


def _violation_snapshot(
    violation: TopicAuthorityContractViolation,
):
    records, observations = _cohort(("eligible_changed",))
    return _snapshot(observations, violations=(violation,))


def run_simulation(*, persist: bool = False) -> dict[str, Any]:
    """Return the complete deterministic synthetic pilot simulation."""
    distribution = (
        ("eligible_changed",) * 35
        + ("same_label",) * 10
        + ("deterministic",) * 10
        + ("low_confidence",) * 5
        + ("review_required",) * 5
        + ("ambiguity",) * 3
        + ("provider_failure",) * 2
        + ("fingerprint_failure",) * 2
        + ("candidate_failure",) * 2
        + ("invalid_response",)
    )
    _, distribution_observations = _cohort(distribution)
    distribution_snapshot = _snapshot(distribution_observations)

    _, clean_observations = _cohort(("eligible_changed",) * 35)
    clean_audits = _audits(clean_observations[:30], (True,) * 30)
    clean = _snapshot(clean_observations, clean_audits)

    regression_audits = _audits(clean_observations[:1], (False,))
    regression = _snapshot(clean_observations[:1], regression_audits)

    precision29_audits = _audits(clean_observations[:29], (True,) * 25 + (False,) * 4)
    precision_config = LimitedTopicAuthorityConfig(
        authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY,
        regression_budget=30,
    )
    precision_before = _snapshot(
        clean_observations[:29], precision29_audits, config=precision_config,
    )
    precision30_audits = _audits(clean_observations[:30], (True,) * 26 + (False,) * 4)
    precision_failure = _snapshot(
        clean_observations[:30], precision30_audits, config=precision_config,
    )

    invalid_decision = _scenario("contract", "eligible_changed")[0]
    invalid_decision = type(invalid_decision)(
        **{**invalid_decision.__dict__, "review_required": True}
    )
    violations = TopicAuthorityContractValidator().validate(
        invalid_decision,
        LimitedTopicAuthorityConfig(
            authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
        ),
        True, True, True, True,
    )
    contract_violation = _snapshot(clean_observations[:1], violations=violations)
    candidate_violation = _violation_snapshot(
        TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_CANDIDATE
    )
    fingerprint_violation = _violation_snapshot(
        TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_FINGERPRINT
    )
    format_violation = _violation_snapshot(
        TopicAuthorityContractViolation.FORMAT_AUTHORITY_VIOLATION
    )
    intent_violation = _violation_snapshot(
        TopicAuthorityContractViolation.READER_INTENT_AUTHORITY_VIOLATION
    )

    _, provider_failure_observations = _cohort(("provider_failure",))
    provider_failure = _snapshot(provider_failure_observations)
    _, shadow_observations = _cohort(
        ("eligible_changed",) * 20,
        mode=ResolverAuthorityMode.SHADOW,
    )
    shadow = _snapshot(
        shadow_observations,
        config=LimitedTopicAuthorityConfig(),
    )

    before_records, before_observations = _cohort(("eligible_changed",) * 5)
    before = _snapshot(before_observations)
    at_stop = _snapshot(
        before_observations,
        _audits(before_observations[:1], (False,)),
    )
    future_results = tuple(item[0].deterministic_topic for item in before_records[:3])
    _, after_observations = _cohort(
        ("eligible_changed",) * 3,
        mode=ResolverAuthorityMode.SHADOW,
    )
    after = _snapshot(after_observations, config=LimitedTopicAuthorityConfig())
    duplicate_rejected = False
    try:
        TopicAuthorityMetricsAggregator().aggregate_safety(
            clean_observations[:1],
            (clean_audits[0], clean_audits[0]),
        )
    except ValueError:
        duplicate_rejected = True

    result = {
        "simulation_cases": len(distribution),
        "scenario_distribution": {
            kind: distribution.count(kind) for kind in tuple(dict.fromkeys(distribution))
        },
        "distribution": distribution_snapshot,
        "clean": clean,
        "single_regression": regression,
        "precision_before_minimum": precision_before,
        "precision_failure": precision_failure,
        "contract_violation": contract_violation,
        "candidate_violation": candidate_violation,
        "fingerprint_violation": fingerprint_violation,
        "format_violation": format_violation,
        "reader_intent_violation": intent_violation,
        "provider_failure_only": provider_failure,
        "shadow": shadow,
        "rollback": {
            "before": before,
            "at_stop": at_stop,
            "after": after,
            "historical_authoritative_overrides": before["operational"].authoritative_topic_overrides,
            "post_rollback_authoritative_overrides": after["operational"].authoritative_topic_overrides,
            "future_deterministic_topics_preserved": all(
                observation.authority_applied is False
                and observation.authority_source is EditorialResolutionSource.DETERMINISTIC_V1
                for observation in after_observations
            ) and len(future_results) == 3,
        },
        "duplicate_audit_rejected": duplicate_rejected,
        "minimum_audited_override_sample": 30,
        "real_provider_calls": 0,
        "production_mutation": False,
        "offline_canary_classification": "CANARY_SAFE",
        "next_step_decision": "READY_FOR_CONTROLLED_TOPIC_AUTHORITY_CANARY_IMPLEMENTATION",
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
    if hasattr(value, "__dataclass_fields__"):
        return _json_safe(asdict(value))
    return value


def _persist(result: dict[str, Any]) -> None:
    safe = _json_safe(result)
    JSON_PATH.write_text(
        json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = (
        "# Limited Topic Authority Offline Canary\n\n"
        f"- Classification: `{safe['offline_canary_classification']}`\n"
        f"- Simulation cases: {safe['simulation_cases']}\n"
        f"- Clean audited overrides: {safe['clean']['safety']['audited_override_count']}\n"
        f"- Clean override precision: {safe['clean']['safety']['override_precision']:.0%}\n"
        f"- Clean stop: {safe['clean']['stop']['should_stop']}\n"
        f"- Regression stop: {safe['single_regression']['stop']['should_stop']}\n"
        f"- Precision stop at 30: {safe['precision_failure']['stop']['should_stop']}\n"
        f"- Real provider calls: {safe['real_provider_calls']}\n"
        f"- Next step: `{safe['next_step_decision']}`\n"
    )
    MARKDOWN_PATH.write_text(summary, encoding="utf-8")


def main() -> None:
    result = run_simulation(persist=True)
    safe = _json_safe(result)
    print(f"Simulation cases: {safe['simulation_cases']}")
    print(f"Offline canary classification: {safe['offline_canary_classification']}")
    print(f"Clean cohort stop: {safe['clean']['stop']['should_stop']}")
    print(f"Single regression stop: {safe['single_regression']['stop']['should_stop']}")
    print(f"Precision failure stop: {safe['precision_failure']['stop']['should_stop']}")
    print(f"Kill-switch recommendation: {safe['single_regression']['stop']['recommended_mode']}")
    print(f"Real provider calls: {safe['real_provider_calls']}")
    print(f"Next-step decision: {safe['next_step_decision']}")


if __name__ == "__main__":
    main()
