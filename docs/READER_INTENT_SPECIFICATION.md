# HKEI OS v2 — Reader Intent Specification

## 1. Purpose

The Reader Intent layer receives:

- `NormalizedSource`
- `SourceRiskAssessment`
- `ExtractedFacts`
- `ContentTypeClassification`
- optional user instruction

It determines the reader's one primary editorial need before editorial strategy and drafting.

It does not:

- write the article
- generate headlines
- perform SEO
- build prompts
- verify facts externally
- determine final publication approval

## 2. Input

The layer accepts exactly:

- one `NormalizedSource`
- one `SourceRiskAssessment`
- one `ExtractedFacts`
- one `ContentTypeClassification`
- optional user instruction

## 3. Output

The layer returns one future object named `ReaderIntentClassification`.

It contains these fields:

- `reader_intent`
- `confidence`
- `reason_codes`
- `supporting_signals`
- `warnings`

Python types are not defined yet.

## 4. Supported MVP Reader Intents

The MVP supports only these exact values:

- `GET_UPDATE`
- `UNDERSTAND_EVENT`
- `KNOW_ACTION`
- `CHECK_CLAIM`
- `COMPARE_OPTIONS`
- `FOLLOW_DEVELOPMENT`
- `FIND_RESULT`
- `UNDERSTAND_IMPACT`
- `GET_GUIDANCE`
- `VERIFY_REQUIREMENTS`

## 5. Core Principle

- Reader intent describes what the reader needs from the article.
- Content type describes editorial treatment.
- Reader intent and content type are related but not identical.
- One source receives exactly one primary reader intent in the MVP.
- Explicit user instruction has highest precedence.
- Deterministic signals are preferred.
- Ambiguous intent must preserve uncertainty.

## 6. GET_UPDATE

Use when the reader mainly needs:

- what happened
- what is new
- the latest confirmed information

Common with:

- `BREAKING_NEWS`
- `STANDARD_NEWS`
- `TECHNOLOGY_NEWS`
- `ECONOMY_NEWS`

Typical signals:

- عاجل
- آخر التطورات
- تحديث
- الآن
- جديد
- announcement or event language

## 7. UNDERSTAND_EVENT

Use when the reader needs:

- explanation of what happened
- causes
- context
- significance
- how events connect

Common with:

- `EXPLAINER`
- `STANDARD_NEWS` with strong background signals

Typical signals:

- لماذا
- كيف
- الأسباب
- الخلفية
- التفاصيل
- ما معنى

## 8. KNOW_ACTION

Use when the reader needs to know:

- what to do
- what to avoid
- where to go
- what step comes next

Common with:

- `PUBLIC_SERVICE_NEWS`
- `GOVERNMENT_SERVICE_CONTENT`
- safety-related content

Typical signals:

- خطوات
- يجب
- تجنب
- التقديم
- التسجيل
- الحجز
- اتبع
- الإجراء المطلوب

## 9. CHECK_CLAIM

Use when the reader needs:

- whether a claim is true
- what evidence exists
- what remains unverified

Common with:

- `FACT_CHECK`
- `TRENDING_SOCIAL_CLAIM`

Requires:

- an identifiable claim
- or explicit fact-check intent

## 10. COMPARE_OPTIONS

Use when the reader needs:

- comparison between alternatives
- costs
- benefits
- features
- risks
- suitability

Typical signals:

- مقارنة
- الأفضل
- الفرق بين
- مقابل
- مزايا
- عيوب

Commercial recommendation systems are outside the MVP.

## 11. FOLLOW_DEVELOPMENT

Use when the reader needs:

- the next stage of an ongoing event
- a timeline
- new developments
- what may happen next

Typical signals:

- تطورات
- مستجدات
- متابعة
- مستمر
- قيد التحقيق
- ongoing event language

## 12. FIND_RESULT

Use when the reader needs:

- a score
- outcome
- final decision
- winner
- completed result

Common with:

- `SPORTS_NEWS`
- elections
- court rulings
- company results

Typical signals:

- نتيجة
- فاز
- خسر
- انتهت
- حسم
- قرار نهائي

## 13. UNDERSTAND_IMPACT

Use when the reader needs:

- consequences
- who is affected
- financial, legal, social, or operational impact

Typical signals:

- تأثير
- ينعكس
- المتضررون
- المستفيدون
- ماذا يعني
- consequences language

