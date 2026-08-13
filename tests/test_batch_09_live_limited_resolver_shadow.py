"""Pre-live fake-provider safety tests for Batch 09 Resolver evaluation."""

from dataclasses import replace
import hashlib
import inspect
import json

import pytest

import examples.run_batch_09_live_limited_resolver_shadow as runner
from src.adjudication.adjudication_confidence import AdjudicationConfidence
from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.adjudication.semantic_adjudication_response import SemanticAdjudicationResponse
from src.adjudication.semantic_adjudication_usage import SemanticAdjudicationUsage


class FakeProvider(SemanticAdjudicationProvider):
    def __init__(self, mutate=None): self.calls=0; self.mutate=mutate
    @property
    def provider_name(self): return "fake"
    @property
    def model_name(self): return "gpt-5-mini"
    def adjudicate(self, request):
        self.calls += 1
        response=SemanticAdjudicationResponse(
            adjudicated_topic=request.candidate_topics[0], adjudicated_format=request.candidate_formats[0],
            topic_confidence=AdjudicationConfidence.HIGH, format_confidence=AdjudicationConfidence.MEDIUM,
            topic_reason="دليل", format_reason="دليل", topic_evidence_refs=("TITLE",), format_evidence_refs=("LEAD",),
            ambiguity_remaining=False, warnings=(), provider="fake", model="gpt-5-mini",
            request_schema_version="1.0", response_schema_version="1.1", input_fingerprint=request.input_fingerprint,
            usage=SemanticAdjudicationUsage(10,5,1),
        )
        return self.mutate(response) if self.mutate else response


@pytest.fixture(scope="module")
def fake_result(tmp_path_factory):
    root=tmp_path_factory.mktemp("batch09-live")
    provider=FakeProvider()
    result=runner.run_evaluation(model="gpt-5-mini",provider=provider,output_json=root/"out.json",output_md=root/"out.md")
    return result,provider,root


def test_exact_inventory_and_raw_integrity() -> None:
    assert runner.CASE_IDS == tuple(f"{value:03d}" for value in range(81,91))
    assert hashlib.sha256(runner.RAW_SOURCE.read_bytes()).hexdigest() == runner.RAW_SHA256
    runner._verify_registration()


def test_frozen_expected_labels_have_thirty_values() -> None:
    data=json.loads((runner.BATCH_ROOT/"expected.json").read_text())["expectations"]
    assert len(data)==10 and sum(len(item)-1 for item in data)==30


def test_expected_labels_are_isolated_until_all_resolver_outputs(monkeypatch,tmp_path) -> None:
    original=runner._score; observed={}
    def guarded(cases):
        observed["count"]=len(cases)
        assert all("expected_topic" not in case for case in cases)
        assert all("resolved_topic" in case for case in cases)
        return original(cases)
    monkeypatch.setattr(runner,"_score",guarded)
    runner.run_evaluation(model="gpt-5-mini",provider=FakeProvider(),output_json=tmp_path/"a.json",output_md=tmp_path/"a.md")
    assert observed["count"]==10


def test_fake_provider_call_bound_and_no_retries(fake_result) -> None:
    result,provider,_=fake_result
    assert provider.calls==result["provider_calls"]<=10
    assert result["retry_attempts"]==0


def test_resolver_topic_authority_and_guarded_format(fake_result) -> None:
    result,_,_=fake_result
    assert all(case["topic_source"] in {"DETERMINISTIC_V1","ADJUDICATION","FALLBACK"} for case in result["cases"])
    assert result["format_v2_direct_override_count"]==0


def test_reader_intent_preserved(fake_result) -> None:
    result,_,_=fake_result
    assert result["reader_intent_mutations"]==0
    assert all(case["resolved_reader_intent"]==case["deterministic_reader_intent"] for case in result["cases"])


def test_candidate_and_fingerprint_integrity(fake_result) -> None:
    result,_,_=fake_result
    assert result["candidate_compliance"]==100
    assert result["fingerprint_integrity"]==100


def test_invalid_response_is_not_accepted(tmp_path) -> None:
    provider=FakeProvider(lambda response: replace(response,input_fingerprint="wrong"))
    result=runner.run_evaluation(model="gpt-5-mini",provider=provider,output_json=tmp_path/"a.json",output_md=tmp_path/"a.md")
    assert result["invalid_response_accepted_count"]==0
    assert result["provider_used_count"]==0


def test_review_and_provider_used_semantics(fake_result) -> None:
    result,_,_=fake_result
    assert result["review_required_count"]==sum(case["review_required"] for case in result["cases"])
    assert result["provider_used_count"]==sum(case["provider_used"] for case in result["cases"])


def test_no_production_mutation(fake_result) -> None:
    result,_,_=fake_result
    assert not result["production_topic_mutated"] and not result["production_format_mutated"]
    assert not result["production_reader_intent_mutated"] and not result["gate_mutated"]


def test_artifacts_are_sanitized(fake_result) -> None:
    _,_,root=fake_result; text=(root/"out.json").read_text()+(root/"out.md").read_text()
    assert not any(value in text for value in ("OPENAI_API_KEY","sk-","raw_prompt","raw_response","# Body"))


def test_runtime_configuration_is_exact() -> None:
    config=runner._configuration("gpt-5-mini")
    assert config.model=="gpt-5-mini" and config.max_output_tokens==1200
    assert config.max_retries==0 and config.timeout_seconds==30.0
    assert config.reasoning_effort.value=="LOW"


def test_runner_does_not_embed_expected_labels_in_provider_inputs() -> None:
    assert "read_expectations" not in inspect.getsource(runner._unscored)
    assert "read_expectations" not in inspect.getsource(runner.LimitedEditorialResolverShadowWorkflow)
    assert "read_expectations" in inspect.getsource(runner._score)


def test_status_distributions_total_ten(fake_result) -> None:
    result,_,_=fake_result
    assert all(sum(values.values())==10 for values in result["resolution_status_distribution"].values())


def test_source_distributions_total_ten(fake_result) -> None:
    result,_,_=fake_result
    assert all(sum(values.values())==10 for values in result["resolution_source_distribution"].values())


def test_fallback_and_authority_safety_counters(fake_result) -> None:
    result,_,_=fake_result
    assert result["fallback_mutation_count"]==0
    assert result["illegal_candidate_accepted_count"]==0
    assert result["unexpected_dimension_authority_count"]==0


def test_per_case_artifact_has_no_source_body(fake_result) -> None:
    result,_,_=fake_result
    assert all("body" not in case and "source" not in case for case in result["cases"])


def test_scientific_status_transition_is_artifact_only(fake_result) -> None:
    result,_,_=fake_result
    assert result["scientific_status_before"]=="UNTOUCHED_PREREGISTERED_RESOLVER_HOLDOUT"
    assert result["scientific_status_after"]=="EVALUATED_PREREGISTERED_RESOLVER_HOLDOUT"
    assert json.loads((runner.BATCH_ROOT/"manifest.json").read_text())["validation_status"]=="NOT_RUN"
