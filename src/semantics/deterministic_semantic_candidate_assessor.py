"""Deterministic candidate-relative assessment of existing semantic evidence."""

from dataclasses import dataclass

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.evidence_role import EvidenceRole
from src.evidence.evidence_strength import EvidenceStrength

from .compositional_semantic_evidence import CompositionalSemanticEvidence
from .semantic_candidate_assessment import SemanticCandidateAssessment
from .semantic_component import SemanticComponent
from .semantic_evidence_direction import SemanticEvidenceDirection
from .semantic_evidence_strength import SemanticEvidenceStrength
from .semantic_evidence_sufficiency import SemanticEvidenceSufficiency


_LABEL_PREFIXES = (
    ("PRIMARY_DOMAIN_", "DOMAIN"),
    ("SECONDARY_DOMAIN_", "DOMAIN"),
    ("TOPIC_", "DOMAIN"),
    ("FORMAT_", "FORMAT"),
    ("INTENT_", "INTENT"),
)
_SUBJECT_BEARING_ROLES = frozenset(
    {"SUBJECT", "OBJECT", "EVENT", "STATE", "CHANGE", "RESULT", "OUTCOME"}
)
_TREATMENT_ROLES = frozenset(
    {
        "ACTION", "CAUSE", "EFFECT", "PROCEDURE", "REQUIREMENT", "SCHEDULE",
        "MEASUREMENT", "PRICE", "CLAIM", "RESULT", "OUTCOME", "CHANGE", "STATE",
    }
)
_SECONDARY_ROLES = frozenset({"AUTHORITY", "ACTOR", "METHOD"})
_COMPONENT_ROLES = {
    SemanticComponent.PRIMARY_SUBJECT: "SUBJECT",
    SemanticComponent.SECONDARY_SUBJECT: "SUBJECT",
    SemanticComponent.INDICATOR: "MEASUREMENT",
    SemanticComponent.CONSEQUENCE: "EFFECT",
    SemanticComponent.INTERPRETATION: "EFFECT",
    SemanticComponent.DEADLINE: "SCHEDULE",
    SemanticComponent.RECOMMENDED_ACTION: "ACTION",
    SemanticComponent.AFFECTED_AUDIENCE: "OBJECT",
}
_FORMAT_CANDIDATES = frozenset(
    {
        "FACT_CHECK", "SERVICE", "GUIDE", "TREND_UPDATE", "RESULT_REPORT",
        "STANDARD_NEWS", "ANALYSIS", "EXPLAINER",
    }
)


@dataclass(frozen=True)
class _EvidenceRecord:
    """Internal symbolic evidence record without raw source material."""

    candidate: str
    family: str
    direction: str
    provenance: tuple[object, ...]
    relationship_type: str
    roles: tuple[str, ...]
    source_strength: EvidenceStrength
    secondary: bool = False


