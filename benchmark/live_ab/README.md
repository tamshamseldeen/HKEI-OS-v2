# Live Editorial A/B Pilot

## Purpose

This harness measures editorial outcomes from the complete HKEI pipeline: raw source → writing analysis → writer packet → writing → final article → blind A/B adjudication → aggregate report. It locates failures without changing the frozen candidate prompt.

Contract validation asks whether interfaces, schemas, and safety rules work. Editorial outcome validation asks whether an article is accurate, useful, appropriately structured, and publishable. Passing one does not imply passing the other.

## Pipeline Architecture

Case files identify source inputs. Baseline artifacts remain under `baseline/`; Prompt v1.1 analysis, packets, and articles remain under `candidate_v1_1/`. Adjudicators see only `ARTICLE_X` and `ARTICLE_Y`. A separate mapping file records which system produced X and Y. Reports aggregate validated, completed UNSEEN cases only.

## Unseen and Regression Cases

`UNSEEN` cases measure live A/B performance. `REGRESSION` cases protect known failure classes and are excluded from unseen win-rate calculations. Supported regression categories are:

1. Market / price: prevent unsupported session labels, fee generalization, and market inference.
2. Political / original attribution: preserve the central policy angle and distinguish the carrier publisher from the original reporting source.
3. Legal / service: prioritize primary legal authority, preserve legal status, and avoid turning a verification date into an expiry date.

These are category-level safeguards, not hard-coded answers.

## Writer Packet Evaluation

WP01–WP08 score source identity, story kernel, material fact recall, fact and source-role classification, temporal control, forbidden inferences, and context discipline. Each dimension is FAIL=0, PARTIAL=1, or PASS=2; maximum score is 16. Evidence must be externally auditable and must not contain hidden reasoning.

## Final Article Evaluation

FA01–FA12 score angle preservation, factual accuracy and recall, unsupported claims, attribution, time, source independence, external context, Arabic quality, reader value, SEO metadata, and proportionality. Each dimension is 0–2; maximum score is 24.

## Critical Failures

CF01–CF08 cover hallucinated material facts, wrong entities, number distortion, angle drift, false original attribution, historical/current-time mixing, source substitution, and material legal/medical misstatement. Any critical failure blocks `PUBLISH_AS_IS`.

## Editorial Readiness

- `PUBLISH_AS_IS`: no material editorial intervention is required.
- `MINOR_EDIT`: only small language, repetition, headline, or non-material presentation edits are required.
- `MAJOR_EDIT`: material intervention involving angle, facts, attribution, context, or structure is required.
- `REJECT`: output is unsafe or fundamentally unreliable, including serious hallucination, source substitution, material distortion, or high-severity legal/medical error.

## Added Value

- `AV3_SUBSTANTIAL_VALUE`: meaningfully improves understanding, utility, synthesis, or editorial clarity.
- `AV2_MODERATE_VALUE`: provides a useful but non-transformative improvement.
- `AV1_MINIMAL_VALUE`: adds limited reader value beyond presentation changes.
- `AV0_NO_ADDED_VALUE`: adds no meaningful reader/editorial value or merely differs textually.

## Blind A/B Methodology

Adjudication payloads expose `ARTICLE_X` and `ARTICLE_Y`, never baseline, candidate, prompt version, or v1.1 identity. Outcomes are `X_WINS`, `Y_WINS`, `TIE`, or `BOTH_FAIL`, with HIGH/MEDIUM/LOW confidence and structured reason codes. Store each `case_NNN.adjudication.json` beside a separate `case_NNN.mapping.json`. The runner uses the manifest seed to provide reproducible assignment through `blind_mapping()`.

## Failure Taxonomy

Each case may contain multiple failures. Origins are `SOURCE_EXTRACTION`, `ANALYSIS`, `VERIFICATION`, `WRITER_PACKET`, `WRITING`, `SEO_METADATA`, or `FORMAT`. Types are `FACT`, `ANGLE`, `ATTRIBUTION`, `TEMPORAL`, `CONTEXT`, `LANGUAGE`, `SEO`, or `PROPORTIONALITY`.

## Gate Thresholds

Defaults require candidate decisive win rate ≥70%, critical failure rate ≤5%, publish-as-is plus minor-edit rate ≥85%, no false-original-attribution or material-number-distortion critical failures, average added value ≥2.0, and no systematic category failure. TIE and BOTH_FAIL are excluded from the decisive denominator.

A category is systematically failing when it has at least two evaluated cases and at least 50% require MAJOR_EDIT/REJECT or at least 50% contain a critical failure. Both values are configurable.

## Adding Cases

Add one JSON object per case under `cases/`, validate it against `schemas/case.schema.json`, ensure `case_id` is unique, and update manifest counts. Provide either `source_url` or `source_text`; never store a gold output. `expected_topic` validates source identity only.

## Running and Reporting

Run `python examples/run_live_ab_pilot.py`. The runner validates the manifest, cases, adjudications, mappings, and rubrics, then writes `reports/pilot_20_summary.json` and `.md`. An empty or incomplete pilot reports `INCOMPLETE` and does not invent metrics.

## Frozen Prompt Rule

Prompt v1.1 and frozen commit `4b2b42472aa95f85d5cdf4a0a8c0377160921104` must remain unchanged during the pilot. Prompt tuning during collection would confound comparisons and invalidate the shared candidate condition.
