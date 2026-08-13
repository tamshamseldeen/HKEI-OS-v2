# Editorial Format Subsystem V2 Specification

Status: **READY_FOR_IMPLEMENTATION**

Current Format V1 status: **LEGACY_BASELINE**

Recommended architecture: **HYBRID_DOCUMENT_PROFILE_AND_RULE_GRAPH**

Current compositional semantic engine reuse: **REUSE_AS_SUPPORT_ONLY**

## 1. Purpose and boundary

Editorial Format V2 classifies **how an article is written and organized**, not
what domain it discusses. Topic and Format may observe the same source, but they
must use separate representations, candidate spaces, evidence codes, decisions,
confidence, and ambiguity. A domain such as sport, economy, health, or politics
must never imply a treatment such as result report, analysis, service, or guide.

This specification replaces the architecture of Format classification without
changing the existing `EditorialFormat` enum. It does not implement production
code, a new Gate, a Resolver, a provider prompt, or Reader Intent V2.

## 2. Problem statement

The current architecture is insufficient in five distinct ways:

1. **Treatment structure recognition.** Local phrases and broad semantic
   relationships do not reliably identify the organizing function of headline,
   lead, and body. Repetition across sections can be counted as independent
   evidence even when it is one editorial assertion.
2. **Treatment competition.** A plausible signal can promote one label without
   a symmetric comparison against its closest alternatives. Defaults and
   precedence can therefore win without an observable positive profile.
3. **Confidence.** Confidence can reflect signal quantity or rule strength even
   when the winning treatment profile is incomplete, contradicted, or narrowly
   ahead of a competitor.
4. **Semantic evidence direction.** Topic-oriented or generic compositional
   semantics may point toward a treatment, but do not establish that treatment's
   document-level structure. Support, suppression, and contradiction need to be
   candidate-specific.
5. **Gate observability.** Scattered warnings do not expose whether the selected
   profile is complete, whether a competitor is close, or whether evidence is
   insufficient. The Gate consequently cannot observe many Format errors.

These are architectural failure classes, not claims about individual benchmark
articles. More case-driven lexical rules would preserve the same weaknesses.

## 3. Architectural decision

V2 uses a **HYBRID_DOCUMENT_PROFILE_AND_RULE_GRAPH**:

- Document profiles make every format operational: required, supporting, and
  disqualifying features; completeness; competitors; and confidence conditions.
- A rule graph compares profiles explicitly. Nodes are candidate states and
  structural features; typed edges support, suppress, contradict, or establish
  a boundary between candidates. The graph aggregates evidence but does not use
  first-match-wins precedence.
- Deterministic categorical outputs remain inspectable. MVP strength is
  `WEAK`, `MODERATE`, or `STRONG`; it is not an opaque probability.

The generic compositional semantic engine is **REUSE_AS_SUPPORT_ONLY**. Its
directional relationships can contribute secondary support or suppression, but
it remains optimized around semantic meaning and domain relationships. Making
it primary would continue to confuse what an article is about with how its
treatment is organized. Section-role extraction and Format-specific document
profiles are the primary V2 engine.

## 4. Conceptual pipeline

```text
RAW ARTICLE
  -> SECTION STRUCTURE EXTRACTION
  -> EDITORIAL TREATMENT FEATURES
  -> FORMAT CANDIDATE PROFILES
  -> CANDIDATE COMPETITION
  -> FORMAT DECISION
  -> FORMAT CONFIDENCE
  -> FORMAT AMBIGUITY
  -> GATE SIGNAL
```

Every stage returns an immutable provider-neutral result with stable reason
codes. Expected labels, benchmark annotations, provider answers, and downstream
Reader Intent are forbidden inputs to these stages.

## 5. Section structure

V2 represents three explicit sections:

- **HEADLINE:** the promised reader task—notification, urgency, explanation,
  instruction, verification, result, movement, encounter, or portrait.
- **LEAD:** the framing contract—what happened, why it matters, what was found,
  what the reader can do, which claim is tested, or whose perspective leads.
- **BODY:** the delivered organization—chronology, causal chain, mechanism,
  procedure, evidence test, Q&A, narrative scene, comparative series, or
  biographical arc.

