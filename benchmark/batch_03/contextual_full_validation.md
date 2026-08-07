# Batch 03 Context-Aware Unseen Validation

| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 021 | GOVERNMENT | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 022 | ECONOMY | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 023 | POLITICS | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 024 | HEALTH | TECHNOLOGY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 025 | HEALTH | GOVERNMENT | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 026 | TECHNOLOGY | GENERAL | SERVICE | STANDARD_NEWS | KNOW_ACTION | GET_UPDATE | NO |
| 027 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 028 | WEATHER | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 029 | EDUCATION | GOVERNMENT | STANDARD_NEWS | GUIDE | GET_UPDATE | VERIFY_REQUIREMENTS | NO |
| 030 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |

## Summary

Total Cases:
10

Topic Accuracy:
20.00%

Editorial Format Accuracy:
80.00%

Reader Intent Accuracy:
80.00%

Full Case Accuracy:
20.00%

Fully Matched:
2

Contextual Evidence Used:
6

Contextual Suppression Used:
0

## Topic Mismatches

ID:
021

Expected:
GOVERNMENT

Predicted:
GENERAL

Confidence:
LOW

Contextual Support:
CLAIM_ATTRIBUTED

Contextual Suppression:
None

ID:
022

Expected:
ECONOMY

Predicted:
GENERAL

Confidence:
LOW

Contextual Support:
CLAIM_ATTRIBUTED

Contextual Suppression:
None

ID:
023

Expected:
POLITICS

Predicted:
GENERAL

Confidence:
LOW

Contextual Support:
None

Contextual Suppression:
None

ID:
024

Expected:
HEALTH

Predicted:
TECHNOLOGY

Confidence:
HIGH

Contextual Support:
TOPIC_TECHNOLOGY, TOPIC_SPORTS

Contextual Suppression:
None

ID:
025

Expected:
HEALTH

Predicted:
GOVERNMENT

Confidence:
MEDIUM

Contextual Support:
CLAIM_ATTRIBUTED, TOPIC_GOVERNMENT

Contextual Suppression:
None

ID:
026

Expected:
TECHNOLOGY

Predicted:
GENERAL

Confidence:
LOW

Contextual Support:
CLAIM_ATTRIBUTED

Contextual Suppression:
None

ID:
028

Expected:
WEATHER

Predicted:
GENERAL

Confidence:
LOW

Contextual Support:
None

Contextual Suppression:
None

ID:
029

Expected:
EDUCATION

Predicted:
GOVERNMENT

Confidence:
HIGH

Contextual Support:
CLAIM_ATTRIBUTED, TOPIC_GOVERNMENT

Contextual Suppression:
None

## Format Mismatches

ID:
026

Expected:
SERVICE

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Contextual Support:
CLAIM_ATTRIBUTED

Contextual Suppression:
None

ID:
029

Expected:
STANDARD_NEWS

Predicted:
GUIDE

Confidence:
MEDIUM

Contextual Support:
CLAIM_ATTRIBUTED, TOPIC_GOVERNMENT

Contextual Suppression:
None

## Reader Intent Mismatches

ID:
026

Expected:
KNOW_ACTION

Predicted:
GET_UPDATE

Confidence:
HIGH

Contextual Support:
CLAIM_ATTRIBUTED

Contextual Suppression:
None

ID:
029

Expected:
GET_UPDATE

Predicted:
VERIFY_REQUIREMENTS

Confidence:
HIGH

Contextual Support:
CLAIM_ATTRIBUTED, TOPIC_GOVERNMENT

Contextual Suppression:
None
