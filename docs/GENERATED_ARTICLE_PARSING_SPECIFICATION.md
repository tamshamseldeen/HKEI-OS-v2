# HKEI OS v2 — Generated Article Parsing Specification

## 1. Purpose

The Generated Article Parsing layer receives:

- one `GenerationResult`
- one `GenerationPrompt`
- one `EditorialPlanningResult`

It returns one normalized generated article representation.

It does not:

- rewrite article content
- improve style
- verify facts externally
- generate SEO metadata
- score editorial quality
- approve publication
- call an LLM

## 2. Input

The layer accepts exactly:

- one `GenerationResult`
- one `GenerationPrompt`
- one `EditorialPlanningResult`

## 3. Output

The layer returns one future object named `ParsedArticle`.

It contains these fields:

- `headline`
- `body_markdown`
- `full_markdown`
- `headings`
- `paragraphs`
- `bullet_items`
- `table_count`
- `faq_detected`
- `timeline_detected`
- `word_count`
- `warnings`
- `reason_codes`

Python types are not defined yet.

## 4. Core Principle

- `GenerationResult.content` is untrusted model output.
- Parsing must be deterministic.
- Parsing must not invent or rewrite content.
- Parsing may normalize harmless formatting only.
- Parsing must detect malformed or disallowed structures.
- Raw generated content must remain available through `GenerationResult`.
- `ParsedArticle` is a structural representation, not a corrected article.

## 5. Supported Input Format

The MVP supports only:

`MARKDOWN_ARTICLE`

Expected structure:

- exactly one Markdown H1 headline
- article body after the headline
- optional H2 headings when allowed
- optional bullet lists when allowed
- optional Markdown tables when allowed
- optional FAQ or timeline only when allowed

## 6. Headline Extraction

Rules:

- The first non-empty line must begin with `# `.
- Extract text after `# ` as the headline.
- Trim leading and trailing whitespace.
- The headline must not be empty.
- Additional H1 headings are invalid.
- Do not rewrite the headline.
- Do not convert plain text into H1 automatically in the MVP.

## 7. Body Extraction

`body_markdown` contains all content after the first H1 headline.

Rules:

- Trim leading and trailing blank lines.
- Preserve internal Markdown.
- Preserve paragraph wording exactly.
- Do not remove supported headings, lists, or tables.
- Do not add missing paragraphs.
- An empty body is invalid.

## 8. Full Markdown

`full_markdown` contains:

- the normalized H1 headline
- one blank line
- normalized `body_markdown`

Harmless normalization may include:

- converting CRLF to LF
- converting CR to LF
- removing trailing whitespace from lines
- collapsing three or more blank lines to two blank lines
- trimming document boundaries

Do not alter wording or punctuation.

## 9. H2 Heading Detection

Detect lines beginning with `## ` and return heading text without the prefix.

Rules:

- Preserve order.
- Preserve duplicates.
- Ignore deeper headings for heading extraction.
- H2 headings are invalid when the `GenerationPrompt` strategy disables
  headings.
- Internal planning labels must be detected as violations.

## 10. Forbidden Internal Labels

Detect these exact internal labels when used as visible headings or standalone
labels:

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
- `EDITORIAL STRATEGY`
- `INTERNAL ARTICLE PLAN`
- `STRUCTURED FACTS`
- `CLAIMS AND ATTRIBUTION`
- `PROHIBITED CLAIMS`
- `ORIGINAL SOURCE MATERIAL`
- `FINAL GENERATION COMMAND`

If one is detected, add:

`INTERNAL_LABEL_EXPOSED`

## 11. Paragraph Extraction

Paragraphs are Markdown blocks separated by one or more blank lines.

Exclude blocks that are:

- the H1 headline
- H2 headings
- bullet lists
- numbered lists
- Markdown tables

Preserve paragraph order and wording. Do not split paragraphs by sentence.

## 12. Bullet Detection

Detect unordered bullet lines beginning with:

- `- `
- `* `
- `+ `

Return bullet text without the marker.

Rules:

- Preserve order.
- Preserve duplicates.
- Bullets are invalid when `strategy.use_bullets` is `False`.

## 13. Table Detection

Detect Markdown tables using:

- a header row
- a following separator row containing dashes

Return only `table_count`. Do not parse table cells in the MVP.

Tables are invalid when `strategy.use_table` is `False`.

## 14. FAQ Detection

FAQ is detected when any of the following applies:

- an H2 heading contains `الأسئلة الشائعة`
- an H2 heading contains `أسئلة شائعة`
- an H2 heading contains `FAQ`
- three or more question-like lines are present

Question-like lines may end with `؟` or `?`, or begin with common Arabic
question forms.

FAQ is invalid when `strategy.use_faq` is `False`.

## 15. Timeline Detection

Timeline is detected when:

- an H2 heading contains `الخط الزمني`
- an H2 heading contains `التسلسل الزمني`
- an H2 heading contains `Timeline`
- three or more date-led lines are present

Timeline is invalid when `strategy.use_timeline` is `False`.

## 16. Word Count

Calculate `word_count` from visible article text.

Exclude:

- Markdown heading markers
- bullet markers
- table separators
- Markdown syntax characters

Include:

- headline words
- body words
- heading text
- bullet text
- table cell text when practical

Use deterministic whitespace-separated counting.

