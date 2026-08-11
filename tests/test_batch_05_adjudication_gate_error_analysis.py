"""Tests for the frozen Batch 05 gate-error analysis."""

from hashlib import sha256
import json
from pathlib import Path

from examples.run_batch_05_adjudication_gate_error_analysis import (
    BATCH_ROOT, ERROR_IDS, analyze_gate_errors, render_json, render_markdown,
)


PROTECTED_DIGESTS = {
    "editorial_validation.json": "a8b210cb8ece13d77cb3f594a3048cac1d306148d9de30fcedc1abd0ae5c9fe3",
    "adjudication_gate_shadow.json": "7eadf2df6bfb0b4028f32bfb1e5ba06506917b7c45e11ce0dcd361b345007fcf",
}


def _frozen_analysis() -> dict[str, object]:
    return json.loads(
        (BATCH_ROOT / "adjudication_gate_error_analysis.json").read_text()
    )


def test_exact_errors_and_control_are_preserved() -> None:
    analysis = _frozen_analysis()
    assert analysis["cases_analyzed"] == 6
    assert tuple(case["id"] for case in analysis["cases"]) == ERROR_IDS
    assert analysis["topic_false_negatives"] == ["046", "050"]
    assert analysis["format_false_negatives"] == ["044", "045", "047"]
    assert analysis["format_false_positives"] == ["048"]
    assert analysis["control"]["id"] == "049"
    assert analysis["control"]["observed_scope"] == "NOT_REQUIRED"
    assert analysis["control"]["failure_classes"] == ["CONTROL_CORRECTLY_AVOIDED"]


def test_frozen_gate_triggers_and_outputs_are_used_verbatim() -> None:
    analysis = _frozen_analysis()
    case_048 = next(case for case in analysis["cases"] if case["id"] == "048")
    assert "ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK" in case_048["trigger_signals"]
    assert "CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED" in case_048["trigger_signals"]
    assert "SOURCE_TOO_THIN_FOR_ANALYSIS" in case_048["available_structured_signals"]


def test_available_missing_owners_and_counterfactuals_are_exact() -> None:
    analysis = _frozen_analysis()
    assert analysis["signals_available_but_unused"] == ["046"]
    assert analysis["signals_not_available"] == ["044", "045", "047", "050"]
    assert {case["id"]: case["primary_owner"] for case in analysis["cases"]} == {
        "044": "CONTEXTUAL_EVIDENCE", "045": "FORMAT_CLASSIFIER",
        "046": "SHARED_UPSTREAM_AND_GATE", "047": "CONTEXTUAL_EVIDENCE",
        "048": "GATE", "050": "CONTEXTUAL_EVIDENCE",
    }
    assert analysis["counterfactual_signal_analysis"] == {
        "MEDIUM_TOPIC_CONFIDENCE_WITHOUT_PRIMARY_DOMAIN": {"cases_triggered": 1, "topic_mismatches_triggered": 1, "format_mismatches_triggered": 1, "matched_cases_triggered": 0},
        "SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN": {"cases_triggered": 3, "topic_mismatches_triggered": 3, "format_mismatches_triggered": 1, "matched_cases_triggered": 0},
        "CONTEXTUAL_ANALYSIS_SUPPORT_WITH_FORMAT_MISMATCH": {"cases_triggered": 1, "topic_mismatches_triggered": 1, "format_mismatches_triggered": 1, "matched_cases_triggered": 0},
        "FORMAT_STRUCTURE_ABSENT": {"cases_triggered": 3, "topic_mismatches_triggered": 3, "format_mismatches_triggered": 3, "matched_cases_triggered": 0},
        "PREDICTION_ONLY_ANALYSIS_SUPPORT": {"cases_triggered": 1, "topic_mismatches_triggered": 1, "format_mismatches_triggered": 0, "matched_cases_triggered": 0},
        "EVENT_EVIDENCE_WITHOUT_DOMAIN_RESOLUTION": {"cases_triggered": 4, "topic_mismatches_triggered": 4, "format_mismatches_triggered": 1, "matched_cases_triggered": 0},
    }


def test_outputs_are_body_free_and_runner_reads_only_authorized_json(monkeypatch) -> None:
    reads = []
    original = Path.read_text
    def tracked(path: Path, *args, **kwargs):
        reads.append(path.name)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", tracked)
    analysis = analyze_gate_errors()
    assert reads == ["editorial_validation.json", "adjudication_gate_shadow.json", "editorial_generalization_analysis.json"]
    rendered = render_json(analysis)
    assert '"body"' not in rendered
    assert "human_risk_annotations" not in rendered
    assert "openai" not in Path(__file__).resolve().parents[1].joinpath("examples/run_batch_05_adjudication_gate_error_analysis.py").read_text().casefold()
    assert "http" not in rendered.casefold()
    assert "os.environ" not in rendered
    assert "## Gate Precision vs Recall" in render_markdown(analysis)


def test_protected_diagnostics_and_production_sources_remain_unchanged() -> None:
    for name, digest in PROTECTED_DIGESTS.items():
        assert sha256((BATCH_ROOT / name).read_bytes()).hexdigest() == digest
    root = Path(__file__).resolve().parents[1]
    changed = __import__("subprocess").run(
        ["git", "diff", "--name-only", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()
    assert not any(
        path.startswith("src/")
        and path
        != "src/evidence/deterministic_contextual_evidence_engine.py"
        for path in changed
    )
    assert not any(path.endswith("source.md") for path in changed)
    assert "benchmark/batch_05/human_risk_annotations.json" not in changed
    assert "benchmark/batch_05/expected.json" not in changed
