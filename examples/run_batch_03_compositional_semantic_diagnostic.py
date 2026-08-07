"""Run the foundational compositional semantic diagnostic for Batch 03."""

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.intake.normalized_source import NormalizedSource
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.semantics.semantic_relationship import SemanticRelationship


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_03"
DIAGNOSTIC_CASE_IDS = ("024", "025", "029")
_EXPECTATIONS: dict[str, dict[str, str | None]] = {
    "024": {
        "relationship": "METHOD_APPLIED_TO_SUBJECT",
        "primary": "PRIMARY_DOMAIN_HEALTH",
        "secondary": "SECONDARY_DOMAIN_TECHNOLOGY",
        "suppression": "PRIMARY_DOMAIN_TECHNOLOGY",
        "unexpected": "PRIMARY_DOMAIN_TECHNOLOGY",
    },
    "025": {
        "relationship": "AUTHORITY_ACTS_ON_SUBJECT",
        "primary": "PRIMARY_DOMAIN_HEALTH",
        "secondary": None,
        "suppression": "PRIMARY_DOMAIN_GOVERNMENT",
        "unexpected": "PRIMARY_DOMAIN_GOVERNMENT",
    },
    "029": {
        "relationship": "AUTHORITY_ACTS_ON_SUBJECT",
        "primary": "PRIMARY_DOMAIN_EDUCATION",
        "secondary": None,
        "suppression": "PRIMARY_DOMAIN_GOVERNMENT",
        "unexpected": "PRIMARY_DOMAIN_GOVERNMENT",
    },
}


def _normalized_source(path: Path) -> NormalizedSource:
    """Build the category-free normalized source used by benchmark workflows."""
    source = parse_source(path)
    return NormalizedSource(
        title=source.title,
        body=source.body,
        source_name=source.source_name,
        source_url=source.source_url,
        published_at=None,
        language="ar",
        country=None,
        author=None,
        images=(),
        attachments=(),
        category=None,
        tags=(),
    )


def _relationship_record(relationship: SemanticRelationship) -> dict[str, object]:
    """Serialize exactly the requested relationship fields in model order."""
    return {
        "source_section": relationship.source_section.value,
        "sentence_index": relationship.sentence_index,
        "relationship_type": relationship.relationship_type.value,
        "subject_component": relationship.subject_component.value,
        "subject_text": relationship.subject_text,
        "object_component": relationship.object_component.value,
        "object_text": relationship.object_text,
        "strength": relationship.strength.value,
        "reason_code": relationship.reason_code,
        "evidence_indexes": list(relationship.evidence_indexes),
        "supports": list(relationship.supports),
        "suppresses": list(relationship.suppresses),
    }


def _provenance_valid(
    relationship: SemanticRelationship,
    contextual_evidence: ContextualEvidence,
) -> bool:
    """Validate referenced indexes and their local section provenance."""
    items = contextual_evidence.all_items
    return all(
        0 <= index < len(items)
        and items[index].source_section is relationship.source_section
        and items[index].sentence_index == relationship.sentence_index
        for index in relationship.evidence_indexes
    )


