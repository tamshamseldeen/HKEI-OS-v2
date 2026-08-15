"""Registration-only integrity contract for internal canary source set 02."""

from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "canary_sources"
RAW = SOURCE_ROOT / "topic_authority_canary_02_raw.txt"
REGISTERED = SOURCE_ROOT / "topic_authority_canary_02.txt"
MANIFEST = SOURCE_ROOT / "topic_authority_canary_02_manifest.json"
EXPECTED_IDS = tuple(f"CANARY2-{number:03d}" for number in range(1, 6))


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def registered_cases():
    text = REGISTERED.read_text(encoding="utf-8")
    parts = re.split(r"(?=^canary_id: CANARY2-\d{3}$)", text, flags=re.MULTILINE)
    return tuple(part for part in parts if part.strip())


def case_field(case, marker, next_marker=None):
    value = case.split(marker, 1)[1]
    if next_marker is not None:
        value = value.split(next_marker, 1)[0]
    return value.strip()


def test_raw_source_exists(): assert RAW.is_file()
def test_registered_source_exists(): assert REGISTERED.is_file()
def test_manifest_exists(): assert MANIFEST.is_file()
def test_exactly_five_cases(): assert len(registered_cases()) == 5
def test_case_ids_exact(): assert tuple(re.search(r"canary_id: (CANARY2-\d{3})", case).group(1) for case in registered_cases()) == EXPECTED_IDS
def test_case_ids_unique(): assert len(set(manifest()["case_ids"])) == 5
def test_every_case_has_url(): assert all(case_field(case, "لينك الخبر:", "عنوان الخبر:") for case in registered_cases())
def test_every_case_has_title(): assert all(case_field(case, "عنوان الخبر:", "محتوى الخبر:") for case in registered_cases())
def test_every_case_has_body(): assert all(case_field(case, "محتوى الخبر:") for case in registered_cases())
def test_no_expected_labels():
    lowered = REGISTERED.read_text(encoding="utf-8").lower()
    assert not any(name in lowered for name in ("expected_topic", "expected_format", "expected_reader_intent"))
def test_no_benchmark_truth_files():
    assert not any((SOURCE_ROOT / name).exists() for name in ("expected.json", "human_risk_annotations.json"))
def test_raw_sha_recorded(): assert sha256(RAW.read_bytes()).hexdigest() == manifest()["raw_source_sha256"]
def test_registered_sha_recorded(): assert sha256(REGISTERED.read_bytes()).hexdigest() == manifest()["registered_source_sha256"]
def test_registered_content_traces_exactly_to_raw():
    registered_without_ids = re.sub(r"^canary_id: CANARY2-\d{3}\n", "", REGISTERED.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert registered_without_ids.rstrip("\n") == RAW.read_text(encoding="utf-8")
def test_source_integrity_verified(): assert manifest()["source_integrity"] == "VERIFIED_FAITHFUL_REGISTRATION"
def test_freshness_verified(): assert manifest()["freshness_status"] == "VERIFIED_NEW_OPERATIONAL_INPUTS"
def test_freshness_duplicate_counts_zero():
    assert manifest()["duplicate_with_canary_01"] == 0
    assert manifest()["duplicate_with_benchmark_batches"] == 0
    assert manifest()["duplicate_with_generic_HKEI_216_fixtures"] == 0
def test_registration_status(): assert manifest()["registration_status"] == "REGISTERED"
def test_operational_status(): assert manifest()["operational_status"] == "CONTROLLED_INTERNAL_OPERATIONAL_CANARY_SOURCE"
def test_evaluation_status_not_run(): assert manifest()["evaluation_status"] == "NOT_RUN"
def test_classifier_execution_no(): assert manifest()["classifier_execution"] == "NO"
def test_gate_execution_no(): assert manifest()["Gate_execution"] == "NO"
def test_resolver_execution_no(): assert manifest()["Resolver_execution"] == "NO"
def test_authority_execution_no(): assert manifest()["authority_execution"] == "NO"
def test_provider_calls_zero(): assert manifest()["provider_calls"] == 0
