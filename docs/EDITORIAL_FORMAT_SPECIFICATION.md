# HKEI OS v2 — Editorial Format Specification

## 1. Purpose

The Editorial Format layer answers:

“How should this material be structured and presented editorially?”

Editorial Format is separate from:

- Topic: what the material is about
- Reader Intent: what the reader needs
- Risk: how cautiously the material must be handled
- Strategy: the detailed drafting treatment
- Publication Decision: whether the article may be published

This layer receives analyzed editorial data and assigns exactly one primary
editorial format in the MVP.

## 2. Architectural Position

The target editorial analysis model is:

```text
Source Intake
→ Source and Risk Assessment
→ Fact Extraction
→ Topic Classification
→ Editorial Format Classification
→ Reader Intent
→ Editorial Strategy
→ Article Planning
→ Prompt Building
→ Generation
→ Parsing
→ Evaluation
```

- The current `ContentTypeClassification` remains unchanged during migration.
- `EditorialFormatClassification` will initially be added alongside the
  existing classification.
- Migration must be incremental and backward-compatible.
- Existing workflow behavior must not be removed until the new model is
  validated.

## 3. Input

The future layer may receive:

- `NormalizedSource`
- `SourceRiskAssessment`
- `ExtractedFacts`
- existing `ContentTypeClassification`
- optional user instruction
- optional source metadata

Python signatures are not defined yet.

## 4. Output

Define one future object named `EditorialFormatClassification` with these
fields:

- `editorial_format`
- `confidence`
- `reason_codes`
- `supporting_signals`
- `warnings`

Python types are not defined yet.

## 5. Supported MVP Editorial Formats

Use only these exact values:

- `BREAKING`
- `STANDARD_NEWS`
- `SERVICE`
- `GUIDE`
- `EXPLAINER`
- `FEATURE`
- `FACT_CHECK`
- `ANALYSIS`
- `INTERVIEW`
- `PROFILE`
- `RESULT_REPORT`
- `TREND_UPDATE`

Do not add:

- Opinion
- Live Blog
- Review
- Investigative Report

These remain outside the first implementation.

## 6. BREAKING

Use when:

- immediacy is the primary editorial value
- the event is new or developing
- available details may be limited
- the reader needs the latest confirmed fact quickly

Typical structure:

- result or event first
- minimal context
- short article
- no padding
- no unsupported background

Breaking is not a topic.

Examples may include:

- sports result just announced
- emergency update
- official decision just issued
- developing public event

Do not classify material as `BREAKING` merely because it is short.

## 7. STANDARD_NEWS

Use when:

- the primary purpose is reporting what happened
- the source supports a conventional news structure
- no more specialized format is strongly justified

Typical structure:

- lead
- core facts
- key details
- attribution
- concise closing

This is the safe fallback format.

## 8. SERVICE

Use when:

- the reader needs practical information affecting action or daily life
- penalties, warnings, interruptions, procedures, deadlines, or public
  instructions are central
- the article should answer what the reader should know or do

Examples:

- traffic fines
- road closures
- service interruptions
- consumer alerts
- public safety instructions
- application deadlines

Typical structure may include:

- what changed
- who is affected
- amounts or dates
- required action
- official attribution

## 9. GUIDE

Use when:

- the article is designed as a reference the reader can consult
- dates, channels, requirements, steps, schedules, or structured answers are
  central
- the content may remain useful beyond the immediate publication moment

Examples:

- match date and broadcasting channels
- application requirements
- how to use an official service
- event schedule
- eligibility and required documents

Typical structures may include:

- direct answer
- sections
- table
- FAQ
- requirements
- deadlines

Guide differs from Service:

- Service focuses on a current practical development.
- Guide organizes reference information for repeated reader use.

## 10. EXPLAINER

Use when:

- understanding is more important than immediacy
- the article explains how, why, causes, consequences, or meaning
- the reader requires context to understand the subject

Typical structure:

- core event or question
- explanation
- causes or mechanisms
- impact
- supplied context

Do not classify a source as `EXPLAINER` only because it is long.

## 11. FEATURE

Use when:

- the article uses narrative, context, history, personalities, or unusual
  details
- the purpose is deeper reader engagement rather than a fast update
- multiple information blocks build one broader story

Examples:

- profile of a club awaiting a famous player
- historical story behind a sporting institution
- cultural or human-interest story
- narrative treatment of a current event

Typical structure may include:

- narrative opening
- thematic sections
- historical context
- personalities
- unusual details
- forward-looking questions supported by the source

Feature must not invent atmosphere, motives, or emotional conclusions.

## 12. FACT_CHECK

Use when:

- one identifiable claim is being assessed
- evidence and verification status are central
- the article requires a clear distinction between claim, evidence, and
  conclusion

Required editorial elements:

- identifiable claim
- source of claim
- supplied evidence
- verification limitations
- cautious conclusion

Do not classify as `FACT_CHECK` without explicit verification context.

## 13. ANALYSIS

Use when:

