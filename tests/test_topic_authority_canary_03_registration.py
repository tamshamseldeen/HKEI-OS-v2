"""Registration-only integrity contract for internal canary source set 03."""

from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

from src.resolution.controlled_topic_authority_consumer import TopicAuthorityConsumerRoute
from src.resolution.resolver_authority_mode import ResolverAuthorityMode
from src.resolution.topic_authority_canary_route_config import TopicAuthorityCanaryRouteConfig
from src.resolution.topic_authority_runtime_config import TopicAuthorityRuntimeConfig


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "canary_sources"
RAW = SOURCE_ROOT / "topic_authority_canary_03_raw.txt"
REGISTERED = SOURCE_ROOT / "topic_authority_canary_03.txt"
MANIFEST = SOURCE_ROOT / "topic_authority_canary_03_manifest.json"
EXPECTED_IDS = tuple(f"CANARY3-{number:03d}" for number in range(1, 6))


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def registered_cases():
    return tuple(part for part in re.split(
        r"(?=^canary_id: CANARY3-\d{3}$)",
        REGISTERED.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    ) if part.strip())


def case_field(case, marker, next_marker=None):
    value = case.split(marker, 1)[1]
    return value.split(next_marker, 1)[0].strip() if next_marker else value.strip()


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def corpus(paths):
    return normalized("\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists()))


def assert_no_exact_duplicates(paths):
    reference = corpus(paths)
    for case in registered_cases():
        fields = (
            case_field(case, "لينك الخبر:", "عنوان الخبر:"),
            case_field(case, "عنوان الخبر:", "محتوى الخبر:"),
            case_field(case, "محتوى الخبر:"),
        )
        assert not any(normalized(field) in reference for field in fields)


def test_raw_source_exists(): assert RAW.is_file()
def test_registered_source_exists(): assert REGISTERED.is_file()
def test_manifest_exists(): assert MANIFEST.is_file()
def test_exactly_five_cases(): assert len(registered_cases()) == 5
def test_case_ids_exact(): assert tuple(re.search(r"canary_id: (CANARY3-\d{3})", case).group(1) for case in registered_cases()) == EXPECTED_IDS
def test_case_ids_unique(): assert len(set(manifest()["case_ids"])) == 5
def test_every_case_has_url(): assert all(case_field(case, "لينك الخبر:", "عنوان الخبر:") for case in registered_cases())
def test_every_case_has_title(): assert all(case_field(case, "عنوان الخبر:", "محتوى الخبر:") for case in registered_cases())
def test_every_case_has_body(): assert all(case_field(case, "محتوى الخبر:") for case in registered_cases())


def test_no_truth_or_review_fields():
    lowered = REGISTERED.read_text(encoding="utf-8").lower()
    forbidden = ("expected_topic", "expected_format", "expected_reader_intent", "correctness", "risk label")
    assert not any(item in lowered for item in forbidden)


def test_raw_sha_recorded(): assert sha256(RAW.read_bytes()).hexdigest() == manifest()["raw_source_sha256"]
def test_registered_sha_recorded(): assert sha256(REGISTERED.read_bytes()).hexdigest() == manifest()["registered_source_sha256"]


def test_registered_content_traces_exactly_to_raw():
    without_ids = re.sub(r"^canary_id: CANARY3-\d{3}\n", "", REGISTERED.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert without_ids.rstrip("\n") == RAW.read_text(encoding="utf-8").rstrip("\n")


def test_source_integrity_verified(): assert manifest()["source_integrity"] == "VERIFIED_FAITHFUL_REGISTRATION"
def test_no_canary_01_duplicates(): assert_no_exact_duplicates([SOURCE_ROOT / "topic_authority_canary_01.txt"])
def test_no_canary_02_duplicates(): assert_no_exact_duplicates([SOURCE_ROOT / "topic_authority_canary_02.txt"])
def test_no_benchmark_duplicates(): assert_no_exact_duplicates(list((ROOT / "benchmark").glob("batch_*/**/source.md")))
def test_no_hkei_216_duplicates(): assert_no_exact_duplicates(list((ROOT / "tests").glob("*consequence*")))
def test_no_hkei_221_duplicates(): assert_no_exact_duplicates([ROOT / "examples/run_topic_world_business_ontology_boundary_analysis.py", ROOT / "benchmark/topic_world_business_ontology_boundary_analysis.json"])
def test_no_hkei_223_duplicates(): assert_no_exact_duplicates([ROOT / "tests/fixtures/topic_ontology_boundary_raw_arabic.json"])


def test_freshness_counts_and_status():
    data = manifest()
    assert data["freshness_status"] == "CONSUMED_FOR_EVALUATION"
    assert all(data[key] == 0 for key in (
        "duplicates_with_canary_01", "duplicates_with_canary_02",
        "duplicates_with_benchmark_batches", "duplicates_with_HKEI_216_fixtures",
        "duplicates_with_HKEI_221_diagnostics", "duplicates_with_HKEI_223_fixtures",
    ))


def test_registration_and_operational_status():
    assert manifest()["registration_status"] == "REGISTERED"
    assert manifest()["operational_status"] == "CONTROLLED_INTERNAL_OPERATIONAL_CANARY_SOURCE"


def test_registration_lifecycle_records_completed_evaluation():
    data = manifest()
    assert data["evaluation_status"] == "COMPLETED_AWAITING_HUMAN_AUDIT"
    assert all(data[key] == "YES" for key in (
        "classifier_execution", "semantic_execution", "Gate_execution",
        "Resolver_execution",
    ))
    assert data["authority_execution"] == "YES_REQUEST_LOCAL_ONLY"
    assert data["provider_calls"] == 4


def test_evaluation_exists_without_human_audit_artifacts():
    assert (ROOT / "benchmark/internal_canary/topic_authority_canary_03.json").is_file()
    assert (ROOT / "benchmark/internal_canary/topic_authority_canary_03.md").is_file()
    forbidden = (
        ROOT / "benchmark/internal_canary/topic_authority_canary_03_human_audit.json",
        ROOT / "benchmark/internal_canary/topic_authority_canary_03_human_audit.md",
    )
    assert not any(path.exists() for path in forbidden)


def test_pilot_remains_shadow():
    assert TopicAuthorityRuntimeConfig().resolve() is ResolverAuthorityMode.SHADOW
    assert manifest()["pilot_effective_mode"] == "SHADOW"


def test_internal_route_remains_disabled():
    assert TopicAuthorityCanaryRouteConfig().resolve_route() is TopicAuthorityConsumerRoute.NORMAL_PRODUCTION_PATH
    assert manifest()["internal_route_state"] == "DISABLED_DEFAULT"
    assert manifest()["canary_continuation"] == "CONSUMED"
