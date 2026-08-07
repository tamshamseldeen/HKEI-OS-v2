"""Validation tests for the immutable Batch 02 unseen dataset."""

from hashlib import sha256
import json
import os
from pathlib import Path
import socket

import pytest


BATCH_ROOT = Path(__file__).resolve().parents[1] / "benchmark" / "batch_02"
BATCH_01_ROOT = BATCH_ROOT.parent / "batch_01"
EXPECTED_IDS = tuple(f"{case_id:03d}" for case_id in range(11, 21))
EXPECTED_SOURCE_NAMES = (
    "اليوم السابع",
    "العربية",
    "الشرق",
    "BBC",
    "اليوم السابع",
    "العربية",
    "الشرق",
    "BBC",
    "اليوم السابع",
    "الشرق",
)
EXPECTED_URLS = (
    "https://www.youm7.com/story/2026/8/7/egypt-wheat-silos-capacity-expansion/6981237",
    "https://www.alarabiya.net/saudi-space-agency-satellite-launch-2026",
    "https://asharq.com/business/ev-market-growth-battery-tech-2026/",
    "https://www.bbc.com/arabic/articles/c112x005520a",
    "https://www.youm7.com/story/2026/8/7/egypt-digital-tax-system-expansion/6981238",
    "https://www.alarabiya.net/aviation-industry-global-recovery-report",
    "https://asharq.com/markets/crypto-regulations-sec-global-standard/",
    "https://www.bbc.com/arabic/articles/c334x009921b",
    "https://www.youm7.com/story/2026/8/7/cairo-international-book-fair-preparations/6981239",
    "https://asharq.com/economy/global-semiconductor-supply-chain-expansion/",
)
EXPECTED_LABELS = (
    ("011", "GOVERNMENT", "STANDARD_NEWS", "GET_UPDATE"),
    ("012", "SCIENCE", "STANDARD_NEWS", "GET_UPDATE"),
    ("013", "TECHNOLOGY", "ANALYSIS", "UNDERSTAND_IMPACT"),
    ("014", "WORLD", "STANDARD_NEWS", "GET_UPDATE"),
    ("015", "GOVERNMENT", "SERVICE", "KNOW_ACTION"),
    ("016", "BUSINESS", "STANDARD_NEWS", "GET_UPDATE"),
    ("017", "ECONOMY", "STANDARD_NEWS", "GET_UPDATE"),
    ("018", "SCIENCE", "STANDARD_NEWS", "GET_UPDATE"),
    ("019", "CULTURE", "STANDARD_NEWS", "GET_UPDATE"),
    ("020", "TECHNOLOGY", "STANDARD_NEWS", "GET_UPDATE"),
)


def _load_json(filename: str) -> dict[str, object]:
    """Load one Batch 02 UTF-8 JSON document."""
    return json.loads((BATCH_ROOT / filename).read_text(encoding="utf-8"))


def _parse_source(path: Path) -> dict[str, str]:
    """Parse the fixed benchmark Markdown format without production code."""
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


def _batch_01_digest() -> str:
    """Calculate a path-sensitive digest of frozen Batch 01 inputs."""
    digest = sha256()
    input_paths = [
        BATCH_01_ROOT / "manifest.json",
        *[
            BATCH_01_ROOT / f"{case_id:03d}" / "source.md"
            for case_id in range(1, 11)
        ],
    ]
    for path in input_paths:
        digest.update(path.relative_to(BATCH_01_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_manifest_has_exact_ordered_cases_and_no_category() -> None:
    """Register exactly cases 011 through 020 in supplied order without labels."""
    manifest = _load_json("manifest.json")
    cases = manifest["cases"]

    assert len(cases) == 10
    assert tuple(case["id"] for case in cases) == EXPECTED_IDS
    assert tuple(case["source_name"] for case in cases) == EXPECTED_SOURCE_NAMES
    assert tuple(case["source_file"] for case in cases) == tuple(
        f"{case_id}/source.md" for case_id in EXPECTED_IDS
    )
    assert all(set(case) == {"id", "source_name", "source_file"} for case in cases)
    assert "category" not in json.dumps(manifest).lower()


def test_every_source_exists_and_preserves_required_metadata() -> None:
    """Preserve non-empty source text, source names, URLs, and case IDs."""
    manifest = _load_json("manifest.json")

    for index, case in enumerate(manifest["cases"]):
        source_path = BATCH_ROOT / case["source_file"]
        assert source_path.is_file()
        source = _parse_source(source_path)
        assert source["title"]
        assert source["body"]
        assert source["id"] == EXPECTED_IDS[index]
        assert source["source_name"] == EXPECTED_SOURCE_NAMES[index]
        assert source["source_name"] == case["source_name"]
        assert source["source_url"] == EXPECTED_URLS[index]
        assert "Benchmark Category" not in source["raw"]


def test_expected_json_contains_exact_preregistered_labels() -> None:
    """Store exactly ten human expectations and no expected risk labels."""
    expected = _load_json("expected.json")
    expectations = expected["expectations"]

    assert set(expected) == {"expectations"}
    assert len(expectations) == 10
    assert tuple(
        (
            item["id"],
            item["topic"],
            item["editorial_format"],
            item["reader_intent"],
        )
        for item in expectations
    ) == EXPECTED_LABELS
    assert all(
        set(item) == {"id", "topic", "editorial_format", "reader_intent"}
        for item in expectations
    )
    assert "risk" not in json.dumps(expected).lower()


def test_dataset_has_only_registered_inputs_and_validation_reports() -> None:
    """Keep Batch 02 free of generated articles and editorial review files."""
    files = tuple(
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*")
        if path.is_file()
    )

    assert len(files) == 16
    assert not any("article" in path.lower() for path in files)
    assert not any("review" in path.lower() for path in files)
    assert set(path for path in files if "validation" in path) == {
        "validation.json",
        "validation.md",
    }
    assert set(path for path in files if "topic_error_analysis" in path) == {
        "topic_error_analysis.json",
        "topic_error_analysis.md",
    }


def test_existing_batch_01_is_unchanged() -> None:
    """Protect the complete pre-existing Batch 01 artifact tree byte-for-byte."""
    assert _batch_01_digest() == (
        "a023907907003075a1f43f3e91cb5ed9152e2e85357f04b3f41f7ca94a073e2d"
    )


def test_validation_requires_no_api_network_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read the entire dataset with external and environment access disabled."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    manifest = _load_json("manifest.json")
    expected = _load_json("expected.json")
    sources = [
        _parse_source(BATCH_ROOT / case["source_file"])
        for case in manifest["cases"]
    ]
    assert len(sources) == len(expected["expectations"]) == 10
