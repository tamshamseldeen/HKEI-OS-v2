import json
from pathlib import Path

from examples.run_topic_authority_canary_01_wrong_override_analysis import (
    build_analysis,
    run_analysis,
)


def test_wrong_override_analysis_preserves_history_and_contracts():
    result = build_analysis()
    assert result["case_analyzed"] == "CANARY-003"
    assert result["human_expected_topic"] == "CRIME"
    assert result["deterministic_topic"] == "CRIME"
    assert result["authoritative_topic"] == "HEALTH"
    assert result["provider_calls"] == 0
    assert result["expected_candidate_present"] is True
    assert result["candidate_universe"][0] == "CRIME"
    assert set(result["candidate_universe"]) >= {"CRIME", "HEALTH"}
    assert result["gate"]["assessment"] == "GATE_APPROPRIATE"
    assert result["provider"]["confidence"] == "HIGH"
    assert result["provider"]["ambiguity_remaining"] is False
    assert result["resolver_assessment"] == "RESOLVER_BEHAVIOR_CORRECT_BY_CONTRACT"
    assert result["applicator_assessment"] == "APPLICATOR_CORRECT_BY_CONTRACT"


def test_wrong_override_analysis_is_deterministic_generic_and_stopped():
    first = build_analysis()
    second = build_analysis()
    assert first == second
    assert first["earliest_failure_stage"] == "TOPIC_ROLE_ASSIGNMENT"
    assert first["primary_failure_class"] == "CONSEQUENCE_PROMOTED_TO_SUBJECT"
    assert "STRUCTURED_EVIDENCE_INCOMPLETE" in first["secondary_failure_classes"]
    assert first["safest_generic_counterfactual"].startswith("A.")
    assert first["overcorrection_risk"] == "LOW"
    assert first["source_specific_fix_proposed"] is False
    assert first["pilot_stopped"] is True
    assert first["pilot_implication"] == "ONE_GENERIC_SEMANTIC_FIX_REQUIRED_BEFORE_NEW_CANARY"
    assert first["source_or_prediction_mutation"] is False


def test_analysis_writes_only_sanitized_diagnostic_artifacts(tmp_path: Path):
    json_path = tmp_path / "analysis.json"
    markdown_path = tmp_path / "analysis.md"
    result = run_analysis(output_json=json_path, output_md=markdown_path)
    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert persisted == result
    assert "API key" not in markdown
    assert "raw prompt" not in json_path.read_text(encoding="utf-8").lower()
    assert "CANARY-003" in markdown


def test_no_production_file_is_part_of_the_diagnostic_output_contract():
    source = Path("examples/run_topic_authority_canary_01_wrong_override_analysis.py").read_text(encoding="utf-8")
    assert "OpenAISemanticAdjudicationProvider" not in source
    assert "adjudicate(" not in source
    assert "provider_calls\": 0" in source
