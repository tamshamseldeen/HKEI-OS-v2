# Limited Topic Authority Pilot Specification

## Status

**Specification status:** `READY_FOR_LIMITED_TOPIC_AUTHORITY_IMPLEMENTATION`

**Pilot boundary:** Topic authority only.

- `FORMAT_AUTHORITY_NOT_INCLUDED`
- `READER_INTENT_AUTHORITY_NOT_INCLUDED`
- `GATE_REFINEMENT_NOT_INCLUDED`

This document defines a controlled pilot. It does not enable production
authority, modify the Resolver or Gate, change provider runtime, or authorize a
provider call.

## Evidence and limitation

The Batch 09 preregistered Resolver holdout observed 60% deterministic Topic
accuracy and 80% resolved Topic accuracy. Two accepted Topic overrides were
correct, none regressed, candidate and fingerprint integrity were 100%, and all
five executed provider calls returned valid responses without retries.

That evidence supports testing existing authority safely. It does not establish
complete Topic coverage: Topic Gate recall was 50%. The pilot tests only this
proposition:

> When the existing Gate requests Topic adjudication and every existing trust
> contract accepts a validated adjudicated Topic, can the Resolver's final Topic
> safely become authoritative?

It does not test whether the Gate detects every wrong deterministic Topic.

## Runtime mode

The conceptual configuration is:

`resolver_authority_mode`

Allowed values are:

- `SHADOW`
- `LIMITED_TOPIC_AUTHORITY`

The default is always `SHADOW`. Missing, malformed, or unrecognized
configuration resolves to `SHADOW`. Enabling `LIMITED_TOPIC_AUTHORITY` must be
explicit and scoped to an approved consumer or traffic cohort. Configuration
must not be inferred from environment, provider success, or Resolver output.

## Authority eligibility contract

An adjudicated Topic becomes authoritative only when every condition is true:

1. `resolver_authority_mode = LIMITED_TOPIC_AUTHORITY`;
2. the existing Gate requested Topic adjudication;
3. provider execution succeeded within the existing timeout and retry policy;
4. the response validator accepted the response;
5. an adjudicated Topic exists;
6. it belongs to the original request-specific Topic candidate universe;
7. request and validated-response fingerprints match exactly;
8. Resolver Topic status is `ADJUDICATED_ACCEPTED`;
9. Resolver Topic source is `ADJUDICATION`;
10. Resolver Topic `review_required` is false;
11. `ambiguity_remaining` is false; and
12. provider Topic confidence is `MEDIUM` or `HIGH`.

No other condition or label source may grant Topic authority. Global enum
membership is insufficient; candidate membership remains request-specific.
Fingerprint mismatch always blocks authority without exception.

Provider confidence is secondary to structural trust. `HIGH` is not required,
because Batch 09 safety arose from the full validator/candidate/fingerprint
contract rather than confidence alone. `MEDIUM` and `HIGH` are eligible after
all structural conditions pass. `LOW` blocks authority in this first pilot and
increments `authority_blocked_by_policy`; the Resolver result remains available
for diagnostics.

## Deterministic preservation and failure handling

The existing deterministic Topic remains production-authoritative when:

- mode is `SHADOW`;
- Topic status is `DETERMINISTIC_ACCEPTED`, `FALLBACK_ACCEPTED`, `UNRESOLVED`,
  or `REVIEW_REQUIRED`;
- `review_required` is true;
- adjudication ambiguity remains;
- provider confidence is `LOW`; or
- any eligibility condition fails.

Fallback never represents AI authority. Timeout, rate limit, provider
unavailability, configuration error, authentication or permission error,
invalid or incomplete response, missing Topic, illegal candidate, and
fingerprint mismatch all preserve the deterministic production Topic.

The existing timeout triggers deterministic fallback; provider latency must not
silently block it. The pilot introduces no retries or fallback model and does
not convert the architecture into provider-call-every-article.

## Review-required and ambiguity policy

The first pilot chooses the conservative option: an adjudicated Topic with
`review_required = true` does not become authoritative. This includes every
accepted result with `ambiguity_remaining = true`. The deterministic Topic
remains authoritative, while resolved Topic, review state, and warnings remain
observable.

This separates diagnostic acceptance by the Resolver from production authority
eligibility. A later policy may be considered only after independent evidence;
the pilot must not relax this rule dynamically.

## Format and Reader Intent boundaries

Production Format continues its current behavior. Resolver Format output and
Format V2 remain observational and guarded. Neither V2 agreement nor a V2
selected label can grant production authority. Any Format mutation caused by
the pilot is an authority-contract violation and immediate stop condition.

Reader Intent remains the current deterministic value. It is not adjudicated or
recomputed from the authoritative Topic during the pilot. Any Reader Intent
authority change is an immediate stop condition.

