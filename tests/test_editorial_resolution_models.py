"""Contract tests for limited editorial Resolver domain models."""

from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path

import pytest

from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.resolution import (
    EditorialDimensionResolution,
    EditorialResolutionDimension,
    EditorialResolutionResult,
    EditorialResolutionSource,
    EditorialResolutionStatus,
    EditorialResolutionWarning,
)
from src.topic.topic import Topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _dimension(
    dimension=EditorialResolutionDimension.TOPIC,
    value=Topic.SCIENCE,
    status=EditorialResolutionStatus.DETERMINISTIC_ACCEPTED,
    source=EditorialResolutionSource.DETERMINISTIC_V1,
    confidence="HIGH",
    confidence_source=EditorialResolutionSource.DETERMINISTIC_V1,
    ambiguity=False,
    review_required=False,
    warnings=(),
):
    return EditorialDimensionResolution(
        dimension=dimension,
        value=value,
        status=status,
        source=source,
        confidence=confidence,
        confidence_source=confidence_source,
        ambiguity=ambiguity,
        review_required=review_required,
        warnings=warnings,
    )


def _result() -> EditorialResolutionResult:
    return EditorialResolutionResult(
        topic_resolution=_dimension(),
        format_resolution=_dimension(
            EditorialResolutionDimension.FORMAT,
            EditorialFormat.STANDARD_NEWS,
        ),
        reader_intent_resolution=_dimension(
            EditorialResolutionDimension.READER_INTENT,
            ReaderIntent.GET_UPDATE,
        ),
        review_required=False,
        warnings=(),
        provider_used=False,
        input_fingerprint="sha256:fixture",
    )


def test_resolution_status_has_exact_contract_values() -> None:
    assert tuple(item.value for item in EditorialResolutionStatus) == (
        "DETERMINISTIC_ACCEPTED",
        "ADJUDICATED_ACCEPTED",
        "FALLBACK_ACCEPTED",
        "UNRESOLVED",
        "REVIEW_REQUIRED",
    )


def test_resolution_source_has_exact_contract_values() -> None:
    assert tuple(item.value for item in EditorialResolutionSource) == (
        "DETERMINISTIC_V1", "FORMAT_V2_SHADOW", "ADJUDICATION", "FALLBACK", "NONE",
    )


def test_warning_contract_contains_specification_symbols() -> None:
    required = {
        "ADJUDICATION_AMBIGUITY_REMAINS", "FORMAT_FALLBACK_USED",
        "FORMAT_V1_V2_DISAGREEMENT", "PROVIDER_UNAVAILABLE",
        "INVALID_ADJUDICATION_RESPONSE", "FINGERPRINT_MISMATCH",
        "ILLEGAL_ADJUDICATED_CANDIDATE", "FORMAT_UNRESOLVED", "TOPIC_UNRESOLVED",
    }
    assert required <= {item.value for item in EditorialResolutionWarning}
    assert len(EditorialResolutionWarning) == len({item.value for item in EditorialResolutionWarning})


def test_dimension_and_final_result_are_frozen() -> None:
    dimension = _dimension()
    result = _result()
    with pytest.raises(FrozenInstanceError):
        dimension.value = Topic.HEALTH
    with pytest.raises(FrozenInstanceError):
        result.provider_used = True


@pytest.mark.parametrize("value", tuple(Topic))
def test_every_topic_is_representable(value: Topic) -> None:
    assert _dimension(value=value).value is value


@pytest.mark.parametrize("value", tuple(EditorialFormat))
def test_all_twelve_formats_are_representable(value: EditorialFormat) -> None:
    result = _dimension(EditorialResolutionDimension.FORMAT, value)
    assert len(EditorialFormat) == 12
    assert result.value is value


@pytest.mark.parametrize("value", tuple(ReaderIntent))
def test_every_reader_intent_is_representable(value: ReaderIntent) -> None:
    result = _dimension(EditorialResolutionDimension.READER_INTENT, value)
    assert result.value is value


@pytest.mark.parametrize(
    ("status", "source"),
    [
        (EditorialResolutionStatus.ADJUDICATED_ACCEPTED, EditorialResolutionSource.DETERMINISTIC_V1),
        (EditorialResolutionStatus.DETERMINISTIC_ACCEPTED, EditorialResolutionSource.ADJUDICATION),
        (EditorialResolutionStatus.FALLBACK_ACCEPTED, EditorialResolutionSource.DETERMINISTIC_V1),
        (EditorialResolutionStatus.UNRESOLVED, EditorialResolutionSource.FALLBACK),
    ],
)
def test_status_source_mismatches_are_rejected(status, source) -> None:
    with pytest.raises(ValueError):
        _dimension(status=status, source=source)


