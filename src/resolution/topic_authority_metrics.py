"""Immutable counter snapshots for the limited Topic authority pilot."""

from dataclasses import dataclass, fields


def _validate_nonnegative_integers(instance: object) -> None:
    for field in fields(instance):
        value = getattr(instance, field.name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field.name} must be a non-negative integer")


@dataclass(frozen=True)
class TopicAuthorityMetrics:
    """Provider-neutral operational counter snapshot."""

    articles_processed: int = 0
    topic_adjudication_requested: int = 0
    provider_calls: int = 0
    valid_adjudications: int = 0
    resolver_adjudicated_accepted: int = 0
    authoritative_topic_overrides: int = 0
    deterministic_topic_preserved: int = 0
    fallbacks: int = 0
    review_required_decisions: int = 0
    authority_blocked_by_policy: int = 0
    provider_failures: int = 0
    candidate_violations: int = 0
    fingerprint_failures: int = 0
    provider_validation_failures: int = 0
    max_consecutive_provider_validation_failures: int = 0

    def __post_init__(self) -> None:
        _validate_nonnegative_integers(self)
        if self.authoritative_topic_overrides > self.resolver_adjudicated_accepted:
            raise ValueError("authoritative overrides cannot exceed accepted resolutions")
        if self.resolver_adjudicated_accepted > self.valid_adjudications:
            raise ValueError("accepted resolutions cannot exceed valid adjudications")
        if self.valid_adjudications > self.provider_calls:
            raise ValueError("valid adjudications cannot exceed provider calls")
        if self.provider_calls > self.articles_processed:
            raise ValueError("provider calls cannot exceed processed articles")
        if self.provider_validation_failures > self.provider_calls:
            raise ValueError("provider validation failures cannot exceed provider calls")


@dataclass(frozen=True)
class TopicAuthoritySafetyMetrics:
    """Human-audited safety counter snapshot and supplied precision."""

    audited_override_count: int = 0
    audited_correct_override_count: int = 0
    audited_incorrect_override_count: int = 0
    override_precision: float | None = None
    rollback_count: int = 0
    authority_contract_violation_count: int = 0
    accepted_candidate_violation_count: int = 0
    accepted_fingerprint_violation_count: int = 0
    format_authority_violation_count: int = 0
    reader_intent_authority_violation_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "audited_override_count", "audited_correct_override_count",
            "audited_incorrect_override_count", "rollback_count",
            "authority_contract_violation_count",
            "accepted_candidate_violation_count", "accepted_fingerprint_violation_count",
            "format_authority_violation_count", "reader_intent_authority_violation_count",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.override_precision is not None and (
            isinstance(self.override_precision, bool)
            or not isinstance(self.override_precision, (int, float))
            or not 0.0 <= self.override_precision <= 1.0
        ):
            raise ValueError("override_precision must be between 0 and 1 or None")
        if (
            self.audited_correct_override_count + self.audited_incorrect_override_count
            > self.audited_override_count
        ):
            raise ValueError("audited outcomes cannot exceed audited overrides")