## Gate boundary and selective calling

The current Gate is used unchanged. The pilot neither expands candidate scope
nor broadens adjudication triggers. Gate coverage and authority safety are
separate experiments. Topic adjudication requests and provider call rate must
be measured so the known recall limitation remains visible.

## Production-facing output contract

The pilot adds an additive, sanitized result alongside current outputs:

- `deterministic_topic`
- `resolved_topic`
- `authoritative_topic`
- `authority_source`
- `authority_applied`
- `resolution_status`
- `review_required`
- symbolic `warnings`
- `provider_used`

`authoritative_topic` equals `resolved_topic` only when the complete authority
eligibility contract passes. Otherwise it equals `deterministic_topic`.

A valid adjudication that agrees with the deterministic Topic does not
constitute an authoritative override. It is recorded as `NO_TOPIC_CHANGE`, is
not an error, fallback, provider failure, incorrect override, or authority
contract violation, and leaves the deterministic production value and source
authoritative.

Existing consumers continue receiving the current deterministic Topic unless
their path is explicitly enrolled in `LIMITED_TOPIC_AUTHORITY`. Format and
Reader Intent contracts do not change.

## Dual recording and provenance

Every pilot decision records both the original deterministic Topic and resolved
Topic, plus the value that became authoritative. Sanitized provenance includes:

- authority source and whether authority was applied;
- resolution status;
- Gate scope;
- provider used;
- response valid;
- candidate compliant;
- fingerprint valid;
- provider Topic confidence;
- ambiguity remaining;
- review required; and
- symbolic warnings.

No record may persist article body, raw prompt, raw provider response,
authorization header, secret, or chain-of-thought. The current Request Builder
disclosure scope remains unchanged: only its bounded title, lead, body excerpt,
and structured deterministic/semantic evidence are sent when the Gate requests
adjudication. The pilot adds no content or retrieval.

Operational failures that block authority consumption must be represented by
canonical sanitized warnings; raw exception strings must never enter authority
results or observations. `AUTHORITY_OBSERVATION_FAILED` means the canary could
not safely record its required authority observation. It is an operational,
provider-neutral condition and requires fail-closed consumption; it does not
change editorial resolution or grant Format or Reader Intent authority.

## Observability

The implementation must expose monotonic counters, partitionable by pilot
cohort and mode:

- `articles_processed`
- `topic_adjudication_requested`
- `provider_calls`
- `valid_adjudications`
- `resolver_adjudicated_accepted`
- `authoritative_topic_overrides`
- `deterministic_topic_preserved`
- `fallbacks`
- `review_required_decisions`
- `authority_blocked_by_policy`
- `provider_failures`
- `candidate_violations`
- `fingerprint_failures`
- `rollback_count`
- `authority_contract_violation_count`

Provider call rate and latency distributions must be observable. Counters must
not contain article text or unbounded identifiers.

Primary audited safety metrics are:

- `authoritative_override_count`
- `audited_correct_override_count`
- `audited_incorrect_override_count`
- `override_precision`
- `rollback_count`
- `provider_failure_count`
- `authority_contract_violation_count`

## Human audit and ground truth

The same provider output must never serve as ground truth. Every authoritative
override in the initial sample is reviewed by a qualified human editor who is
shown the source and the deterministic and authoritative Topics but not hidden
model reasoning. Review records the correct Topic and whether the override was
correct. Disagreements follow an independent editorial adjudication procedure.

After the minimum sample, ongoing pilot monitoring must audit every override or
a preregistered statistically valid sample whose selection cannot be influenced
by provider confidence or outcome. Unaudited decisions do not count toward
pilot-success precision.

## Preregistered thresholds

The initial regression budget is **zero**: no audited case with a correct
deterministic Topic may be replaced by an incorrect authoritative Topic.

Pilot success requires all of the following:

- at least **30 authoritative Topic overrides** independently audited;
- Topic override precision at least 90%;
- audited incorrect overrides within the regression budget of zero;
- authority-contract violations equal zero;
- candidate or fingerprint violations accepted equal zero;
- fallback mutation equal zero;
- Format authority violations equal zero;
- Reader Intent authority violations equal zero; and
- no unresolved immediate stop condition.

Thirty overrides are large enough to avoid extrapolating from the two Batch 09
changes while remaining practical for a limited internal pilot. Passing the
threshold does not authorize full rollout.

## Stop conditions

Immediately set the kill switch to `SHADOW` upon any of:

- any authority-contract violation;
- acceptance of an illegal candidate or fingerprint mismatch;
- accidental Format or Reader Intent authority;
- mutation outside Topic;
- any audited incorrect override, because the regression budget is zero;
- three consecutive provider validation failures; or
- provider validation failures exceeding 5% after at least 20 provider calls.

