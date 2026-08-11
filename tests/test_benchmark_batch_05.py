"""Integrity tests for the immutable Batch 05 advanced-risk holdout."""

from hashlib import sha256
import json
import os
from pathlib import Path
import socket

import pytest


BATCH_ROOT = Path(__file__).resolve().parents[1] / "benchmark" / "batch_05"
EXPECTED_IDS = tuple(f"{case_id:03d}" for case_id in range(41, 51))
RAW_SOURCE_SHA256 = (
    "ebf0c104ca993ecfb2cb52fdda84c40165c08f9b59461beb93f6f33fc3766def"
)
BATCH_04_DIGEST = (
    "2eedd5b9c1e81acbbd9b403fdd603833735bd5460a9e7ea2bd2ecb734a6f56d9"
)
EXPECTED_SOURCE_NAMES = (
    "العربية",
    "العربية",
    "العربية",
    "الشرق",
    "الشرق",
    "الشرق",
    "الشرق",
    "الشرق",
    "العربية",
    "الشرق",
)
EXPECTED_SOURCE_SHA256 = {
    "041": "55f9c266746e908359bc8ee1c90bfd0113dd82b85d168acaa05fcf0e8c024bb4",
    "042": "497b2edf0ed8ad491bda3624125cc3bd544d3076b6b46f63b1b0d500cef9fa13",
    "043": "264e53ac5dbdc9dd93df044f2df157b18d6c8f789f4388558b926ff28cfed0c1",
    "044": "71ad59cb43264ef72331f492e0e6ce160dd643b6cb9c4d81ac13e05930c8efee",
    "045": "e444b5a1912c3ec42687adf67eb6f4a171443bcc40a7063cab77eb66d58d0ff8",
    "046": "5b4486ddcfb55ec7257b39929e4ac1eaa2b78106be974f334893c9c31b0d2c9b",
    "047": "ff099a07a2f645de154cc3ecad4490ab6cae700edd758bbc6dc7026aed6c1caf",
    "048": "cbd6a3afc69b388d2b0bfe563fb6f102c4d28cc0f99c5f1ca2cfaade47927213",
    "049": "97f63adf87ca1f37f9ce43740b22093c458e7f69a37cf8fb7ec1aac1e4f57591",
    "050": "b1db99db831c4bb233de398f7c23560d0ad5c6e41180aee80268cf9c7f96c6b3",
}
EXPECTED_EDITORIAL_LABELS = (
    ("041", "POLITICS", "STANDARD_NEWS", "GET_UPDATE"),
    ("042", "CRIME", "STANDARD_NEWS", "GET_UPDATE"),
    ("043", "POLITICS", "STANDARD_NEWS", "GET_UPDATE"),
    ("044", "WORLD", "ANALYSIS", "UNDERSTAND_IMPACT"),
    ("045", "WORLD", "EXPLAINER", "UNDERSTAND_EVENT"),
    ("046", "SCIENCE", "ANALYSIS", "UNDERSTAND_IMPACT"),
    ("047", "POLITICS", "ANALYSIS", "UNDERSTAND_IMPACT"),
    ("048", "WORLD", "STANDARD_NEWS", "GET_UPDATE"),
    ("049", "ECONOMY", "STANDARD_NEWS", "GET_UPDATE"),
    ("050", "CRIME", "STANDARD_NEWS", "GET_UPDATE"),
)
EXPECTED_RISK_ANNOTATIONS = (
    ("041", "HIGH", True, True, "SECURITY", "Potential cross-border attack; possibility must not become confirmed event."),
    ("042", "HIGH", True, True, "CRIMINAL_LEGAL", "Criminal conviction plus disputed family claim; attribution must be preserved."),
    ("043", "HIGH", True, False, "LEGAL_POLITICAL", "Executive action with constitutional and judicial context."),
    ("044", "HIGH", False, False, "WAR_SECURITY", "War and defense analysis; avoid unsupported operational inference."),
    ("045", "HIGH", False, False, "MILITARY_DEFENSE", "Military restructuring and unmanned systems."),
    ("046", "HIGH", False, True, "BIOSECURITY", "Dual-use biological research; descriptive reporting must not become procedural enablement."),
    ("047", "HIGH", True, True, "POLITICAL_LEGAL", "Government scrutiny, discrimination allegations, protests, and institutional conflict."),
    ("048", "HIGH", True, True, "INTELLIGENCE_SECURITY", "Intelligence estimate; explicitly not a confirmed attack decision."),
    ("049", "LOW", True, True, "ECONOMIC_DATA", "Economic data and estimates; distinguish reported rate from economist estimate."),
    ("050", "HIGH", True, False, "VIOLENT_CRIME", "Fatal school shooting with casualty reporting attributed to local media/broadcaster."),
)


def _load_json(filename: str) -> dict[str, object]:
    return json.loads((BATCH_ROOT / filename).read_text(encoding="utf-8"))


