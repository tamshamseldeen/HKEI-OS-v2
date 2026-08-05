# FACT EXTRACTION SPECIFICATION

## 1. Purpose

The Fact Extraction layer converts one `NormalizedSource` into structured editorial facts.

It does not:

- generate articles
- summarize
- rewrite
- classify article type
- make editorial decisions
- evaluate SEO

## 2. Input

The layer accepts exactly one `NormalizedSource`.

## 3. Output

The layer returns exactly one future object: `ExtractedFacts`.

## 4. Fact Types

### Core Fact

A Core Fact is a statement directly supported by the source that can be restated without inference.

### Claim

A Claim is a statement asserted by a source that has not been independently verified and must retain its attribution.

### Quote

A Quote is wording explicitly attributed to a speaker or source and preserved as it appears in the source material.

### Named Person

A Named Person is an explicitly identified individual mentioned in the source, including the name and any directly supported role or title.

### Organization

An Organization is an explicitly named company, institution, association, or other organized body mentioned in the source.

### Government Entity

A Government Entity is an explicitly named ministry, agency, authority, court, legislature, municipality, or other public body.

### Location

A Location is a place identified in the source, such as a city, district, street, venue, or geographic feature.

### Country

A Country is a nation or sovereign territory explicitly identified in the source.

### Date

A Date is an explicit calendar date or directly stated relative date whose wording and context are preserved.

### Time

A Time is an explicit time of day, deadline, or time reference stated in the source.

### Number

A Number is a numeric value stated in the source, retained with its original precision, unit, and context.

### Percentage

A Percentage is a proportional value expressed as a percentage in the source and preserved exactly.

### Currency

A Currency is a monetary amount or currency reference stated in the source, including its exact value and denomination.

### Law / Regulation

A Law / Regulation is an explicitly named or cited statute, regulation, decree, rule, or other legal instrument.

### Product

A Product is an explicitly named commercial, medical, digital, or physical offering mentioned in the source.

### Event

An Event is a directly described occurrence, announcement, meeting, incident, launch, decision, or scheduled activity.

### Unknown Information

Unknown Information is a material detail that the source leaves missing, unnamed, unspecified, or unpublished and that must not be inferred.

## 5. Core Facts

Core facts are statements directly supported by the source and safe to restate.

They must not contain inference.

## 6. Claims

Claims are statements asserted by a source but not independently verified.

Claims must preserve attribution.

## 7. Quotes

Quotes must preserve wording when possible.

Never invent quotations.

Never reconstruct quotations.

## 8. Numbers

Numbers include:

- counts
- money
- fines
- percentages
- measurements
- durations

Numbers must be preserved exactly.

## 9. Unknown Information

Missing information should be explicitly represented instead of inferred.

Examples include:

- unnamed people
- unknown dates
- unknown locations
- unpublished values

## 10. Extraction Rules

- Extract only supported facts.
- Preserve uncertainty.
- Preserve attribution.
- Preserve numeric precision.
- Preserve official terminology.

## 11. Non-Goals

No summarization.

No hallucination.

No interpretation.

No sentiment analysis.

No rewriting.

No editorial opinion.

## 12. MVP Scope

The MVP extracts only deterministic facts.

No AI.

No NLP libraries.

No external services.

## 13. Acceptance Criteria

A future implementation must be able to:

- identify factual statements
- separate claims from facts
- identify quotations
- identify numbers
- identify dates
- identify entities
- identify missing information
- preserve attribution
- never invent facts
