"""Diagnose Batch 04 contextual and semantic coverage without classifiers."""

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_benchmark_batch_02_validation import parse_source, read_manifest
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.semantics.deterministic_compositional_semantic_engine import (
    DeterministicCompositionalSemanticEngine,
)
from src.semantics.semantic_relationship import SemanticRelationship
from src.workflows.editorial_classification_workflow import (
    EditorialClassificationWorkflow,
)


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_04"
CASE_IDS = tuple(f"{case_id:03d}" for case_id in range(31, 41))
INSPECTED_ROLES = (
    "SUBJECT",
    "ACTOR",
    "ACTION",
    "AUTHORITY",
    "AFFECTED_AUDIENCE",
    "REQUIREMENT",
    "DEADLINE",
    "RESULT",
    "CONSEQUENCE",
    "WARNING",
    "ATTRIBUTION",
    "CLAIM",
    "PREDICTION",
    "UNCERTAINTY",
    "INTERPRETATION",
)
CASE_OBSERVATIONS = {
    "031": [
        "Persisted case 031 is weather reporting, not the specified security-authority/cross-border-attack scenario.",
        "The contextual layer exposed uncertainty and consequence cues but no domain-bearing subject, actor, action, or authority evidence, so no security-event composition was possible.",
    ],
    "032": [
        "Persisted case 032 is cement-price reporting, not the specified criminal/legal conviction and disputed-family-claim scenario.",
        "Attribution and a generic business actor were exposed, but they did not form a compositional relationship or domain candidate.",
    ],
    "033": [
        "Persisted case 033 is sports-training reporting, not the specified executive citizenship/immigration action and constitutional challenge.",
        "No contextual evidence was extracted; consequently both domain composition and format composition were absent.",
    ],
    "034": [
        "Persisted case 034 is a sports schedule, not the specified war/security pressure and resource-constraint analysis.",
        "The editorial result matched despite semantic non-use; the only contextual item was attribution and it produced no relationship or domain.",
    ],
    "035": [
        "Persisted case 035 is a vehicle price/specification guide, not the specified military restructuring and unmanned-systems explainer.",
        "Attribution and consequence evidence remained uncomposed, leaving both domain and explanatory-format support empty.",
    ],
    "036": [
        "Persisted case 036 is preventive health guidance, not the specified AI/biological-science development and dual-use analysis.",
        "Authority and uncertainty evidence produced no relationships or analysis-format support; the requested biological-science structure is therefore not tested by this source.",
    ],
    "037": [
        "Persisted case 037 is a health-sector memorandum, not the specified university/government institutional conflict and protests.",
        "No contextual evidence was extracted, so no primary-domain competition was represented semantically.",
    ],
    "038": [
        "Persisted case 038 is Ebola outbreak reporting, not the specified NATO/Russia intelligence estimate and possible future attack.",
        "One action-to-object relationship supported health, but that support was not promoted to a primary domain candidate and no format or intent support was produced.",
    ],
    "039": [
        "Persisted case 039 is gold-price reporting and matched ECONOMY without contextual items, relationships, or semantic candidates.",
        "The match is therefore a control showing that the prior workflow prediction was sufficient without recorded contextual or semantic contribution; this diagnostic does not invoke the topic classifier to attribute a more specific path.",
    ],
    "040": [
        "Persisted case 040 is petroleum/gas production reporting, not the specified CRIME control scenario.",
        "The matched ECONOMY result coexisted with authority and prediction evidence that remained uncomposed, showing the prior prediction did not require recorded semantic evidence.",
    ],
}
RECOMMENDATIONS = (
    "Add domain-bearing event/object composition that can promote relationship support into explicit primary and secondary domain candidates.",
    "Expand reusable security-event, legal-policy, institutional-conflict, military-transformation, biological-science, and intelligence-estimate composition classes only against correctly registered source material.",
    "Add explanatory-framing and analysis-framing composition based on structural relationships rather than case-specific terms.",
    "Keep workflow usage accounting aligned with relationship-level supports as well as promoted domain and format candidates.",
    "Resolve the mismatch between the persisted Batch 04 corpus and the case scenarios before using those scenarios to judge architectural coverage.",
)


