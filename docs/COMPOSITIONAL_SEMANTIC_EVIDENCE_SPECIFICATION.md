# HKEI OS v2 — Compositional Semantic Evidence Specification

## 1. Purpose

Compositional Semantic Evidence is the deterministic layer that answers:

> How do multiple contextual evidence items relate to each other inside the same sentence, headline, lead, or local context?

The layer derives relationships rather than merely detecting terms. It improves HKEI's ability to distinguish:

- authority from subject;
- actor from subject;
- method or tool from subject;
- action from object;
- event from domain;
- institution from domain;
- recommended action from ordinary reporting; and
- primary from secondary domain evidence.

## 2. Architectural Position

The target architecture is:

Source Intake
→ Risk Assessment
→ Fact Extraction
→ Contextual Editorial Evidence
→ Compositional Semantic Evidence
→ Topic Classification
→ Editorial Format Classification
→ Reader Intent
→ Strategy
→ Planning
→ Prompting
→ Generation
→ Parsing
→ Evaluation

Contextual Evidence detects local evidence items. Compositional Semantic Evidence relates those items. Classifiers consume the resulting semantic compositions. This layer does not itself make final Topic, Format, or Reader Intent decisions.

## 3. Core Principle

Meaning must not be inferred from isolated evidence items. It emerges from combinations such as:

AUTHORITY + ACTION + OBJECT + DOMAIN-BEARING SUBJECT

For example:

وزارة الصحة + تقدم + فحوصات طبية

must support HEALTH as the primary domain even though the authority is governmental.

## 4. Semantic Components

The layer uses the following conceptual components:

- AUTHORITY
- ACTOR
- PRIMARY_SUBJECT
- SECONDARY_SUBJECT
- ACTION
- OBJECT
- METHOD
- TOOL
- DOMAIN
- EVENT
- INDICATOR
- OUTCOME
- AFFECTED_AUDIENCE
- RECOMMENDED_ACTION
- REQUIREMENT
- DEADLINE
- LOCATION
- ATTRIBUTION
- CLAIM
- PREDICTION
- UNCERTAINTY
- INTERPRETATION
- CONSEQUENCE

These are conceptual components only. This specification does not define final Python enums.

## 5. Relationship Types

The layer should support these reusable relationship types:

- AUTHORITY_ACTS_ON_SUBJECT
- ACTOR_PERFORMS_ACTION
- ACTION_TARGETS_OBJECT
- METHOD_APPLIED_TO_SUBJECT
- TOOL_USED_FOR_TASK
- EVENT_HAS_OUTCOME
- INDICATOR_DESCRIBES_DOMAIN
- SUBJECT_BELONGS_TO_DOMAIN
- INSTITUTION_BELONGS_TO_DOMAIN
- RECOMMENDATION_TARGETS_AUDIENCE
- REQUIREMENT_APPLIES_TO_AUDIENCE
- ACTION_HAS_DEADLINE
- CLAIM_ATTRIBUTED_TO_AUTHORITY
- PREDICTION_ABOUT_EVENT
- INTERPRETATION_OF_INDICATOR
- CONSEQUENCE_OF_EVENT

## 6. Authority vs Subject

This distinction is mandatory.

Example:

> أعلنت وزارة الصحة تقديم الفحوصات الطبية.

Composition:

- AUTHORITY: وزارة الصحة
- ACTION: تقديم
- OBJECT: الفحوصات الطبية
- PRIMARY_SUBJECT: medical screening
- DOMAIN: HEALTH

The authority type must not automatically determine the article's primary topic.

## 7. Actor vs Subject

Example:

> شركات السيارات الكهربائية تتجه لتقنيات البطاريات الصلبة.

Composition:

- ACTOR: companies
- PRIMARY_SUBJECT: battery technology
- DOMAIN: TECHNOLOGY
- Secondary domain: BUSINESS

Actor type is contextual evidence, not a final domain decision.

## 8. Method / Tool vs Subject

Example:

> الذكاء الاصطناعي ينجح في تشخيص أورام السرطان.

Composition:

