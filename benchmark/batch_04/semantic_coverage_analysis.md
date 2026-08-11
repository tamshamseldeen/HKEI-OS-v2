# Batch 04 Semantic Coverage Failure Analysis

## Summary

Cases:
10

Cases With Contextual Evidence:
7

Cases With Semantic Relationships:
1

Cases With Primary Semantic Domains:
0

Cases With Semantic Format Support:
0

### Failure Class Counts

CONTEXTUAL_EVIDENCE_MISSING:
3

CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED:
6

SEMANTIC_RELATIONSHIP_PRESENT_WITHOUT_DOMAIN:
1

SEMANTIC_DOMAIN_PRESENT_BUT_NOT_RECORDED_AS_USED:
0

DOMAIN_MODEL_COVERAGE_GAP:
10

FORMAT_SEMANTIC_COVERAGE_GAP:
4

## Case Diagnostics

### Case 031

Previous Matches:
Topic=True; Format=True; Intent=True; Full=True

Contextual Item Count:
3

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=2, WARNING=0, ATTRIBUTION=0, CLAIM=0, PREDICTION=0, UNCERTAINTY=1, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
FORMAT_ANALYSIS

Contextual Intent Support:
INTENT_UNDERSTAND_IMPACT

Contextual Claim Support:
CLAIM_UNCERTAIN

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED, DOMAIN_MODEL_COVERAGE_GAP

Architectural Observations:
- Persisted case 031 is weather reporting, not the specified security-authority/cross-border-attack scenario.
- The contextual layer exposed uncertainty and consequence cues but no domain-bearing subject, actor, action, or authority evidence, so no security-event composition was possible.

#### Contextual Evidence by Role

- CONSEQUENCE: CONSEQUENCE_CONTEXT_PATTERN; CONSEQUENCE_CONTEXT_PATTERN
- UNCERTAINTY: UNCERTAINTY_CONTEXT_PATTERN

#### Semantic Relationships

None

### Case 032

Previous Matches:
Topic=True; Format=True; Intent=True; Full=True

Contextual Item Count:
2

Contextual Role Counts:
SUBJECT=0, ACTOR=1, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=1, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
TOPIC_BUSINESS

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
CLAIM_ATTRIBUTED

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED, DOMAIN_MODEL_COVERAGE_GAP

Architectural Observations:
- Persisted case 032 is cement-price reporting, not the specified criminal/legal conviction and disputed-family-claim scenario.
- Attribution and a generic business actor were exposed, but they did not form a compositional relationship or domain candidate.

#### Contextual Evidence by Role

- ACTOR: GENERIC_BUSINESS_TOKEN
- ATTRIBUTION: ATTRIBUTION_SIGNAL

#### Semantic Relationships

None

### Case 033

Previous Matches:
Topic=False; Format=False; Intent=False; Full=False

Contextual Item Count:
0

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=0, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
None

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_MISSING, DOMAIN_MODEL_COVERAGE_GAP, FORMAT_SEMANTIC_COVERAGE_GAP

Architectural Observations:
- Persisted case 033 is sports-training reporting, not the specified executive citizenship/immigration action and constitutional challenge.
- No contextual evidence was extracted; consequently both domain composition and format composition were absent.

#### Contextual Evidence by Role

None

#### Semantic Relationships

None

### Case 034

Previous Matches:
Topic=True; Format=True; Intent=True; Full=True

Contextual Item Count:
1

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=1, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
CLAIM_ATTRIBUTED

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED, DOMAIN_MODEL_COVERAGE_GAP

Architectural Observations:
- Persisted case 034 is a sports schedule, not the specified war/security pressure and resource-constraint analysis.
- The editorial result matched despite semantic non-use; the only contextual item was attribution and it produced no relationship or domain.

#### Contextual Evidence by Role

- ATTRIBUTION: ATTRIBUTION_SIGNAL

#### Semantic Relationships

None

### Case 035

Previous Matches:
Topic=False; Format=False; Intent=False; Full=False

Contextual Item Count:
3

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=1, WARNING=0, ATTRIBUTION=2, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
FORMAT_ANALYSIS

