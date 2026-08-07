# Batch 03 Expanded Semantic Diagnostic

## Summary

Cases:
5

Required Relationships Passed:
5/5

Required Primary Domains Passed:
5/5

Required Secondary Domains Passed:
1/1

Required Format Support Passed:
1/1

Required Intent Support Passed:
1/1

Provenance Valid:
5/5

Unexpected Primary Domains:
0

## Case 021

Primary Domain Candidates:
PRIMARY_DOMAIN_GOVERNMENT

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

- [SECTION:LEAD] [SENTENCE:0] [TYPE:INSTITUTION_BELONGS_TO_DOMAIN] [STRENGTH:STRONG]
  Subject: AUTHORITY = "الهيئة القومية للأنفاق"
  Object: PRIMARY_SUBJECT = "المونوريل"
  Reason: PUBLIC_INFRASTRUCTURE_DOMAIN_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_GOVERNMENT
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
N-A

required_format_support_present:
N-A

required_intent_support_present:
N-A

unexpected_primary_domain_present:
NO

provenance_valid:
YES

## Case 022

Primary Domain Candidates:
PRIMARY_DOMAIN_ECONOMY

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

- [SECTION:HEADLINE] [SENTENCE:0] [TYPE:INDICATOR_DESCRIBES_DOMAIN] [STRENGTH:STRONG]
  Subject: INDICATOR = "النمو الاقتصادي"
  Object: DOMAIN = "ECONOMY"
  Reason: ECONOMIC_INDICATOR_DOMAIN_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_ECONOMY
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:INDICATOR_DESCRIBES_DOMAIN] [STRENGTH:STRONG]
  Subject: INDICATOR = "نمو الأنشطة غير النفطية"
  Object: DOMAIN = "ECONOMY"
  Reason: ECONOMIC_INDICATOR_DOMAIN_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_ECONOMY
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
N-A

required_format_support_present:
N-A

required_intent_support_present:
N-A

unexpected_primary_domain_present:
NO

provenance_valid:
YES

## Case 023

Primary Domain Candidates:
PRIMARY_DOMAIN_POLITICS

Secondary Domain Candidates:
SECONDARY_DOMAIN_ECONOMY

Format Support:
None

Format Suppression:
None

Intent Support:
None

Warnings:
None

### Relationships

- [SECTION:HEADLINE] [SENTENCE:0] [TYPE:ACTOR_PERFORMS_ACTION] [STRENGTH:STRONG]
  Subject: ACTOR = "واشنطن ووبكين"
  Object: ACTION = "مفاوضات"
  Reason: INTERNATIONAL_NEGOTIATION_DOMAIN_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_POLITICS, SECONDARY_DOMAIN_ECONOMY
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTOR_PERFORMS_ACTION] [STRENGTH:STRONG]
  Subject: ACTOR = "الولايات المتحدة ووالصين"
  Object: ACTION = "اجتماعات رفيعة المستوى"
  Reason: INTERNATIONAL_NEGOTIATION_DOMAIN_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_POLITICS, SECONDARY_DOMAIN_ECONOMY
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
YES

required_format_support_present:
N-A

required_intent_support_present:
N-A

unexpected_primary_domain_present:
NO

provenance_valid:
YES

## Case 026

Primary Domain Candidates:
PRIMARY_DOMAIN_TECHNOLOGY

Secondary Domain Candidates:
None

Format Support:
FORMAT_SERVICE

Format Suppression:
None

Intent Support:
INTENT_KNOW_ACTION

Warnings:
None

### Relationships

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTOR_PERFORMS_ACTION] [STRENGTH:MEDIUM]
  Subject: ACTOR = "خبراء الأمن السيبراني"
  Object: ACTION = "حذر"
  Reason: ACTOR_ACTION_COMPOSITION
  Evidence Indexes: 0
  Supports: None
  Suppresses: None

- [SECTION:LEAD] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "حذر"
  Object: OBJECT = "الأمن السيبراني"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: 0
  Supports: PRIMARY_DOMAIN_TECHNOLOGY
  Suppresses: None

- [SECTION:BODY] [SENTENCE:0] [TYPE:RECOMMENDATION_TARGETS_AUDIENCE] [STRENGTH:STRONG]
  Subject: RECOMMENDED_ACTION = "بضرورة تحديث برامج الحماية"
  Object: AFFECTED_AUDIENCE = "الشركات"
  Reason: RECOMMENDED_ACTION_AUDIENCE_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_TECHNOLOGY, FORMAT_SERVICE, INTENT_KNOW_ACTION
  Suppresses: None

- [SECTION:BODY] [SENTENCE:0] [TYPE:ACTION_TARGETS_OBJECT] [STRENGTH:MEDIUM]
  Subject: ACTION = "طالب"
  Object: OBJECT = "برامج الحماية"
  Reason: ACTION_DOMAIN_OBJECT_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_TECHNOLOGY
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
N-A

required_format_support_present:
YES

required_intent_support_present:
YES

unexpected_primary_domain_present:
NO

provenance_valid:
YES

## Case 028

Primary Domain Candidates:
PRIMARY_DOMAIN_WEATHER

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

- [SECTION:LEAD] [SENTENCE:0] [TYPE:EVENT_HAS_OUTCOME] [STRENGTH:STRONG]
  Subject: EVENT = "الأمطار الموسمية الغزيرة"
  Object: OUTCOME = "فيضانات"
  Reason: WEATHER_EVENT_DOMAIN_COMPOSITION
  Evidence Indexes: None
  Supports: PRIMARY_DOMAIN_WEATHER
  Suppresses: None

### Diagnostic Flags

required_relationship_present:
YES

required_primary_domain_present:
YES

required_secondary_domain_present:
N-A

required_format_support_present:
N-A

required_intent_support_present:
N-A

unexpected_primary_domain_present:
NO

provenance_valid:
YES
