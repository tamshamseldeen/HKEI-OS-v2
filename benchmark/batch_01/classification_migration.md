# Batch 01 Classification Migration

| ID | Category | Legacy Content Type | Topic | Editorial Format | Reader Intent | Risk | Topic Conflict | Format Conflict | Risk Mixing | Intent Suspect | Strategy Suspect |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | economy | LEGAL_FINANCIAL_HIGH_RISK_CONTENT | ECONOMY | STANDARD_NEWS | FOLLOW_DEVELOPMENT | HIGH | NO | NO | YES | NO | NO |
| 002 | economy | SPORTS_NEWS | ECONOMY | STANDARD_NEWS | FIND_RESULT | LOW | YES | NO | NO | YES | YES |
| 003 | technology | LEGAL_FINANCIAL_HIGH_RISK_CONTENT | TECHNOLOGY | STANDARD_NEWS | UNDERSTAND_IMPACT | HIGH | NO | NO | YES | YES | NO |
| 004 | weather | BREAKING_NEWS | WEATHER | BREAKING | GET_UPDATE | LOW | NO | NO | NO | NO | NO |
| 005 | government | SPORTS_NEWS | GOVERNMENT | STANDARD_NEWS | FIND_RESULT | LOW | YES | NO | NO | YES | YES |
| 006 | economy | SPORTS_NEWS | ECONOMY | STANDARD_NEWS | FIND_RESULT | LOW | YES | NO | NO | YES | YES |
| 007 | economy | ECONOMY_NEWS | ECONOMY | GUIDE | UNDERSTAND_IMPACT | LOW | NO | NO | NO | NO | NO |
| 008 | culture | STANDARD_NEWS | CULTURE | STANDARD_NEWS | GET_UPDATE | LOW | NO | NO | NO | NO | NO |
| 009 | sports | SPORTS_NEWS | SPORTS | RESULT_REPORT | FIND_RESULT | LOW | NO | NO | NO | NO | NO |
| 010 | economy | LEGAL_FINANCIAL_HIGH_RISK_CONTENT | ECONOMY | STANDARD_NEWS | UNDERSTAND_IMPACT | HIGH | NO | NO | YES | YES | NO |

## Summary

Legacy Topic Conflicts:
3

Legacy Format Conflicts:
0

Legacy Risk Mixing Cases:
3

Reader Intent Suspect Cases:
5

Strategy Suspect Cases:
3

## Migration Candidates

### Remove legacy topic dependency

- 002
- 005
- 006

### Remove legacy risk dependency

- 001
- 003
- 010

### Review reader intent dependency

- 002
- 003
- 005
- 006
- 010

### Review strategy dependency

- 002
- 005
- 006
