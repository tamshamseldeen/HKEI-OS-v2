# Semantic Evidence Directionality and Sufficiency Specification

Status: **SPECIFIED — NOT IMPLEMENTED**

This document defines a deterministic, provider-neutral contract for semantic evidence directionality and sufficiency. It separates evidence presence, direction, strength, sufficiency, classifier confidence, candidate competition, and Gate resolution state.

## Core Principle

The architecture must distinguish these propositions explicitly:

1. `EVIDENCE_PRESENT`: a relevant signal or relationship was detected.
2. `EVIDENCE_DIRECTIONALLY_RELEVANT`: that evidence changes the plausibility of a particular candidate.
3. `EVIDENCE_STRONG`: the evidence has high deterministic quality or weight.
4. `EVIDENCE_SUFFICIENT`: the complete evidence set coherently resolves the candidate decision.

Presence alone never implies directional relevance, strength, or sufficiency. Strong evidence is not automatically sufficient. Sufficiency is assessed per candidate, not globally.

## Semantic Evidence Lifecycle

Every stage must remain inspectable:

```text
RAW SIGNAL
→ SEMANTIC COMPONENT
→ SEMANTIC RELATIONSHIP
→ DIRECTIONAL SUPPORT / SUPPRESSION
→ CANDIDATE STRENGTH
→ CONFLICT ANALYSIS
→ SUFFICIENCY ASSESSMENT
→ CLASSIFIER CONSUMPTION
→ GATE CONSUMPTION
```

No stage may silently collapse evidence presence into decision resolution. Each transition must retain provenance sufficient to explain the next stage.

## Conceptual Domain Models

These are future conceptual models. This specification does not implement them.

### `SemanticEvidenceDirection`

- `SUPPORT`: increases the plausibility of the assessed candidate.
- `SUPPRESS`: decreases the plausibility of the assessed candidate.
- `NEUTRAL`: is semantically relevant but does not discriminate the candidate.
- `CONFLICTING`: supports incompatible interpretations or has materially opposed directional effects.

Direction is candidate-relative. A relationship that supports one candidate may suppress another or remain neutral for a third. A generic semantic relationship is never globally supportive by default.

### `SemanticEvidenceStrength`

- `WEAK`
- `MODERATE`
- `STRONG`

Strength describes deterministic evidence quality and weight. It does not describe final classifier confidence and does not by itself resolve uncertainty.

### `SemanticEvidenceSufficiency`

- `INSUFFICIENT`: evidence exists but does not resolve the decision.
- `PARTIAL`: evidence materially favors one direction, but meaningful uncertainty remains.
- `SUFFICIENT`: evidence strongly, coherently, and consistently resolves the candidate decision.
- `CONFLICTED`: meaningful evidence supports incompatible candidates or unresolved positive and negative directions.

Sufficiency is independent of the maximum strength of any individual item.

### `SemanticCandidateAssessment`

A future candidate assessment should conceptually expose:

- `candidate`
- `directional_support`
- `directional_suppression`
- `strength`
- `sufficiency`
- `relationship_provenance`
- `role_basis`
- `competing_candidates`
- `warnings`

Topic assessments are produced per domain candidate. Format assessments are produced per legal Editorial Format candidate for which semantic evidence exists. Neither dimension should retain only one global semantic-sufficiency value when candidates compete.

## Strength and Sufficiency Rules

One `STRONG` item may remain `PARTIAL` or `INSUFFICIENT` when:

- a competing domain remains;
- the primary subject role is unresolved;
- authority, actor, or method ambiguity remains;
- the article-treatment structure is incomplete;
- support and suppression conflict;
- evidence provenance represents a secondary context rather than the organizing subject.

Multiple `WEAK` items do not automatically accumulate into `SUFFICIENT`. Aggregation requires:

- independent evidence rather than duplicate lexical matches;
- semantic coherence;
- directional consistency;
- relevant role coverage;
- absence of unresolved material conflict.

Duplicate or correlated evidence may increase evidence quantity without increasing sufficiency.

## Topic Sufficiency Contract

A Topic candidate may be `SUFFICIENT` only when all applicable conditions hold:

