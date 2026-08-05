"""Tests for stable LLM generation errors."""

from src.generation.generation_error import GenerationError


def test_generation_error_stores_code_and_original_exception() -> None:
    """Store stable code and internal original exception unchanged."""
    original = ValueError("private provider details")
    error = GenerationError("PROVIDER_RESPONSE_INVALID", original)

    assert error.code == "PROVIDER_RESPONSE_INVALID"
    assert error.original_exception is original
    assert str(error) == "PROVIDER_RESPONSE_INVALID"
    assert "private provider details" not in str(error)


def test_generation_error_accepts_no_original_exception() -> None:
    """Default the internal original exception to None."""
    error = GenerationError("PROVIDER_NOT_CONFIGURED")

    assert error.original_exception is None
    assert str(error) == error.code
