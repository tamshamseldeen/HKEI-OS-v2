# Batch 05 Editorial Generalization Analysis

## Baseline

Batch 01 Topic:
100%

Batch 02 Full:
100%

Batch 03 Full:
100%

Batch 05 First Holdout:

Topic:
10%

Format:
60%

Intent:
60%

Full:
10%

## Failure Distribution

ACTOR_SUBJECT_CONFUSION:
2

CONTEXTUAL_FORMAT_OVERTRIGGER:
1

CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED:
1

CONTEXT_EXTRACTION_GAP:
2

CONTEXT_PRESENT_BUT_UNCOMPOSED:
6

CRIME_LEGAL_DOMAIN_GAP:
2

DETERMINISTIC_GENERALIZATION_LIMIT:
9

DOWNSTREAM_INTENT_FROM_WRONG_FORMAT:
4

EVENT_DOMAIN_MODEL_GAP:
4

FORMAT_ANALYSIS_STRUCTURE_GAP:
3

FORMAT_EXPLAINER_STRUCTURE_GAP:
1

GEOPOLITICAL_DOMAIN_GAP:
4

INSTITUTIONAL_CONFLICT_DOMAIN_GAP:
1

LOW_CONFIDENCE_FALLBACK:
7

METHOD_SUBJECT_CONFUSION:
2

MILITARY_DEFENSE_DOMAIN_GAP:
2

POLICY_LEGAL_DOMAIN_GAP:
2

PRIMARY_DOMAIN_MODEL_GAP:
9

SCIENCE_BIOLOGICAL_DOMAIN_GAP:
1

SEMANTIC_RELATIONSHIP_WITHOUT_DOMAIN:
1

## Case Diagnostics

### Case 041

Expected/Predicted Topic: POLITICS / GENERAL
Expected/Predicted Format: STANDARD_NEWS / STANDARD_NEWS
Expected/Predicted Intent: GET_UPDATE / GET_UPDATE

Contextual Items: 3
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_PRESENT_BUT_UNCOMPOSED, PRIMARY_DOMAIN_MODEL_GAP, EVENT_DOMAIN_MODEL_GAP, GEOPOLITICAL_DOMAIN_GAP, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP

- Uncertainty and attribution were extracted, but security authority, preventive government action, and the possible international event were not composed into a domain.
- The GENERAL low-confidence fallback makes this a topic adjudication candidate; STANDARD_NEWS and GET_UPDATE were already sufficient.

### Case 042

Expected/Predicted Topic: CRIME / TECHNOLOGY
Expected/Predicted Format: STANDARD_NEWS / STANDARD_NEWS
Expected/Predicted Intent: GET_UPDATE / GET_UPDATE

Contextual Items: 2
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_PRESENT_BUT_UNCOMPOSED, PRIMARY_DOMAIN_MODEL_GAP, METHOD_SUBJECT_CONFUSION, CRIME_LEGAL_DOMAIN_GAP, EVENT_DOMAIN_MODEL_GAP, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, MULTIPLE_COMPETING_TOPIC_SIGNALS, METHOD_SUBJECT_AMBIGUITY

- Surface phone/SIM signals supported TECHNOLOGY while the criminal conviction, prison sentence, drug case, and legal dispute did not produce a crime/legal event domain.
- This is method/surface-object versus primary-event confusion combined with a crime/legal ontology gap.

### Case 043

Expected/Predicted Topic: POLITICS / GENERAL
Expected/Predicted Format: STANDARD_NEWS / STANDARD_NEWS
Expected/Predicted Intent: GET_UPDATE / GET_UPDATE

Contextual Items: 1
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_PRESENT_BUT_UNCOMPOSED, PRIMARY_DOMAIN_MODEL_GAP, POLICY_LEGAL_DOMAIN_GAP, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP

- Executive action, citizenship policy, constitutional challenge, and judicial review produced neither a relationship nor a policy/legal primary domain.
- A reusable policy-plus-legal-plus-executive-action composition is absent; format and intent were already sufficient.

### Case 044

Expected/Predicted Topic: WORLD / GENERAL
Expected/Predicted Format: ANALYSIS / STANDARD_NEWS
Expected/Predicted Intent: UNDERSTAND_IMPACT / GET_UPDATE

Contextual Items: 0
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_EXTRACTION_GAP, PRIMARY_DOMAIN_MODEL_GAP, EVENT_DOMAIN_MODEL_GAP, GEOPOLITICAL_DOMAIN_GAP, MILITARY_DEFENSE_DOMAIN_GAP, FORMAT_ANALYSIS_STRUCTURE_GAP, DOWNSTREAM_INTENT_FROM_WRONG_FORMAT, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, FORMAT_LOW_CONFIDENCE

