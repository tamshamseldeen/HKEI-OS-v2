# Limited Editorial Resolver Specification

## Status

**Specification status:** `READY_FOR_LIMITED_RESOLVER_IMPLEMENTATION`

**Topic status:** `TOPIC_RESOLUTION_READY_FOR_IMPLEMENTATION`

**Format status:** `FORMAT_FULL_AUTHORITY_DEFERRED`

This document specifies a limited, provider-neutral authority layer. It does
not implement that layer, change any classifier, or make any provider call.

## Purpose and boundary

The Resolver is not another classifier. It deterministically chooses which
already-produced, legal result becomes authoritative for each editorial
dimension. The dimensions are resolved independently; there is no global mode
that makes all deterministic or all adjudicated outputs authoritative.

The Resolver consumes structured outputs from earlier stages and produces
labels, statuses, and provenance. It:

- never invents or coerces a label;
- never calls a provider or decides whether a provider should be called;
- never consumes a raw provider response;
- never generates article text or an `ArticlePlan`;
- performs no random, time-dependent, or network operation; and
- returns identical output for identical inputs.

The existing shadow workflows remain non-mutating. A future Resolver is a new,
explicit production-authority layer and does not retroactively change shadow
semantics.

## Authority model

Authority is asymmetric and per dimension:

| Dimension | MVP authority | Constraint |
|---|---|---|
| Topic | Deterministic Topic or validated adjudicated Topic | Adjudication must satisfy every trust boundary |
| Format | Validated adjudicated Format, else compatible V1 fallback | V2 is a trust signal, not a production label source |
| Reader Intent | Current deterministic Reader Intent | No independent adjudication or recomputation in MVP |

Provider confidence is advisory. It may affect warnings, review status, and
future policy, but it cannot make an illegal, invalid, or mismatched response
acceptable. A valid legal selection need not be `HIGH` confidence.

## Conceptual types

### Resolution status

Each dimension uses a provider-neutral status:

- `DETERMINISTIC_ACCEPTED`: an eligible deterministic result is authoritative.
- `ADJUDICATED_ACCEPTED`: a validated adjudicated result is authoritative.
- `FALLBACK_ACCEPTED`: a compatibility result is retained after the preferred
  authority path was unavailable or invalid.
- `UNRESOLVED`: no legal label can safely be returned.
- `REVIEW_REQUIRED`: reserved for interfaces that model review as the primary
  state. In the preferred model, the selected status remains one of the first
  four and `review_required` is an independent Boolean.

Keeping review orthogonal prevents a valid label with residual ambiguity from
being represented as a failure.

### Resolution source

- `DETERMINISTIC_V1`
- `FORMAT_V2_SHADOW`
- `ADJUDICATION`
- `FALLBACK`
- `NONE`

Topic must never use `FORMAT_V2_SHADOW`. In the MVP, Format V2 may contribute
trust and warning metadata, but the final Format source must not be
`FORMAT_V2_SHADOW`.

### EditorialResolutionResult

A future immutable conceptual model should contain:

- `final_topic`
- `topic_resolution_status`
- `topic_source`
- `final_format`
- `format_resolution_status`
- `format_source`
- `final_reader_intent`
- `reader_intent_resolution_status`
- `reader_intent_source`
- separately provenance-bearing deterministic and provider Topic confidences
- separately provenance-bearing deterministic and provider Format confidences
- `topic_ambiguity`
- `format_ambiguity`
- `review_required`
- symbolic `warnings`
- `provider_used`
- `input_fingerprint`

The model must not contain article text, raw prompts, raw responses, raw SDK
exceptions, or reasoning text. Confidence values must retain their provenance;
the Resolver must not synthesize a blended confidence without a separate,
documented policy.

## Hard trust boundaries

### Validator boundary

The Resolver accepts only the domain-level response produced by the response
validator. Raw OpenAI or other provider responses are outside its input
contract. A configuration, authentication, permission, rate-limit, timeout,
incomplete-response, or invalid-response outcome is provider failure metadata,
not an adjudication result.

### Candidate membership

An adjudicated Topic or Format is eligible only when it is a member of the
corresponding legal candidate universe supplied in the adjudication request.
No post-hoc enum coercion, nearest-label mapping, or candidate expansion is
permitted.