def _source_fields(source: object) -> dict[str, object]:
    return {
        "title": source.title,
        "body": source.body,
        "source_name": source.source_name,
        "source_url": source.source_url,
        "published_at": None,
        "language": "ar",
        "country": None,
        "author": None,
        "images": (),
        "attachments": (),
        "category": None,
        "tags": (),
        "user_instruction": None,
    }


def _relationship_record(relationship: SemanticRelationship) -> dict[str, object]:
    return {
        "relationship_type": relationship.relationship_type.value,
        "source_section": relationship.source_section.value,
        "sentence_index": relationship.sentence_index,
        "subject_component": relationship.subject_component.value,
        "subject_text": relationship.subject_text,
        "object_component": relationship.object_component.value,
        "object_text": relationship.object_text,
        "strength": relationship.strength.value,
        "reason_code": relationship.reason_code,
        "supports": list(relationship.supports),
        "suppresses": list(relationship.suppresses),
    }


def _labels(items: tuple[object, ...], prefix: str) -> list[str]:
    return list(
        dict.fromkeys(
            label
            for item in items
            for label in item.supports
            if label.startswith(prefix)
        )
    )


def _failure_classes(
    *,
    contextual_count: int,
    relationship_count: int,
    primary_count: int,
    format_support_count: int,
    previous_format_match: bool,
    semantic_domain_was_used: bool,
) -> list[str]:
    failures: list[str] = []
    if contextual_count == 0:
        failures.append("CONTEXTUAL_EVIDENCE_MISSING")
    elif relationship_count == 0:
        failures.append("CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED")
    elif primary_count == 0:
        failures.append("SEMANTIC_RELATIONSHIP_PRESENT_WITHOUT_DOMAIN")
    if primary_count and not semantic_domain_was_used:
        failures.append("SEMANTIC_DOMAIN_PRESENT_BUT_NOT_RECORDED_AS_USED")
    if primary_count == 0:
        failures.append("DOMAIN_MODEL_COVERAGE_GAP")
    if not previous_format_match and format_support_count == 0:
        failures.append("FORMAT_SEMANTIC_COVERAGE_GAP")
    return failures


