# Strict Trigger Diagnostic / Production Parity Audit

## Historical Result

HKEI-111:

Incremental TP:
1

Incremental FP:
0

## Production Result

HKEI-113:

Incremental TP:
1

Incremental FP:
2

False Positives:

batch_02/014
batch_02/019

## Logic Comparison

| Condition | HKEI-111 Diagnostic Candidate | Production Gate | Equivalent | Observed Difference |
|---|---|---|---|---|
| no primary semantic domain | required | required | YES | Both test an empty primary_domain_candidates collection. |
| contextual evidence exists | required | required | YES | Both test whether contextual items are present. |
| no semantic relationships | required | required | YES | Both require an empty relationships collection. |
| topic already requires adjudication | must be false | must be false | YES | Both use the same pre-strict topic-required baseline. |
| LOW confidence requirement | any classifier LOW | topic or format LOW | NO | The diagnostic also considers reader-intent LOW; it does not affect audited cases. |
| deterministic sufficiency | predicted TOPIC_* support exists | topic and format are each sufficient | NO | Production couples topic sufficiency to format confidence. |
| topic confidence handling | not part of sufficiency | HIGH non-GENERAL topic required | NO | Production defines a separate confidence-based topic sufficiency predicate. |
| format confidence handling | only contributes to any LOW | HIGH required for combined sufficiency | NO | LOW format confidence defeats production sufficiency even with deterministic topic support. |
| unresolved hint handling | not part of sufficiency | topic and format hints defeat sufficiency | NO | Production added hint-aware sufficiency conditions. |
| semantic conflict handling | not part of sufficiency | conflict defeats topic or format sufficiency | NO | Production added conflict-aware sufficiency conditions. |
| method-subject ambiguity handling | not part of sufficiency | ambiguity defeats topic sufficiency | NO | Production added ambiguity-aware topic sufficiency. |
| evaluation ordering | candidate evaluated after pre-strict decision | strict evaluated after existing-topic predicate | YES | Both evaluate strict logic only after the same pre-strict topic decision. |

## Case 014

| Field | Value |
|---|---|
| batch | batch_02 |
| id | 014 |
| expected_topic | WORLD |
| current_predicted_topic | WORLD |
| topic_match | True |
| topic_confidence | HIGH |
| format_confidence | LOW |
| primary_domain_candidates |  |
| semantic_relationship_count | 0 |
| contextual_item_count | 4 |
| existing_topic_required_before_strict | False |
| diagnostic_strict_candidate | False |
| production_strict_trigger | True |
| diagnostic_deterministic_sufficiency | True |
| production_deterministic_sufficiency | False |
| current_gate_scope | TOPIC_REQUIRED |
| trigger_signals | NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, UNRESOLVED_EVIDENCE_STACK_STRICT, FORMAT_LOW_CONFIDENCE |

## Case 019

| Field | Value |
|---|---|
| batch | batch_02 |
| id | 019 |
| expected_topic | CULTURE |
| current_predicted_topic | CULTURE |
| topic_match | True |
| topic_confidence | HIGH |
| format_confidence | LOW |
| primary_domain_candidates |  |
| semantic_relationship_count | 0 |
| contextual_item_count | 2 |
| existing_topic_required_before_strict | False |
| diagnostic_strict_candidate | False |
| production_strict_trigger | True |
| diagnostic_deterministic_sufficiency | True |
| production_deterministic_sufficiency | False |
| current_gate_scope | TOPIC_REQUIRED |
| trigger_signals | NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, UNRESOLVED_EVIDENCE_STACK_STRICT, FORMAT_LOW_CONFIDENCE |

## Case 050

| Field | Value |
|---|---|
| batch | batch_05 |
| id | 050 |
| expected_topic | CRIME |
| current_predicted_topic | EDUCATION |
| topic_match | False |
| topic_confidence | HIGH |
| format_confidence | LOW |
| primary_domain_candidates |  |
| semantic_relationship_count | 0 |
| contextual_item_count | 1 |
| existing_topic_required_before_strict | False |
| diagnostic_strict_candidate | True |
| production_strict_trigger | True |
| diagnostic_deterministic_sufficiency | False |
| production_deterministic_sufficiency | False |
| current_gate_scope | TOPIC_REQUIRED |
| trigger_signals | NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, UNRESOLVED_EVIDENCE_STACK_STRICT, FORMAT_LOW_CONFIDENCE |

## Control 049

| Field | Value |
|---|---|
| batch | batch_05 |
| id | 049 |
| expected_topic | ECONOMY |
| current_predicted_topic | ECONOMY |
| topic_match | True |
| topic_confidence | HIGH |
| format_confidence | MEDIUM |
| primary_domain_candidates | PRIMARY_DOMAIN_ECONOMY |
| semantic_relationship_count | 8 |
| contextual_item_count | 7 |
| existing_topic_required_before_strict | False |
| diagnostic_strict_candidate | False |
| production_strict_trigger | False |
| diagnostic_deterministic_sufficiency | True |
| production_deterministic_sufficiency | False |
| current_gate_scope | NOT_REQUIRED |
| trigger_signals |  |

## Root Cause

PRODUCTION_TRIGGER_NOT_EQUIVALENT_TO_VALIDATED_CANDIDATE

DETERMINISTIC_SUFFICIENCY_DEFINITION_DRIFT

The diagnostic treats matching contextual TOPIC_* support as deterministic sufficiency. Production instead requires both topic and format sufficiency; LOW format confidence therefore fires the trigger for 014 and 019.

Production can use the validated diagnostic sufficiency test to avoid 014 and 019 while retaining 050, which lacks TOPIC_EDUCATION contextual support.

## Recommended Action

ALIGN_PRODUCTION_TO_VALIDATED_STRICT_LOGIC

## Gate Freeze Decision

NOT SAFE

Diagnostic and production strict-trigger semantics are not aligned, and the two cross-batch false positives have not been intentionally accepted or eliminated.

## Current Same-Baseline Metrics

Diagnostic cases triggered: 1

Diagnostic incremental TP: 1

Diagnostic incremental FP: 0

Production cases triggered: 3

Production incremental TP: 1

Production incremental FP: 2
