"""Registration-only integrity tests for the untouched Batch 07 holdout."""

import ast
import hashlib
import json
from pathlib import Path
import re

from src.formatting.editorial_format import EditorialFormat
from src.intent.reader_intent import ReaderIntent
from src.topic.topic import Topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_07"
RAW_SOURCE = PROJECT_ROOT.parent / "benchmark_sources" / "batch_07_raw.txt"
EXPECTED_IDS = tuple(f"{value:03d}" for value in range(61, 71))
RAW_SHA256 = "7a8ab6b9155276eeabbb4459590fa9c10528cfd3c9a5fc517f8d0abed5d39be3"


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
    headings = list(re.finditer(r"(?m)^(?:## )?الخبر (\d+) —[^\n]*$", raw))
    cases = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(raw)
        section = raw[heading.end():end].strip()
        url = re.search(
            r"(?:\*\*)?لينك الخبر:(?:\*\*)?\s*\n(.+?)(?:\n\n)",
            section, re.DOTALL,
        ).group(1).strip()
        if url.startswith("["):
            url = re.match(r"\[(.*?)\]\(", url, re.DOTALL).group(1)
        title = re.search(
            r"(?:\*\*)?عنوان الخبر:(?:\*\*)?\s*\n(.+?)(?:\n\n)",
            section, re.DOTALL,
        ).group(1).strip()
        body = re.search(
            r"(?:\*\*)?محتوى الخبر:(?:\*\*)?\s*\n(.*)",
            section, re.DOTALL,
        ).group(1).strip()
        cases.append({
            "id": f"{60 + int(heading.group(1)):03d}",
            "url": url,
            "title": title,
            "body": re.sub(r"\n\n---\s*$", "", body),
        })
    return cases


def test_batch_directory_has_exactly_ten_canonical_case_sources() -> None:
    assert BATCH_ROOT.is_dir()
    case_dirs = tuple(sorted(path.name for path in BATCH_ROOT.iterdir() if path.is_dir()))
    assert case_dirs == EXPECTED_IDS
    assert all((BATCH_ROOT / case_id / "source.md").is_file() for case_id in EXPECTED_IDS)


def test_manifest_registers_untouched_holdout_and_raw_integrity() -> None:
    manifest = _json("manifest.json")
    assert manifest["batch_id"] == "batch_07"
    assert tuple(manifest["case_ids"]) == EXPECTED_IDS
    assert manifest["case_count"] == 10
    assert manifest["raw_source_path"] == str(RAW_SOURCE)
    assert manifest["raw_source_sha256"] == RAW_SHA256
    assert hashlib.sha256(RAW_SOURCE.read_bytes()).hexdigest() == RAW_SHA256
    assert manifest["registration_status"] == "REGISTERED"
    assert manifest["scientific_status"] == "UNTOUCHED_PREREGISTERED_HOLDOUT"
    assert manifest["source_integrity"] == "VERIFIED"
    assert manifest["expected_labels_status"] == "PREREGISTERED_FROZEN"
    assert manifest["validation_status"] == "NOT_RUN"
    assert tuple(case["id"] for case in manifest["cases"]) == EXPECTED_IDS


def test_each_source_exactly_preserves_authoritative_url_title_and_body() -> None:
    raw_cases = _parse_raw()
    assert tuple(case["id"] for case in raw_cases) == EXPECTED_IDS
    for raw_case in raw_cases:
        source = _parse_source(BATCH_ROOT / raw_case["id"] / "source.md")
        assert source["id"] == raw_case["id"]
        assert source["url"] == raw_case["url"]
        assert source["title"] == raw_case["title"]
        assert source["body"] == raw_case["body"]
        assert source["source_name"]


def test_exactly_thirty_preregistered_labels_are_enum_aligned() -> None:
    expectations = _json("expected.json")["expectations"]
    assert tuple(item["id"] for item in expectations) == EXPECTED_IDS
    assert len({item["id"] for item in expectations}) == 10
    assert sum(len(item) - 1 for item in expectations) == 30
    assert all(item["topic"] in {value.value for value in Topic} for item in expectations)
    assert all(item["editorial_format"] in {value.value for value in EditorialFormat} for item in expectations)
    assert all(item["reader_intent"] in {value.value for value in ReaderIntent} for item in expectations)


def test_human_risk_annotations_cover_exactly_the_holdout() -> None:
    annotations = _json("human_risk_annotations.json")["annotations"]
    assert tuple(item["id"] for item in annotations) == EXPECTED_IDS
    assert len({item["id"] for item in annotations}) == 10
    required = {
        "id", "expected_risk_band", "attribution_required",
        "uncertainty_present", "sensitive_context", "notes",
    }
    assert all(set(item) == required for item in annotations)


def test_batch_contains_registration_and_authorized_evaluation_files_only() -> None:
    files = {
        path.relative_to(BATCH_ROOT).as_posix()
        for path in BATCH_ROOT.rglob("*") if path.is_file()
    }
    diagnostic_outputs = {
        "full_stack_shadow_evaluation.json",
        "full_stack_shadow_evaluation.md",
        "gate_failure_analysis.json",
        "gate_failure_analysis.md",
        "post_gate_refinement_full_stack_evaluation.json",
        "post_gate_refinement_full_stack_evaluation.md",
        "gate_refinement_comparison.json",
        "gate_refinement_comparison.md",
    }
    assert files == {
        "manifest.json", "expected.json", "human_risk_annotations.json",
        *diagnostic_outputs,
        *(f"{case_id}/source.md" for case_id in EXPECTED_IDS),
    }
    forbidden = (
        "validation", "classifier", "classification", "contextual",
        "semantic", "candidate", "gate", "adjudication", "openai",
        "provider", "resolver", "prediction",
    )
    assert not any(
        term in path.casefold()
        for path in files - diagnostic_outputs
        for term in forbidden
    )


def test_registration_data_contains_no_machine_output_fields() -> None:
    payload = json.dumps({
        "manifest": _json("manifest.json"),
        "expected": _json("expected.json"),
        "risks": _json("human_risk_annotations.json"),
    }).casefold()
    forbidden = (
        "classifier_output", "classification_output", "semantic_evidence",
        "candidate_assessment", "gate_decision", "provider_response",
        "openai_response", "resolver_output",
    )
    assert not any(field in payload for field in forbidden)


def test_registration_test_imports_no_prediction_or_provider_modules() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = (
        "classifier", "contextual", "semantic_engine", "candidate_assessor",
        "adjudication", "gate", "openai", "provider", "workflow",
    )
    assert not any(term in module.casefold() for module in imported for term in forbidden)
