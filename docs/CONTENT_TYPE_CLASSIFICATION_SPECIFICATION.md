# HKEI OS v2 — Content Type Classification Specification

## 1. Purpose

The Content Type Classification layer receives:

- `NormalizedSource`
- `SourceRiskAssessment`
- `ExtractedFacts`

It assigns the source material one editorial content type before strategy and drafting.

It does not:

- write the article
- generate headlines
- perform SEO
- build prompts
- verify facts externally
- make the final publication decision

## 2. Input

The layer accepts exactly:

- one `NormalizedSource`
- one `SourceRiskAssessment`
- one `ExtractedFacts`

## 3. Output

The layer returns one future object named `ContentTypeClassification`.

It contains these fields:

- `content_type`
- `confidence`
- `reason_codes`
- `supporting_signals`
- `warnings`

Python types are not defined yet.

## 4. Supported MVP Content Types

The MVP supports only these exact values:

- `BREAKING_NEWS`
- `STANDARD_NEWS`
- `NEWS_REWRITE`
- `PUBLIC_SERVICE_NEWS`
- `GOVERNMENT_SERVICE_CONTENT`
- `EXPLAINER`
- `FACT_CHECK`
- `HEALTH_CONTENT`
- `LEGAL_FINANCIAL_HIGH_RISK_CONTENT`
- `SPORTS_NEWS`
- `TECHNOLOGY_NEWS`
- `ECONOMY_NEWS`
- `TRENDING_SOCIAL_CLAIM`

## 5. Classification Principles

- Classification describes editorial treatment, not only subject category.
- Risk level and content type are separate concerns.
- One source receives exactly one primary content type.
- Classification must preserve uncertainty.
- Deterministic signals are preferred in the MVP.
- A keyword alone must not override stronger structural evidence.
- High-risk status may restrict treatment but does not automatically define the content type.

## 6. BREAKING_NEWS

Use when:

- the source reports a new event
- immediacy is central
- available details may still be limited
- the reader's main need is a fast factual update

Typical signals:

- عاجل
- الآن
- منذ قليل
- قبل قليل
- immediate event language
- recent publication time combined with a new event

Do not use merely because the source is short.

## 7. STANDARD_NEWS

Use when:

- the source reports a current event
- enough details exist for a conventional news report
- the primary goal is informing the reader what happened

This is the default news classification when no more specific type applies.

## 8. NEWS_REWRITE

Use when:

- the user explicitly requests rewriting or re-editing
- the source is an existing article
- the primary goal is structural and linguistic transformation

Automatic detection alone is insufficient for this type in the MVP. It normally requires explicit user instruction or metadata.

## 9. PUBLIC_SERVICE_NEWS

Use when:

- the source gives practical information affecting daily life
- the reader needs to know what to do, avoid, pay, prepare, or follow

Examples:

- traffic fines
- service interruptions
- application deadlines
- consumer warnings
- weather-related instructions
- public transport changes

## 10. GOVERNMENT_SERVICE_CONTENT

Use when:

- the source explains a government service
- eligibility, fees, procedures, documents, dates, or official steps are central

Examples:

- residency procedures
- visa requirements
- government benefits
- permit applications
- official digital services

This content type requires stronger source attribution.

## 11. EXPLAINER

Use when:

- the reader needs understanding, not only an update
- the source explains why, how, consequences, steps, or background
- structure may include sections, lists, tables, or examples

Do not classify as `EXPLAINER` only because the source is long.

## 12. FACT_CHECK

Use when:

- the source evaluates a specific claim
- the workflow must distinguish claim, evidence, and verdict
- the article must not be produced without identifiable claim evidence

`FACT_CHECK` requires explicit claim-verification context.

## 13. HEALTH_CONTENT

Use when:

- health, disease, medication, treatment, diagnosis, symptoms, dosage, prevention, or medical guidance is central

`HEALTH_CONTENT` remains subject to risk assessment and mandatory human review when required.

