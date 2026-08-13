from dataclasses import fields
import pytest

from src.resolution import (
    InMemoryTopicAuthorityObservationSink, NoOpTopicAuthorityObservationSink,
    ResolverAuthorityMode, TopicAuthorityObservation, TopicAuthorityObservationSink,
)
from tests.topic_authority_operational_fixtures import observation


def test_protocol_accepts_sink(): assert isinstance(InMemoryTopicAuthorityObservationSink(), TopicAuthorityObservationSink)
def test_sanitized_observation_recorded():
    sink = InMemoryTopicAuthorityObservationSink(); item = observation(); sink.record(item); assert sink.observations == (item,)
def test_duplicate_fingerprint_is_idempotent():
    sink = InMemoryTopicAuthorityObservationSink(); sink.record(observation()); sink.record(observation()); assert len(sink.observations) == 1
def test_distinct_fingerprints_recorded():
    sink = InMemoryTopicAuthorityObservationSink(); sink.record(observation()); sink.record(observation(decision_fingerprint="other")); assert len(sink.observations) == 2
def test_none_identity_is_not_assumed_duplicate():
    sink = InMemoryTopicAuthorityObservationSink(); sink.record(observation(decision_fingerprint=None)); sink.record(observation(decision_fingerprint=None)); assert len(sink.observations) == 2
def test_observation_has_no_source_fields():
    names = {f.name for f in fields(TopicAuthorityObservation)}
    assert not names & {"article", "body", "source", "prompt", "request", "response", "api_key", "authorization", "reasoning"}
@pytest.mark.parametrize("needle", ["body", "prompt", "api_key", "authorization", "chain_of_thought"])
def test_sink_contract_excludes_sensitive_field(needle): assert needle not in {f.name for f in fields(TopicAuthorityObservation)}
def test_shadow_observation_supported():
    sink = InMemoryTopicAuthorityObservationSink(); sink.record(observation(authority_mode=ResolverAuthorityMode.SHADOW)); assert len(sink.observations) == 1
def test_limited_observation_supported():
    sink = InMemoryTopicAuthorityObservationSink(); sink.record(observation()); assert len(sink.observations) == 1
def test_noop_retains_nothing(): assert NoOpTopicAuthorityObservationSink().record(observation()) is None
@pytest.mark.parametrize("sink", [InMemoryTopicAuthorityObservationSink(), NoOpTopicAuthorityObservationSink()])
def test_invalid_observation_rejected(sink):
    with pytest.raises(ValueError): sink.record("raw source")
