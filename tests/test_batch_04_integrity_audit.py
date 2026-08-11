"""Integrity tests for the quarantined Batch 04 risk annotations."""

from hashlib import sha256
import json
import os
from pathlib import Path
import socket

import pytest

from examples.run_benchmark_batch_02_validation import parse_source, read_manifest


BATCH_ROOT = Path(__file__).resolve().parents[1] / "benchmark" / "batch_04"
EXPECTED_IDS = tuple(f"{case_id:03d}" for case_id in range(31, 41))
FROZEN_INPUT_DIGEST = (
    "20c08c974d31c3bb762437e6a3970a2b31dd16431cf43084cd7470f791f38224"
)
RISK_ANNOTATION_DIGEST = (
    "aa3d0b9616368d449e4bb60d1f71cbf923556da089553468b42d3797969b4ad6"
)
EDITORIAL_OUTPUT_DIGESTS = {
    "editorial_validation.json": (
        "52d489ca09e45948fc9601bc24df6fe28d945256da492d4cf82df153c5b6d519"
    ),
    "editorial_validation.md": (
        "e94511a5fb19e3068f66920ebd5d5baf4f06d5ef6bdd79cc184033fabe29f293"
    ),
}
REQUIRED_COMPATIBILITY_TERMS = {
    "031": ("هجوم", "أمني"),
    "032": ("إدانة", "جنائي"),
    "033": ("دستوري", "تنفيذي"),
    "034": ("حرب", "دفاع"),
    "035": ("عسكري", "مسيرة"),
    "036": ("بحث", "بيولوجي"),
    "037": ("احتجاج", "تمييز"),
    "038": ("روسيا", "الناتو"),
    "039": ("خبير اقتصادي", "تقدير"),
    "040": ("إطلاق نار", "مدرسة"),
}


def _load_json(filename: str) -> dict[str, object]:
    return json.loads((BATCH_ROOT / filename).read_text(encoding="utf-8"))


def _digest(paths: list[Path]) -> str:
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(BATCH_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_exactly_ten_cases_are_audited_in_registered_order() -> None:
    audit = _load_json("integrity_audit.json")
    assert audit["batch"] == "batch_04"
    assert audit["case_count"] == 10
    assert tuple(case["id"] for case in audit["cases"]) == EXPECTED_IDS


def test_audit_joins_persisted_titles_topics_and_annotation_contexts() -> None:
    audit = _load_json("integrity_audit.json")
    expected = {
        item["id"]: item for item in _load_json("expected.json")["expectations"]
    }
    annotations = {
        item["id"]: item
        for item in _load_json("human_risk_annotations.json")["annotations"]
    }
    for case in audit["cases"]:
        source = parse_source(BATCH_ROOT / case["id"] / "source.md")
        assert case["source_title"] == source.title
        assert case["expected_topic"] == expected[case["id"]]["topic"]
        assert (
            case["sensitive_context"]
            == annotations[case["id"]]["sensitive_context"]
        )
        assert case["audit_reason"]


def test_deterministic_text_checks_confirm_explicit_incompatibility() -> None:
    """Require scenario-bearing terms and the explicit frozen audit decision."""
    audit = _load_json("integrity_audit.json")
    for case in audit["cases"]:
        title = case["source_title"].casefold()
        terms = REQUIRED_COMPATIBILITY_TERMS[case["id"]]
        textual_compatibility = all(term.casefold() in title for term in terms)
        assert textual_compatibility is False
        assert case["annotation_corresponds_to_source"] is False
    assert audit["compatible_annotations"] == 0
    assert audit["incompatible_annotations"] == 10


def test_quarantine_marker_states_every_required_restriction() -> None:
    marker = BATCH_ROOT / "RISK_ANNOTATIONS_QUARANTINED.md"
    assert marker.is_file()
    text = marker.read_text(encoding="utf-8")
    assert "does not correspond to the Batch 04 source corpus" in text
    assert "must not be used for risk, attribution, or uncertainty validation" in text
    assert "retained only for audit and history" in text
    assert "A separate future batch will host the intended advanced-risk corpus" in text


def test_frozen_sources_expectations_and_annotations_are_unchanged() -> None:
    paths = [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[
            BATCH_ROOT / case["source_file"]
            for case in read_manifest(BATCH_ROOT)
        ],
    ]
    assert _digest(paths) == FROZEN_INPUT_DIGEST
    assert sha256(
        (BATCH_ROOT / "human_risk_annotations.json").read_bytes()
    ).hexdigest() == RISK_ANNOTATION_DIGEST


def test_editorial_validation_history_is_unchanged() -> None:
    for filename, expected_digest in EDITORIAL_OUTPUT_DIGESTS.items():
        assert sha256((BATCH_ROOT / filename).read_bytes()).hexdigest() == (
            expected_digest
        )


def test_audit_artifacts_have_no_classifier_dependencies() -> None:
    contents = (
        (BATCH_ROOT / "integrity_audit.json").read_text(encoding="utf-8")
        + (BATCH_ROOT / "integrity_audit.md").read_text(encoding="utf-8")
    )
    assert "Classifier" not in contents
    assert "src." not in contents


def test_audit_reads_use_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert _load_json("integrity_audit.json")["case_count"] == 10
