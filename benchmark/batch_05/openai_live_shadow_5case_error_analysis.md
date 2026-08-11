# OpenAI Five-Case Live Adjudication Error Analysis

## Summary

Topic Accuracy: 60.00%

Format Accuracy: 0.00%

Valid Responses: 5/5

## Topic Findings

Three cases improved the deterministic Topic. Cases 044 and 046 preserved an incorrect deterministic Topic; 046 also exposes SCIENCE/TECHNOLOGY ontology overlap.

## Format Findings

All 3 Format-required cases preserved STANDARD_NEWS and missed ANALYSIS or EXPLAINER. Expected labels were available in every required candidate set.

## Deterministic Anchoring

Deterministic Format was preserved in 3/3 required cases (100.00%).

## Label Semantics

The provider receives labels such as ANALYSIS, EXPLAINER, and STANDARD_NEWS without operational definitions: LABEL_SEMANTICS_UNDERSPECIFIED.

## Structured Evidence Use

Case 046 preserved STANDARD_NEWS despite contextual FORMAT_ANALYSIS support. Cases 044/045 lacked comparable structured format semantics.

## Excerpt Adequacy

Cases 044/045 are classified EXCERPT_INFORMATION_GAP because partial excerpts accompanied incorrect required decisions and no semantic relationship summary. Other selected excerpts are sufficient for this diagnostic.

## Ambiguity Signal

Ambiguity was meaningful for 1 correct case and weak for 2 incorrect cases.

## Architectural Conclusion

LABEL_SEMANTICS_UNDERSPECIFIED with repeated DETERMINISTIC_FORMAT_ANCHORING; case 046 also shows STRUCTURED_EVIDENCE_UNDERUSED.

Primary classes: 044: LABEL_SEMANTICS_UNDERSPECIFIED, 045: LABEL_SEMANTICS_UNDERSPECIFIED, 046: STRUCTURED_EVIDENCE_UNDERUSED, 048: AMBIGUITY_SIGNAL_MEANINGFUL, 050: UNKNOWN

## Recommended Next Step

COMBINATION_OF_A_B_C
