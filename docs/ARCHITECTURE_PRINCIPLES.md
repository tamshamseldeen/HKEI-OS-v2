# HKEI OS v2 — Architecture Principles

## 1. Product Definition Before Implementation

No component is implemented without a documented MVP requirement.

## 2. Minimal Architecture

Build the smallest architecture that completes the first end-to-end use case.

## 3. Editorial Logic Is Independent

Editorial policy must remain independent from:

- OpenAI
- Anthropic
- Google
- Any individual LLM provider

## 4. Facts Before Prose

Generation cannot begin before supplied facts, claims, quotations, and missing information are separated.

## 5. Editorial Decisions Before Drafting

The system determines content type, risk, reader intent, article length, and required structure before drafting.

## 6. LLMs Are Execution Engines

The LLM drafts and assists with analysis, but it does not define the product architecture or editorial constitution.

## 7. Deterministic Logic Where Practical

Use deterministic rules for:

- Required fields
- Risk levels
- Output validation
- Missing information
- Prohibited claims
- Mandatory warnings

Use LLM reasoning only where semantic judgment is necessary.

## 8. Human Review Before Publication

HKEI assists editors. It does not eliminate editorial accountability.

## 9. High-Risk Content Protection

Medical, legal, financial, government-service, immigration, public-safety, and emergency content must use stricter verification policies.

## 10. No Vendor Lock-In

Provider integrations must be adapters around stable HKEI interfaces.

## 11. Testable Components

Every implemented behavior must have:

- Clear input
- Clear output
- Acceptance criteria
- Automated tests where appropriate

## 12. No Premature Features

Do not add:

- Crawlers
- Dashboards
- Plugins
- Style learners
- Multi-agent orchestration
- Publishing integrations

until the first MVP passes its quality validation.

## 13. One End-to-End Workflow First

The first implementation target is:

Raw News
→ Editorial Package

Only after this works reliably may the system expand.

## 14. Change Control

Architecture may change only when:

- A real test reveals a measurable problem.
- The proposed change is documented.
- The change simplifies or measurably improves the product.

Do not redesign the system based only on new ideas.