def _parse_source(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    title, remainder = text.split("\n\n# Body\n\n", 1)
    body, metadata = remainder.split("\n\n# Metadata\n\n", 1)
    metadata_lines = metadata.strip().splitlines()
    return {
        "title": title.removeprefix("# Title\n\n"),
        "body": body,
        "source_name": metadata_lines[1],
        "source_url": metadata_lines[4],
        "id": metadata_lines[7],
        "raw": text,
    }


def _tree_digest(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_manifest_registers_exactly_cases_041_through_050() -> None:
    manifest = _load_json("manifest.json")
    cases = manifest["cases"]
    assert set(manifest) == {"cases"}
    assert len(cases) == 10
    assert tuple(case["id"] for case in cases) == EXPECTED_IDS
    assert tuple(case["source_name"] for case in cases) == EXPECTED_SOURCE_NAMES
    assert tuple(case["source_file"] for case in cases) == tuple(
        f"{case_id}/source.md" for case_id in EXPECTED_IDS
    )
    assert all(set(case) == {"id", "source_name", "source_file"} for case in cases)


def test_source_text_metadata_and_raw_registration_are_frozen() -> None:
    assert RAW_SOURCE_SHA256 == (
        "ebf0c104ca993ecfb2cb52fdda84c40165c08f9b59461beb93f6f33fc3766def"
    )
    for case_id, source_name in zip(EXPECTED_IDS, EXPECTED_SOURCE_NAMES):
        path = BATCH_ROOT / case_id / "source.md"
        source = _parse_source(path)
        assert source["id"] == case_id
        assert source["source_name"] == source_name
        assert source["title"]
        assert source["body"]
        assert source["source_url"].startswith("https://")
        assert "category" not in source["raw"].casefold()
        assert sha256(path.read_bytes()).hexdigest() == EXPECTED_SOURCE_SHA256[case_id]


def test_editorial_expectations_are_exactly_preregistered() -> None:
    expected = _load_json("expected.json")
    expectations = expected["expectations"]
    assert set(expected) == {"expectations"}
    assert len(expectations) == 10
    assert tuple(
        (
            item["id"], item["topic"], item["editorial_format"],
            item["reader_intent"],
        )
        for item in expectations
    ) == EXPECTED_EDITORIAL_LABELS
    assert all(
        set(item) == {"id", "topic", "editorial_format", "reader_intent"}
        for item in expectations
    )
    assert sum(len(item) - 1 for item in expectations) == 30


def test_human_risk_annotations_are_exactly_preregistered() -> None:
    document = _load_json("human_risk_annotations.json")
    annotations = document["annotations"]
    required = {
        "id", "expected_risk_band", "attribution_required",
        "uncertainty_present", "sensitive_context", "notes",
    }
    assert set(document) == {"annotations"}
    assert len(annotations) == 10
    assert all(set(item) == required for item in annotations)
    assert tuple(
        (
            item["id"], item["expected_risk_band"],
            item["attribution_required"], item["uncertainty_present"],
            item["sensitive_context"], item["notes"],
        )
        for item in annotations
    ) == EXPECTED_RISK_ANNOTATIONS


def test_batch_contains_only_registered_inputs_and_authorized_outputs() -> None:
    files = {
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*")
        if path.is_file()
    }
    assert files == {
        "manifest.json",
        "expected.json",
        "human_risk_annotations.json",
        "editorial_validation.json",
        "editorial_validation.md",
        "editorial_generalization_analysis.json",
        "editorial_generalization_analysis.md",
        "adjudication_gate_shadow.json",
        "adjudication_gate_shadow.md",
        "adjudication_gate_error_analysis.json",
        "adjudication_gate_error_analysis.md",
            "adjudication_hint_coverage_analysis.json",
            "adjudication_hint_coverage_analysis.md",
            "adjudication_request_shadow.json",
            "adjudication_request_shadow.md",
            "adjudication_shadow_plumbing.json",
            "adjudication_shadow_plumbing.md",
            "openai_live_shadow_5case.json",
            "openai_live_shadow_5case.md",
            "openai_live_shadow_5case_error_analysis.json",
            "openai_live_shadow_5case_error_analysis.md",
            *(f"{case_id}/source.md" for case_id in EXPECTED_IDS),
        }
    assert not any(
        term in path.casefold()
        for path in files
        for term in ("diagnostic", "article")
    )


def test_batch_04_and_its_quarantine_remain_unchanged() -> None:
    batch_04 = BATCH_ROOT.parent / "batch_04"
    assert _tree_digest(batch_04) == BATCH_04_DIGEST
    assert (batch_04 / "RISK_ANNOTATIONS_QUARANTINED.md").is_file()


def test_production_modules_do_not_import_batch_05_risk_annotations() -> None:
    source_root = BATCH_ROOT.parents[1] / "src"
    assert all(
        "human_risk_annotations" not in path.read_text(encoding="utf-8")
        for path in source_root.rglob("*.py")
    )


def test_registration_uses_no_api_network_or_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)
    assert len(_load_json("manifest.json")["cases"]) == 10
    assert len(_load_json("expected.json")["expectations"]) == 10
    assert len(_load_json("human_risk_annotations.json")["annotations"]) == 10
