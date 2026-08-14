# CANARY-003 Wrong Topic Override Analysis

This one-time offline diagnostic preserves the frozen historical result:
deterministic `CRIME`, authoritative
`HEALTH`, and human expected
`CRIME`.

The earliest failure stage is `TOPIC_ROLE_ASSIGNMENT`. CRIME was
detected but remained LOW confidence; the fingerprint-matched structured request
contained no semantic relationships or domain candidates. The Gate appropriately
requested Topic adjudication, but the all-label candidate universe and missing
subject-versus-consequence representation allowed food-safety context to become
HEALTH/HIGH with ambiguity false.

Resolver and authority applicator behavior were correct by contract. This was an
editorial semantic regression, not an authority-contract violation.

Safest generic counterfactual: `A. consequence-vs-subject semantic protection`.
Overcorrection risk: `LOW`. The protection must
preserve HEALTH where disease, food poisoning, unsafe products, or a public-health
hazard is the central subject rather than a consequence of another central event.

Pilot implication: `ONE_GENERIC_SEMANTIC_FIX_REQUIRED_BEFORE_NEW_CANARY`. The pilot remains stopped;
any future generic change requires generic fixtures and a new internal canary.
No provider call, source-specific tuning, or production mutation occurred.
