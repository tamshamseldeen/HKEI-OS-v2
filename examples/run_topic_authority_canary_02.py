"""Run the authorized five-case INTERNAL_SINGLE_PATH Topic authority canary once."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.run_openai_semantic_adjudication_live_canary import (  # noqa: E402
    _configuration, _create_openai_client, _SanitizedErrorCapturingProvider,
)
from src.adjudication.environment_semantic_adjudication_secret_resolver import EnvironmentSemanticAdjudicationSecretResolver  # noqa: E402
from src.adjudication.openai_semantic_adjudication_provider import OpenAISemanticAdjudicationProvider  # noqa: E402
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider  # noqa: E402
from src.adjudication.semantic_adjudication_provider_config_validator import SemanticAdjudicationProviderConfigValidator  # noqa: E402
from src.adjudication.semantic_adjudication_runtime_context_builder import SemanticAdjudicationRuntimeContextBuilder  # noqa: E402
from src.semantics.deterministic_semantic_candidate_assessor import DeterministicSemanticCandidateAssessor  # noqa: E402
from src.semantics.semantic_evidence_sufficiency import SemanticEvidenceSufficiency  # noqa: E402
from src.semantics.semantic_relationship_type import SemanticRelationshipType  # noqa: E402
from src.resolution import (  # noqa: E402
    InMemoryTopicAuthorityObservationSink, LimitedTopicAuthorityConfig,
    ResolverAuthorityMode, TopicAuthorityBlockReason, TopicAuthorityCanaryRouteConfig,
    TopicAuthorityContractViolation, TopicAuthorityMetricsAggregator,
    TopicAuthorityPilotStopEvaluator, TopicAuthorityRuntimeConfig, TopicAuthoritySafetyMetrics,
)
from src.workflows.controlled_topic_authority_canary_workflow import ControlledTopicAuthorityCanaryWorkflow  # noqa: E402
from src.workflows.experimental_semantic_adjudication_shadow_workflow import ExperimentalSemanticAdjudicationShadowWorkflow  # noqa: E402
from src.workflows.internal_topic_authority_canary import InternalTopicAuthorityCanaryEntrypoint  # noqa: E402
from src.workflows.limited_editorial_resolver_shadow_workflow import LimitedEditorialResolverShadowWorkflow  # noqa: E402


SOURCE = ROOT / "canary_sources/topic_authority_canary_02.txt"
MANIFEST = ROOT / "canary_sources/topic_authority_canary_02_manifest.json"
OUTPUT_JSON = ROOT / "benchmark/internal_canary/topic_authority_canary_02.json"
OUTPUT_MD = ROOT / "benchmark/internal_canary/topic_authority_canary_02.md"
SOURCE_SHA256 = "06ac5eff8fb27212ec06351f056d9911d47bd739fe29e27b81844a1519e2cb04"
CASE_IDS = tuple(f"CANARY2-{number:03d}" for number in range(1, 6))
MAX_CALLS = 5


class _CallLimitedProvider(SemanticAdjudicationProvider):
    def __init__(self, provider):
        self.provider = provider
        self.call_count = 0
    @property
    def provider_name(self): return self.provider.provider_name
    @property
    def model_name(self): return self.provider.model_name
    def adjudicate(self, request):
        if self.call_count >= MAX_CALLS:
            raise RuntimeError("internal canary live-call limit exceeded")
        self.call_count += 1
        return self.provider.adjudicate(request)


class _CapturingControlledWorkflow(ControlledTopicAuthorityCanaryWorkflow):
    last_result = None
    def analyze(self, **fields):
        self.last_result = super().analyze(**fields)
        return self.last_result


def _verify_source():
    if not SOURCE.is_file() or sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise RuntimeError("registered canary source integrity failure")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if tuple(data["case_ids"]) != CASE_IDS or data["case_count"] != 5:
        raise RuntimeError("registered canary inventory mismatch")
    if data["evaluation_status"] != "NOT_RUN" or data["provider_calls"] != 0:
        raise RuntimeError("registered canary was already evaluated")
    if data["source_integrity"] != "VERIFIED_FAITHFUL_REGISTRATION":
        raise RuntimeError("registered source integrity was not verified")
    if data["freshness_status"] != "VERIFIED_NEW_OPERATIONAL_INPUTS":
        raise RuntimeError("registered source freshness was not verified")
    if any(data[name] != 0 for name in (
        "duplicate_with_canary_01",
        "duplicate_with_benchmark_batches",
        "duplicate_with_generic_HKEI_216_fixtures",
    )):
        raise RuntimeError("registered source freshness audit failed")


def _parse_cases():
    parts = re.split(r"(?=^canary_id: CANARY2-\d{3}$)", SOURCE.read_text(encoding="utf-8"), flags=re.MULTILINE)
    cases = []
    for part in (item for item in parts if item.strip()):
        case_id = re.search(r"^canary_id: (CANARY2-\d{3})$", part, re.MULTILINE).group(1)
        url = part.split("لينك الخبر:", 1)[1].split("عنوان الخبر:", 1)[0].strip()
        title = part.split("عنوان الخبر:", 1)[1].split("محتوى الخبر:", 1)[0].strip()
        body = part.split("محتوى الخبر:", 1)[1].strip()
        cases.append((case_id, {"title": title, "body": body, "source_name": "internal-canary", "source_url": url, "language": "ar"}))
    if tuple(item[0] for item in cases) != CASE_IDS:
        raise RuntimeError("registered canary parse mismatch")
    return tuple(cases)


def _live_provider(model):
    context = SemanticAdjudicationRuntimeContextBuilder(
        config_validator=SemanticAdjudicationProviderConfigValidator(),
        secret_resolver=EnvironmentSemanticAdjudicationSecretResolver(),
    ).build(_configuration(model))
    return OpenAISemanticAdjudicationProvider(
        runtime_context=context,
        client=_create_openai_client(context),
    )


def _semantic_diagnostic(raw):
    evidence = raw.shadow_workflow_result.editorial_result.semantic_evidence
    assessments = DeterministicSemanticCandidateAssessor().assess(
        semantic_evidence=evidence
    )
    consequence_domains = tuple(dict.fromkeys(
        support.removeprefix("SECONDARY_DOMAIN_")
        for relationship in evidence.relationships
        if relationship.relationship_type is SemanticRelationshipType.CONSEQUENCE_OF_EVENT
        for support in relationship.supports
        if support.startswith("SECONDARY_DOMAIN_")
    ))
    primary_domains = tuple(
        item.removeprefix("PRIMARY_DOMAIN_")
        for item in evidence.primary_domain_candidates
    )
    consequence_only_primary = tuple(
        item.candidate for item in assessments
        if "CONSEQUENCE_ONLY_SUPPORT" in item.warnings
        and item.sufficiency is SemanticEvidenceSufficiency.SUFFICIENT
    )
    return {
        "central_topic_role_support": list(primary_domains),
        "consequence_context_topic_support": list(consequence_domains),
        "consequence_only_primary_sufficiency": list(consequence_only_primary),
        "consequence_only_primary_sufficiency_count": len(consequence_only_primary),
    }


def _case_record(case_id, safe, raw, capturing, latency_ms):
    response = raw.shadow_workflow_result.validated_response
    usage = response.usage if response else None
    observation = raw.authority_observation
    return {
        "canary_id": case_id,
        "deterministic_topic": safe.deterministic_topic.value,
        "resolved_topic": safe.resolved_topic.value if safe.resolved_topic else None,
        "authoritative_topic": safe.authoritative_topic.value,
        "consumer_topic": safe.consumer_topic.value,
        "gate_scope": raw.shadow_workflow_result.adjudication_decision.scope.value,
        "resolver_topic_status": raw.resolution_result.topic_resolution.status.value,
        "provider_called": observation.provider_called,
        "provider_status": "SUCCESS" if observation.provider_valid else (capturing.sanitized_error or "NOT_CALLED"),
        "response_valid": observation.provider_valid,
        "candidate_compliant": observation.candidate_compliant,
        "fingerprint_valid": observation.fingerprint_valid,
        "provider_confidence": safe.provider_confidence.value if safe.provider_confidence else None,
        "ambiguity_remaining": safe.ambiguity_remaining,
        "review_required": safe.review_required,
        "authority_applied": safe.authority_applied,
        "authority_consumed": safe.authority_consumed,
        "authority_source": safe.authority_source.value,
        "route": safe.route.value,
        "block_reasons": [item.value for item in safe.block_reasons],
        "warnings": [item.value for item in safe.warnings],
        "stop_recommended": safe.stop_recommended,
        "input_fingerprint": observation.decision_fingerprint,
        "consequence_role_diagnostic_summary": _semantic_diagnostic(raw),
        "usage": ({"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "reasoning_tokens": usage.reasoning_tokens} if usage else None),
        "latency_milliseconds": latency_ms,
    }


def _summary(cases, provider_calls, stopped, contract_violations, global_before, global_after):
    consumed = sum(item["authority_consumed"] for item in cases)
    provider_errors = sum(item["provider_called"] and not item["response_valid"] for item in cases)
    consequence_regressions = sum(
        item["consequence_role_diagnostic_summary"]["consequence_only_primary_sufficiency_count"]
        for item in cases
    )
    unsafe = bool(contract_violations) or any(
        item["route"] != "INTERNAL_TOPIC_AUTHORITY_CANARY_PATH"
        or (item["authority_consumed"] and "AUTHORITY_OBSERVATION_FAILED" in item["warnings"])
        for item in cases
    )
    classification = "SECOND_CANARY_UNSAFE" if unsafe else "SECOND_CANARY_STOPPED_SAFELY" if stopped else "SECOND_CANARY_OPERATIONALLY_CLEAN" if consumed else "SECOND_CANARY_CLEAN_WITH_NO_AUTHORITY_OPPORTUNITY"
    return {
        "canary_id": "topic_authority_canary_02",
        "operational_status": "CONTROLLED_INTERNAL_OPERATIONAL_CANARY",
        "classification": classification,
        "cases_attempted": len(cases), "cases_completed": len(cases),
        "topic_adjudication_requests": sum(item["gate_scope"] in {"TOPIC_REQUIRED", "TOPIC_AND_FORMAT_REQUIRED"} for item in cases),
        "provider_calls": provider_calls,
        "valid_responses": sum(item["response_valid"] for item in cases),
        "invalid_responses": provider_errors,
        "provider_errors": provider_errors,
        "retry_attempts": 0,
        "resolver_adjudicated_accepted": sum(item["resolver_topic_status"] == "ADJUDICATED_ACCEPTED" for item in cases),
        "authority_applied_count": sum(item["authority_applied"] for item in cases),
        "authority_consumed_count": consumed,
        "no_topic_change_count": sum("NO_TOPIC_CHANGE" in item["block_reasons"] for item in cases),
        "authority_blocked_count": sum(not item["authority_applied"] for item in cases),
        "observation_failures": sum("AUTHORITY_OBSERVATION_FAILED" in item["warnings"] for item in cases),
        "contract_violations": contract_violations,
        "candidate_violations": sum(not item["candidate_compliant"] for item in cases),
        "fingerprint_violations": sum(not item["fingerprint_valid"] for item in cases),
        "format_authority_violations": 0, "reader_intent_authority_violations": 0,
        "stop_recommendations": sum(item["stop_recommended"] for item in cases),
        "consequence_only_primary_sufficiency_count": consequence_regressions,
        "hkei_216_generalization_signal": (
            "CONSEQUENCE_SUBJECT_REGRESSION_RECURRED"
            if consequence_regressions
            else "NO_NEW_CONSEQUENCE_SUBJECT_REGRESSION_OBSERVED"
            if len(cases) == len(CASE_IDS)
            else "INSUFFICIENT_AUTHORITY_OPPORTUNITY_TO_ASSESS"
        ),
        "canary_stopped_early": stopped,
        "audit_queue": [{
            "canary_id": item["canary_id"],
            "decision_fingerprint": item["input_fingerprint"],
            "deterministic_topic": item["deterministic_topic"],
            "authoritative_topic": item["authoritative_topic"],
            "correctness": None,
        } for item in cases if item["authority_consumed"]],
        "human_correctness_judgments_made": 0,
        "global_mode_before_run": global_before.value,
        "global_mode_after_run": global_after.value,
        "internal_route_state_after_run": "DISABLED_DEFAULT",
        "production_wide_authority_enabled": False,
        "next_step_decision": "PAUSE_FOR_HUMAN_AUDIT" if consumed else "CONTINUE_INTERNAL_CANARY_ACCUMULATION",
        "cases": cases,
    }


def render_markdown(summary):
    return f"""# Second Internal Topic Authority Canary

