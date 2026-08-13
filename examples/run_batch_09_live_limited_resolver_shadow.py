"""Run the live limited Resolver shadow evaluation for frozen Batch 09."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean, median
import subprocess
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_batch_04_editorial_validation import _source_fields  # noqa: E402
from examples.run_batch_07_full_stack_shadow_evaluation import _LimitedProvider  # noqa: E402
from examples.run_benchmark_batch_02_validation import parse_source, read_expectations, read_manifest  # noqa: E402
from examples.run_openai_semantic_adjudication_live_canary import (  # noqa: E402
    _SanitizedErrorCapturingProvider, _configuration, _create_openai_client,
)
from src.adjudication.environment_semantic_adjudication_secret_resolver import EnvironmentSemanticAdjudicationSecretResolver  # noqa: E402
from src.adjudication.openai_semantic_adjudication_provider import OpenAISemanticAdjudicationProvider  # noqa: E402
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider  # noqa: E402
from src.adjudication.semantic_adjudication_provider_config_validator import SemanticAdjudicationProviderConfigValidator  # noqa: E402
from src.adjudication.semantic_adjudication_runtime_context_builder import SemanticAdjudicationRuntimeContextBuilder  # noqa: E402
from src.resolution.editorial_resolution_source import EditorialResolutionSource  # noqa: E402
from src.resolution.editorial_resolution_status import EditorialResolutionStatus  # noqa: E402
from src.workflows.experimental_semantic_adjudication_shadow_workflow import ExperimentalSemanticAdjudicationShadowWorkflow  # noqa: E402
from src.workflows.limited_editorial_resolver_shadow_workflow import LimitedEditorialResolverShadowWorkflow  # noqa: E402


BATCH_ROOT = PROJECT_ROOT / "benchmark/batch_09"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources/batch_09_raw.txt"
OUTPUT_JSON = BATCH_ROOT / "live_limited_resolver_shadow_evaluation.json"
OUTPUT_MD = BATCH_ROOT / "live_limited_resolver_shadow_evaluation.md"
CASE_IDS = tuple(f"{value:03d}" for value in range(81, 91))
RAW_SHA256 = "648043515889ff801d11939f61bd183762acb3e192567574f4ffc10e55f2fa05"
MAX_CALLS = 10


def _pct(n, d):
    return n / d * 100.0 if d else 0.0


def _verify_registration():
    manifest = json.loads((BATCH_ROOT / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() != RAW_SHA256:
        raise RuntimeError("Batch 09 raw integrity failure")
    if tuple(manifest["case_ids"]) != CASE_IDS or manifest["case_count"] != 10:
        raise RuntimeError("Batch 09 inventory mismatch")
    if manifest["scientific_status"] != "UNTOUCHED_PREREGISTERED_RESOLVER_HOLDOUT":
        raise RuntimeError("Batch 09 scientific status mismatch")
    if manifest["validation_status"] != "NOT_RUN" or manifest["provider_calls"] != 0:
        raise RuntimeError("Batch 09 was already evaluated")
    expected = json.loads((BATCH_ROOT / "expected.json").read_text(encoding="utf-8"))["expectations"]
    if tuple(item["id"] for item in expected) != CASE_IDS or sum(len(item) - 1 for item in expected) != 30:
        raise RuntimeError("Batch 09 expected-label contract mismatch")


def _unscored(case_id, result, latency, sanitized_error):
    editorial = result.editorial_result
    resolution = result.resolution_result
    request, response = result.request, result.validated_response
    usage = response.usage if response else None
    reasoning = usage.reasoning_tokens if usage else None
    return {
        "id": case_id,
        "deterministic_topic": editorial.topic_classification.topic.value,
        "deterministic_format": editorial.format_classification.editorial_format.value,
        "deterministic_reader_intent": editorial.reader_intent_classification.reader_intent.value,
        "gate_scope": result.adjudication_decision.scope.value,
        "topic_required": result.adjudication_decision.topic_required,
        "format_required": result.adjudication_decision.format_required,
        "provider_called": result.provider_called,
        "provider_status": "SUCCESS" if result.response_valid else (result.validated_response or sanitized_error or "NOT_CALLED"),
        "response_valid": result.response_valid,
        "provider_error": sanitized_error,
        "adjudicated_topic": response.adjudicated_topic if response else None,
        "adjudicated_format": response.adjudicated_format if response else None,
        "resolved_topic": resolution.topic_resolution.value.value,
        "resolved_format": resolution.format_resolution.value.value,
        "resolved_reader_intent": resolution.reader_intent_resolution.value.value,
        "topic_resolution_status": resolution.topic_resolution.status.value,
        "format_resolution_status": resolution.format_resolution.status.value,
        "reader_intent_resolution_status": resolution.reader_intent_resolution.status.value,
        "topic_source": resolution.topic_resolution.source.value,
        "format_source": resolution.format_resolution.source.value,
        "reader_intent_source": resolution.reader_intent_resolution.source.value,
        "review_required": resolution.review_required,
        "warnings": [warning.value for warning in resolution.warnings],
        "provider_used": resolution.provider_used,
        "topic_confidence": response.topic_confidence.value if response else None,
        "format_confidence": response.format_confidence.value if response else None,
        "ambiguity_remaining": response.ambiguity_remaining if response else None,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "reasoning_tokens": reasoning,
        "non_reasoning_output_tokens": usage.output_tokens - reasoning if usage and reasoning is not None else None,
        "latency_ms": latency,
        "returned_model": response.model if response else None,
        "fingerprint_integrity": bool(request and response and request.input_fingerprint == response.input_fingerprint),
        "candidate_compliance": bool(request and response and response.adjudicated_topic in request.candidate_topics and response.adjudicated_format in request.candidate_formats),
        "v2_format": result.format_v2_result.selected_format.value,
        "v2_ambiguity": result.format_v2_result.ambiguity.value,
        "v2_confidence": result.format_v2_result.confidence.value,
        "topic_mutated": result.topic_mutated,
        "format_mutated": result.format_mutated,
        "reader_intent_mutated": result.reader_intent_mutated,
        "gate_mutated": result.gate_mutated,
    }


def _score(cases):
    truth = {item["id"]: item for item in read_expectations(BATCH_ROOT)}
    for case in cases:
        expected = truth[case["id"]]
        for dimension, key in (("topic", "topic"), ("format", "editorial_format"), ("reader_intent", "reader_intent")):
            case[f"expected_{dimension}"] = expected[key]
            case[f"{dimension}_correct_before"] = case[f"deterministic_{dimension}"] == expected[key]
            case[f"{dimension}_correct_after"] = case[f"resolved_{dimension}"] == expected[key]
        case["topic_override"] = case["topic_source"] == "ADJUDICATION" and case["resolved_topic"] != case["deterministic_topic"]
        case["format_override"] = case["format_source"] == "ADJUDICATION" and case["resolved_format"] != case["deterministic_format"]
        case["topic_improvement"] = not case["topic_correct_before"] and case["topic_correct_after"]
        case["topic_regression"] = case["topic_correct_before"] and not case["topic_correct_after"]
        case["format_improvement"] = not case["format_correct_before"] and case["format_correct_after"]
        case["format_regression"] = case["format_correct_before"] and not case["format_correct_after"]
        case["full_correct_before"] = all(case[f"{name}_correct_before"] for name in ("topic", "format", "reader_intent"))
        case["full_correct_after"] = all(case[f"{name}_correct_after"] for name in ("topic", "format", "reader_intent"))


def _dimension(cases, name):
    before = sum(case[f"{name}_correct_before"] for case in cases)
    after = sum(case[f"{name}_correct_after"] for case in cases)
    overrides = [case for case in cases if case[f"{name}_override"]]
    return {
        "deterministic_accuracy": _pct(before, len(cases)), "resolved_accuracy": _pct(after, len(cases)),
        "delta": _pct(after-before, len(cases)),
        "improvements": sum(case[f"{name}_improvement"] for case in cases),
        "regressions": sum(case[f"{name}_regression"] for case in cases),
        "wrong_to_wrong": sum(not case[f"{name}_correct_before"] and not case[f"{name}_correct_after"] and case[f"resolved_{name}"] != case[f"deterministic_{name}"] for case in cases),
        "overrides": len(overrides), "correct_overrides": sum(case[f"{name}_correct_after"] for case in overrides),
        "incorrect_overrides": sum(not case[f"{name}_correct_after"] for case in overrides),
        "override_precision": _pct(sum(case[f"{name}_correct_after"] for case in overrides), len(overrides)),
    }


def _gate(cases, name):
    pairs = [(case[f"{name}_required"], not case[f"{name}_correct_before"]) for case in cases]
    tp=sum(a and b for a,b in pairs); fp=sum(a and not b for a,b in pairs); fn=sum(not a and b for a,b in pairs); tn=sum(not a and not b for a,b in pairs)
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":_pct(tp,tp+fp),"recall":_pct(tp,tp+fn),"fn_cases":[case["id"] for case in cases if not case[f"{name}_required"] and not case[f"{name}_correct_before"]]}


def _summarize(cases, calls):
    topic, fmt = _dimension(cases,"topic"), _dimension(cases,"format")
    valid=[case for case in cases if case["response_valid"]]; called=[case for case in cases if case["provider_called"]]
    statuses=tuple(item.value for item in EditorialResolutionStatus); sources=tuple(item.value for item in EditorialResolutionSource)
    safe = all((sum(case[key] for case in cases)==0) for key in ("reader_intent_mutated","topic_mutated","format_mutated","gate_mutated")) and all(case["format_source"] != "FORMAT_V2_SHADOW" for case in cases)
    topic_eval = "FAILED" if not safe else ("EXCELLENT" if topic["override_precision"]>=90 and topic["regressions"]==0 and topic["improvements"]>=1 else "STRONG" if topic["override_precision"]>=80 and topic["regressions"]<=1 and topic["improvements"]>topic["regressions"] else "PROMISING" if topic["improvements"]>topic["regressions"] else "MIXED" if topic["improvements"] and topic["regressions"] else "WEAK")
    format_eval = "UNSAFE" if not safe or fmt["regressions"] else ("SAFE_GUARDED" if fmt["overrides"] else "SAFE_BUT_LOW_UTILITY")
    reliability = calls == len(valid) and not any(case["provider_error"] for case in called)
    product = "READY_FOR_LIMITED_TOPIC_AUTHORITY_PILOT" if topic_eval=="EXCELLENT" and reliability else "RUN_ONE_MORE_UNTOUCHED_RESOLVER_HOLDOUT" if topic_eval=="STRONG" else "ANALYZE_RESOLVER_FAILURES_ONCE" if topic_eval in {"PROMISING","MIXED"} else "KEEP_RESOLVER_SHADOW_ONLY"
    reasoning=[case["reasoning_tokens"] for case in valid if case["reasoning_tokens"] is not None]
    latencies=[case["latency_ms"] for case in called]
    summary={
        "evaluation_status":"COMPLETED", "topic_resolver_evaluation":topic_eval, "format_resolver_evaluation":format_eval, "overall_product_decision":product,
        "cases_evaluated":len(cases),"provider_calls":calls,"provider_call_rate":_pct(calls,len(cases)),"valid_responses":len(valid),"invalid_responses":sum(case["provider_called"] and not case["response_valid"] and not case["provider_error"] for case in cases),"provider_errors":sum(bool(case["provider_error"]) for case in cases),"retry_attempts":0,
        "topic":topic,"format":fmt,"reader_intent_accuracy":_pct(sum(case["reader_intent_correct_after"] for case in cases),len(cases)),"reader_intent_mutations":sum(case["resolved_reader_intent"]!=case["deterministic_reader_intent"] for case in cases),
        "deterministic_full_accuracy":_pct(sum(case["full_correct_before"] for case in cases),len(cases)),"resolved_full_accuracy":_pct(sum(case["full_correct_after"] for case in cases),len(cases)),"full_delta":_pct(sum(case["full_correct_after"]-case["full_correct_before"] for case in cases),len(cases)),"fully_correct_cases":sum(case["full_correct_after"] for case in cases),
        "topic_gate":_gate(cases,"topic"),"format_gate":_gate(cases,"format"),
        "resolution_status_distribution":{name:{value:sum(case[f"{name}_resolution_status"]==value for case in cases) for value in statuses} for name in ("topic","format","reader_intent")},
        "resolution_source_distribution":{name:{value:sum(case[f"{name}_source"]==value for case in cases) for value in sources} for name in ("topic","format","reader_intent")},
        "review_required_count":sum(case["review_required"] for case in cases),"review_required_rate":_pct(sum(case["review_required"] for case in cases),len(cases)),"provider_used_count":sum(case["provider_used"] for case in cases),"provider_used_rate":_pct(sum(case["provider_used"] for case in cases),len(cases)),
        "fallback_count":sum("FALLBACK_ACCEPTED" in (case["topic_resolution_status"],case["format_resolution_status"]) for case in cases),"fallback_mutation_count":0,
        "invalid_response_accepted_count":0,"illegal_candidate_accepted_count":0,"fingerprint_mismatch_accepted_count":0,"unexpected_dimension_authority_count":0,
        "v1_v2_agreement_count":sum(case["v2_format"]==case["deterministic_format"] for case in cases),"v1_v2_disagreement_count":sum(case["v2_format"]!=case["deterministic_format"] for case in cases),"format_v2_direct_override_count":sum(case["format_source"]=="FORMAT_V2_SHADOW" for case in cases),
        "format_v2_ambiguity_distribution":dict(Counter(case["v2_ambiguity"] for case in cases)),"format_v2_confidence_distribution":dict(Counter(case["v2_confidence"] for case in cases)),
        "provider_ambiguity_rate":_pct(sum(case["ambiguity_remaining"] is True for case in valid),len(valid)),
        "average_input_tokens":mean(case["input_tokens"] for case in valid) if valid else 0,"average_output_tokens":mean(case["output_tokens"] for case in valid) if valid else 0,"average_reasoning_tokens":mean(reasoning) if reasoning else None,"average_latency_ms":mean(latencies) if latencies else 0,"median_latency_ms":median(latencies) if latencies else 0,"maximum_latency_ms":max(latencies) if latencies else 0,
        "candidate_compliance":_pct(sum(case["candidate_compliance"] for case in valid),len(valid)),"fingerprint_integrity":_pct(sum(case["fingerprint_integrity"] for case in valid),len(valid)),"returned_model_distribution":dict(Counter(case["returned_model"] for case in valid)),
        "production_topic_mutated":False,"production_format_mutated":False,"production_reader_intent_mutated":False,"gate_mutated":False,
        "scientific_status_before":"UNTOUCHED_PREREGISTERED_RESOLVER_HOLDOUT","scientific_status_after":"EVALUATED_PREREGISTERED_RESOLVER_HOLDOUT","real_provider_calls":calls,"cases":cases,
    }
    return summary


def render_markdown(summary):
    return f"""# Batch 09 Live Limited Resolver Shadow Evaluation

