# HKEI OS v2 — Semantic Adjudication Specification

## 1. Purpose

Semantic Adjudication is a structured fallback used when deterministic lexical, contextual, and compositional evidence cannot resolve editorial ambiguity with sufficient confidence. It does not replace deterministic classification. It operates only after the deterministic pipeline reaches a defined uncertainty boundary.

## 2. Architectural Position

The target architecture is:

```text
Source Intake
→ Risk Assessment
→ Fact Extraction
→ Contextual Editorial Evidence
→ Compositional Semantic Evidence
→ Deterministic Topic / Format
→ Adjudication Gate
   ├── no adjudication required
   │     → deterministic result
   └── adjudication required
         → Semantic Adjudicator
         → Structured Adjudication Result
         → Resolution Layer
→ Reader Intent
→ Strategy
→ Planning
→ Prompting
→ Generation
```

Reader Intent remains downstream of resolved Topic and Format. It is outside the first adjudication scope unless a future specification explicitly expands that scope.

## 3. Core Principle

The system prefers deterministic resolution when sufficient and uses semantic adjudication only when unresolved. The objective is not to ask a model to classify every article; it is to adjudicate only when existing structured evidence says the deterministic result is uncertain, incomplete, or conflicted.

## 4. Scope of MVP Adjudication

The MVP may resolve only:

- Topic
- Editorial Format

It must not adjudicate Reader Intent, Risk, Attribution, Uncertainty, claim truth, factual verification, or generation strategy.

## 5. Gate Inputs

The gate may inspect only existing structured outputs and the minimum source text needed for resolution:

- topic classification, confidence, reason codes, supporting signals, and warnings;
- format classification, confidence, reason codes, supporting signals, and warnings;
- contextual evidence counts, support labels, and suppression labels;
- semantic relationship count and summaries;
- primary and secondary semantic-domain candidates;
- semantic format support and suppression;
- content classification;
- source headline, lead, and selected body excerpts where needed.

Benchmark expectations and human annotations are forbidden gate inputs.

## 6. Candidate Topic Trigger Signals

The HKEI-097 findings identify these candidate signals:

| Signal | Provisional role | Interpretation |
| --- | --- | --- |
| `NO_PRIMARY_SEMANTIC_DOMAIN` | Soft trigger | Domain evidence is absent; insufficient alone when a specific topic has high confidence and no conflict. |
| `TOPIC_LOW_CONFIDENCE` | Soft trigger | The deterministic topic is uncertain. |
| `TOPIC_GENERAL_FALLBACK` | Soft trigger | The system could not select a specific topic. |
| `CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP` | Soft trigger | Evidence exists but composition did not resolve it. |
| `METHOD_SUBJECT_AMBIGUITY` | Hard trigger candidate | Available evidence indicates a surface method may be displacing the primary subject. |
| `SEMANTIC_DOMAIN_CONFLICT` | Hard trigger candidate | Structured semantic domains conflict with the deterministic topic. |
| `MULTIPLE_COMPETING_TOPIC_SIGNALS` | Soft trigger | More than one topic has meaningful structured support. |

No individual designation finalizes production behavior. A hard-trigger candidate still requires schema validation and an approved policy. A soft trigger should normally participate in a combination. A valid specific topic with high confidence and no unresolved conflict is a non-trigger even when no semantic domain exists.

## 7. Candidate Format Trigger Signals

| Signal | Provisional role | Interpretation |
| --- | --- | --- |
| `FORMAT_LOW_CONFIDENCE` | Soft trigger | The deterministic structure decision is uncertain. |
| `ANALYTICAL_CONTEXT_WITH_STANDARD_NEWS_FALLBACK` | Soft trigger | Analysis support exists but the final format used a news fallback. Prediction alone is insufficient. |
| `EXPLAINER_STRUCTURE_UNRESOLVED` | Soft trigger | Mechanism or structural explanation is present but unresolved. |
| `CONTEXTUAL_FORMAT_SUPPORT_NOT_PROMOTED` | Hard trigger candidate | Structured support exists and was not reflected in the final decision. |
| `FORMAT_CONFLICT` | Hard trigger candidate | Strong structured format signals disagree. |

`STANDARD_NEWS` by itself is a non-trigger. The gate must not automatically adjudicate every news result.

## 8. Gate Policy Concept

The conceptual gate states are:

- `NOT_REQUIRED`
- `TOPIC_REQUIRED`
- `FORMAT_REQUIRED`
- `TOPIC_AND_FORMAT_REQUIRED`