- the primary subject/domain relationship is resolved;
- a domain-bearing subject, object, or event is present;
- authority, actor, and method alternatives do not dominate the domain interpretation;
- competing domains are absent or materially weaker;
- positive and negative evidence is directionally coherent;
- promotion provenance and role basis are explicit;
- the promotion is not derived solely from candidate existence.

A primary-domain candidate object existing is not sufficient proof of resolution.

### Role precedence and risk

Subject-bearing evidence normally has greater promotion relevance than contextual identity evidence. Conceptually:

```text
SUBJECT / OBJECT / EVENT
> RESULT / CHANGE / STATE
> ACTION
> ACTOR / AUTHORITY
> METHOD
```

This ordering is not an undocumented numeric score or an unconditional rule. It identifies semantic-role risk that must be visible in the assessment.

When a Topic is supported primarily through `AUTHORITY`, `ACTOR`, or `METHOD`, sufficiency normally remains `INSUFFICIENT` or `PARTIAL`, unless the article is explicitly organized around that authority, actor, or method as its subject.

### Domain promotion output

Domain promotion must expose separately:

- candidate domain;
- promotion strength;
- supporting relationship provenance;
- role basis;
- competing-domain evidence;
- candidate-relative direction;
- sufficiency state.

These concepts must not be encoded into one confidence value.

## Topic Confidence Contract

Classifier confidence and semantic sufficiency are independent.

- `HIGH` classifier confidence with `PARTIAL` semantic sufficiency is possible.
- `LOW` classifier confidence with `SUFFICIENT` semantic evidence is possible.

Semantic evidence may increase Topic confidence only when its candidate assessment is coherent and sufficient. `INSUFFICIENT` or `CONFLICTED` semantics must not increase confidence. `PARTIAL` evidence may make a limited, explicitly traceable contribution but must never imply resolution.

## Format Sufficiency Contract

Editorial Format sufficiency requires evidence about the article's organizing treatment. A support label alone cannot make a Format resolved.

- `TREND_UPDATE` requires coherent movement over time: current state, a prior or reference state, and direction, continuation, or comparison.
- `RESULT_REPORT` requires a completed observed result or outcome as the organizing purpose.
- `FACT_CHECK` requires a claim or assertion, verification or evaluation, and a truth/status conclusion.
- `GUIDE` requires actionable recommendation, instruction, or reader-directed behavior.
- `SERVICE` requires actionable logistical, procedural, eligibility, deadline, availability, location, or price/rate information.
- `ANALYSIS` requires structurally important cause, effect, consequence, trade-off, constraint, or implication composition.
- `EXPLAINER` requires an organizing process or mechanism and understanding-oriented treatment.
- `STANDARD_NEWS` requires positive event-reporting evidence when no stronger treatment structure becomes `SUFFICIENT`.

`STANDARD_NEWS` must not be an unexamined fallback merely because another Format has `PARTIAL` support. Its event-reporting evidence must be assessable as its own candidate.

## Directional Format Mapping

Future mappings must state explicitly:

- required positive structures;
- required negative structures or their required absence;
- direction produced for each candidate;
- strength produced;
- conditions for `SUFFICIENT`;
- conflict conditions;
- provenance retained.

Examples of generic directionality:

- current value plus prior comparison and continued movement → `SUPPORT TREND_UPDATE`;
- completed final outcome → `SUPPORT RESULT_REPORT` and may `SUPPRESS` future/schedule interpretations;
- future scheduled event → `SUPPRESS RESULT_REPORT`;
- claim without verification → `SUPPRESS FACT_CHECK`;
- procedure without claim evaluation → `SUPPORT SERVICE`, not `FACT_CHECK`.

A broad mapping such as “temporal word → `TREND_UPDATE`” cannot meet this contract.

### Result versus trend

`RESULT_REPORT` means a completed observed outcome is the organizing purpose. `TREND_UPDATE` means movement or change over time is the organizing purpose.

A completed result may contain numerical change without being a trend. A trend may contain current values without being a result report. The candidate assessments must preserve this boundary instead of selecting whichever structure fires first.

### Service versus fact-check

`SERVICE` answers actionable logistical, procedural, or requirements questions. `FACT_CHECK` evaluates the truth or status of a claim.

Authority confirmation alone does not create `FACT_CHECK`. Procedure details alone do not create verification.

### Analysis boundary

