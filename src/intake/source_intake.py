"""Public source intake service."""

from .normalized_source import NormalizedSource
from .source_normalizer import SourceNormalizer
from .source_validator import SourceValidator


class SourceValidationError(ValueError):
    """Report ordered validation errors from source intake.

    Attributes:
        errors: Validation error codes in validator order.
    """

    def __init__(self, errors: tuple[str, ...]) -> None:
        """Initialize the source validation error.

        Args:
            errors: Validation error codes in validator order.
        """
        self.errors: tuple[str, ...] = errors
        super().__init__(f"Source validation failed: {', '.join(errors)}")


class SourceIntake:
    """Validate and normalize source fields through one entry point."""

    def __init__(
        self,
        validator: SourceValidator | None = None,
        normalizer: SourceNormalizer | None = None,
    ) -> None:
        """Initialize the source intake service.

        Args:
            validator: Validator to use, or None to create the default.
            normalizer: Normalizer to use, or None to create the default.
        """
        self._validator = validator if validator is not None else SourceValidator()
        self._normalizer = (
            normalizer if normalizer is not None else SourceNormalizer()
        )

    def process(
        self,
        *,
        title: str | None,
        body: str | None,
        source_name: str | None,
        source_url: str | None = None,
        published_at: str | None = None,
        language: str | None = None,
        country: str | None = None,
        author: str | None = None,
        images: tuple[str, ...] = (),
        attachments: tuple[str, ...] = (),
        category: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> NormalizedSource:
        """Validate source fields and return their normalized representation.

        Args:
            title: Raw source title.
            body: Raw source body.
            source_name: Raw source name.
            source_url: Optional raw source URL.
            published_at: Optional publication timestamp.
            language: Optional source language code.
            country: Optional country associated with the source.
            author: Optional source author.
            images: Image references associated with the source.
            attachments: Attachment references associated with the source.
            category: Optional source category.
            tags: Tags associated with the source.

        Returns:
            The normalized source object.

        Raises:
            SourceValidationError: If source validation returns any errors.
        """
        errors = self._validator.validate(
            title=title,
            body=body,
            source_name=source_name,
            source_url=source_url,
            language=language,
        )
        if errors:
            raise SourceValidationError(errors)

        assert title is not None
        assert body is not None
        assert source_name is not None

        return self._normalizer.normalize(
            title=title,
            body=body,
            source_name=source_name,
            source_url=source_url,
            published_at=published_at,
            language=language,
            country=country,
            author=author,
            images=images,
            attachments=attachments,
            category=category,
            tags=tags,
        )
