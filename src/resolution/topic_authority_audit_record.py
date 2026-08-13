"""Minimal provider-neutral human audit record for Topic authority."""

from dataclasses import dataclass
from enum import Enum

from src.topic.topic import Topic


class TopicAuthorityAuditStatus(str, Enum):
    """Describe whether independent human review has completed."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class TopicAuthorityAuditRecord:
    """Record a sanitized human judgment without reviewer PII or source text."""

    decision_fingerprint: str
    authoritative_topic: Topic
    review_status: TopicAuthorityAuditStatus
    human_reviewed_correctness: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision_fingerprint, str) or not self.decision_fingerprint.strip():
            raise ValueError("decision_fingerprint must be a non-empty string")
        if not isinstance(self.authoritative_topic, Topic):
            raise ValueError("authoritative_topic must be a Topic")
        if not isinstance(self.review_status, TopicAuthorityAuditStatus):
            raise ValueError("review_status must be a TopicAuthorityAuditStatus")
        if self.human_reviewed_correctness is not None and not isinstance(
            self.human_reviewed_correctness, bool
        ):
            raise ValueError("human_reviewed_correctness must be a boolean or None")
        if (
            self.review_status is TopicAuthorityAuditStatus.PENDING
            and self.human_reviewed_correctness is not None
        ):
            raise ValueError("pending audits cannot have reviewed correctness")
        if (
            self.review_status is TopicAuthorityAuditStatus.COMPLETED
            and self.human_reviewed_correctness is None
        ):
            raise ValueError("completed audits require reviewed correctness")
