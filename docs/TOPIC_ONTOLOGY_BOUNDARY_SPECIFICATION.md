# Topic Ontology Boundary Specification

Status: `READY_FOR_GENERIC_ONTOLOGY_BOUNDARY_IMPLEMENTATION`

This document is a production-neutral specification. It defines editorial
semantics and future implementation constraints; it does not change the Topic
enum, classifier, semantic engine, Gate, Resolver, authority policy, or prompt.

## 1. Core editorial principle

The primary Topic MUST follow the article's `ORGANIZING_EDITORIAL_SUBJECT`.
Entity type, asset ownership, announcement source, location, downstream impact,
or general economic significance MUST NOT determine the Topic by itself.

The organizing editorial subject is the domain that best explains why the
headline, lead, and sustained body treatment belong together as one story.

## 2. Operational Topic definitions

### WORLD

`WORLD` applies when the organizing editorial subject is an international or
cross-border event, geopolitical development, international-security incident,
conflict or cross-border confrontation, diplomatic development, or major foreign
event not better represented by another supported Topic.

`WORLD` does not mean anything outside a domestic country, anything with a
foreign location, or anything involving a foreign company. Geography is context,
not sufficient primary evidence.

### BUSINESS

`BUSINESS` applies when the organizing editorial subject is company operations,
corporate strategy, management decisions, earnings or performance, corporate
transactions, mergers or acquisitions, products or services, business expansion
or contraction, operational disruption treated as a company story, commercial
asset performance, or corporate continuity.

A company acting only as owner, victim, information source, participant, or
named entity is insufficient for `BUSINESS`. The company's commercial activity
must receive central and sustained editorial treatment.

### ECONOMY

`ECONOMY` applies when the organizing treatment concerns markets, prices,
inflation, trade, macroeconomic conditions, economic indicators, monetary or
fiscal effects, supply and demand, sector-wide consequences, or broad production
and economic impact.

Economic significance alone is insufficient. Company size, strategic importance,
possible market effects, possible energy effects, or the mere occurrence of a
company event MUST NOT imply `ECONOMY` without explicit economic treatment.

## 3. Editorial role model

### ENTITY_ROLE

`ENTITY_ROLE` identifies an organization or other entity descriptively: company,
government, school, hospital, sports club, or similar. Entity identity is not a
primary-subject decision and `ENTITY_TYPE_NOT_PRIMARY_BY_ITSELF` applies.

### OWNER_ROLE

`OWNER_ROLE` identifies the entity that owns or controls an affected asset or
object. Ownership does not establish the article's editorial domain and
`OWNER_NOT_PRIMARY_BY_ITSELF` applies. A company owning an attacked vessel does
not automatically make the story `BUSINESS`.

### SOURCE_ROLE

`SOURCE_ROLE` identifies the entity providing an announcement or information.
Attribution is distinct from subject matter and `SOURCE_NOT_PRIMARY_BY_ITSELF`
applies. A company announcing an attack, a ministry announcing a school date, or
a hospital announcing an incident does not determine Topic through source type.

### PRIMARY_EVENT

`PRIMARY_EVENT` is the central occurrence organizing the headline, lead, and
body: for example an attack, earthquake, court ruling, market crash, earnings
announcement, or school-year change. It receives stronger Topic relevance than
entity identity, ownership, or attribution.

### PRIMARY_SUBJECT

`PRIMARY_SUBJECT` is the editorial concept or domain around which the story is
organized. `PRIMARY_EVENT` and `PRIMARY_SUBJECT` can reinforce one another, but
they are not identical: an attack is an event, while international security can
be the subject domain through which the attack is treated.

### DOWNSTREAM_IMPACT

`DOWNSTREAM_IMPACT` is a secondary effect of the primary event or subject. It
reuses the HKEI-216 consequence contract: impact can support secondary-domain
evidence, but `CONSEQUENCE_NOT_PRIMARY_BY_ITSELF` applies unless independent,
central treatment establishes that domain as primary.

## 4. Conceptual evidence hierarchy

Evidence priority, without numeric weights, is:

1. `PRIMARY_SUBJECT` plus `PRIMARY_EVENT` — strongest.
2. `SUSTAINED_TREATMENT`.
3. `DOWNSTREAM_IMPACT` or consequence.
4. `ENTITY_ROLE`, `OWNER_ROLE`, or `SOURCE_ROLE` — weakest.

`AUTHORITY_NOT_PRIMARY_BY_ITSELF` and `METHOD_NOT_PRIMARY_BY_ITSELF` remain part
of the generic role-protection contract alongside entity, owner, source, and
consequence protections.

## 5. Event-centrality contract

Event centrality MUST be inferred from headline framing, lead framing, sustained
body treatment, repeated reference to the event as an organizing thread, and
the article's overall organization. Raw occurrence counts MUST NOT substitute
for editorial centrality.

An event is central when later paragraphs explain, contextualize, update, or
trace consequences back to it. A named entity can recur because attribution is
required; recurrence alone does not make the entity the subject.

## 6. Pairwise boundary rules

### WORLD versus BUSINESS

When a company is involved but an international or security event organizes the
story, the company is mainly owner/source/victim/affected party, and commercial
operations are not sustained treatment, prefer `WORLD` over `BUSINESS`.

When international context exists but company operations, losses, production,
management, continuity, performance, or commercial impact organize the article,
prefer `BUSINESS` over `WORLD`.

### WORLD versus ECONOMY

An international event with only implied economic consequences remains `WORLD`.
`ECONOMY` may become primary when macro, market, trade, price, aggregate supply,
production, monetary, fiscal, or sector-wide treatment is sustained.

