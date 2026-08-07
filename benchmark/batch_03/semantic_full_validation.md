# Batch 03 Semantic-Aware Full Validation

| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 021 | GOVERNMENT | GOVERNMENT | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 022 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 023 | POLITICS | POLITICS | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 024 | HEALTH | HEALTH | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 025 | HEALTH | HEALTH | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 026 | TECHNOLOGY | TECHNOLOGY | SERVICE | SERVICE | KNOW_ACTION | KNOW_ACTION | YES |
| 027 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 028 | WEATHER | WEATHER | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 029 | EDUCATION | EDUCATION | STANDARD_NEWS | GUIDE | GET_UPDATE | VERIFY_REQUIREMENTS | NO |
| 030 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |

## Summary

Total Cases:
10

Topic Accuracy:
100.00%

Editorial Format Accuracy:
90.00%

Reader Intent Accuracy:
90.00%

Full Case Accuracy:
90.00%

Fully Matched:
9

Semantic Evidence Used:
8

Semantic Suppression Used:
3

## Previous Batch 03 Context-Aware

Topic:
20.00%

Format:
80.00%

Reader Intent:
80.00%

Full:
20.00%

## Topic Mismatches

None

## Format Mismatches

ID:
029

Expected:
STANDARD_NEWS

Predicted:
GUIDE

Semantic Primary:
PRIMARY_DOMAIN_EDUCATION

Semantic Format:
None

Semantic Suppression:
PRIMARY_DOMAIN_GOVERNMENT

## Intent Mismatches

ID:
029

Expected:
GET_UPDATE

Predicted:
VERIFY_REQUIREMENTS

Semantic Primary:
PRIMARY_DOMAIN_EDUCATION

Semantic Format:
None

Semantic Suppression:
PRIMARY_DOMAIN_GOVERNMENT
