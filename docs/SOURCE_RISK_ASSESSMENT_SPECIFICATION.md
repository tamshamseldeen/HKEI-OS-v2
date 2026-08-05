# HKEI OS v2 — Source and Risk Assessment Specification

## 1. Purpose

The Source and Risk Assessment layer receives one validated `NormalizedSource` and determines:

- source availability
- source attribution quality
- verification status
- editorial risk level
- required warnings
- whether generation may continue

This layer does not:

- rewrite the source
- generate an article
- create headlines
- perform SEO work
- build prompts
- claim external verification unless verification actually occurred

## 2. Input

The layer accepts exactly one `NormalizedSource`.

The available fields are:

- `title`
- `body`
- `source_name`
- `source_url`
- `published_at`
- `language`
- `country`
- `author`
- `images`
- `attachments`
- `category`
- `tags`

## 3. Assessment Output

The layer will return one future object named `SourceRiskAssessment`.

The object will contain these fields:

- `source_status`
- `verification_status`
- `risk_level`
- `risk_topics`
- `warnings`
- `requires_official_source`
- `requires_human_review`
- `generation_allowed`
- `reason_codes`

Python types are not defined at this stage.

## 4. Source Status

Use these exact values:

- `IDENTIFIED`
- `PARTIALLY_IDENTIFIED`
- `UNIDENTIFIED`

`IDENTIFIED`:
The `source_name` exists and the `source_url` exists.

`PARTIALLY_IDENTIFIED`:
The `source_name` exists but the `source_url` is missing.

`UNIDENTIFIED`:
The source cannot be meaningfully attributed.

A source name alone does not prove reliability.

## 5. Verification Status

Use these exact values:

- `UNVERIFIED`
- `SOURCE_PROVIDED`
- `OFFICIAL_SOURCE_PROVIDED`
- `MULTIPLE_SOURCES_PROVIDED`
- `VERIFIED_EXTERNALLY`

`UNVERIFIED`:
No usable attribution or supporting source is available.

`SOURCE_PROVIDED`:
A source is supplied, but HKEI has not independently verified it.

`OFFICIAL_SOURCE_PROVIDED`:
The supplied material is explicitly attributed to an official authority.

`MULTIPLE_SOURCES_PROVIDED`:
More than one distinct source supports the material.

`VERIFIED_EXTERNALLY`:
A separate verification process has actually confirmed the claim.

HKEI must never label content `VERIFIED_EXTERNALLY` unless an external verification operation was completed successfully.

## 6. Risk Levels

Use these exact values:

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

`LOW`:
Ordinary content with limited potential for serious harm.

`MEDIUM`:
Content where errors could mislead readers or damage reputation but are unlikely to cause immediate serious harm.

`HIGH`:
Content involving health, law, finance, government services, immigration, public safety, elections, allegations, crime, emergencies, or other consequential decisions.

`CRITICAL`:
Content involving immediate danger, emergency instructions, active violence, self-harm, life-threatening medical guidance, or claims that could cause severe harm if wrong.

## 7. High-Risk Topics

- Medical diagnosis or treatment
- Medication and dosage
- Legal rights and obligations
- Financial products and investment claims
- Taxes and government fees
- Government benefits and eligibility
- Immigration and residency
- Public safety and emergency instructions
- Elections and voting procedures
- Crime allegations
- Defamation-sensitive claims
- Active conflict or violence
- Self-harm
- Missing persons
- Children’s safety
- Product recalls
- Cybersecurity incidents
- Identity theft and fraud warnings

## 8. Deterministic Risk Signals

Deterministic rules should detect explicit terms and metadata associated with high-risk topics.

Examples may include:

- medicine names
- dosage units
- court or legal terminology
- currency and investment terminology
- visa or residency terminology
- emergency terminology
- allegations against named persons
- voting dates or procedures

Keyword detection alone is not sufficient for a final editorial judgment.

## 9. Required Warnings

The warning codes are:

- `SOURCE_URL_MISSING`
- `SOURCE_UNIDENTIFIED`
- `CONTENT_UNVERIFIED`
- `OFFICIAL_SOURCE_REQUIRED`
- `HIGH_RISK_CONTENT`
- `CRITICAL_RISK_CONTENT`
- `HUMAN_REVIEW_REQUIRED`
- `EXTERNAL_VERIFICATION_REQUIRED`
- `ALLEGATION_REQUIRES_ATTRIBUTION`
- `TIME_SENSITIVE_INFORMATION`
- `MISSING_PUBLICATION_DATE`

Warnings must be machine-readable and may appear together.

## 10. Generation Decision

`generation_allowed` may be `True` or `False`.

Generation may continue when:

- the source is usable
- the content can be written with clear attribution
- uncertainty is preserved
- required warnings are attached

Generation must stop when:

- critical claims have no usable attribution
- the source is empty or unusable
- the requested output would require invented facts
- immediate-harm instructions cannot be verified
- allegations cannot be safely attributed
- required official confirmation is unavailable for critical content

`HIGH` risk does not always mean automatic rejection.

It may mean:

- stronger attribution
- restricted wording
- mandatory warnings
- human review
- publication decision of Needs Revision

## 11. Human Review Policy

Human review is mandatory when:

- `risk_level` is `HIGH` or `CRITICAL`
- allegations involve identifiable people or organizations
- medical, legal, financial, immigration, government-service, or emergency guidance is included
- official verification is required but incomplete
- the assessment contains conflicting signals

## 12. Non-Goals

- No article generation
- No headline generation
- No rewriting
- No automatic web search
- No source crawling
- No legal determination
- No medical diagnosis
- No financial recommendation
- No final publication approval

## 13. MVP Scope

For the first MVP:

- Assess one `NormalizedSource`.
- Use deterministic rules only.
- Do not browse the web.
- Do not contact external verification services.
- Return risk, warnings, and generation eligibility.
- Preserve all uncertainty.
- Require human review for `HIGH` and `CRITICAL` content.

## 14. Acceptance Criteria

The specification is satisfied when the future implementation can:

- receive one `NormalizedSource`
- assign one source status
- assign one verification status
- assign one risk level
- return zero or more warnings
- state whether an official source is required
- state whether human review is required
- state whether generation may continue
- explain decisions using stable reason codes
- never claim verification that did not occur
