# Batch 02 Contextual Evidence Diagnostic

## Summary

Cases:
6

Total Evidence Items:
28

Cases With Evidence:
6

Cases Without Evidence:
0

Required Topic Support Passed:
6/6

Required Format Support Passed:
1/2

Required Intent Support Passed:
1/2

Unexpected Sports Signals:
0

Suppression Cases:
1

## Case 011

Evidence Items:
3

### Topic Support

TOPIC_GOVERNMENT: 2

### Format Support

None

### Intent Support

None

### Claim Support

CLAIM_ATTRIBUTED: 1

### Suppression

None

### Roles

ATTRIBUTION: 1
AUTHORITY: 2

### Evidence Detail

- [SECTION:LEAD] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:ATTRIBUTION] [STRENGTH:MEDIUM] "أعلنت"
  Reason: ATTRIBUTION_SIGNAL
  Supports: CLAIM_ATTRIBUTED
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:AUTHORITY] [STRENGTH:STRONG] "وزارة التموين"
  Reason: GOVERNMENT_CONTEXT_PHRASE
  Supports: TOPIC_GOVERNMENT
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:AUTHORITY] [STRENGTH:WEAK] "وزارة"
  Reason: GENERIC_GOVERNMENT_TOKEN
  Supports: TOPIC_GOVERNMENT
  Suppresses: None

## Case 013

Evidence Items:
8

### Topic Support

TOPIC_TECHNOLOGY: 4
TOPIC_BUSINESS: 2

### Format Support

None

### Intent Support

None

### Claim Support

CLAIM_UNCERTAIN: 2

### Suppression

None

### Roles

SUBJECT: 4
ACTOR: 2
UNCERTAINTY: 1
PREDICTION: 1

### Evidence Detail

- [SECTION:HEADLINE] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "السيارات الكهربائية"
  Reason: TECHNOLOGY_CONTEXT_PHRASE
  Supports: TOPIC_TECHNOLOGY
  Suppresses: None
- [SECTION:HEADLINE] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "البطاريات الصلبة"
  Reason: TECHNOLOGY_CONTEXT_PHRASE
  Supports: TOPIC_TECHNOLOGY
  Suppresses: None
- [SECTION:HEADLINE] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:ACTOR] [STRENGTH:WEAK] "شركات"
  Reason: GENERIC_BUSINESS_TOKEN
  Supports: TOPIC_BUSINESS
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "بطاريات الحالة الصلبة"
  Reason: TECHNOLOGY_CONTEXT_PHRASE
  Supports: TOPIC_TECHNOLOGY
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:ACTOR] [STRENGTH:WEAK] "شركات"
  Reason: GENERIC_BUSINESS_TOKEN
  Supports: TOPIC_BUSINESS
  Suppresses: None
- [SECTION:BODY] [SENTENCE:0] [LEVEL:CONTEXT] [ROLE:UNCERTAINTY] [STRENGTH:STRONG] "قد"
  Reason: UNCERTAINTY_CONTEXT_PATTERN
  Supports: CLAIM_UNCERTAIN
  Suppresses: None
- [SECTION:BODY] [SENTENCE:0] [LEVEL:CONTEXT] [ROLE:PREDICTION] [STRENGTH:STRONG] "قد"
  Reason: PREDICTION_CONTEXT_PATTERN
  Supports: CLAIM_UNCERTAIN
  Suppresses: None
- [SECTION:BODY] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "السيارات الكهربائية"
  Reason: TECHNOLOGY_CONTEXT_PHRASE
  Supports: TOPIC_TECHNOLOGY
  Suppresses: None

## Case 015

Evidence Items:
7

### Topic Support

TOPIC_GOVERNMENT: 4

### Format Support

FORMAT_SERVICE: 2

### Intent Support

INTENT_KNOW_ACTION: 2
INTENT_VERIFY_REQUIREMENTS: 1

### Claim Support

CLAIM_ATTRIBUTED: 1

### Suppression

None

### Roles

AUTHORITY: 4
ATTRIBUTION: 1
REQUIREMENT: 1
DEADLINE: 1

### Evidence Detail

