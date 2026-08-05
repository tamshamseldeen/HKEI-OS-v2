# HKEI OS v2 — Article Planning Specification

## 1. Purpose

The Article Planning layer receives:

- `NormalizedSource`
- `SourceRiskAssessment`
- `ExtractedFacts`
- `ContentTypeClassification`
- `ReaderIntentClassification`
- `EditorialStrategy`
- optional user instruction

It creates one structured editorial plan for the future article.

It does not:

- write article prose
- generate final headlines
- build prompts
- call an LLM
- create SEO metadata
- verify facts externally
- approve publication

## 2. Input

The layer accepts exactly:

- one `NormalizedSource`
- one `SourceRiskAssessment`
- one `ExtractedFacts`
- one `ContentTypeClassification`
- one `ReaderIntentClassification`
- one `EditorialStrategy`
- optional user instruction

## 3. Output

The layer returns one future object named `ArticlePlan`.

It contains these fields:

- `working_title`
- `lead_instruction`
- `sections`
- `closing_instruction`
- `required_facts`
- `required_attributions`
- `required_warnings`
- `prohibited_claims`
- `missing_information`
- `target_word_count`
- `reason_codes`
- `warnings`

Python types are not defined yet.

## 4. Core Principle

- Strategy determines treatment.
- Planning determines structure.
- The plan is internal editorial guidance.
- The plan must never appear directly in the final article.
- Every planned section must have a clear editorial purpose.
- No section may require unsupported facts.
- Thin source material must produce a small plan.
- Planning must preserve source uncertainty and risk controls.

## 5. Working Title

`working_title` is an internal descriptive title.

Rules:

- It may reuse the source title when suitable.
- It must not add unsupported facts.
- It is not the final publication headline.
- It must reflect the selected content type and primary fact.
- It must remain concise.

## 6. Lead Instruction

`lead_instruction` describes how the opening paragraph should work.

It must specify:

- which fact appears first
- whether attribution is required
- whether uncertainty must be shown
- whether the reader action or result should appear immediately

Do not write the final lead.

## 7. Article Sections

One future structure is named `ArticleSectionPlan`.

It contains these fields:

- `section_id`
- `purpose`
- `required_facts`
- `optional_facts`
- `required_attributions`
- `include_heading`
- `heading_guidance`
- `max_words`

Python types are not defined yet.

Rules:

- Section IDs must be stable machine-readable values.
- Section purpose must describe editorial function.
- Heading guidance must not be copied directly into the final article.
- A section may be omitted when unsupported.
- Section order must be preserved.
- No duplicate section purpose.

## 8. Supported MVP Section IDs

Use only these exact values:

- `LEAD`
- `CORE_UPDATE`
- `RESULT`
- `KEY_DETAILS`
- `OFFICIAL_INFORMATION`
- `CLAIM`
- `EVIDENCE`
- `VERDICT`
- `REQUIREMENTS`
- `PROCEDURE`
- `FEES`
- `DEADLINES`
- `READER_ACTION`
- `IMPACT`
- `EXPLANATION`
- `BACKGROUND`
- `TIMELINE`
- `COMPARISON`
- `QUOTES`
- `MISSING_INFORMATION`
- `CLOSING`

## 9. Lead Rules by Reader Intent

`GET_UPDATE`
→ newest confirmed fact first

`UNDERSTAND_EVENT`
→ event first, then explanation need

`KNOW_ACTION`
→ practical consequence or required action first

`CHECK_CLAIM`
→ claim first with attribution

`COMPARE_OPTIONS`
→ comparison subject first

`FOLLOW_DEVELOPMENT`
→ latest confirmed development first

`FIND_RESULT`
→ result first

`UNDERSTAND_IMPACT`
→ decision or event first, then affected parties

`GET_GUIDANCE`
→ safe practical guidance with attribution

`VERIFY_REQUIREMENTS`
→ service or requirement first

## 10. Plan for BREAKING_NEWS

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `MISSING_INFORMATION` when needed
- `CLOSING`

Rules:

- No FAQ
- No background unless supplied and essential
- No unnecessary headings
- No repeated facts
- Minimal structure

## 11. Plan for STANDARD_NEWS

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `KEY_DETAILS`
- `OFFICIAL_INFORMATION` when available
- `IMPACT` when supported
- `CLOSING`

## 12. Plan for NEWS_REWRITE

Default section order depends on source evidence and reader intent.

Rules:

- Do not reproduce source paragraph order.
- Preserve facts and attribution.
- Use the selected strategy.
- Build an independent editorial structure.
- Do not add unsupported sections.

