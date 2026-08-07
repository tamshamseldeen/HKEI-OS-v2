# HKEI OS v2 — Topic Classification Specification

## 1. Purpose

Topic Classification is the layer that answers:

> “What is this material primarily about?”

Topic is separate from:

- Editorial Format: how the material should be presented
- Reader Intent: what the reader needs
- Risk: how cautiously it must be handled
- Strategy: how the final article should be constructed
- Publication Decision

One source receives exactly one primary topic in the MVP.

## 2. Architectural Position

The target model is:

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

- Existing `ContentTypeClassification` remains temporarily for backward compatibility.
- `TopicClassification` is additive during migration.
- Editorial Format remains independent.
- Topic must eventually replace topic-like values currently embedded in `ContentTypeClassification`.
- No production workflow is migrated in the first implementation.

## 3. Input

The future classifier may receive:

- `NormalizedSource`
- `ExtractedFacts`
- `SourceRiskAssessment`
- existing `ContentTypeClassification`
- source metadata
- optional user instruction

Python signatures are not defined yet.

## 4. Output

The future output object is `TopicClassification`.

Fields:

- `topic`
- `confidence`
- `reason_codes`
- `supporting_signals`
- `warnings`

Python types are not defined yet.

## 5. Supported MVP Topics

Use only these exact values:

- `POLITICS`
- `ECONOMY`
- `BUSINESS`
- `TECHNOLOGY`
- `SPORTS`
- `GOVERNMENT`
- `WEATHER`
- `HEALTH`
- `CULTURE`
- `SCIENCE`
- `EDUCATION`
- `CRIME`
- `ENTERTAINMENT`
- `WORLD`
- `GENERAL`

`GENERAL` is the safe fallback.

## 6. Topic Definition Principle

Topic describes subject matter only.

Examples:

- Sports match result: Topic = `SPORTS`; Format = `RESULT_REPORT`.
- Sports match schedule: Topic = `SPORTS`; Format = `GUIDE`.
- Sports club history: Topic = `SPORTS`; Format = `FEATURE`.
- Traffic fine: Topic = `GOVERNMENT`; Format = `SERVICE`.
- Interest-rate decision: Topic = `ECONOMY`; Format = `STANDARD_NEWS`.
- Semiconductor market growth: Topic = `TECHNOLOGY`; Format may be `STANDARD_NEWS` or `ANALYSIS`.

Topic must not imply format.

## 7. POLITICS

Use when the primary subject involves:

- political institutions
- political parties
- elections
- political leaders acting politically
- diplomacy driven primarily by political decisions
- legislation as political activity

Do not classify ordinary government services as `POLITICS`.

## 8. ECONOMY

Use when macroeconomic activity is central.

Examples:

- inflation
- interest rates
- central banks
- currencies
- commodities
- oil markets
- employment
- GDP
- economic indicators
- trade
- shipping costs when economic impact is central
- tourism revenues as economic indicators

`ECONOMY` news is not automatically high-risk financial guidance.

## 9. BUSINESS

Use when a company, corporate transaction, earnings report, industry business activity, merger, acquisition, or commercial organization is central.

Distinguish:

`ECONOMY`
→ economy-wide or market-wide activity

`BUSINESS`
→ company or corporate activity

## 10. TECHNOLOGY

Use when technology is the main subject.

Examples:

- artificial intelligence
- semiconductors
- software
- hardware
- digital platforms
- cybersecurity
- consumer technology
- data centers

Financial metrics about a technology company do not automatically convert the topic to `ECONOMY` or financial high risk.

## 11. SPORTS

Use when the primary subject is:

- teams
- players
- coaches
- matches
- tournaments
- transfers
- training camps
- sports organizations

Words describing goals or winning intentions must not cause non-sports material to become `SPORTS`.

Sports topic does not imply `RESULT_REPORT`.

## 12. GOVERNMENT

