# HKEI OS v2 — Product Definition

## 1. Product Purpose

HKEI is a general Arabic editorial operating system for news websites covering all editorial categories.

## 2. Target Users

- Arabic news publishers
- News editors
- Journalists
- Editorial managers
- SEO editors
- Digital publishing teams

## 3. Problem Statement

Existing AI writing tools often:

- Paraphrase mechanically
- Repeat source structure
- Produce generic or robotic Arabic
- Add unsupported information
- Use the same format for every content type
- Focus on keywords instead of reader value
- Produce articles that require extensive human rewriting

## 4. Product Promise

HKEI should convert source material into an article that is:

- Factually grounded
- Original in structure and wording
- Easy and fast to read
- Simple enough for a general reader
- More useful than the raw source
- Naturally optimized without keyword stuffing
- Ready for a short human editorial review

HKEI does not guarantee ranking, Discover appearance, Google News inclusion, or protection from penalties.

## 5. Editorial Direction

HKEI should combine these editorial qualities without copying or imitating any publisher:

- BBC Arabic: accuracy, neutrality, and context
- Al Arabiya: speed, clarity, and accessibility
- Youm7: strong Arabic headlines and search awareness without misleading clickbait

## 6. Inputs

The MVP accepts:

- Original title
- Original body
- Source name
- Source URL, optional
- Publication date, optional
- Country, optional
- Category, optional
- User instructions, optional

## 7. Outputs

The MVP returns:

- Publication decision: Publish, Needs Revision, or Reject
- Editorial title
- SEO title
- Google News title
- Google Discover title
- Meta description
- URL slug
- Article summary
- Final Arabic article
- Suggested category
- Suggested tags
- Source and verification warnings
- Missing-information warnings
- Editorial quality report

FAQ, timeline, tables, bullet lists, and background sections must be generated only when editorially useful.

## 8. Supported MVP Content Types

Include only:

- Breaking News
- Standard News
- News Rewrite
- Public Service News
- Government Service Content
- Explainer
- Fact Check
- Health Content
- Legal and Financial High-Risk Content
- Sports News
- Technology News
- Economy News
- Trending and Social Media Claims

## 9. Core Workflow

Source Intake
→ Source and Risk Assessment
→ Fact Separation
→ Content-Type Classification
→ Reader-Intent Identification
→ Editorial Strategy
→ Article Planning
→ Arabic Drafting
→ Google Readiness
→ Editorial Quality Review
→ Publish / Revise / Reject

## 10. Non-Negotiable Rules

- Never invent facts, quotes, names, numbers, dates, sources, or events.
- Never increase certainty beyond the source.
- Never present statements or allegations as verified facts.
- Never use deceptive clickbait.
- Never pad an article to reach an arbitrary word count.
- Never reproduce the source sentence by sentence.
- Never hide uncertainty.
- Never claim independent verification unless it actually occurred.
- High-risk medical, legal, financial, government-benefit, immigration, and safety content requires stronger verification.
- Human review remains required before publication.

## 11. Natural Arabic Requirements

Include:

- Modern Arabic journalistic language
- Short and medium sentences with natural variation
- Short paragraphs
- One primary idea per paragraph
- No literal English translation
- No repetitive openings
- No robotic transitions
- No unnecessary formalism
- No generic filler

Forbidden by default unless supported by the story:

- لن تصدق
- مفاجأة مدوية
- صدمة
- معجزة
- في تطور لافت
- في خطوة مهمة
- جدير بالذكر
- تجدر الإشارة
- اجتاحت مواقع التواصل
- أثار ضجة واسعة

## 12. MVP Non-Goals

Explicitly exclude from v2 MVP:

- WordPress plugin
- Automatic publishing
- Website crawling
- Training a proprietary language model
- Publisher-style imitation
- Multi-agent architecture
- Large editorial corpus
- Automated social media publishing
- Full analytics dashboard
- Self-learning system
- Mobile application
- SaaS billing

## 13. Success Criteria

The MVP is successful when:

- A raw source can be transformed through one documented workflow.
- The generated article preserves supplied facts.
- Unsupported facts are not added.
- The article is structurally independent from the source.
- The article uses natural Arabic.
- The article answers the reader's main question early.
- High-risk content is flagged appropriately.
- A human editor can approve or correct the output within five minutes.
- The same input produces a consistent editorial structure.
- The system works with more than one LLM provider without redesigning editorial logic.

## 14. First MVP

Define the first MVP as:

Input:
One raw Arabic news article.

Output:
One verified editorial package containing titles, metadata, final article, warnings, and quality review.

No crawler.
No automatic publication.
No advanced dashboard.

## 15. Open Questions

- What minimum source information is required before generation?
- Which checks are deterministic and which require an LLM?
- How should official sources be recorded?
- What quality threshold permits Publish instead of Needs Revision?
- Which output elements are mandatory for every content type?
- How should high-risk content be handled when official verification is unavailable?