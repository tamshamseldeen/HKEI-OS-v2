# HKEI OS v2 — Contextual Editorial Evidence Specification

## 1. Purpose

Contextual Editorial Evidence is an intermediate deterministic analysis layer between raw or extracted source material and editorial classifiers.

It answers:

> “What does this text segment mean editorially in its local context?”

The layer moves HKEI beyond isolated keyword scoring without becoming an LLM-based semantic classifier.

## 2. Architectural Position

The target architecture is:

Source Intake
→ Risk Assessment
→ Fact Extraction
→ Contextual Editorial Evidence
→ Topic Classification
→ Editorial Format Classification
→ Reader Intent
→ Editorial Strategy
→ Planning
→ Prompt Building
→ Generation
→ Parsing
→ Evaluation

- Contextual evidence does not itself choose Topic.
- It does not itself choose Editorial Format.
- It does not itself choose Reader Intent.
- It produces reusable evidence consumed by downstream classifiers.
- Existing classifiers remain unchanged during the first implementation phase.

## 3. Core Principle

Do not treat keyword presence as equivalent to editorial meaning.

Meaning must consider:

- token boundaries
- phrase boundaries
- local sentence context
- headline position
- lead position
- grammatical or editorial role where deterministically identifiable
- neighboring terms
- repeated concepts
- competing evidence
- source structure

## 4. Evidence Hierarchy

The evidence levels are:

- `TOKEN`
- `PHRASE`
- `CONTEXT`
- `STRUCTURAL`

Their strength order is:

`STRUCTURAL` > `CONTEXT` > `PHRASE` > `TOKEN`

A lower-level signal must not automatically override stronger contextual evidence.

## 5. TOKEN Evidence

A `TOKEN` is one complete lexical token.

Examples:

- وزارة
- كوكب
- مباراة
- غرامة
- طلاب

Rules:

- Token boundaries are required.
- Substring matches are prohibited.
- Tokens may be weak or strong.
- Generic tokens should usually be weak evidence.

For example, هدف must match سجل هدف, but not تستهدف.

## 6. PHRASE Evidence

A `PHRASE` is a meaningful multi-token expression.

Examples:

- علماء الفلك
- البنك المركزي
- أسعار الفائدة
- معرض الكتاب
- الفاتورة الإلكترونية
- الأصول الرقمية
- أشباه الموصلات
- مصلحة الضرائب
- موجة حر
- القنوات الناقلة

Phrase evidence is stronger than isolated token evidence.

## 7. CONTEXT Evidence

`CONTEXT` combines related evidence within a local sentence or bounded text window.

Example:

> أعلن فريق دولي من علماء الفلك اكتشاف كوكب جديد.

Evidence:

- فريق → weak generic group reference
- علماء الفلك → strong `SCIENCE` phrase
- اكتشاف كوكب → strong `SCIENCE` contextual evidence

Contextual interpretation: the word فريق must not create `SPORTS` evidence in this context.

## 8. STRUCTURAL Evidence

`STRUCTURAL` evidence uses the role of information inside the article.

Supported MVP structural positions:

- `HEADLINE`
- `LEAD`
- `BODY`
- `METADATA`
- `USER_INSTRUCTION`

Default evidence importance:

`USER_INSTRUCTION`, when editorially applicable, > `HEADLINE` > `LEAD` > `BODY` > `METADATA`.

Metadata remains supporting evidence and must not replace textual understanding.

## 9. Headline Analysis

The headline should be analyzed separately from the body.

Extract deterministic evidence for:

- primary subject
- primary action or event
- result
- requirement
- deadline
- warning
- question or explanation framing
- analysis framing
- service framing

The MVP does not implement full syntactic parsing.

## 10. Lead Analysis

The lead is the first meaningful sentence or first meaningful paragraph of the body.

The lead should strongly influence:

- primary subject
- event type
- authority or source
- affected audience
- immediate reader need

Headline and lead agreement is strong evidence.

## 11. Local Context Windows

Context must operate on bounded units.

MVP units are:

- sentence
- headline
- lead

Unrestricted whole-document keyword co-occurrence is not contextual evidence. Two terms appearing in unrelated paragraphs must not automatically form one contextual signal.

## 12. Evidence Roles

Reusable editorial roles are:

- `SUBJECT`
- `ACTOR`
- `ACTION`
- `OBJECT`
- `AUTHORITY`
- `AFFECTED_AUDIENCE`
- `REQUIREMENT`
- `DEADLINE`
- `RESULT`
- `CONSEQUENCE`
- `WARNING`
- `NUMBER`
- `DATE`
- `LOCATION`
- `ATTRIBUTION`
- `CLAIM`
- `PREDICTION`
- `UNCERTAINTY`
- `EXPLANATION`
- `COMPARISON`
- `BACKGROUND`
- `INTERPRETATION`

The first implementation does not need to detect every role. These roles define the target model.

## 13. Actor vs Primary Subject

This distinction is mandatory.

Example:

> شركات السيارات الكهربائية تتجه لتقنيات البطاريات الصلبة.

