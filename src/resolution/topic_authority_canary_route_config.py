"""Immutable availability configuration for the internal Topic canary route."""

from dataclasses import dataclass

from .controlled_topic_authority_consumer import TopicAuthorityConsumerRoute


@dataclass(frozen=True)
class TopicAuthorityCanaryRouteConfig:
    """Enable only route availability; authority mode remains a separate contract."""

    route_enabled: bool = False
    session_identifier: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.route_enabled, bool):
            raise ValueError("route_enabled must be a boolean")
        if self.session_identifier is not None and (
            not isinstance(self.session_identifier, str)
            or not self.session_identifier.strip()
            or self.session_identifier != self.session_identifier.strip()
        ):
            raise ValueError("session_identifier must be a normalized non-empty string or None")

    def resolve_route(self) -> TopicAuthorityConsumerRoute:
        return (
            TopicAuthorityConsumerRoute.INTERNAL_TOPIC_AUTHORITY_CANARY_PATH
            if self.route_enabled
            else TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH
        )
