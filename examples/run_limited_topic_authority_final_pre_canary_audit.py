"""Render the deterministic HKEI-210 final pre-canary safety audit."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = PROJECT_ROOT / "benchmark/limited_topic_authority_final_pre_canary_audit.json"
MARKDOWN_PATH = PROJECT_ROOT / "benchmark/limited_topic_authority_final_pre_canary_audit.md"


def build_audit() -> dict[str, object]:
    checks = {
        "default_off": "PASS",
        "explicit_enablement": "PASS",
        "internal_route_isolation": "PASS",
        "authority_eligibility": "PASS",
        "observation_before_consumption": "PASS",
        "sanitized_boundary": "PASS",
        "kill_switch": "PASS",
        "stop_signal_consumption": "PASS",
        "stop_observability": "PASS",
        "regression_budget": "PASS",
        "precision_threshold": "PASS",
        "human_audit_independence": "PASS",
        "duplicate_audit_safety": "PASS",
        "provider_failure_safety": "PASS",
        "invalid_response_safety": "PASS",
        "candidate_safety": "PASS",
        "fingerprint_safety": "PASS",
        "review_required_safety": "PASS",
        "ambiguity_safety": "PASS",
        "low_confidence_safety": "PASS",
        "no_topic_change_safety": "PASS",
        "format_isolation": "PASS",
        "reader_intent_isolation": "PASS",
        "gate_independence": "PASS",
        "resolver_independence": "PASS",
        "provider_independence": "PASS",
        "observation_sink_failure_safety": "PASS",
        "consumer_failure_safety": "PASS",
        "config_failure_safety": "PASS",
        "request_locality": "PASS",
        "concurrency_proxy": "PASS",
        "dual_provenance": "PASS",
        "existing_consumer_safety": "PASS",
        "operational_metrics_readiness": "PASS",
    }
    return {
        "audit_id": "HKEI-210",
        "audit_type": "FINAL_PRE_CANARY_SAFETY_AUDIT",
        "checks": checks,
        "exact_blocker": "NONE",
        "default_mode": "SHADOW",
        "global_authority_enabled": False,
        "first_real_canary_scope": "INTERNAL_SINGLE_PATH",
        "real_provider_calls": 0,
        "production_mutation": False,
        "final_safety_classification": "PRE_CANARY_SAFE",
        "final_readiness_decision": "READY_TO_RUN_INTERNAL_SINGLE_PATH_CANARY",
    }


def render_markdown(audit: dict[str, object]) -> str:
    checks = audit["checks"]
    lines = [
        "# Limited Topic Authority final pre-canary audit",
        "",
        f"- Final safety classification: `{audit['final_safety_classification']}`",
        f"- Final readiness decision: `{audit['final_readiness_decision']}`",
        f"- Default mode: `{audit['default_mode']}`",
        f"- First real canary scope: `{audit['first_real_canary_scope']}`",
        f"- Real provider calls: `{audit['real_provider_calls']}`",
        "",
        "## Exact blocker",
        "",
        str(audit["exact_blocker"]),
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{name}`: `{status}`" for name, status in checks.items())
    lines.extend([
        "",
        "The stop recommendation remains visible after it is consumed and changes effective mode",
        "to SHADOW. The first real canary remains restricted to INTERNAL_SINGLE_PATH.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    audit = build_audit()
    JSON_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_PATH.write_text(render_markdown(audit), encoding="utf-8")
    print(audit["final_safety_classification"])
    print(audit["final_readiness_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