- Actor: شركات السيارات الكهربائية
- Primary development: تقنيات البطاريات الصلبة
- Possible primary topic: `TECHNOLOGY`
- `BUSINESS` may remain secondary evidence.

The actor's organizational type must not automatically determine the article topic.

## 14. Authority vs Primary Subject

Example:

> أعلنت وزارة السياحة ارتفاع الإيرادات السياحية بنسبة 18%.

- Authority: وزارة السياحة
- Primary subject: tourism revenue growth
- Possible topic: `ECONOMY`

A government authority must not automatically make the topic `GOVERNMENT`.

## 15. Generic-Term Suppression

Weak generic terms may be suppressed when stronger local context assigns them a different role.

Examples:

- فريق دولي من علماء الفلك: فريق is a generic group noun, so suppress the `SPORTS` interpretation.
- ممثلو عدد من الدول: ممثلو means representatives and must not trigger `ENTERTAINMENT` from ممثل.
- تستهدف الخطوة: this must not trigger `SPORTS` from هدف.

## 16. Competing Evidence

The layer must preserve competing evidence rather than prematurely discard it.

For a technology story about companies and investment, possible evidence may be:

- `TECHNOLOGY`: strong
- `BUSINESS`: medium
- `ECONOMY`: weak

The downstream classifier decides the primary topic. Contextual evidence exposes the competition.

## 17. Primary and Secondary Evidence

Evidence may later support a primary candidate and secondary candidates, but this layer must not return a final topic.

Conceptual example:

- `TECHNOLOGY`: strong contextual support
- `BUSINESS`: supporting contextual evidence

This specification does not define a multi-topic production model yet.

## 18. Evidence Strength

Evidence strengths are:

- `STRONG`
- `MEDIUM`
- `WEAK`

Strength must derive from deterministic factors such as:

- evidence level
- structural position
- contextual agreement
- corroborating phrases
- repeated independent evidence
- suppression conflicts

Strength must not use arbitrary confidence generated by AI.

## 19. Positive Evidence

Positive evidence supports an interpretation.

For example:

علماء الفلك + كوكب + مرصد → strong science evidence.

## 20. Negative / Suppression Evidence

The system must support evidence that weakens an otherwise possible interpretation.

For example, فريق may normally weakly support `SPORTS`, but فريق دولي من علماء الفلك produces suppression evidence against the `SPORTS` interpretation.

This concept is required.

## 21. Topic Support

A future TopicClassifier may consume contextual evidence.

Examples:

- `SCIENCE`: علماء الفلك + اكتشاف كوكب
- `CULTURE`: معرض الكتاب + هيئة الكتاب
- `ECONOMY`: البطالة + سوق العمل
- `GOVERNMENT`: مصلحة الضرائب + required registration
- `TECHNOLOGY`: أشباه الموصلات + صناعة الرقائق

The TopicClassifier remains responsible for final classification.

## 22. Editorial Format Support

Contextual evidence must also support format.

Example:

> دعت مصلحة الضرائب الشركات للتسجيل قبل نهاية الشهر.

Evidence roles:

- `AUTHORITY`
- `AFFECTED_AUDIENCE`
- `REQUIREMENT`
- `DEADLINE`

This strongly supports `SERVICE`.

Another example:

> يشير تحليل إلى أن التقنية قد تخفض الأسعار خلال السنوات المقبلة.

Evidence roles:

- `INTERPRETATION`
- `PREDICTION`
- `CONSEQUENCE`

This may support `ANALYSIS`. The Editorial Format Classifier makes the final decision.

## 23. Reader Intent Support

Examples:

- `REQUIREMENT` + `DEADLINE` → supports `KNOW_ACTION` or `VERIFY_REQUIREMENTS`
- `RESULT` → supports `FIND_RESULT`
- `EXPLANATION` → supports `UNDERSTAND_EVENT`
- `INTERPRETATION` + `CONSEQUENCE` → supports `UNDERSTAND_IMPACT`

The ReaderIntentClassifier remains authoritative.

## 24. Risk Support

Contextual evidence may support risk analysis, including:

- medical recommendation
- legal allegation
- investment recommendation
- security threat
- criminal accusation

Topic alone must not determine risk.

## 25. Claim and Attribution Foundation

The contextual layer must be designed so it can later support:

- `CONFIRMED_FACT`
- `ATTRIBUTED_CLAIM`
- `UNVERIFIED_CLAIM`
- `PREDICTION`
- `INFERENCE`
- `UNKNOWN`

Example:

> قال مسؤول إن هجومًا قد يقع.

It must preserve:

- `ATTRIBUTION`: مسؤول
- `CLAIM`: هجوم
- `UNCERTAINTY`: قد

It must not become: هجوم سيقع.

Claim verification is not implemented by this specification.

## 26. Sentence Segmentation

The MVP should support deterministic sentence segmentation for Arabic and Latin punctuation.

Possible boundaries:

- `.`
- `؟`
- `!`
- `؛`
- newline paragraph boundaries