### Fingerprint integrity

Where the current request/response contract carries an input fingerprint, the
validated response fingerprint must exactly match the request fingerprint. A
missing fingerprint when one is required, or any mismatch, makes adjudication
ineligible. The deterministic baseline remains available and the symbolic
warning `FINGERPRINT_MISMATCH` is emitted.

## Topic resolution contract

The final Topic comes from exactly one of two sources: the deterministic Topic
or the validated adjudicated Topic.

Adjudicated Topic overrides deterministic Topic only if all conditions hold:

1. the Gate requested Topic adjudication;
2. the provider call succeeded;
3. the response validator accepted the response;
4. an adjudicated Topic is present;
5. the Topic belongs to the request's legal Topic candidate set;
6. fingerprint integrity passes where supported; and
7. the response has no structural-invalid state.

When all conditions hold, the result is `ADJUDICATED_ACCEPTED` from
`ADJUDICATION`. Provider Topic confidence is preserved separately. If
`ambiguity_remaining` is true, the legal Topic may still be accepted, but
`topic_ambiguity` remains true, `review_required` is true, and
`ADJUDICATION_AMBIGUITY_REMAINS` is emitted.

If Topic adjudication was not requested, deterministic Topic is
`DETERMINISTIC_ACCEPTED` from `DETERMINISTIC_V1`. If adjudication was requested
but failed any condition above, deterministic Topic is preserved with
`FALLBACK_ACCEPTED` from `FALLBACK`, plus the applicable warning and review
state. If no legal deterministic Topic exists, Topic is `UNRESOLVED` from
`NONE`.

Confidence alone never repairs a failed safeguard and never changes candidate
legality.

## Guarded Format resolution contract

Format does not receive unconditional deterministic authority. Inputs may
include V1, the V2 shadow assessment, and validated adjudication, but the MVP
has only two label-authority paths:

1. validated adjudicated Format when the Gate requested Format adjudication
   and every validator, candidate, and fingerprint safeguard passes; or
2. deterministic V1 as a compatibility fallback with explicit trust and review
   metadata.

When adjudication is valid, Format is `ADJUDICATED_ACCEPTED` from
`ADJUDICATION`. Residual ambiguity remains visible and requires review.

When no Format adjudication was requested, a future policy may recognize the
conceptual state `FORMAT_DETERMINISTICALLY_TRUSTED`. Candidate evidence for that
state may include V2 profile `COMPLETE`, ambiguity `CLEAR`, confidence `HIGH`,
no material competition or contradiction, and useful V1/V2 agreement. This
specification deliberately sets no numeric threshold and does not authorize V2
as the final source. Until a later phase validates that policy on a new
untouched holdout, V1 is retained for compatibility.

When Format adjudication is required but unavailable or invalid, the explicit
MVP fallback is option C: preserve Format V1 while marking it `LOW_TRUST` through
status and warnings. The result is `FALLBACK_ACCEPTED` from `FALLBACK`, with
`review_required = true` and `FORMAT_FALLBACK_USED`. This is compatible with
interfaces that require a Format label, does not fabricate confidence, and
does not claim semantic certainty. If V1 itself is absent or illegal, Format is
`UNRESOLVED` from `NONE` and requires review.

V1 is therefore a `LEGACY_BASELINE`, not a statement of certainty. V2 is a
`TRUST_SIGNAL`, not an MVP production label source. V1/V2 disagreement emits
`FORMAT_V1_V2_DISAGREEMENT` and normally requires review even when another
legal source supplies the final label.

## Reader Intent policy

The MVP preserves the current deterministic Reader Intent. It is
`DETERMINISTIC_ACCEPTED` from `DETERMINISTIC_V1`; the Resolver neither
adjudicates it nor recomputes it from a newly resolved Topic or Format. This
avoids silently redesigning a downstream contract. Recalculation from resolved
dimensions requires a future dedicated phase and its own tests.

## Review-required contract

`review_required` means human review is advisable; it does not mean the whole
resolution failed. It is true when any dimension has a material trust concern,
including:

- accepted adjudication with ambiguity remaining;
- Format fallback after provider failure or invalid response;
- V1/V2 Format disagreement;
- unresolved candidate competition or contradiction;
- incomplete Format structure;
- a provider configuration, authentication, permission, rate-limit, timeout,
  unavailable, incomplete-response, or invalid-response outcome;