### BUSINESS versus ECONOMY

Company-specific performance, strategy, transactions, management, operations,
or continuity indicate `BUSINESS`. Economy-wide, market-wide, or sector-wide
conditions and indicators indicate `ECONOMY`. The two MUST NOT be collapsed.

## 7. Generic decision matrix

| Boundary | First Topic primary when | Second Topic primary when | Ambiguity indicator | Ignore as primary evidence |
|---|---|---|---|---|
| WORLD / BUSINESS | International, diplomatic, conflict, or security event organizes treatment | Corporate operations, performance, management, transaction, or continuity organizes treatment | External event and sustained corporate consequences receive comparable primary weight | Foreign location; company identity; asset ownership; company statement |
| WORLD / ECONOMY | International event dominates and economic consequences are implied or secondary | Explicit macro, market, price, trade, aggregate supply, or sector treatment dominates | Geopolitical event and sustained macroeconomic analysis receive comparable weight | Strategic importance; possible market effect; foreign location |
| BUSINESS / ECONOMY | Company-specific commercial activity dominates | Market-wide, economy-wide, or sector-wide conditions dominate | Corporate case is used throughout as both company story and representative economic indicator | Company size; isolated price or revenue figure; generic market mention |
| GOVERNMENT / BUSINESS | Public administration, service, regulation, or implementation is the subject | Corporate response, operations, compliance program, or commercial effect is the subject | Regulation and sustained company operations receive equal organizing weight | Ministry as announcement source; company as regulated entity |
| POLITICS / BUSINESS | Political decision, contest, diplomacy, or party/leader action organizes treatment | Corporate strategy, transaction, governance, or performance organizes treatment | Political conflict and corporate decision are co-equal throughout | Politician quote; corporate lobbying mention; company identity |
| WORLD / GOVERNMENT | Cross-border, diplomatic, international-security, or foreign event organizes treatment | Domestic public administration, service delivery, or agency implementation organizes treatment | International event and domestic governmental response are co-equal | Foreign location; ministry attribution; authority identity |

## 8. Ambiguity contract

The conceptual boundary state is one of:

- `CLEAR`: one Topic has materially stronger primary-event, primary-subject, and
  sustained-treatment support.
- `BOUNDARY_COMPETING`: two Topics have genuine primary-subject support and
  neither can be demoted to entity, owner, source, context, or consequence.
- `INSUFFICIENT_EVIDENCE`: the available article is too thin to establish a
  defensible organizing subject.

`TOPIC_BOUNDARY_AMBIGUITY` is the diagnostic condition corresponding to a
structurally `BOUNDARY_COMPETING` case. It is not a new production enum in this
specification and MUST NOT be inferred merely from multiple keyword matches.

Human review may return `UNSURE` when role analysis still leaves a genuine
boundary split. `UNSURE` is neither correct, incorrect, regression, nor success.

## 9. External-event and company-centric protections

For a company-linked external event, if the company is chiefly victim, owner,
source, participant, or affected party and the external event drives headline
and lead, the company domain MUST NOT dominate without sustained business
treatment. This is `EXTERNAL_EVENT_PROTECTION`.

Conversely, if the external event is context while the article sustains focus on
company operations, impact, management, losses, production, or continuity,
`BUSINESS` may remain primary. This `COMPANY_CENTRIC_EVENT_PROTECTION` prevents
overcorrection toward `WORLD`.

## 10. Authority and provider-confidence implications

Provider confidence is not sufficient to resolve ontology ambiguity. A HIGH or
MEDIUM-confidence provider decision in a structurally
`TOPIC_BOUNDARY_AMBIGUITY` case may still require human review or no authority.
A future `AMBIGUOUS_BOUNDARY_BLOCK` may prevent Topic authority when the boundary
remains competing. This specification does not implement that blocker or shrink
the candidate universe.

## 11. Single-label decision and research direction

The current production architecture retains exactly one primary Topic:
`SINGLE_LABEL_RETAINED`. Secondary Topics are not added here.

A Primary-plus-Secondary Topic model could reduce information loss in mixed
stories, but current evidence does not justify production implementation.
`SECONDARY_DOMAIN_MODEL_DEFERRED_FOR_RESEARCH` records that direction without
changing contracts.

## 12. Design evidence

HKEI-221 identified 15 historical similar cases, 24 newly authored synthetic
scenarios, 11 scenarios where a secondary dimension is lost, and 4 forced-choice
ambiguous scenarios. These are design evidence only. No historical case is
relabelled by this specification.

## 13. Future implementation scope

Likely implementation scope is limited to entity/owner/source role protection,
stronger primary-event centrality, clearer operational WORLD/BUSINESS/ECONOMY
semantics, and ambiguity propagation. Candidate-universe shrinkage is not a
default part of the scope.

Implementation MUST proceed in phases:

1. Phase 1 — canonical role and relationship models.
2. Phase 2 — generic Arabic role extraction.
3. Phase 3 — event-centrality composition.
4. Phase 4 — Topic promotion and sufficiency integration.
5. Phase 5 — boundary-ambiguity detection.
6. Phase 6 — generic fixture validation.
7. Phase 7 — historical shadow audit.
8. Phase 8 — new untouched canary.

Each phase must preserve provider neutrality and frozen downstream contracts
unless separately authorized.

## 14. Pilot constraint

Pilot effective mode remains `SHADOW`. No new canary may run until ontology
implementation and validation are complete. Provider calls for this specification are `0`, and no production file is modified.