Contextual Intent Support:
INTENT_UNDERSTAND_IMPACT

Contextual Claim Support:
CLAIM_ATTRIBUTED

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED, DOMAIN_MODEL_COVERAGE_GAP, FORMAT_SEMANTIC_COVERAGE_GAP

Architectural Observations:
- Persisted case 035 is a vehicle price/specification guide, not the specified military restructuring and unmanned-systems explainer.
- Attribution and consequence evidence remained uncomposed, leaving both domain and explanatory-format support empty.

#### Contextual Evidence by Role

- CONSEQUENCE: CONSEQUENCE_CONTEXT_PATTERN
- ATTRIBUTION: ATTRIBUTION_SIGNAL; ATTRIBUTION_SIGNAL

#### Semantic Relationships

None

### Case 036

Previous Matches:
Topic=True; Format=False; Intent=True; Full=False

Contextual Item Count:
4

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=2, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=0, CLAIM=0, PREDICTION=0, UNCERTAINTY=2, INTERPRETATION=0

Contextual Topic Support:
TOPIC_GOVERNMENT

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
CLAIM_UNCERTAIN

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED, DOMAIN_MODEL_COVERAGE_GAP, FORMAT_SEMANTIC_COVERAGE_GAP

Architectural Observations:
- Persisted case 036 is preventive health guidance, not the specified AI/biological-science development and dual-use analysis.
- Authority and uncertainty evidence produced no relationships or analysis-format support; the requested biological-science structure is therefore not tested by this source.

#### Contextual Evidence by Role

- AUTHORITY: GENERIC_GOVERNMENT_TOKEN; GENERIC_GOVERNMENT_TOKEN
- UNCERTAINTY: UNCERTAINTY_CONTEXT_PATTERN; UNCERTAINTY_CONTEXT_PATTERN

#### Semantic Relationships

None

### Case 037

Previous Matches:
Topic=False; Format=True; Intent=True; Full=False

Contextual Item Count:
0

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=0, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
None

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_MISSING, DOMAIN_MODEL_COVERAGE_GAP

Architectural Observations:
- Persisted case 037 is a health-sector memorandum, not the specified university/government institutional conflict and protests.
- No contextual evidence was extracted, so no primary-domain competition was represented semantically.

#### Contextual Evidence by Role

None

#### Semantic Relationships

None

### Case 038

Previous Matches:
Topic=False; Format=False; Intent=True; Full=False

Contextual Item Count:
1

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=1, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
CLAIM_ATTRIBUTED

Semantic Relationship Count:
1

Semantic Relationship Types:
ACTION_TARGETS_OBJECT

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
None

Failure Classes:
SEMANTIC_RELATIONSHIP_PRESENT_WITHOUT_DOMAIN, DOMAIN_MODEL_COVERAGE_GAP, FORMAT_SEMANTIC_COVERAGE_GAP

Architectural Observations:
- Persisted case 038 is Ebola outbreak reporting, not the specified NATO/Russia intelligence estimate and possible future attack.
- One action-to-object relationship supported health, but that support was not promoted to a primary domain candidate and no format or intent support was produced.

#### Contextual Evidence by Role

- ATTRIBUTION: ATTRIBUTION_SIGNAL

#### Semantic Relationships

- Type: ACTION_TARGETS_OBJECT
  Source: LEAD sentence 0
  Subject: ACTION = "دعا"
  Object: OBJECT = "الأمراض"
  Strength: MEDIUM
  Reason Code: ACTION_DOMAIN_OBJECT_COMPOSITION
  Supports: PRIMARY_DOMAIN_HEALTH
  Suppresses: None

### Case 039

Previous Matches:
Topic=True; Format=True; Intent=True; Full=True

Contextual Item Count:
0

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=0, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=0, CLAIM=0, PREDICTION=0, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
None

Contextual Format Support:
None

Contextual Intent Support:
None

Contextual Claim Support:
None

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_MISSING, DOMAIN_MODEL_COVERAGE_GAP