- the article interprets significance, consequences, patterns, or likely
  implications
- interpretation is supported by sufficient evidence
- the reader needs more than explanation of the event itself

Analysis requires:

- strong source depth
- clear distinction between facts and interpretation
- attribution where relevant
- no unsupported prediction

Analysis must not be selected from thin source material.

## 14. INTERVIEW

Use when:

- questions and answers with an identifiable person are central
- direct responses are available
- attribution is explicit

Typical structures:

- introduction
- interviewer questions
- exact or clearly attributed responses
- brief contextual sections

Do not reconstruct an interview from indirect quotations.

## 15. PROFILE

Use when:

- one person, organization, team, product, or institution is the main subject
- identity, history, achievements, characteristics, or significance are central

Typical structures:

- identifying introduction
- background
- milestones
- current relevance
- supplied facts and quotations

Do not invent personality traits, motives, or reputation claims.

## 16. RESULT_REPORT

Use when:

- the confirmed outcome is the primary reader need
- score, winner, verdict, final decision, or completed result is central

Common examples:

- sports match result
- election result
- court ruling
- financial result
- award result

Typical structure:

- result first
- essential details
- supported context
- quotations when available

Do not invent missing result details.

## 17. TREND_UPDATE

Use when:

- the source originates mainly from social-media circulation or viral discussion
- verification is incomplete
- the article must report what is circulating without presenting it as confirmed
  fact

Typical structure:

- what is circulating
- who published or shared it
- what is confirmed
- what remains unverified
- official response when supplied

Virality must never be treated as verification.

## 18. Topic Independence

The same topic may use different editorial formats.

Examples:

- Sports + `BREAKING`
- Sports + `RESULT_REPORT`
- Sports + `GUIDE`
- Sports + `FEATURE`
- Sports + `ANALYSIS`
- Sports + `PROFILE`
- Government + `SERVICE`
- Government + `GUIDE`
- Government + `STANDARD_NEWS`
- Government + `EXPLAINER`
- Technology + `STANDARD_NEWS`
- Technology + `GUIDE`
- Technology + `EXPLAINER`
- Technology + `ANALYSIS`

Topic must never determine format alone.

## 19. Reader Intent Relationship

Common but non-mandatory relationships are:

- `GET_UPDATE` → `BREAKING` or `STANDARD_NEWS`
- `UNDERSTAND_EVENT` → `EXPLAINER` or `FEATURE`
- `KNOW_ACTION` → `SERVICE` or `GUIDE`
- `CHECK_CLAIM` → `FACT_CHECK` or `TREND_UPDATE`
- `COMPARE_OPTIONS` → `GUIDE` or `ANALYSIS`
- `FOLLOW_DEVELOPMENT` → `BREAKING` or `STANDARD_NEWS`
- `FIND_RESULT` → `RESULT_REPORT`
- `UNDERSTAND_IMPACT` → `EXPLAINER` or `ANALYSIS`
- `GET_GUIDANCE` → `SERVICE` or `GUIDE`
- `VERIFY_REQUIREMENTS` → `GUIDE` or `SERVICE`

Reader intent supports classification but does not determine it alone.

## 20. Risk Relationship

- Risk and format are separate dimensions.
- A medical article may be `GUIDE`, `SERVICE`, `EXPLAINER`, or `STANDARD_NEWS`.
- A legal article may be `STANDARD_NEWS`, `SERVICE`, `GUIDE`, or `ANALYSIS`.
- High risk may restrict structure and wording.
- High risk must not automatically define format.
- `CRITICAL` risk may prevent generation regardless of format.

## 21. Deterministic Signals

Possible MVP signals include:

- explicit user instruction
- source category
- title terminology
- body structure
- question-and-answer patterns
- number of headings or thematic blocks
- procedural terminology
- deadline terminology
- match or result terminology
- historical and narrative terminology
- claim-verification terminology
- social-platform metadata
- source depth
- quotation structure
- number of distinct facts, dates, values, and sections

Keywords alone are insufficient.

## 22. Explicit User Instruction

Explicit user instruction has highest precedence when safe and supported.

Examples:

- “اكتب خبرًا عاجلًا”
- “اكتب دليلًا”
- “اكتب تقريرًا تحليليًا”
- “أعده في صورة أسئلة وأجوبة”
- “اكتب بروفايل”
- “اكتب تقرير نتيجة”

Rules:

- User instruction may influence format.
- User instruction cannot force unsupported format.
- Thin material cannot become `ANALYSIS` or `FEATURE` merely by request.
- Missing interview responses cannot become `INTERVIEW`.
- Missing evidence cannot become `FACT_CHECK`.
- Unsupported requests must produce warnings.

## 23. Precedence Rules

Use this default precedence:

1. Explicit supported user instruction
2. `FACT_CHECK`
3. `INTERVIEW`
4. `RESULT_REPORT`
5. `GUIDE`
6. `SERVICE`
7. `FEATURE`
8. `PROFILE`
9. `ANALYSIS`
10. `TREND_UPDATE`
11. `BREAKING`
12. `EXPLAINER`
13. `STANDARD_NEWS`

