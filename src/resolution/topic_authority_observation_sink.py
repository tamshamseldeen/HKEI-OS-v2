"""Provider-neutral sinks for sanitized Topic-authority observations."""

from typing import Protocol, runtime_checkable

from .topic_authority_observation import TopicAuthorityObservation


@runtime_checkable
class TopicAuthorityObservationSink(Protocol):
    def record(self, observation: TopicAuthorityObservation) -> None:
        """Record one sanitized observation, or raise on failure."""


class InMemoryTopicAuthorityObservationSink:
    """Test-safe idempotent sink with no external I/O or source payloads."""

    def __init__(self) -> None:
        self._observations: list[TopicAuthorityObservation] = []
        self._identities: set[str] = set()

    @property
    def observations(self) -> tuple[TopicAuthorityObservation, ...]:
        return tuple(self._observations)

    def record(self, observation: TopicAuthorityObservation) -> None:
        if not isinstance(observation, TopicAuthorityObservation):
            raise ValueError("observation must be a TopicAuthorityObservation")
        identity = observation.decision_fingerprint
        if identity is not None and identity in self._identities:
            return
        self._observations.append(observation)
        if identity is not None:
            self._identities.add(identity)


class NoOpTopicAuthorityObservationSink:
    """Production-safe default that retains and emits nothing."""

    def record(self, observation: TopicAuthorityObservation) -> None:
        if not isinstance(observation, TopicAuthorityObservation):
            raise ValueError("observation must be a TopicAuthorityObservation")