Normalization links duplicated or near-duplicated propositions across sections
to one evidence identity. Repeating headline text in the lead or body may show
placement, but never creates additional independent support. Section role,
coverage, order, and transitions remain observable.

The section extractor also emits structural boundaries such as paragraphs,
lists, questions and answers, time-series sequences, claim/evidence/conclusion
segments, steps, quotations, scene changes, and entity-centered chronology.

## 6. Document-level feature vocabulary

Features are categorical observations backed by one or more section references.
No feature is bound to a single keyword.

| Feature | Operational meaning |
|---|---|
| `EVENT_REPORTING` | Lead establishes a reportable event and body supplies event facts or developments. |
| `TEMPORAL_MOVEMENT` | Multiple comparable observations establish direction or change over time. |
| `COMPLETED_OUTCOME` | A concluded process has an observed final state, winner, decision, measurement, or result. |
| `CAUSAL_EXPLANATION` | Causes, consequences, assumptions, and implications organize the document. |
| `MECHANISM_EXPLANATION` | The document organizes understanding of how a system, process, or concept works. |
| `ACTIONABLE_GUIDANCE` | Recommendations or choices are organized around a reader goal. |
| `PROCEDURAL_SERVICE` | Dates, prices, eligibility, documents, locations, availability, or steps enable a transaction or access. |
| `CLAIM_VERIFICATION` | A bounded claim is tested against evidence and receives a verdict. |
| `URGENT_BREAKING_SIGNAL` | Immediacy and unresolved live development organize headline, lead, and update structure. |
| `LIST_OR_RANKING_STRUCTURE` | Ordered items or comparative ranks are the primary delivery structure. |
| `INTERVIEW_QA_STRUCTURE` | Questions and attributed answers organize the body. |
| `OPINION_ARGUMENTATION` | A thesis is advanced through reasons, interpretation, and counter-position handling. |
| `COMPARATIVE_STRUCTURE` | Two or more entities, periods, choices, or states are systematically compared. |
| `NARRATIVE_SCENE_STRUCTURE` | Scenes, characters, detail, and narrative progression organize a reported story. |
| `BIOGRAPHICAL_ARC` | One person or entity is organized through background, milestones, and present relevance. |

Each feature records section coverage, evidence identity, direction, strength,
and contradiction. Lexical cues may help locate evidence but cannot independently
establish a document feature.

## 7. Candidate profile contract

One immutable profile exists for every `EditorialFormat`. A profile declares:

- `required_features`: all-of and explicitly declared any-of groups;
- `supporting_features`: evidence that strengthens but cannot create the profile;
- `disqualifying_features`: contradictions or structures owned by another format;
- `competing_formats`: candidates requiring direct boundary comparison;
- `minimum_structural_completeness`: required section and feature coverage;
- `confidence_conditions`: conditions for high, medium, and low confidence;
- `ambiguity_conditions`: conditions that yield competing, insufficient, or
  contradictory states.

An evaluated candidate exposes its matched/missing required features, support,
negative evidence, section coverage, completeness, strength, competing edges,
reason codes, and warnings.

### Completeness

- `INCOMPLETE`: a required feature group or required section role is absent.
- `PARTIAL`: the organizing treatment is meaningful but one required structural
  element, section transition, or coverage condition is weak or missing.
- `COMPLETE`: every required feature group and minimum section coverage is met.

Completeness describes treatment structure, not correctness or confidence.

### Strength

- `WEAK`: isolated, indirect, or single-section evidence.
- `MODERATE`: coherent multi-signal evidence with limited section coverage or a
  meaningful competitor.
- `STRONG`: coherent independent evidence across required section roles with no
  material contradiction.

## 8. Operational profiles for all formats

### 8.1 `STANDARD_NEWS`

- **Definition:** a bounded event or development reported primarily to update.
- **Reader experience:** learn what happened, who was involved, where/when, and
  essential context.
- **Required structure:** `EVENT_REPORTING`; event-framing headline or lead; body
  facts or attributed development beyond mere repetition.
- **Optional structure:** chronology, quotes, concise background, consequences.
- **Negative evidence:** urgency governs the whole document; explanation,
  procedure, verdict, final outcome, trend, Q&A, portrait, or argument governs.