Segmentation must preserve original text. It must not rewrite source content.

## 27. Evidence Provenance

Every contextual evidence item must eventually preserve provenance.

Conceptual fields:

- `source_section`
- `sentence_index`
- `matched_text`
- `evidence_level`
- `role`
- `strength`
- `reason_code`

Final Python dataclasses are not defined yet.

## 28. Deterministic Requirement

The MVP contextual layer must be:

- deterministic
- reproducible
- standard-library compatible
- offline
- provider-independent
- network-independent

Identical input must produce identical evidence.

## 29. AI Relationship

Contextual Editorial Evidence is not intended to eliminate AI.

The target future hybrid architecture is:

Deterministic contextual evidence → downstream deterministic classifier.

If confidence is high and conflict is low, accept the deterministic result. If confidence is low or evidence conflict is material, allow future AI semantic adjudication.

AI adjudication is outside the MVP.

## 30. AI-Agnostic Principle

Future semantic adjudication must not depend on one provider. Potential providers may include any supported LLM implementation.

Provider choice must remain outside editorial-domain models.

## 31. Benchmark Learning Examples

### Example A

> تستهدف هذه الخطوة حماية المستثمرين

- Incorrect lexical behavior: هدف → `SPORTS`
- Correct contextual behavior: `ACTION` / purpose context; no `SPORTS` evidence

### Example B

> أعلن فريق دولي من علماء الفلك اكتشاف كوكب

- Incorrect lexical behavior: فريق → `SPORTS`
- Correct contextual behavior: `SUBJECT` / `ACTOR` is a scientific research team; `SCIENCE` contextual evidence dominates

### Example C

> أبدى ممثلو عدد من الدول القلق

- Incorrect lexical behavior: ممثل → `ENTERTAINMENT`
- Correct contextual behavior: `ACTOR` is country representatives; no `ENTERTAINMENT` evidence

### Example D

> دعت مصلحة الضرائب الشركات للتسجيل قبل نهاية الشهر

Contextual roles:

- `AUTHORITY`
- `AFFECTED_AUDIENCE`
- `REQUIREMENT`
- `DEADLINE`

Potential downstream format support: `SERVICE`.

### Example E

> شركات السيارات الكهربائية تتجه لتقنيات البطاريات الصلبة لتقليل التكاليف

Contextual evidence:

- Actor: companies
- Primary development: battery technology
- Consequence: cost reduction

Topic support:

- `TECHNOLOGY`: strong
- `BUSINESS`: secondary

Potential format support is `ANALYSIS` only when interpretation evidence is sufficiently supported.

## 32. Relationship to Existing DeterministicTopicClassifier

- HKEI-067 token-boundary improvements remain valid.
- Current vocabulary remains a lexical evidence source.
- Contextual evidence will complement rather than immediately replace it.
- Legacy ContentType contamination must remain removed.
- Topic migration must remain backward-compatible.
- Existing benchmark behavior must be preserved unless a benchmark expectation is formally adjudicated.

## 33. Relationship to Batch 02

The current baseline is:

- Batch 01 Topic Accuracy: 100.00%
- Batch 02 Topic Accuracy: 90.00%
- Batch 02 Editorial Format Accuracy: 80.00%
- Batch 02 Reader Intent Accuracy: 80.00%
- Batch 02 Full Case Accuracy: 70.00%

These values are baseline measurements, not implementation targets to hard-code.

## 34. Non-Goals

- No LLM calls
- No semantic embeddings
- No external NLP libraries
- No web verification
- No final topic decision
- No final format decision
- No final reader-intent decision
- No article rewriting
- No claim verification
- No benchmark-specific exceptions
- No full Arabic dependency parser
- No sentiment analysis

## 35. MVP Implementation Scope

The first implementation should focus on:

- sentence segmentation
- token-aware matching
- phrase matching
- headline evidence
- lead evidence
- body evidence
- contextual windows
- weak-signal suppression
- contextual role patterns
- evidence strength
- evidence provenance

Initial reusable roles should prioritize:

- `SUBJECT`
- `ACTOR`
- `ACTION`
- `AUTHORITY`
- `AFFECTED_AUDIENCE`
- `REQUIREMENT`
- `DEADLINE`
- `RESULT`
- `CONSEQUENCE`
- `WARNING`
- `ATTRIBUTION`
- `CLAIM`
- `PREDICTION`
- `UNCERTAINTY`
- `INTERPRETATION`

## 36. Acceptance Criteria

The future implementation must:

- analyze context rather than isolated substring presence
- preserve sentence-level provenance
- distinguish weak generic terms from contextual meaning
- support phrase evidence
- support suppression evidence
- distinguish actor from primary subject where deterministic patterns permit
- distinguish authority from primary subject
- expose competing evidence
- support Topic without selecting Topic
- support Format without selecting Format
- support Reader Intent without selecting Reader Intent
- provide a foundation for future Evidence Modeling
- make no AI or network calls
- remain deterministic
- remain reusable across editorial layers
- avoid benchmark-specific rules
