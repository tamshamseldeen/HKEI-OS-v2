# Batch 06 Blind Generalization Validation

## Holdout Integrity

Cases: 10

IDs: 051–060

Provider Calls: 0

## Pre-Gate Editorial Performance

Topic Accuracy: 40.00%

Format Accuracy: 40.00%

Reader Intent Accuracy: 40.00%

Full Case Accuracy: 0.00%

## Topic Mismatches

- 051: GENERAL → ECONOMY
- 053: BUSINESS → ECONOMY
- 054: BUSINESS → ECONOMY
- 055: WORLD → BUSINESS
- 056: EDUCATION → GOVERNMENT
- 060: BUSINESS → GOVERNMENT

## Format Mismatches

- 052: ANALYSIS → STANDARD_NEWS
- 054: RESULT_REPORT → STANDARD_NEWS
- 056: FACT_CHECK → GUIDE
- 057: STANDARD_NEWS → RESULT_REPORT
- 058: TREND_UPDATE → STANDARD_NEWS
- 059: TREND_UPDATE → STANDARD_NEWS

## Reader Intent Mismatches

- 052: UNDERSTAND_IMPACT → GET_UPDATE
- 054: FIND_RESULT → GET_UPDATE
- 056: CHECK_CLAIM → VERIFY_REQUIREMENTS
- 057: GET_UPDATE → FIND_RESULT
- 058: FOLLOW_DEVELOPMENT → GET_UPDATE
- 059: FOLLOW_DEVELOPMENT → GET_UPDATE

## Contextual / Semantic Evidence

Contextual Evidence Cases: 9

Semantic Relationship Cases: 3

Primary Semantic Domain Cases: 1

Semantic Format Support Cases: 0

## Gate Coverage

Topic Gate Precision: 85.71%

Topic Gate Recall: 100.00%

Format Gate Precision: 100.00%

Format Gate Recall: 50.00%

Projected Provider Calls: 9/10

## Generalization Assessment

WEAK

## Gate Assessment

WEAK

## Scientific Conclusion

Batch 06 records observed generalization and gate coverage without tuning. Correct dimensions generalized as reported above; mismatches and missed or unnecessary gate decisions remain raw holdout findings for later analysis.
