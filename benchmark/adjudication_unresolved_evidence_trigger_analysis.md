# Generic Unresolved-Evidence Trigger Analysis

## Current Gate

Batch 05 Topic Recall:
88.89%

Remaining Topic False Negative:
050

## Candidate 1

UNRESOLVED_EVIDENCE_STACK

Cases triggered:
21

True positives:
9

False positives:
12

True negatives:
25

False negatives:
4

Incremental true positives:
1

Incremental false positives:
2

Precision:
42.86%

Recall:
69.23%

Specificity:
67.57%

Accuracy:
68.00%

Quality:
POOR

## Candidate 2

UNRESOLVED_EVIDENCE_STACK_STRICT

Cases triggered:
1

True positives:
1

False positives:
0

True negatives:
37

False negatives:
12

Incremental true positives:
1

Incremental false positives:
0

Precision:
100.00%

Recall:
7.69%

Specificity:
100.00%

Accuracy:
76.00%

Quality:
EXCELLENT

## Cross-Batch False Positives

| Batch | Candidate | New False Positives |
| --- | --- | ---: |
| batch_01 | UNRESOLVED_EVIDENCE_STACK | 0 |
| batch_01 | UNRESOLVED_EVIDENCE_STACK_STRICT | 0 |
| batch_02 | UNRESOLVED_EVIDENCE_STACK | 2 |
| batch_02 | UNRESOLVED_EVIDENCE_STACK_STRICT | 0 |
| batch_03 | UNRESOLVED_EVIDENCE_STACK | 0 |
| batch_03 | UNRESOLVED_EVIDENCE_STACK_STRICT | 0 |
| batch_04 | UNRESOLVED_EVIDENCE_STACK | 0 |
| batch_04 | UNRESOLVED_EVIDENCE_STACK_STRICT | 0 |
| batch_05 | UNRESOLVED_EVIDENCE_STACK | 0 |
| batch_05 | UNRESOLVED_EVIDENCE_STACK_STRICT | 0 |

## Critical Controls

050 captured by base: True

050 captured by strict: True

049 triggered by base: False

049 triggered by strict: False

## Recommendation

IMPLEMENT_STRICT_CANDIDATE
