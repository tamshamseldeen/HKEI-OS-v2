"""Registration-only integrity tests for the Batch 06 unseen holdout."""

import ast
import hashlib
import json
from pathlib import Path
import re

from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.topic.topic import Topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_06"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_06_raw.txt"
EXPECTED_IDS = tuple(f"{value:03d}" for value in range(51, 61))
RAW_SHA256 = "7ef269f70c78816521c8d3228db720b771294c9fb91fcbe31629b7748f115a06"


def _json(name: str) -> dict:
    return json.loads((BATCH_ROOT / name).read_text(encoding="utf-8"))


def _parse_source(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    title_part, remainder = content.split("\n# Body\n", maxsplit=1)
    body_part, metadata = remainder.split("\n# Metadata\n", maxsplit=1)
    lines = [line for line in metadata.splitlines() if line]
    return {
        "id": lines[5],
        "title": title_part.removeprefix("# Title\n").strip(),
        "body": body_part.strip(),
        "source_name": lines[1],
        "url": lines[3],
    }


def _parse_raw() -> list[dict[str, str]]:
    raw = RAW_SOURCE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"الخبر (?P<number>\d+) — [^\n]+\n\n"
        r"لينك الخبر:\n(?P<url>.*?)\n\n"
        r"عنوان الخبر:\n(?P<title>.*?)\n\n"
        r"محتوى الخبر:\n(?P<body>.*?)"
        r"(?=\n\nالخبر \d+ —|\Z)",
        re.DOTALL,
    )
    return [
        {
            "id": f"{50 + int(match.group('number')):03d}",
            "url": match.group("url").strip(),
            "title": match.group("title").strip(),
            "body": match.group("body").strip(),
        }
        for match in pattern.finditer(raw)
    ]


def test_batch_directory_exact_cases_and_canonical_sources_exist() -> None:
    assert BATCH_ROOT.is_dir()
    case_dirs = tuple(sorted(path.name for path in BATCH_ROOT.iterdir() if path.is_dir()))
    assert case_dirs == EXPECTED_IDS
    assert all((BATCH_ROOT / case_id / "source.md").is_file() for case_id in EXPECTED_IDS)


def test_manifest_registers_exact_holdout_and_raw_integrity() -> None:
    manifest = _json("manifest.json")
    assert manifest["batch_id"] == "batch_06"
    assert tuple(manifest["case_ids"]) == EXPECTED_IDS
    assert manifest["case_count"] == 10
    assert manifest["raw_source_path"] == str(RAW_SOURCE)
    assert manifest["raw_source_sha256"] == RAW_SHA256
    assert hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() == RAW_SHA256
    assert manifest["registration_status"] == "REGISTERED"
    assert manifest["source_integrity"] == "VERIFIED"
    assert manifest["expected_labels_status"] == "PREREGISTERED"
    assert manifest["validation_status"] == "NOT_RUN"
    assert tuple(item["id"] for item in manifest["cases"]) == EXPECTED_IDS


def test_each_derived_source_exactly_preserves_authoritative_raw_fields() -> None:
    raw_cases = _parse_raw()
    assert tuple(case["id"] for case in raw_cases) == EXPECTED_IDS
    for raw_case in raw_cases:
        source = _parse_source(BATCH_ROOT / raw_case["id"] / "source.md")
        assert source["id"] == raw_case["id"]
        assert source["url"] == raw_case["url"]
        assert source["title"] == raw_case["title"]
        assert source["body"] == raw_case["body"]
        assert source["source_name"]


def test_expected_labels_are_complete_unique_and_enum_aligned() -> None:
    expectations = _json("expected.json")["expectations"]
    assert tuple(item["id"] for item in expectations) == EXPECTED_IDS
    assert len({item["id"] for item in expectations}) == 10
    assert sum(len(item) - 1 for item in expectations) == 30
    topics = {item.value for item in Topic}
    formats = {item.value for item in EditorialFormat}
    intents = {item.value for item in ReaderIntent}
    assert all(item["topic"] in topics for item in expectations)
    assert all(item["editorial_format"] in formats for item in expectations)
    assert all(item["reader_intent"] in intents for item in expectations)


def test_human_risk_annotations_cover_exact_cases() -> None:
    annotations = _json("human_risk_annotations.json")["annotations"]
    assert tuple(item["id"] for item in annotations) == EXPECTED_IDS
    assert len({item["id"] for item in annotations}) == 10
    required = {
        "id", "expected_risk_band", "attribution_required",
        "uncertainty_present", "sensitive_context", "notes",
    }
    assert all(set(item) == required for item in annotations)


def test_batch_contains_only_registration_and_authorized_validation_outputs() -> None:
    files = {
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*") if path.is_file()
    }
    assert files == {
        "manifest.json", "expected.json", "human_risk_annotations.json",
        "editorial_validation.json", "editorial_validation.md",
        "generalization_failure_analysis.json",
        "generalization_failure_analysis.md",
        "post_hkei_157_comparison.json",
        "post_hkei_157_comparison.md",
        *(f"{case_id}/source.md" for case_id in EXPECTED_IDS),
    }
    forbidden = ("contextual", "semantic", "adjudication", "openai", "provider")
    assert not any(term in path.casefold() for path in files for term in forbidden)


def test_registration_test_imports_no_prediction_or_provider_modules() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = (
        "classifier", "contextual", "semantic_engine", "adjudication",
        "openai", "provider", "workflow",
    )
    assert not any(term in module.casefold() for module in imported for term in forbidden)