- fingerprint mismatch;
- illegal adjudicated candidate; or
- any `UNRESOLVED` dimension.

It is false only when every authoritative selection follows its eligible path
without a condition requiring review.

Symbolic warnings include:

- `ADJUDICATION_AMBIGUITY_REMAINS`
- `FORMAT_FALLBACK_USED`
- `FORMAT_V1_V2_DISAGREEMENT`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_CONFIGURATION_ERROR`
- `PROVIDER_AUTHENTICATION_ERROR`
- `PROVIDER_PERMISSION_ERROR`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_TIMEOUT`
- `INCOMPLETE_ADJUDICATION_RESPONSE`
- `INVALID_ADJUDICATION_RESPONSE`
- `FINGERPRINT_MISMATCH`
- `ILLEGAL_ADJUDICATED_CANDIDATE`
- `FORMAT_STRUCTURE_INCOMPLETE`

Warnings carry no source text or provider payload.

## Gate and Resolver responsibilities

The Gate owns **should adjudication be requested?** It determines scope before
provider orchestration. The Resolver must not reopen, broaden, or second-guess
that decision.

Provider orchestration owns executing the permitted request and producing a
validated domain response or sanitized failure state.

The Resolver owns **which eligible result becomes authoritative?** It consumes
the Gate decision and completed orchestration result but performs no provider
call itself.

## Failure-mode decision table

| Scenario | Topic behavior | Format behavior | Review / warnings |
|---|---|---|---|
| 1. No Gate request | Accept deterministic Topic | Preserve compatible V1; V2 remains trust metadata | Review only for independent Format conflict/incompleteness |
| 2. Valid Topic-only adjudication | Accept legal adjudicated Topic | Preserve compatible V1 | Preserve adjudication ambiguity; note Format trust concerns |
| 3. Valid Format-only adjudication | Preserve deterministic Topic | Accept legal adjudicated Format | Preserve adjudication ambiguity if present |
| 4. Valid Topic+Format adjudication | Accept each legal adjudicated dimension independently | Accept legal adjudicated Format | One dimension may fall back while the other succeeds |
| 5. Provider timeout | Preserve deterministic Topic | Preserve V1 as low-trust fallback | `PROVIDER_TIMEOUT`, Format review required |
| 6. Provider rate limit | Preserve deterministic Topic | Preserve V1 as low-trust fallback | `PROVIDER_RATE_LIMITED`, Format review required |
| 7. Invalid response | Preserve deterministic Topic | Preserve V1 as low-trust fallback | `INVALID_ADJUDICATION_RESPONSE`, review required |
| 8. Incomplete response | Preserve deterministic Topic | Preserve V1 as low-trust fallback | `INCOMPLETE_ADJUDICATION_RESPONSE`, review required |
| 9. Illegal candidate | Reject only the affected adjudicated dimension | Preserve V1 if Format affected | `ILLEGAL_ADJUDICATED_CANDIDATE`, review required |
| 10. Fingerprint mismatch | Reject adjudicated dimensions | Preserve V1 as low-trust fallback | `FINGERPRINT_MISMATCH`, review required |
| 11. Ambiguity remaining | Accept a legal validated Topic/Format | Accept legal adjudicated Format | Preserve ambiguity; `ADJUDICATION_AMBIGUITY_REMAINS` |
| 12. V1/V2 disagreement | Topic unaffected | Do not make V2 authoritative; prefer valid adjudication or preserve V1 | `FORMAT_V1_V2_DISAGREEMENT`, review required |
| 13. Provider unavailable and Format unresolved | Preserve deterministic Topic | Preserve legal V1 as low-trust fallback; otherwise `UNRESOLVED` | `PROVIDER_UNAVAILABLE`, `FORMAT_FALLBACK_USED` when applicable |

Configuration, authentication, and permission errors follow the same fail-safe
selection behavior as timeout and rate limit, with their own symbolic warning.
No provider failure silently erases a deterministic baseline.

## Limited Resolver MVP

The MVP is deliberately narrow:

- **Topic:** deterministic Topic is authoritative unless a Gate-requested,
  successful, validated, legal, fingerprint-matching adjudicated Topic replaces
  it.
