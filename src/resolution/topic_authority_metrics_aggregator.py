"""Pure immutable aggregation for limited Topic authority telemetry."""

from .editorial_resolution_status import EditorialResolutionStatus
from .resolver_authority_mode import ResolverAuthorityMode
from .topic_authority_audit_record import TopicAuthorityAuditRecord, TopicAuthorityAuditStatus
from .topic_authority_block_reason import TopicAuthorityBlockReason
from .topic_authority_contract_violation import TopicAuthorityContractViolation
from .topic_authority_metrics import TopicAuthorityMetrics, TopicAuthoritySafetyMetrics
from .topic_authority_observation import TopicAuthorityObservation


class TopicAuthorityMetricsAggregator:
    """Aggregate explicit immutable observations and independent audits."""

    _POLICY_REASONS = {
        TopicAuthorityBlockReason.MODE_SHADOW,
        TopicAuthorityBlockReason.REVIEW_REQUIRED,
        TopicAuthorityBlockReason.AMBIGUITY_REMAINS,
        TopicAuthorityBlockReason.PROVIDER_CONFIDENCE_TOO_LOW,
    }

    def aggregate_operational(
        self,
        observations: tuple[TopicAuthorityObservation, ...],
    ) -> TopicAuthorityMetrics:
        self._validate_observations(observations)
        return TopicAuthorityMetrics(
            articles_processed=len(observations),
            topic_adjudication_requested=sum(item.topic_adjudication_requested for item in observations),
            provider_calls=sum(item.provider_called for item in observations),
            valid_adjudications=sum(item.provider_valid for item in observations),
            resolver_adjudicated_accepted=sum(
                item.resolution_status is EditorialResolutionStatus.ADJUDICATED_ACCEPTED
                for item in observations
            ),
            authoritative_topic_overrides=sum(
                item.authority_applied
                and item.authority_mode is ResolverAuthorityMode.LIMITED_TOPIC_AUTHORITY
                for item in observations
            ),
            deterministic_topic_preserved=sum(not item.authority_applied for item in observations),
            fallbacks=sum(
                item.resolution_status is EditorialResolutionStatus.FALLBACK_ACCEPTED
                for item in observations
            ),
            review_required_decisions=sum(item.review_required for item in observations),
            authority_blocked_by_policy=sum(
                not item.authority_applied
                and bool(self._POLICY_REASONS.intersection(item.block_reasons))
                for item in observations
            ),
            provider_failures=sum(
                item.provider_failure_category is not None for item in observations
            ),
            candidate_violations=sum(not item.candidate_compliant for item in observations),
            fingerprint_failures=sum(not item.fingerprint_valid for item in observations),
            provider_validation_failures=sum(
                item.provider_called and not item.provider_valid for item in observations
            ),
            max_consecutive_provider_validation_failures=self._max_consecutive_validation_failures(
                observations
            ),
        )

    def aggregate_safety(
        self,
        observations: tuple[TopicAuthorityObservation, ...],
        audit_records: tuple[TopicAuthorityAuditRecord, ...] = (),
        contract_violations: tuple[TopicAuthorityContractViolation, ...] = (),
        rollback_count: int = 0,
    ) -> TopicAuthoritySafetyMetrics:
        self._validate_observations(observations)
        if not isinstance(audit_records, tuple) or any(
            not isinstance(item, TopicAuthorityAuditRecord) for item in audit_records
        ):
            raise ValueError("audit_records must be a tuple of TopicAuthorityAuditRecord")
        if not isinstance(contract_violations, tuple) or any(
            not isinstance(item, TopicAuthorityContractViolation) for item in contract_violations
        ):
            raise ValueError("contract_violations must be a tuple of TopicAuthorityContractViolation")
        if isinstance(rollback_count, bool) or not isinstance(rollback_count, int) or rollback_count < 0:
            raise ValueError("rollback_count must be a non-negative integer")
        identities = [item.decision_fingerprint for item in audit_records]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate audit decision fingerprint")

        applied_fingerprints = {
            observation_fingerprint
            for observation_fingerprint in self._applied_fingerprints(observations)
            if observation_fingerprint is not None
        }
        for record in audit_records:
            if record.decision_fingerprint not in applied_fingerprints:
                raise ValueError("audit record must refer to an authority-applied decision")
        completed = tuple(
            item for item in audit_records
            if item.review_status is TopicAuthorityAuditStatus.COMPLETED
        )
        correct = sum(item.human_reviewed_correctness is True for item in completed)
        incorrect = sum(item.human_reviewed_correctness is False for item in completed)
        precision = correct / len(completed) if completed else None
        return TopicAuthoritySafetyMetrics(
            audited_override_count=len(completed),
            audited_correct_override_count=correct,
            audited_incorrect_override_count=incorrect,
            override_precision=precision,
            rollback_count=rollback_count,
            authority_contract_violation_count=len(contract_violations),
            accepted_candidate_violation_count=sum(
                item is TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_CANDIDATE
                for item in contract_violations
            ),
            accepted_fingerprint_violation_count=sum(
                item is TopicAuthorityContractViolation.AUTHORITY_APPLIED_WITH_INVALID_FINGERPRINT
                for item in contract_violations
            ),
            format_authority_violation_count=sum(
                item is TopicAuthorityContractViolation.FORMAT_AUTHORITY_VIOLATION
                for item in contract_violations
            ),
            reader_intent_authority_violation_count=sum(
                item is TopicAuthorityContractViolation.READER_INTENT_AUTHORITY_VIOLATION
                for item in contract_violations
            ),
        )

    @staticmethod
    def _applied_fingerprints(
        observations: tuple[TopicAuthorityObservation, ...],
    ) -> tuple[str | None, ...]:
        return tuple(
            item.decision_fingerprint
            for item in observations if item.authority_applied
        )

    @staticmethod
    def _validate_observations(
        observations: tuple[TopicAuthorityObservation, ...],
    ) -> None:
        if not isinstance(observations, tuple) or any(
            not isinstance(item, TopicAuthorityObservation) for item in observations
        ):
            raise ValueError("observations must be a tuple of TopicAuthorityObservation")
        if any(item.provider_used and not item.provider_valid for item in observations):
            raise ValueError("provider-used observations must be valid")

    @staticmethod
    def _max_consecutive_validation_failures(
        observations: tuple[TopicAuthorityObservation, ...],
    ) -> int:
        maximum = current = 0
        for item in observations:
            if item.provider_called and not item.provider_valid:
                current += 1
                maximum = max(maximum, current)
            else:
                current = 0
        return maximum
