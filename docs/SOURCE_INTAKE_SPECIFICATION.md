# Source Intake Specification

## Purpose

Describe the responsibility of the Source Intake layer.

State clearly that it is responsible only for accepting,
validating and normalizing incoming source material.

It must not perform:

- editorial decisions
- article generation
- rewriting
- SEO
- prompting

## Supported Input Types

Include:

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

title

body

source_name

## Optional Fields

source_url

published_at

language

country

author

images

attachments

category

tags

## Validation Rules

Document:

- missing title
- missing body
- unsupported language
- duplicated source
- empty content
- malformed URL

## Normalization Rules

Document:

- whitespace normalization
- HTML removal
- unicode normalization
- newline normalization
- metadata cleanup

## Output

State that Source Intake returns exactly one object:

NormalizedSource

## Non Goals

State explicitly:

No AI.

No editorial logic.

No fact extraction.

No classification.

No prompt generation.

## Future Extensions

RSS

Crawler

API

CMS

Webhook