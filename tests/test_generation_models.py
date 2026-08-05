"""Tests for provider-agnostic LLM generation models."""

from dataclasses import FrozenInstanceError, fields

import pytest

from src.generation.finish_reason import FinishReason
from src.generation.generation_configuration import GenerationConfiguration
from src.generation.generation_result import GenerationResult


def test_finish_reason_values_are_exact() -> None:
    """Expose every finish reason in specification order."""
    assert tuple(reason.value for reason in FinishReason) == (
        "COMPLETED",
        "LENGTH_LIMIT",
        "CONTENT_FILTERED",
        "TOOL_CALL",
        "STOPPED",
        "UNKNOWN",
    )


def test_generation_configuration_stores_fields_in_order() -> None:
    """Store configuration fields unchanged in specification order."""
    metadata = (("workflow_id", "workflow-1"), ("env", "test"))
    configuration = GenerationConfiguration(
        model="model-id",
        max_output_tokens=800,
        temperature=0.2,
        timeout_seconds=30.0,
        request_metadata=metadata,
    )

    assert configuration.model == "model-id"
    assert configuration.max_output_tokens == 800
    assert configuration.temperature == 0.2
    assert configuration.timeout_seconds == 30.0
    assert configuration.request_metadata is metadata
    assert isinstance(configuration.request_metadata, tuple)
    assert tuple(field.name for field in fields(configuration)) == (
        "model",
        "max_output_tokens",
        "temperature",
        "timeout_seconds",
        "request_metadata",
    )


def test_generation_configuration_is_immutable_and_accepts_none() -> None:
    """Accept no temperature and prevent configuration reassignment."""
    configuration = GenerationConfiguration("model-id", 800, None, 30.0, ())

    assert configuration.temperature is None
    with pytest.raises(FrozenInstanceError):
        configuration.model = "other"  # type: ignore[misc]


def test_generation_result_stores_fields_in_order() -> None:
    """Store normalized result fields unchanged in specification order."""
    warnings = ("OUTPUT_TRUNCATED", "OUTPUT_TRUNCATED")
    result = GenerationResult(
        content="raw output",
        provider_name="provider-id",
        model_name="model-id",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        finish_reason=FinishReason.LENGTH_LIMIT,
        request_id="request-1",
        warnings=warnings,
    )

    assert result.content == "raw output"
    assert result.provider_name == "provider-id"
    assert result.model_name == "model-id"
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.total_tokens == 150
    assert result.finish_reason is FinishReason.LENGTH_LIMIT
    assert result.request_id == "request-1"
    assert result.warnings is warnings
    assert isinstance(result.warnings, tuple)
    assert tuple(field.name for field in fields(result)) == (
        "content",
        "provider_name",
        "model_name",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "finish_reason",
        "request_id",
        "warnings",
    )


def test_generation_result_is_immutable_and_accepts_none() -> None:
    """Accept unavailable metadata and prevent result reassignment."""
    result = GenerationResult(
        "raw output",
        "provider-id",
        "model-id",
        None,
        None,
        None,
        FinishReason.UNKNOWN,
        None,
        (),
    )

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.total_tokens is None
    assert result.request_id is None
    with pytest.raises(FrozenInstanceError):
        result.content = "changed"  # type: ignore[misc]
