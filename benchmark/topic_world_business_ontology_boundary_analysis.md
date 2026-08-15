# WORLD vs BUSINESS Topic Ontology Boundary Analysis

Case status: `ONTOLOGY_BOUNDARY_REQUIRES_ANALYSIS`. CANARY2-002 remains `UNSURE`; no Topic is frozen as truth.

## Finding

The entity, event, treatment, and impact are distinct. A company identity, asset ownership, or announcement source does not by itself make BUSINESS primary. BUSINESS requires sustained corporate or commercial treatment; WORLD requires the international/security event to organize the story; ECONOMY requires macro, market, trade, price, supply, production, or financial-impact treatment.

Current BUSINESS semantics are conceptually narrow but operational signals remain overbroad. WORLD is not merely geographic, yet its international-security boundary is underspecified. Event centrality exists but is underweighted relative to company identity, and no explicit owner role exists.

## Evidence

The historical audit found 15 unique mixed-pattern candidates without relabeling them. The synthetic set contains 24 new Arabic scenarios: 6 WORLD-primary, 6 BUSINESS-primary, 4 ECONOMY-primary, 4 genuinely ambiguous, and 4 controls.

Representability: 9 clearly representable, 11 representable with a secondary dimension lost, 4 forced-choice ambiguous, and 0 ontology mismatches.

## Decision

Single-label assessment: `SINGLE_LABEL_ADEQUATE_WITH_CLEARER_RULES`.

Provider confidence: `CONFIDENCE_INSUFFICIENT_FOR_ONTOLOGY_BOUNDARY`.

Architecture direction: `D. COMBINE_SEMANTIC_CLARIFICATION_AND_ROLE_PROTECTION`.

Pilot implication: `TOPIC_ONTOLOGY_SPECIFICATION_REQUIRED_BEFORE_PILOT`. Effective mode remains `SHADOW`; provider calls: 0; production modifications: none.