- **Closest competitors:** `BREAKING`, `ANALYSIS`, `EXPLAINER`, `RESULT_REPORT`,
  `TREND_UPDATE`, `SERVICE`.
- **Conceptual example:** an institution announces a completed decision and the
  article reports its terms and immediate context.

`STANDARD_NEWS` is never “nothing else matched.” Without observable event-report
structure it remains incomplete and cannot be a confident default.

### 8.2 `BREAKING`

- **Definition:** an urgent, materially unfolding development whose immediacy is
  the organizing treatment.
- **Reader experience:** receive a time-critical update with known facts and
  explicit unresolved state.
- **Required structure:** `URGENT_BREAKING_SIGNAL` plus `EVENT_REPORTING`; headline
  and lead express immediacy; body has live/update or explicitly incomplete facts.
- **Optional structure:** timestamped updates, emergency instruction, attribution.
- **Negative evidence:** mere recent publication, retrospective reporting,
  completed stable account, promotional urgency.
- **Closest competitors:** `STANDARD_NEWS`, `SERVICE`, `RESULT_REPORT`.
- **Conceptual example:** a developing evacuation announced minutes ago with
  confirmed facts and pending details.

### 8.3 `SERVICE`

- **Definition:** logistical information that enables access, compliance, or a
  concrete transaction.
- **Reader experience:** determine whether, when, where, and how to obtain or use
  a service.
- **Required structure:** `PROCEDURAL_SERVICE`; at least two operational elements
  such as dates, prices, eligibility, documents, locations, or availability.
- **Optional structure:** steps, contacts, exceptions, deadlines, warnings.
- **Negative evidence:** recommendation-led choice, general explanation, a claim
  verdict, or an event announcement without actionable logistics.
- **Closest competitors:** `GUIDE`, `STANDARD_NEWS`, `FACT_CHECK`.
- **Conceptual example:** application dates, eligibility, required documents, fee,
  location, and submission route for a public service.

### 8.4 `GUIDE`

- **Definition:** organized recommendations or instructions for achieving a
  reader goal or making a choice.
- **Reader experience:** decide what to do and carry out a goal successfully.
- **Required structure:** `ACTIONABLE_GUIDANCE`; goal framing; ordered actions,
  options, or recommendations with decision-relevant explanation.
- **Optional structure:** checklist, ranking, comparison, cautions, examples.
- **Negative evidence:** logistics-only service data, mechanism-only explanation,
  or event reporting with incidental advice.
- **Closest competitors:** `SERVICE`, `EXPLAINER`, `FEATURE`.
- **Conceptual example:** how to choose and safely use a household device based on
  needs and trade-offs.

### 8.5 `EXPLAINER`

- **Definition:** a treatment organized to make a process, mechanism, concept, or
  system understandable.
- **Reader experience:** understand how something works and how its parts connect.
- **Required structure:** `MECHANISM_EXPLANATION`; question/concept framing; body
  decomposes stages, components, or relationships.
- **Optional structure:** definitions, examples, diagrams, limited causes.
- **Negative evidence:** thesis-led implications, event-first reporting, or
  action-first recommendations.
- **Closest competitors:** `ANALYSIS`, `GUIDE`, `STANDARD_NEWS`.
- **Conceptual example:** how a new voting mechanism processes ballots from input
  through validation and counting.

### 8.6 `FEATURE`

- **Definition:** a reported narrative or thematic treatment built around human,
  cultural, historical, or experiential depth.
- **Reader experience:** encounter a subject through scenes, voices, detail, and
  thematic progression.
- **Required structure:** `NARRATIVE_SCENE_STRUCTURE` or an equivalent thematic
  arc; body development beyond event summary.
- **Optional structure:** history, multiple voices, sensory detail, comparisons.
- **Negative evidence:** Q&A governs, one subject's biography governs, urgent
  update, procedure, or compact event report.
- **Closest competitors:** `PROFILE`, `INTERVIEW`, `ANALYSIS`, `STANDARD_NEWS`.
- **Conceptual example:** a reported narrative about how a neighborhood adapts to
  a long-term change through several residents and scenes.

