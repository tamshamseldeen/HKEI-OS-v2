import json
from pathlib import Path

from examples.run_adjudication_strict_trigger_parity_analysis import (
    OUTPUT_JSON,
    OUTPUT_MD,
    analyze_strict_trigger_parity,
    render_json,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


def test_parity_analysis_uses_same_fifty_case_corpus_and_baseline() -> None:
    result = analyze_strict_trigger_parity()
    assert result["cases_analyzed"] == 50
    assert "same current existing-topic-required state" in result[
        "baseline_consistency"
    ]


def test_hkei_111_candidate_is_reconstructed_independently() -> None:
    result = analyze_strict_trigger_parity()
    assert result["diagnostic_candidate_metrics"] == {
        "cases_triggered": 1,
        "incremental_topic_TP": 1,
        "incremental_topic_FP": 0,
    }


def test_production_trigger_is_inspected_independently() -> None:
    result = analyze_strict_trigger_parity()
    assert result["production_trigger_metrics"] == {
        "cases_triggered": 3,
        "incremental_topic_TP": 1,
        "incremental_topic_FP": 2,
    }
    assert result["cross_batch_false_positive_cases"] == [
        "batch_02/014",
        "batch_02/019",
    ]


def test_required_cases_expose_deterministic_sufficiency_difference() -> None:
    result = analyze_strict_trigger_parity()
    cases = {(case["batch"], case["id"]): case for case in result["cases"]}
    assert set(cases) == {
        ("batch_02", "014"),
        ("batch_02", "019"),
        ("batch_05", "049"),
        ("batch_05", "050"),
    }
    for key in (("batch_02", "014"), ("batch_02", "019")):
        case = cases[key]
        assert case["topic_match"] is True
        assert case["diagnostic_deterministic_sufficiency"] is True
        assert case["production_deterministic_sufficiency"] is False
        assert case["diagnostic_strict_candidate"] is False
        assert case["production_strict_trigger"] is True
    case_050 = cases[("batch_05", "050")]
    assert case_050["diagnostic_strict_candidate"] is True
    assert case_050["production_strict_trigger"] is True
    assert case_050["diagnostic_deterministic_sufficiency"] is False
    case_049 = cases[("batch_05", "049")]
    assert case_049["diagnostic_strict_candidate"] is False
    assert case_049["production_strict_trigger"] is False


def test_logic_and_metric_comparison_are_deterministic() -> None:
    first = analyze_strict_trigger_parity()
    second = analyze_strict_trigger_parity()
    assert first == second
    assert len(first["logic_differences"]) == 12
    assert first["primary_discrepancy_cause"] == (
        "DETERMINISTIC_SUFFICIENCY_DEFINITION_DRIFT"
    )
    assert first["primary_conclusion"] == (
        "PRODUCTION_TRIGGER_NOT_EQUIVALENT_TO_VALIDATED_CANDIDATE"
    )
    assert first["recommended_action"] == (
        "ALIGN_PRODUCTION_TO_VALIDATED_STRICT_LOGIC"
    )
    assert first["gate_freeze_safe"] is False


def test_persisted_outputs_match_deterministic_rendering() -> None:
    result = analyze_strict_trigger_parity()
    assert OUTPUT_JSON.read_text(encoding="utf-8") == render_json(result)
    assert OUTPUT_MD.read_text(encoding="utf-8") == render_markdown(result)


def test_json_contains_no_source_bodies_or_risk_annotations() -> None:
    persisted = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    serialized = json.dumps(persisted)
    assert '"body"' not in serialized
    assert "human_risk_annotations" not in serialized
    assert "risk_annotations" not in serialized


def test_analysis_runner_has_no_api_or_web_access() -> None:
    source = (
        ROOT / "examples" / "run_adjudication_strict_trigger_parity_analysis.py"
    ).read_text(encoding="utf-8")
    assert "openai" not in source.lower()
    assert "requests" not in source
    assert "urllib" not in source
    assert "human_risk_annotations" not in source


def test_audit_does_not_modify_production_or_expectation_files() -> None:
    allowed = {
        "benchmark/adjudication_strict_trigger_parity_analysis.json",
        "benchmark/adjudication_strict_trigger_parity_analysis.md",
        "examples/run_adjudication_strict_trigger_parity_analysis.py",
        "tests/test_adjudication_strict_trigger_parity_analysis.py",
    }
    assert all(path.exists() for path in (OUTPUT_JSON, OUTPUT_MD))
    assert not any("expected.json" in path for path in allowed)
    assert not any(path.startswith("src/") for path in allowed)