def analyze_coverage(
    *,
    batch_root: Path = BATCH_ROOT,
    classification_workflow: EditorialClassificationWorkflow | None = None,
    contextual_engine: DeterministicContextualEvidenceEngine | None = None,
    semantic_engine: DeterministicCompositionalSemanticEngine | None = None,
) -> dict[str, Any]:
    """Inspect each pipeline layer independently without editorial classifiers."""
    classification = classification_workflow or EditorialClassificationWorkflow()
    contextual = contextual_engine or DeterministicContextualEvidenceEngine()
    semantic = semantic_engine or DeterministicCompositionalSemanticEngine()
    manifest = {case["id"]: case for case in read_manifest(batch_root)}
    previous = json.loads(
        (batch_root / "editorial_validation.json").read_text(encoding="utf-8")
    )
    previous_by_id = {case["id"]: case for case in previous["cases"]}
    cases: list[dict[str, Any]] = []

    for case_id in CASE_IDS:
        persisted = parse_source(batch_root / manifest[case_id]["source_file"])
        classified = classification.process(**_source_fields(persisted))
        source = classified.ingestion.source
        contextual_evidence = contextual.analyze(
            source=source, user_instruction=None
        )
        semantic_evidence = semantic.compose(
            source=source, contextual_evidence=contextual_evidence
        )
        items = contextual_evidence.all_items
        prior = previous_by_id[case_id]
        relationships = [
            _relationship_record(relationship)
            for relationship in semantic_evidence.relationships
        ]
        role_counts = Counter(item.role.value for item in items)
        evidence_by_role = {
            role: [
                {
                    "reason_code": item.reason_code,
                    "source_section": item.source_section.value,
                    "sentence_index": item.sentence_index,
                    "supports": list(item.supports),
                    "suppresses": list(item.suppresses),
                }
                for item in items
                if item.role.value == role
            ]
            for role in INSPECTED_ROLES
        }
        domain_was_used = bool(
            semantic_evidence.primary_domain_candidates
            or semantic_evidence.secondary_domain_candidates
            or semantic_evidence.format_support
            or semantic_evidence.intent_support
        )
        cases.append(
            {
                "id": case_id,
                "previous_topic_match": prior["topic_match"],
                "previous_format_match": prior["format_match"],
                "previous_intent_match": prior["reader_intent_match"],
                "previous_full_match": prior["full_match"],
                "contextual_item_count": len(items),
                "contextual_role_counts": {
                    role: role_counts.get(role, 0) for role in INSPECTED_ROLES
                },
                "contextual_evidence_by_role": evidence_by_role,
                "contextual_topic_support": _labels(items, "TOPIC_"),
                "contextual_format_support": _labels(items, "FORMAT_"),
                "contextual_intent_support": _labels(items, "INTENT_"),
                "contextual_claim_support": _labels(items, "CLAIM_"),
                "contextual_suppressions": list(
                    dict.fromkeys(
                        label for item in items for label in item.suppresses
                    )
                ),
                "semantic_relationship_count": len(relationships),
                "semantic_relationship_types": list(
                    dict.fromkeys(
                        item["relationship_type"] for item in relationships
                    )
                ),
                "semantic_relationships": relationships,
                "semantic_primary_domain_candidates": list(
                    semantic_evidence.primary_domain_candidates
                ),
                "semantic_secondary_domain_candidates": list(
                    semantic_evidence.secondary_domain_candidates
                ),
                "semantic_format_support": list(semantic_evidence.format_support),
                "semantic_format_suppression": list(
                    semantic_evidence.format_suppression
                ),
                "semantic_intent_support": list(semantic_evidence.intent_support),
                "semantic_suppressions": list(semantic_evidence.all_suppressions),
                "semantic_warning_codes": list(semantic_evidence.warnings),
                "failure_classes": _failure_classes(
                    contextual_count=len(items),
                    relationship_count=len(relationships),
                    primary_count=len(semantic_evidence.primary_domain_candidates),
                    format_support_count=len(semantic_evidence.format_support),
                    previous_format_match=prior["format_match"],
                    semantic_domain_was_used=domain_was_used,
                ),
                "architectural_observations": CASE_OBSERVATIONS[case_id],
            }
        )

    failure_counts = Counter(
        failure for case in cases for failure in case["failure_classes"]
    )
    contextual_missing = [
        case["id"] for case in cases if case["contextual_item_count"] == 0
    ]
    uncomposed = [
        case["id"]
        for case in cases
        if case["contextual_item_count"] > 0
        and case["semantic_relationship_count"] == 0
    ]
    relationship_without_domain = [
        case["id"]
        for case in cases
        if case["semantic_relationship_count"] > 0
        and not case["semantic_primary_domain_candidates"]
    ]
    semantic_domains = [
        case["id"]
        for case in cases
        if case["semantic_primary_domain_candidates"]
    ]
    return {
        "batch": "batch_04",
        "case_count": len(cases),
        "cases_with_contextual_evidence": sum(
            case["contextual_item_count"] > 0 for case in cases
        ),
        "cases_with_semantic_relationships": sum(
            case["semantic_relationship_count"] > 0 for case in cases
        ),
        "cases_with_primary_domain_candidates": len(semantic_domains),
        "cases_with_secondary_domain_candidates": sum(
            bool(case["semantic_secondary_domain_candidates"]) for case in cases
        ),
        "cases_with_semantic_format_support": sum(
            bool(case["semantic_format_support"]) for case in cases
        ),
        "contextual_missing_cases": contextual_missing,
        "uncomposed_context_cases": uncomposed,
        "relationship_without_domain_cases": relationship_without_domain,
        "semantic_domain_cases": semantic_domains,
        "failure_class_counts": {
            name: failure_counts.get(name, 0)
            for name in (
                "CONTEXTUAL_EVIDENCE_MISSING",
                "CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED",
                "SEMANTIC_RELATIONSHIP_PRESENT_WITHOUT_DOMAIN",
                "SEMANTIC_DOMAIN_PRESENT_BUT_NOT_RECORDED_AS_USED",
                "DOMAIN_MODEL_COVERAGE_GAP",
                "FORMAT_SEMANTIC_COVERAGE_GAP",
            )
        },
        "why_semantic_evidence_used_was_zero": (
            "The validation usage metric counts primary or secondary domain candidates, "
            "semantic format support, or semantic intent support. All four were empty for "
            "all ten cases. Seven cases had contextual evidence, but six produced no "
            "relationship; case 038 produced one relationship whose health support was "
            "not promoted to a domain candidate. Thus the zero reflects observed semantic "
            "outputs, not a workflow/reporting omission of an existing domain candidate."
        ),
        "general_architectural_findings": {
            "context_extraction_coverage": (
                "Three cases had no contextual items; the other seven mostly exposed "
                "generic attribution, authority, uncertainty, consequence, or prediction cues."
            ),
            "semantic_composition_coverage": (
                "Six context-bearing cases remained uncomposed; only case 038 produced a relationship."
            ),
            "domain_modeling_coverage": (
                "No case produced a primary or secondary domain candidate; relationship-level "
                "health support in 038 was not promoted."
            ),
            "format_modeling_coverage": (
                "No case produced semantic format support or suppression, including all four prior format mismatches."
            ),
            "workflow_integration_behavior": (
                "The prior usage calculation accurately reported zero under its documented candidate/support criteria."
            ),
            "failure_scope": (
                "The evidence shows a mixture of extraction, composition, domain-model, and "
                "format-model coverage gaps. Topic and format failures precede and are "
                "independent of ReaderIntentClassifierV2."
            ),
            "corpus_specification_mismatch": (
                "The HKEI-093 case scenarios do not describe the persisted Batch 04 sources, "
                "so those requested conceptual structures cannot be evaluated from this corpus."
            ),
        },
        "recommended_next_architecture": list(RECOMMENDATIONS),
        "cases": cases,
    }


