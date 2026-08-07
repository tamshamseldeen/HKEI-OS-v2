# Batch 02 Topic Error Analysis

## Summary

Topic Mismatches:
8

Legacy Contamination Suspected:
3

Substring Collision Suspected:
6

Expected Vocabulary Gap:
4

Human Adjudication Required:
5

## Mismatch Diagnostics

### Case 011

Expected:
GOVERNMENT

Predicted:
ECONOMY

Confidence:
MEDIUM

Legacy Content Type:
ECONOMY_NEWS

Legacy Implied Topic:
ECONOMY

Legacy Support Applied:
YES

Title Matches:

None

Body Matches:

ECONOMY:
- التجارة — علنت وزارة التموين والتجارة الداخلية عن افتتاح
GOVERNMENT:
- وزارة — أعلنت وزارة التموين والتجارة ال
- وزارة — يات قياسية. وأكدت الوزارة أن هذه الخطوة تأتي

Risk Topics:
None

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- BODY_TOPIC_SIGNAL
- LEGACY_CONTENT_TYPE_TOPIC_SIGNAL

Supporting Signals:
- BODY_ECONOMY_SIGNAL
- LEGACY_TOPIC_SUPPORT

Warnings:
None

Diagnostic Flags:
- LEGACY_TOPIC_CONTAMINATION_SUSPECTED
- SUBSTRING_COLLISION_SUSPECTED

### Case 013

Expected:
TECHNOLOGY

Predicted:
BUSINESS

Confidence:
LOW

Legacy Content Type:
LEGAL_FINANCIAL_HIGH_RISK_CONTENT

Legacy Implied Topic:
None

Legacy Support Applied:
NO

Title Matches:

BUSINESS:
- شركات — شركات السيارات الكهربائية

Body Matches:

BUSINESS:
- شركات — تسارع كبرى شركات تصنيع السيارات حول
TECHNOLOGY:
- تقنية — الشرق" إلى أن هذه التقنية قد تسهم في خفض أسعا
SCIENCE:
- أبحاث — م ضخ الاستثمارات في أبحاث بطاريات الحالة الصل

Risk Topics:
- financial

Government Entity Evidence:
NO

Structured Economic Evidence:
YES

Reason Codes:
- TITLE_TOPIC_SIGNAL
- BODY_TOPIC_SIGNAL

Supporting Signals:
- TITLE_BUSINESS_SIGNAL
- BODY_BUSINESS_SIGNAL

Warnings:
- LOW_TOPIC_CONFIDENCE

Diagnostic Flags:
- SUBSTRING_COLLISION_SUSPECTED

### Case 014

Expected:
WORLD

Predicted:
GENERAL

Confidence:
LOW

Legacy Content Type:
STANDARD_NEWS

Legacy Implied Topic:
None

Legacy Support Applied:
NO

Title Matches:

None

Body Matches:

ENTERTAINMENT:
- ممثل — لتوصل للاتفاق، أبدى ممثلو عدد من الدول القلق

Risk Topics:
None

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- DEFAULT_GENERAL_TOPIC

Supporting Signals:
- INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
- LOW_TOPIC_CONFIDENCE
- TOPIC_SIGNAL_INSUFFICIENT

Diagnostic Flags:
- SUBSTRING_COLLISION_SUSPECTED
- EXPECTED_TOPIC_VOCABULARY_GAP

### Case 015

Expected:
GOVERNMENT

Predicted:
GENERAL

Confidence:
LOW

Legacy Content Type:
LEGAL_FINANCIAL_HIGH_RISK_CONTENT

Legacy Implied Topic:
None

Legacy Support Applied:
NO

Title Matches:

None

Body Matches:

BUSINESS:
- شركات — رائب المصرية كافة الشركات والمكلفين المتبقين
GOVERNMENT:
- وزارة — شهر الجاري. وأكدت الوزارة أن الفاتورة الإلكتر

Risk Topics:
- financial

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- DEFAULT_GENERAL_TOPIC

Supporting Signals:
- INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
- LOW_TOPIC_CONFIDENCE
- TOPIC_SIGNAL_INSUFFICIENT

Diagnostic Flags:
- SUBSTRING_COLLISION_SUSPECTED

### Case 017

Expected:
ECONOMY

Predicted:
SPORTS

Confidence:
MEDIUM

Legacy Content Type:
SPORTS_NEWS

Legacy Implied Topic:
SPORTS

Legacy Support Applied:
YES

Title Matches:

None

Body Matches:

SPORTS:
- هدف — اية المستثمرين. وتستهدف هذه الخطوة الحد من

Risk Topics:
None

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- BODY_TOPIC_SIGNAL
- LEGACY_CONTENT_TYPE_TOPIC_SIGNAL

Supporting Signals:
- BODY_SPORTS_SIGNAL
- LEGACY_TOPIC_SUPPORT

Warnings:
None

Diagnostic Flags:
- LEGACY_TOPIC_CONTAMINATION_SUSPECTED
- SUBSTRING_COLLISION_SUSPECTED
- EXPECTED_TOPIC_VOCABULARY_GAP

### Case 018

Expected:
SCIENCE

Predicted:
SPORTS

