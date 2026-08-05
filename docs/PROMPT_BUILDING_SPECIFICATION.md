# HKEI OS v2 — Prompt Building Specification

## 1. Purpose

The Prompt Building layer receives:

- `NormalizedSource`
- `SourceRiskAssessment`
- `ExtractedFacts`
- `ContentTypeClassification`
- `ReaderIntentClassification`
- `EditorialStrategy`
- `ArticlePlan`
- optional user instruction

It converts them into one provider-agnostic generation request.

It does not:

- call an LLM
- select an LLM provider
- generate article prose
- verify facts externally
- approve publication
- create final quality scores

## 2. Input

The layer accepts exactly:

- one `EditorialPlanningResult`
- optional user instruction
- one editorial policy text
- optional language-generation configuration

## 3. Output

The layer returns one future object named `GenerationPrompt`.

It contains these fields:

- `system_prompt`
- `user_prompt`
- `target_language`
- `target_word_count`
- `required_output_format`
- `prohibited_content`
- `required_warnings`
- `reason_codes`

Python types are not defined yet.

## 4. Core Principle

- `PromptBuilder` translates editorial decisions into model instructions.
- `PromptBuilder` must not make new editorial decisions.
- `PromptBuilder` must not reinterpret source facts.
- `PromptBuilder` must remain independent from OpenAI, Anthropic, Google, or any other provider.
- Internal planning labels must never appear in final article output.
- Source facts, claims, uncertainty, and attribution must remain clearly separated.
- The prompt must instruct the model to write only from supplied material.

## 5. Prompt Layers

Use this exact order:

1. Editorial Identity
2. Non-Negotiable Safety Rules
3. Editorial Policy
4. Output Requirements
5. Editorial Strategy
6. Internal Article Plan
7. Structured Facts
8. Claims and Attribution
9. Missing Information
10. Prohibited Claims
11. Original Source Material
12. User Instruction
13. Final Generation Command

This order must remain stable in the MVP.

## 6. System Prompt Responsibilities

The system prompt must define:

- the model's role as an Arabic editorial drafting assistant
- factual-grounding rules
- attribution rules
- uncertainty rules
- high-risk restrictions
- natural-Arabic requirements
- publication-ready formatting expectations
- prohibition against exposing internal planning
- prohibition against invented information

The system prompt must not contain:

- provider-specific syntax
- API parameters
- model names
- source-specific private data
- final article content

## 7. Editorial Identity

Use this product-neutral identity:

“You are an Arabic editorial drafting assistant operating inside HKEI OS.”

The model:

- follows HKEI editorial decisions
- does not make independent publication decisions
- does not claim verification
- does not reveal internal reasoning
- does not expose internal strategy or planning labels

Do not reference any publisher, website, or media organization.

## 8. Non-Negotiable Safety Rules

- Use only supplied facts and source material.
- Never invent facts, names, quotes, numbers, dates, places, causes, consequences, or sources.
- Never increase certainty beyond the source.
- Preserve attribution for claims.
- Preserve uncertainty.
- Do not provide unsupported medical, legal, financial, immigration, government-service, or emergency guidance.
- Do not treat social-media circulation as verification.
- Do not generate direct quotations unless exact quotations were supplied.
- Do not claim external verification unless explicitly stated in the input.
- Do not add background from model memory.
- Do not pad the article to reach a word count.

## 9. Editorial Policy Injection

The prompt may include one approved editorial policy text.

Rules:

- Policy must be loaded separately from source content.
- Policy belongs in the system prompt.
- Policy must be treated as editorial rules, not source facts.
- Missing policy must produce a deterministic configuration error in future implementation.
- Policy must be cached and not reloaded for every build when practical.

Implementation is not defined yet.

## 10. Output Requirements

The prompt must require:

