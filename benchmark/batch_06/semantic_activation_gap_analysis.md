# Batch 06 Semantic Activation Gap Analysis

## Why HKEI-157 Did Not Move Batch 06

The synthetic suite exercised the real raw-text path, but its expressions matched the new component regexes directly. The Arabic holdout uses morphological, nominal, elliptical, and synonymous journalistic forms that do not normalize into the same components.

## Activation Funnel

- 051: LEXICAL_COMPONENTS
- 052: RELATIONSHIP_ACCEPTED
- 053: CONTEXTUAL_EVIDENCE
- 054: CONTEXTUAL_EVIDENCE
- 055: CONTEXTUAL_EVIDENCE
- 056: DOMAIN_PROMOTED
- 057: CONTEXTUAL_EVIDENCE
- 058: CONTEXTUAL_EVIDENCE
- 059: RELATIONSHIP_ACCEPTED
- 060: CONTEXTUAL_EVIDENCE

## Component Extraction

Most failures stop before reusable semantic components are normalized.

## Cross-Sentence Locality

Several relevant signals cross title/lead/body boundaries; the current body-adjacent window cannot combine those sections.

## Topic Failure Activation

Topic failures primarily lack normalized domain-bearing subjects or lose them to authority/actor precedence.

## Format Failure Activation

No case emits semantic format support.

## Format Gate False Negatives

Cases 054, 056, and 059 receive no new semantic format signal.

## Why Semantic Format Support Is 0/10

- 051: NO_VALID_FORMAT_STRUCTURE
- 052: FORMAT_COMPONENTS_EXTRACTED_BUT_NOT_COMPOSED
- 053: NO_VALID_FORMAT_STRUCTURE
- 054: FORMAT_COMPONENTS_NOT_EXTRACTED
- 055: NO_VALID_FORMAT_STRUCTURE
- 056: FORMAT_COMPONENTS_NOT_EXTRACTED
- 057: FORMAT_COMPONENTS_EXTRACTED_BUT_NOT_COMPOSED
- 058: FORMAT_COMPONENTS_NOT_EXTRACTED
- 059: RELATIONSHIP_EXISTS_BUT_FORMAT_MAPPING_MISSING
- 060: NO_VALID_FORMAT_STRUCTURE

## Synthetic vs Real Path

Path classification: SAME_PATH.

## Arabic Expression Findings

Observed categories include verb inflection, nominal and prepositional constructions, implicit subjects, headline ellipsis, multiword concepts, temporal phrasing, and synonymous journalistic phrasing.

## Test Realism Audit

Raw-text scenarios: 25; extraction bypasses: 0.

## Dominant Root Cause

B_REAL_TEXT_COMPONENT_EXTRACTION_GAP

## Recommended Next Step

IMPROVE_GENERIC_COMPONENT_EXTRACTION

## Architectural Ownership

- 051: SEMANTIC_COMPONENT_EXTRACTION
- 052: COMPOSITIONAL_RELATIONSHIP_ENGINE
- 053: LEXICAL_EXTRACTION
- 054: SEMANTIC_COMPONENT_EXTRACTION
- 055: SEMANTIC_COMPONENT_EXTRACTION
- 056: SEMANTIC_COMPONENT_EXTRACTION
- 057: COMPOSITIONAL_RELATIONSHIP_ENGINE
- 058: SEMANTIC_COMPONENT_EXTRACTION
- 059: FORMAT_SEMANTIC_MAPPING
- 060: SEMANTIC_COMPONENT_EXTRACTION
