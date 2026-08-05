"""Normalized source model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedSource:
    """Represent source material in the normalized intake format.

    Attributes:
        title: Title of the source material.
        body: Body content of the source material.
        source_name: Name of the source.
        source_url: URL where the source material was published.
        published_at: Publication timestamp supplied by the source.
        language: Language of the source material.
        country: Country associated with the source material.
        author: Author of the source material.
        images: Image references associated with the source material.
        attachments: Attachment references associated with the source material.
        category: Category supplied with the source material.
        tags: Tags supplied with the source material.
    """

    title: str
    body: str
    source_name: str
    source_url: str | None = None
    published_at: str | None = None
    language: str | None = None
    country: str | None = None
    author: str | None = None
    images: tuple[str, ...] = ()
    attachments: tuple[str, ...] = ()
    category: str | None = None
    tags: tuple[str, ...] = ()
