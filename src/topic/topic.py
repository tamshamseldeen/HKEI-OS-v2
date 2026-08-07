"""Supported primary editorial topic values."""

from enum import Enum


class Topic(str, Enum):
    """Describe what source material is primarily about."""

    POLITICS = "POLITICS"
    ECONOMY = "ECONOMY"
    BUSINESS = "BUSINESS"
    TECHNOLOGY = "TECHNOLOGY"
    SPORTS = "SPORTS"
    GOVERNMENT = "GOVERNMENT"
    WEATHER = "WEATHER"
    HEALTH = "HEALTH"
    CULTURE = "CULTURE"
    SCIENCE = "SCIENCE"
    EDUCATION = "EDUCATION"
    CRIME = "CRIME"
    ENTERTAINMENT = "ENTERTAINMENT"
    WORLD = "WORLD"
    GENERAL = "GENERAL"
