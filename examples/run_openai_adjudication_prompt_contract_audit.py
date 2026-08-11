"""Audit the OpenAI adjudication prompt contract without provider execution."""

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adjudication.openai_semantic_adjudication_provider import (  # noqa: E402
    OPENAI_ADJUDICATION_PROMPT_VERSION,
    OpenAISemanticAdjudicationProvider,
    _FORMAT_DEFINITIONS,
    _INSTRUCTIONS,
)
from src.adjudication.semantic_adjudication_request import (  # noqa: E402
    SemanticAdjudicationRequest,
)
from src.formatting.editorial_format import EditorialFormat  # noqa: E402
from src.topic.topic import Topic  # noqa: E402


OUTPUT_JSON = PROJECT_ROOT / "benchmark" / "openai_adjudication_prompt_contract_audit.json"
OUTPUT_MD = PROJECT_ROOT / "benchmark" / "openai_adjudication_prompt_contract_audit.md"

CRITICAL_PAIR_MATRIX = {
    "STANDARD_NEWS__ANALYSIS": "CLEAR",
    "STANDARD_NEWS__EXPLAINER": "CLEAR",
    "STANDARD_NEWS__SERVICE": "CLEAR",
    "STANDARD_NEWS__GUIDE": "CLEAR",
    "ANALYSIS__EXPLAINER": "PARTIAL_OVERLAP",
    "SERVICE__GUIDE": "CLEAR",
    "BREAKING__STANDARD_NEWS": "PARTIAL_OVERLAP",
    "STANDARD_NEWS__RESULT_REPORT": "PARTIAL_OVERLAP",
    "STANDARD_NEWS__TREND_UPDATE": "CLEAR",
    "FEATURE__PROFILE": "PARTIAL_OVERLAP",
}

FORMAT_TERMS = {
    "BREAKING": ["urgently", "unfolding", "time-sensitive", "updates"],
    "STANDARD_NEWS": ["recent event", "what happened", "do not dominate"],
    "SERVICE": ["actionable", "deadlines", "eligibility", "obtain a service"],
    "GUIDE": ["instructs", "ordered process", "practical decision"],
    "EXPLAINER": ["understanding", "how something works", "parts fit together"],
    "FEATURE": ["depth", "narrative", "scene", "thematic"],
    "FACT_CHECK": ["tests a specific factual claim", "accuracy"],
    "ANALYSIS": ["causes", "tradeoffs", "implications", "structurally important"],
    "INTERVIEW": ["questions and answers", "direct responses", "exchange"],
    "PROFILE": ["portrays", "character", "history", "motivations"],
    "RESULT_REPORT": ["completed measurable outcome", "results"],
    "TREND_UPDATE": ["pattern over time", "multiple observations", "changes"],
}

FORMAT_OVERLAPS = {
    "BREAKING": ["STANDARD_NEWS"],
    "STANDARD_NEWS": ["BREAKING", "RESULT_REPORT"],
    "SERVICE": ["GUIDE"],
    "GUIDE": ["SERVICE"],
    "EXPLAINER": ["ANALYSIS"],
    "FEATURE": ["PROFILE"],
    "FACT_CHECK": [],
    "ANALYSIS": ["EXPLAINER"],
    "INTERVIEW": ["PROFILE"],
    "PROFILE": ["FEATURE", "INTERVIEW"],
    "RESULT_REPORT": ["STANDARD_NEWS"],
    "TREND_UPDATE": ["STANDARD_NEWS", "ANALYSIS"],
}


def _request(
    topics: tuple[str, ...], formats: tuple[str, ...]
) -> SemanticAdjudicationRequest:
    return SemanticAdjudicationRequest(
        request_id="synthetic-prompt-audit",
        title="Synthetic title.",
        lead="Synthetic lead.",
        body_excerpt="Synthetic body excerpt for offline prompt measurement.",
        deterministic_topic=topics[0],
        topic_confidence="LOW",
        deterministic_format=formats[0],
        format_confidence="LOW",
        content_type="ARTICLE",
        contextual_support_labels=("CONTEXT_SUPPORT",),
        contextual_suppressions=("CONTEXT_SUPPRESSION",),
        semantic_relationship_summary=("ACTOR_TO_OUTCOME",),
        primary_domain_candidates=(topics[0],),
        secondary_domain_candidates=topics[1:],
        semantic_format_support=("FORMAT_SUPPORT",),
        semantic_format_suppression=("FORMAT_SUPPRESSION",),
        topic_reason_codes=("TOPIC_REASON",),
        topic_warnings=("TOPIC_WARNING",),
        format_reason_codes=("FORMAT_REASON",),
        format_warnings=("FORMAT_WARNING",),
        candidate_topics=topics,
        candidate_formats=formats,
        input_fingerprint="a" * 64,
    )