def test_adjudicated_and_unresolved_status_source_contracts() -> None:
    adjudicated = _dimension(
        status=EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
        source=EditorialResolutionSource.ADJUDICATION,
        confidence_source=EditorialResolutionSource.ADJUDICATION,
    )
    unresolved = _dimension(
        value=None,
        status=EditorialResolutionStatus.UNRESOLVED,
        source=EditorialResolutionSource.NONE,
        confidence=None,
        confidence_source=EditorialResolutionSource.NONE,
        review_required=True,
        warnings=(EditorialResolutionWarning.TOPIC_UNRESOLVED,),
    )
    assert adjudicated.source is EditorialResolutionSource.ADJUDICATION
    assert unresolved.value is None


def test_topic_cannot_use_format_v2_shadow() -> None:
    with pytest.raises(ValueError, match="Topic resolution"):
        _dimension(
            status=EditorialResolutionStatus.REVIEW_REQUIRED,
            source=EditorialResolutionSource.FORMAT_V2_SHADOW,
            confidence_source=EditorialResolutionSource.FORMAT_V2_SHADOW,
            review_required=True,
        )


def test_reader_intent_cannot_use_adjudication() -> None:
    with pytest.raises(ValueError, match="Reader Intent"):
        _dimension(
            EditorialResolutionDimension.READER_INTENT,
            ReaderIntent.GET_UPDATE,
            EditorialResolutionStatus.ADJUDICATED_ACCEPTED,
            EditorialResolutionSource.ADJUDICATION,
            confidence_source=EditorialResolutionSource.ADJUDICATION,
        )


def test_format_v2_shadow_is_representable_only_as_diagnostic_model_state() -> None:
    result = _dimension(
        EditorialResolutionDimension.FORMAT,
        EditorialFormat.EXPLAINER,
        EditorialResolutionStatus.REVIEW_REQUIRED,
        EditorialResolutionSource.FORMAT_V2_SHADOW,
        confidence_source=EditorialResolutionSource.FORMAT_V2_SHADOW,
        review_required=True,
    )
    assert result.source is EditorialResolutionSource.FORMAT_V2_SHADOW
    assert result.review_required is True


def test_ambiguity_and_review_are_independent_from_accepted_value() -> None:
    ambiguous = _dimension(ambiguity=True, review_required=True)
    reviewed = _dimension(ambiguity=False, review_required=True)
    assert ambiguous.status is EditorialResolutionStatus.DETERMINISTIC_ACCEPTED
    assert ambiguous.value is Topic.SCIENCE and reviewed.value is Topic.SCIENCE
    assert ambiguous.ambiguity is True and reviewed.ambiguity is False


def test_review_required_status_cannot_contradict_review_flag() -> None:
    with pytest.raises(ValueError, match="requires review_required"):
        _dimension(status=EditorialResolutionStatus.REVIEW_REQUIRED)


def test_top_level_review_flag_remains_explicit() -> None:
    result = _result()
    assert result.review_required is False
    assert all(not item.review_required for item in (
        result.topic_resolution, result.format_resolution, result.reader_intent_resolution,
    ))


def test_confidence_requires_explicit_provenance() -> None:
    with pytest.raises(ValueError, match="explicit provenance"):
        _dimension(confidence="HIGH", confidence_source=EditorialResolutionSource.NONE)
    with pytest.raises(ValueError, match="missing confidence"):
        _dimension(confidence=None, confidence_source=EditorialResolutionSource.DETERMINISTIC_V1)


def test_model_fields_exclude_sensitive_source_benchmark_and_provider_config() -> None:
    names = {item.name for model in (EditorialDimensionResolution, EditorialResolutionResult) for item in fields(model)}
    forbidden = {
        "api_key", "authorization", "provider_config", "raw_response", "raw_prompt",
        "raw_source", "source_body", "article_body", "benchmark", "case_id", "expected_label",
    }
    assert names.isdisjoint(forbidden)


def test_models_have_no_resolver_behavior_gate_openai_or_v2_execution_dependency() -> None:
    model_files = (
        "editorial_resolution_status.py", "editorial_resolution_source.py",
        "editorial_resolution_warning.py", "editorial_dimension_resolution.py",
        "editorial_resolution_result.py",
    )
    source = "\n".join(
        (PROJECT_ROOT / "src/resolution" / name).read_text(encoding="utf-8")
        for name in model_files
    )
    assert "def resolve(" not in source
    assert "adjudication_gate" not in source.casefold()
    assert "openai" not in source.casefold()
    assert "EditorialFormatV2Classifier" not in source


def test_canonical_contract_aligns_with_specification_without_parsing_prose() -> None:
    assert EditorialResolutionStatus.REVIEW_REQUIRED.value == "REVIEW_REQUIRED"
    assert EditorialResolutionSource.FORMAT_V2_SHADOW.value == "FORMAT_V2_SHADOW"
    assert EditorialResolutionWarning.FORMAT_FALLBACK_USED.value == "FORMAT_FALLBACK_USED"
    signature = inspect.signature(EditorialResolutionResult)
    assert tuple(signature.parameters) == (
        "topic_resolution", "format_resolution", "reader_intent_resolution",
        "review_required", "warnings", "provider_used", "input_fingerprint",
    )