- METHOD: artificial intelligence
- PRIMARY_SUBJECT: cancer diagnosis
- DOMAIN: HEALTH
- Secondary domain: TECHNOLOGY

A tool or method must not outrank the domain-bearing object or subject when the article is primarily about the application outcome.

## 9. Domain-Bearing Objects

Some objects carry strong domain meaning. Conceptual examples include:

- medical screening → HEALTH
- unemployment rate → ECONOMY
- university ranking → EDUCATION
- flooding → WEATHER
- ransomware attack → TECHNOLOGY
- international negotiations → POLITICS / WORLD

The implementation should identify reusable semantic classes rather than hard-code benchmark phrases.

## 10. Event-Domain Composition

Example composition:

heavy monsoon rain + flooding + landslides + evacuation

- EVENT: flooding
- CONDITION: weather event
- DOMAIN: WEATHER

The domain may be inferred from an event class even when explicit category vocabulary is absent.

## 11. Indicator-Domain Composition

Example composition:

unemployment rate + labor market + economic growth

- INDICATOR: unemployment
- DOMAIN: ECONOMY

Indicator relationships are stronger than generic institutional actors.

## 12. Institution-Domain Composition

Institutions may imply a domain only when paired with domain-bearing subject matter:

- Ministry of Health + medical services → HEALTH
- Ministry of Higher Education + universities → EDUCATION
- Transport authority + public infrastructure project → GOVERNMENT

An institution alone must remain weak evidence.

## 13. Recommended-Action Structure

Example:

> حذر خبراء الأمن السيبراني الشركات بضرورة تحديث برامج الحماية.

Composition:

- AUTHORITY / ACTOR: experts
- AFFECTED_AUDIENCE: companies
- RECOMMENDED_ACTION: update protection
- DOMAIN: TECHNOLOGY
- Format support: SERVICE
- Intent support: KNOW_ACTION

Advice or action directed at an audience must be distinguished from ordinary reporting.

## 14. Negative Format Evidence

The composition layer should later produce negative evidence when a format lacks structural support.

Example:

> وزارة التعليم أعلنت تقدم الجامعات في التصنيف.

This contains no REQUIREMENT, DEADLINE, PROCEDURE, ELIGIBILITY, or READER_ACTION. GUIDE should therefore receive negative evidence. This prevents ordinary institutional news from becoming a false GUIDE classification.

## 15. Primary vs Secondary Domain

The layer should expose PRIMARY_DOMAIN_CANDIDATE and SECONDARY_DOMAIN_CANDIDATE without making the final topic decision.

For AI cancer diagnosis:

- Primary: HEALTH
- Secondary: TECHNOLOGY

For a technology-company merger:

- Primary: BUSINESS
- Secondary: TECHNOLOGY

## 16. Candidate Domain Competition

When multiple domains are present, the layer must evaluate composition rather than raw term count. Relevant factors may include:

- primary subject;
- action object;
- headline focus;
- lead focus;
- event class;
- method or tool role;
- actor role;
- outcome; and
- repeated domain-bearing objects.

The layer must not define arbitrary keyword precedence.

## 17. Structural Position

Headline and lead relationships should carry more weight than body-only compositions. Every composition must preserve provenance rather than collapsing all evidence into document-wide counts.

## 18. Locality

Compositions should be formed only from evidence within:

- the same headline;
- the same sentence;
- the same lead; or
- explicitly bounded nearby context.

Unrelated evidence from distant paragraphs must not be combined.

## 19. Semantic Strength

Conceptual strengths are STRONG, MEDIUM, and WEAK. Strength may depend on:

- relationship completeness;
- structural position;
- corroboration;
- semantic specificity; and
- conflicting compositions.

## 20. Suppression / Negative Evidence

The layer must support both `supports` and `suppresses`.

For example, METHOD=AI with PRIMARY_SUBJECT=cancer diagnosis may:

- support TOPIC_HEALTH;
- support TOPIC_TECHNOLOGY_SECONDARY; and
- suppress TOPIC_TECHNOLOGY_PRIMARY.

Final label strings are not defined by this specification.

## 21. Relationship Provenance

