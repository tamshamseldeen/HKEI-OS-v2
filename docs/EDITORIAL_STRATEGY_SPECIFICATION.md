# HKEI OS v2 — Editorial Strategy Specification

## 1. Purpose

The Editorial Strategy layer receives:

- `NormalizedSource`
- `SourceRiskAssessment`
- `ExtractedFacts`
- `ContentTypeClassification`
- `ReaderIntentClassification`
- optional user instruction

It determines how the article should be written before planning and drafting.

It does not:

- write the article
- generate headlines
- build prompts
- perform SEO generation
- verify facts externally
- approve publication

## 2. Input

The layer accepts exactly:

- one `NormalizedSource`
- one `SourceRiskAssessment`
- one `ExtractedFacts`
- one `ContentTypeClassification`
- one `ReaderIntentClassification`
- optional user instruction

## 3. Output

The layer returns one future object named `EditorialStrategy`.

It contains these fields:

- `article_length`
- `article_depth`
- `writing_mode`
- `use_headings`
- `use_bullets`
- `use_table`
- `use_faq`
- `use_timeline`
- `use_background`
- `use_quotes`
- `use_attribution`
- `include_missing_information`
- `include_reader_action`
- `target_word_count`
- `reason_codes`
- `warnings`

Python types are not defined yet.

## 4. Core Principle

- Strategy determines treatment before drafting.
- Content type answers what kind of content this is.
- Reader intent answers what the reader needs.
- Strategy answers how the article should be built.
- Risk may restrict the strategy.
- Source depth limits article depth.
- The system must never force long-form output from thin source material.
- One source receives exactly one primary strategy in the MVP.

## 5. Article Length

Use these exact values:

- `VERY_SHORT`
- `SHORT`
- `MEDIUM`
- `LONG`

`VERY_SHORT`:
80 to 150 words.

`SHORT`:
150 to 300 words.

`MEDIUM`:
300 to 600 words.

`LONG`:
600 to 1000 words.

These are editorial targets, not rigid quotas.

## 6. Article Depth

Use these exact values:

- `UPDATE`
- `STANDARD`
- `EXPLAINED`
- `DETAILED`

`UPDATE`:
Fast factual coverage with minimal context.

`STANDARD`:
Conventional news coverage with core facts and essential context.

`EXPLAINED`:
Adds causes, steps, consequences, or practical explanation.

`DETAILED`:
Uses substantial source material, background, evidence, and structured sections.

## 7. Writing Mode

Use these exact values:

- `DIRECT_NEWS`
- `SERVICE`
- `EXPLAINER`
- `FACT_CHECK`
- `HIGH_RISK_CAUTION`
- `RESULT_REPORT`
- `TREND_UPDATE`
- `COMPARISON`

## 8. Structural Options

The strategy contains these boolean controls:

- `use_headings`
- `use_bullets`
- `use_table`
- `use_faq`
- `use_timeline`
- `use_background`
- `use_quotes`
- `use_attribution`
- `include_missing_information`
- `include_reader_action`

Each option is enabled only when editorially useful and supported by the source.

## 9. Source-Depth Signals

Deterministic source-depth signals include:

- title and body word count
- number of core facts
- number of claims
- number of quotes
- number of dates
- number of numbers
- number of currencies
- number of entities
- number of unknown-information items
- source attribution quality
- classification confidence
- reader-intent confidence

Source length alone is not sufficient.

## 10. VERY_SHORT Strategy

Use when:

- source material is extremely limited
- only one or two supported facts exist
- unknown information is substantial
- the main reader need is a fast update or result

Default characteristics:

`article_length`:
`VERY_SHORT`

`article_depth`:
`UPDATE`

`target_word_count`:
120

`use_headings`:
`False`

`use_bullets`:
`False`

`use_table`:
`False`

`use_faq`:
`False`

`use_timeline`:
`False`

`use_background`:
`False`

`include_missing_information`:
`True` when important details are absent

## 11. SHORT Strategy

Use when:

- enough facts exist for a concise report
- the source supports a lead and two to four short paragraphs
- extensive background is unnecessary

Default target: 220 words.

## 12. MEDIUM Strategy

Use when:

- the source contains multiple facts, dates, numbers, procedures, consequences, or context
- the reader needs explanation or practical value
- headings may improve navigation