- **Format:** a Gate-requested, validated, legal, fingerprint-matching
  adjudicated Format is authoritative; otherwise preserve V1 for compatibility
  and explicitly expose fallback trust/review status. V2 never directly
  overrides the production Format.
- **Reader Intent:** preserve the current deterministic value.
- **Safety:** preserve confidence and ambiguity provenance, emit symbolic
  warnings, never call a provider, and never consume raw provider output.

## Generator and ArticlePlan boundaries

The Resolver produces editorial labels, authority status, trust metadata, and
provenance only. It does not write or rewrite article text.

A future generation layer should consume `EditorialResolutionResult`, not raw
classifier/adjudicator disagreement. A future `ArticlePlan` should be derived
from resolved Topic, resolved Format, resolved Reader Intent, and explicit
review/trust metadata. Planning policy must decide how to handle
`review_required` or `UNRESOLVED`; the Resolver must not hide those states.

## Auditability

Without exposing chain-of-thought, the result must answer:

- which Topic and Format were chosen;
- which source supplied each choice;
- which resolution rule was applied;
- whether a provider result was eligible and used;
- whether fallback was used;
- whether ambiguity remains; and
- which symbolic conditions make human review advisable.

Structured statuses, sources, confidence provenance, ambiguity flags,
fingerprint, and warnings are sufficient. Free-form reasoning is neither
required nor permitted.

## Backward-compatible migration

1. Add resolver enums and result models alongside existing outputs.
2. Add a pure Resolver without replacing current classifier contracts.
3. Expose resolver results in a new shadow workflow while current outputs remain
   unchanged.
4. Evaluate Topic authority separately.
5. Introduce limited Topic authority behind a controlled integration boundary.
6. Retain compatible V1 Format output while consumers adopt explicit trust and
   review metadata.
7. Consider later Format authority only after new untouched validation.

No existing contract is replaced abruptly.

## Future Format V2 integration

- **Phase A — trust signal only:** V2 completeness, ambiguity, confidence, and
  competition inform review metadata but never supply the final Format.
- **Phase B — shadow resolver recommendation:** calculate and audit what V2
  would recommend without mutating production outputs.
- **Phase C — bounded deterministic authority:** after new untouched evidence,
  allow V2 authority only for a defined safe policy such as
  `CLEAR`/`COMPLETE`/`HIGH`, with no competition or contradiction.
- **Phase D — full Format resolver authority:** consider broader authority only
  after untouched validation demonstrates safety across Format families.

HKEI-193 does not establish Phase C or D readiness.

## Resolver implementation phases

1. **Enums and models:** immutable provider-neutral statuses, sources, warnings,
   inputs, and `EditorialResolutionResult`.
2. **Pure Resolver:** deterministic per-dimension policy with no I/O or network.
3. **Fake-provider integration tests:** exercise validated success and sanitized
   failure inputs without external calls.
4. **Shadow full-stack workflow:** add non-mutating resolver output alongside
   current results.
5. **Topic authority evaluation:** evaluate legal changes, preservation, review
   behavior, and provenance.
6. **Limited production Topic integration:** introduce Topic authority through a
   controlled, observable compatibility path.
7. **Future Format V2 trust integration:** proceed through Format phases only
   when new untouched evidence supports them.

## Future test strategy

Implementation tests must cover pure deterministic resolution, valid provider
success per Gate scope, every sanitized provider failure, invalid and incomplete
responses, illegal candidates, fingerprint mismatch, ambiguity preservation,
V1 Format fallback, missing fallback, V1/V2 disagreement, idempotence, no
network, and rejection of raw provider input. Tests must also prove independent
per-dimension resolution and non-mutation of existing shadow results.

## Benchmark and readiness policy

Batch 07 and Batch 08 may be referenced only as historical diagnostics. The
Resolver must not be tuned against them. Any production-readiness claim,
particularly Format V2 Phase C or D authority, requires a new untouched,
preregistered holdout evaluated after the policy is frozen.

The accepted architecture decision is therefore
`READY_FOR_LIMITED_RESOLVER_IMPLEMENTATION`: Topic authority may proceed to
models and pure tests, while full Format authority remains deferred and Reader
Intent remains unchanged.