def render_json(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _display(values: list[object]) -> str:
    return ", ".join(str(value) for value in values) if values else "None"


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render the deterministic evidence-based diagnosis."""
    lines = [
        "# Batch 04 Semantic Coverage Failure Analysis",
        "",
        "## Summary",
        "",
        "Cases:", str(analysis["case_count"]), "",
        "Cases With Contextual Evidence:", str(analysis["cases_with_contextual_evidence"]), "",
        "Cases With Semantic Relationships:", str(analysis["cases_with_semantic_relationships"]), "",
        "Cases With Primary Semantic Domains:", str(analysis["cases_with_primary_domain_candidates"]), "",
        "Cases With Semantic Format Support:", str(analysis["cases_with_semantic_format_support"]), "",
        "### Failure Class Counts", "",
    ]
    for name, count in analysis["failure_class_counts"].items():
        lines.extend((f"{name}:", str(count), ""))
    lines.extend(("## Case Diagnostics", ""))
    for case in analysis["cases"]:
        lines.extend(
            (
                f'### Case {case["id"]}', "",
                "Previous Matches:",
                f'Topic={case["previous_topic_match"]}; Format={case["previous_format_match"]}; Intent={case["previous_intent_match"]}; Full={case["previous_full_match"]}', "",
                "Contextual Item Count:", str(case["contextual_item_count"]), "",
                "Contextual Role Counts:",
                ", ".join(f"{role}={count}" for role, count in case["contextual_role_counts"].items()), "",
                "Contextual Topic Support:", _display(case["contextual_topic_support"]), "",
                "Contextual Format Support:", _display(case["contextual_format_support"]), "",
                "Contextual Intent Support:", _display(case["contextual_intent_support"]), "",
                "Contextual Claim Support:", _display(case["contextual_claim_support"]), "",
                "Semantic Relationship Count:", str(case["semantic_relationship_count"]), "",
                "Semantic Relationship Types:", _display(case["semantic_relationship_types"]), "",
                "Primary Domain Candidates:", _display(case["semantic_primary_domain_candidates"]), "",
                "Secondary Domain Candidates:", _display(case["semantic_secondary_domain_candidates"]), "",
                "Semantic Format Support:", _display(case["semantic_format_support"]), "",
                "Semantic Format Suppression:", _display(case["semantic_format_suppression"]), "",
                "Semantic Intent Support:", _display(case["semantic_intent_support"]), "",
                "Semantic Suppressions:", _display(case["semantic_suppressions"]), "",
                "Semantic Warning Codes:", _display(case["semantic_warning_codes"]), "",
                "Failure Classes:", _display(case["failure_classes"]), "",
                "Architectural Observations:",
                *[f"- {observation}" for observation in case["architectural_observations"]],
                "", "#### Contextual Evidence by Role", "",
            )
        )
        for role, evidence in case["contextual_evidence_by_role"].items():
            if evidence:
                lines.append(
                    f'- {role}: '
                    + "; ".join(item["reason_code"] for item in evidence)
                )
        if not case["contextual_item_count"]:
            lines.append("None")
        lines.extend(("", "#### Semantic Relationships", ""))
        if not case["semantic_relationships"]:
            lines.extend(("None", ""))
        for relationship in case["semantic_relationships"]:
            lines.extend(
                (
                    f'- Type: {relationship["relationship_type"]}',
                    f'  Source: {relationship["source_section"]} sentence {relationship["sentence_index"]}',
                    f'  Subject: {relationship["subject_component"]} = "{relationship["subject_text"]}"',
                    f'  Object: {relationship["object_component"]} = "{relationship["object_text"]}"',
                    f'  Strength: {relationship["strength"]}',
                    f'  Reason Code: {relationship["reason_code"]}',
                    f'  Supports: {_display(relationship["supports"])}',
                    f'  Suppresses: {_display(relationship["suppresses"])}',
                    "",
                )
            )
    lines.extend(
        (
            "## Why Semantic Evidence Used Was Zero", "",
            analysis["why_semantic_evidence_used_was_zero"], "",
            "## Cross-Case Architectural Findings", "",
        )
    )
    finding_titles = {
        "context_extraction_coverage": "Context extraction coverage",
        "semantic_composition_coverage": "Semantic composition coverage",
        "domain_modeling_coverage": "Domain modeling coverage",
        "format_modeling_coverage": "Format modeling coverage",
        "workflow_integration_behavior": "Workflow/integration behavior",
        "failure_scope": "Failure scope",
        "corpus_specification_mismatch": "Corpus/specification mismatch",
    }
    for key, title in finding_titles.items():
        lines.extend((f"### {title}", "", analysis["general_architectural_findings"][key], ""))
    lines.extend(("## Recommended Next Architecture", ""))
    lines.extend(f"- {item}" for item in analysis["recommended_next_architecture"])
    lines.append("")
    return "\n".join(lines)


def render_console(analysis: dict[str, Any]) -> str:
    return "\n".join(
        (
            "=== BATCH 04 SEMANTIC COVERAGE FAILURE ANALYSIS ===", "",
            "Cases:", str(analysis["case_count"]), "",
            "Cases With Contextual Evidence:", str(analysis["cases_with_contextual_evidence"]), "",
            "Cases With Semantic Relationships:", str(analysis["cases_with_semantic_relationships"]), "",
            "Cases With Primary Semantic Domains:", str(analysis["cases_with_primary_domain_candidates"]), "",
            "Cases With Semantic Format Support:", str(analysis["cases_with_semantic_format_support"]),
        )
    )


def main() -> int:
    analysis = analyze_coverage()
    (BATCH_ROOT / "semantic_coverage_analysis.json").write_text(
        render_json(analysis), encoding="utf-8"
    )
    (BATCH_ROOT / "semantic_coverage_analysis.md").write_text(
        render_markdown(analysis), encoding="utf-8"
    )
    print(render_console(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
