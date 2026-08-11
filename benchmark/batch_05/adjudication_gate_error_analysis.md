# Batch 05 Adjudication Gate Error Analysis

## Baseline

Topic:
TP 7
FP 0
TN 1
FN 2

Topic Precision:
100%

Topic Recall:
77.78%

Format:
TP 1
FP 1
TN 5
FN 3

Format Precision:
50%

Format Recall:
25%

## Topic False Negatives

### 046

Scope: FORMAT_REQUIRED

Triggers: NO_PRIMARY_SEMANTIC_DOMAIN, ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK, CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED

Failure classes: TOPIC_FALSE_NEGATIVE, GATE_POLICY_TOO_STRICT, GATE_SIGNAL_AVAILABLE_BUT_UNUSED, TOPIC_MEDIUM_CONFIDENCE_AMBIGUITY, SPECIFIC_TOPIC_FALSE_CONFIDENCE, METHOD_SUBJECT_AMBIGUITY_NOT_EXPOSED

- MEDIUM topic confidence plus no primary domain was a generic unresolved-domain signal that the gate recorded but did not use to request topic adjudication.
- The particular method-versus-subject distinction was not structurally represented: ACTION_TARGETS_OBJECT did not identify a method/tool component or SCIENCE domain. A generic gate can identify unresolved domain ambiguity, but cannot select SCIENCE.

### 050

Scope: NOT_REQUIRED

Triggers: NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, FORMAT_LOW_CONFIDENCE

Failure classes: TOPIC_FALSE_NEGATIVE, GATE_SIGNAL_NOT_AVAILABLE, SPECIFIC_TOPIC_FALSE_CONFIDENCE, EVENT_DOMAIN_AMBIGUITY_NOT_EXPOSED

- The final topic was specific and HIGH confidence, while contextual evidence exposed attribution only and semantic evidence exposed no event relationship or primary domain.
- Violence, casualties, police response, investigation, and CRIME were absent from current structured evidence. Detecting them from text belongs upstream or to the adjudicator, not the gate.

## Format False Negatives

### 044

Scope: TOPIC_REQUIRED

Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, FORMAT_LOW_CONFIDENCE

Failure classes: FORMAT_FALSE_NEGATIVE, GATE_SIGNAL_NOT_AVAILABLE

- Neither contextual nor semantic evidence exposed cause, constraint, resource depletion, impact, consequence, interpretation, or FORMAT_ANALYSIS support.
- Low format confidence existed, but the missing ANALYSIS distinction was absent upstream; the gate cannot infer it from raw prose without becoming a classifier.

### 045

Scope: TOPIC_REQUIRED

Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, FORMAT_LOW_CONFIDENCE

Failure classes: FORMAT_FALSE_NEGATIVE, GATE_SIGNAL_NOT_AVAILABLE, EXPLAINER_SIGNAL_NOT_AVAILABLE

- No structured output exposed explanatory framing, mechanism, organizational transformation, or how/why structure.
- EXPLAINER_STRUCTURE_UNRESOLVED could not be emitted because no contextual or semantic EXPLAINER target existed upstream.

### 047

Scope: TOPIC_REQUIRED

Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP

Failure classes: FORMAT_FALSE_NEGATIVE, GATE_SIGNAL_NOT_AVAILABLE, INSTITUTIONAL_CONFLICT_SIGNAL_NOT_AVAILABLE

- Only uncertainty was exposed contextually; no relationship, primary domain, format support, institutional conflict, policy/legal implication, or interpretive structure was available.
- The ANALYSIS distinction is missing upstream rather than ignored by the gate.

## Format False Positive

### 048

Scope: TOPIC_AND_FORMAT_REQUIRED

Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK, CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED

Failure classes: FORMAT_FALSE_POSITIVE, PREDICTION_FALSE_ANALYSIS_TRIGGER, UNCERTAINTY_FALSE_ANALYSIS_TRIGGER

- ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK and CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED caused the format request.
- The persisted diagnosis attributes contextual FORMAT_ANALYSIS to prediction, uncertainty, future possibility, and an intelligence estimate, while SOURCE_TOO_THIN_FOR_ANALYSIS shows the final classifier correctly rejected that proxy.

