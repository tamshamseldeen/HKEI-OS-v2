"""Editorial article depth values."""

from enum import Enum


class ArticleDepth(str, Enum):
    """Describe the target editorial depth of an article."""

    UPDATE = "UPDATE"
    STANDARD = "STANDARD"
    EXPLAINED = "EXPLAINED"
    DETAILED = "DETAILED"
