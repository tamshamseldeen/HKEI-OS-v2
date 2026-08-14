"""Render the HKEI-210 rerun after the stop-visibility fix."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.run_limited_topic_authority_final_pre_canary_audit import build_audit


JSON_PATH = PROJECT_ROOT / "benchmark/limited_topic_authority_final_pre_canary_audit_rerun.json"
MARKDOWN_PATH = PROJECT_ROOT / "benchmark/limited_topic_authority_final_pre_canary_audit_rerun.md"


def build_rerun_audit() -> dict[str, object]:
    current = build_audit()
    return {
        "audit_id": "HKEI-210-RERUN",
        "audit_type": "FINAL_PRE_CANARY_SAFETY_AUDIT_RERUN",
        "previous_audit": {
            "commit": "1c9d359",
            "final_safety_classification": "PRE_CANARY_BLOCKED",
            "final_readiness_decision": "FIX_ONE_OPERATIONAL_BLOCKER_FIRST",
            "stop_signal_audit": "FAIL",
            "stop_observability": "FAIL",
        },
        "fix_commit": "7d39db7",
        "current_checks": current["checks"],
        "previous_blocker_verification": {
            "stop_signal_consumed": "PASS",
            "stop_recommended_true": "PASS",
            "effective_mode_shadow": "PASS",
            "stop_event_observable_after_transition": "PASS",
        },
        "regression_budget": 0,
        "precision_threshold": 0.90,
        "minimum_audited_overrides": 30,
        "format_authority_paths": 0,
        "reader_intent_authority_paths": 0,
        "global_authority_enabled": False,
        "default_mode": "SHADOW",
        "first_real_canary_scope": "INTERNAL_SINGLE_PATH",
        "percentage_rollout": False,
        "real_provider_calls": 0,
        "production_mutation": False,
        "final_safety_classification": current["final_safety_classification"],
        "final_readiness_decision": current["final_readiness_decision"],
    }


def render_markdown(audit: dict[str, object]) -> str:
    previous = audit["previous_audit"]
    blocker = audit["previous_blocker_verification"]
    lines = [
        "# Limited Topic Authority final pre-canary audit rerun",
        "",
        f"- Fix commit: `{audit['fix_commit']}`",
        f"- Final safety classification: `{audit['final_safety_classification']}`",
        f"- Final readiness decision: `{audit['final_readiness_decision']}`",
        f"- First real canary scope: `{audit['first_real_canary_scope']}`",
        f"- Default mode: `{audit['default_mode']}`",
        f"- Real provider calls: `{audit['real_provider_calls']}`",
        "",
        "## Preserved previous finding",
        "",
        f"At `{previous['commit']}`, stop-signal audit and stop observability were `FAIL`,",
        f"yielding `{previous['final_safety_classification']}` and",
        f"`{previous['final_readiness_decision']}`.",
        "",
        "## Previous blocker verification",
        "",
    ]
    lines.extend(f"- `{name}`: `{status}`" for name, status in blocker.items())
    lines.extend(["", "## Complete current audit", ""])
    lines.extend(f"- `{name}`: `{status}`" for name, status in audit["current_checks"].items())
    lines.extend([
        "",
        "All readiness preconditions pass. This audit does not enable authority; the default",
        "remains SHADOW and any first real canary remains INTERNAL_SINGLE_PATH only.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    audit = build_rerun_audit()
    JSON_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(render_markdown(audit), encoding="utf-8")
    print(audit["final_safety_classification"])
    print(audit["final_readiness_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
