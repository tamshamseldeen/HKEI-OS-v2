# Batch 02 Context-Aware Topic Validation

| ID | Expected Topic | Predicted Topic | Confidence | Match | Contextual Support | Contextual Suppression |
| --- | --- | --- | --- | --- | --- | --- |
| 011 | GOVERNMENT | GOVERNMENT | MEDIUM | YES | TOPIC_GOVERNMENT | None |
| 012 | SCIENCE | SCIENCE | LOW | YES | None | None |
| 013 | TECHNOLOGY | TECHNOLOGY | HIGH | YES | TOPIC_TECHNOLOGY, TOPIC_BUSINESS | None |
| 014 | WORLD | WORLD | HIGH | YES | TOPIC_WORLD | None |
| 015 | GOVERNMENT | GOVERNMENT | HIGH | YES | TOPIC_GOVERNMENT | None |
| 016 | BUSINESS | BUSINESS | HIGH | YES | TOPIC_BUSINESS | None |
| 017 | ECONOMY | ECONOMY | HIGH | YES | TOPIC_ECONOMY | None |
| 018 | SCIENCE | SCIENCE | HIGH | YES | TOPIC_SCIENCE, TOPIC_SPORTS | TOPIC_SPORTS |
| 019 | CULTURE | CULTURE | HIGH | YES | TOPIC_CULTURE | None |
| 020 | TECHNOLOGY | TECHNOLOGY | MEDIUM | YES | TOPIC_TECHNOLOGY | None |

## Summary

Total Cases:
10

Matched:
10

Mismatched:
0

Accuracy:
100.00%

Contextual Selection Used:
9

Contextual Suppression Used:
1

## Mismatches

None