Use when public authorities, official services, infrastructure, regulations, public administration, or government programs are central.

Examples:

- transport ministry projects
- traffic regulations
- public-service procedures
- government digital services
- official infrastructure projects

Government topic does not automatically imply high risk.

## 13. WEATHER

Use when the primary subject is:

- weather conditions
- heat waves
- storms
- rainfall
- drought
- meteorological warnings
- climate-related immediate conditions

Climate science research may instead be `SCIENCE` when research is the primary focus.

## 14. HEALTH

Use when the primary subject is:

- disease
- medicine
- treatment
- diagnosis
- symptoms
- hospitals
- public health
- medical research with direct health relevance

Health topic and medical risk remain separate dimensions.

## 15. CULTURE

Use when the primary subject is:

- archaeology
- heritage
- arts
- literature
- museums
- cultural institutions
- historical discoveries primarily framed culturally

## 16. SCIENCE

Use when scientific research, discovery, space, physics, biology, environment research, or academic scientific findings are central.

## 17. EDUCATION

Use when the primary subject is:

- schools
- universities
- exams
- educational policy
- students
- curricula
- admissions

## 18. CRIME

Use when the primary subject is:

- criminal incidents
- arrests
- criminal investigations
- prosecutions
- criminal allegations

Crime topic must remain separate from legal risk.

## 19. ENTERTAINMENT

Use when the primary subject is:

- cinema
- television
- music
- celebrities acting in entertainment context
- entertainment events

## 20. WORLD

Use only when international affairs are central but no more specific supported topic applies.

`WORLD` must not override a more specific topic such as `ECONOMY`, `SPORTS`, `TECHNOLOGY`, or `WEATHER` merely because multiple countries are involved.

## 21. GENERAL

Use when:

- no supported topic clearly dominates
- source material is too thin
- signals conflict without a defensible winner

`GENERAL` must produce low confidence.

## 22. Source Category Signal

`source.category` is a strong supporting signal when supplied.

Mappings may include:

- `economy` → `ECONOMY`
- `business` → `BUSINESS`
- `technology` → `TECHNOLOGY`
- `sports` → `SPORTS`
- `government` → `GOVERNMENT`
- `weather` → `WEATHER`
- `health` → `HEALTH`
- `culture` → `CULTURE`
- `science` → `SCIENCE`
- `education` → `EDUCATION`
- `crime` → `CRIME`
- `entertainment` → `ENTERTAINMENT`
- `politics` → `POLITICS`

Rules:

- Category is strong evidence, not unquestionable truth.
- Strong contradictory structural evidence may override category.
- Category must never determine editorial format.

## 23. Deterministic Signals

Possible signals:

- source category
- title terminology
- body terminology
- tags
- named organizations
- government entities
- sports teams and competition terminology
- economic indicators
- technology terminology
- weather terminology
- health terminology
- cultural terminology
- extracted facts
- dominant repeated terminology

Keywords alone are insufficient.

Require multiple supporting signals when category is unavailable.

## 24. Topic Precedence

Do not use one universal semantic precedence to force unrelated topics.

Instead:

1. Explicit reliable source category
2. Strong title signals
3. Consistent body signals
4. Tags
5. Extracted entities and structured facts
6. Existing `ContentTypeClassification` as transitional evidence only
7. `GENERAL` fallback

When multiple topics have strong evidence:

- select the primary subject of the headline and lead
- add `CONFLICTING_TOPIC_SIGNALS`
- reduce confidence when necessary

## 25. Existing ContentType Transitional Mapping

Use existing content type only as supporting evidence.

`SPORTS_NEWS`
→ `SPORTS`

`TECHNOLOGY_NEWS`
→ `TECHNOLOGY`

`ECONOMY_NEWS`
→ `ECONOMY`

`HEALTH_CONTENT`
→ `HEALTH`

`GOVERNMENT_SERVICE_CONTENT`
→ `GOVERNMENT`