Confidence:
MEDIUM

Legacy Content Type:
SPORTS_NEWS

Legacy Implied Topic:
SPORTS

Legacy Support Applied:
YES

Title Matches:

None

Body Matches:

SPORTS:
- فريق — أعلن فريق دولي من علماء الفلك

Risk Topics:
None

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- BODY_TOPIC_SIGNAL
- LEGACY_CONTENT_TYPE_TOPIC_SIGNAL

Supporting Signals:
- BODY_SPORTS_SIGNAL
- LEGACY_TOPIC_SUPPORT

Warnings:
None

Diagnostic Flags:
- LEGACY_TOPIC_CONTAMINATION_SUSPECTED
- EXPECTED_TOPIC_VOCABULARY_GAP

### Case 019

Expected:
CULTURE

Predicted:
GENERAL

Confidence:
LOW

Legacy Content Type:
STANDARD_NEWS

Legacy Implied Topic:
None

Legacy Support Applied:
NO

Title Matches:

None

Body Matches:

None

Risk Topics:
None

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- DEFAULT_GENERAL_TOPIC

Supporting Signals:
- INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
- LOW_TOPIC_CONFIDENCE
- TOPIC_SIGNAL_INSUFFICIENT

Diagnostic Flags:
- EXPECTED_TOPIC_VOCABULARY_GAP

### Case 020

Expected:
TECHNOLOGY

Predicted:
GENERAL

Confidence:
LOW

Legacy Content Type:
LEGAL_FINANCIAL_HIGH_RISK_CONTENT

Legacy Implied Topic:
None

Legacy Support Applied:
NO

Title Matches:

None

Body Matches:

ECONOMY:
- السوق — بية مضاعفة حصتها في السوق العالمية بحلول نهاي
TECHNOLOGY:
- أشباه الموصلات — لإنشاء مصانع جديدة لأشباه الموصلات داخل دول التكتل. وت
SPORTS:
- هدف — اخل دول التكتل. وتستهدف الإستراتيجية الأورو

Risk Topics:
- financial

Government Entity Evidence:
NO

Structured Economic Evidence:
NO

Reason Codes:
- DEFAULT_GENERAL_TOPIC

Supporting Signals:
- INSUFFICIENT_TOPIC_EVIDENCE

Warnings:
- LOW_TOPIC_CONFIDENCE
- TOPIC_SIGNAL_INSUFFICIENT

Diagnostic Flags:
- SUBSTRING_COLLISION_SUSPECTED

## Human Adjudication Queue

### Case 011

Title:
"التموين" تعلن زيادة الطاقات التخزينية للصوامع لتأمين المخزون الاستراتيجي للقمح

Expected Topic:
GOVERNMENT

Predicted Topic:
ECONOMY

Possible Competing Topics:
- GOVERNMENT
- ECONOMY

Short Diagnostic Summary:
Multiple primary-topic labels remain defensible from the supplied title and body.

### Case 013

Title:
شركات السيارات الكهربائية تتجه لتقنيات البطاريات الصلبة لتقليل التكاليف

Expected Topic:
TECHNOLOGY

Predicted Topic:
BUSINESS

Possible Competing Topics:
- TECHNOLOGY
- BUSINESS
- ECONOMY
- SCIENCE

Short Diagnostic Summary:
Multiple primary-topic labels remain defensible from the supplied title and body.

### Case 014

Title:
مؤتمر الأمم المتحدة للمناخ يختتم أعماله باتفاق على إقرار صندوق الخسائر والأضرار

Expected Topic:
WORLD

Predicted Topic:
GENERAL

Possible Competing Topics:
- WORLD
- WEATHER
- POLITICS

Short Diagnostic Summary:
Multiple primary-topic labels remain defensible from the supplied title and body.

### Case 016

Title:
شركات الطيران العالمية تتوقع أرباحاً قياسية بفضل انتعاش حركة السفر

Expected Topic:
BUSINESS

Predicted Topic:
BUSINESS

Possible Competing Topics:
- BUSINESS
- ECONOMY

Short Diagnostic Summary:
Multiple primary-topic labels remain defensible from the supplied title and body.

### Case 020

Title:
أوروبا ترصد مليارات الأورو لتوطين صناعة الرقائق الإلكترونية وتقليل الاعتماد الخارجي

Expected Topic:
TECHNOLOGY

Predicted Topic:
GENERAL

Possible Competing Topics:
- TECHNOLOGY
- ECONOMY
- GOVERNMENT

Short Diagnostic Summary:
Multiple primary-topic labels remain defensible from the supplied title and body.

### Candidate Vocabulary Observations

- 014: WORLD may need supplied international climate-conference terminology.
- 017: ECONOMY may need supplied digital-asset and financial-regulation terminology.
- 018: SCIENCE may need supplied astronomy, planet, and observatory terminology.
- 019: CULTURE may need supplied book-fair and publishing terminology.

## Candidate Failure Classes

### Legacy dependency

011, 017, 018

### Substring matching

011, 013, 014, 015, 017, 020

### Vocabulary coverage

014, 017, 018, 019

### Topic scoring / precedence

011, 013, 015, 020

### Human-label ambiguity

011, 013, 014, 020