### 8.7 `FACT_CHECK`

- **Definition:** a bounded claim is verified and receives an evidence-based
  conclusion.
- **Reader experience:** know what was claimed, how it was checked, and the verdict.
- **Required structure:** all three of claim, verification, and conclusion;
  collectively `CLAIM_VERIFICATION`.
- **Optional structure:** source hierarchy, uncertainty, claim decomposition.
- **Negative evidence:** claim quotation without testing, service correction,
  opinion rebuttal, or ordinary reporting of disagreement.
- **Closest competitors:** `STANDARD_NEWS`, `ANALYSIS`, `SERVICE`.
- **Conceptual example:** a circulating numerical claim is traced to its source,
  compared with records, and rated with limitations.

### 8.8 `ANALYSIS`

- **Definition:** a document-level causal, interpretive, or implications-led
  treatment.
- **Reader experience:** understand why events occurred, what drives them, and
  what consequences or scenarios follow.
- **Required structure:** `CAUSAL_EXPLANATION`; a question or thesis; multi-step
  reasoning connecting evidence to implications.
- **Optional structure:** comparison, counterargument, scenarios, expert views.
- **Negative evidence:** background context alone, mechanism-only teaching,
  event-first summary, or unsupported opinion.
- **Closest competitors:** `EXPLAINER`, `STANDARD_NEWS`, `FEATURE`.
- **Conceptual example:** an evidence-led account of drivers behind a policy shift
  and its plausible consequences.

### 8.9 `INTERVIEW`

- **Definition:** an attributed exchange in which questions and answers organize
  the article.
- **Reader experience:** encounter a subject's views through the interview exchange.
- **Required structure:** `INTERVIEW_QA_STRUCTURE`; identifiable interviewer
  questions and attributed answers across the body.
- **Optional structure:** introductory framing, edited transcript notes, follow-ups.
- **Negative evidence:** a report merely containing quotations, a narrative
  portrait, or one isolated question.
- **Closest competitors:** `PROFILE`, `FEATURE`, `STANDARD_NEWS`.
- **Conceptual example:** a structured conversation with a researcher presented as
  a sequence of substantive questions and answers.

### 8.10 `PROFILE`

- **Definition:** an entity-centered portrait organized by identity, background,
  milestones, character, and current relevance.
- **Reader experience:** understand who or what the subject is across time.
- **Required structure:** `BIOGRAPHICAL_ARC`; a stable focal subject; background
  plus at least one milestone and present-relevance section.
- **Optional structure:** quotes, achievements, controversies, scene-setting.
- **Negative evidence:** Q&A governs, a single current event governs, or multiple
  subjects form a thematic feature.
- **Closest competitors:** `FEATURE`, `INTERVIEW`, `STANDARD_NEWS`.
- **Conceptual example:** a person-centered account of origins, career milestones,
  defining choices, and present role.

### 8.11 `RESULT_REPORT`

- **Definition:** the primary treatment reports a completed, observed outcome.
- **Reader experience:** learn the final result and the decisive path to it.
- **Required structure:** `COMPLETED_OUTCOME`; explicit completion; final state or
  measured result; body explains decisive events or result components.
- **Optional structure:** score, ranking, statistics, reactions, consequences.
- **Negative evidence:** future schedule, projection, incomplete process, movement
  across periods, or ordinary announcement lacking an observed outcome.
- **Closest competitors:** `TREND_UPDATE`, `STANDARD_NEWS`, `BREAKING`.
- **Conceptual example:** final election count or completed match result with the
  decisive sequence and official outcome.

### 8.12 `TREND_UPDATE`

- **Definition:** a document organized around directional movement across multiple
  comparable observations over time.
- **Reader experience:** understand what is rising, falling, accelerating,
  slowing, or changing and over which interval.
- **Required structure:** `TEMPORAL_MOVEMENT`; at least two comparable time points
  or periods; explicit direction; current observation in series context.
- **Optional structure:** drivers, comparison, volatility, forecast caveats.
- **Negative evidence:** one static current value, one completed outcome, ordinary
  market event, or unsupported directional wording.
- **Closest competitors:** `RESULT_REPORT`, `STANDARD_NEWS`, `ANALYSIS`.
- **Conceptual example:** a multi-period change in prices or participation with
  comparable values and direction.

