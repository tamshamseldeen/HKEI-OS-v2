# Second Internal Topic Authority Canary — Independent Human Audit

The reviewer must determine the best Topic from the article itself and must not
assume either `deterministic_topic` or `authoritative_topic` is correct.
Provider output is not ground truth.

Choose `human_expected_topic` only from the legal Topic values in the JSON audit
packet. Set `human_correctness` to `CORRECT_OVERRIDE`, `INCORRECT_OVERRIDE`,
`UNSURE`, or leave it `UNREVIEWED`. No provider prompt, response, reasoning, or
chain-of-thought is included.

## CANARY2-001

- Audit identity: `105cb08f0553979ac022501fc8a9e16b9cf5aa9b73575b3d34a6383b9cd1116c`
- Deterministic / authoritative Topic: `GENERAL` / `WORLD`
- Title: زلزال بقوة 7.7 درجات يضرب سواحل إندونيسيا وتحذير من تسونامي
- Faithful excerpt: ضرب زلزال قوي بلغت شدته 7.7 درجات على مقياس ريختر قبالة سواحل إندونيسيا، السبت، ما أدى إلى إطلاق تحذيرات من احتمال تشكل أمواج مد عاتية «تسونامي» في بعض المناطق الساحلية. وأعلن المركز الأورومتوسطي لرصد الزلازل وقوع الهزة القوية، فيما أشارت هيئة المسح الجيولوجي الأميركية كذلك إلى تسجيل زلزال كبير قبالة السواحل الإندونيسية.
- Human correctness: `CORRECT_OVERRIDE`
- Human expected Topic: `WORLD`
- Override transition: `WRONG_TO_RIGHT`
- Reviewer notes: The article is centrally about a major earthquake off Indonesia and the resulting tsunami warning. The available Topic taxonomy has no dedicated earthquake or natural-disaster label, and WEATHER is not appropriate for a geological event. WORLD is therefore more specific and editorially appropriate than GENERAL.
- Review timestamp: `2026-08-15T04:31:51Z`

## CANARY2-002

- Audit identity: `218688620285f5c799caff2c31a5c88f4d5886b143e288ff2dbad7cb12272b9f`
- Deterministic / authoritative Topic: `ECONOMY` / `BUSINESS`
- Title: أدنوك الإماراتية: تعرض إحدى سفننا لهجوم أثناء عبورها مضيق هرمز
- Faithful excerpt: أعلنت شركة بترول أبوظبي الوطنية «أدنوك» تعرض إحدى السفن التابعة لها لهجوم أثناء عبورها مضيق هرمز مساء الجمعة 14 أغسطس. وأكدت الشركة أن الاستهداف لم يسفر عن وقوع إصابات بين أفراد طاقم السفينة، فيما جرى التعامل مع الحادث وفق الإجراءات المعمول بها.
- Human correctness: `INCORRECT_OVERRIDE`
- Human expected Topic: `WORLD`
- Override transition: `WRONG_TO_WRONG`
- Reviewer notes: The article's organizing event is an attack on a vessel while transiting the Strait of Hormuz. ADNOC identifies the vessel owner and is the source of the announcement, but the article is not primarily about the company's commercial activity or business performance. Within the available Topic taxonomy, WORLD best represents the international/security event. BUSINESS is therefore an incorrect authoritative Topic.
- Review timestamp: `2026-08-15T04:31:51Z`

Judgment source: `INDEPENDENT_HUMAN_REVIEW`.

Prepared: 2. Reviewed: 2. Correct: 1. Incorrect: 1. Unsure: 0.

Pilot mode: `SHADOW`. Canary continuation: `PAUSED_FOR_HUMAN_AUDIT`.