## 13. Plan for PUBLIC_SERVICE_NEWS

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `KEY_DETAILS`
- `READER_ACTION`
- `FEES` when supported
- `DEADLINES` when supported
- `MISSING_INFORMATION` when needed
- `CLOSING`

Bullets may be used for practical actions when strategy allows.

## 14. Plan for GOVERNMENT_SERVICE_CONTENT

Default section order:

- `LEAD`
- `REQUIREMENTS`
- `PROCEDURE`
- `FEES` when supported
- `DEADLINES` when supported
- `OFFICIAL_INFORMATION`
- `READER_ACTION`
- `MISSING_INFORMATION` when needed
- `CLOSING`

Use attribution for all official procedures and requirements.

## 15. Plan for EXPLAINER

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `EXPLANATION`
- `BACKGROUND` when allowed
- `IMPACT` when supported
- `MISSING_INFORMATION` when needed
- `CLOSING`

## 16. Plan for FACT_CHECK

Default section order:

- `LEAD`
- `CLAIM`
- `EVIDENCE`
- `VERDICT`
- `MISSING_INFORMATION` when needed
- `CLOSING`

Rules:

- Claim must be identifiable.
- Evidence must be supplied.
- Verdict must preserve uncertainty.
- No definitive verdict without sufficient evidence.

## 17. Plan for HEALTH_CONTENT

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `OFFICIAL_INFORMATION`
- `EXPLANATION` when supported
- `READER_ACTION` when supported
- `MISSING_INFORMATION`
- `CLOSING`

Rules:

- Attribution is mandatory.
- No diagnosis.
- No invented treatment.
- No dosage reconstruction.
- Human review remains required when indicated.

## 18. Plan for LEGAL_FINANCIAL_HIGH_RISK_CONTENT

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `OFFICIAL_INFORMATION`
- `IMPACT`
- `READER_ACTION` only when source-supported
- `MISSING_INFORMATION`
- `CLOSING`

Rules:

- Preserve legal or financial attribution.
- Avoid definitive advice.
- Do not interpret obligations beyond the source.

## 19. Plan for SPORTS_NEWS

Default section order:

- `LEAD`
- `RESULT`
- `KEY_DETAILS`
- `QUOTES` when available
- `MISSING_INFORMATION` when needed
- `CLOSING`

Rules:

- Result appears first.
- Do not invent scorers, timing, competition, venue, standings, or significance.
- Very thin sources may use only `LEAD`, `RESULT`, and `MISSING_INFORMATION`.

## 20. Plan for TECHNOLOGY_NEWS

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `KEY_DETAILS`
- `IMPACT` when supported
- `OFFICIAL_INFORMATION` when available
- `CLOSING`

## 21. Plan for ECONOMY_NEWS

Default section order:

- `LEAD`
- `CORE_UPDATE`
- `KEY_DETAILS`
- `IMPACT`
- `OFFICIAL_INFORMATION`
- `MISSING_INFORMATION` when needed
- `CLOSING`

Use numbers and currencies exactly as supplied.

## 22. Plan for TRENDING_SOCIAL_CLAIM

Default section order:

- `LEAD`
- `CLAIM`
- `OFFICIAL_INFORMATION` when available
- `EVIDENCE` when supplied
- `MISSING_INFORMATION`
- `CLOSING`

Rules:

- Virality must not be treated as verification.
- Attribution is mandatory.
- Unverified status must be visible.

## 23. Required Facts

`required_facts` must contain facts that must appear in the final article.

Rules:

- Use only `ExtractedFacts` and `NormalizedSource`.
- Preserve exact numeric meaning.
- Preserve dates and currencies.
- Preserve uncertainty.
- Do not duplicate equivalent facts.
- Do not include facts excluded by risk policy.

## 24. Required Attributions

`required_attributions` must include:

- source attribution for claims
- official authority attribution
- attribution required by risk assessment
- attribution for quotations

Do not invent attribution.

## 25. Required Warnings

`required_warnings` must include relevant warnings from:

- `SourceRiskAssessment`
- `ContentTypeClassification`
- `ReaderIntentClassification`
- `EditorialStrategy`

Rules:

- Preserve order by workflow stage.
- Remove duplicates while preserving first occurrence.
- Warnings are internal unless they must be reflected editorially.

## 26. Prohibited Claims

`prohibited_claims` must describe unsupported statements the draft must not add.

Examples:

- unsupported cause
- unsupported consequence
- unsupported ranking impact
- unsupported legal interpretation
- unsupported medical advice
- unsupported financial recommendation
- unsupported quote
- unsupported identity
- unsupported date or number