Architectural Observations:
- Persisted case 039 is gold-price reporting and matched ECONOMY without contextual items, relationships, or semantic candidates.
- The match is therefore a control showing that the prior workflow prediction was sufficient without recorded contextual or semantic contribution; this diagnostic does not invoke the topic classifier to attribute a more specific path.

#### Contextual Evidence by Role

None

#### Semantic Relationships

None

### Case 040

Previous Matches:
Topic=True; Format=True; Intent=True; Full=True

Contextual Item Count:
3

Contextual Role Counts:
SUBJECT=0, ACTOR=0, ACTION=0, AUTHORITY=2, AFFECTED_AUDIENCE=0, REQUIREMENT=0, DEADLINE=0, RESULT=0, CONSEQUENCE=0, WARNING=0, ATTRIBUTION=0, CLAIM=0, PREDICTION=1, UNCERTAINTY=0, INTERPRETATION=0

Contextual Topic Support:
TOPIC_GOVERNMENT

Contextual Format Support:
FORMAT_ANALYSIS

Contextual Intent Support:
INTENT_UNDERSTAND_IMPACT

Contextual Claim Support:
CLAIM_UNCERTAIN

Semantic Relationship Count:
0

Semantic Relationship Types:
None

Primary Domain Candidates:
None

Secondary Domain Candidates:
None

Semantic Format Support:
None

Semantic Format Suppression:
None

Semantic Intent Support:
None

Semantic Suppressions:
None

Semantic Warning Codes:
SEMANTIC_COMPOSITION_EMPTY

Failure Classes:
CONTEXTUAL_EVIDENCE_PRESENT_BUT_UNCOMPOSED, DOMAIN_MODEL_COVERAGE_GAP

Architectural Observations:
- Persisted case 040 is petroleum/gas production reporting, not the specified CRIME control scenario.
- The matched ECONOMY result coexisted with authority and prediction evidence that remained uncomposed, showing the prior prediction did not require recorded semantic evidence.

#### Contextual Evidence by Role

- AUTHORITY: GENERIC_GOVERNMENT_TOKEN; GENERIC_GOVERNMENT_TOKEN
- PREDICTION: PREDICTION_CONTEXT_PATTERN

#### Semantic Relationships

None

## Why Semantic Evidence Used Was Zero

The validation usage metric counts primary or secondary domain candidates, semantic format support, or semantic intent support. All four were empty for all ten cases. Seven cases had contextual evidence, but six produced no relationship; case 038 produced one relationship whose health support was not promoted to a domain candidate. Thus the zero reflects observed semantic outputs, not a workflow/reporting omission of an existing domain candidate.

## Cross-Case Architectural Findings

### Context extraction coverage

Three cases had no contextual items; the other seven mostly exposed generic attribution, authority, uncertainty, consequence, or prediction cues.

### Semantic composition coverage

Six context-bearing cases remained uncomposed; only case 038 produced a relationship.

### Domain modeling coverage

No case produced a primary or secondary domain candidate; relationship-level health support in 038 was not promoted.

### Format modeling coverage

No case produced semantic format support or suppression, including all four prior format mismatches.

### Workflow/integration behavior

The prior usage calculation accurately reported zero under its documented candidate/support criteria.

### Failure scope

The evidence shows a mixture of extraction, composition, domain-model, and format-model coverage gaps. Topic and format failures precede and are independent of ReaderIntentClassifierV2.

### Corpus/specification mismatch

The HKEI-093 case scenarios do not describe the persisted Batch 04 sources, so those requested conceptual structures cannot be evaluated from this corpus.

## Recommended Next Architecture

- Add domain-bearing event/object composition that can promote relationship support into explicit primary and secondary domain candidates.
- Expand reusable security-event, legal-policy, institutional-conflict, military-transformation, biological-science, and intelligence-estimate composition classes only against correctly registered source material.
- Add explanatory-framing and analysis-framing composition based on structural relationships rather than case-specific terms.
- Keep workflow usage accounting aligned with relationship-level supports as well as promoted domain and format candidates.
- Resolve the mismatch between the persisted Batch 04 corpus and the case scenarios before using those scenarios to judge architectural coverage.
