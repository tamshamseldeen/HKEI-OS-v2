# OpenAI Adjudication Prompt Contract Audit

## Prompt Version

1.1

## Format Operational Coverage

12/12 formats are OPERATIONAL; none are LABEL_ONLY.

## Critical Pair Distinctness

- STANDARD_NEWS vs ANALYSIS: CLEAR — Event reporting is distinguished from structurally important causal interpretation.
- STANDARD_NEWS vs EXPLAINER: CLEAR — Reporting what happened is distinguished from organizing for mechanism understanding.
- STANDARD_NEWS vs SERVICE: CLEAR — Event reporting is distinguished from actionable service information.
- STANDARD_NEWS vs GUIDE: CLEAR — Event reporting is distinguished from ordered practical instruction.
- ANALYSIS vs EXPLAINER: PARTIAL_OVERLAP — Both explain, but ANALYSIS centers implications and causal tradeoffs while EXPLAINER centers mechanisms or concepts.
- SERVICE vs GUIDE: CLEAR — Actionable official information is distinguished from an instructional process or decision.
- ANALYSIS vs STANDARD_NEWS: CLEAR — The reverse comparison preserves the same interpretation-versus-reporting boundary.
- EXPLAINER vs GUIDE: CLEAR — Understanding a mechanism is distinguished from following practical instructions.

## Topic Semantics

Topic definition operational: TRUE.

## Authority / Method Protection

Authority-subject protection: TRUE.

Method-subject protection: TRUE.

## Deterministic Anchoring

Reduction strength: STRONG. The baseline follows source, evidence, and legal candidates.

## Structured Evidence

- contextual_supports: DEFINED_AND_ACTIONABLE
- contextual_suppressions: DEFINED_AND_ACTIONABLE
- semantic_relationships: DEFINED_AND_ACTIONABLE
- primary_domain_candidates: DEFINED_AND_ACTIONABLE
- secondary_domain_candidates: DEFINED_AND_ACTIONABLE
- semantic_format_support: DEFINED_AND_ACTIONABLE
- semantic_format_suppression: DEFINED_AND_ACTIONABLE
- topic_reason_codes: DEFINED_AND_ACTIONABLE
- topic_warnings: DEFINED_AND_ACTIONABLE
- format_reason_codes: DEFINED_AND_ACTIONABLE
- format_warnings: DEFINED_AND_ACTIONABLE

Suppression semantics correct: TRUE.

## Confidence and Ambiguity

Confidence semantics: CLEAR. Ambiguity guidance clear: TRUE.

## Prompt Injection / CoT Safety

Prompt injection boundary valid: TRUE. Chain-of-thought safe: TRUE.

## Prompt Economy

COMPACT; largest representative prompt: 6152 characters. Duplication: LOW.

## Contradictions

None.

## Benchmark Leakage

FALSE.

## HKEI-150 Failure Coverage

LABEL_SEMANTICS_UNDERSPECIFIED: ADDRESSED.

DETERMINISTIC_FORMAT_ANCHORING: ADDRESSED.

STRUCTURED_EVIDENCE_UNDERUSED: ADDRESSED.

## Overall Assessment

EXCELLENT

## Recommended Next Step

READY_FOR_LIVE_AB_COMPARISON
