"""Validation for raw source fields."""


class SourceValidator:
    """Validate raw source fields before normalization."""

    def validate(
        self,
        *,
        title: str | None,
        body: str | None,
        source_name: str | None,
        source_url: str | None = None,
        language: str | None = None,
    ) -> tuple[str, ...]:
        """Return validation error codes for raw source fields.

        Args:
            title: Raw source title.
            body: Raw source body.
            source_name: Raw source name.
            source_url: Optional raw source URL.
            language: Optional source language code.

        Returns:
            Validation error codes in the defined order.
        """
        errors: list[str] = []

        if title is None:
            errors.append("MISSING_TITLE")
        if body is None:
            errors.append("MISSING_BODY")
        if source_name is None:
            errors.append("MISSING_SOURCE_NAME")

        if title is not None and not title.strip():
            errors.append("EMPTY_TITLE")
        if body is not None and not body.strip():
            errors.append("EMPTY_BODY")
        if source_name is not None and not source_name.strip():
            errors.append("EMPTY_SOURCE_NAME")

        if source_url is not None and not source_url.startswith(
            ("http://", "https://")
        ):
            errors.append("MALFORMED_URL")

        if language is not None and language not in ("ar", "en"):
            errors.append("UNSUPPORTED_LANGUAGE")

        return tuple(errors)