Every future composition must preserve:

- source section;
- sentence index;
- evidence item references;
- relationship type;
- subject span;
- object span;
- strength;
- reason code;
- supports; and
- suppresses.

Full document bodies must not be stored inside each relationship.

## 22. Determinism

The MVP must be deterministic, reproducible, standard-library compatible, offline, and provider-independent. Identical evidence input must produce identical semantic compositions.

## 23. Batch 03 Architecture-Learning Examples

The following cases are architectural examples only:

- 021: Authority + public transport infrastructure → GOVERNMENT.
- 022: Economic institution + non-oil growth + investment → ECONOMY.
- 023: US + China + negotiations + tariffs → POLITICS primary and ECONOMY secondary.
- 024: AI as METHOD and cancer diagnosis as PRIMARY_SUBJECT → HEALTH primary and TECHNOLOGY secondary.
- 025: Health ministry as AUTHORITY and medical screenings as PRIMARY_SUBJECT → HEALTH.
- 026: Cybersecurity threat + directed protection action → TECHNOLOGY with SERVICE / KNOW_ACTION support.
- 028: Heavy rain + flooding + landslides → WEATHER.
- 029: Higher-education ministry as AUTHORITY and universities and rankings as PRIMARY_SUBJECT → EDUCATION with negative GUIDE evidence.

These cases must not be implemented as hard-coded exceptions.

## 24. Relationship to Contextual Evidence

Contextual Evidence remains responsible for token matching, phrase matching, contextual local evidence, roles, and provenance. Compositional Semantic Evidence consumes those items and derives relationships between them. It should not duplicate lexical matching where avoidable.

## 25. Relationship to Topic

A future TopicClassifier should prefer compositional primary-domain evidence over generic authority, generic actor, weak lexical signals, and legacy content type.

## 26. Relationship to Format

A future FormatClassifier may consume:

- RECOMMENDED_ACTION;
- REQUIREMENT;
- DEADLINE;
- negative guide evidence; and
- interpretation + prediction + consequence.

## 27. Relationship to Reader Intent

A future ReaderIntentClassifier may consume directed action, requirements, result structure, analysis structure, and explanation structure.

## 28. Relationship to Risk

Future risk logic may consume claim relationships, medical domain, legal allegations, security threats, financial advice, and biosecurity context. Semantic domain alone must not define risk.

## 29. Future AI Adjudication

If compositional evidence remains ambiguous, a future AI semantic adjudicator may receive:

- headline;
- lead;
- contextual evidence;
- compositional relationships; and
- candidate domains.

It may return structured classification. The deterministic layer should minimize unnecessary AI calls. No AI is implemented here.

## 30. Non-Goals

- No final topic
- No final format
- No final reader intent
- No LLM
- No embeddings
- No external NLP libraries
- No dependency parser
- No web verification
- No article rewriting
- No benchmark-specific rules
- No full semantic graph in the MVP

## 31. MVP Scope

The first implementation should support compositions for:

- authority vs subject;
- actor vs subject;
- method or tool vs subject;
- action-object;
- institution-domain;
- event-domain;
- indicator-domain;
- recommended-action structure;
- negative format evidence; and
- primary vs secondary domain candidates.

## 32. Acceptance Criteria

The future implementation must:

- consume ContextualEvidence;
- derive relationships between evidence items;
- preserve provenance;
- distinguish authority from subject;
- distinguish actor from subject;
- distinguish method or tool from subject;
- identify domain-bearing objects;
- derive event-domain evidence;
- derive indicator-domain evidence;
- support recommended-action structure;
- support negative format evidence;
- expose primary and secondary domain candidates;
- make no final classification;
- remain deterministic;
- remain reusable across Topic, Format, Intent, and Risk; and
- avoid benchmark-specific exceptions.

## 33. Current Baselines

- Batch 01 Topic: 100%
- Batch 02 Context-Aware Full: 100%
- Batch 03 Context-Aware: Topic 20%, Format 80%, Intent 80%, Full 20%

Batch 03 exposed missing semantic composition and is now a development diagnostic set, not an unseen validation set.
