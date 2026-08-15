# Second Canary Human Audit Result

Safety classification: `PILOT_STOPPED_AS_DESIGNED`

Audit outcome: `SECOND_CANARY_AUDIT_MIXED`

Reviewed/correct/incorrect/unsure: 2 / 1 / 0 / 1

Override precision: 1.000000 (not evaluable against the 90% threshold until 30 audits)

Regression budget/count/exceeded: 0 / 0 / `False`

Wrong-to-wrong overrides: 0

Cumulative audited/correct/incorrect/precision: 4 / 3 / 1 / 0.750000

Stop: `True`; reason: `REGRESSION_BUDGET_EXCEEDED`; recommended mode: `SHADOW`

Canary continuation allowed: `False`

Next step: `ANALYZE_WORLD_BUSINESS_ONTOLOGY_BOUNDARY`

The incorrect override was contract-compliant and remains part of the historical
canary record. No provider was called and no provider reasoning is included.
