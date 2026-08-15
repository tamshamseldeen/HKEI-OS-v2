"""Contract tests for the production-neutral HKEI-222 specification."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/TOPIC_ONTOLOGY_BOUNDARY_SPECIFICATION.md"


def text(): return SPEC.read_text(encoding="utf-8")


def test_world_definition_present(): assert "### WORLD" in text() and "international-security incident" in text()
def test_business_definition_present(): assert "### BUSINESS" in text() and "company operations" in text()
def test_economy_definition_present(): assert "### ECONOMY" in text() and "macroeconomic conditions" in text()
def test_entity_protection_specified(): assert "ENTITY_TYPE_NOT_PRIMARY_BY_ITSELF" in text()
def test_owner_protection_specified(): assert "OWNER_ROLE" in text() and "OWNER_NOT_PRIMARY_BY_ITSELF" in text()
def test_source_protection_specified(): assert "SOURCE_ROLE" in text() and "SOURCE_NOT_PRIMARY_BY_ITSELF" in text()
def test_primary_event_specified(): assert "### PRIMARY_EVENT" in text() and "stronger Topic relevance" in text()
def test_primary_subject_specified(): assert "### PRIMARY_SUBJECT" in text() and "organizing editorial subject" in text().lower()
def test_consequence_integration_specified(): assert "DOWNSTREAM_IMPACT" in text() and "CONSEQUENCE_NOT_PRIMARY_BY_ITSELF" in text()
def test_world_business_boundary_defined(): assert "### WORLD versus BUSINESS" in text()
def test_world_economy_boundary_defined(): assert "### WORLD versus ECONOMY" in text()
def test_business_economy_boundary_defined(): assert "### BUSINESS versus ECONOMY" in text()
def test_generic_matrix_has_six_boundaries():
    assert all(pair in text() for pair in ("WORLD / BUSINESS", "WORLD / ECONOMY", "BUSINESS / ECONOMY", "GOVERNMENT / BUSINESS", "POLITICS / BUSINESS", "WORLD / GOVERNMENT"))
def test_ambiguity_contract_defined(): assert all(state in text() for state in ("`CLEAR`", "`BOUNDARY_COMPETING`", "`INSUFFICIENT_EVIDENCE`", "`TOPIC_BOUNDARY_AMBIGUITY`"))
def test_confidence_limitation_defined(): assert "Provider confidence is not sufficient to resolve ontology ambiguity" in text()
def test_single_label_retained(): assert "SINGLE_LABEL_RETAINED" in text()
def test_secondary_model_deferred(): assert "SECONDARY_DOMAIN_MODEL_DEFERRED_FOR_RESEARCH" in text()
def test_all_role_protections_present():
    assert all(name in text() for name in ("ENTITY_TYPE_NOT_PRIMARY_BY_ITSELF", "OWNER_NOT_PRIMARY_BY_ITSELF", "SOURCE_NOT_PRIMARY_BY_ITSELF", "AUTHORITY_NOT_PRIMARY_BY_ITSELF", "METHOD_NOT_PRIMARY_BY_ITSELF", "CONSEQUENCE_NOT_PRIMARY_BY_ITSELF"))
def test_event_centrality_not_raw_counts(): assert "Raw occurrence counts MUST NOT substitute" in text()
def test_external_and_company_centric_protections(): assert "EXTERNAL_EVENT_PROTECTION" in text() and "COMPANY_CENTRIC_EVENT_PROTECTION" in text()
def test_implementation_phases_documented(): assert all(f"Phase {number}" in text() for number in range(1, 9))
def test_acceptance_status_ready(): assert "Status: `READY_FOR_GENERIC_ONTOLOGY_BOUNDARY_IMPLEMENTATION`" in text()
def test_pilot_remains_shadow(): assert "Pilot effective mode remains `SHADOW`" in text()
def test_no_production_code_changes():
    status = subprocess.run(["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    assert not any(line[3:].startswith("src/") for line in status)
def test_no_provider_calls(): assert "Provider calls for this specification are `0`" in text()