These are specification concepts, not enums or implemented constants.

## 9. Gate Safety Rule

A single weak signal need not trigger adjudication. A combination such as `GENERAL` topic, low confidence, and no primary semantic domain strongly supports topic adjudication. By contrast, a valid specific topic, high confidence, and no unresolved conflict may remain deterministic despite missing semantic evidence. Gate decisions must be based on combinations of structured signals rather than isolated flags.

## 10. Avoiding External Calls

A future policy should return `NOT_REQUIRED` for a specific, high-confidence deterministic topic with no unresolved conflict. This preserves the successful deterministic pattern represented by Batch 05 case 049 and minimizes unnecessary provider calls.

## 11. Adjudication Input Contract

A future structured request concept contains:

- `request_id`
- `title`
- `lead`
- `body_excerpt`
- `deterministic_topic`
- `topic_confidence`
- `deterministic_format`
- `format_confidence`
- `content_type`
- `contextual_support_labels`
- `contextual_suppressions`
- `semantic_relationship_summary`
- `primary_domain_candidates`
- `secondary_domain_candidates`
- `semantic_format_support`
- `semantic_format_suppression`
- `topic_reason_codes`
- `topic_warnings`
- `format_reason_codes`
- `format_warnings`
- `candidate_topics`
- `candidate_formats`

The request must never include benchmark labels.

## 12. Minimal Text Principle

The adjudicator receives the minimum source text necessary to resolve ambiguity, in this preferred order:

1. headline;
2. lead;
3. selected relevant sentences.

Full text remains a future last resort when local evidence cannot resolve ambiguity. Sending an entire article by default is prohibited.

## 13. Candidate Topic Set

Adjudication must select only from the current `Topic` enum:

```text
POLITICS
ECONOMY
BUSINESS
TECHNOLOGY
SPORTS
GOVERNMENT
WEATHER
HEALTH
CULTURE
SCIENCE
EDUCATION
CRIME
ENTERTAINMENT
WORLD
GENERAL
```

Arbitrary free-text topic labels are invalid. This specification does not modify the enum.

## 14. Candidate Format Set

Adjudication must select only from the current `EditorialFormat` enum:

```text
BREAKING
STANDARD_NEWS
SERVICE
GUIDE
EXPLAINER
FEATURE
FACT_CHECK
ANALYSIS
INTERVIEW
PROFILE
RESULT_REPORT
TREND_UPDATE
```

Unknown or invented formats are invalid.

## 15. Structured Adjudication Output

A future structured response concept contains:

- `adjudicated_topic`
- `adjudicated_format`
- `topic_confidence`
- `format_confidence`
- `topic_reason`
- `format_reason`
- `topic_evidence_refs`
- `format_evidence_refs`
- `ambiguity_remaining`
- `warnings`
- `provider_metadata`

## 16. Confidence

Adjudicator confidence is categorical: `HIGH`, `MEDIUM`, or `LOW`. Provider self-reported probabilities are not authoritative. HKEI owns confidence validation and resolution policy.

## 17. Evidence References

Decisions must cite supplied evidence using concise references such as `HEADLINE`, `LEAD`, `BODY_SENTENCE_2`, `SEMANTIC_RELATIONSHIP_1`, or `CONTEXTUAL_ITEM_4`. References must resolve to the request evidence and may be accompanied by a short rationale.

## 18. No Chain-of-Thought Requirement

The provider must be asked for structured classification, concise rationale, and evidence references. It must not be asked for hidden reasoning, private deliberation, or detailed step-by-step chain-of-thought.

## 19. Provider Independence

The core architecture depends on an abstraction such as `SemanticAdjudicationProvider`, never directly on OpenAI, Anthropic, Gemini, Copilot, or a local-model implementation. Provider choice is an adapter concern.

## 20. Provider Capabilities

A future provider must support structured input and output, restricted topic and format candidates, bounded timeouts, explicit errors, a model identifier, and usage metadata. Streaming is not required.

## 21. Resolution Layer

The adjudicator does not mutate deterministic classifications. A separate Resolution Layer combines the deterministic and adjudication results and produces resolved Topic and Format. This separation is mandatory for auditability.

## 22. Resolution Principles

- If adjudication is not required, use the deterministic result.
- If required and a provider returns a valid `HIGH` or `MEDIUM` structured result, an approved resolution policy may prefer it.
- If provider output is invalid, retain the deterministic result and add a warning.
- If the provider fails, retain the deterministic result.
- Provider failure must not block article processing by default.