## 17. Required Warnings

- `ARTICLE_H1_MISSING`
- `ARTICLE_H1_MULTIPLE`
- `ARTICLE_HEADLINE_EMPTY`
- `ARTICLE_BODY_EMPTY`
- `INTERNAL_LABEL_EXPOSED`
- `HEADINGS_NOT_ALLOWED`
- `BULLETS_NOT_ALLOWED`
- `TABLE_NOT_ALLOWED`
- `FAQ_NOT_ALLOWED`
- `TIMELINE_NOT_ALLOWED`
- `CODE_FENCE_DETECTED`
- `JSON_OUTPUT_DETECTED`
- `YAML_OUTPUT_DETECTED`
- `XML_OUTPUT_DETECTED`
- `MODEL_COMMENTARY_DETECTED`
- `ARTICLE_TOO_SHORT`
- `ARTICLE_TOO_LONG`
- `MARKDOWN_STRUCTURE_INVALID`

Warnings may appear together.

## 18. Fatal Parsing Errors

Future implementations use these stable parsing error codes:

- `GENERATED_CONTENT_EMPTY`
- `ARTICLE_HEADLINE_MISSING`
- `ARTICLE_HEADLINE_MULTIPLE`
- `ARTICLE_BODY_MISSING`
- `UNSUPPORTED_GENERATED_FORMAT`
- `GENERATED_ARTICLE_INVALID`

Fatal errors must stop parsing. Exception classes are not defined yet.

## 19. Empty Content Policy

If `GenerationResult.content` is empty or whitespace-only, raise:

`GENERATED_CONTENT_EMPTY`

The parser must not fabricate content.

## 20. Headline Validation

Parsing must fail when:

- no H1 headline exists
- more than one H1 headline exists
- the H1 headline is empty

Do not downgrade these failures to warnings in the MVP.

## 21. Body Validation

Parsing must fail when body content is empty after the headline.

A headline-only response is not a valid article.

## 22. Disallowed Output Detection

Detect and warn when output contains:

- fenced code blocks
- JSON-like object output
- YAML document output
- XML document output
- model commentary before or after the article
- `إليك المقال`
- `بالطبع`
- `سأقوم`
- `تم إنشاء المقال`
- `Here is the article`

The parser must not remove commentary in the MVP.

## 23. Structural Validation Against Strategy

Read structural flags from `EditorialStrategy` and validate:

- headings
- bullets
- tables
- FAQ
- timeline

If a disabled structure appears:

- preserve content
- add the corresponding warning
- do not rewrite the article

## 24. Length Validation

Compare `word_count` with `GenerationPrompt.target_word_count` using a tolerance
of ±20%.

If the count is below tolerance, add `ARTICLE_TOO_SHORT`.

If the count is above tolerance, add `ARTICLE_TOO_LONG`.

Exceptions:

- Accuracy remains more important than length.
- Length warnings are not fatal.
- `VERY_SHORT` articles may fall below tolerance when source material is thin.
- The parser does not pad or shorten content.

## 25. Reason Codes

- `ARTICLE_MARKDOWN_PARSED`
- `ARTICLE_HEADLINE_EXTRACTED`
- `ARTICLE_BODY_EXTRACTED`
- `ARTICLE_STRUCTURE_DETECTED`
- `ARTICLE_WORD_COUNT_CALCULATED`
- `ARTICLE_STRATEGY_STRUCTURE_CHECKED`
- `ARTICLE_LENGTH_CHECKED`
- `ARTICLE_INTERNAL_LABEL_CHECKED`
- `ARTICLE_DISALLOWED_OUTPUT_CHECKED`

## 26. Determinism

Identical inputs must produce identical `ParsedArticle` values.

Do not use:

- timestamps
- random IDs
- LLM calls
- provider metadata
- external services
- nondeterministic ordering

## 27. Security

- Generated output is untrusted.
- Do not execute code blocks.
- Do not render or execute embedded scripts.
- Do not follow links.
- Do not interpret HTML as executable content.
- Parsing must operate on text only.
- HTML sanitization belongs to a later publication layer.

## 28. Non-Goals

- No article rewriting
- No grammar correction
- No fact verification
- No style improvement
- No SEO generation
- No quality scoring
- No publication decision
- No HTML rendering
- No sanitization for final publication
- No LLM repair
- No automatic retry
- No provider calls

## 29. MVP Scope

For the first MVP:

- Parse one Markdown article.
- Extract one headline.
- Extract body Markdown.
- Detect H2 headings.
- Detect paragraphs.
- Detect bullets.
- Count tables.
- Detect FAQ.
- Detect timeline.
- Calculate word count.
- Validate allowed structures.
- Return warnings and reason codes.
- Do not rewrite output.

## 30. Acceptance Criteria

The future implementation must:

- receive one `GenerationResult`
- receive one `GenerationPrompt`
- receive one `EditorialPlanningResult`
- return exactly one `ParsedArticle`
- preserve generated wording
- require exactly one H1 headline
- require a non-empty body
- normalize line endings deterministically
- detect headings, paragraphs, bullets, tables, FAQ, and timeline
- detect exposed internal labels
- detect disallowed output formats
- validate structural flags against strategy
- validate target length with tolerance
- return stable warnings
- return stable reason codes
- make no AI or network calls
