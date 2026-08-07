# Batch 02 Topic Error Analysis

## Summary

Topic Mismatches:
1

Legacy Contamination Suspected:
0

Substring Collision Suspected:
1

Expected Vocabulary Gap:
0

Human Adjudication Required:
5

## Mismatch Diagnostics

### Case 011

Expected:
GOVERNMENT

Predicted:
GENERAL

Confidence:
LOW

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
GENERAL

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
TECHNOLOGY

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
WORLD

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
TECHNOLOGY

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

011

### Substring matching

011

### Vocabulary coverage

None

### Topic scoring / precedence

011

### Human-label ambiguity

011