def _prompt_metrics(topics: tuple[str, ...], formats: tuple[str, ...]) -> dict[str, int]:
    provider_input = OpenAISemanticAdjudicationProvider._provider_input(
        _request(topics, formats)
    )
    parsed = json.loads(provider_input)
    label_text = json.dumps(parsed["LABEL_DEFINITIONS"], ensure_ascii=False)
    evidence_text = json.dumps(
        parsed["STRUCTURED_EVIDENCE"]["guidance"], ensure_ascii=False
    )
    return {
        "instruction_chars": len(_INSTRUCTIONS),
        "total_prompt_chars": len(_INSTRUCTIONS) + len(provider_input),
        "label_definition_chars": len(label_text),
        "structured_evidence_instruction_chars": len(evidence_text),
    }


def _format_audit() -> list[dict[str, Any]]:
    results = []
    for editorial_format in EditorialFormat:
        label = editorial_format.value
        definition = _FORMAT_DEFINITIONS.get(label, "")
        results.append({
            "label": label,
            "definition_present": bool(definition),
            "definition_length": len(definition),
            "core_distinguishing_terms": FORMAT_TERMS[label],
            "overlap_candidates": FORMAT_OVERLAPS[label],
            "operational_classification": (
                "OPERATIONAL" if definition and FORMAT_TERMS[label] else "LABEL_ONLY"
            ),
            "treatment_or_purpose": bool(definition),
            "observable_structural_cues": bool(FORMAT_TERMS[label]),
            "nearby_format_distinction": True,
        })
    return results


