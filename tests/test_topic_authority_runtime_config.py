import pytest

from src.resolution import ResolverAuthorityMode, TopicAuthorityRuntimeConfig
from src.resolution.topic_authority_pilot_stop_decision import (
    TopicAuthorityPilotStopDecision, TopicAuthorityPilotStopReason,
)


def stop():
    return TopicAuthorityPilotStopDecision(True, (TopicAuthorityPilotStopReason.AUTHORITY_CONTRACT_VIOLATION,), ResolverAuthorityMode.SHADOW)


def test_missing_config_is_shadow(): assert TopicAuthorityRuntimeConfig().resolve() is ResolverAuthorityMode.SHADOW
def test_explicit_shadow(): assert TopicAuthorityRuntimeConfig("SHADOW").resolve() is ResolverAuthorityMode.SHADOW
def test_explicit_limited(): assert TopicAuthorityRuntimeConfig("LIMITED_TOPIC_AUTHORITY").resolve() is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
def test_enum_input(): assert TopicAuthorityRuntimeConfig(ResolverAuthorityMode.SHADOW).resolve() is ResolverAuthorityMode.SHADOW
@pytest.mark.parametrize("value", ["", "limited", "LIMITED", "unknown", 1, True])
def test_invalid_values_rejected(value):
    with pytest.raises(ValueError): TopicAuthorityRuntimeConfig(value)
def test_invalid_does_not_create_limited():
    config = TopicAuthorityRuntimeConfig()
    with pytest.raises(ValueError): config.set_mode("bad")
    assert config.resolve() is ResolverAuthorityMode.SHADOW
def test_explicit_update_to_limited():
    config = TopicAuthorityRuntimeConfig(); config.set_mode("LIMITED_TOPIC_AUTHORITY")
    assert config.resolve() is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
def test_kill_switch_updates_to_shadow():
    config = TopicAuthorityRuntimeConfig("LIMITED_TOPIC_AUTHORITY"); config.apply_stop_signal(stop())
    assert config.resolve() is ResolverAuthorityMode.SHADOW
def test_kill_switch_has_no_stale_limited_state():
    config = TopicAuthorityRuntimeConfig("LIMITED_TOPIC_AUTHORITY"); config.apply_stop_signal(stop())
    assert config.resolve() is config.resolve() is ResolverAuthorityMode.SHADOW
def test_non_stop_does_not_mutate():
    signal = TopicAuthorityPilotStopDecision(False, (), None)
    config = TopicAuthorityRuntimeConfig("LIMITED_TOPIC_AUTHORITY"); config.apply_stop_signal(signal)
    assert config.resolve() is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
def test_parse_is_deterministic(): assert TopicAuthorityRuntimeConfig.parse("SHADOW") is TopicAuthorityRuntimeConfig.parse("SHADOW")
def test_no_global_shared_state():
    a, b = TopicAuthorityRuntimeConfig("LIMITED_TOPIC_AUTHORITY"), TopicAuthorityRuntimeConfig()
    a.set_mode("SHADOW"); assert b.resolve() is ResolverAuthorityMode.SHADOW
