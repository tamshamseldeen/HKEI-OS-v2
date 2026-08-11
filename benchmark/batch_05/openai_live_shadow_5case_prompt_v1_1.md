# OpenAI Limited Live Shadow Evaluation — 5 Cases

## Scope

Cases: 044, 045, 046, 048, 050

Provider: OpenAI

Configured Model: gpt-5-mini

Reasoning Effort: LOW

Maximum Calls: 5

## Reliability

Provider Calls: 5

Valid Responses: 5

Failed Responses: 0

Candidate Compliance: 100.00%

Fingerprint Integrity: 100.00%

## Editorial Accuracy

Topic Accuracy: 80.00%

Format Accuracy: 33.33%

Fully Correct Cases: 2/5

Topic Improvements: 4

Topic Regressions: 0

Format Improvements: 1

Format Regressions: 0

## Ambiguity

Ambiguity True: 0

Ambiguity Rate: 0.00%

## Efficiency

Average Input Tokens: 1825.2

Average Output Tokens: 550

Average Reasoning Tokens: 179.2

Average Non-Reasoning Output Tokens: 370.8

Average Reasoning Share: 31.70%

Average Latency: 9711.8 ms

Median Latency: 9939 ms

Maximum Latency: 15065 ms

## Shadow Safety

Topic Mutations: 0

Format Mutations: 0

Intent Mutations: 0

## Case Table

| ID | Scope | Valid | Det Topic | Adj Topic | Expected Topic | Topic Correct | Det Format | Adj Format | Expected Format | Format Correct | Ambiguity | Reasoning Tokens | Output Tokens | Latency |
|---|---|---:|---|---|---|---:|---|---|---|---:|---:|---:|---:|---:|
| 044 | TOPIC_AND_FORMAT_REQUIRED | True | GENERAL | WORLD | WORLD | True | STANDARD_NEWS | STANDARD_NEWS | ANALYSIS | False | False | 128 | 440 | 7218 |
| 045 | TOPIC_AND_FORMAT_REQUIRED | True | GENERAL | GOVERNMENT | WORLD | False | STANDARD_NEWS | EXPLAINER | EXPLAINER | True | False | 256 | 719 | 9939 |
| 046 | TOPIC_AND_FORMAT_REQUIRED | True | TECHNOLOGY | SCIENCE | SCIENCE | True | STANDARD_NEWS | STANDARD_NEWS | ANALYSIS | False | False | 256 | 676 | 15065 |
| 048 | TOPIC_REQUIRED | True | GENERAL | WORLD | WORLD | True | STANDARD_NEWS | STANDARD_NEWS | STANDARD_NEWS | None | False | 128 | 458 | 10421 |
| 050 | TOPIC_REQUIRED | True | EDUCATION | CRIME | CRIME | True | STANDARD_NEWS | STANDARD_NEWS | STANDARD_NEWS | None | False | 128 | 457 | 5916 |
