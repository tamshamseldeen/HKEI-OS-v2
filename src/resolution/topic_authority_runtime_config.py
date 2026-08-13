"""Request-local operational configuration for Topic authority."""

from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_pilot_stop_decision import TopicAuthorityPilotStopDecision


class TopicAuthorityRuntimeConfig:
    """Explicit, auditable mode source; SHADOW is the safe default and kill switch."""

    def __init__(self, value: str | ResolverAuthorityMode | None = None) -> None:
        self._mode = self.parse(value)

    @staticmethod
    def parse(value: str | ResolverAuthorityMode | None) -> ResolverAuthorityMode:
        if value is None:
            return ResolverAuthorityMode.SHADOW
        if isinstance(value, ResolverAuthorityMode):
            return value
        if not isinstance(value, str):
            raise ValueError("resolver_authority_mode must be a string or ResolverAuthorityMode")
        try:
            return ResolverAuthorityMode(value)
        except ValueError as error:
            raise ValueError("invalid resolver_authority_mode") from error

    def resolve(self) -> ResolverAuthorityMode:
        """Read the effective mode for this request; no caller-side caching."""
        return self._mode

    def set_mode(self, value: str | ResolverAuthorityMode) -> ResolverAuthorityMode:
        """Apply an explicit operational configuration update."""
        self._mode = self.parse(value)
        return self._mode

    def apply_stop_signal(self, signal: TopicAuthorityPilotStopDecision | None) -> ResolverAuthorityMode:
        """Apply the existing evaluator's explicit SHADOW recommendation."""
        if signal is not None and signal.should_stop:
            if signal.recommended_mode is not ResolverAuthorityMode.SHADOW:
                raise ValueError("a stop signal must recommend SHADOW")
            self._mode = ResolverAuthorityMode.SHADOW
        return self._mode