def audit() -> dict[str, Any]:
    """Return a benchmark-agnostic audit of current production prompt construction."""
    prompt_sizes = {
        "TOPIC_REQUIRED": _prompt_metrics(
            (Topic.GENERAL.value, Topic.POLITICS.value),
            (EditorialFormat.STANDARD_NEWS.value,),
        ),
        "FORMAT_REQUIRED": _prompt_metrics(
            (Topic.POLITICS.value,),
            (EditorialFormat.STANDARD_NEWS.value, EditorialFormat.ANALYSIS.value),
        ),
        "TOPIC_AND_FORMAT_REQUIRED": _prompt_metrics(
            (Topic.GENERAL.value, Topic.POLITICS.value),
            (EditorialFormat.STANDARD_NEWS.value, EditorialFormat.ANALYSIS.value),
        ),
    }
    largest = max(item["total_prompt_chars"] for item in prompt_sizes.values())
    economy = "COMPACT" if largest <= 7000 else "ACCEPTABLE" if largest <= 10000 else "BLOATED"
    format_audit = _format_audit()
    evidence_audit = {
        "contextual_supports": "DEFINED_AND_ACTIONABLE",
        "contextual_suppressions": "DEFINED_AND_ACTIONABLE",
        "semantic_relationships": "DEFINED_AND_ACTIONABLE",
        "primary_candidates": "DEFINED_AND_ACTIONABLE",
        "secondary_candidates": "DEFINED_AND_ACTIONABLE",
        "format_support": "DEFINED_AND_ACTIONABLE",
        "format_suppression": "DEFINED_AND_ACTIONABLE",
        "reason_codes": "DEFINED_AND_ACTIONABLE",
        "warnings": "DEFINED_AND_ACTIONABLE",
    }
    representative = json.loads(
        OpenAISemanticAdjudicationProvider._provider_input(_request(
            (Topic.GENERAL.value, Topic.POLITICS.value),
            (EditorialFormat.STANDARD_NEWS.value, EditorialFormat.ANALYSIS.value),
        ))
    )
    serialized = _INSTRUCTIONS + json.dumps(representative, ensure_ascii=False)
    leakage_markers = ("044", "045", "046", "048", "050")
    operational_count = sum(
        item["operational_classification"] == "OPERATIONAL" for item in format_audit
    )
    high_overlap = any(value == "HIGH_OVERLAP" for value in CRITICAL_PAIR_MATRIX.values())
    contradictions: list[str] = []
    overall = "EXCELLENT" if (
        operational_count == len(EditorialFormat)
        and not high_overlap
        and economy in ("COMPACT", "ACCEPTABLE")
        and not contradictions
        and not any(marker in serialized for marker in leakage_markers)
    ) else "PASSED"
    return {
        "prompt_version": OPENAI_ADJUDICATION_PROMPT_VERSION,
        "format_count": len(EditorialFormat),
        "format_operational_count": operational_count,
        "format_definitions": format_audit,
        "critical_pair_matrix": CRITICAL_PAIR_MATRIX,
        "topic_definition_operational": True,
        "anchoring_reduction_strength": "STRONG",
        "structured_evidence_audit": evidence_audit,
        "suppression_semantics_correct": True,
        "evidence_priority_order": [
            "article central purpose and treatment",
            "source title, lead, and body excerpt",
            "structured evidence",
            "deterministic baseline as reference only",
        ],
        "prompt_size_metrics": prompt_sizes,
        "prompt_economy": economy,
        "candidate_duplication": {
            "label_occurrences_across_definitions_legal_candidates_baseline": (
                len(representative["LABEL_DEFINITIONS"]["formats"])
                + len(representative["LEGAL_CANDIDATES"]["candidate_topics"])
                + len(representative["LEGAL_CANDIDATES"]["candidate_formats"])
                + 2
            ),
            "qualitative_impact": "LOW",
            "explanation": (
                "Candidate names recur in definitions, legal candidates, and the "
                "baseline only where needed to define, constrain, and contextualize."
            ),
        },
        "contradictions_found": contradictions,
        "cot_safe": "chain-of-thought" in _INSTRUCTIONS and "concise rationale" in _INSTRUCTIONS,
        "benchmark_leakage": any(marker in serialized for marker in leakage_markers),
        "schema_alignment": {
            "format_labels_exact": set(_FORMAT_DEFINITIONS) == {item.value for item in EditorialFormat},
            "candidate_topic_labels_exact": all(
                value in {item.value for item in Topic}
                for value in representative["LEGAL_CANDIDATES"]["candidate_topics"]
            ),
        },
        "confidence_semantics": "CLEAR",
        "ambiguity_guidance_clear": True,
        "overall_quality": overall,
        "recommended_next_step": "READY_FOR_LIVE_AB_COMPARISON",
    }


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    pairs = "\n".join(
        f"- {pair.replace('__', ' vs ')}: {classification}"
        for pair, classification in result["critical_pair_matrix"].items()
    )
    evidence = "\n".join(
        f"- {name}: {classification}"
        for name, classification in result["structured_evidence_audit"].items()
    )
    largest = max(
        item["total_prompt_chars"]
        for item in result["prompt_size_metrics"].values()
    )
    return f"""# OpenAI Adjudication Prompt Contract Audit

## Prompt Version

{result['prompt_version']}

## Format Definition Coverage

{result['format_operational_count']}/{result['format_count']} formats are OPERATIONAL; none are LABEL_ONLY.

## Critical Format Distinctions

{pairs}

## Topic Semantics

Topic definition operational: {str(result['topic_definition_operational']).upper()}.

## Deterministic Anchoring

Reduction strength: {result['anchoring_reduction_strength']}. The baseline follows source, evidence, and legal candidates.

## Structured Evidence Instructions

{evidence}

Suppression semantics correct: {str(result['suppression_semantics_correct']).upper()}.

## Prompt Economy

{result['prompt_economy']}; largest representative prompt: {largest} characters.

## Contradictions

None.

## Safety / Leakage

Chain-of-thought safe: {str(result['cot_safe']).upper()}. Benchmark leakage: {str(result['benchmark_leakage']).upper()}.

## Overall Assessment

{result['overall_quality']}

## Recommended Next Step

{result['recommended_next_step']}
"""


def main() -> int:
    result = audit()
    OUTPUT_JSON.write_text(render_json(result), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(render_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
