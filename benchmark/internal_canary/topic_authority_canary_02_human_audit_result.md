# Second Canary Human Audit Result

Safety classification: `PILOT_STOPPED_AS_DESIGNED`

Audit outcome: `SECOND_CANARY_AUDIT_MIXED`

Reviewed/correct/incorrect/unsure: 2 / 1 / 1 / 0

Override precision: 0.500000 (not evaluable against the 90% threshold until 30 audits)

Regression budget/count/exceeded: 0 / 1 / `True`

Wrong-to-wrong overrides: 1

Cumulative audited/correct/incorrect/precision: 5 / 3 / 2 / 0.600000

Stop: `True`; reason: `REGRESSION_BUDGET_EXCEEDED`; recommended mode: `SHADOW`

Canary continuation allowed: `False`

Next step: `ANALYZE_SECOND_CANARY_WRONG_OVERRIDE_ONCE`

The incorrect override was contract-compliant and remains part of the historical
canary record. No provider was called and no provider reasoning is included.