These are conceptual rules; acceptance thresholds remain undefined.

## 23. Fail-Open Behavior

Provider outage must not break editorial processing. The deterministic result remains usable and a future warning such as `SEMANTIC_ADJUDICATION_UNAVAILABLE` records the outage. This task does not implement that warning.

## 24. Invalid Provider Output

The future system rejects unknown Topic values, unknown EditorialFormat values, missing required fields, malformed structured responses, and unsupported labels. Rejection falls back to the deterministic result.

## 25. Determinism and Auditability

Because provider adjudication may not be perfectly deterministic, an audit record should store provider, model, request schema version, response schema version, input fingerprint, structured result, timestamp, and usage metadata. Secrets must never be stored.

## 26. Input Fingerprint

A future deterministic fingerprint should cover the selected source text, candidate labels, structured evidence, and schema version. It enables caching, repeatability, cost control, and audit comparison. Hashing is not implemented by this specification.

## 27. Cache Concept

Cached adjudication may be reused only when input fingerprint, provider, model, and schema version match exactly. Any source, evidence, candidate, model, or schema change invalidates reuse.

## 28. Cost Control

Future controls should:

- avoid adjudicating confident deterministic cases;
- limit source text;
- cache identical requests;
- batch only when isolated structured responses remain guaranteed;
- record token and usage metadata;
- support an optional per-run adjudication budget.

## 29. Latency Control

Adjudication is optional and bounded. A future implementation must support timeouts, deterministic fallback, and a maximum retry count. It must never block indefinitely.

## 30. Topic Examples

Batch 05 is used only as architecture-learning evidence:

| Case | Deterministic observation | Candidate gate state | Architectural lesson |
| --- | --- | --- | --- |
| 041 | `GENERAL / LOW`, no primary domain, attribution and uncertainty context | `TOPIC_REQUIRED` | A geopolitical/security event was not represented by the deterministic ontology. |
| 042 | `TECHNOLOGY / LOW` for a criminal/legal primary event | `TOPIC_REQUIRED` | A surface mechanism can displace the primary event. |
| 043 | `GENERAL / LOW` for executive policy with constitutional challenge | `TOPIC_REQUIRED` | Policy, legal, and executive-action composition is unresolved. |
| 044 | `GENERAL + STANDARD_NEWS` for war constraints, causes, and impacts | `TOPIC_AND_FORMAT_REQUIRED` | Both domain and analytical structure are unresolved. |
| 045 | Military restructuring with explanatory framing | `TOPIC_AND_FORMAT_REQUIRED` | Domain and explainer structure are unresolved. |
| 046 | `TECHNOLOGY / STANDARD_NEWS` despite contextual `FORMAT_ANALYSIS` and `INTENT_UNDERSTAND_IMPACT` | `TOPIC_AND_FORMAT_REQUIRED` | Useful contextual evidence can exist without successful composition or promotion. |
| 047 | Universities as the surface institution in a political/legal conflict | `TOPIC_AND_FORMAT_REQUIRED` | The affected institution need not define the primary event domain. |
| 048 | Intelligence prediction with correct `STANDARD_NEWS` format | `TOPIC_REQUIRED` | Prediction and uncertainty do not automatically imply analysis. |
| 049 | Aligned economy evidence and primary semantic domain | `NOT_REQUIRED` | Confident aligned deterministic evidence should bypass adjudication. |
| 050 | Violent incident unresolved as a crime event | `TOPIC_REQUIRED` | Reusable event-domain modeling is needed. |

These examples do not define case-specific production rules.

## 31. Format Adjudication Principles

Format adjudication distinguishes `STANDARD_NEWS` from `ANALYSIS`, `EXPLAINER`, `GUIDE`, and `SERVICE` using sustained editorial structure rather than isolated words.

## 32. ANALYSIS Structure

Conceptual analysis support includes cause, consequence, impact, tradeoff, constraint, interpretation, and forward implication. A prediction alone is insufficient.

## 33. EXPLAINER Structure

Conceptual explainer support includes how something works, why it is changing, background plus mechanism, process explanation, and structural transformation. A question-mark headline alone is insufficient.

## 34. STANDARD_NEWS Safety

`STANDARD_NEWS` remains appropriate when a source primarily reports an event, announcement, estimate, result, or incident without sustained explanatory or analytical structure.

## 35. Reader Intent

Reader Intent remains downstream. Resolved Topic and Format feed `ReaderIntentClassifierV2`; the MVP adds no Reader Intent adjudication. The Batch 05 diagnostic baseline is zero direct intent failures and four intent failures downstream from wrong formats.

