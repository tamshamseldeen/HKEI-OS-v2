# Limited Topic Authority final pre-canary audit

- Final safety classification: `PRE_CANARY_BLOCKED`
- Final readiness decision: `FIX_ONE_OPERATIONAL_BLOCKER_FIRST`
- Default mode: `SHADOW`
- First real canary scope: `INTERNAL_SINGLE_PATH`
- Real provider calls: `0`

## Exact blocker

ControlledTopicAuthorityCanaryWorkflow.analyze_operational consumes the explicit stop signal through runtime_config, then calls OperationalTopicAuthorityCanary.execute with stop_signal=None; the safe result therefore reports stop_recommended=false even when the supplied stop decision requested SHADOW.

## Checks

- `default_off`: `PASS`
- `explicit_enablement`: `PASS`
- `internal_route_isolation`: `PASS`
- `authority_eligibility`: `PASS`
- `observation_before_consumption`: `PASS`
- `sanitized_boundary`: `PASS`
- `kill_switch`: `PASS`
- `stop_signal_consumption`: `PASS`
- `stop_observability`: `FAIL`
- `regression_budget`: `PASS`
- `precision_threshold`: `PASS`
- `human_audit_independence`: `PASS`
- `duplicate_audit_safety`: `PASS`
- `provider_failure_safety`: `PASS`
- `invalid_response_safety`: `PASS`
- `candidate_safety`: `PASS`
- `fingerprint_safety`: `PASS`
- `review_required_safety`: `PASS`
- `ambiguity_safety`: `PASS`
- `low_confidence_safety`: `PASS`
- `no_topic_change_safety`: `PASS`
- `format_isolation`: `PASS`
- `reader_intent_isolation`: `PASS`
- `gate_independence`: `PASS`
- `resolver_independence`: `PASS`
- `provider_independence`: `PASS`
- `observation_sink_failure_safety`: `PASS`
- `consumer_failure_safety`: `PASS`
- `config_failure_safety`: `PASS`
- `request_locality`: `PASS`
- `concurrency_proxy`: `PASS`
- `dual_provenance`: `PASS`
- `existing_consumer_safety`: `PASS`
- `operational_metrics_readiness`: `PASS`

The stop recommendation is consumed safely and changes effective mode to SHADOW, but its
presence is lost at the sanitized result boundary. No real canary should run until that
single observability blocker is corrected and re-audited.
