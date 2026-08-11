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

Topic Accuracy: 60.00%

Format Accuracy: 0.00%

Fully Correct Cases: 2/5

Topic Improvements: 3

Topic Regressions: 0

Format Improvements: 0

Format Regressions: 0

## Ambiguity

Ambiguity True: 3

Ambiguity Rate: 60.00%

## Efficiency

Average Input Tokens: 955.4

Average Output Tokens: 505.6

Average Reasoning Tokens: 153.6

Average Non-Reasoning Output Tokens: 352

Average Reasoning Share: 30.11%

Average Latency: 6963.4 ms

Median Latency: 6745 ms

Maximum Latency: 8429 ms

## Shadow Safety

Topic Mutations: 0

Format Mutations: 0

Intent Mutations: 0

## Case Table

| ID | Scope | Valid | Det Topic | Adj Topic | Expected Topic | Topic Correct | Det Format | Adj Format | Expected Format | Format Correct | Ambiguity | Reasoning Tokens | Output Tokens | Latency |
|---|---|---:|---|---|---|---:|---|---|---|---:|---:|---:|---:|---:|
| 044 | TOPIC_AND_FORMAT_REQUIRED | True | GENERAL | GENERAL | WORLD | False | STANDARD_NEWS | STANDARD_NEWS | ANALYSIS | False | True | 64 | 532 | 8429 |
| 045 | TOPIC_AND_FORMAT_REQUIRED | True | GENERAL | WORLD | WORLD | True | STANDARD_NEWS | STANDARD_NEWS | EXPLAINER | False | True | 192 | 487 | 6300 |
| 046 | TOPIC_AND_FORMAT_REQUIRED | True | TECHNOLOGY | TECHNOLOGY | SCIENCE | False | STANDARD_NEWS | STANDARD_NEWS | ANALYSIS | False | False | 128 | 465 | 6745 |
| 048 | TOPIC_REQUIRED | True | GENERAL | WORLD | WORLD | True | STANDARD_NEWS | STANDARD_NEWS | STANDARD_NEWS | None | True | 128 | 451 | 5632 |
| 050 | TOPIC_REQUIRED | True | EDUCATION | CRIME | CRIME | True | STANDARD_NEWS | STANDARD_NEWS | STANDARD_NEWS | None | False | 256 | 593 | 7711 |
