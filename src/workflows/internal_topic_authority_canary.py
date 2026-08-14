"""Internal-only opt-in entrypoint for the controlled Topic authority canary."""

from src.resolution.sanitized_topic_authority_canary_result import (
    SanitizedTopicAuthorityCanaryResult,
)
from src.resolution.topic_authority_canary_route_config import (
    TopicAuthorityCanaryRouteConfig,
)
from src.resolution.topic_authority_pilot_stop_decision import (
    TopicAuthorityPilotStopDecision,
)

from .controlled_topic_authority_canary_workflow import (
    ControlledTopicAuthorityCanaryWorkflow,
)


class InternalTopicAuthorityCanaryEntrypoint:
    """Separate INTERNAL_ONLY boundary; never registered as a default endpoint."""

    INTERNAL_ONLY = True

    def __init__(
        self,
        workflow: ControlledTopicAuthorityCanaryWorkflow,
        route_config: TopicAuthorityCanaryRouteConfig | None = None,
    ) -> None:
        if not isinstance(workflow, ControlledTopicAuthorityCanaryWorkflow):
            raise ValueError("workflow must be a ControlledTopicAuthorityCanaryWorkflow")
        if route_config is not None and not isinstance(
            route_config, TopicAuthorityCanaryRouteConfig
        ):
            raise ValueError("route_config must be a TopicAuthorityCanaryRouteConfig or None")
        self._workflow = workflow
        self._route_config = route_config or TopicAuthorityCanaryRouteConfig()

    @property
    def route_config(self) -> TopicAuthorityCanaryRouteConfig:
        return self._route_config

    def run_internal_topic_authority_canary(
        self,
        *,
        stop_signal: TopicAuthorityPilotStopDecision | None = None,
        **analysis_fields,
    ) -> SanitizedTopicAuthorityCanaryResult:
        """Run the safe boundary using the explicitly configured route availability."""
        return self._workflow.analyze_operational(
            route=self._route_config.resolve_route(),
            stop_signal=stop_signal,
            **analysis_fields,
        )
