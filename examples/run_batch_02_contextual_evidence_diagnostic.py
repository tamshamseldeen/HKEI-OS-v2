"""Run contextual evidence diagnostics over selected Batch 02 sources."""

from collections.abc import Iterable
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evidence.contextual_evidence_item import ContextualEvidenceItem
from src.evidence.deterministic_contextual_evidence_engine import (
    DeterministicContextualEvidenceEngine,
)
from src.evidence.evidence_strength import EvidenceStrength
from src.intake.normalized_source import NormalizedSource


BATCH_ROOT = PROJECT_ROOT / "benchmark" / "batch_02"
DIAGNOSTIC_CASE_IDS = ("011", "013", "015", "018", "019", "020")
_REQUIRED_TOPIC_SUPPORT = {
    "011": "TOPIC_GOVERNMENT",
    "013": "TOPIC_TECHNOLOGY",
    "015": "TOPIC_GOVERNMENT",
    "018": "TOPIC_SCIENCE",
    "019": "TOPIC_CULTURE",
    "020": "TOPIC_TECHNOLOGY",
}
_REQUIRED_FORMAT_SUPPORT = {
    "013": "FORMAT_ANALYSIS",
    "015": "FORMAT_SERVICE",
}
_REQUIRED_INTENT_SUPPORT = {
    "013": "INTENT_UNDERSTAND_IMPACT",
    "015": "INTENT_KNOW_ACTION",
}


@dataclass(frozen=True)
class DiagnosticSource:
    """Represent exact persisted source fields needed by the diagnostic."""

    case_id: str
    title: str
    body: str
    source_name: str
    source_url: str


def read_manifest(
    batch_root: Path = BATCH_ROOT,
) -> tuple[dict[str, str], ...]:
    """Read ordered local manifest entries without classifier dependencies."""
    manifest = json.loads(
        (batch_root / "manifest.json").read_text(encoding="utf-8")
    )
    return tuple(manifest["cases"])


def parse_source(path: Path) -> DiagnosticSource:
    """Parse the exact persisted Batch 02 Markdown source format."""
    content = path.read_text(encoding="utf-8")
    title_part, remainder = content.split("\n# Body\n", maxsplit=1)
    body_part, metadata = remainder.split("\n# Metadata\n", maxsplit=1)
    metadata_lines = [line for line in metadata.splitlines() if line]
    return DiagnosticSource(
        case_id=metadata_lines[5],
        title=title_part.removeprefix("# Title\n").strip(),
        body=body_part.strip(),
        source_name=metadata_lines[1],
        source_url=metadata_lines[3],
    )


