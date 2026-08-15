"""Integrity tests for the offline HKEI-221 ontology-boundary analysis."""

import json
from pathlib import Path

from examples.run_topic_world_business_ontology_boundary_analysis import (
    OUTPUT_JSON, SCENARIOS, build_analysis,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "benchmark/internal_canary/topic_authority_canary_02_human_audit.json"


def analysis(): return build_analysis()
def audit_case(): return next(item for item in json.loads(AUDIT.read_text(encoding="utf-8"))["records"] if item["canary_id"] == "CANARY2-002")


def test_canary2_002_remains_unsure(): assert audit_case()["human_correctness"] == analysis()["canary2_002_human_status"] == "UNSURE"
def test_no_expected_topic_forced(): assert audit_case()["human_expected_topic"] == analysis()["canary2_002_expected_topic"] == "UNREVIEWED"
def test_world_definition_audited(): assert analysis()["world_semantics_assessment"]["finding"] == "NOT_MERELY_GEOGRAPHIC_BUT_OPERATIONALLY_UNDERSPECIFIED"
def test_business_definition_audited(): assert analysis()["business_semantics_assessment"]["rejected_interpretation"] == "Any event involving a company."
def test_economy_boundary_audited(): assert analysis()["economy_boundary_assessment"]["finding"] == "NO_PRIMARY_SUPPORT_WITHOUT_MACRO_OR_MARKET_TREATMENT"
def test_entity_role_audited(): assert analysis()["role_protection"]["entity_vs_subject"] == "PROTECTION_EXISTS_BUT_INCOMPLETE"
def test_owner_role_audited(): assert analysis()["role_protection"]["owner_vs_subject"] == "OWNER_ROLE_NOT_PROTECTED"
def test_source_role_audited(): assert analysis()["role_protection"]["source_vs_subject"] == "SOURCE_ROLE_PARTIALLY_PROTECTED"
def test_event_centrality_audited(): assert analysis()["role_protection"]["event_centrality"] == "REPRESENTED_BUT_NOT_STRONG_ENOUGH_FOR_EXTERNAL_EVENTS"
def test_exactly_24_unique_synthetic_scenarios(): assert len(SCENARIOS) == len({item[0] for item in SCENARIOS}) == 24
def test_scenario_distribution_exact(): assert analysis()["scenario_distribution"] == {"WORLD_PRIMARY":6,"BUSINESS_PRIMARY":6,"ECONOMY_PRIMARY":4,"GENUINELY_AMBIGUOUS":4,"OTHER":4}
def test_ambiguous_cases_represented(): assert analysis()["representability_counts"]["GENUINELY_FORCED_CHOICE_AMBIGUOUS"] == 4
def test_representability_partition_exact(): assert analysis()["representability_counts"] == {"REPRESENTABLE_SECONDARY_DIMENSION_LOST":11,"CLEARLY_REPRESENTABLE":9,"GENUINELY_FORCED_CHOICE_AMBIGUOUS":4}
def test_historical_cases_audited(): assert analysis()["historical_corpus_audit"]["unique_similar_case_count"] == 15
def test_no_historical_relabeling(): assert analysis()["historical_corpus_audit"]["historical_relabeling"] is False
def test_canary_evidence_in_historical_audit(): assert {"CANARY-004","CANARY2-002"} <= set(analysis()["historical_corpus_audit"]["unique_similar_case_ids"])
def test_single_label_adequacy_classification(): assert analysis()["single_label_sufficiency_assessment"] == "SINGLE_LABEL_ADEQUATE_WITH_CLEARER_RULES"
def test_architecture_recommendation(): assert analysis()["recommended_architecture_direction"] == "D. COMBINE_SEMANTIC_CLARIFICATION_AND_ROLE_PROTECTION"
def test_pilot_implication(): assert analysis()["pilot_implication"] == "TOPIC_ONTOLOGY_SPECIFICATION_REQUIRED_BEFORE_PILOT"
def test_provider_confidence_boundary(): assert analysis()["provider_confidence_implication"] == "CONFIDENCE_INSUFFICIENT_FOR_ONTOLOGY_BOUNDARY"
def test_primary_secondary_is_research_not_implementation(): assert analysis()["primary_secondary_model_evidence"] == "MIXED_STORIES_SHOW_INFORMATION_LOSS_BUT_CURRENT_EVIDENCE_SUPPORTS_RESEARCH_NOT_IMPLEMENTATION"
def test_no_production_modification(): assert analysis()["production_files_modified"] == []
def test_no_provider_calls(): assert analysis()["provider_calls"] == 0
def test_pilot_remains_shadow_and_stopped(): assert analysis()["pilot_effective_mode"] == "SHADOW" and analysis()["pilot_state"] == "STOPPED"
def test_human_unsure_is_neither_success_nor_regression():
    semantics = analysis()["human_unsure_semantics"]
    assert "neither success, regression, correct, nor incorrect" in semantics
def test_persisted_analysis_matches_if_present():
    if OUTPUT_JSON.exists(): assert json.loads(OUTPUT_JSON.read_text(encoding="utf-8")) == analysis()
