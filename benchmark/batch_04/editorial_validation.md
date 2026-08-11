# Batch 04 Advanced Holdout Editorial Validation

| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 031 | WEATHER | WEATHER | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 032 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 033 | SPORTS | TECHNOLOGY | STANDARD_NEWS | GUIDE | GET_UPDATE | VERIFY_REQUIREMENTS | NO |
| 034 | SPORTS | SPORTS | GUIDE | GUIDE | VERIFY_REQUIREMENTS | VERIFY_REQUIREMENTS | YES |
| 035 | TECHNOLOGY | ECONOMY | GUIDE | STANDARD_NEWS | COMPARE_OPTIONS | GET_UPDATE | NO |
| 036 | HEALTH | HEALTH | GUIDE | STANDARD_NEWS | GET_GUIDANCE | GET_GUIDANCE | NO |
| 037 | HEALTH | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 038 | HEALTH | GENERAL | STANDARD_NEWS | BREAKING | GET_UPDATE | GET_UPDATE | NO |
| 039 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 040 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |

## Summary

Total Cases:
10

Topic Accuracy:
60.00%

Editorial Format Accuracy:
60.00%

Reader Intent Accuracy:
80.00%

Full Case Accuracy:
50.00%

Fully Matched:
5

Semantic Evidence Used:
0

Semantic Suppression Used:
0

## Topic Mismatches

ID:
033

Expected:
SPORTS

Predicted:
TECHNOLOGY

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Support:
None

Semantic Suppressions:
None

Reason Codes:
BODY_TOPIC_SIGNAL

Warnings:
LOW_TOPIC_CONFIDENCE

ID:
035

Expected:
TECHNOLOGY

Predicted:
ECONOMY

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Support:
CLAIM_ATTRIBUTED, FORMAT_ANALYSIS, INTENT_UNDERSTAND_IMPACT

Semantic Suppressions:
None

Reason Codes:
BODY_TOPIC_SIGNAL, ECONOMIC_STRUCTURE_SIGNAL

Warnings:
LOW_TOPIC_CONFIDENCE

ID:
037

Expected:
HEALTH

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Support:
None

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
038

Expected:
HEALTH

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Support:
CLAIM_ATTRIBUTED

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

## Format Mismatches

ID:
033

Expected:
STANDARD_NEWS

Predicted:
GUIDE

Confidence:
MEDIUM

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
GUIDE_STRUCTURE_SIGNAL

Warnings:
None

ID:
035

Expected:
GUIDE

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
DEFAULT_STANDARD_NEWS_FORMAT

Warnings:
None

ID:
036

Expected:
GUIDE

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
DEFAULT_STANDARD_NEWS_FORMAT

Warnings:
None

ID:
038

Expected:
STANDARD_NEWS

Predicted:
BREAKING

Confidence:
MEDIUM

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
BREAKING_IMMEDIACY_SIGNAL

Warnings:
None

## Reader Intent Mismatches

ID:
033

Expected:
GET_UPDATE

Predicted:
VERIFY_REQUIREMENTS

Confidence:
HIGH

Reason Codes:
FORMAT_READER_INTENT_MAPPING

Warnings:
None

ID:
035

Expected:
COMPARE_OPTIONS

Predicted:
GET_UPDATE

Confidence:
HIGH

Reason Codes:
FORMAT_READER_INTENT_MAPPING, DEFAULT_GET_UPDATE

Warnings:
None
