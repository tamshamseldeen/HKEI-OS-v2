"""Run expanded compositional semantic diagnostics for Batch 03."""

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
DIAGNOSTIC_CASE_IDS = ("021", "022", "023", "026", "028")
_EXPECTATIONS: dict[str, dict[str, object]] = {
    "021": {
        "relationships": (
            "INSTITUTION_BELONGS_TO_DOMAIN",
            "AUTHORITY_ACTS_ON_SUBJECT",
        ),
        "reason": None,
        "primary": "PRIMARY_DOMAIN_GOVERNMENT",
        "secondary": None,
        "format": None,
        "intent": None,
    },
    "022": {
        "relationships": ("INDICATOR_DESCRIBES_DOMAIN",),
        "reason": None,
        "primary": "PRIMARY_DOMAIN_ECONOMY",
        "secondary": None,
        "format": None,
        "intent": None,
    },
    "023": {
        "relationships": ("ACTOR_PERFORMS_ACTION",),
        "reason": "INTERNATIONAL_NEGOTIATION_DOMAIN_COMPOSITION",
        "primary": "PRIMARY_DOMAIN_POLITICS",
        "secondary": "SECONDARY_DOMAIN_ECONOMY",
        "format": None,
        "intent": None,
    },
    "026": {
        "relationships": ("RECOMMENDATION_TARGETS_AUDIENCE",),
        "reason": None,
        "primary": "PRIMARY_DOMAIN_TECHNOLOGY",
        "secondary": None,
        "format": "FORMAT_SERVICE",
        "intent": "INTENT_KNOW_ACTION",
    },
    "028": {
        "relationships": ("EVENT_HAS_OUTCOME",),
        "reason": None,
        "primary": "PRIMARY_DOMAIN_WEATHER",
        "secondary": None,
        "format": None,
        "intent": None,
    },
}


