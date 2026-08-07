# Batch 03 Compositional Context Failure Analysis

## Summary

Cases Analyzed:
8

VOCABULARY_GAP:
0

COMPOSITIONAL_RELATIONSHIP_MISSING:
8

AUTHORITY_SUBJECT_CONFUSION:
3

ACTOR_SUBJECT_CONFUSION:
2

METHOD_SUBJECT_CONFUSION:
1

DOMAIN_PRECEDENCE_ERROR:
4

ACTION_STRUCTURE_MISSING:
1

EVENT_DOMAIN_MAPPING_MISSING:
1

FORMAT_ACTION_FALSE_POSITIVE:
1

INSUFFICIENT_CONTEXT_COMPOSITION:
4

## Case Diagnostics

### Case 021

Current Prediction:
Topic=GENERAL; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=GOVERNMENT; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
CLAIM_ATTRIBUTED

Conceptual Roles:
- AUTHORITY: الهيئة القومية للأنفاق
- PRIMARY_SUBJECT: منظومة المونوريل
- ACTION: التشغيل التجريبي
- DOMAIN: public infrastructure, government transport

Missing Relationships:
- Official transport authority operates a public-infrastructure project.
- Operational project object carries the government-transport domain.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- AUTHORITY_SUBJECT_CONFUSION
- INSUFFICIENT_CONTEXT_COMPOSITION

General Fix Candidates:
- Compose institution authority with its acted-on subject instead of treating authority as the subject domain.
- Detect domain-bearing objects and weight them above generic actors or institutions.

### Case 022

Current Prediction:
Topic=GENERAL; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=ECONOMY; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
CLAIM_ATTRIBUTED

Conceptual Roles:
- ACTOR: صندوق النقد الدولي
- PRIMARY_SUBJECT: النمو الاقتصادي
- INDICATOR: الأنشطة غير النفطية, الاستثمار
- DOMAIN: ECONOMY

Missing Relationships:
- Reporting institution describes macroeconomic subject and indicators.
- Economic indicators jointly establish the primary domain.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- ACTOR_SUBJECT_CONFUSION
- INSUFFICIENT_CONTEXT_COMPOSITION

General Fix Candidates:
- Separate actors from the primary subject through action-object composition.
- Detect domain-bearing objects and weight them above generic actors or institutions.

### Case 023

Current Prediction:
Topic=GENERAL; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=POLITICS; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
None

Conceptual Roles:
- ACTOR: الولايات المتحدة, الصين, مسؤولون تجاريون
- ACTION: مفاوضات
- OBJECT: التعرفة والقيود التجارية
- DOMAIN: international politics, diplomacy

Missing Relationships:
- State actors negotiate policy restrictions in an international relationship.
- Diplomatic action is primary while trade is secondary evidence.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- ACTOR_SUBJECT_CONFUSION
- DOMAIN_PRECEDENCE_ERROR

General Fix Candidates:
- Separate actors from the primary subject through action-object composition.
- Resolve candidate domains through contextual competition among authority, actor, method, object, event, and outcome evidence.

### Case 024

Current Prediction:
Topic=TECHNOLOGY; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=HEALTH; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
TOPIC_TECHNOLOGY, TOPIC_SPORTS

Conceptual Roles:
- METHOD: الذكاء الاصطناعي
- PRIMARY_SUBJECT: تشخيص أورام السرطان
- OBJECT: الصور الطبية, الأورام
- DOMAIN: HEALTH

Missing Relationships:
- Technology is the diagnostic method, not the primary subject.
- Medical objects and outcome establish health as the dominant domain.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- METHOD_SUBJECT_CONFUSION
- DOMAIN_PRECEDENCE_ERROR

General Fix Candidates:
- Distinguish a method or tool from the domain-bearing object it is used to examine.
- Detect domain-bearing objects and weight them above generic actors or institutions.
- Resolve candidate domains through contextual competition among authority, actor, method, object, event, and outcome evidence.

### Case 025

Current Prediction:
Topic=GOVERNMENT; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=HEALTH; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
CLAIM_ATTRIBUTED, TOPIC_GOVERNMENT

Conceptual Roles:
- AUTHORITY: وزارة الصحة
- ACTION: تقديم خدمات وفحوصات
- PRIMARY_SUBJECT: health screening, medical services
- DOMAIN: HEALTH

Missing Relationships:
- Government authority supplies services whose objects carry the health domain.
- Institution type should not override the acted-on medical subject.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- AUTHORITY_SUBJECT_CONFUSION
- DOMAIN_PRECEDENCE_ERROR