## 27. Missing Information

`missing_information` must include material unknowns that affect understanding.

Rules:

- Use `ExtractedFacts.unknown_information`.
- Add only meaningful missing details.
- Do not turn every absent detail into a warning.
- Mention missing information once in the article unless necessary.

## 28. Heading Planning

`include_heading` may be `True` only when:

- `EditorialStrategy.use_headings` is `True`
- the section represents a distinct information block
- the article is not `VERY_SHORT`
- a heading improves navigation

`heading_guidance` must:

- be descriptive
- be Arabic-oriented
- avoid generic labels
- not expose internal section IDs

## 29. Word Allocation

The sum of section `max_words` should remain close to `EditorialStrategy.target_word_count`.

Rules:

- `LEAD` should generally receive 10% to 20%.
- `CORE_UPDATE` or `RESULT` receives priority.
- Missing information should remain concise.
- No section may exist only to fill word count.
- `VERY_SHORT` plans should normally have 2 to 4 sections.
- `SHORT` plans should normally have 3 to 6 sections.
- `MEDIUM` plans should normally have 4 to 8 sections.
- `LONG` plans should normally have 5 to 10 sections.

These are planning guides, not rigid quotas.

## 30. Closing Instruction

`closing_instruction` defines how the article should end.

Possible functions:

- concise final confirmed fact
- practical next step
- preserved uncertainty
- official-source reminder
- summary of impact

Do not:

- promise updates
- add generic conclusions
- repeat the lead
- add motivational language
- invent future developments

## 31. Reason Codes

- `RESULT_FIRST_PLAN`
- `UPDATE_FIRST_PLAN`
- `SERVICE_ACTION_PLAN`
- `REQUIREMENTS_FIRST_PLAN`
- `EXPLAINER_STRUCTURE_PLAN`
- `FACT_CHECK_STRUCTURE_PLAN`
- `HIGH_RISK_ATTRIBUTION_PLAN`
- `TREND_CLAIM_CAUTION_PLAN`
- `IMPACT_FOCUSED_PLAN`
- `COMPARISON_STRUCTURE_PLAN`
- `TIMELINE_STRUCTURE_PLAN`
- `LIMITED_SOURCE_PLAN`
- `MISSING_INFORMATION_SECTION_REQUIRED`
- `HEADINGS_ENABLED_BY_STRATEGY`
- `HEADINGS_DISABLED_BY_STRATEGY`
- `UNSUPPORTED_SECTION_REMOVED`
- `WORD_BUDGET_APPLIED`

## 32. Warning Codes

- `PLAN_SOURCE_TOO_THIN`
- `PLAN_REQUIRED_FACT_MISSING`
- `PLAN_ATTRIBUTION_REQUIRED`
- `PLAN_HIGH_RISK_REVIEW_REQUIRED`
- `PLAN_FACT_CHECK_EVIDENCE_INSUFFICIENT`
- `PLAN_UNSUPPORTED_BACKGROUND`
- `PLAN_UNSUPPORTED_TABLE`
- `PLAN_UNSUPPORTED_TIMELINE`
- `PLAN_UNSUPPORTED_QUOTE`
- `PLAN_MISSING_INFORMATION_REQUIRED`

## 33. Explicit User Instruction

- User instruction may request emphasis or structure.
- User instruction may not override source limits.
- User instruction may not remove mandatory attribution.
- User instruction may not remove risk warnings.
- User instruction may not force unsupported sections.
- Unsupported requests generate warnings.

## 34. Non-Goals

- No article prose generation
- No final headline generation
- No SEO metadata generation
- No prompt building
- No LLM calls
- No external verification
- No source crawling
- No automatic publication
- No publisher-style imitation

## 35. MVP Scope

For the first MVP:

- Produce one `ArticlePlan`.
- Use deterministic logic only.
- Use workflow outputs already available.
- Create ordered internal section plans.
- Allocate a target word budget.
- Preserve facts, attribution, warnings, and uncertainty.
- Do not generate article prose.
- Do not use an LLM.
- Do not browse the web.

## 36. Acceptance Criteria

The future implementation must:

- receive the full strategy workflow data
- return exactly one `ArticlePlan`
- create an ordered section sequence
- use only supported section IDs
- include required facts
- include required attribution
- include required warnings
- include prohibited claims
- include meaningful missing information
- respect strategy structural flags
- respect target word count
- remove unsupported sections
- never expose internal planning labels in final content
- remain separate from prompt building and drafting