## Control

### 049

Scope: NOT_REQUIRED

Triggers: None

Failure classes: CONTROL_CORRECTLY_AVOIDED

- Title/body signals, structured economic values, contextual topic support, a semantic relationship, and PRIMARY_DOMAIN_ECONOMY aligned with the HIGH-confidence topic.
- No ambiguity or format-conflict trigger was present, so NOT_REQUIRED correctly preserved deterministic sufficiency.

## Gate vs Upstream Responsibility

| ID | Error | Primary Owner | Signal Available? | Missing Distinction |
| --- | --- | --- | --- | --- |
| 044 | FORMAT_FALSE_NEGATIVE | CONTEXTUAL_EVIDENCE | No | CAUSE_CONSTRAINT_RESOURCE_DEPLETION_IMPACT_STRUCTURE, FORMAT_ANALYSIS_SUPPORT |
| 045 | FORMAT_FALSE_NEGATIVE | FORMAT_CLASSIFIER | No | EXPLANATORY_FRAMING, MECHANISM_OR_TRANSFORMATION_STRUCTURE, FORMAT_EXPLAINER_SUPPORT |
| 046 | TOPIC_FALSE_NEGATIVE | SHARED_UPSTREAM_AND_GATE | Yes, but unused | METHOD_SUBJECT_RELATIONSHIP, SCIENCE_OR_BIOLOGICAL_PRIMARY_DOMAIN |
| 047 | FORMAT_FALSE_NEGATIVE | CONTEXTUAL_EVIDENCE | No | INSTITUTIONAL_CONFLICT, POLICY_OR_LEGAL_IMPLICATION, CAUSE_CONSEQUENCE_OR_INTERPRETATION, FORMAT_ANALYSIS_SUPPORT |
| 048 | FORMAT_FALSE_POSITIVE | GATE | Yes, but misused | PRIMARY_SEMANTIC_DOMAIN, SEMANTIC_FORMAT_SUPPORT |
| 050 | TOPIC_FALSE_NEGATIVE | CONTEXTUAL_EVIDENCE | No | VIOLENT_INCIDENT_EVENT, FATALITIES_OR_INJURIES, POLICE_RESPONSE_OR_INVESTIGATION, CRIME_PRIMARY_DOMAIN |
| 049 | CONTROL_CORRECT | GATE | N/A | None |

The gate must not become a second classifier. Reading raw text, recognizing new domain vocabulary, interpreting event semantics, or deciding whether prose is analytical belongs upstream or to the adjudicator.

## Counterfactual Signals

| Signal | Cases Triggered | Topic Mismatches | Format Mismatches | Matched Cases |
| --- | ---: | ---: | ---: | ---: |
| MEDIUM_TOPIC_CONFIDENCE_WITHOUT_PRIMARY_DOMAIN | 1 | 1 | 1 | 0 |
| SPECIFIC_TOPIC_WITH_UNRESOLVED_DOMAIN | 3 | 3 | 1 | 0 |
| CONTEXTUAL_ANALYSIS_SUPPORT_WITH_FORMAT_MISMATCH | 1 | 1 | 1 | 0 |
| FORMAT_STRUCTURE_ABSENT | 3 | 3 | 3 | 0 |
| PREDICTION_ONLY_ANALYSIS_SUPPORT | 1 | 1 | 0 | 0 |
| EVENT_EVIDENCE_WITHOUT_DOMAIN_RESOLUTION | 4 | 4 | 1 | 0 |

These are conceptual diagnostics only. FORMAT_STRUCTURE_ABSENT and EVENT_EVIDENCE_WITHOUT_DOMAIN_RESOLUTION rely on persisted diagnostic truth and are not deployable gate predicates.

## Gate Precision vs Recall

Favor recall enough to surface unresolved deterministic errors, but constrain it with structured ambiguity evidence because false positives incur provider cost; Batch 05 supports a measured recall increase, not unconditional low-confidence or contextual-analysis triggers.

## Recommended Next Step

D. Combine refinement using existing structured ambiguity (A), additional upstream evidence (B), and adjudicator/provider architecture for semantics that should not be inferred by the gate (C).
