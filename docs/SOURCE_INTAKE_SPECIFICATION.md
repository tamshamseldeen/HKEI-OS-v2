# Source Intake Specification

## Purpose

The Source Intake layer is responsible only for accepting, validating, and normalizing incoming source material.

It must not perform:

- editorial decisions
- article generation
- rewriting
- SEO
- prompting

## Supported Input Types

- Raw text
- Headline + body
- URL
- RSS item
- PDF
- DOCX
- Press release
- Government statement
- Social media post

## Required Fields

- `title`
- `body`
- `source_name`

## Optional Fields

- `source_url`
- `published_at`
- `language`
- `country`
- `author`
- `images`
- `attachments`
- `category`
- `tags`

## Validation Rules

- Missing title: reject input when `title` is absent.
- Missing body: reject input when `body` is absent.
- Unsupported language: reject input when its language is not supported.
- Duplicated source: reject input that duplicates an already accepted source.
- Empty content: reject input whose title or body contains no meaningful content.
- Malformed URL: reject input when a supplied `source_url` is not a valid URL.

## Normalization Rules

- Whitespace normalization: replace inconsistent spacing with consistent whitespace.
- HTML removal: remove HTML markup from textual content.
- Unicode normalization: convert text to a consistent Unicode representation.
- Newline normalization: convert line endings to a consistent newline format.
- Metadata cleanup: trim and standardize supplied metadata values.

## Output

Source Intake returns exactly one object: `NormalizedSource`.

## Non Goals

No AI.

No editorial logic.

No fact extraction.

No classification.

No prompt generation.

## Future Extensions

- RSS
- Crawler
- API
- CMS
- Webhook