def _count_values(values: Iterable[str]) -> dict[str, int]:
    """Count values in deterministic first-occurrence order."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _item_record(item: ContextualEvidenceItem) -> dict[str, object]:
    """Serialize exactly the required immutable evidence item fields."""
    return {
        "source_section": item.source_section.value,
        "sentence_index": item.sentence_index,
        "matched_text": item.matched_text,
        "evidence_level": item.evidence_level.value,
        "role": item.role.value,
        "strength": item.strength.value,
        "reason_code": item.reason_code,
        "supports": list(item.supports),
        "suppresses": list(item.suppresses),
    }


def _has_strong_support(
    items: tuple[ContextualEvidenceItem, ...],
    label: str,
) -> bool:
    """Return whether a label has at least one strong evidence item."""
    return any(
        label in item.supports and item.strength is EvidenceStrength.STRONG
        for item in items
    )


def analyze_diagnostic(
    *,
    batch_root: Path = BATCH_ROOT,
    engine: DeterministicContextualEvidenceEngine | None = None,
) -> dict[str, Any]:
    """Analyze six diagnostic cases without invoking editorial classifiers.

    Args:
        batch_root: Directory containing frozen Batch 02 source material.
        engine: Optional contextual evidence engine supplied for isolated tests.

    Returns:
        Complete machine-readable contextual evidence diagnostic.
    """
    active_engine = engine or DeterministicContextualEvidenceEngine()
    manifest_by_id = {case["id"]: case for case in read_manifest(batch_root)}
    cases: list[dict[str, Any]] = []
    for case_id in DIAGNOSTIC_CASE_IDS:
        source = parse_source(
            batch_root / manifest_by_id[case_id]["source_file"]
        )
        normalized_source = NormalizedSource(
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
        evidence = active_engine.analyze(
            source=normalized_source,
            user_instruction=None,
        )
        items = evidence.all_items
        supports_summary = _count_values(
            label for item in items for label in item.supports
        )
        suppresses_summary = _count_values(
            label for item in items for label in item.suppresses
        )
        roles_summary = _count_values(item.role.value for item in items)
        strength_counts = _count_values(item.strength.value for item in items)
        strength_summary = {
            strength.value: strength_counts.get(strength.value, 0)
            for strength in EvidenceStrength
        }
        required_topic = _REQUIRED_TOPIC_SUPPORT[case_id]
        required_format = _REQUIRED_FORMAT_SUPPORT.get(case_id)
        required_intent = _REQUIRED_INTENT_SUPPORT.get(case_id)
        sports_support = supports_summary.get("TOPIC_SPORTS", 0) > 0
        sports_suppressed = suppresses_summary.get("TOPIC_SPORTS", 0) > 0
        unexpected_sports = sports_support and not (
            case_id == "018" and sports_suppressed
        )
        cases.append(
            {
                "id": case_id,
                "headline_item_count": len(evidence.headline_items),
                "lead_item_count": len(evidence.lead_items),
                "body_item_count": len(evidence.body_items),
                "all_item_count": len(items),
                "supports_summary": supports_summary,
                "suppresses_summary": suppresses_summary,
                "roles_summary": roles_summary,
                "strength_summary": strength_summary,
                "has_required_topic_support": (
                    required_topic in supports_summary
                    and (
                        case_id not in {"013", "018", "020"}
                        or _has_strong_support(items, required_topic)
                    )
                ),
                "has_required_format_support": (
                    required_format in supports_summary
                    if required_format is not None
                    else None
                ),
                "has_required_intent_support": (
                    required_intent in supports_summary
                    if required_intent is not None
                    else None
                ),
                "has_unexpected_sports_signal": unexpected_sports,
                "has_contextual_suppression": bool(suppresses_summary),
                "items": [_item_record(item) for item in items],
            }
        )

    topic_passed = sum(case["has_required_topic_support"] for case in cases)
    format_cases = [
        case for case in cases if case["has_required_format_support"] is not None
    ]
    intent_cases = [
        case for case in cases if case["has_required_intent_support"] is not None
    ]
    return {
        "batch": "batch_02",
        "case_count": len(cases),
        "total_evidence_items": sum(case["all_item_count"] for case in cases),
        "cases_with_evidence": sum(case["all_item_count"] > 0 for case in cases),
        "cases_without_evidence": sum(case["all_item_count"] == 0 for case in cases),
        "required_topic_support_passed": topic_passed,
        "required_topic_support_applicable": len(cases),
        "required_format_support_passed": sum(
            case["has_required_format_support"] for case in format_cases
        ),
        "required_format_support_applicable": len(format_cases),
        "required_intent_support_passed": sum(
            case["has_required_intent_support"] for case in intent_cases
        ),
        "required_intent_support_applicable": len(intent_cases),
        "unexpected_sports_signals": sum(
            case["has_unexpected_sports_signal"] for case in cases
        ),
        "suppression_cases": sum(
            case["has_contextual_suppression"] for case in cases
        ),
        "cases": cases,
    }


def diagnostic_status(analysis: dict[str, Any]) -> str:
    """Return PASSED only when every required evidence check succeeds."""
    passed = (
        analysis["required_topic_support_passed"]
        == analysis["required_topic_support_applicable"]
        and analysis["required_format_support_passed"]
        == analysis["required_format_support_applicable"]
        and analysis["required_intent_support_passed"]
        == analysis["required_intent_support_applicable"]
        and analysis["unexpected_sports_signals"] == 0
    )
    return "PASSED" if passed else "FAILED"


def render_json(analysis: dict[str, Any]) -> str:
    """Render deterministic diagnostic JSON without separate source bodies."""
    return json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"


def _support_lines(
    summary: dict[str, int],
    prefix: str,
) -> list[str]:
    """Render support-label counts for one downstream namespace."""
    values = [
        f"{label}: {count}"
        for label, count in summary.items()
        if label.startswith(prefix)
    ]
    return values or ["None"]


def render_markdown(analysis: dict[str, Any]) -> str:
    """Render summary, support groups, roles, and ordered evidence detail."""
    lines = [
        "# Batch 02 Contextual Evidence Diagnostic",
        "",
        "## Summary",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Total Evidence Items:",
        str(analysis["total_evidence_items"]),
        "",
        "Cases With Evidence:",
        str(analysis["cases_with_evidence"]),
        "",
        "Cases Without Evidence:",
        str(analysis["cases_without_evidence"]),
        "",
        "Required Topic Support Passed:",
        (
            f"{analysis['required_topic_support_passed']}/"
            f"{analysis['required_topic_support_applicable']}"
        ),
        "",
        "Required Format Support Passed:",
        (
            f"{analysis['required_format_support_passed']}/"
            f"{analysis['required_format_support_applicable']}"
        ),
        "",
        "Required Intent Support Passed:",
        (
            f"{analysis['required_intent_support_passed']}/"
            f"{analysis['required_intent_support_applicable']}"
        ),
        "",
        "Unexpected Sports Signals:",
        str(analysis["unexpected_sports_signals"]),
        "",
        "Suppression Cases:",
        str(analysis["suppression_cases"]),
        "",
    ]
    for case in analysis["cases"]:
        lines.extend(
            (
                f"## Case {case['id']}",
                "",
                "Evidence Items:",
                str(case["all_item_count"]),
                "",
                "### Topic Support",
                "",
                *_support_lines(case["supports_summary"], "TOPIC_"),
                "",
                "### Format Support",
                "",
                *_support_lines(case["supports_summary"], "FORMAT_"),
                "",
                "### Intent Support",
                "",
                *_support_lines(case["supports_summary"], "INTENT_"),
                "",
                "### Claim Support",
                "",
                *_support_lines(case["supports_summary"], "CLAIM_"),
                "",
                "### Suppression",
                "",
            )
        )
        lines.extend(
            (
                [
                    f"{label}: {count}"
                    for label, count in case["suppresses_summary"].items()
                ]
                or ["None"]
            )
        )
        lines.extend(("", "### Roles", ""))
        lines.extend(
            f"{role}: {count}"
            for role, count in case["roles_summary"].items()
        )
        lines.extend(("", "### Evidence Detail", ""))
        for item in case["items"]:
            supports = ", ".join(item["supports"]) or "None"
            suppresses = ", ".join(item["suppresses"]) or "None"
            lines.extend(
                (
                    (
                        f"- [SECTION:{item['source_section']}] "
                        f"[SENTENCE:{item['sentence_index']}] "
                        f"[LEVEL:{item['evidence_level']}] "
                        f"[ROLE:{item['role']}] "
                        f"[STRENGTH:{item['strength']}] "
                        f'"{item["matched_text"]}"'
                    ),
                    f"  Reason: {item['reason_code']}",
                    f"  Supports: {supports}",
                    f"  Suppresses: {suppresses}",
                )
            )
        lines.append("")
    return "\n".join(lines)


def _status_value(value: bool | None) -> str:
    """Render one case quality value as YES, NO, or N-A."""
    if value is None:
        return "N-A"
    return "YES" if value else "NO"


def render_console(analysis: dict[str, Any]) -> str:
    """Render the required compact contextual evidence diagnostic."""
    lines = [
        "=== CONTEXTUAL EVIDENCE DIAGNOSTIC ===",
        "",
        "Cases:",
        str(analysis["case_count"]),
        "",
        "Required Topic Support:",
        (
            f"{analysis['required_topic_support_passed']}/"
            f"{analysis['required_topic_support_applicable']}"
        ),
        "",
        "Required Format Support:",
        (
            f"{analysis['required_format_support_passed']}/"
            f"{analysis['required_format_support_applicable']}"
        ),
        "",
        "Required Intent Support:",
        (
            f"{analysis['required_intent_support_passed']}/"
            f"{analysis['required_intent_support_applicable']}"
        ),
        "",
        "Unexpected Sports Signals:",
        str(analysis["unexpected_sports_signals"]),
        "",
        "Suppression Cases:",
        str(analysis["suppression_cases"]),
        "",
        "Status:",
        diagnostic_status(analysis),
        "",
    ]
    for case in analysis["cases"]:
        lines.append(
            f"{case['id']} | items={case['all_item_count']} | "
            f"topic={_status_value(case['has_required_topic_support'])} | "
            f"format={_status_value(case['has_required_format_support'])} | "
            f"intent={_status_value(case['has_required_intent_support'])} | "
            "unexpected_sports="
            f"{_status_value(case['has_unexpected_sports_signal'])}"
        )
    return "\n".join(lines)


def main() -> int:
    """Persist evidence diagnostic reports and return their quality status."""
    analysis = analyze_diagnostic()
    (BATCH_ROOT / "contextual_evidence_diagnostic.json").write_text(
        render_json(analysis),
        encoding="utf-8",
    )
    (BATCH_ROOT / "contextual_evidence_diagnostic.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    print(render_console(analysis))
    return 0 if diagnostic_status(analysis) == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