- No contextual evidence represented the ongoing war, air-defense constraint, resource depletion, military pressure, or consequences, so WORLD had no domain support.
- ANALYSIS structure was also unresolved; GET_UPDATE followed the wrong STANDARD_NEWS format, making the intent failure downstream.

### Case 045

Expected/Predicted Topic: WORLD / GENERAL
Expected/Predicted Format: EXPLAINER / STANDARD_NEWS
Expected/Predicted Intent: UNDERSTAND_EVENT / GET_UPDATE

Contextual Items: 0
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_EXTRACTION_GAP, PRIMARY_DOMAIN_MODEL_GAP, GEOPOLITICAL_DOMAIN_GAP, MILITARY_DEFENSE_DOMAIN_GAP, FORMAT_EXPLAINER_STRUCTURE_GAP, DOWNSTREAM_INTENT_FROM_WRONG_FORMAT, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, FORMAT_LOW_CONFIDENCE

- Military restructuring, organizational transformation, and unmanned systems produced no contextual items or military/geopolitical domain.
- The explanatory framing was not structurally represented, so EXPLAINER and its downstream UNDERSTAND_EVENT intent were missed.

### Case 046

Expected/Predicted Topic: SCIENCE / TECHNOLOGY
Expected/Predicted Format: ANALYSIS / STANDARD_NEWS
Expected/Predicted Intent: UNDERSTAND_IMPACT / GET_UPDATE

Contextual Items: 7
Semantic Relationships: 1
Primary Domains: None
Failure Classes: SEMANTIC_RELATIONSHIP_WITHOUT_DOMAIN, PRIMARY_DOMAIN_MODEL_GAP, METHOD_SUBJECT_CONFUSION, SCIENCE_BIOLOGICAL_DOMAIN_GAP, CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED, FORMAT_ANALYSIS_STRUCTURE_GAP, DOWNSTREAM_INTENT_FROM_WRONG_FORMAT, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: NO_PRIMARY_SEMANTIC_DOMAIN, METHOD_SUBJECT_AMBIGUITY, ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK

- AI was treated as the primary TECHNOLOGY signal while viruses, biological design, dual use, and consequences did not become a SCIENCE primary domain.
- A semantic relationship existed without a domain candidate, and contextual FORMAT_ANALYSIS plus INTENT_UNDERSTAND_IMPACT support was not promoted; the intent failure is downstream from format.

### Case 047

Expected/Predicted Topic: POLITICS / GENERAL
Expected/Predicted Format: ANALYSIS / STANDARD_NEWS
Expected/Predicted Intent: UNDERSTAND_IMPACT / GET_UPDATE

Contextual Items: 1
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_PRESENT_BUT_UNCOMPOSED, PRIMARY_DOMAIN_MODEL_GAP, ACTOR_SUBJECT_CONFUSION, POLICY_LEGAL_DOMAIN_GAP, INSTITUTIONAL_CONFLICT_DOMAIN_GAP, FORMAT_ANALYSIS_STRUCTURE_GAP, DOWNSTREAM_INTENT_FROM_WRONG_FORMAT, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP

- The university surface subject did not compose with federal scrutiny, discrimination allegations, protests, policy, and legal institutional conflict into POLITICS.
- ANALYSIS structure was unresolved, and the resulting intent failure is downstream from STANDARD_NEWS.

### Case 048

Expected/Predicted Topic: WORLD / GENERAL
Expected/Predicted Format: STANDARD_NEWS / STANDARD_NEWS
Expected/Predicted Intent: GET_UPDATE / GET_UPDATE

Contextual Items: 6
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_PRESENT_BUT_UNCOMPOSED, PRIMARY_DOMAIN_MODEL_GAP, GEOPOLITICAL_DOMAIN_GAP, CONTEXTUAL_FORMAT_OVERTRIGGER, LOW_CONFIDENCE_FALLBACK, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: TOPIC_LOW_CONFIDENCE, TOPIC_GENERAL_FALLBACK, NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK

- The intelligence estimate, uncertainty, prediction, Russia, and NATO produced contextual analytical support but no geopolitical primary domain.
- The final STANDARD_NEWS decision correctly resisted treating prediction or uncertainty alone as ANALYSIS; this is a format negative control despite the topic failure.

### Case 049

Expected/Predicted Topic: ECONOMY / ECONOMY
Expected/Predicted Format: STANDARD_NEWS / STANDARD_NEWS
Expected/Predicted Intent: GET_UPDATE / GET_UPDATE

Contextual Items: 7
Semantic Relationships: 8
Primary Domains: PRIMARY_DOMAIN_ECONOMY
Failure Classes: None
Candidate Triggers: None

- Existing title, body, structured economic values, contextual economy support, and compositional PRIMARY_DOMAIN_ECONOMY evidence aligned.
- The deterministic pipeline was sufficient for topic, STANDARD_NEWS, and GET_UPDATE; semantic absence must not be inferred because primary-domain evidence was present.

### Case 050

