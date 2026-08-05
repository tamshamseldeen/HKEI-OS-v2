"""Normalization of accepted source fields."""

import re

from .normalized_source import NormalizedSource


class SourceNormalizer:
    """Normalize accepted source fields into a NormalizedSource."""

    def normalize(
        self,
        *,
        title: str,
        body: str,
        source_name: str,
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
        """Normalize accepted fields without validating their content.

        Args:
            title: Accepted source title.
            body: Accepted source body.
            source_name: Accepted source name.
            source_url: Optional source URL.
            published_at: Optional publication timestamp.
            language: Optional source language code.
            country: Optional country associated with the source.
            author: Optional source author.
            images: Image references associated with the source.
            attachments: Attachment references associated with the source.
            category: Optional source category.
            tags: Tags associated with the source.

        Returns:
            A NormalizedSource containing the normalized values.
        """
        normalized_body = body.replace("\r\n", "\n").replace("\r", "\n")
        normalized_body = "\n".join(
            line.strip() for line in normalized_body.split("\n")
        ).strip()
        normalized_body = re.sub(r"\n{3,}", "\n\n", normalized_body)

        return NormalizedSource(
            title=" ".join(title.split()),
            body=normalized_body,
            source_name=" ".join(source_name.split()),
            source_url=self._normalize_optional_string(source_url),
            published_at=self._normalize_optional_string(published_at),
            language=self._normalize_optional_string(language),
            country=self._normalize_optional_string(country),
            author=self._normalize_optional_string(author),
            images=self._normalize_tuple(images),
            attachments=self._normalize_tuple(attachments),
            category=self._normalize_optional_string(category),
            tags=self._normalize_tuple(tags),
        )

    @staticmethod
    def _normalize_optional_string(value: str | None) -> str | None:
        """Trim an optional string and convert an empty result to None.

        Args:
            value: Optional string to normalize.

        Returns:
            The trimmed string, or None when absent or empty.
        """
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
        """Trim tuple items and remove empty results.

        Args:
            values: String tuple to normalize.

        Returns:
            A tuple containing the remaining trimmed strings.
        """
        return tuple(item.strip() for item in values if item.strip())
