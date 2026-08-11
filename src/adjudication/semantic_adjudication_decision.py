"""Immutable semantic adjudication gate decision contract."""

from dataclasses import dataclass

from .adjudication_scope import AdjudicationScope


@dataclass(frozen=True)
class SemanticAdjudicationDecision:
    """Store an adjudication scope and its ordered diagnostic evidence."""

    scope: AdjudicationScope

    trigger_signals: tuple[str, ...]

    topic_required: bool
    format_required: bool

    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
