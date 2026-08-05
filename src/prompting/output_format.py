"""Supported generation output format values."""

from enum import Enum


class OutputFormat(str, Enum):
    """Describe the required format of generated editorial content."""

    MARKDOWN_ARTICLE = "MARKDOWN_ARTICLE"