Expected/Predicted Topic: CRIME / EDUCATION
Expected/Predicted Format: STANDARD_NEWS / STANDARD_NEWS
Expected/Predicted Intent: GET_UPDATE / GET_UPDATE

Contextual Items: 1
Semantic Relationships: 0
Primary Domains: None
Failure Classes: CONTEXT_PRESENT_BUT_UNCOMPOSED, PRIMARY_DOMAIN_MODEL_GAP, ACTOR_SUBJECT_CONFUSION, CRIME_LEGAL_DOMAIN_GAP, EVENT_DOMAIN_MODEL_GAP, DETERMINISTIC_GENERALIZATION_LIMIT
Candidate Triggers: NO_PRIMARY_SEMANTIC_DOMAIN, CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP, FORMAT_LOW_CONFIDENCE

- Education surface signals outranked the shooting event, fatalities, injuries, police response, and investigation because no reusable violent-crime event domain was produced.
- STANDARD_NEWS and GET_UPDATE were sufficient; only topic needs broader event-domain adjudication.

## Reader Intent Dependency

Direct intent failures: 0.
Downstream-from-format intent failures: 4.
All observed intent failures follow incorrect format decisions, so the frozen evidence does not justify changing ReaderIntentClassifierV2.

## Candidate Semantic-Adjudication Triggers

| Trigger | Cases Triggered | Mismatches Captured | Correct Cases Triggered | Mismatch Precision |
| --- | ---: | ---: | ---: | ---: |
| TOPIC_LOW_CONFIDENCE | 7 | 7 | 0 | 100.00% |
| TOPIC_GENERAL_FALLBACK | 6 | 6 | 0 | 100.00% |
| NO_PRIMARY_SEMANTIC_DOMAIN | 9 | 9 | 0 | 100.00% |
| CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP | 6 | 6 | 0 | 100.00% |
| MULTIPLE_COMPETING_TOPIC_SIGNALS | 1 | 1 | 0 | 100.00% |
| METHOD_SUBJECT_AMBIGUITY | 2 | 2 | 0 | 100.00% |
| SEMANTIC_DOMAIN_CONFLICT | 0 | 0 | 0 | N/A |
| FORMAT_LOW_CONFIDENCE | 3 | 2 | 1 | 66.67% |
| ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK | 2 | 1 | 1 | 50.00% |
| EXPLAINER_STRUCTURE_UNRESOLVED | 0 | 0 | 0 | N/A |

## Deterministic vs Adjudication Boundary

A candidate boundary is to retain deterministic decisions when a primary semantic domain aligns with high-confidence topic evidence, while considering structured adjudication when existing outputs show no primary domain together with low topic confidence, GENERAL fallback, uncomposed contextual evidence, or method/subject ambiguity. Format adjudication can be narrower: low confidence plus unresolved structural support, while analytical context alone must not trigger adjudication because case 048 is a negative control. This boundary uses existing outputs and does not send every article to a provider.

## Architecture Decision Inputs

### Dictionary expansion

Generalization: limited to anticipated lexical forms. Maintenance: frequent dictionary review. Cost and latency: lowest. Determinism: highest. Provider dependence: none. Auditability: direct, but interactions and omissions grow difficult to reason about.

### Deterministic semantic ontology expansion

Generalization: better across reusable event, actor, subject, policy, legal, military, scientific, and format relationships. Maintenance: substantial ontology and composition work. Cost and latency: low at runtime. Determinism: high. Provider dependence: none. Auditability: strong when provenance is preserved.

### Structured semantic adjudication fallback

Generalization: potentially broad when deterministic evidence is ambiguous or incomplete. Maintenance: schemas, prompts, evaluation, and provider controls. Cost and latency: higher but gated. Determinism: lower unless outputs are constrained and validated. Provider dependence: explicit. Auditability: viable with recorded triggers, inputs, structured outputs, and deterministic fallback behavior.

## Required Conclusion

1. The dominant failure is not purely lexical; lexical surface cues contribute to cases 042, 046, 047, and 050, but several cases fall back despite meaningful events.
2. Composition is a dominant boundary: six context-bearing failures have no relationship, and case 046 has a relationship without a domain.
3. The current deterministic semantic domain ontology is not broad enough for the observed geopolitical, crime/legal, military, science/biological, policy/legal, institutional-conflict, and violent-event structures.
4. Adding case-specific phrases would constitute overfitting; improvements should represent reusable event, role, relationship, and framing structures.
5. Reader intent can remain downstream of Format because all four intent failures are explained by wrong format decisions.
6. The frozen evidence supports evaluating an adjudication fallback, but does not define a final production policy.
7. Existing signals that can gate evaluation include missing primary semantic domain, low topic confidence, GENERAL fallback, contextual evidence without relationships, method/subject ambiguity, format low confidence, and unresolved analytical context—with case 048 constraining over-triggering.