class DeterministicSemanticCandidateAssessor:
    """Assess only candidates represented by supplied deterministic evidence."""

    def assess(
        self,
        *,
        semantic_evidence: CompositionalSemanticEvidence,
        contextual_evidence: ContextualEvidence | None = None,
    ) -> tuple[SemanticCandidateAssessment, ...]:
        """Return candidate assessments sorted lexically by candidate string."""
        records = self._records(semantic_evidence, contextual_evidence)
        grouped: dict[tuple[str, str], list[_EvidenceRecord]] = {}
        duplicate_candidates: set[tuple[str, str]] = set()
        seen: set[tuple[object, ...]] = set()
        for record in records:
            identity = (
                record.candidate, record.family, record.direction, record.provenance
            )
            key = (record.candidate, record.family)
            if identity in seen:
                duplicate_candidates.add(key)
                continue
            seen.add(identity)
            grouped.setdefault(key, []).append(record)

        preliminary = {
            key: self._preliminary(value, family=key[1], all_records=records)
            for key, value in grouped.items()
        }
        material_by_family: dict[str, tuple[str, ...]] = {}
        for family in {family for _, family in grouped}:
            material_by_family[family] = tuple(
                candidate
                for (candidate, candidate_family), item in preliminary.items()
                if candidate_family == family
                and item["direction"] is SemanticEvidenceDirection.SUPPORT
                and item["strength"] in {
                    SemanticEvidenceStrength.MODERATE,
                    SemanticEvidenceStrength.STRONG,
                }
            )

        assessments = []
        for key, candidate_records in grouped.items():
            candidate, family = key
            item = preliminary[key]
            competitors = tuple(
                value for value in material_by_family[family] if value != candidate
            )
            warnings = list(item["warnings"])
            if key in duplicate_candidates:
                warnings.append("DUPLICATE_EVIDENCE_DISCOUNTED")
            if competitors:
                warnings.append("COMPETING_CANDIDATE")
            sufficiency = self._sufficiency(
                direction=item["direction"],
                strength=item["strength"],
                roles=item["roles"],
                competitors=competitors,
                warnings=tuple(warnings),
                independent_supports=item["independent_supports"],
                family=family,
                structure_complete=bool(item["structure_complete"]),
                complete_competitors=tuple(
                    value for value in competitors
                    if preliminary[(value, family)]["structure_complete"]
                ),
            )
            assessments.append(
                SemanticCandidateAssessment(
                    candidate=candidate,
                    direction=item["direction"],
                    strength=item["strength"],
                    sufficiency=sufficiency,
                    supporting_relationship_types=self._unique(
                        record.relationship_type
                        for record in candidate_records
                        if record.direction == "SUPPORT"
                    ),
                    suppressing_relationship_types=self._unique(
                        record.relationship_type
                        for record in candidate_records
                        if record.direction == "SUPPRESS"
                    ),
                    role_basis=item["roles"],
                    competing_candidates=competitors,
                    warnings=self._unique(warnings),
                )
            )
        return tuple(sorted(assessments, key=lambda item: item.candidate))

    def _records(
        self,
        semantic: CompositionalSemanticEvidence,
        contextual: ContextualEvidence | None,
    ) -> tuple[_EvidenceRecord, ...]:
        records: list[_EvidenceRecord] = []
        for relationship in semantic.relationships:
            roles = self._relationship_roles(relationship.subject_component, relationship.object_component)
            provenance = (
                "SEMANTIC", relationship.source_section.value,
                relationship.sentence_index, relationship.relationship_type.value,
                relationship.reason_code, relationship.evidence_indexes,
            )
            records.extend(self._label_records(
                relationship.supports, "SUPPORT", provenance,
                relationship.relationship_type.value, roles, relationship.strength,
            ))
            records.extend(self._label_records(
                relationship.suppresses, "SUPPRESS", provenance,
                relationship.relationship_type.value, roles, relationship.strength,
            ))
            if not relationship.supports and not relationship.suppresses:
                neutral = self._normalized_label(relationship.object_text)
                if neutral is not None:
                    candidate, family, secondary = neutral
                    records.append(_EvidenceRecord(
                        candidate, family, "NEUTRAL", provenance,
                        relationship.relationship_type.value, roles,
                        relationship.strength, secondary,
                    ))
        represented_supports = {
            label for relationship in semantic.relationships
            for label in relationship.supports
        }
        represented_suppressions = {
            label for relationship in semantic.relationships
            for label in relationship.suppresses
        }
        collection_supports = tuple(
            label for label in (
                semantic.primary_domain_candidates
                + semantic.secondary_domain_candidates
                + semantic.format_support
                + semantic.intent_support
            ) if label not in represented_supports
        )
        collection_suppressions = tuple(
            label for label in semantic.format_suppression
            if label not in represented_suppressions
        )
        records.extend(self._label_records(
            collection_supports, "SUPPORT", ("SEMANTIC_COLLECTION",),
            "SEMANTIC_COLLECTION_SUPPORT", (), EvidenceStrength.WEAK,
        ))
        records.extend(self._label_records(
            collection_suppressions, "SUPPRESS", ("SEMANTIC_COLLECTION",),
            "SEMANTIC_COLLECTION_SUPPRESSION", (), EvidenceStrength.WEAK,
        ))
        if contextual is not None:
            for item in contextual.all_items:
                provenance = (
                    "CONTEXTUAL", item.source_section.value, item.sentence_index,
                    item.reason_code, item.role.value,
                )
                roles = (self._contextual_role(item.role),)
                records.extend(self._label_records(
                    item.supports, "SUPPORT", provenance,
                    f"CONTEXTUAL_{item.reason_code}", roles, item.strength,
                ))
                records.extend(self._label_records(
                    item.suppresses, "SUPPRESS", provenance,
                    f"CONTEXTUAL_{item.reason_code}", roles, item.strength,
                ))
        return tuple(records)

    def _label_records(
        self,
        labels: tuple[str, ...],
        direction: str,
        provenance: tuple[object, ...],
        relationship_type: str,
        roles: tuple[str, ...],
        source_strength: EvidenceStrength,
    ) -> tuple[_EvidenceRecord, ...]:
        records = []
        for label in labels:
            normalized = self._normalized_label(label)
            if normalized is None:
                continue
            candidate, family, secondary = normalized
            records.append(_EvidenceRecord(
                candidate, family, direction, provenance,
                relationship_type, roles, source_strength, secondary,
            ))
        return tuple(records)

    @staticmethod
    def _normalized_label(label: str) -> tuple[str, str, bool] | None:
        for prefix, family in _LABEL_PREFIXES:
            if label.startswith(prefix) and len(label) > len(prefix):
                return label.removeprefix(prefix), family, prefix == "SECONDARY_DOMAIN_"
        return None

    def _preliminary(
        self,
        records: list[_EvidenceRecord],
        *,
        family: str,
        all_records: tuple[_EvidenceRecord, ...],
    ) -> dict[str, object]:
        supports = [record for record in records if record.direction == "SUPPORT"]
        suppressions = [record for record in records if record.direction == "SUPPRESS"]
        neutral = [record for record in records if record.direction == "NEUTRAL"]
        roles = self._unique(role for record in records for role in record.roles)
        warnings: list[str] = []
        if supports and suppressions:
            direction = SemanticEvidenceDirection.CONFLICTING
            warnings.append("SUPPORT_SUPPRESSION_CONFLICT")
        elif supports:
            direction = SemanticEvidenceDirection.SUPPORT
        elif suppressions:
            direction = SemanticEvidenceDirection.SUPPRESS
        else:
            direction = SemanticEvidenceDirection.NEUTRAL
        independent_supports = len(supports)
        relevant_roles = (
            _SUBJECT_BEARING_ROLES
            if family == "DOMAIN"
            else _SUBJECT_BEARING_ROLES | _TREATMENT_ROLES
        )
        central = bool(set(roles) & relevant_roles)
        dominated = set(roles) and set(roles) <= _SECONDARY_ROLES
        if dominated:
            for role in ("AUTHORITY", "ACTOR", "METHOD"):
                if role in roles:
                    warnings.append(f"{role}_DOMINATED")
        if supports and not central:
            warnings.append("SUBJECT_ROLE_UNRESOLVED")
        if any(record.secondary for record in supports):
            warnings.append("SUBJECT_ROLE_UNRESOLVED")
        structure_complete = True
        if family == "FORMAT":
            structure_complete = self._format_structure_complete(
                candidate=records[0].candidate,
                supports=supports,
                all_records=all_records,
            )
            if supports and not structure_complete:
                warnings.append("FORMAT_STRUCTURE_INCOMPLETE")
        if not supports or dominated or (independent_supports == 1 and not central):
            strength = SemanticEvidenceStrength.WEAK
        elif (
            family == "FORMAT"
            and structure_complete
            and records[0].candidate != "TREND_UPDATE"
        ):
            strength = SemanticEvidenceStrength.STRONG
        elif independent_supports >= 2 and central:
            strength = SemanticEvidenceStrength.STRONG
        else:
            strength = SemanticEvidenceStrength.MODERATE
        if direction is SemanticEvidenceDirection.CONFLICTING:
            strength = max(
                strength,
                SemanticEvidenceStrength.MODERATE,
                key=self._strength_rank,
            )
        if supports and independent_supports < 2:
            warnings.append("INSUFFICIENT_INDEPENDENT_SUPPORT")
        return {
            "direction": direction,
            "strength": strength,
            "roles": roles,
            "warnings": tuple(warnings),
            "independent_supports": independent_supports,
            "neutral_count": len(neutral),
            "family": family,
            "structure_complete": structure_complete,
        }

    @classmethod
    def _format_structure_complete(
        cls,
        *,
        candidate: str,
        supports: list[_EvidenceRecord],
        all_records: tuple[_EvidenceRecord, ...],
    ) -> bool:
        """Require complete, candidate-specific editorial treatment structure."""
        if candidate not in _FORMAT_CANDIDATES or not supports:
            return False
        reasons = {record.provenance[4] for record in supports if len(record.provenance) > 4}
        all_symbols = {
            record.relationship_type.upper() for record in all_records
        } | {
            role for record in all_records for role in record.roles
        }
        if candidate == "RESULT_REPORT" and any(
            "PREDICTION" in symbol or "FUTURE" in symbol
            for symbol in all_symbols
        ):
            return False
        if candidate != "SERVICE" and f"BOUNDED_{candidate}_STRUCTURE" in reasons:
            return True
        roles = {role for record in supports for role in record.roles}
        types = {record.relationship_type for record in supports}
        symbols = {str(value).upper() for value in reasons} | roles | types

        def has(*terms: str) -> bool:
            return any(term in symbol for term in terms for symbol in symbols)

        if candidate == "FACT_CHECK":
            return (
                has("CLAIM", "ASSERTION")
                and has("VERIF", "EVALUAT", "CHECK")
                and has("VERDICT", "CONCLUSION", "TRUTH", "STATUS", "OUTCOME")
            )
        if candidate == "SERVICE":
            actionable = has("ACTION", "APPLICATION", "REGISTRATION", "PROCEDURE")
            access_detail = has(
                "REQUIREMENT", "ELIGIBILITY", "DEADLINE", "SCHEDULE", "LOCATION",
                "AVAILABILITY", "PRICE", "RATE",
            )
            organizing = (
                has("APPLICATION", "REGISTRATION", "PROCEDURE", "ELIGIBILITY")
                or (has("REQUIREMENT") and has("DEADLINE", "SCHEDULE"))
            )
            return actionable and access_detail and organizing
        if candidate == "GUIDE":
            recommendation = has("RECOMMEND", "INSTRUCTION", "GUIDANCE", "ADVICE")
            action = has("ACTION")
            distinct_actions = {
                record.provenance for record in supports
                if set(record.roles) & {"ACTION", "OBJECT"}
            }
            return recommendation and action and len(distinct_actions) >= 2
        if candidate == "TREND_UPDATE":
            current = has("INDICATOR", "MEASUREMENT", "CURRENT", "VALUE", "LEVEL")
            reference = has("REFERENCE", "PRIOR", "PREVIOUS", "COMPARISON", "PERIOD")
            movement = has("CHANGE", "MOVEMENT", "INCREASE", "DECREASE", "DIRECTION")
            return current and reference and movement
        if candidate == "RESULT_REPORT":
            completed = has("COMPLETED", "FINAL", "EVENT", "RESULT")
            outcome = has("OUTCOME", "SCORE", "RANKING", "FINAL", "RESULT")
            future = has("FUTURE", "PLANNED", "SCHEDULED", "EXPECTED")
            return completed and outcome and not future
        if candidate == "ANALYSIS":
            subject = has("EVENT", "STATE", "CHANGE")
            explanation = has("CAUSE", "CONSTRAINT", "TRADEOFF")
            consequence = has("EFFECT", "IMPLICATION", "CONSEQUENCE", "OUTCOME")
            return subject and explanation and consequence
        if candidate == "EXPLAINER":
            subject = has("SYSTEM", "PROCESS", "CONCEPT", "CHANGE", "SUBJECT")
            mechanism = has("MECHANISM", "METHOD", "HOW")
            understanding = has("UNDERSTANDING", "EXPLANATION", "EXPLAINER")
            return subject and mechanism and understanding
        if candidate == "STANDARD_NEWS":
            event = has("EVENT", "ANNOUNCEMENT", "DECISION", "DEVELOPMENT", "STATEMENT")
            reporting = has("REPORT", "NEWS", "ACTOR_PERFORMS_ACTION")
            return event and reporting
        return False

    @staticmethod
    def _sufficiency(
        *,
        direction: SemanticEvidenceDirection,
        strength: SemanticEvidenceStrength,
        roles: tuple[str, ...],
        competitors: tuple[str, ...],
        warnings: tuple[str, ...],
        independent_supports: int,
        family: str,
        structure_complete: bool,
        complete_competitors: tuple[str, ...],
    ) -> SemanticEvidenceSufficiency:
        if direction is SemanticEvidenceDirection.CONFLICTING:
            return SemanticEvidenceSufficiency.CONFLICTED
        if direction is not SemanticEvidenceDirection.SUPPORT:
            return SemanticEvidenceSufficiency.INSUFFICIENT
        if set(roles) and set(roles) <= _SECONDARY_ROLES:
            return SemanticEvidenceSufficiency.INSUFFICIENT
        if strength is SemanticEvidenceStrength.WEAK:
            return SemanticEvidenceSufficiency.INSUFFICIENT
        if family == "FORMAT" and not structure_complete:
            return SemanticEvidenceSufficiency.PARTIAL
        if complete_competitors:
            return SemanticEvidenceSufficiency.PARTIAL
        if competitors and family != "FORMAT":
            return SemanticEvidenceSufficiency.PARTIAL
        relevant_roles = (
            _SUBJECT_BEARING_ROLES
            if family == "DOMAIN"
            else _SUBJECT_BEARING_ROLES | _TREATMENT_ROLES
        )
        central = bool(set(roles) & relevant_roles)
        if (
            strength is SemanticEvidenceStrength.STRONG
            and central
            and (independent_supports >= 2 or (family == "FORMAT" and structure_complete))
            and "SUBJECT_ROLE_UNRESOLVED" not in warnings
        ):
            return SemanticEvidenceSufficiency.SUFFICIENT
        return SemanticEvidenceSufficiency.PARTIAL

    @staticmethod
    def _relationship_roles(
        subject: SemanticComponent,
        object_: SemanticComponent,
    ) -> tuple[str, ...]:
        return DeterministicSemanticCandidateAssessor._unique(
            (
                _COMPONENT_ROLES.get(subject, subject.value),
                _COMPONENT_ROLES.get(object_, object_.value),
            )
        )

    @staticmethod
    def _contextual_role(role: EvidenceRole) -> str:
        return {
            EvidenceRole.CONSEQUENCE: "EFFECT",
            EvidenceRole.TEMPORAL_UPDATE: "CHANGE",
            EvidenceRole.DEADLINE: "SCHEDULE",
            EvidenceRole.COMPARISON: "CHANGE",
        }.get(role, role.value)

    @staticmethod
    def _strength_rank(value: SemanticEvidenceStrength) -> int:
        return {
            SemanticEvidenceStrength.WEAK: 0,
            SemanticEvidenceStrength.MODERATE: 1,
            SemanticEvidenceStrength.STRONG: 2,
        }[value]

    @staticmethod
    def _unique(values: object) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))  # type: ignore[arg-type]
