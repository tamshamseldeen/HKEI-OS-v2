"""Provider-neutral semantic adjudication token usage telemetry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticAdjudicationUsage:
    """Store trusted token counts without retaining provider usage objects."""

    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None

    def __post_init__(self) -> None:
        self._require_non_negative_integer("input_tokens", self.input_tokens)
        self._require_non_negative_integer("output_tokens", self.output_tokens)
        if self.reasoning_tokens is not None:
            self._require_non_negative_integer(
                "reasoning_tokens", self.reasoning_tokens
            )
            if self.reasoning_tokens > self.output_tokens:
                raise ValueError("reasoning_tokens must not exceed output_tokens")

    @staticmethod
    def _require_non_negative_integer(name: str, value: object) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
