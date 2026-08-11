# Semantic Adjudication Candidate-Universe Analysis

## Problem

Current Batch 05 shadow request coverage:

Topic:
0.00%

Format:
25.00%

Structurally valid requests can still be semantically incapable of correction when the target label is absent.

## Strategy Comparison

| Strategy | Topic Coverage | Avg Topic Candidates | Format Coverage | Avg Format Candidates | Avg Payload Chars | Scope Violations | Quality |
|---|---:|---:|---:|---:|---:|---:|---|
| CURRENT_STRUCTURED_ONLY | 52.00% | 2.00 | 42.86% | 1.57 | 81.46 | 0 | POOR |
| FULL_ENUM_FOR_REQUIRED_SCOPE | 100.00% | 15.00 | 100.00% | 12.00 | 247.88 | 0 | EXCELLENT |
| FULL_ENUM_FALLBACK_WHEN_EVIDENCE_THIN | 96.00% | 11.68 | 100.00% | 12.00 | 213.85 | 0 | ACCEPTABLE |
| FULL_ENUM_FALLBACK_WHEN_NO_SEMANTIC_DOMAIN | 100.00% | 14.56 | 42.86% | 1.57 | 210.54 | 0 | POOR |

## Batch-by-Batch Coverage

### CURRENT_STRUCTURED_ONLY

| Batch | Topic Required | Topic Coverage | Format Required | Format Coverage |
|---|---:|---:|---:|---:|
| batch_01 | 3 | 100.00% | 0 | 0.00% |
| batch_02 | 3 | 100.00% | 0 | 0.00% |
| batch_03 | 2 | 100.00% | 0 | 0.00% |
| batch_04 | 8 | 62.50% | 3 | 66.67% |
| batch_05 | 9 | 0.00% | 4 | 25.00% |

### FULL_ENUM_FOR_REQUIRED_SCOPE

| Batch | Topic Required | Topic Coverage | Format Required | Format Coverage |
|---|---:|---:|---:|---:|
| batch_01 | 3 | 100.00% | 0 | 0.00% |
| batch_02 | 3 | 100.00% | 0 | 0.00% |
| batch_03 | 2 | 100.00% | 0 | 0.00% |
| batch_04 | 8 | 100.00% | 3 | 100.00% |
| batch_05 | 9 | 100.00% | 4 | 100.00% |

### FULL_ENUM_FALLBACK_WHEN_EVIDENCE_THIN

| Batch | Topic Required | Topic Coverage | Format Required | Format Coverage |
|---|---:|---:|---:|---:|
| batch_01 | 3 | 100.00% | 0 | 0.00% |
| batch_02 | 3 | 100.00% | 0 | 0.00% |
| batch_03 | 2 | 100.00% | 0 | 0.00% |
| batch_04 | 8 | 100.00% | 3 | 100.00% |
| batch_05 | 9 | 88.89% | 4 | 100.00% |

### FULL_ENUM_FALLBACK_WHEN_NO_SEMANTIC_DOMAIN

| Batch | Topic Required | Topic Coverage | Format Required | Format Coverage |
|---|---:|---:|---:|---:|
| batch_01 | 3 | 100.00% | 0 | 0.00% |
| batch_02 | 3 | 100.00% | 0 | 0.00% |
| batch_03 | 2 | 100.00% | 0 | 0.00% |
| batch_04 | 8 | 100.00% | 3 | 66.67% |
| batch_05 | 9 | 100.00% | 4 | 25.00% |

## Candidate-Universe Architecture

The Gate controls when external semantic adjudication is allowed. The candidate universe controls what legal decisions the adjudicator may return. It must not become a second deterministic classifier.

A narrow set lowers ambiguity but can make correction impossible. A full enum gives broader semantic freedom while remaining schema-safe because every label is bounded by the current enums.

The provider may select only from the supplied enum-bounded universe, and a later Resolver must validate and apply the response. Non-required dimensions remain deterministic-only.

## Recommendation

USE_FULL_ENUM_FOR_REQUIRED_SCOPE

This policy maximizes correction possibility, preserves schema restriction and scope isolation, avoids benchmark-specific mappings, and is simple to audit.

Batch 01 has no persisted EditorialFormat expectation, so its Format-required cases are included in request-size and scope analysis but excluded from Format coverage denominators.
