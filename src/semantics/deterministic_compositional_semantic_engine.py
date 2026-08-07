"""Foundational deterministic compositional semantic evidence engine."""

from collections.abc import Iterable
import re

from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.contextual_evidence_item import ContextualEvidenceItem
from src.evidence.evidence_role import EvidenceRole
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource

from .compositional_semantic_evidence import CompositionalSemanticEvidence
from .semantic_component import SemanticComponent
from .semantic_relationship import SemanticRelationship
from .semantic_relationship_type import SemanticRelationshipType


_SENTENCE_BOUNDARY = re.compile(r"[.؟!؛\n]+")
_AUTHORITY_PATTERNS = (
    r"وزارة الصحة والسكان",
    r"وزارة الصحة",
    r"وزارة التعليم العالي والبحث العلمي",
    r"وزارة التعليم العالي",
    r"الهيئة القومية للأنفاق",
    r"مصلحة الضرائب المصرية",
    r"مصلحة الضرائب",
)
_ACTOR_PATTERNS = (
    r"فريق أبحاث بريطاني",
    r"فريق بحثي",
    r"خبراء الأمن السيبراني",
    r"خبراء",
)
_ACTION_TERMS = (
    "تطوير",
    "تقديم",
    "فحوصات",
    "الكشف",
    "انطلاق",
    "إطلاق",
    "تحقيق",
    "طوّر",
    "طور",
    "قدّم",
    "قدم",
    "فحص",
    "بدأ",
    "بدء",
    "أطلق",
    "حذروا",
    "حذرت",
    "حذر",
    "طالبوا",
    "طالبت",
    "طالب",
    "دعت",
    "دعا",
    "حقق",
    "أعلنت",
    "أعلن",
)
_DOMAIN_OBJECT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"الخدمات الطبية والفحوصات المجانية", "HEALTH"),
    (r"تشخيص أورام السرطان(?: المبكرة)?", "HEALTH"),
    (r"التصنيفات العالمية للجامعات", "EDUCATION"),
    (r"الجامعات(?: المصرية)?", "EDUCATION"),
    (r"التعليم العالي", "EDUCATION"),
    (r"القبول الجامعي", "EDUCATION"),
    (r"العملية التعليمية", "EDUCATION"),
    (r"الطلاب", "EDUCATION"),
    (r"الخدمات الطبية", "HEALTH"),
    (r"الفحوصات الطبية", "HEALTH"),
    (r"الفحوصات", "HEALTH"),
    (r"فحوصات", "HEALTH"),
    (r"الصور الطبية", "HEALTH"),
    (r"أورام", "HEALTH"),
    (r"السرطان", "HEALTH"),
    (r"تشخيص", "HEALTH"),
    (r"الشفاء", "HEALTH"),
    (r"الأمراض", "HEALTH"),
    (r"علاج", "HEALTH"),
    (r"بدء التشغيل التجريبي لمنظومة المونوريل", "GOVERNMENT"),
    (r"التشغيل التجريبي لمنظومة المونوريل", "GOVERNMENT"),
    (r"منظومة المونوريل", "GOVERNMENT"),
    (r"تشغيل مرفق عام", "GOVERNMENT"),
    (r"مشروع حكومي", "GOVERNMENT"),
    (r"بنية تحتية", "GOVERNMENT"),
    (r"منظومة نقل", "GOVERNMENT"),
    (r"خدمة حكومية", "GOVERNMENT"),
    (r"مونوريل", "GOVERNMENT"),
    (r"مترو", "GOVERNMENT"),
    (r"هيئة النقل", "GOVERNMENT"),
    (r"هجمات الفدية", "TECHNOLOGY"),
    (r"الأمن السيبراني", "TECHNOLOGY"),
    (r"البرمجيات الخبيثة", "TECHNOLOGY"),
    (r"برامج الحماية", "TECHNOLOGY"),
    (r"الذكاء الاصطناعي", "TECHNOLOGY"),
    (r"خوارزمية", "TECHNOLOGY"),
    (r"التشفير", "TECHNOLOGY"),
)
_AI_MEDICAL_METHOD = re.compile(
    r"(?P<method>الذكاء الاصطناعي).{0,40}?"
    r"(?P<subject>تشخيص\s+أورام\s+السرطان(?:\s+المبكرة)?)"
)
_METHOD_INDICATORS = (
    "باستخدام",
    "باستخدام تقنيات",
    "عبر",
    "من خلال",
    "بالاعتماد على",
    "قادرة على",
    "يساعد في",
    "تستخدم في",
)