def analyze_diagnostic(
    *,
    batch_root: Path = BATCH_ROOT,
    contextual_engine: DeterministicContextualEvidenceEngine | None = None,
    semantic_engine: DeterministicCompositionalSemanticEngine | None = None,
) -> dict[str, Any]:
    """Analyze the three persisted cases without invoking classifiers."""
    contextual = contextual_engine or DeterministicContextualEvidenceEngine()
    semantic = semantic_engine or DeterministicCompositionalSemanticEngine()
    manifest = {case["id"]: case for case in read_manifest(batch_root)}
    cases: list[dict[str, Any]] = []

    for case_id in DIAGNOSTIC_CASE_IDS:
        source = _normalized_source(batch_root / manifest[case_id]["source_file"])
        contextual_evidence = contextual.analyze(
            source=source,
            user_instruction=None,
        )
        semantic_evidence = semantic.compose(
            source=source,
            contextual_evidence=contextual_evidence,
        )
        expected = _EXPECTATIONS[case_id]
        relationship_types = tuple(
            relationship.relationship_type.value
            for relationship in semantic_evidence.relationships
        )
        suppressions = tuple(
            suppression
            for relationship in semantic_evidence.relationships
            for suppression in relationship.suppresses
        ) + semantic_evidence.format_suppression
        required_secondary = expected["secondary"]
        unexpected = expected["unexpected"]
        primary_present = expected["primary"] in semantic_evidence.primary_domain_candidates
        cases.append(
            {
                "id": case_id,
                "contextual_item_count": len(contextual_evidence.all_items),
                "semantic_relationship_count": len(semantic_evidence.relationships),
                "primary_domain_candidates": list(
                    semantic_evidence.primary_domain_candidates
                ),
                "secondary_domain_candidates": list(
                    semantic_evidence.secondary_domain_candidates
                ),
                "format_support": list(semantic_evidence.format_support),
                "format_suppression": list(semantic_evidence.format_suppression),
                "intent_support": list(semantic_evidence.intent_support),
                "warnings": list(semantic_evidence.warnings),
                "relationships": [
                    _relationship_record(relationship)
                    for relationship in semantic_evidence.relationships
                ],
                "required_relationship_present": expected["relationship"]
                in relationship_types,
                "required_primary_domain_present": primary_present,
                "required_secondary_domain_present": (
                    required_secondary in semantic_evidence.secondary_domain_candidates
                    if required_secondary is not None
                    else None
                ),
                "required_suppression_present": expected["suppression"]
                in suppressions,
                "unexpected_primary_domain_present": (
                    unexpected in semantic_evidence.primary_domain_candidates
                    and (case_id != "024" or not primary_present)
                ),
                "provenance_valid": all(
                    _provenance_valid(relationship, contextual_evidence)
                    for relationship in semantic_evidence.relationships
                ),
            }
        )

    secondary_cases = [
        case
        for case in cases
        if case["required_secondary_domain_present"] is not None
    ]
    return {
        "batch": "batch_03",
        "case_count": len(cases),
        "required_relationships_passed": sum(
            case["required_relationship_present"] for case in cases
        ),
        "required_primary_domains_passed": sum(
            case["required_primary_domain_present"] for case in cases
        ),
        "required_secondary_domains_passed": sum(
            case["required_secondary_domain_present"] for case in secondary_cases
        ),
        "required_secondary_domains_applicable": len(secondary_cases),
        "required_suppressions_passed": sum(
            case["required_suppression_present"] for case in cases
        ),
        "provenance_valid_cases": sum(case["provenance_valid"] for case in cases),
        "unexpected_primary_domains": sum(
            case["unexpected_primary_domain_present"] for case in cases
        ),
        "cases": cases,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    """Return PASSED only when every required diagnostic check succeeds."""
    passed = (
        analysis["required_relationships_passed"] == 3
        and analysis["required_primary_domains_passed"] == 3
        and analysis["required_secondary_domains_passed"]
        == analysis["required_secondary_domains_applicable"]
        and analysis["required_suppressions_passed"] == 3
        and analysis["provenance_valid_cases"] == 3
        and analysis["unexpected_primary_domains"] == 0
    )
    return "PASSED" if passed else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic diagnostic JSON."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[object]) -> str:
    """Render ordered diagnostic values or None."""
    return ", ".join(str(value) for value in values) if values else "None"


def _flag(value: bool | None) -> str:
    """Render a diagnostic flag in its required form."""
    if value is None:
        return "N-A"
    return "YES" if value else "NO"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the required human-readable diagnostic report."""
    lines = [
        "# Batch 03 Compositional Semantic Diagnostic",
        "",
        "## Summary",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Required Relationships Passed:",
        f'{analysis["required_relationships_passed"]}/3',
        "",
        "Required Primary Domains Passed:",
        f'{analysis["required_primary_domains_passed"]}/3',
        "",
        "Required Secondary Domains Passed:",
        (
            f'{analysis["required_secondary_domains_passed"]}/'
            f'{analysis["required_secondary_domains_applicable"]}'
        ),
        "",
        "Required Suppressions Passed:",
        f'{analysis["required_suppressions_passed"]}/3',
        "",
        "Provenance Valid:",
        f'{analysis["provenance_valid_cases"]}/3',
        "",
        "Unexpected Primary Domains:",
        str(analysis["unexpected_primary_domains"]),
        "",
    ]
    for case in analysis["cases"]:
        lines.extend(
            (
                f'## Case {case["id"]}',
                "",
                "Primary Domain Candidates:",
                _display(case["primary_domain_candidates"]),
                "",
                "Secondary Domain Candidates:",
                _display(case["secondary_domain_candidates"]),
                "",
                "Format Support:",
                _display(case["format_support"]),
                "",
                "Format Suppression:",
                _display(case["format_suppression"]),
                "",
                "Intent Support:",
                _display(case["intent_support"]),
                "",
                "Warnings:",
                _display(case["warnings"]),
                "",
                "### Relationships",
                "",
            )
        )
        for relationship in case["relationships"]:
            lines.extend(
                (
                    (
                        f'- [SECTION:{relationship["source_section"]}] '
                        f'[SENTENCE:{relationship["sentence_index"]}] '
                        f'[TYPE:{relationship["relationship_type"]}] '
                        f'[STRENGTH:{relationship["strength"]}]'
                    ),
                    (
                        f'  Subject: {relationship["subject_component"]} = '
                        f'"{relationship["subject_text"]}"'
                    ),
                    (
                        f'  Object: {relationship["object_component"]} = '
                        f'"{relationship["object_text"]}"'
                    ),
                    f'  Reason: {relationship["reason_code"]}',
                    (
                        "  Evidence Indexes: "
                        f'{_display(relationship["evidence_indexes"])}'
                    ),
                    f'  Supports: {_display(relationship["supports"])}',
                    f'  Suppresses: {_display(relationship["suppresses"])}',
                    "",
                )
            )
        lines.extend(("### Diagnostic Flags", ""))
        for key in (
            "required_relationship_present",
            "required_primary_domain_present",
            "required_secondary_domain_present",
            "required_suppression_present",
            "unexpected_primary_domain_present",
            "provenance_valid",
        ):
            lines.extend((f"{key}:", _flag(case[key]), ""))
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render the required concise console diagnostic."""
    lines = [
        "=== BATCH 03 COMPOSITIONAL SEMANTIC DIAGNOSTIC ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Required Relationships:",
        f'{analysis["required_relationships_passed"]}/3',
        "",
        "Required Primary Domains:",
        f'{analysis["required_primary_domains_passed"]}/3',
        "",
        "Required Secondary Domains:",
        (
            f'{analysis["required_secondary_domains_passed"]}/'
            f'{analysis["required_secondary_domains_applicable"]}'
        ),
        "",
        "Required Suppressions:",
        f'{analysis["required_suppressions_passed"]}/3',
        "",
        "Provenance Valid:",
        f'{analysis["provenance_valid_cases"]}/3',
        "",
        "Unexpected Primary Domains:",
        str(analysis["unexpected_primary_domains"]),
        "",
    ]
    for case in analysis["cases"]:
        lines.append(
            f'{case["id"]} | relationships={case["semantic_relationship_count"]} '
            f'| primary={_flag(case["required_primary_domain_present"])} '
            f'| secondary={_flag(case["required_secondary_domain_present"])} '
            f'| suppression={_flag(case["required_suppression_present"])} '
            f'| provenance={_flag(case["provenance_valid"])}'
        )
    return "\n".join(lines)


def main() -> None:
    """Write deterministic reports and print the diagnostic summary."""
    analysis = analyze_diagnostic()
    (BATCH_ROOT / "compositional_semantic_diagnostic.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "compositional_semantic_diagnostic.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))


if __name__ == "__main__":
    main()
