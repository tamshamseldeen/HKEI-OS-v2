# Batch 06 Activation-to-Decision Gap Analysis

## Summary

Semantic activation increased materially without editorial accuracy improvement.

## Topic Evidence Reachability

- 051: EXPECTED_DOMAIN_NOT_EXTRACTED
- 053: EXPECTED_DOMAIN_EXTRACTED_AS_COMPONENT
- 054: EXPECTED_DOMAIN_NOT_EXTRACTED
- 055: ONTOLOGY_BOUNDARY
- 056: EXPECTED_DOMAIN_PRESENT_IN_RELATIONSHIP
- 060: EXPECTED_DOMAIN_EXTRACTED_AS_COMPONENT

## Domain Promotion

{"SUBJECT_ROLE_UNRESOLVED": 1, "DOMAIN_MAPPING_MISSING": 2, "COMPETING_DOMAIN_PRECEDENCE": 1, "RELATIONSHIP_TOO_WEAK": 1, "AUTHORITY_DOMINANCE": 1}

## Topic Classifier Consumption

Primary and secondary candidates and semantic suppressions are consumed; relationship support affects decisions primarily after promotion.

## Topic Gate Recall Regression

Case 055: FALSE_PRIMARY_DOMAIN_SUFFICIENCY.

## Format Semantic Support

- 052: EXPECTED_FORMAT_SUPPORT_NOT_EMITTED
- 054: WRONG_FORMAT_SUPPORT_EMITTED
- 056: WRONG_FORMAT_SUPPORT_EMITTED
- 057: NO_SEMANTIC_FORMAT_SIGNAL
- 058: WRONG_FORMAT_SUPPORT_EMITTED
- 059: EXPECTED_FORMAT_SUPPORT_NOT_EMITTED

## Format Classifier Consumption

No expected-format support was emitted; all three new supports were wrong or contradictory.

## Format Gate False Negatives

Cases 054, 056, and 059 remain false negatives.

## Reader Intent Dependency

Direct failures: 0; downstream failures: 6.

## Evidence Quantity vs Quality

YES

## False Semantic Confidence

Cases: 052, 054, 055, 056, 058, 059.

## Architectural Ownership

- 051: SHARED_UPSTREAM
- 052: FORMAT_SEMANTIC_MAPPING
- 053: DOMAIN_PROMOTION
- 054: FORMAT_SEMANTIC_MAPPING
- 055: DOMAIN_PROMOTION
- 056: DOMAIN_PROMOTION
- 057: FORMAT_SEMANTIC_MAPPING
- 058: FORMAT_SEMANTIC_MAPPING
- 059: FORMAT_SEMANTIC_MAPPING
- 060: DOMAIN_PROMOTION

## Dominant Root Cause

F_MIXED_ACTIVATION_TO_DECISION_GAP

## Recommended Next Step

COMBINATION_OF_PROMOTION_AND_CONSUMPTION