class DeterministicCompositionalSemanticEngine:
    """Compose foundational semantic relationships from local source evidence."""

    def compose(
        self,
        *,
        source: NormalizedSource,
        contextual_evidence: ContextualEvidence,
    ) -> CompositionalSemanticEvidence:
        """Compose deterministic local semantic relationships.

        Args:
            source: Normalized source text to inspect without mutation.
            contextual_evidence: Existing local evidence with provenance.

        Returns:
            Exactly one immutable compositional semantic evidence collection.
        """
        indexed_items = tuple(enumerate(contextual_evidence.all_items))
        relationships: list[SemanticRelationship] = []
        for source_section, sentence_index, text in self._source_units(source):
            local_items = tuple(
                (index, item)
                for index, item in indexed_items
                if item.source_section is source_section
                and item.sentence_index == sentence_index
            )
            relationships.extend(
                self._compose_unit(
                    text=text,
                    source_section=source_section,
                    sentence_index=sentence_index,
                    local_items=local_items,
                )
            )
        ordered_relationships = tuple(dict.fromkeys(relationships))
        primary = self._domain_candidates(
            ordered_relationships,
            prefix="PRIMARY_DOMAIN_",
        )
        secondary = self._domain_candidates(
            ordered_relationships,
            prefix="SECONDARY_DOMAIN_",
        )
        return CompositionalSemanticEvidence(
            relationships=ordered_relationships,
            primary_domain_candidates=primary,
            secondary_domain_candidates=secondary,
            format_support=(),
            format_suppression=(),
            intent_support=(),
            warnings=() if ordered_relationships else ("SEMANTIC_COMPOSITION_EMPTY",),
        )

    def _compose_unit(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[SemanticRelationship, ...]:
        """Compose the authorized relationship types inside one local unit."""
        relationships: list[SemanticRelationship] = []
        actions = self._action_matches(text)
        domain_objects = self._domain_object_matches(text)
        authorities = self._authority_matches(text, local_items)
        actors = self._actor_matches(text)

        if actions and domain_objects:
            authority_objects = tuple(
                value
                for value in domain_objects
                if not any(
                    authority.start() <= value[0]
                    and value[1] <= authority.end()
                    for authority in authorities
                )
            )
            primary_object = self._primary_domain_object(
                actions,
                authority_objects or domain_objects,
            )
            object_text, domain = primary_object[2], primary_object[3]
            for authority in authorities:
                supports = (f"PRIMARY_DOMAIN_{domain}",)
                suppresses = (
                    ("PRIMARY_DOMAIN_GOVERNMENT",)
                    if domain != "GOVERNMENT"
                    else ()
                )
                relationships.append(
                    SemanticRelationship(
                        source_section=source_section,
                        sentence_index=sentence_index,
                        relationship_type=(
                            SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT
                        ),
                        subject_component=SemanticComponent.AUTHORITY,
                        subject_text=authority.group(0),
                        object_component=SemanticComponent.PRIMARY_SUBJECT,
                        object_text=object_text,
                        strength=EvidenceStrength.STRONG,
                        reason_code="AUTHORITY_DOMAIN_SUBJECT_COMPOSITION",
                        evidence_indexes=self._involved_indexes(
                            local_items,
                            authority.group(0),
                            object_text,
                            role=EvidenceRole.AUTHORITY,
                        ),
                        supports=supports,
                        suppresses=suppresses,
                    )
                )

        for actor in actors:
            action = self._nearest_action(actor, actions)
            if action is None:
                continue
            relationships.append(
                SemanticRelationship(
                    source_section=source_section,
                    sentence_index=sentence_index,
                    relationship_type=SemanticRelationshipType.ACTOR_PERFORMS_ACTION,
                    subject_component=SemanticComponent.ACTOR,
                    subject_text=actor.group(0),
                    object_component=SemanticComponent.ACTION,
                    object_text=action.group("action"),
                    strength=EvidenceStrength.MEDIUM,
                    reason_code="ACTOR_ACTION_COMPOSITION",
                    evidence_indexes=self._involved_indexes(
                        local_items,
                        actor.group(0),
                        action.group("action"),
                        role=EvidenceRole.ACTOR,
                    ),
                    supports=(),
                    suppresses=(),
                )
            )

        for action in actions:
            target = self._nearest_object_after(action, domain_objects)
            if target is None:
                continue
            relationships.append(
                SemanticRelationship(
                    source_section=source_section,
                    sentence_index=sentence_index,
                    relationship_type=SemanticRelationshipType.ACTION_TARGETS_OBJECT,
                    subject_component=SemanticComponent.ACTION,
                    subject_text=action.group("action"),
                    object_component=SemanticComponent.OBJECT,
                    object_text=target[2],
                    strength=EvidenceStrength.MEDIUM,
                    reason_code="ACTION_DOMAIN_OBJECT_COMPOSITION",
                    evidence_indexes=self._involved_indexes(
                        local_items,
                        action.group("action"),
                        target[2],
                    ),
                    supports=(f"PRIMARY_DOMAIN_{target[3]}",),
                    suppresses=(),
                )
            )

        method_compositions = [
            (
                method_match.group("method"),
                method_match.group("subject"),
                "HEALTH",
            )
            for method_match in _AI_MEDICAL_METHOD.finditer(text)
        ]
        method_compositions.extend(
            self._indicator_method_compositions(text, domain_objects)
        )
        for method_text, subject_text, primary_domain in dict.fromkeys(
            method_compositions
        ):
            relationships.append(
                SemanticRelationship(
                    source_section=source_section,
                    sentence_index=sentence_index,
                    relationship_type=(
                        SemanticRelationshipType.METHOD_APPLIED_TO_SUBJECT
                    ),
                    subject_component=SemanticComponent.METHOD,
                    subject_text=method_text,
                    object_component=SemanticComponent.PRIMARY_SUBJECT,
                    object_text=subject_text,
                    strength=EvidenceStrength.STRONG,
                    reason_code="METHOD_DOMAIN_SUBJECT_COMPOSITION",
                    evidence_indexes=self._involved_indexes(
                        local_items,
                        method_text,
                        subject_text,
                    ),
                    supports=(
                        f"PRIMARY_DOMAIN_{primary_domain}",
                        "SECONDARY_DOMAIN_TECHNOLOGY",
                    ),
                    suppresses=("PRIMARY_DOMAIN_TECHNOLOGY",),
                )
            )
        return tuple(relationships)

    @staticmethod
    def _indicator_method_compositions(
        text: str,
        objects: tuple[tuple[int, int, str, str], ...],
    ) -> tuple[tuple[str, str, str], ...]:
        """Compose technology methods with distinct domain-bearing subjects."""
        if not any(indicator in text for indicator in _METHOD_INDICATORS):
            return ()
        technology_objects = [value for value in objects if value[3] == "TECHNOLOGY"]
        domain_subjects = [value for value in objects if value[3] != "TECHNOLOGY"]
        if not technology_objects or not domain_subjects:
            return ()
        return tuple(
            (method[2], subject[2], subject[3])
            for method in technology_objects
            for subject in domain_subjects
            if method != subject
        )

    @staticmethod
    def _source_units(
        source: NormalizedSource,
    ) -> tuple[tuple[SourceSection, int, str], ...]:
        """Return headline, lead, and body units in contextual source order."""
        body_sentences = tuple(
            segment.strip()
            for segment in _SENTENCE_BOUNDARY.split(source.body)
            if segment.strip()
        )
        units: list[tuple[SourceSection, int, str]] = [
            (SourceSection.HEADLINE, 0, source.title)
        ]
        if body_sentences:
            units.append((SourceSection.LEAD, 0, body_sentences[0]))
            units.extend(
                (SourceSection.BODY, index, sentence)
                for index, sentence in enumerate(body_sentences[1:])
            )
        return tuple(units)

    @staticmethod
    def _authority_matches(
        text: str,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[re.Match[str], ...]:
        """Return explicit local authority phrases in source order."""
        has_authority_context = any(
            item.role is EvidenceRole.AUTHORITY for _, item in local_items
        )
        matches = [
            match
            for pattern in _AUTHORITY_PATTERNS
            for match in re.finditer(rf"(?<!\w){pattern}(?!\w)", text)
        ]
        if not matches and not has_authority_context:
            return ()
        return tuple(
            match
            for match in sorted(matches, key=lambda value: (value.start(), -len(value.group(0))))
            if not any(
                prior.start() == match.start() and prior.end() >= match.end()
                for prior in matches
                if prior is not match
            )
        )

    @staticmethod
    def _actor_matches(text: str) -> tuple[re.Match[str], ...]:
        """Return clear non-authority actor phrases in source order."""
        matches = [
            match
            for pattern in _ACTOR_PATTERNS
            for match in re.finditer(rf"(?<!\w){pattern}(?!\w)", text)
        ]
        return tuple(
            match
            for match in sorted(
                matches,
                key=lambda value: (value.start(), -len(value.group(0))),
            )
            if not any(
                prior.start() == match.start() and prior.end() > match.end()
                for prior in matches
            )
        )

    @staticmethod
    def _action_matches(text: str) -> tuple[re.Match[str], ...]:
        """Return token-aware supported actions in source order."""
        expression = "|".join(re.escape(term) for term in _ACTION_TERMS)
        return tuple(
            re.finditer(
                rf"(?<!\w)(?:و)?(?P<action>{expression})(?!\w)",
                text,
            )
        )

    @staticmethod
    def _domain_object_matches(
        text: str,
    ) -> tuple[tuple[int, int, str, str], ...]:
        """Return longest non-overlapping domain-bearing object spans."""
        candidates = sorted(
            (
                (match.start(), match.end(), match.group(0), domain)
                for pattern, domain in _DOMAIN_OBJECT_PATTERNS
                for match in re.finditer(rf"(?<!\w){pattern}(?!\w)", text)
            ),
            key=lambda value: (value[0], -(value[1] - value[0])),
        )
        accepted: list[tuple[int, int, str, str]] = []
        for candidate in candidates:
            if any(
                candidate[0] < existing[1] and existing[0] < candidate[1]
                for existing in accepted
            ):
                continue
            accepted.append(candidate)
        return tuple(sorted(accepted, key=lambda value: value[0]))

    @staticmethod
    def _primary_domain_object(
        actions: tuple[re.Match[str], ...],
        objects: tuple[tuple[int, int, str, str], ...],
    ) -> tuple[int, int, str, str]:
        """Choose the earliest domain object following any local action."""
        following = [
            value for value in objects if any(value[0] >= action.end() for action in actions)
        ]
        return following[0] if following else objects[0]

    @staticmethod
    def _nearest_action(
        actor: re.Match[str],
        actions: tuple[re.Match[str], ...],
    ) -> re.Match[str] | None:
        """Return the closest local action before or after a clear actor."""
        if not actions:
            return None
        return min(
            actions,
            key=lambda action: min(
                abs(action.start() - actor.end()),
                abs(actor.start() - action.end()),
            ),
        )

    @staticmethod
    def _nearest_object_after(
        action: re.Match[str],
        objects: tuple[tuple[int, int, str, str], ...],
    ) -> tuple[int, int, str, str] | None:
        """Return the nearest domain-bearing object after an action."""
        following = [value for value in objects if value[0] >= action.end()]
        return min(following, key=lambda value: value[0]) if following else None

    @staticmethod
    def _involved_indexes(
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
        *texts: str,
        role: EvidenceRole | None = None,
    ) -> tuple[int, ...]:
        """Return indexes of genuinely related local contextual evidence."""
        return tuple(
            index
            for index, item in local_items
            if (role is not None and item.role is role)
            or any(
                item.matched_text in text or text in item.matched_text
                for text in texts
                if text
            )
        )

    @staticmethod
    def _domain_candidates(
        relationships: Iterable[SemanticRelationship],
        *,
        prefix: str,
    ) -> tuple[str, ...]:
        """Collect unique strong domain candidates in first-occurrence order."""
        return tuple(
            dict.fromkeys(
                support
                for relationship in relationships
                if relationship.strength is EvidenceStrength.STRONG
                for support in relationship.supports
                if support.startswith(prefix)
            )
        )