General Fix Candidates:
- Compose institution authority with its acted-on subject instead of treating authority as the subject domain.
- Detect domain-bearing objects and weight them above generic actors or institutions.
- Resolve candidate domains through contextual competition among authority, actor, method, object, event, and outcome evidence.

### Case 026

Current Prediction:
Topic=GENERAL; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=TECHNOLOGY; Format=SERVICE; Intent=KNOW_ACTION

Observed Contextual Support:
CLAIM_ATTRIBUTED

Conceptual Roles:
- ACTOR: cybersecurity experts
- PRIMARY_SUBJECT: ransomware attacks
- AFFECTED_AUDIENCE: financial institutions, companies
- RECOMMENDED_ACTION: update protection, apply encryption
- DOMAIN: TECHNOLOGY

Missing Relationships:
- Experts direct protective actions to an affected audience.
- Threat, audience, and recommended action jointly support service treatment and action intent.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- ACTION_STRUCTURE_MISSING
- INSUFFICIENT_CONTEXT_COMPOSITION

General Fix Candidates:
- Detect recommended-action structures from adviser, affected audience, and requested action relationships.
- Detect domain-bearing objects and weight them above generic actors or institutions.

### Case 028

Current Prediction:
Topic=GENERAL; Format=STANDARD_NEWS; Intent=GET_UPDATE

Expected:
Topic=WEATHER; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
None

Conceptual Roles:
- ENVIRONMENTAL_CONDITION: heavy monsoon rain
- ACTION: flooding, landslides
- OUTCOME: displacement, evacuation
- DOMAIN: WEATHER

Missing Relationships:
- Environmental condition causes hazardous events and human outcomes.
- The condition-event-outcome chain establishes the weather domain.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- EVENT_DOMAIN_MAPPING_MISSING
- INSUFFICIENT_CONTEXT_COMPOSITION

General Fix Candidates:
- Compose environmental conditions, events, and outcomes into candidate domain evidence.
- Resolve candidate domains through contextual competition among authority, actor, method, object, event, and outcome evidence.

### Case 029

Current Prediction:
Topic=GOVERNMENT; Format=GUIDE; Intent=VERIFY_REQUIREMENTS

Expected:
Topic=EDUCATION; Format=STANDARD_NEWS; Intent=GET_UPDATE

Observed Contextual Support:
CLAIM_ATTRIBUTED, TOPIC_GOVERNMENT

Conceptual Roles:
- AUTHORITY: وزارة التعليم العالي
- PRIMARY_SUBJECT: الجامعات المصرية
- ACTION: international rankings
- DOMAIN: EDUCATION

Missing Relationships:
- Education authority reports an outcome about universities.
- No requirement, deadline, procedure, eligibility, or reader action exists.

Failure Classes:
- COMPOSITIONAL_RELATIONSHIP_MISSING
- AUTHORITY_SUBJECT_CONFUSION
- DOMAIN_PRECEDENCE_ERROR
- FORMAT_ACTION_FALSE_POSITIVE

General Fix Candidates:
- Compose institution authority with its acted-on subject instead of treating authority as the subject domain.
- Detect domain-bearing objects and weight them above generic actors or institutions.
- Add negative format evidence when requirement, deadline, procedure, eligibility, and reader action are absent.

## Cross-Case Architectural Findings

### 1. Authority is being confused with subject
Institution labels can dominate the acted-on domain object.

### 2. Methods/tools are being confused with subject
A prominent method can outrank the domain-bearing object it serves.

### 3. Domain-bearing objects are underweighted
Objects and outcomes do not yet compose into strong candidate domains.

### 4. Event semantics are missing
Condition, event, and outcome relationships are not represented.

### 5. Recommended-action structure is incomplete
Advice is not composed from adviser, audience, threat, and action.

### 6. Format negative evidence is missing
Ordinary institutional news lacks an explicit absence signal for actionable structure.

### 7. Phrase dictionaries do not generalize sufficiently
Independent phrase hits cannot express which entity is acting on which object.

## Proposed Next Architecture

Token Evidence
↓
Phrase Evidence
↓
Local Context Evidence
↓
Compositional Semantic Evidence
↓
Candidate Domain Evidence
↓
Topic / Format / Intent classifiers

Compositional Semantic Evidence should consume relationships between multiple evidence items rather than adding more case-specific keywords.