Default target: 450 words.

## 13. LONG Strategy

Use only when:

- the source contains substantial verified material
- multiple sections are editorially justified
- background, timeline, evidence, or detailed procedures are available
- the article can add value without padding

Default target: 800 words.

`LONG` must never be selected only because the user asks for more words when source material is insufficient.

## 14. Strategy by Content Type

`BREAKING_NEWS`
→ `VERY_SHORT` / `UPDATE` / `DIRECT_NEWS`

`STANDARD_NEWS`
→ `SHORT` / `STANDARD` / `DIRECT_NEWS`

`NEWS_REWRITE`
→ preserve suitable source depth / `DIRECT_NEWS`

`PUBLIC_SERVICE_NEWS`
→ `MEDIUM` / `EXPLAINED` / `SERVICE`

`GOVERNMENT_SERVICE_CONTENT`
→ `MEDIUM` / `EXPLAINED` / `SERVICE`

`EXPLAINER`
→ `MEDIUM` or `LONG` / `EXPLAINED` / `EXPLAINER`

`FACT_CHECK`
→ `MEDIUM` / `DETAILED` / `FACT_CHECK`

`HEALTH_CONTENT`
→ `SHORT` or `MEDIUM` / `EXPLAINED` / `HIGH_RISK_CAUTION`

`LEGAL_FINANCIAL_HIGH_RISK_CONTENT`
→ `SHORT` or `MEDIUM` / `EXPLAINED` / `HIGH_RISK_CAUTION`

`SPORTS_NEWS`
→ `VERY_SHORT` or `SHORT` / `UPDATE` or `STANDARD` / `RESULT_REPORT`

`TECHNOLOGY_NEWS`
→ `SHORT` / `STANDARD` / `DIRECT_NEWS`

`ECONOMY_NEWS`
→ `SHORT` or `MEDIUM` / `STANDARD` or `EXPLAINED` / `DIRECT_NEWS`

`TRENDING_SOCIAL_CLAIM`
→ `VERY_SHORT` or `SHORT` / `UPDATE` / `TREND_UPDATE`

These defaults may be adjusted by source depth, risk, and reader intent.

## 15. Strategy by Reader Intent

`GET_UPDATE`
→ concise, direct, minimal background

`UNDERSTAND_EVENT`
→ explanation, context, headings when useful

`KNOW_ACTION`
→ practical steps, bullets when useful, reader action

`CHECK_CLAIM`
→ claim, evidence, verdict structure

`COMPARE_OPTIONS`
→ comparison structure, table only when supported

`FOLLOW_DEVELOPMENT`
→ chronology or timeline when dates exist

`FIND_RESULT`
→ result first, then essential details

`UNDERSTAND_IMPACT`
→ affected parties, consequences, supporting numbers

`GET_GUIDANCE`
→ cautious practical guidance with warnings

`VERIFY_REQUIREMENTS`
→ requirements, documents, fees, deadlines, steps

## 16. Risk Constraints

`LOW`:
No extra structural restriction.

`MEDIUM`:
Preserve attribution and uncertainty.

`HIGH`:

- Mandatory human review.
- Use attribution.
- Use cautious wording.
- Do not add unsupported guidance.
- Do not over-expand.

`CRITICAL`:
Generation may be blocked. If generation is allowed for review purposes, use `HIGH_RISK_CAUTION` and minimal supported content only.

## 17. Heading Rules

Headings may be used when:

- the article has more than one distinct information block
- the target length is `MEDIUM` or `LONG`
- the reader intent requires procedures, explanation, comparison, or impact

Headings must not:

- expose internal labels
- repeat the headline
- use generic labels such as “التفاصيل” without added value
- appear in `VERY_SHORT` articles

## 18. Bullet Rules

Bullets may be used when:

- listing steps
- listing requirements
- listing penalties
- listing dates
- listing features or differences

Bullets must not replace normal prose in ordinary news.

## 19. Table Rules

Tables may be used only when:

- comparing structured values
- listing fees
- listing penalties
- presenting dates or requirements
- the source contains enough exact data

Never create a table from inferred or incomplete values.

## 20. FAQ Rules

FAQ may be used only when:

