"""Stable errors for provider-agnostic LLM generation."""


class GenerationError(RuntimeError):
    """Report a stable LLM generation error.

    Attributes:
        code: Stable generation error code.
        original_exception: Original provider exception when available.
    """

    def __init__(
        self,
        code: str,
        original_exception: Exception | None = None,
    ) -> None:
        """Initialize a generation error.

        Args:
            code: Stable generation error code.
            original_exception: Original exception retained as internal context.
        """
        self.code = code
        self.original_exception = original_exception
        super().__init__(code)