After at least 30 audited overrides, also stop if measured Topic override
precision is below 90%. Before that minimum, precision is reported but cannot
declare success; an incorrect override still triggers the zero-budget stop.

Operational provider failures that correctly preserve deterministic Topic are
not authority-contract violations, but their rate is monitored and the repeated
failure thresholds above protect reliability.

## Kill switch and rollback

The kill switch is the centrally controlled `resolver_authority_mode`. Setting
it to `SHADOW` must affect newly evaluated requests immediately through the
existing dynamic configuration mechanism when available; implementation must
not cache authority mode in request-global mutable state. If the deployment
environment cannot refresh configuration safely without restart, implementation
must stop for architecture review rather than weaken the kill-switch contract.

Rollback consists only of setting the mode to `SHADOW`. No code rollback, data
migration, or deletion of historical diagnostics is required. Previously
recorded deterministic/resolved/authoritative provenance remains available for
audit. `rollback_count` increments once per authority-to-shadow transition.

## Determinism and concurrency

Given the same immutable deterministic outputs, Gate scope, validated response,
Resolver output, candidate universe, fingerprint, confidence, ambiguity, review
state, and authority mode, the authority decision must be identical.

The decision is request-local. Candidate sets, fingerprints, authority mode
snapshot, and intermediate decisions must not be held in shared mutable state.
Concurrent requests cannot observe or overwrite one another's trust data.

## Rollout stages

1. **Stage 0 — SHADOW only:** record eligibility and counterfactual authority;
   verify metrics and kill-switch operation.
2. **Stage 1 — internal limited Topic authority:** explicitly enrolled internal
   consumers; audit every authoritative override.
3. **Stage 2 — small percentage/canary:** preregister cohort and exposure;
   maintain zero regression budget and immediate rollback.
4. **Stage 3 — expanded pilot:** proceed only after independent safety review
   confirms thresholds and operational reliability.

This specification authorizes no full rollout.

## Operational canary wiring

The operational authority source is `resolver_authority_mode`, parsed strictly as
`SHADOW` or `LIMITED_TOPIC_AUTHORITY`; a missing value is `SHADOW`. It is resolved
for each request, and an explicit stop recommendation updates that same source to
`SHADOW`, so no cached LIMITED decision can survive the kill switch.

Authority consumption is restricted to the explicitly selected
`INTERNAL_TOPIC_AUTHORITY_CANARY_PATH`. The normal production route and every
SHADOW execution consume the deterministic Topic. An authority decision may be
eligible and applied in the canary computation without being consumed downstream.

A sanitized observation is recorded before authority consumption. Observation
failure adds `AUTHORITY_OBSERVATION_FAILED` and fails closed to the deterministic
Topic. Observation identities use the decision fingerprint for idempotent duplicate
handling. The public canary result preserves deterministic, resolved, authoritative,
and consumer Topic provenance, but excludes article content, source/request/prompt
objects, provider payloads or exceptions, credentials, and reasoning text.

## Backward compatibility

Authority output is additive. Existing consumers remain on current Topic by
default. Enrollment is explicit per path or cohort, and disabling enrollment
restores current behavior without schema or data migration. Historical Resolver
diagnostics remain non-authoritative and queryable.

## Benchmark and future-evidence boundary

Batch 09 is evaluated and frozen. Its evidence supports eligibility for this
pilot specification only. No implementation may encode cases 081–090 or tune
the Gate, Resolver, classifier, candidate universe, or confidence policy against
their outcomes.

Before broad production rollout, require at least one additional untouched,
preregistered Resolver evaluation or an equivalent independent pilot audit that
was not used to define or tune the authority policy.

## Implementation phases

1. **Pilot configuration and models:** define the authority mode, additive
   output, immutable decision inputs, and sanitized counters.
2. **Authority applicator:** implement the pure eligibility predicate and
   deterministic-preservation path without provider orchestration.
3. **Shadow/authority parity tests:** prove shadow eligibility and enabled
   authority use identical inputs and differ only in authority application.
4. **Failure and rollback tests:** cover every provider/trust failure, kill
   switch, zero mutation, concurrency isolation, and mode refresh.
5. **Offline canary simulation:** exercise dual recording, metrics, human-audit
   sampling, and all stop conditions without external authority.
6. **Controlled pilot enablement:** begin Stage 1 only after explicit operational
   approval and verified monitoring/rollback readiness.

The accepted architecture decision is
`READY_FOR_LIMITED_TOPIC_AUTHORITY_IMPLEMENTATION` under the conservative
policies and preregistered thresholds above.
