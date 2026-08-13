"""Controlled downstream-only Topic authority canary orchestration."""

from dataclasses import replace

from src.adjudication.semantic_adjudication_provider import SemanticAdjudicationProvider
from src.resolution.editorial_resolution_source import EditorialResolutionSource
from src.resolution.limited_topic_authority_applicator import LimitedTopicAuthorityApplicator
from src.resolution.limited_topic_authority_config import LimitedTopicAuthorityConfig
from src.resolution.resolver_authority_mode import ResolverAuthorityMode
from src.resolution.topic_authority_contract_validator import TopicAuthorityContractValidator
from src.resolution.topic_authority_metrics import TopicAuthorityMetrics, TopicAuthoritySafetyMetrics
from src.resolution.topic_authority_observation_builder import TopicAuthorityObservationBuilder
from src.resolution.topic_authority_pilot_stop_evaluator import TopicAuthorityPilotStopEvaluator
from src.resolution.topic_authority_provider_failure_category import (
    TopicAuthorityProviderFailureCategory,
)

from .controlled_topic_authority_canary_result import ControlledTopicAuthorityCanaryResult
from .limited_editorial_resolver_shadow_workflow import LimitedEditorialResolverShadowWorkflow
from src.resolution.controlled_topic_authority_consumer import (
    ControlledTopicAuthorityConsumerAdapter,
    TopicAuthorityConsumerRoute,
)
from src.resolution.operational_topic_authority_canary import OperationalTopicAuthorityCanary
from src.resolution.topic_authority_observation_sink import TopicAuthorityObservationSink
from src.resolution.topic_authority_pilot_stop_decision import TopicAuthorityPilotStopDecision
from src.resolution.topic_authority_runtime_config import TopicAuthorityRuntimeConfig


class ControlledTopicAuthorityCanaryWorkflow:
    """Wire existing shadow and authority components without enabling rollout."""

    def __init__(
        self,
        *,
        provider: SemanticAdjudicationProvider,
        config: LimitedTopicAuthorityConfig | None = None,
        shadow_workflow: LimitedEditorialResolverShadowWorkflow | None = None,
        applicator: LimitedTopicAuthorityApplicator | None = None,
        observation_builder: TopicAuthorityObservationBuilder | None = None,
        contract_validator: TopicAuthorityContractValidator | None = None,
        stop_evaluator: TopicAuthorityPilotStopEvaluator | None = None,
        runtime_config: TopicAuthorityRuntimeConfig | None = None,
        observation_sink: TopicAuthorityObservationSink | None = None,
        consumer_adapter: ControlledTopicAuthorityConsumerAdapter | None = None,
    ) -> None:
        if not isinstance(provider, SemanticAdjudicationProvider):
            raise ValueError("provider must implement SemanticAdjudicationProvider")
        if config is not None and not isinstance(config, LimitedTopicAuthorityConfig):
            raise ValueError("config must be LimitedTopicAuthorityConfig or None")
        self.provider = provider
        self.config = config or LimitedTopicAuthorityConfig()
        self.shadow_workflow = shadow_workflow or LimitedEditorialResolverShadowWorkflow(
            provider=provider
        )
        self.applicator = applicator or LimitedTopicAuthorityApplicator()
        self.observation_builder = observation_builder or TopicAuthorityObservationBuilder()
        self.contract_validator = contract_validator or TopicAuthorityContractValidator()
        self.stop_evaluator = stop_evaluator or TopicAuthorityPilotStopEvaluator()
        self.runtime_config = runtime_config or TopicAuthorityRuntimeConfig(
            self.config.authority_mode
        )
        self.operational_canary = OperationalTopicAuthorityCanary(
            self.runtime_config, observation_sink, consumer_adapter
        )

    def analyze(
        self,
        *,
        candidate_compliant: bool = True,
        fingerprint_valid: bool = True,
        response_valid: bool | None = None,
        provider_available: bool = True,
        provider_failure_category: TopicAuthorityProviderFailureCategory | None = None,
        operational_metrics: TopicAuthorityMetrics | None = None,
        safety_metrics: TopicAuthoritySafetyMetrics | None = None,
        **article_fields,
    ) -> ControlledTopicAuthorityCanaryResult:
        """Run upstream once, then apply request-local authority policy."""
        effective_config = replace(
            self.config, authority_mode=self.runtime_config.resolve()
        )
        shadow = self.shadow_workflow.analyze(**article_fields)
        actual_response_valid = shadow.response_valid if response_valid is None else response_valid
        decision = self.applicator.apply(
            shadow.resolution_result,
            effective_config,
            candidate_compliant,
            fingerprint_valid,
            actual_response_valid,
            provider_available,
        )
        violations = self.contract_validator.validate(
            decision,
            effective_config,
            candidate_compliant,
            fingerprint_valid,
            actual_response_valid,
            provider_available,
        )
        effective_decision = decision
        if violations:
            effective_decision = replace(
                decision,
                authoritative_topic=decision.deterministic_topic,
                authority_applied=False,
                authority_source=EditorialResolutionSource.DETERMINISTIC_V1,
                block_reasons=(),
            )
        observation = self.observation_builder.build(
            effective_decision,
            effective_config.authority_mode,
            topic_adjudication_requested=shadow.adjudication_decision.topic_required,
            provider_called=shadow.provider_called,
            provider_valid=actual_response_valid,
            candidate_compliant=candidate_compliant,
            fingerprint_valid=fingerprint_valid,
            provider_failure_category=provider_failure_category,
        )
        stop_decision = None
        if (operational_metrics is None) != (safety_metrics is None):
            raise ValueError("operational_metrics and safety_metrics must be supplied together")
        if operational_metrics is not None and safety_metrics is not None:
            stop_decision = self.stop_evaluator.evaluate(
                operational_metrics, safety_metrics, effective_config
            )
        return ControlledTopicAuthorityCanaryResult(
            shadow_workflow_result=shadow,
            resolution_result=shadow.resolution_result,
            authority_decision=effective_decision,
            authority_observation=observation,
            contract_violations=violations,
            stop_decision=stop_decision,
            deterministic_topic=effective_decision.deterministic_topic,
            resolved_topic=effective_decision.resolved_topic,
            authoritative_topic=effective_decision.authoritative_topic,
            authority_applied=effective_decision.authority_applied,
            authority_source=effective_decision.authority_source,
            warnings=effective_decision.warnings,
        )

    def analyze_operational(
        self,
        *,
        route: TopicAuthorityConsumerRoute = TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH,
        stop_signal: TopicAuthorityPilotStopDecision | None = None,
        **analysis_fields,
    ):
        """Run once and return only the sanitized operational consumer boundary."""
        self.runtime_config.apply_stop_signal(stop_signal)
        result = self.analyze(**analysis_fields)
        return self.operational_canary.execute(
            result.authority_decision,
            result.authority_observation,
            route,
            stop_signal=None,
        )

    def apply_to_resolution(
        self,
        resolution_result,
        *,
        candidate_compliant: bool,
        fingerprint_valid: bool,
        response_valid: bool,
        provider_available: bool,
    ):
        """Apply mode downstream without rerunning any upstream component."""
        return self.applicator.apply(
            resolution_result,
            replace(self.config, authority_mode=self.runtime_config.resolve()),
            candidate_compliant,
            fingerprint_valid,
            response_valid,
            provider_available,
        )
