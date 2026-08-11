# Batch 05 Advanced-Risk Editorial Holdout Validation

| ID | Expected Topic | Predicted Topic | Expected Format | Predicted Format | Expected Intent | Predicted Intent | Full Match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 041 | POLITICS | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 042 | CRIME | TECHNOLOGY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 043 | POLITICS | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 044 | WORLD | GENERAL | ANALYSIS | STANDARD_NEWS | UNDERSTAND_IMPACT | GET_UPDATE | NO |
| 045 | WORLD | GENERAL | EXPLAINER | STANDARD_NEWS | UNDERSTAND_EVENT | GET_UPDATE | NO |
| 046 | SCIENCE | TECHNOLOGY | ANALYSIS | STANDARD_NEWS | UNDERSTAND_IMPACT | GET_UPDATE | NO |
| 047 | POLITICS | GENERAL | ANALYSIS | STANDARD_NEWS | UNDERSTAND_IMPACT | GET_UPDATE | NO |
| 048 | WORLD | GENERAL | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |
| 049 | ECONOMY | ECONOMY | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | YES |
| 050 | CRIME | EDUCATION | STANDARD_NEWS | STANDARD_NEWS | GET_UPDATE | GET_UPDATE | NO |

## Summary

Total Cases:
10

Topic Accuracy:
10.00%

Editorial Format Accuracy:
60.00%

Reader Intent Accuracy:
60.00%

Full Case Accuracy:
10.00%

Fully Matched:
1

Cases With Contextual Evidence:
8

Cases With Semantic Relationships:
2

Cases With Primary Semantic Domain:
1

Cases With Semantic Format Support:
0

Semantic Evidence Used:
1

Semantic Suppression Used:
0

## Topic Mismatches

ID:
041

Expected:
POLITICS

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
CLAIM_UNCERTAIN, CLAIM_ATTRIBUTED

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Supporting Signals:
INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
042

Expected:
CRIME

Predicted:
TECHNOLOGY

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
CLAIM_UNCERTAIN, TOPIC_BUSINESS

Semantic Suppressions:
None

Reason Codes:
TITLE_TOPIC_SIGNAL, BODY_TOPIC_SIGNAL

Supporting Signals:
TITLE_TECHNOLOGY_SIGNAL, BODY_TECHNOLOGY_SIGNAL

Warnings:
LOW_TOPIC_CONFIDENCE

ID:
043

Expected:
POLITICS

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
CLAIM_UNCERTAIN

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Supporting Signals:
INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
044

Expected:
WORLD

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
None

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Supporting Signals:
INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
045

Expected:
WORLD

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
None

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Supporting Signals:
INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
046

Expected:
SCIENCE

Predicted:
TECHNOLOGY

Confidence:
MEDIUM

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
TOPIC_TECHNOLOGY, CLAIM_UNCERTAIN, FORMAT_ANALYSIS, INTENT_UNDERSTAND_IMPACT

Semantic Suppressions:
None

Reason Codes:
TITLE_TOPIC_SIGNAL, BODY_TOPIC_SIGNAL, LEGACY_CONTENT_TYPE_TOPIC_SIGNAL, CONTEXTUAL_TOPIC_EVIDENCE

Supporting Signals:
TITLE_TECHNOLOGY_SIGNAL, BODY_TECHNOLOGY_SIGNAL, LEGACY_TOPIC_SUPPORT, CONTEXTUAL_TOPIC_SUPPORT

Warnings:
None

ID:
047

Expected:
POLITICS

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
CLAIM_UNCERTAIN

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Supporting Signals:
INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
048

Expected:
WORLD

Predicted:
GENERAL

Confidence:
LOW

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
CLAIM_UNCERTAIN, FORMAT_ANALYSIS, INTENT_UNDERSTAND_IMPACT

Semantic Suppressions:
None

Reason Codes:
DEFAULT_GENERAL_TOPIC

Supporting Signals:
INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
LOW_TOPIC_CONFIDENCE, TOPIC_SIGNAL_INSUFFICIENT

ID:
050

Expected:
CRIME

Predicted:
EDUCATION

Confidence:
HIGH

Semantic Primary Domains:
None

Semantic Secondary Domains:
None

Contextual Supports:
CLAIM_ATTRIBUTED

Semantic Suppressions:
None

Reason Codes:
TITLE_TOPIC_SIGNAL, BODY_TOPIC_SIGNAL

Supporting Signals:
TITLE_EDUCATION_SIGNAL, BODY_EDUCATION_SIGNAL

Warnings:
None

## Format Mismatches

ID:
044

Expected:
ANALYSIS

Predicted:
STANDARD_NEWS

Confidence:
LOW

Contextual Format Supports:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
DEFAULT_STANDARD_NEWS_FORMAT

Supporting Signals:
EXISTING_CONTENT_TYPE_FALLBACK

Warnings:
LOW_EDITORIAL_FORMAT_CONFIDENCE

ID:
045

Expected:
EXPLAINER

Predicted:
STANDARD_NEWS

Confidence:
LOW

Contextual Format Supports:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
DEFAULT_STANDARD_NEWS_FORMAT

Supporting Signals:
EXISTING_CONTENT_TYPE_FALLBACK

Warnings:
LOW_EDITORIAL_FORMAT_CONFIDENCE

ID:
046

Expected:
ANALYSIS

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Contextual Format Supports:
FORMAT_ANALYSIS

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
DEFAULT_STANDARD_NEWS_FORMAT

Supporting Signals:
EXISTING_CONTENT_TYPE_FALLBACK

Warnings:
None

ID:
047

Expected:
ANALYSIS

Predicted:
STANDARD_NEWS

Confidence:
MEDIUM

Contextual Format Supports:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Reason Codes:
DEFAULT_STANDARD_NEWS_FORMAT

Supporting Signals:
EXISTING_CONTENT_TYPE_FALLBACK

Warnings:
None

## Reader Intent Mismatches

ID:
044

Expected:
UNDERSTAND_IMPACT

Predicted:
GET_UPDATE

Confidence:
LOW

Reason Codes:
FORMAT_READER_INTENT_MAPPING, DEFAULT_GET_UPDATE

Supporting Signals:
FORMAT_STANDARD_NEWS, TOPIC_GENERAL

Warnings:
LOW_READER_INTENT_CONFIDENCE

ID:
045

Expected:
UNDERSTAND_EVENT

Predicted:
GET_UPDATE

Confidence:
LOW

Reason Codes:
FORMAT_READER_INTENT_MAPPING, DEFAULT_GET_UPDATE

Supporting Signals:
FORMAT_STANDARD_NEWS, TOPIC_GENERAL

Warnings:
LOW_READER_INTENT_CONFIDENCE

ID:
046

Expected:
UNDERSTAND_IMPACT

Predicted:
GET_UPDATE

Confidence:
HIGH

Reason Codes:
FORMAT_READER_INTENT_MAPPING, DEFAULT_GET_UPDATE

Supporting Signals:
FORMAT_STANDARD_NEWS, TOPIC_TECHNOLOGY

Warnings:
None

ID:
047

Expected:
UNDERSTAND_IMPACT

Predicted:
GET_UPDATE

Confidence:
HIGH

Reason Codes:
FORMAT_READER_INTENT_MAPPING, DEFAULT_GET_UPDATE

Supporting Signals:
FORMAT_STANDARD_NEWS, TOPIC_GENERAL

Warnings:
None
