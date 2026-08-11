# Batch 05 Semantic Adjudication Shadow Plumbing Validation

## Summary

Cases:
10

Requests Created:
9

Requests Avoided:
1

Provider Calls:
9

Validated Responses:
9

Invalid Responses:
0

Provider Errors:
0

Topic Candidate Coverage:
100.00%

Format Candidate Coverage:
100.00%

Shadow Topic Mutations:
0

Shadow Format Mutations:
0

Shadow Intent Mutations:
0

## Case Table

| ID | Scope | Request | Provider Called | Validated | Deterministic Topic | Oracle Topic | Deterministic Format | Oracle Format | Shadow Mutation |
|---|---|---|---|---|---|---|---|---|---|
| 041 | TOPIC_REQUIRED | YES | YES | YES | GENERAL | POLITICS | STANDARD_NEWS | STANDARD_NEWS | NO |
| 042 | TOPIC_REQUIRED | YES | YES | YES | TECHNOLOGY | CRIME | STANDARD_NEWS | STANDARD_NEWS | NO |
| 043 | TOPIC_REQUIRED | YES | YES | YES | GENERAL | POLITICS | STANDARD_NEWS | STANDARD_NEWS | NO |
| 044 | TOPIC_AND_FORMAT_REQUIRED | YES | YES | YES | GENERAL | WORLD | STANDARD_NEWS | ANALYSIS | NO |
| 045 | TOPIC_AND_FORMAT_REQUIRED | YES | YES | YES | GENERAL | WORLD | STANDARD_NEWS | EXPLAINER | NO |
| 046 | TOPIC_AND_FORMAT_REQUIRED | YES | YES | YES | TECHNOLOGY | SCIENCE | STANDARD_NEWS | ANALYSIS | NO |
| 047 | TOPIC_AND_FORMAT_REQUIRED | YES | YES | YES | GENERAL | POLITICS | STANDARD_NEWS | ANALYSIS | NO |
| 048 | TOPIC_REQUIRED | YES | YES | YES | GENERAL | WORLD | STANDARD_NEWS | STANDARD_NEWS | NO |
| 049 | NOT_REQUIRED | NO | NO | NO | ECONOMY | N/A | STANDARD_NEWS | N/A | NO |
| 050 | TOPIC_REQUIRED | YES | YES | YES | EDUCATION | CRIME | STANDARD_NEWS | STANDARD_NEWS | NO |

## Invalid Response Probe

PASS

## Provider Failure Probe

PASS
