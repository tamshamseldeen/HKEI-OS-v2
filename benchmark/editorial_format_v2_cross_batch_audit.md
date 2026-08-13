# Editorial Format V2 Cross-Batch Offline Shadow Audit

Assessment: MIXED

Readiness: REFINE_V2_FEATURE_EXTRACTION_ON_GENERIC_FIXTURES_ONLY

Cases: 60

V1 / V2 accuracy: 55.00000000000001 / 41.66666666666667

This is a historical shadow audit. It is not a new generalization claim and no
benchmark result was used to tune production logic.

| Batch | Cases | V1 | V2 | Delta |
|---|---:|---:|---:|---:|
| batch_01 | 0 | 0.0 | 0.0 | 0.0 |
| batch_02 | 10 | 90.0 | 60.0 | -30.0 |
| batch_03 | 10 | 100.0 | 30.0 | -70.0 |
| batch_05 | 10 | 50.0 | 60.0 | 10.0 |
| batch_06 | 10 | 40.0 | 40.0 | 0.0 |
| batch_07 | 10 | 40.0 | 20.0 | -20.0 |
| batch_08 | 10 | 10.0 | 40.0 | 30.0 |

Provider calls: 0. V1, Reader Intent, and Gate were not mutated.
