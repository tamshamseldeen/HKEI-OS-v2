"""Immutable result for controlled Topic authority canary wiring."""

from dataclasses import dataclass

from src.resolution.editorial_resolution_result import EditorialResolutionResult
from src.resolution.editorial_resolution_source import EditorialResolutionSource
from src.resolution.editorial_resolution_warning import EditorialResolutionWarning
from src.resolution.topic_authority_contract_violation import TopicAuthorityContractViolation
from src.resolution.topic_authority_decision import TopicAuthorityDecision
from src.resolution.topic_authority_observation import TopicAuthorityObservation
from src.resolution.topic_authority_pilot_stop_decision import TopicAuthorityPilotStopDecision
from src.topic.topic import Topic

from .limited_editorial_resolver_shadow_result import LimitedEditorialResolverShadowResult


@dataclass(frozen=True)
class ControlledTopicAuthorityCanaryResult:
    """Expose sanitized authority provenance without persisting source content."""

    shadow_workflow_result: LimitedEditorialResolverShadowResult
    resolution_result: EditorialResolutionResult
    authority_decision: TopicAuthorityDecision
    authority_observation: TopicAuthorityObservation
    contract_violations: tuple[TopicAuthorityContractViolation, ...]
    stop_decision: TopicAuthorityPilotStopDecision | None
    deterministic_topic: Topic
    resolved_topic: Topic | None
    authoritative_topic: Topic
    authority_applied: bool
    authority_source: EditorialResolutionSource
    warnings: tuple[EditorialResolutionWarning, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.shadow_workflow_result, LimitedEditorialResolverShadowResult):
            raise ValueError("shadow_workflow_result has an invalid type")
        if self.resolution_result is not self.shadow_workflow_result.resolution_result:
            raise ValueError("resolution_result must be the shadow workflow resolution")
        if not isinstance(self.authority_decision, TopicAuthorityDecision):
            raise ValueError("authority_decision has an invalid type")
        if not isinstance(self.authority_observation, TopicAuthorityObservation):
            raise ValueError("authority_observation has an invalid type")
        if not isinstance(self.contract_violations, tuple) or any(
            not isinstance(item, TopicAuthorityContractViolation)
            for item in self.contract_violations
        ):
            raise ValueError("contract_violations has an invalid type")
        if self.stop_decision is not None and not isinstance(
            self.stop_decision, TopicAuthorityPilotStopDecision
        ):
            raise ValueError("stop_decision has an invalid type")
        if not isinstance(self.deterministic_topic, Topic):
            raise ValueError("deterministic_topic must be a Topic")
        if self.resolved_topic is not None and not isinstance(self.resolved_topic, Topic):
            raise ValueError("resolved_topic must be a Topic or None")
        if not isinstance(self.authoritative_topic, Topic):
            raise ValueError("authoritative_topic must be a Topic")
        if not isinstance(self.authority_applied, bool):
            raise ValueError("authority_applied must be a boolean")
        if not isinstance(self.authority_source, EditorialResolutionSource):
            raise ValueError("authority_source has an invalid type")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, EditorialResolutionWarning) for item in self.warnings
        ):
            raise ValueError("warnings has an invalid type")
        if self.contract_violations and (
            self.authority_applied
            or self.authoritative_topic is not self.deterministic_topic
            or self.authority_source is not EditorialResolutionSource.DETERMINISTIC_V1
        ):
            raise ValueError("contract violations require deterministic authority preservation")
