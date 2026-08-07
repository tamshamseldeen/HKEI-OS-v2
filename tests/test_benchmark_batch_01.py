"""Validation tests for persistent editorial benchmark batch 01."""

import json
from pathlib import Path
import socket
from typing import TypedDict

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_01"
EXPECTED_IDS = tuple(f"{number:03d}" for number in range(1, 11))
EXPECTED_SOURCES = (
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
EXPECTED_CATEGORIES = (
    "economy",
    "economy",
    "technology",
    "weather",
    "government",
    "economy",
    "economy",
    "culture",
    "sports",
    "economy",
)


class ManifestCase(TypedDict):
    """Describe one manifest entry used only by batch validation tests."""

    id: str
    source_name: str
    benchmark_category: str
    source_file: str


def load_cases() -> tuple[ManifestCase, ...]:
    """Load ordered case metadata from the static local manifest."""
    data = json.loads((BATCH_ROOT / "manifest.json").read_text(encoding="utf-8"))
    return tuple(data["cases"])


def parse_source(path: Path) -> dict[str, str]:
    """Parse fixed source sections and metadata from one local Markdown file."""
    content = path.read_text(encoding="utf-8")
    title_part, remainder = content.split("\n# Body\n", maxsplit=1)
    body_part, metadata = remainder.split("\n# Metadata\n", maxsplit=1)
    metadata_lines = [line for line in metadata.splitlines() if line]
    return {
        "title": title_part.removeprefix("# Title\n").strip(),
        "body": body_part.strip(),
        "source_name": metadata_lines[1],
        "source_url": metadata_lines[3],
        "benchmark_category": metadata_lines[5],
        "id": metadata_lines[7],
    }


def test_manifest_contains_exactly_ten_ordered_unique_cases() -> None:
    """List exactly IDs 001 through 010 once and in ascending order."""
    cases = load_cases()
    ids = tuple(case["id"] for case in cases)

    assert len(cases) == 10
    assert ids == EXPECTED_IDS
    assert len(set(ids)) == 10


def test_exactly_ten_case_directories_exist() -> None:
    """Create only the ten specified numeric case directories."""
    directories = tuple(
        sorted(path.name for path in BATCH_ROOT.iterdir() if path.is_dir())
    )

    assert directories == EXPECTED_IDS


def test_manifest_preserves_sources_categories_and_paths() -> None:
    """Preserve supplied source names, categories, and ordered source paths."""
    cases = load_cases()

    assert tuple(case["source_name"] for case in cases) == EXPECTED_SOURCES
    assert tuple(case["benchmark_category"] for case in cases) == (
        EXPECTED_CATEGORIES
    )
    assert tuple(case["source_file"] for case in cases) == tuple(
        f"{case_id}/source.md" for case_id in EXPECTED_IDS
    )
    assert all(set(case) == {
        "id",
        "source_name",
        "benchmark_category",
        "source_file",
    } for case in cases)


@pytest.mark.parametrize("case", load_cases(), ids=EXPECTED_IDS)
def test_source_file_sections_and_metadata(case: ManifestCase) -> None:
    """Require complete local source sections and preserved manifest metadata."""
    source_path = BATCH_ROOT / case["source_file"]

    assert source_path.is_file()
    content = source_path.read_text(encoding="utf-8")
    assert "# Title\n" in content
    assert "\n# Body\n" in content
    assert "\n# Metadata\n" in content
    parsed = parse_source(source_path)
    assert parsed["title"]
    assert parsed["body"]
    assert parsed["source_name"] == case["source_name"]
    assert parsed["benchmark_category"] == case["benchmark_category"]
    assert parsed["id"] == case["id"]
    assert parsed["source_url"].startswith("https://")


@pytest.mark.parametrize("case_id", EXPECTED_IDS)
def test_generated_and_review_files_do_not_exist(case_id: str) -> None:
    """Exclude generated articles and editorial reviews from the source batch."""
    case_root = BATCH_ROOT / case_id

    assert not (case_root / "generated.md").exists()
    assert not (case_root / "review.md").exists()


def test_validation_requires_no_api_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load and parse the complete batch while network sockets are unavailable."""
    def fail_network(*args: object, **kwargs: object) -> socket.socket:
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "socket", fail_network)

    cases = load_cases()
    parsed = tuple(parse_source(BATCH_ROOT / case["source_file"]) for case in cases)
    assert len(parsed) == 10