- Precedence resolves competing supported matches.
- Stronger structural evidence may outweigh a weak keyword match.
- Unsupported high-precedence formats must fall through safely.
- `STANDARD_NEWS` is the fallback.

## 24. Confidence

Use these exact values:

- `HIGH`
- `MEDIUM`
- `LOW`

Definitions:

`HIGH`:
Strong and consistent structural or explicit signals support one format.

`MEDIUM`:
One format is most likely, but overlap exists.

`LOW`:
The material is insufficient, contradictory, or weakly structured.

`LOW` confidence must produce a warning.

## 25. Warning Codes

- `LOW_EDITORIAL_FORMAT_CONFIDENCE`
- `CONFLICTING_EDITORIAL_FORMAT_SIGNALS`
- `UNSUPPORTED_FORMAT_REQUEST`
- `SOURCE_TOO_THIN_FOR_FEATURE`
- `SOURCE_TOO_THIN_FOR_ANALYSIS`
- `FACT_CHECK_EVIDENCE_MISSING`
- `INTERVIEW_STRUCTURE_MISSING`
- `GUIDE_STRUCTURE_INSUFFICIENT`
- `TREND_VERIFICATION_INCOMPLETE`
- `FORMAT_MIGRATION_COMPATIBILITY_WARNING`

## 26. Relationship to Existing ContentTypeClassification

The temporary migration approach is:

- Existing `ContentTypeClassification` remains the authoritative classification
  for current workflows.
- `EditorialFormatClassification` will be introduced as an additional result.
- The first implementation may use existing content type as one supporting
  signal.
- Strategy and planning must not be migrated immediately.
- Migration occurs only after benchmark validation.
- No existing enum or workflow is removed in the first phase.

Possible future mapping examples:

- `BREAKING_NEWS` → `BREAKING`
- `STANDARD_NEWS` → `STANDARD_NEWS`
- `NEWS_REWRITE` → `STANDARD_NEWS` unless explicit format differs
- `PUBLIC_SERVICE_NEWS` → `SERVICE`
- `GOVERNMENT_SERVICE_CONTENT` → `GUIDE` or `SERVICE` depending on structure
- `EXPLAINER` → `EXPLAINER`
- `FACT_CHECK` → `FACT_CHECK`
- `HEALTH_CONTENT` → topic-like classification requiring separate format
  inference
- `LEGAL_FINANCIAL_HIGH_RISK_CONTENT` → risk/topic-like classification requiring
  separate format inference
- `SPORTS_NEWS` → topic-like classification requiring separate format inference
- `TECHNOLOGY_NEWS` → topic-like classification requiring separate format
  inference
- `ECONOMY_NEWS` → topic-like classification requiring separate format inference
- `TRENDING_SOCIAL_CLAIM` → `TREND_UPDATE`

This mapping is transitional and not the final topic model.

## 27. Benchmark Examples

Example 1:

Subject:
Sports

Material:
A match has just ended with a confirmed score.

Editorial Format:
`RESULT_REPORT` or `BREAKING` depending on immediacy.

---

Example 2:

Subject:
Sports

Material:
Match date, broadcasting channels, stadium, and viewing methods.

Editorial Format:
`GUIDE`

---

Example 3:

Subject:
Sports

Material:
History, identity, stadium, personalities, and future expectations surrounding a
club.

Editorial Format:
`FEATURE`

---

Example 4:

Subject:
Government / Public Safety

Material:
Traffic violation, fine amount, risks, and required behavior.

Editorial Format:
`SERVICE`

## 28. Non-Goals

- No topic classification implementation
- No strategy migration
- No planning migration
- No prompt migration
- No workflow removal
- No AI classification
- No web verification
- No publisher-style imitation
- No multi-format output
- No automatic content rewriting
- No Opinion format
- No Live Blog format
- No Review format
- No Investigative format

## 29. MVP Scope

For the first implementation:

- Return exactly one primary editorial format.
- Use deterministic signals only.
- Use existing workflow outputs as supporting evidence.
- Keep existing `ContentTypeClassification` intact.
- Add the new classification without changing generation behavior.
- Return confidence, reason codes, supporting signals, and warnings.
- Do not use an LLM.
- Do not browse the web.

## 30. Acceptance Criteria

The future implementation must:

- classify one source into exactly one supported format
- keep topic and format conceptually separate
- preserve current workflow compatibility
- use explicit instruction before inferred signals
- reject unsupported format requests safely
- distinguish `SERVICE` from `GUIDE`
- distinguish `EXPLAINER` from `ANALYSIS`
- distinguish `FEATURE` from `STANDARD_NEWS`
- distinguish `RESULT_REPORT` from general `SPORTS_NEWS`
- default safely to `STANDARD_NEWS`
- return stable confidence
- return stable reason codes
- return stable warnings
- make no AI or network calls
- avoid modifying existing production behavior in the first phase