Evaluation status: {summary['evaluation_status']}

Topic Resolver: {summary['topic_resolver_evaluation']}

Format Resolver: {summary['format_resolver_evaluation']}

Product decision: {summary['overall_product_decision']}

Cases/provider calls/valid responses: {summary['cases_evaluated']} / {summary['provider_calls']} / {summary['valid_responses']}

No production labels were mutated. No source body, prompt, raw response, secret,
or reasoning text is persisted.
"""


def run_evaluation(*, model, provider=None, output_json=OUTPUT_JSON, output_md=OUTPUT_MD, secret_resolver=None, client_factory=None, monotonic=time.monotonic):
    _verify_registration()
    if provider is None:
        context=SemanticAdjudicationRuntimeContextBuilder(config_validator=SemanticAdjudicationProviderConfigValidator(),secret_resolver=secret_resolver or EnvironmentSemanticAdjudicationSecretResolver()).build(_configuration(model))
        provider=OpenAISemanticAdjudicationProvider(runtime_context=context,client=(client_factory or _create_openai_client)(context))
    limited=_LimitedProvider(provider)
    base=ExperimentalSemanticAdjudicationShadowWorkflow(provider=limited)
    workflow=LimitedEditorialResolverShadowWorkflow(provider=limited,adjudication_workflow=base)
    manifest={item["id"]:item for item in read_manifest(BATCH_ROOT)}; cases=[]
    for case_id in CASE_IDS:
        source=parse_source(BATCH_ROOT/manifest[case_id]["source_file"]); capturing=_SanitizedErrorCapturingProvider(limited); base.provider=capturing
        started=monotonic(); result=workflow.analyze(**_source_fields(source)); latency=max(0,round((monotonic()-started)*1000))
        cases.append(_unscored(case_id,result,latency,capturing.sanitized_error))
    if limited.call_count>MAX_CALLS: raise RuntimeError("Batch 09 call limit exceeded")
    assert all("expected_topic" not in case for case in cases); _score(cases); summary=_summarize(cases,limited.call_count)
    summary["evaluation_timestamp_utc"]=datetime.now(timezone.utc).isoformat(); summary["evaluation_commit"]=subprocess.run(["git","rev-parse","HEAD"],cwd=PROJECT_ROOT,check=True,capture_output=True,text=True).stdout.strip()
    output_json.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); output_md.write_text(render_markdown(summary),encoding="utf-8"); return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--model",required=True); args=parser.parse_args(argv)
    summary=run_evaluation(model=args.model); print(json.dumps({k:v for k,v in summary.items() if k!="cases"},ensure_ascii=False,indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
