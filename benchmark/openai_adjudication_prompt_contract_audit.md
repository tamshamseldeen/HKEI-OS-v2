# OpenAI Adjudication Prompt Contract Audit

## Prompt Version

1.1

## Format Definition Coverage

12/12 formats are OPERATIONAL; none are LABEL_ONLY.

## Critical Format Distinctions

- STANDARD_NEWS vs ANALYSIS: CLEAR
- STANDARD_NEWS vs EXPLAINER: CLEAR
- STANDARD_NEWS vs SERVICE: CLEAR
- STANDARD_NEWS vs GUIDE: CLEAR
- ANALYSIS vs EXPLAINER: PARTIAL_OVERLAP
- SERVICE vs GUIDE: CLEAR
- BREAKING vs STANDARD_NEWS: PARTIAL_OVERLAP
- STANDARD_NEWS vs RESULT_REPORT: PARTIAL_OVERLAP
- STANDARD_NEWS vs TREND_UPDATE: CLEAR
- FEATURE vs PROFILE: PARTIAL_OVERLAP

## Topic Semantics

Topic definition operational: TRUE.

## Deterministic Anchoring

Reduction strength: STRONG. The baseline follows source, evidence, and legal candidates.

## Structured Evidence Instructions

- contextual_supports: DEFINED_AND_ACTIONABLE
- contextual_suppressions: DEFINED_AND_ACTIONABLE
- semantic_relationships: DEFINED_AND_ACTIONABLE
- primary_candidates: DEFINED_AND_ACTIONABLE
- secondary_candidates: DEFINED_AND_ACTIONABLE
- format_support: DEFINED_AND_ACTIONABLE
- format_suppression: DEFINED_AND_ACTIONABLE
- reason_codes: DEFINED_AND_ACTIONABLE
- warnings: DEFINED_AND_ACTIONABLE

Suppression semantics correct: TRUE.

## Prompt Economy

COMPACT; largest representative prompt: 6152 characters.

## Contradictions

None.

## Safety / Leakage

Chain-of-thought safe: TRUE. Benchmark leakage: FALSE.

## Overall Assessment

EXCELLENT

## Recommended Next Step

READY_FOR_LIVE_AB_COMPARISON