Classification: `{summary['classification']}`

Cases completed/provider calls/valid responses: {summary['cases_completed']} / {summary['provider_calls']} / {summary['valid_responses']}

Authority applied/consumed: {summary['authority_applied_count']} / {summary['authority_consumed_count']}

Global mode before/after: `{summary['global_mode_before_run']}` / `{summary['global_mode_after_run']}`

Next step: `{summary['next_step_decision']}`

Only sanitized provenance is persisted. No source body, raw prompt, raw response,
provider exception payload, secret, or reasoning text is stored.
"""


def run_canary(*, model="gpt-5-mini", provider=None, output_json=OUTPUT_JSON, output_md=OUTPUT_MD, monotonic=time.monotonic):
    _verify_source()
    if output_json == OUTPUT_JSON and (OUTPUT_JSON.exists() or OUTPUT_MD.exists()):
        raise RuntimeError("Canary 02 evaluation artifact already exists")
    global_before = TopicAuthorityRuntimeConfig().resolve()
    if global_before is not ResolverAuthorityMode.SHADOW or TopicAuthorityCanaryRouteConfig().route_enabled:
        raise RuntimeError("global canary safety baseline failed")
    limited_provider = _CallLimitedProvider(provider or _live_provider(model))
    capturing = _SanitizedErrorCapturingProvider(limited_provider)
    base = ExperimentalSemanticAdjudicationShadowWorkflow(provider=capturing)
    shadow = LimitedEditorialResolverShadowWorkflow(provider=capturing, adjudication_workflow=base)
    runtime = TopicAuthorityRuntimeConfig(ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY)
    sink = InMemoryTopicAuthorityObservationSink()
    workflow = _CapturingControlledWorkflow(
        provider=capturing,
        config=LimitedTopicAuthorityConfig(authority_mode=ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY),
        runtime_config=runtime, observation_sink=sink, shadow_workflow=shadow,
    )
    entry = InternalTopicAuthorityCanaryEntrypoint(workflow, TopicAuthorityCanaryRouteConfig(True, "HKEI-218"))
    records = []; violations = []; stopped = False
    aggregator = TopicAuthorityMetricsAggregator(); evaluator = TopicAuthorityPilotStopEvaluator()
    for case_id, fields in _parse_cases():
        safety = TopicAuthoritySafetyMetrics(authority_contract_violation_count=len(violations))
        stop = evaluator.evaluate(aggregator.aggregate_operational(sink.observations), safety, workflow.config)
        if stop.should_stop:
            runtime.apply_stop_signal(stop); stopped = True; break
        capturing.sanitized_error = None
        started = monotonic(); safe = entry.run_internal_topic_authority_canary(**fields); latency = max(0, round((monotonic()-started)*1000))
        raw = workflow.last_result
        violations.extend(item.value for item in raw.contract_violations)
        record = _case_record(case_id, safe, raw, capturing, latency)
        records.append(record)
        hard_stop = (
            bool(raw.contract_violations)
            or not record["candidate_compliant"]
            or not record["fingerprint_valid"]
            or (record["authority_consumed"] and "AUTHORITY_OBSERVATION_FAILED" in record["warnings"])
            or record["stop_recommended"]
        )
        if hard_stop:
            runtime.set_mode(ResolverAuthorityMode.SHADOW); stopped = True; break
    global_after = TopicAuthorityRuntimeConfig().resolve()
    summary = _summary(records, limited_provider.call_count, stopped, violations, global_before, global_after)
    summary["source_sha256"] = SOURCE_SHA256
    summary["model"] = model
    summary["evaluation_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    summary["evaluation_commit"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    output_md.write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--model", default="gpt-5-mini"); args=parser.parse_args(argv)
    summary=run_canary(model=args.model)
    print(json.dumps({key:value for key,value in summary.items() if key not in {"cases", "audit_queue"}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