- [SECTION:HEADLINE] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:AUTHORITY] [STRENGTH:STRONG] "الفاتورة الإلكترونية"
  Reason: GOVERNMENT_CONTEXT_PHRASE
  Supports: TOPIC_GOVERNMENT
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:ATTRIBUTION] [STRENGTH:MEDIUM] "دعت"
  Reason: ATTRIBUTION_SIGNAL
  Supports: CLAIM_ATTRIBUTED
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:CONTEXT] [ROLE:REQUIREMENT] [STRENGTH:STRONG] "دعت مصلحة الضرائب المصرية كافة الشركات والمكلفين المتبقين للتسجيل"
  Reason: REQUIREMENT_CONTEXT_PATTERN
  Supports: FORMAT_SERVICE, INTENT_KNOW_ACTION
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:AUTHORITY] [STRENGTH:STRONG] "مصلحة الضرائب"
  Reason: GOVERNMENT_CONTEXT_PHRASE
  Supports: TOPIC_GOVERNMENT
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:AUTHORITY] [STRENGTH:STRONG] "الفاتورة الإلكترونية"
  Reason: GOVERNMENT_CONTEXT_PHRASE
  Supports: TOPIC_GOVERNMENT
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:CONTEXT] [ROLE:DEADLINE] [STRENGTH:STRONG] "قبل نهاية الشهر"
  Reason: DEADLINE_CONTEXT_PATTERN
  Supports: FORMAT_SERVICE, INTENT_KNOW_ACTION, INTENT_VERIFY_REQUIREMENTS
  Suppresses: None
- [SECTION:BODY] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:AUTHORITY] [STRENGTH:STRONG] "الفاتورة الإلكترونية"
  Reason: GOVERNMENT_CONTEXT_PHRASE
  Supports: TOPIC_GOVERNMENT
  Suppresses: None

## Case 018

Evidence Items:
7

### Topic Support

TOPIC_SCIENCE: 4
TOPIC_SPORTS: 1

### Format Support

None

### Intent Support

None

### Claim Support

CLAIM_ATTRIBUTED: 1

### Suppression

TOPIC_SPORTS: 1

### Roles

ATTRIBUTION: 1
SUBJECT: 4
ACTOR: 2

### Evidence Detail

- [SECTION:LEAD] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:ATTRIBUTION] [STRENGTH:MEDIUM] "أعلن"
  Reason: ATTRIBUTION_SIGNAL
  Supports: CLAIM_ATTRIBUTED
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "علماء الفلك"
  Reason: SCIENCE_CONTEXT_PHRASE
  Supports: TOPIC_SCIENCE
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "اكتشاف كوكب"
  Reason: SCIENCE_CONTEXT_PHRASE
  Supports: TOPIC_SCIENCE
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "المجموعة الشمسية"
  Reason: SCIENCE_CONTEXT_PHRASE
  Supports: TOPIC_SCIENCE
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:TOKEN] [ROLE:ACTOR] [STRENGTH:WEAK] "فريق"
  Reason: GENERIC_SPORTS_TOKEN
  Supports: TOPIC_SPORTS
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:CONTEXT] [ROLE:ACTOR] [STRENGTH:STRONG] "أعلن فريق دولي من علماء الفلك اكتشاف كوكب خارج المجموعة الشمسية يدور في المنطقة القابلة للسكن حول نجمه"
  Reason: SCIENCE_CONTEXT_SUPPRESSES_GENERIC_TEAM
  Supports: None
  Suppresses: TOPIC_SPORTS
- [SECTION:BODY] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "المرصد الأوروبي"
  Reason: SCIENCE_CONTEXT_PHRASE
  Supports: TOPIC_SCIENCE
  Suppresses: None

## Case 019

Evidence Items:
2

### Topic Support

TOPIC_CULTURE: 2

### Format Support

None

### Intent Support

None

### Claim Support

None

### Suppression

None

### Roles

SUBJECT: 2

### Evidence Detail

- [SECTION:HEADLINE] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "هيئة الكتاب"
  Reason: CULTURE_CONTEXT_PHRASE
  Supports: TOPIC_CULTURE
  Suppresses: None
- [SECTION:LEAD] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "معرض القاهرة الدولي للكتاب"
  Reason: CULTURE_CONTEXT_PHRASE
  Supports: TOPIC_CULTURE
  Suppresses: None

## Case 020

Evidence Items:
1

### Topic Support

TOPIC_TECHNOLOGY: 1

### Format Support

None

### Intent Support

None

### Claim Support

None

### Suppression

None

### Roles

SUBJECT: 1

### Evidence Detail

- [SECTION:HEADLINE] [SENTENCE:0] [LEVEL:PHRASE] [ROLE:SUBJECT] [STRENGTH:STRONG] "الرقائق الإلكترونية"
  Reason: TECHNOLOGY_CONTEXT_PHRASE
  Supports: TOPIC_TECHNOLOGY
  Suppresses: None
