"""Integrity tests for the immutable Batch 04 unseen validation dataset."""

from hashlib import sha256
import json
import os
from pathlib import Path
import socket

import pytest


BATCH_ROOT = Path(__file__).resolve().parents[1] / "benchmark" / "batch_04"
EXPECTED_IDS = tuple(f"{case_id:03d}" for case_id in range(31, 41))
EXPECTED_SOURCE_NAMES = (
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
    "اليوم السابع",
)
EXPECTED_URLS = (
    'https://www.youm7.com/story/2026/8/7/%D8%A7%D9%84%D8%B7%D9%82%D8%B3-%D8%A7%D9%84%D9%8A%D9%88%D9%85-%D8%B4%D8%AF%D9%8A%D8%AF-%D8%A7%D9%84%D8%AD%D8%B1%D8%A7%D8%B1%D8%A9-%D8%B1%D8%B7%D8%A8-%D9%88%D9%86%D8%B4%D8%A7%D8%B7-%D8%B1%D9%8A%D8%A7%D8%AD-%D9%8A%D9%84%D8%B7%D9%81-%D8%A7%D9%84%D8%A3%D8%AC%D9%88%D8%A7%D8%A1-%D9%88%D8%A7%D9%84%D9%85%D8%AD%D8%B3%D9%88%D8%B3%D8%A9/7505037',
    'https://www.youm7.com/story/2026/8/7/%D8%A7%D8%B3%D8%AA%D9%82%D8%B1%D8%A7%D8%B1-%D8%B3%D8%B9%D8%B1-%D8%A7%D9%84%D8%A3%D8%B3%D9%85%D9%86%D8%AA-%D8%A7%D9%84%D9%8A%D9%88%D9%85-%D8%A7%D9%84%D8%AC%D9%85%D8%B9%D8%A9-7-%D8%A3%D8%BA%D8%B3%D8%B7%D8%B3-2026-%D8%A7%D9%84%D8%B7%D9%86-%D8%A8%D9%804000/7505309',
    'https://www.youm7.com/story/2026/8/7/%D8%A7%D9%84%D8%A3%D9%87%D9%84%D9%8A-%D9%8A%D8%A8%D8%AF%D8%A3-%D8%A7%D9%84%D9%8A%D9%88%D9%85-%D8%A8%D8%B1%D9%86%D8%A7%D9%85%D8%AC%D9%87-%D8%A7%D9%84%D8%AA%D8%AF%D8%B1%D9%8A%D8%A8%D9%8A-%D8%A8%D8%A7%D9%84%D9%85%D8%B9%D8%B3%D9%83%D8%B1-%D8%A7%D9%84%D8%AE%D8%A7%D8%B1%D8%AC%D9%8A/7504773',
    'https://www.youm7.com/story/2026/8/7/%D8%AA%D8%B9%D8%B1%D9%81-%D8%B9%D9%84%D9%8A-%D9%85%D9%88%D8%A7%D8%B9%D9%8A%D8%AF-%D9%85%D8%A8%D8%A7%D8%B1%D9%8A%D8%A7%D8%AA-%D8%A7%D9%84%D8%A3%D9%87%D9%84%D9%8A-%D9%81%D9%8A-%D8%A7%D9%84%D8%AF%D9%88%D8%B1%D9%8A-%D8%A7%D9%84%D9%85%D9%85%D8%AA%D8%A7%D8%B2-%D9%85%D9%88%D8%B3%D9%85-2026/7504897',
    'https://www.youm7.com/story/2026/8/7/%D8%A7%D8%B9%D8%B1%D9%81-%D8%B3%D8%B9%D8%B1-%D9%88%D9%85%D9%88%D8%A7%D8%B5%D9%81%D8%A7%D8%AA-%D8%A5%D9%85-%D8%AC%D9%89-%D8%B2%D8%AF-%D8%A5%D8%B3-%D8%A7%D9%84%D9%83%D8%B1%D9%88%D8%B3-%D8%A3%D9%88%D9%81%D8%B1-%D9%81%D9%89/7505635',
    'https://www.youm7.com/story/2026/8/7/%D9%82%D8%A8%D9%84-%D9%81%D9%88%D8%A7%D8%AA-%D8%A7%D9%84%D8%A3%D9%88%D8%A7%D9%86-5-%D9%86%D8%B5%D8%A7%D8%A6%D8%AD-%D9%85%D9%86-%D9%88%D8%B2%D8%A7%D8%B1%D8%A9-%D8%A7%D9%84%D8%B5%D8%AD%D8%A9-%D9%82%D8%AF-%D8%AA%D8%AD%D9%85%D9%8A%D9%83/7504687',
    'https://www.youm7.com/story/2026/8/7/%D9%88%D8%B2%D9%8A%D8%B1-%D8%A7%D9%84%D8%B5%D8%AD%D8%A9-%D9%8A%D9%88%D9%82%D8%B9-%D9%85%D8%B0%D9%83%D8%B1%D8%A9-%D8%AA%D9%81%D8%A7%D9%87%D9%85-%D9%85%D8%B9-%D9%86%D8%B8%D9%8A%D8%B1%D9%87-%D8%A7%D9%84%D8%AA%D8%B4%D8%A7%D8%AF%D9%8A-%D9%84%D8%AF%D8%B9%D9%85-%D8%A7%D9%84%D9%82%D8%B7%D8%A7%D8%B9/7505700',
    'https://www.youm7.com/story/2026/8/7/%D8%A7%D9%84%D8%B5%D8%AD%D8%A9-%D8%A7%D9%84%D8%B9%D8%A7%D9%84%D9%85%D9%8A%D8%A9-%D8%A3%D9%88%D8%BA%D9%86%D8%AF%D8%A7-%D8%AA%D8%B3%D9%8A%D8%B7%D8%B1-%D8%B9%D9%84%D9%89-%D8%A5%D9%8A%D8%A8%D9%88%D9%84%D8%A7-%D9%85%D8%AD%D9%84%D9%8A%D8%A7-%D9%88%D8%A7%D8%B3%D8%AA%D9%85%D8%B1%D8%A7%D8%B1-%D8%AA%D9%81%D8%B4%D9%89-%D8%A7%D9%84%D9%81%D9%8A%D8%B1%D9%88%D8%B3/7505569',
    'https://www.youm7.com/story/2026/8/7/%D8%B3%D8%B9%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8-%D8%A7%D9%84%D9%8A%D9%88%D9%85-%D8%A7%D9%84%D8%AC%D9%85%D8%B9%D8%A9-7-%D8%A3%D8%BA%D8%B3%D8%B7%D8%B3-2026-%D9%81%D9%89-%D9%85%D8%B5%D8%B1-%D8%B9%D9%8A%D8%A7%D8%B1/7505429',
    'https://www.youm7.com/story/2026/8/7/%D8%A7%D9%84%D8%A8%D8%AA%D8%B1%D9%88%D9%84-%D8%AA%D9%86%D8%AC%D8%AD-%D9%81%D9%89-%D8%A5%D8%B6%D8%A7%D9%81%D8%A9-1300-%D9%85%D9%84%D9%8A%D9%88%D9%86-%D9%82%D8%AF%D9%85-%D9%85%D9%83%D8%B9%D8%A8-%D8%BA%D8%A7%D8%B2-%D9%88%D8%A3%D9%83%D8%AB%D8%B1/7505108',
)
EXPECTED_LABELS = (
    ('031', 'WEATHER', 'STANDARD_NEWS', 'GET_UPDATE'),
    ('032', 'ECONOMY', 'STANDARD_NEWS', 'GET_UPDATE'),
    ('033', 'SPORTS', 'STANDARD_NEWS', 'GET_UPDATE'),
    ('034', 'SPORTS', 'GUIDE', 'VERIFY_REQUIREMENTS'),
    ('035', 'TECHNOLOGY', 'GUIDE', 'COMPARE_OPTIONS'),
    ('036', 'HEALTH', 'GUIDE', 'GET_GUIDANCE'),
    ('037', 'HEALTH', 'STANDARD_NEWS', 'GET_UPDATE'),
    ('038', 'HEALTH', 'STANDARD_NEWS', 'GET_UPDATE'),
    ('039', 'ECONOMY', 'STANDARD_NEWS', 'GET_UPDATE'),
    ('040', 'ECONOMY', 'STANDARD_NEWS', 'GET_UPDATE'),
)
REGISTERED_BATCH_DIGEST = (
    "20c08c974d31c3bb762437e6a3970a2b31dd16431cf43084cd7470f791f38224"
)


def _load_json(filename: str) -> dict[str, object]:
    """Read one Batch 04 UTF-8 JSON document."""
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
    """Register exactly cases 031–040 in source order without category fields."""
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


def test_batch_contains_only_registered_inputs_and_expectations() -> None:
    """Exclude generated articles, validation, and analysis output."""
    files = {
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*")
        if path.is_file()
    }
    assert files == {
        "manifest.json",
        "expected.json",
        *(f"{case_id}/source.md" for case_id in EXPECTED_IDS),
    }
    assert not any(
        term in path.lower()
        for path in files
        for term in ("article", "analysis", "validation", "report")
    )

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
