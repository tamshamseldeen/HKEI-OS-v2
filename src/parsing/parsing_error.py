"""Stable errors for deterministic generated-article parsing."""


class ParsingError(RuntimeError):
    """Report a stable generated-article parsing error.

    Attributes:
        code: Stable parsing error code.
        original_exception: Original exception when available.
    """

    def __init__(
        self,
        code: str,
        original_exception: Exception | None = None,
    ) -> None:
        """Initialize a parsing error.

        Args:
            code: Stable parsing error code.
            original_exception: Original exception retained as internal context.
        """
        self.code = code
        self.original_exception = original_exception
        super().__init__(code)