## 36. Relationship to Risk

Editorial semantic adjudication remains separate from Risk, Attribution, Uncertainty, and claim handling. A later safety layer may define its own separate contract. Editorial and safety adjudication must not be mixed.

## 37. Relationship to Human Risk Annotations

Benchmark human-risk annotations are evaluation metadata only. They must never be passed into the gate, adjudication request, provider, resolver, or editorial decision.

## 38. Privacy and Secrets

Provider requests and stored logs must exclude API keys, credentials, environment variables, and private system metadata. Text minimization and established data-handling policy apply.

## 39. Security Boundary

Provider output is untrusted input. Validate every returned value before resolution and never execute provider-returned code.

## 40. Future Provider Interface

Conceptually:

```python
class SemanticAdjudicationProvider:
    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        ...
```

This is illustrative documentation, not an implementation.

## 41. Future Gate Interface

Conceptually:

```python
class SemanticAdjudicationGate:
    def evaluate(
        self,
        deterministic_result,
        contextual_evidence,
        semantic_evidence,
    ) -> SemanticAdjudicationDecision:
        ...
```

## 42. Future Resolver Interface

Conceptually:

```python
class SemanticAdjudicationResolver:
    def resolve(
        self,
        deterministic_result,
        adjudication_result,
    ):
        ...
```

No interface in Sections 40–42 is created by this task.

## 43. Experimental Rollout

### Phase 1: shadow adjudication

- The deterministic result remains the production result.
- The adjudicator runs only for triggered benchmark cases.
- Outputs are compared with no behavior change.

### Phase 2: experimental resolution workflow

- A resolver may use a validated adjudication result.
- The workflow remains benchmark-only.

### Phase 3: production integration

- Integration occurs only after unseen validation and explicit approval.

## 44. Shadow Mode

Shadow mode is mandatory before production use. It stores the deterministic result, adjudicated result, and agreement or disagreement without replacing the deterministic decision.

## 45. Evaluation Metrics

Future evaluation measures:

- trigger rate;
- topic accuracy among triggered cases;
- format accuracy among triggered cases;
- false-trigger rate;
- deterministic cases unnecessarily adjudicated;
- adjudicator agreement with deterministic high-confidence cases;
- fallback rate;
- provider error rate;
- cost per article;
- latency per adjudication.

## 46. Benchmark Hygiene

Batch 05 has been opened and analyzed. It is architecture-learning evidence and must not be treated as unseen validation after informing design. Future adjudication evaluation requires a new unseen batch.

## 47. Baselines

| Measure | Baseline |
| --- | ---: |
| Tests | 1,131 passed |
| Batch 01 Topic | 100% |
| Batch 02 Full | 100% |
| Batch 03 Full | 100% |
| Batch 05 Topic | 10% |
| Batch 05 Format | 60% |
| Batch 05 Intent | 60% |
| Batch 05 Full | 10% |
| Direct Intent Failures | 0 |
| Downstream Intent Failures | 4 |
| Semantic Adjudication Topic Candidates | 9 |
| Semantic Adjudication Format Candidates | 4 |

## 48. Trigger Findings from HKEI-097

| Trigger | Diagnostic finding |
| --- | ---: |
| `NO_PRIMARY_SEMANTIC_DOMAIN` | 9/9 topic mismatches captured |
| `TOPIC_LOW_CONFIDENCE` | 7/7 |
| `TOPIC_GENERAL_FALLBACK` | 6/6 |
| `CONTEXT_PRESENT_BUT_NO_SEMANTIC_RELATIONSHIP` | 6/6 |
| `METHOD_SUBJECT_AMBIGUITY` | 2/2 |

These are diagnostic findings, not final thresholds or production policy.

## 49. Non-Goals

This specification creates no provider implementation, OpenAI integration, API call, prompt implementation, production gate, final threshold, classifier replacement, benchmark tuning, risk adjudication, claim adjudication, or web research.

## 50. Acceptance Criteria

This specification defines:

- a gated fallback architecture;
- Topic and Editorial Format MVP scope;
- provider-independent request and response concepts;
- gate and resolution concepts;
- fail-open and invalid-output behavior;
- enum-restricted outputs and validation requirements;
- caching, fingerprinting, and audit concepts;
- cost and latency controls;
- mandatory shadow-mode rollout;
- separation from Reader Intent and Risk;
- no case-specific production rules;
- no dependency on a single provider.
