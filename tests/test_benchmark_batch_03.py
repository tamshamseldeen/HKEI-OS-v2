"""Integrity tests for the immutable Batch 03 unseen validation dataset."""

from hashlib import sha256
import json
import os
from pathlib import Path
import socket

import pytest


BATCH_ROOT = Path(__file__).resolve().parents[1] / "benchmark" / "batch_03"
EXPECTED_IDS = tuple(f"{case_id:03d}" for case_id in range(21, 31))
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
    "https://www.youm7.com/story/2026/8/7/egypt-new-administrative-capital-monorail/6981240",
    "https://www.alarabiya.net/business/gulf-economies-non-oil-growth-2026",
    "https://asharq.com/politics/us-china-trade-talks-tariffs-discussion/",
    "https://www.bbc.com/arabic/articles/c445x001122c",
    "https://www.youm7.com/story/2026/8/7/egypt-health-initiative-100-million-seha/6981241",
    "https://www.alarabiya.net/tech/cybersecurity-global-threats-ransomware-2026",
    "https://asharq.com/real-estate/middle-east-property-market-boom/",
    "https://www.bbc.com/arabic/articles/c556x002223d",
    "https://www.youm7.com/story/2026/8/7/egypt-higher-education-universities-ranking/6981242",
    "https://asharq.com/markets/natural-gas-prices-europe-winter-prep/",
)
EXPECTED_LABELS = (
    ("021", "GOVERNMENT", "STANDARD_NEWS", "GET_UPDATE"),
    ("022", "ECONOMY", "STANDARD_NEWS", "GET_UPDATE"),
    ("023", "POLITICS", "STANDARD_NEWS", "GET_UPDATE"),
    ("024", "HEALTH", "STANDARD_NEWS", "GET_UPDATE"),
    ("025", "HEALTH", "STANDARD_NEWS", "GET_UPDATE"),
    ("026", "TECHNOLOGY", "SERVICE", "KNOW_ACTION"),
    ("027", "ECONOMY", "STANDARD_NEWS", "GET_UPDATE"),
    ("028", "WEATHER", "STANDARD_NEWS", "GET_UPDATE"),
    ("029", "EDUCATION", "STANDARD_NEWS", "GET_UPDATE"),
    ("030", "ECONOMY", "STANDARD_NEWS", "GET_UPDATE"),
)
REGISTERED_BATCH_DIGEST = (
    "6fc29192f5bbb7cfd56f3645f01b71780d03ecdca601521d044c1b9766dbfe99"
)


def _load_json(filename: str) -> dict[str, object]:
    """Read one Batch 03 UTF-8 JSON document."""
    return json.loads((BATCH_ROOT / filename).read_text(encoding="utf-8"))


def _parse_source(path: Path) -> dict[str, str]:
    """Parse the fixed source format without production dependencies."""
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


def _digest(paths: list[Path], root: Path) -> str:
    """Return one deterministic path-sensitive digest."""
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_manifest_registers_exact_order_without_category() -> None:
    """Register exactly cases 021–030 in source order without category fields."""
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


def test_sources_exist_and_preserve_exact_metadata() -> None:
    """Preserve every supplied ID, source name, URL, title, and body."""
    cases = _load_json("manifest.json")["cases"]

    for index, case in enumerate(cases):
        path = BATCH_ROOT / case["source_file"]
        assert path.is_file()
        source = _parse_source(path)
        assert source["title"]
        assert source["body"]
        assert source["id"] == EXPECTED_IDS[index]
        assert source["source_name"] == EXPECTED_SOURCE_NAMES[index]
        assert source["source_name"] == case["source_name"]
        assert source["source_url"] == EXPECTED_URLS[index]
        assert "category" not in source["raw"].lower()


def test_expected_labels_are_exactly_preregistered() -> None:
    """Store ten expectation records containing exactly thirty human labels."""
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
    assert sum(len(item) - 1 for item in expectations) == 30


def test_batch_contains_only_registered_inputs_and_validation_reports() -> None:
    """Exclude generated articles and unrelated analysis output."""
    files = tuple(
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*")
        if path.is_file()
    )

    assert len(files) == 24
    assert set(files) == {
        "manifest.json",
        "expected.json",
        "contextual_full_validation.json",
        "contextual_full_validation.md",
        "compositional_context_analysis.json",
        "compositional_context_analysis.md",
        "compositional_semantic_diagnostic.json",
        "compositional_semantic_diagnostic.md",
        "semantic_topic_diagnostic.json",
        "semantic_topic_diagnostic.md",
        "expanded_semantic_diagnostic.json",
        "expanded_semantic_diagnostic.md",
        "semantic_full_validation.json",
        "semantic_full_validation.md",
        *(f"{case_id}/source.md" for case_id in EXPECTED_IDS),
    }
    assert not any(
        term in path.lower()
        for path in files
        for term in ("article", "report")
    )
    ordered_paths = [
        BATCH_ROOT / "manifest.json",
        BATCH_ROOT / "expected.json",
        *[BATCH_ROOT / f"{case_id}/source.md" for case_id in EXPECTED_IDS],
    ]
    assert _digest(ordered_paths, BATCH_ROOT) == REGISTERED_BATCH_DIGEST


def test_prior_batch_inputs_remain_unchanged() -> None:
    """Protect the registered Batch 01 and Batch 02 input material."""
    benchmark_root = BATCH_ROOT.parent
    batch_01 = benchmark_root / "batch_01"
    batch_02 = benchmark_root / "batch_02"
    batch_01_paths = [
        batch_01 / "manifest.json",
        *[batch_01 / f"{case_id:03d}" / "source.md" for case_id in range(1, 11)],
    ]
    batch_02_paths = [
        batch_02 / "manifest.json",
        batch_02 / "expected.json",
        *[batch_02 / f"{case_id:03d}" / "source.md" for case_id in range(11, 21)],
    ]

    assert _digest(batch_01_paths, batch_01) == (
        "a023907907003075a1f43f3e91cb5ed9152e2e85357f04b3f41f7ca94a073e2d"
    )
    assert _digest(batch_02_paths, batch_02) == (
        "d6480ad14f4640a4c3dcf29268accbd848455fd01177416ba092aacb4189a755"
    )


def test_registration_requires_no_api_network_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read registered artifacts with network and environment access forbidden."""
    def fail_access(*args: object, **kwargs: object) -> object:
        raise AssertionError("external access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_access)
    monkeypatch.setattr(os, "getenv", fail_access)

    assert len(_load_json("manifest.json")["cases"]) == 10
    assert len(_load_json("expected.json")["expectations"]) == 10