## 14. GET_GUIDANCE

Use when the reader needs:

- practical advice
- safe guidance
- preventive recommendations

Common with:

- `HEALTH_CONTENT`
- public safety content
- consumer warnings

High-risk guidance must follow risk controls and human review requirements.

## 15. VERIFY_REQUIREMENTS

Use when the reader needs:

- eligibility
- fees
- documents
- deadlines
- conditions
- procedures

Common with:

- `GOVERNMENT_SERVICE_CONTENT`
- legal and financial service content
- immigration and residency procedures

Typical signals:

- شروط
- رسوم
- مستندات
- أهلية
- موعد
- متطلبات
- إجراءات
- طريقة التقديم

## 16. Deterministic Signals

Possible MVP signals include:

- explicit user instruction
- content type
- title keywords
- body keywords
- source category
- extracted claims
- extracted dates
- extracted numbers
- extracted currencies
- risk topics
- procedural terminology
- result terminology
- ongoing-event terminology

Content type may provide a default intent but must not override stronger explicit evidence.

## 17. Default Mapping by Content Type

`BREAKING_NEWS`
→ `GET_UPDATE`

`STANDARD_NEWS`
→ `GET_UPDATE`

`NEWS_REWRITE`
→ preserve intent from source signals; otherwise `GET_UPDATE`

`PUBLIC_SERVICE_NEWS`
→ `KNOW_ACTION`

`GOVERNMENT_SERVICE_CONTENT`
→ `VERIFY_REQUIREMENTS`

`EXPLAINER`
→ `UNDERSTAND_EVENT`

`FACT_CHECK`
→ `CHECK_CLAIM`

`HEALTH_CONTENT`
→ `GET_GUIDANCE`

`LEGAL_FINANCIAL_HIGH_RISK_CONTENT`
→ `UNDERSTAND_IMPACT`

`SPORTS_NEWS`
→ `FIND_RESULT`

`TECHNOLOGY_NEWS`
→ `GET_UPDATE`

`ECONOMY_NEWS`
→ `UNDERSTAND_IMPACT`

`TRENDING_SOCIAL_CLAIM`
→ `CHECK_CLAIM`

This mapping is a fallback, not an absolute rule.

## 18. Precedence Rules

Use this exact precedence:

1. Explicit user instruction
2. `CHECK_CLAIM`
3. `VERIFY_REQUIREMENTS`
4. `KNOW_ACTION`
5. `FIND_RESULT`
6. `GET_GUIDANCE`
7. `COMPARE_OPTIONS`
8. `FOLLOW_DEVELOPMENT`
9. `UNDERSTAND_IMPACT`
10. `UNDERSTAND_EVENT`
11. `GET_UPDATE`

Stop at the first sufficiently supported intent.

## 19. Confidence

Use these exact values:

- `HIGH`
- `MEDIUM`
- `LOW`

`HIGH`:
Explicit instruction or strong consistent signals support one intent.

`MEDIUM`:
One intent is most likely, but overlapping signals exist.

`LOW`:
The source is insufficient or contradictory.

Low confidence must add a warning.

## 20. Warning Codes

- `LOW_READER_INTENT_CONFIDENCE`
- `CONFLICTING_READER_INTENT_SIGNALS`
- `EXPLICIT_USER_INTENT_REQUIRED`
- `CLAIM_EVIDENCE_REQUIRED`
- `HIGH_RISK_GUIDANCE_REQUIRES_REVIEW`
- `REQUIREMENTS_SOURCE_RECOMMENDED`

## 21. Non-Goals

- No article generation
- No headline generation
- No SEO generation
- No prompt building
- No audience-persona modeling
- No sentiment analysis
- No personalization
- No multi-intent output in the MVP
- No web verification

## 22. MVP Scope

For the first MVP:

- Identify one primary reader intent.
- Use deterministic signals only.
- Use classification, metadata, risk, and extracted facts.
- Do not use an LLM.
- Return confidence, reasons, signals, and warnings.

## 23. Acceptance Criteria

The future implementation must:

- receive classification workflow data
- return exactly one supported reader intent
- return one confidence level
- return stable reason codes
- return zero or more supporting signals
- return zero or more warnings
- preserve separation between content type and reader intent
- use explicit instruction before inferred signals
- default safely through the documented content-type mapping
- never infer unsupported high-risk guidance
