# Batch 03 Compositional Semantic Diagnostic

## Summary

Cases:
3

Required Relationships Passed:
3/3

Required Primary Domains Passed:
3/3

Required Secondary Domains Passed:
1/1

Required Suppressions Passed:
3/3

Provenance Valid:
3/3

Unexpected Primary Domains:
0

## Case 024

Primary Domain Candidates:
PRIMARY_DOMAIN_HEALTH

Secondary Domain Candidates:
SECONDARY_DOMAIN_TECHNOLOGY

Format Support:
None

Format Suppression:
None

Intent Support:
None

Warnings:
None

### Relationships

- [SECTION:HEADLINE] [SENTENCE:0] [TYPE:METHOD_APPLIED_TO_SUBJECT] [STRENGTH:STRONG]
  Subject: METHOD = "الذكاء الاصطناعي"
  Object: PRIMARY_SUBJECT = "تشخيص أورام السرطان المبكرة"
  Reason: METHOD_DOMAIN_SUBJECT_COMPOSITION
  Evidence Indexes: 0
  Supports: PRIMARY_DOMAIN_HEALTH, SECONDARY_DOMAIN_TECHNOLOGY
  Suppresses: PRIMARY_DOMAIN_TECHNOLOGY

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTOR_PERFORMS_ACTION] [STRENGTH:MEDIUM]
  Subject: ACTOR = "فريق أبحاث بريطاني"
  Object: ACTION = "طور"
  Reason: ACTOR_ACTION_COMPOSITION
  Evidence Indexes: 1
  Supports: None
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "طور"
  Object: OBJECT = "خوارزمية"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_TECHNOLOGY
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:METHOD_APPLIED_TO_SUBJECT] [STRENGTH:STRONG]
  Subject: METHOD = "خوارزمية"
  Object: PRIMARY_SUBJECT = "الصور الطبية"
  Reason: METHOD_DOMAIN_SUBJECT_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_HEALTH, SECONDARY_DOMAIN_TECHNOLOGY
  Suppresses: PRIMARY_DOMAIN_TECHNOLOGY

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
YES

required_suppression_present:
YES

unexpected_primary_domain_present:
NO

provenance_valid:
YES

## Case 025

Primary Domain Candidates:
PRIMARY_DOMAIN_HEALTH

Secondary Domain Candidates:
None

Format Support:
None

Format Suppression:
None

Intent Support:
None

Warnings:
None

### Relationships

- [SECTION:LEAD] [SENTENCE:0] [TYPE:AUTHORITY_ACTS_ON_SUBJECT] [STRENGTH:STRONG]
  Subject: AUTHORITY = "وزارة الصحة والسكان"
  Object: PRIMARY_SUBJECT = "الخدمات الطبية والفحوصات المجانية"
  Reason: AUTHORITY_DOMAIN_SUBJECT_COMPOSITION
  Evidence Indexes: 1
  Supports: PRIMARY_DOMAIN_HEALTH
  Suppresses: PRIMARY_DOMAIN_GOVERNMENT

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "أعلنت"
  Object: OBJECT = "الخدمات الطبية والفحوصات المجانية"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: 0
  Supports: PRIMARY_DOMAIN_HEALTH
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "تقديم"
  Object: OBJECT = "الخدمات الطبية والفحوصات المجانية"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_HEALTH
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
N-A

required_suppression_present:
YES

unexpected_primary_domain_present:
NO

provenance_valid:
YES

## Case 029

Primary Domain Candidates:
PRIMARY_DOMAIN_EDUCATION

Secondary Domain Candidates:
None

Format Support:
None

Format Suppression:
None

Intent Support:
None

Warnings:
None

### Relationships

- [SECTION:LEAD] [SENTENCE:0] [TYPE:AUTHORITY_ACTS_ON_SUBJECT] [STRENGTH:STRONG]
  Subject: AUTHORITY = "وزارة التعليم العالي والبحث العلمي"
  Object: PRIMARY_SUBJECT = "الجامعات"
  Reason: AUTHORITY_DOMAIN_SUBJECT_COMPOSITION
  Evidence Indexes: 1, 2, 3
  Supports: PRIMARY_DOMAIN_EDUCATION
  Suppresses: PRIMARY_DOMAIN_GOVERNMENT

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "أعلنت"
  Object: OBJECT = "التعليم العالي"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: 0, 2
  Supports: PRIMARY_DOMAIN_EDUCATION
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "تحقيق"
  Object: OBJECT = "الجامعات"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_EDUCATION
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
N-A

required_suppression_present:
YES

unexpected_primary_domain_present:
NO

provenance_valid:
YES