- reader intent is `VERIFY_REQUIREMENTS`, `KNOW_ACTION`, or `UNDERSTAND_EVENT`
- there are at least three distinct supported questions
- the article is `MEDIUM` or `LONG`

Do not use FAQ in:

- `BREAKING_NEWS`
- `VERY_SHORT` articles
- ordinary result reports
- sources with limited facts

## 21. Timeline Rules

Timeline may be used only when:

- multiple meaningful dates or times exist
- chronological order improves understanding
- the source supports every timeline item

## 22. Background Rules

Background may be used only when:

- the source provides background
- verified prior context is supplied
- the reader cannot understand the event without it

Do not generate background from model memory in the MVP.

## 23. Quote Rules

Use quotes only when:

- exact quotes exist in `ExtractedFacts`
- attribution is available
- the wording is preserved

Never invent, reconstruct, or paraphrase a direct quote as if exact.

## 24. Missing Information Policy

`include_missing_information` should be `True` when:

- missing information materially affects understanding
- the source is incomplete
- the article could otherwise imply false certainty

Missing information should be mentioned concisely and only once unless editorially necessary.

## 25. Reader Action Policy

`include_reader_action` should be `True` when:

- reader intent is `KNOW_ACTION`
- reader intent is `VERIFY_REQUIREMENTS`
- reader intent is `GET_GUIDANCE`
- public safety or government service content requires a next step

Reader action must be supported by the source.

## 26. Reason Codes

- `LIMITED_SOURCE_DEPTH`
- `SUFFICIENT_STANDARD_DEPTH`
- `RICH_SOURCE_DEPTH`
- `BREAKING_UPDATE_STRATEGY`
- `SERVICE_STRATEGY`
- `EXPLAINER_STRATEGY`
- `FACT_CHECK_STRATEGY`
- `HIGH_RISK_CAUTION_STRATEGY`
- `RESULT_FIRST_STRATEGY`
- `TREND_CAUTION_STRATEGY`
- `COMPARISON_STRATEGY`
- `READER_ACTION_REQUIRED`
- `MISSING_INFORMATION_MUST_BE_SHOWN`
- `SOURCE_TOO_THIN_FOR_REQUESTED_LENGTH`
- `HEADINGS_NOT_JUSTIFIED`
- `TABLE_NOT_JUSTIFIED`
- `FAQ_NOT_JUSTIFIED`
- `TIMELINE_NOT_JUSTIFIED`

## 27. Warning Codes

- `SOURCE_TOO_THIN_FOR_LONG_FORM`
- `HIGH_RISK_REVIEW_REQUIRED`
- `CRITICAL_RISK_GENERATION_RESTRICTED`
- `UNSUPPORTED_BACKGROUND_REQUEST`
- `UNSUPPORTED_TABLE_REQUEST`
- `UNSUPPORTED_FAQ_REQUEST`
- `UNSUPPORTED_TIMELINE_REQUEST`
- `UNSUPPORTED_QUOTE_REQUEST`
- `MISSING_INFORMATION_NOTICE_REQUIRED`

## 28. Explicit User Instruction

- User instruction may request length, format, or style.
- User instruction may influence strategy.
- User instruction must never override factual limits, risk controls, or source depth.
- Unsupported requests must produce warnings instead of fabricated expansion.
- Configurability is allowed only within editorial safety boundaries.

## 29. Non-Goals

- No article generation
- No headline generation
- No prompt building
- No SEO metadata generation
- No external verification
- No publisher-style imitation
- No model selection
- No automatic publication
- No arbitrary word-count padding

## 30. MVP Scope

For the first MVP:

- Produce one `EditorialStrategy`.
- Use deterministic logic only.
- Use workflow outputs already available.
- Support the documented structural controls.
- Do not use an LLM.
- Do not browse the web.
- Do not generate content.
- Return stable reasons and warnings.

## 31. Acceptance Criteria

The future implementation must:

- receive source, assessment, facts, content type, reader intent, and optional instruction
- return exactly one article length
- return exactly one article depth
- return exactly one writing mode
- return structural boolean controls
- return one target word count
- return stable reason codes
- return zero or more warnings
- respect source-depth limits
- respect risk restrictions
- avoid long-form output from thin material
- enable structures only when supported
- keep strategy separate from article generation