## 9. Candidate competition

All viable profiles are evaluated before selection. For each declared competitor
edge, the rule graph applies a boundary test and records winner, loser, tie, or
unresolved. Selection orders candidates by:

1. completeness (`COMPLETE` before `PARTIAL` before `INCOMPLETE`);
2. required-feature satisfaction;
3. candidate-specific negative evidence;
4. categorical strength;
5. boundary-test outcome.

No enum order or first match breaks a substantive tie. A tie becomes ambiguity.
Mandatory boundary tests include:

| Boundary | Deciding question |
|---|---|
| `STANDARD_NEWS` / `BREAKING` | Does verified immediacy and unresolved live structure organize the document? |
| `STANDARD_NEWS` / `ANALYSIS` | Are causal reasoning and implications the organizing purpose rather than context? |
| `STANDARD_NEWS` / `EXPLAINER` | Does mechanism understanding organize the body rather than event facts? |
| `STANDARD_NEWS` / `RESULT_REPORT` | Is a completed observed outcome, not merely a decision or announcement, central? |
| `RESULT_REPORT` / `TREND_UPDATE` | Is the document about one final outcome or movement across comparable periods? |
| `SERVICE` / `GUIDE` | Does it enable access/compliance through logistics, or guide choices/actions toward a goal? |
| `SERVICE` / `FACT_CHECK` | Are logistics corrected, or is a bounded claim actually verified and concluded? |
| `ANALYSIS` / `EXPLAINER` | Does it explain causes/implications, or mechanisms/components? |
| `FEATURE` / `PROFILE` | Is the organizing arc thematic/multi-voice, or centered on one subject's biography? |
| `INTERVIEW` / `PROFILE` | Does Q&A structure govern, or is interview material evidence inside a portrait? |

## 10. Ambiguity and confidence

Format ambiguity is explicit:

- `CLEAR`: one complete or clearly dominant profile, with no material contradiction.
- `COMPETING`: two or more viable profiles remain close after boundary tests.
- `INSUFFICIENT_EVIDENCE`: no candidate reaches the minimum structural profile.
- `CONTRADICTORY`: evidence materially supports and disqualifies the same candidate,
  or incompatible section treatments cannot be resolved.

Confidence is separate from evidence count:

- `HIGH`: winner is `COMPLETE`, strength is `STRONG`, boundary tests are decisive,
  ambiguity is `CLEAR`, and contradiction is low.
- `MEDIUM`: meaningful `PARTIAL` or `COMPLETE` structure exists, but strength is
  moderate, a competitor remains, or limited contradiction exists.
- `LOW`: evidence is weak/incomplete, ambiguity is insufficient or contradictory,
  or no clear winner exists.

High confidence is forbidden for an incomplete profile or competing ambiguity.

## 11. Result and downstream interfaces

The V2 result should preserve the current public classification fields where
possible—selected `EditorialFormat`, categorical confidence, reason codes,
supporting signals, and warnings—while adding a versioned diagnostic object:

- leading Format candidate;
- competing candidates and boundary outcomes;
- completeness and strength per candidate;
- supporting structural features with section references;
- missing required and negative features;
- ambiguity state;
- contradiction and warnings.

### Future Gate contract

Gate V2 should consume Format confidence, ambiguity, candidate competition, and
leading-profile completeness. It should be able to open on incomplete evidence,
unresolved competition, contradiction, or low confidence without reconstructing
these facts from scattered semantic warnings. Gate V2 is not implemented here;
the current Gate remains unchanged during shadow migration.

### Reader Intent

The interface is `Format V2 result -> Reader Intent`. Reader Intent may use the
selected format as one downstream input, but remains a separate model with its
own enum, evidence, confidence, and tests. This specification does not redesign it.

### Provider adjudication

The future provider-neutral request can expose the leading candidate, competitors,
profile completeness, supporting structural features, negative features, and
ambiguity state. It must not expose chain-of-thought. Prompt v1.1 and the current
Request Builder remain unchanged in this task.

## 12. Backward-compatible migration

There is no flag-day rewrite:

