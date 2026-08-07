# Batch 02 Unseen Validation

| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 011 | GOVERNMENT | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 012 | SCIENCE | SCIENCE | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 013 | TECHNOLOGY | TECHNOLOGY | ANALYSIS | STANDARD_NEWS | UNDERSTAND_IMPACT | GET_UPDATE | NO |
| 014 | WORLD | WORLD | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 015 | GOVERNMENT | GOVERNMENT | SERVICE | STANDARD_NEWS | KNOW_ACTION | GET_UPDATE | NO |
| 016 | BUSINESS | BUSINESS | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 017 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 018 | SCIENCE | SCIENCE | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 019 | CULTURE | CULTURE | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 020 | TECHNOLOGY | TECHNOLOGY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |

## Summary

Total Cases:
10

Topic Accuracy:
90.00%

Editorial Format Accuracy:
80.00%

Reader Intent Accuracy:
80.00%

Fully Matched Cases:
7

Full Case Accuracy:
70.00%

## Topic Mismatches

ID:
011

Expected:
GOVERNMENT

Predicted:
GENERAL

Confidence:
LOW

Reason Codes:
- DEFAULT_GENERAL_TOPIC

Warnings:
- LOW_TOPIC_CONFIDENCE
- TOPIC_SIGNAL_INSUFFICIENT

## Editorial Format Mismatches

ID:
013

Expected:
ANALYSIS

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Reason Codes:
- DEFAULT_STANDARD_NEWS_FORMAT

Warnings:
None

ID:
015

Expected:
SERVICE

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Reason Codes:
- DEFAULT_STANDARD_NEWS_FORMAT

Warnings:
None

## Reader Intent Mismatches

ID:
013

Expected:
UNDERSTAND_IMPACT

Predicted:
GET_UPDATE

Confidence:
HIGH

Reason Codes:
- FORMAT_READER_INTENT_MAPPING
- DEFAULT_GET_UPDATE

Warnings:
None

ID:
015

Expected:
KNOW_ACTION

Predicted:
GET_UPDATE

Confidence:
HIGH

Reason Codes:
- FORMAT_READER_INTENT_MAPPING
- DEFAULT_GET_UPDATE

Warnings:
None