Cause/effect language contributes to `ANALYSIS` only when its relationships are structurally meaningful and organizing. Incidental consequence or background language remains insufficient.

## Conflict and Negative Evidence

Suppression participates directly in sufficiency. A candidate cannot be `SUFFICIENT` while material suppression remains unresolved unless positive evidence clearly dominates under documented, generic, deterministic logic.

If an article contains competing structures—for example, schedule details and completed-result language—the system must be able to emit `CONFLICTED`. If multiple candidates have `STRONG` support, `CONFLICTED` is preferred over arbitrary first-match precedence unless generic ontology precedence is legitimately decisive and explainable.

## False Sufficiency Protection

`FALSE_SUFFICIENCY` is a diagnostic anti-pattern:

```text
semantic evidence exists
+ candidate produced
+ uncertainty marked resolved
+ evidence is insufficient, partial, or conflicted
```

It must be detectable without benchmark labels through candidate assessments, unresolved-role findings, competing candidates, support/suppression conflict, provenance, and sufficiency state.

The architecture must explicitly prevent:

- partial semantics marked resolved;
- wrong directional support marked sufficient;
- confidence inflation from evidence quantity;
- authority, actor, or method evidence creating false primary sufficiency;
- duplicate lexical evidence masquerading as independent corroboration.

## Gate Consumption Contract

The Gate must eventually consume semantic sufficiency explicitly rather than infer resolution from evidence or candidate presence.

- `SUFFICIENT` may reduce the need for adjudication when direction agrees with the relevant deterministic decision and no material conflict remains.
- `PARTIAL` must not suppress unresolved-evidence triggers.
- `INSUFFICIENT` must not make a case appear resolved.
- `CONFLICTED` should normally strengthen adjudication need.

A wrong primary domain with `PARTIAL` or `INSUFFICIENT` sufficiency must not independently suppress Topic adjudication. Wrong Format support with `PARTIAL` or `CONFLICTED` sufficiency must not make Format adjudication unnecessary. Support existence is not resolution.

This document does not implement or modify Gate behavior.

## Provenance and Explainability

Every candidate assessment and sufficiency decision must be explainable using:

- support evidence identifiers and types;
- suppression evidence identifiers and types;
- semantic relationship identifiers and types;
- semantic role basis;
- competing candidates;
- conflict findings;
- aggregation and independence findings;
- warnings.

A hidden aggregate score is not sufficient provenance.

## Determinism

Given identical normalized evidence, direction, strength, conflict, and sufficiency must be identical. The MVP uses categorical deterministic semantics. It requires no external model, randomness, or floating-point probability calibration.

## Expected Diagnostic Outputs

Future diagnostics should expose, without requiring benchmark labels:

- per-candidate assessments;
- direction and strength;
- sufficiency and conflict state;
- false-sufficiency findings;
- directional-mapping provenance;
- confidence contribution eligibility;
- the distinction between evidence existence and resolved uncertainty.

## Scientific Status and Benchmark Independence

Batch 06 is a `DIAGNOSTIC_DEVELOPMENT_SET`. It is suitable only for:

- historical comparison;
- failure diagnosis;
- regression observation.

It is not a pristine unseen holdout and must not support final generalization claims. After the architecture stabilizes, final evaluation should use a newly preregistered, untouched Batch 07. This specification contains no benchmark-specific rules or copied benchmark text.

## Recommended Implementation Sequence

1. Add direction, strength, and sufficiency domain models.
2. Add per-candidate assessments to the semantic engine.
3. Migrate domain promotion and Format semantic mapping to candidate assessments.
4. Recalibrate classifier confidence contribution using sufficiency.
5. Update the Gate to consume sufficiency rather than evidence presence.
6. Run all regression suites.
7. Use Batch 06 only for diagnostic comparison.
8. Create Batch 07 as an untouched preregistered holdout.

Each phase should land with provider-neutral deterministic tests before the next phase changes downstream consumption.

## Non-Goals

This specification does not authorize or implement:

- production logic;
- Gate, classifier, evidence-engine, or semantic-engine changes;
- OpenAI or Prompt changes;
- a Resolver;
- benchmark relabeling;
- new regex dictionaries;
- case-specific rules;
- probabilistic calibration.