1. **Phase 1 — V2 models:** add provider-neutral feature, profile, evaluation,
   completeness, strength, competition, ambiguity, and result models.
2. **Phase 2 — extractor:** implement section/document feature extraction with
   evidence identity and duplicate suppression.
3. **Phase 3 — evaluator:** implement all 12 profiles and the competition graph.
4. **Phase 4 — shadow classifier:** run V1 and V2 side by side; V1 remains the
   production result and V2 cannot mutate Topic, Format, Reader Intent, confidence,
   or Gate.
5. **Phase 5 — cross-batch offline comparison:** use evaluated corpora only for
   diagnosis and historical regression, never a new generalization claim.
6. **Phase 6 — untouched holdout:** preregister and evaluate a new corpus with
   frozen labels before any prediction.
7. **Phase 7 — Gate shadow consumption:** measure a future Gate contract using V2
   ambiguity, completeness, competition, and confidence without production mutation.
8. **Phase 8 — production decision:** adopt, guard, or reject V2 based on the
   preregistered criteria and regression evidence.

The current enum and benchmark readers remain compatible. An adapter may project
the selected V2 candidate into the current `EditorialFormatClassification` while
the richer diagnostics stay versioned and optional.

## 13. V1 freeze and benchmark policy

Format V1 is frozen as **LEGACY_BASELINE**. No more case-driven regex, precedence,
or semantic mapping tuning is permitted. Only bug, security, and independently
demonstrated regression fixes are allowed.

Batch 07 and Batch 08 are evaluated corpora. They may support diagnostic
comparison and historical regression testing, but cannot establish V2
generalization. Any final V2 claim requires a new untouched preregistered corpus;
expected labels must be frozen before V2, Gate, provider, or assessor execution.

## 14. Test strategy

### A. Synthetic structural unit tests

Use small, newly authored documents to isolate section roles, duplicate evidence,
feature extraction, every profile's required/negative conditions, every mandatory
competition edge, completeness, strength, ambiguity, and confidence invariants.
Tests vary wording while preserving structure and vary structure while preserving
keywords. Keyword presence alone must not determine the answer.

### B. Raw Arabic document-level fixtures

Use newly authored generic Arabic fixtures—not copied or paraphrased benchmark
articles—covering news announcement, urgent breaking update, analysis, explainer,
service, guide, result report, trend update, fact-check, feature, interview, and
profile. Include hard negative pairs, section reordering, repeated headline/lead
phrases, missing required sections, contradiction, and mixed treatments.

### C. Untouched holdout evaluation

Register a new diverse corpus, hash raw inputs, freeze human labels and risks,
isolate truth until after shadow results, and measure deterministic/effective
accuracy, Gate precision/recall, changes, regressions, profile validity, and safety.
No holdout-driven tuning is permitted.

## 15. Preregistered success criteria

Before production integration, the new untouched holdout must demonstrate:

- deterministic Format accuracy at least 70%, **or** effective Format accuracy
  after adjudication at least 80%;
- Format Gate recall at least 80%;
- at most one Format adjudication regression per ten cases;
- valid candidate/profile diagnostics and internal invariants;
- no production mutation throughout shadow evaluation.

Passing only historical Batch 07/08 regression tests is insufficient.

## 16. Resolver boundary

Topic Resolver design may proceed independently. Full Format authority must wait
until V2 satisfies the untouched-holdout criteria. A `LIMITED_RESOLVER` is an
acceptable intermediate architecture: Topic may resolve within its own validated
contract while Format remains guarded, shadow-only, or adjudication-heavy. Reader
Intent must not silently inherit an unresolved Format as authoritative.

## 17. Non-goals

This specification does not implement production behavior, tune any benchmark,
add Gate rules or Format regexes, call OpenAI, change Prompt v1.1, implement a
Resolver, redesign Reader Intent, or modify expected labels.

## 18. Acceptance decision

**READY_FOR_IMPLEMENTATION.** All 12 enum profiles have operational required,
supporting, negative, competition, completeness, confidence, ambiguity, and
conceptual-example contracts. The pipeline, Gate/provider interfaces,
backward-compatible migration, testing policy, untouched-holdout requirement,
V1 freeze, and Resolver boundary are defined.