## 14. LEGAL_FINANCIAL_HIGH_RISK_CONTENT

Use when:

- legal obligations, court decisions, taxes, penalties, investments, loans, interest, financial products, or consequential financial guidance are central

Use only when legal or financial decision-making is a primary reader need.

## 15. SPORTS_NEWS

Use when:

- teams, players, matches, competitions, scores, transfers, or sports organizations are central

Sports commentary and opinion are outside the MVP.

## 16. TECHNOLOGY_NEWS

Use when:

- technology products, platforms, cybersecurity, software, hardware, artificial intelligence, or digital services are central

Cybersecurity incidents may also carry high risk.

## 17. ECONOMY_NEWS

Use when:

- markets, companies, economic indicators, prices, trade, employment, inflation, energy, or business activity are central

`ECONOMY_NEWS` differs from personal financial guidance.

## 18. TRENDING_SOCIAL_CLAIM

Use when:

- the source originates mainly from social media or viral circulation
- verification is incomplete
- the primary editorial need is cautious attribution

This type must preserve uncertainty and must not present virality as truth.

## 19. Deterministic Signals

Possible MVP signals include:

- source category
- tags
- title keywords
- body keywords
- risk topics
- government-entity presence
- numbers, currencies, dates, and deadlines
- user instruction
- social-platform source metadata
- event and service terminology

Signal weights and precedence must be documented in implementation tasks.

## 20. Precedence Rules

The default precedence is:

1. Explicit user instruction
2. `FACT_CHECK`
3. `GOVERNMENT_SERVICE_CONTENT`
4. `HEALTH_CONTENT`
5. `LEGAL_FINANCIAL_HIGH_RISK_CONTENT`
6. `PUBLIC_SERVICE_NEWS`
7. `SPORTS_NEWS`
8. `TECHNOLOGY_NEWS`
9. `ECONOMY_NEWS`
10. `TRENDING_SOCIAL_CLAIM`
11. `BREAKING_NEWS`
12. `EXPLAINER`
13. `NEWS_REWRITE`
14. `STANDARD_NEWS`

Precedence resolves competing matches but does not replace supporting evidence.

## 21. Confidence

Use these exact values:

- `HIGH`
- `MEDIUM`
- `LOW`

`HIGH`:
Strong and consistent signals support one content type.

`MEDIUM`:
One type is most likely, but signals overlap.

`LOW`:
The available material is insufficient or contradictory.

Low confidence must add a warning.

## 22. Warning Codes

- `LOW_CLASSIFICATION_CONFIDENCE`
- `CONFLICTING_CONTENT_TYPE_SIGNALS`
- `EXPLICIT_USER_INTENT_REQUIRED`
- `FACT_CHECK_EVIDENCE_MISSING`
- `GOVERNMENT_SOURCE_RECOMMENDED`
- `SOCIAL_CLAIM_UNVERIFIED`
- `HIGH_RISK_TREATMENT_REQUIRED`

## 23. Non-Goals

- No article generation
- No headline generation
- No SEO generation
- No prompt building
- No sentiment analysis
- No political-bias classification
- No publisher-style imitation
- No multi-label output in the MVP
- No automatic web verification

## 24. MVP Scope

For the first MVP:

- Classify one `EditorialIngestionResult`.
- Return exactly one primary content type.
- Use deterministic signals only.
- Use source metadata, risk topics, and extracted facts.
- Do not browse the web.
- Do not use an LLM.
- Return confidence, reasons, and warnings.

## 25. Acceptance Criteria

The future implementation must:

- receive one normalized source, assessment, and facts
- return exactly one supported content type
- return one confidence level
- return stable reason codes
- return zero or more supporting signals
- return zero or more warnings
- preserve separation between risk and content type
- default safely to `STANDARD_NEWS` when no stronger type is supported
- never classify `FACT_CHECK` without claim-verification context
- never classify `NEWS_REWRITE` without explicit intent or metadata
