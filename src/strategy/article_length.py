"""Editorial article length values."""

from enum import Enum


class ArticleLength(str, Enum):
    """Describe the target editorial length of an article."""

    VERY_SHORT = "VERY_SHORT"
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"