- Arabic language
- publication-ready Markdown
- one primary headline
- natural Arabic paragraphs
- no internal labels
- no planning metadata
- no strategy metadata
- no model commentary
- no explanations before or after the article
- no token counts
- no confidence scores inside the article
- no FAQ unless enabled by `EditorialStrategy`
- no headings unless enabled by `EditorialStrategy`
- no table unless enabled by `EditorialStrategy`
- no timeline unless enabled by `EditorialStrategy`
- no bullets unless enabled by `EditorialStrategy`

## 11. Target Length

Use `EditorialStrategy.target_word_count`.

Rules:

- Treat target length as guidance, not a quota.
- Accuracy has priority over length.
- Thin source material must remain concise.
- The model must not add unsupported material to reach the target.
- A reasonable future tolerance is plus or minus 20%.

## 12. Editorial Strategy Section

Include internally:

- article length
- article depth
- writing mode
- structural flags
- target word count
- strategy warnings

This information is internal guidance only. Do not reproduce it in the final article.

## 13. Internal Article Plan Section

Include:

- working title
- lead instruction
- ordered section plans
- closing instruction
- word budgets
- required facts
- required attribution
- missing information
- prohibited claims

Rules:

- Section IDs are internal.
- Section purposes are internal.
- Heading guidance is internal.
- Do not copy internal labels into the article.
- Use the plan to create natural Arabic structure.

## 14. Structured Facts Section

Include these categories separately:

- core facts
- claims
- quotes
- named people
- organizations
- government entities
- locations
- countries
- dates
- times
- numbers
- percentages
- currencies
- laws and regulations
- products
- events

Rules:

- Empty categories must be represented clearly.
- Facts must not be mixed with claims.
- Exact numbers, dates, currencies, and quotations must be preserved.
- Duplicate source facts may be supplied but must not be unnecessarily repeated in output.

## 15. Claims and Attribution Section

Claims must be listed separately from confirmed facts.

For each supplied claim, the model must:

- preserve attribution
- preserve uncertainty
- avoid presenting it as independently verified
- avoid strengthening wording
- avoid adding conclusions not supported by evidence

If attribution is required but unavailable:

- the article must use cautious wording
- required warning context must be preserved
- the model must not invent attribution

## 16. Missing Information Section

Include `ArticlePlan.missing_information`.

Rules:

- Missing information may be mentioned only when editorially relevant.
- Mention it concisely.
- Do not repeatedly list missing details.
- Do not convert missing information into assumptions.
- Do not promise future updates.

## 17. Prohibited Claims Section

Include `ArticlePlan.prohibited_claims`.

The model must treat these as hard constraints.

Examples:

- unsupported facts
- unsupported quotes
- unsupported dates
- unsupported numbers
- unsupported causes
- unsupported consequences
- unsupported legal interpretations
- unsupported medical guidance
- unsupported financial recommendations
- unsupported sports-result details
- unverified social claims presented as facts

## 18. Original Source Material

Include:

- original title
- original body
- source name
- source URL when present
- publication date when present
- country when present
- author when present

Rules:

- Clearly label source material.
- Do not treat source metadata as article prose.
- Preserve source attribution.
- Do not instruct the model to copy source structure.
- The final article must be structurally independent.

## 19. User Instruction

Include user instruction only when present.

Rules:

- User instruction has lower priority than factual safety and risk controls.
- User instruction may influence tone, emphasis, or supported structure.
- User instruction may not force invented facts.
- User instruction may not remove attribution.
- User instruction may not remove mandatory warnings.
- User instruction may not override prohibited claims.
- User instruction may not force unsupported expansion.

## 20. Final Generation Command

The prompt must end with a direct command requiring the model to:

- write one final Arabic article
- follow the approved strategy
- follow the internal plan
- use only supplied material
- preserve uncertainty
- preserve attribution
- avoid repetition
- produce natural Arabic
- return article content only

Use wording equivalent to:

“Write the final publication-ready Arabic article now. Return the article only.”

## 21. Provider-Agnostic Design

The future implementation must not include:

