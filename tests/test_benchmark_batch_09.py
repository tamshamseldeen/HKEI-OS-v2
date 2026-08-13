"""Registration-only integrity tests for the untouched Batch 09 Resolver holdout."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.topic.topic import Topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_09"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_09_raw.txt"
EXPECTED_IDS = tuple(f"{value:03d}" for value in range(81, 91))
RAW_SHA256 = "648043515889ff801d11939f61bd183762acb3e192567574f4ffc10e55f2fa05"
PRE_REGISTRATION_COMMIT = "713bda9fd33a125be882ed19e6e15ab3e291c0c2"


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


def _raw_field(section: str, label: str, next_label: str | None = None) -> str:
    marker = rf"(?:\*\*)?{label}:(?:\*\*)?\s*\n"
    start_match = re.search(marker, section)
    assert start_match is not None
    start = start_match.end()
    if next_label is None:
        return section[start:].strip()
    ending = re.search(
        rf"\n\n(?:\*\*)?{next_label}:(?:\*\*)?\s*\n",
        section[start:],
    )
    assert ending is not None
    return section[start : start + ending.start()].strip()


def _parse_raw() -> list[dict[str, str]]:
    raw = RAW_SOURCE.read_text(encoding="utf-8")
    headings = list(re.finditer(r"(?m)^(?:## )?الخبر (\d+) —[^\n]*$", raw))
    cases = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(raw)
        section = raw[heading.end() : end].strip()
        url = _raw_field(section, "لينك الخبر", "عنوان الخبر")
        if url.startswith("["):
            match = re.match(r"\[(.*?)\]\(", url, re.DOTALL)
            assert match is not None
            url = match.group(1)
        body = re.sub(r"\n\n---\s*$", "", _raw_field(section, "محتوى الخبر")).strip()
        cases.append({
            "id": f"{80 + int(heading.group(1)):03d}",
            "url": url,
            "title": _raw_field(section, "عنوان الخبر", "محتوى الخبر"),
            "body": body,
        })
    return cases


def test_batch_has_exactly_ten_canonical_case_sources() -> None:
    assert BATCH_ROOT.is_dir()
    case_dirs = tuple(sorted(path.name for path in BATCH_ROOT.iterdir() if path.is_dir()))
    assert case_dirs == EXPECTED_IDS
    assert all((BATCH_ROOT / case_id / "source.md").is_file() for case_id in EXPECTED_IDS)


def test_manifest_registers_frozen_untouched_resolver_holdout() -> None:
    manifest = _json("manifest.json")
    assert manifest["batch_id"] == "batch_09"
    assert tuple(manifest["case_ids"]) == EXPECTED_IDS
    assert manifest["case_count"] == 10
    assert manifest["registration_status"] == "REGISTERED"
    assert manifest["scientific_status"] == "UNTOUCHED_PREREGISTERED_RESOLVER_HOLDOUT"
    assert manifest["source_integrity"] == "VERIFIED"
    assert manifest["expected_labels_status"] == "PREREGISTERED_FROZEN"
    assert manifest["validation_status"] == "NOT_RUN"
    assert manifest["provider_calls"] == 0


def test_raw_source_sha_and_manifest_path_are_exact() -> None:
    manifest = _json("manifest.json")
    assert manifest["raw_source_path"] == str(RAW_SOURCE)
    assert manifest["raw_source_sha256"] == RAW_SHA256
    assert hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() == RAW_SHA256


def test_every_registered_url_title_and_body_exactly_matches_raw_input() -> None:
    raw_cases = _parse_raw()
    assert tuple(case["id"] for case in raw_cases) == EXPECTED_IDS
    for raw_case in raw_cases:
        source = _parse_source(BATCH_ROOT / raw_case["id"] / "source.md")
        assert source["id"] == raw_case["id"]
        assert source["url"] == raw_case["url"]
        assert source["title"] == raw_case["title"]
        assert source["body"] == raw_case["body"]
        assert all(source[field] for field in ("url", "title", "body"))


def test_expected_labels_cover_ten_cases_and_exactly_thirty_values() -> None:
    expectations = _json("expected.json")["expectations"]
    assert tuple(item["id"] for item in expectations) == EXPECTED_IDS
    assert len({item["id"] for item in expectations}) == 10
    assert sum(len(item) - 1 for item in expectations) == 30
    assert all(set(item) == {"id", "topic", "editorial_format", "reader_intent"} for item in expectations)


def test_expected_labels_are_current_enum_values() -> None:
    expectations = _json("expected.json")["expectations"]
    assert all(item["topic"] in {value.value for value in Topic} for item in expectations)
    assert all(item["editorial_format"] in {value.value for value in EditorialFormat} for item in expectations)
    assert all(item["reader_intent"] in {value.value for value in ReaderIntent} for item in expectations)


def test_human_risk_annotations_cover_exactly_the_holdout() -> None:
    annotations = _json("human_risk_annotations.json")["annotations"]
    assert tuple(item["id"] for item in annotations) == EXPECTED_IDS
    assert len({item["id"] for item in annotations}) == 10
    assert all(set(item) == {
        "id", "expected_risk_band", "attribution_required",
        "uncertainty_present", "sensitive_context", "notes",
    } for item in annotations)


def test_batch_contains_registration_files_only() -> None:
    files = {
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*") if path.is_file()
    }
    assert files == {
        "manifest.json", "expected.json", "human_risk_annotations.json",
        *(f"{case_id}/source.md" for case_id in EXPECTED_IDS),
    }


def test_registration_contains_no_execution_or_validation_outputs() -> None:
    registration = json.dumps({
        "manifest": _json("manifest.json"),
        "expected": _json("expected.json"),
        "risks": _json("human_risk_annotations.json"),
    }).casefold()
    forbidden = (
        "predicted_topic", "predicted_format", "classifier_output",
        "semantic_evidence", "format_v2", "candidate_assessment", "gate_decision",
        "provider_response", "resolver_output", "validation_output", "accuracy",
    )
    assert not any(field in registration for field in forbidden)


def test_registration_test_imports_no_execution_modules() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = (
        "classifier", "semantic_engine", "candidate_assessor", "adjudication",
        "gate", "openai", "provider", "request_builder", "resolver", "workflow",
    )
    assert not any(term in module.casefold() for module in imported for term in forbidden)


def test_previous_benchmark_batches_are_unmodified_by_registration() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", PRE_REGISTRATION_COMMIT],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert not any(
        path.startswith(tuple(f"benchmark/batch_{value:02d}/" for value in range(1, 9)))
        for path in changed
    )