`PUBLIC_SERVICE_NEWS`
→ no fixed topic

`LEGAL_FINANCIAL_HIGH_RISK_CONTENT`
→ no fixed topic

`BREAKING_NEWS`
→ no topic

`STANDARD_NEWS`
→ no topic

`NEWS_REWRITE`
→ no topic

`EXPLAINER`
→ no topic

`FACT_CHECK`
→ no topic

`TRENDING_SOCIAL_CLAIM`
→ no topic

Mixed-format values must not force a topic.

## 26. Benchmark Failure Examples

The following Batch 01 failures motivated this layer.

### Example A

OPEC+ oil-production decision

Correct primary topic:
`ECONOMY`

Incorrect legacy outcome observed:
`SPORTS_NEWS`

### Example B

Cairo Metro Line 4 construction progress

Correct primary topic:
`GOVERNMENT`

Incorrect legacy outcome observed:
`SPORTS_NEWS`

### Example C

Saudi tourism revenue growth

Correct primary topic:
`ECONOMY`

Incorrect legacy outcome observed:
`SPORTS_NEWS`

### Example D

Semiconductor companies and AI investment

Correct primary topic:
`TECHNOLOGY`

Incorrect legacy outcome observed:
`LEGAL_FINANCIAL_HIGH_RISK_CONTENT`

These are architecture-learning cases, not exceptions to hard-code.

## 27. Risk Independence

Topic must not determine risk.

Examples:

- Gold market news: Topic = `ECONOMY`; Risk may remain `LOW` or `MEDIUM` depending on claims.
- Personal investment recommendation: Topic = `ECONOMY`; Risk may be `HIGH`.
- Semiconductor market-cap news: Topic = `TECHNOLOGY`; Risk is not `HIGH` merely because investment terminology appears.
- Court fraud case: Topic may be `CRIME` or `BUSINESS`; Risk may be `HIGH`.

## 28. Confidence

Use:

- `HIGH`
- `MEDIUM`
- `LOW`

`HIGH`:
Strong consistent topic evidence.

`MEDIUM`:
One topic is most likely but overlap exists.

`LOW`:
Weak, contradictory, or insufficient evidence.

## 29. Warning Codes

- `LOW_TOPIC_CONFIDENCE`
- `CONFLICTING_TOPIC_SIGNALS`
- `CATEGORY_TOPIC_CONFLICT`
- `TOPIC_SIGNAL_INSUFFICIENT`
- `LEGACY_CONTENT_TYPE_CONFLICT`
- `TOPIC_MIGRATION_COMPATIBILITY_WARNING`

## 30. Non-Goals

- No editorial format classification
- No reader-intent classification
- No risk classification
- No strategy generation
- No article writing
- No AI classification
- No external search
- No multi-topic output in MVP
- No removal of `ContentTypeClassification` yet

## 31. MVP Scope

For the first implementation:

- classify exactly one primary topic
- use deterministic signals
- strongly use supplied source category
- use source title, body, tags, and extracted facts
- treat existing `ContentTypeClassification` as transitional evidence only
- return confidence, reasons, signals, and warnings
- make no AI or network calls
- remain additive

## 32. Acceptance Criteria

The future implementation must:

- return exactly one supported topic
- correctly distinguish subject from editorial format
- correctly classify the ten Batch 01 benchmark categories where sufficient evidence exists
- classify OPEC+ as `ECONOMY`
- classify semiconductor AI investment as `TECHNOLOGY`
- classify Cairo Metro construction as `GOVERNMENT`
- classify Saudi tourism revenue growth as `ECONOMY`
- classify Egyptian national-team training as `SPORTS` without implying `RESULT_REPORT`
- avoid using financial terminology alone to determine topic risk
- use `GENERAL` safely when evidence is inadequate
- return stable confidence
- return stable reason codes
- return stable warnings
- preserve existing workflows unchanged during the first phase
