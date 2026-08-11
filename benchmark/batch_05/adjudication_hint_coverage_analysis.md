# Batch 05 Adjudication Hint Coverage Analysis

## Summary

Target Cases:
4

Hints Observed:
0/4

Components Present But Uncombined:
4

Cross-Sentence Structure Required:
4

Missing Component Extraction:
4

## Component Matrix

### 044

Target hint: ADJUDICATION_ANALYTICAL_CONSTRAINT

| Component | Source Present | Context Detected | Section | Sentence | Role | Reason | Evidence Span |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| constraint_pressure | True | False | LEAD | 0 | None | None | ضغوطًا متزايدة |
| resource_limitation | True | False | BODY | 0 | None | None | ارتفاع معدلات استخدام الذخائر |
| capability | True | False | BODY | 1 | None | None | قدرة أوكرانيا على تأمين |
| consequence_impact | True | False | BODY | 3 | None | None | تحولت قضية الدفاع الجوي |

Failures: LEXICAL_SIGNAL_MISSING, COMPONENTS_PRESENT_BUT_NOT_COMBINED, LOCALITY_TOO_STRICT, CROSS_SENTENCE_STRUCTURE_REQUIRED, ROLE_ASSIGNMENT_MISMATCH, HINT_THRESHOLD_TOO_STRICT, HINT_ENGINE_GENERALIZATION_GAP

### 045

Target hint: ADJUDICATION_EXPLANATORY_TRANSFORMATION

| Component | Source Present | Context Detected | Section | Sentence | Role | Reason | Evidence Span |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| institution_action | True | False | LEAD | 0 | None | None | روسيا إعادة هيكلة قواتها |
| structural_change | True | False | LEAD | 0 | None | None | تغييرات تنظيمية وقيادية |
| new_organizational_unit | True | False | BODY | 0 | None | None | استحداث قوات مستقلة |
| role_evolution | True | False | BODY | 3 | None | None | تحول الطائرات غير المأهولة |
| transformation_context | True | False | LEAD | 0 | None | None | في ضوء الخبرات |

Failures: LEXICAL_SIGNAL_MISSING, COMPONENTS_PRESENT_BUT_NOT_COMBINED, LOCALITY_TOO_STRICT, CROSS_SENTENCE_STRUCTURE_REQUIRED, ROLE_ASSIGNMENT_MISMATCH, HINT_THRESHOLD_TOO_STRICT, HINT_ENGINE_GENERALIZATION_GAP

### 047

Target hint: ADJUDICATION_INSTITUTIONAL_POLICY_CONFLICT

| Component | Source Present | Context Detected | Section | Sentence | Role | Reason | Evidence Span |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| institution | True | False | LEAD | 0 | None | None | الجامعات الأميركية |
| government_scrutiny | True | False | LEAD | 0 | None | None | تدقيقًا متزايدًا من إدارة |
| policy_disagreement | True | False | LEAD | 0 | None | None | سياسات القبول الجامعي |
| protests_rights_conflict | True | False | LEAD | 0 | None | None | الاحتجاجات داخل الحرم الجامعي |
| legal_political_dispute | True | False | BODY | 2 | None | None | مواجهة سياسية وقانونية |
| institutional_autonomy | True | False | BODY | 2 | None | None | حدود استقلال الجامعات |

Failures: LEXICAL_SIGNAL_MISSING, COMPONENTS_PRESENT_BUT_NOT_COMBINED, LOCALITY_TOO_STRICT, CROSS_SENTENCE_STRUCTURE_REQUIRED, ROLE_ASSIGNMENT_MISMATCH, HINT_THRESHOLD_TOO_STRICT, HINT_ENGINE_GENERALIZATION_GAP

### 050

Target hint: ADJUDICATION_EVENT_PUBLIC_SAFETY

| Component | Source Present | Context Detected | Section | Sentence | Role | Reason | Evidence Span |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| serious_incident | True | False | LEAD | 0 | None | None | حادث إطلاق نار |
| casualties_injuries | True | False | LEAD | 0 | None | None | القتلى والمصابين |
| police_emergency_response | True | False | BODY | 0 | None | None | استنفار أجهزة الشرطة والطوارئ |
| investigation | True | False | BODY | 3 | None | None | بدأت السلطات التحقيق |

Failures: LEXICAL_SIGNAL_MISSING, COMPONENTS_PRESENT_BUT_NOT_COMBINED, LOCALITY_TOO_STRICT, CROSS_SENTENCE_STRUCTURE_REQUIRED, ROLE_ASSIGNMENT_MISMATCH, HINT_THRESHOLD_TOO_STRICT, HINT_ENGINE_GENERALIZATION_GAP

## Negative Controls

### 048

Any adjudication hint observed: False

- Prediction, uncertainty, future possibility, and an intelligence estimate produce uncertainty/prediction evidence but no constraint structure.
- The analytical-constraint hint correctly remains absent; future relaxation must still require constraint, resource/capability, and consequence components.

### 049

Any adjudication hint observed: False

- Repeated economy context and indicator evidence provide a useful deterministic control, with no unresolved event, transformation, constraint, or institutional-conflict structure.

## Locality Findings

All four target cases require cross-sentence composition. The relevant components are distributed across adjacent sentences or paragraphs; arbitrary document-wide mixing is neither necessary nor recommended.

## Generalization Findings

E. A mixture: the rules are conceptually aligned but combine literal vocabulary, missing component roles, an all-of threshold, and a synthetic single-sentence shape that does not reflect multi-sentence journalistic prose.

The synthetic tests place every literal component in one sentence. Real editorial prose introduces a subject in the lead, develops response or mechanism in following paragraphs, and states consequences or implications later, so the implementation overfits the synthetic test shape.

## Recommended Architecture Change

RELAX_LOCALITY_WITH_BOUNDED_WINDOW, ADD_COMPONENT_AGGREGATION, EXPAND_GENERIC_ROLE_COVERAGE, and ADD_CROSS_SENTENCE_COMPOSITION.

Use only a same-paragraph or adjacent-sentence window. Preserve KEEP_CURRENT_BEHAVIOR for controls 048 and 049, and retain substantive component requirements so prediction or uncertainty alone cannot form an analytical-constraint hint.