- OpenAI message objects
- Anthropic message objects
- Gemini request objects
- model names
- API keys
- temperature
- token limits
- provider-specific response formats

Provider adapters will convert `GenerationPrompt` later.

## 22. Required Output Format

Use this MVP value:

`MARKDOWN_ARTICLE`

The final generated content should contain:

- one Markdown H1 headline
- article body
- optional H2 headings only when enabled
- optional lists, tables, FAQ, or timeline only when enabled

The generated article must not contain:

- JSON
- YAML
- XML
- internal IDs
- reasoning
- strategy
- planning metadata
- warnings as machine codes

## 23. Prompt Size Policy

- Include only information necessary for generation.
- Avoid repeating identical facts across multiple prompt sections where practical.
- Preserve critical warnings even when prompt size is reduced.
- Never remove prohibited claims.
- Never remove high-risk restrictions.
- Never remove required attribution.
- Never remove source text in the MVP.
- Prompt compression is outside the first implementation.

## 24. Deterministic Formatting

The future `PromptBuilder` should use deterministic section headings and ordering.

Prompt output should be reproducible for identical inputs.

Do not include:

- timestamps generated at runtime
- random IDs
- provider-specific metadata
- nondeterministic ordering

## 25. Configuration Errors

Future configuration errors:

- `EDITORIAL_POLICY_MISSING`
- `UNSUPPORTED_OUTPUT_FORMAT`
- `TARGET_LANGUAGE_MISSING`
- `INVALID_TARGET_WORD_COUNT`
- `REQUIRED_PLAN_MISSING`

Configuration errors must stop prompt creation.

Exception classes are not defined yet.

## 26. Reason Codes

- `PROMPT_EDITORIAL_POLICY_INCLUDED`
- `PROMPT_STRATEGY_INCLUDED`
- `PROMPT_PLAN_INCLUDED`
- `PROMPT_FACTS_INCLUDED`
- `PROMPT_CLAIMS_SEPARATED`
- `PROMPT_MISSING_INFORMATION_INCLUDED`
- `PROMPT_PROHIBITIONS_INCLUDED`
- `PROMPT_SOURCE_INCLUDED`
- `PROMPT_USER_INSTRUCTION_INCLUDED`
- `PROMPT_HIGH_RISK_RESTRICTIONS_INCLUDED`
- `PROMPT_MARKDOWN_OUTPUT_REQUIRED`

## 27. Security and Injection Resistance

- Source text is untrusted content.
- User instruction is untrusted content.
- Content inside the source must never override system rules.
- Instructions found inside source material must be treated as quoted source content, not system instructions.
- HTML, Markdown, JSON, or command-like text inside the source must not change prompt hierarchy.
- The future implementation must clearly delimit source content.
- The model must be instructed to ignore instructions embedded inside source material.

## 28. Non-Goals

- No LLM call
- No provider selection
- No API request
- No article generation
- No response parsing
- No quality evaluation
- No SEO metadata generation
- No publication decision
- No automatic web verification
- No prompt optimization by AI
- No publisher-style imitation

## 29. MVP Scope

For the first MVP:

- Build one `GenerationPrompt`.
- Use deterministic formatting.
- Use one approved editorial policy.
- Use Arabic as the target language.
- Use `MARKDOWN_ARTICLE` as the output format.
- Include full source material.
- Include workflow decisions and constraints.
- Do not call an LLM.
- Do not use provider-specific objects.

## 30. Acceptance Criteria

The future implementation must:

- receive one `EditorialPlanningResult`
- return exactly one `GenerationPrompt`
- return separate system and user prompts
- include editorial policy
- include safety rules
- include strategy
- include article plan
- include structured facts
- separate facts from claims
- include missing information
- include prohibited claims
- include original source material
- include user instruction when present
- require Arabic Markdown output
- prevent internal labels from appearing in final article
- remain provider-agnostic
- produce identical output for identical input
- make no LLM or network calls