def _normalized_source(path: Path) -> NormalizedSource:
    """Build the exact category-free normalized benchmark source."""
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
    """Serialize exactly the required semantic relationship fields."""
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
    """Validate all referenced indexes and local section provenance."""
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
    """Analyze five persisted cases without invoking classifiers."""
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
            item.relationship_type.value for item in semantic_evidence.relationships
        )
        reason_codes = tuple(
            item.reason_code for item in semantic_evidence.relationships
        )
        reason = expected["reason"]
        required_relationship = bool(
            any(
                value in relationship_types
                for value in expected["relationships"]
            )
            and (reason is None or reason in reason_codes)
        )
        primary_present = (
            expected["primary"] in semantic_evidence.primary_domain_candidates
        )
        other_primaries = tuple(
            value
            for value in semantic_evidence.primary_domain_candidates
            if value != expected["primary"]
        )
        secondary = expected["secondary"]
        required_format = expected["format"]
        required_intent = expected["intent"]
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
                    _relationship_record(item)
                    for item in semantic_evidence.relationships
                ],
                "required_relationship_present": required_relationship,
                "required_primary_domain_present": primary_present,
                "required_secondary_domain_present": (
                    secondary in semantic_evidence.secondary_domain_candidates
                    if secondary is not None
                    else None
                ),
                "required_format_support_present": (
                    required_format in semantic_evidence.format_support
                    if required_format is not None
                    else None
                ),
                "required_intent_support_present": (
                    required_intent in semantic_evidence.intent_support
                    if required_intent is not None
                    else None
                ),
                "unexpected_primary_domain_present": bool(
                    not primary_present and other_primaries
                ),
                "provenance_valid": all(
                    _provenance_valid(item, contextual_evidence)
                    for item in semantic_evidence.relationships
                ),
            }
        )
    secondary_cases = [
        case
        for case in cases
        if case["required_secondary_domain_present"] is not None
    ]
    format_cases = [
        case
        for case in cases
        if case["required_format_support_present"] is not None
    ]
    intent_cases = [
        case
        for case in cases
        if case["required_intent_support_present"] is not None
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
        "required_format_support_passed": sum(
            case["required_format_support_present"] for case in format_cases
        ),
        "required_format_support_applicable": len(format_cases),
        "required_intent_support_passed": sum(
            case["required_intent_support_present"] for case in intent_cases
        ),
        "required_intent_support_applicable": len(intent_cases),
        "provenance_valid_cases": sum(case["provenance_valid"] for case in cases),
        "unexpected_primary_domains": sum(
            case["unexpected_primary_domain_present"] for case in cases
        ),
        "cases": cases,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    """Return PASSED only when every blocking diagnostic check succeeds."""
    passed = (
        analysis["required_relationships_passed"] == 5
        and analysis["required_primary_domains_passed"] == 5
        and analysis["required_format_support_passed"]
        == analysis["required_format_support_applicable"]
        and analysis["required_intent_support_passed"]
        == analysis["required_intent_support_applicable"]
        and analysis["provenance_valid_cases"] == 5
        and analysis["unexpected_primary_domains"] == 0
    )
    return "PASSED" if passed else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic diagnostic JSON without source bodies."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[object]) -> str:
    """Render ordered values or an explicit None."""
    return ", ".join(str(value) for value in values) if values else "None"


def _flag(value: bool | None) -> str:
    """Render one diagnostic flag as YES, NO, or N-A."""
    if value is None:
        return "N-A"
    return "YES" if value else "NO"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the required expanded semantic Markdown report."""
    lines = [
        "# Batch 03 Expanded Semantic Diagnostic",
        "",
        "## Summary",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Required Relationships Passed:",
        f'{analysis["required_relationships_passed"]}/5',
        "",
        "Required Primary Domains Passed:",
        f'{analysis["required_primary_domains_passed"]}/5',
        "",
        "Required Secondary Domains Passed:",
        f'{analysis["required_secondary_domains_passed"]}/{analysis["required_secondary_domains_applicable"]}',
        "",
        "Required Format Support Passed:",
        f'{analysis["required_format_support_passed"]}/{analysis["required_format_support_applicable"]}',
        "",
        "Required Intent Support Passed:",
        f'{analysis["required_intent_support_passed"]}/{analysis["required_intent_support_applicable"]}',
        "",
        "Provenance Valid:",
        f'{analysis["provenance_valid_cases"]}/5',
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
        for item in case["relationships"]:
            lines.extend(
                (
                    f'- [SECTION:{item["source_section"]}] [SENTENCE:{item["sentence_index"]}] [TYPE:{item["relationship_type"]}] [STRENGTH:{item["strength"]}]',
                    f'  Subject: {item["subject_component"]} = "{item["subject_text"]}"',
                    f'  Object: {item["object_component"]} = "{item["object_text"]}"',
                    f'  Reason: {item["reason_code"]}',
                    f'  Evidence Indexes: {_display(item["evidence_indexes"])}',
                    f'  Supports: {_display(item["supports"])}',
                    f'  Suppresses: {_display(item["suppresses"])}',
                    "",
                )
            )
        lines.extend(("### Diagnostic Flags", ""))
        for key in (
            "required_relationship_present",
            "required_primary_domain_present",
            "required_secondary_domain_present",
            "required_format_support_present",
            "required_intent_support_present",
            "unexpected_primary_domain_present",
            "provenance_valid",
        ):
            lines.extend((f"{key}:", _flag(case[key]), ""))
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    """Render the required expanded semantic console output."""
    lines = [
        "=== BATCH 03 EXPANDED SEMANTIC DIAGNOSTIC ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Required Relationships:",
        f'{analysis["required_relationships_passed"]}/5',
        "",
        "Required Primary Domains:",
        f'{analysis["required_primary_domains_passed"]}/5',
        "",
        "Required Secondary Domains:",
        f'{analysis["required_secondary_domains_passed"]}/{analysis["required_secondary_domains_applicable"]}',
        "",
        "Required Format Support:",
        f'{analysis["required_format_support_passed"]}/{analysis["required_format_support_applicable"]}',
        "",
        "Required Intent Support:",
        f'{analysis["required_intent_support_passed"]}/{analysis["required_intent_support_applicable"]}',
        "",
        "Provenance Valid:",
        f'{analysis["provenance_valid_cases"]}/5',
        "",
        "Unexpected Primary Domains:",
        str(analysis["unexpected_primary_domains"]),
        "",
    ]
    lines.extend(
        f'{case["id"]} | relationship={_flag(case["required_relationship_present"])} '
        f'| primary={_flag(case["required_primary_domain_present"])} '
        f'| format={_flag(case["required_format_support_present"])} '
        f'| intent={_flag(case["required_intent_support_present"])} '
        f'| provenance={_flag(case["provenance_valid"])}'
        for case in analysis["cases"]
    )
    return "\n".join(lines)


def main() -> int:
    """Write reports, print raw results, and return diagnostic status."""
    analysis = analyze_diagnostic()
    (BATCH_ROOT / "expanded_semantic_diagnostic.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "expanded_semantic_diagnostic.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0 if diagnostic_status(analysis) == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
