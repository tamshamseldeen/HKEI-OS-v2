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
_PUBLIC_INSTITUTION_PATTERNS = (
    r"الهيئة القومية للأنفاق",
    r"هيئة النقل(?: العامة| الوطنية)?",
    r"هيئة حكومية",
    r"وزارة النقل",
    r"national transport authority",
    r"public transport authority",
)
_PUBLIC_OPERATION_PATTERNS = (
    r"بدء التشغيل(?: التجريبي)?",
    r"التشغيل(?: التجريبي)?",
    r"انطلاق(?: مرحلة)? التشغيل",
    r"إطلاق",
    r"تشغيل",
    r"launch",
    r"start(?:ing)? operation",
)
_PUBLIC_INFRASTRUCTURE_PATTERNS = (
    r"(?:ل)?منظومة نقل(?: عامة)?",
    r"(?:ل)?منظومة المونوريل",
    r"نظام نقل(?: عام)?",
    r"شبكة سكك حديدية",
    r"مرفق عام",
    r"مشروع بنية تحتية",
    r"بنية تحتية للنقل",
    r"قطار المونوريل",
    r"المونوريل",
    r"مترو(?: الأنفاق)?",
    r"public transport system",
    r"rail system",
    r"public facility",
    r"infrastructure project",
    r"public service infrastructure",
)
_ECONOMIC_INDICATOR_PATTERNS = (
    r"معدل البطالة",
    r"البطالة",
    r"التضخم",
    r"النمو الاقتصادي",
    r"نمو الأنشطة غير النفطية",
    r"نمو القطاعات غير النفطية",
    r"الناتج المحلي(?: الإجمالي)?",
    r"سوق العمل",
    r"مستويات الاستثمار",
    r"الاستثمار",
    r"أسعار الفائدة",
    r"حجم التجارة",
    r"المؤشرات المالية",
    r"unemployment rate",
    r"inflation",
    r"economic growth",
    r"gross domestic product",
    r"GDP",
    r"non-oil growth",
    r"labor market",
    r"investment levels",
    r"interest rates",
    r"trade volumes",
    r"fiscal indicators",
)
_NEGOTIATION_PATTERNS = (
    r"مفاوضات",
    r"المحادثات",
    r"محادثات",
    r"اجتماعات(?: رفيعة المستوى)?",
    r"لقاءات دبلوماسية",
    r"negotiations",
    r"talks",
    r"diplomatic meetings",
)
_STATE_ACTOR_PATTERNS = (
    r"دولتين",
    r"الدولتين",
    r"حكومتين",
    r"الحكومتين",
    r"الولايات المتحدة",
    r"(?:و)?الصين",
    r"واشنطن",
    r"(?:و)?بكين",
    r"دولتان",
    r"حكومتان",
    r"two states",
    r"two governments",
)
_TRADE_NEGOTIATION_PATTERNS = (
    r"التعرفة الجمركية",
    r"الرسوم الجمركية",
    r"القيود التجارية",
    r"التوتر التجاري",
    r"التبادل التجاري",
    r"trade negotiations",
    r"tariffs",
    r"trade restrictions",
    r"sanctions",
)
_RECOMMENDATION_ACTOR_PATTERNS = (
    r"خبراء(?: الأمن السيبراني)?",
    r"الخبراء",
    r"جهة مختصة",
    r"سلطة مختصة",
    r"experts",
    r"authority",
)
_AUDIENCE_PATTERNS = (
    r"الشركات",
    r"المؤسسات(?: المالية)?",
    r"المواطنين",
    r"المستخدمين",
    r"الطلاب",
    r"companies",
    r"institutions",
    r"users",
)
_DIRECTIVE_PATTERNS = (
    r"بضرورة تحديث(?: برامج| أنظمة)? الحماية",
    r"ضرورة تحديث(?: برامج| أنظمة)? الحماية",
    r"تحديث برامج الحماية",
    r"تطبيق أنظمة التشفير",
    r"اتخاذ إجراءات",
    r"يجب[^.؟!؛]{0,80}",
    r"ينصح[^.؟!؛]{0,80}",
    r"أوص[ىت][^.؟!؛]{0,80}",
    r"update protection",
    r"apply encryption",
    r"take action",
)
_CYBERSECURITY_PATTERNS = (
    r"الأمن السيبراني",
    r"البرمجيات الخبيثة",
    r"هجمات الفدية",
    r"هجمات إلكترونية",
    r"التشفير",
    r"حماية البيانات",
    r"برامج الحماية",
    r"أنظمة الحماية",
    r"اختراق",
    r"ثغرات أمنية",
    r"cybersecurity",
    r"malware",
    r"ransomware",
    r"encryption",
    r"data protection",
)
_WEATHER_CONDITION_PATTERNS = (
    r"الأمطار الموسمية الغزيرة",
    r"أمطار غزيرة",
    r"عواصف",
    r"درجات حرارة مرتفعة",
    r"موجة حر",
    r"رياح قوية",
    r"heavy rain",
    r"monsoon rain",
    r"storms",
    r"high temperatures",
    r"heat wave",
    r"strong winds",
)
_WEATHER_EVENT_PATTERNS = (
    r"فيضانات",
    r"سيول مفاجئة",
    r"انزلاقات تربة",
    r"انهيارات أرضية",
    r"أضرار العاصفة",
    r"flooding",
    r"floods",
    r"landslides",
    r"flash floods",
    r"storm damage",
)
_WEATHER_OUTCOME_PATTERNS = (
    r"تشرّد",
    r"تشريد",
    r"إجلاء",
    r"ضحايا",
    r"إغلاق الطرق",
    r"أضرار",
    r"displacement",
    r"evacuation",
    r"casualties",
    r"road closures",
    r"damage",
)
_IMMEDIATE_WEATHER_EVENT_PATTERNS = (
    r"تسببت",
    r"أدت",
    r"اجتاحت",
    r"وقوع",
    r"ضربت",
    r"شهدت",
    r"caused",
    r"swept",
    r"hit",
)
_SCIENCE_FRAMING_PATTERNS = (
    r"دراسة علمية",
    r"بحث علمي",
    r"باحثون",
    r"scientific study",
    r"researchers",
)
_REPORTING_INSTITUTION_PATTERNS = (
    r"وزارة(?: الصحة| التعليم(?: العالي)?| النقل)?",
    r"الوزارة",
    r"الهيئة(?: القومية للأنفاق)?",
    r"الجهاز(?: المركزي)?",
    r"البنك المركزي",
    r"صندوق النقد(?: الدولي)?",
    r"مؤسسة عامة",
    r"جهة حكومية",
    r"ministry",
    r"authority",
    r"central bank",
    r"statistical agency",
)
_INSTITUTIONAL_REPORTING_ACTIONS = (
    r"أعلنت",
    r"أعلن",
    r"كشفت",
    r"كشف",
    r"أكدت",
    r"أكد",
    r"أفادت",
    r"أفاد",
    r"أوضحت",
    r"أوضح",
    r"الانتهاء",
    r"بدء التشغيل",
    r"انطلاق",
    r"حقق(?:ت)?",
    r"تحقيق",
    r"reported",
    r"announced",
    r"revealed",
    r"completed",
    r"launched",
)
_NON_ACTIONABLE_REPORTING_SUBJECTS = (
    r"التصنيفات(?: الدولية| العالمية)?",
    r"ترتيب الجامعات",
    r"مراكز متقدمة",
    r"تقدم",
    r"ارتفاع",
    r"انخفاض",
    r"نمو",
    r"عدد المستفيدين",
    r"الاحتياطيات",
    r"المؤشر",
    r"الأداء",
    r"إنجاز",
    r"الانتهاء من المشروع",
    r"التشغيل التجريبي",
    r"المشروع",
    r"الجامعات",
    r"القطاع",
    r"فحص [^\n.؟!؛]{0,40} مواطن",
    r"ranking",
    r"performance",
    r"achievement",
    r"status",
    r"result",
    r"development",
    r"beneficiaries",
    r"reserves",
)
_ACTIONABLE_GUIDE_PATTERNS = (
    r"شروط",
    r"متطلبات",
    r"المستندات(?: المطلوبة)?",
    r"مستندات",
    r"الوثائق(?: المطلوبة)?",
    r"صورة الهوية",
    r"رسوم(?: التسجيل| التقديم)?",
    r"أهلية",
    r"مؤهل(?:ون|ين)?",
    r"باب التسجيل",
    r"تسجيل (?:الطلاب|الرغبات|المواطنين)",
    r"يمكن (?:للطلاب|للمواطنين|للمستخدمين)",
    r"عبر الموقع",
    r"طريقة التقديم",
    r"كيفية",
    r"خطوات",
    r"اتبع",
    r"يجب",
    r"يتعين",
    r"آخر موعد",
    r"موعد نهائي",
    r"تغلق[^.؟!؛]{0,60}(?:الأحد|الاثنين|الثلاثاء|الأربعاء|الخميس|الجمعة|السبت)",
    r"يستمر حتى",
    r"required documents",
    r"eligibility",
    r"registration",
    r"application procedure",
    r"required fees",
    r"step-by-step",
    r"how to",
    r"deadline",
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
        format_support = self._relationship_supports(
            ordered_relationships,
            prefix="FORMAT_",
        )
        intent_support = self._relationship_supports(
            ordered_relationships,
            prefix="INTENT_",
        )
        actionable = self._has_actionable_guide_structure(
            source=source,
            contextual_evidence=contextual_evidence,
            relationships=ordered_relationships,
            format_support=format_support,
        )
        non_actionable_reporting = (
            not actionable
            and self._has_non_actionable_institutional_reporting(
                source=source,
                relationships=ordered_relationships,
            )
        )
        if non_actionable_reporting:
            format_support = tuple(
                dict.fromkeys(format_support + ("FORMAT_STANDARD_NEWS",))
            )
        format_suppression = (
            ("FORMAT_GUIDE",) if non_actionable_reporting else ()
        )
        return CompositionalSemanticEvidence(
            relationships=ordered_relationships,
            primary_domain_candidates=primary,
            secondary_domain_candidates=secondary,
            format_support=format_support,
            format_suppression=format_suppression,
            intent_support=intent_support,
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

        relationships.extend(
            self._public_infrastructure_relationships(
                text=text,
                source_section=source_section,
                sentence_index=sentence_index,
                local_items=local_items,
            )
        )
        relationships.extend(
            self._economic_indicator_relationships(
                text=text,
                source_section=source_section,
                sentence_index=sentence_index,
                local_items=local_items,
            )
        )
        relationships.extend(
            self._international_negotiation_relationships(
                text=text,
                source_section=source_section,
                sentence_index=sentence_index,
                local_items=local_items,
            )
        )
        relationships.extend(
            self._recommendation_relationships(
                text=text,
                source_section=source_section,
                sentence_index=sentence_index,
                local_items=local_items,
            )
        )
        relationships.extend(
            self._weather_event_relationships(
                text=text,
                source_section=source_section,
                sentence_index=sentence_index,
                local_items=local_items,
            )
        )

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
    def _pattern_matches(
        text: str,
        patterns: tuple[str, ...],
    ) -> tuple[re.Match[str], ...]:
        """Return longest non-overlapping reusable pattern matches in order."""
        candidates = sorted(
            (
                match
                for pattern in patterns
                for match in re.finditer(rf"(?<!\w){pattern}(?!\w)", text, re.IGNORECASE)
            ),
            key=lambda match: (match.start(), -len(match.group(0))),
        )
        accepted: list[re.Match[str]] = []
        for candidate in candidates:
            if any(
                candidate.start() < existing.end()
                and existing.start() < candidate.end()
                for existing in accepted
            ):
                continue
            accepted.append(candidate)
        return tuple(accepted)

    def _public_infrastructure_relationships(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[SemanticRelationship, ...]:
        """Compose official operation of reusable public infrastructure."""
        institutions = self._pattern_matches(text, _PUBLIC_INSTITUTION_PATTERNS)
        operations = self._pattern_matches(text, _PUBLIC_OPERATION_PATTERNS)
        infrastructure = self._pattern_matches(text, _PUBLIC_INFRASTRUCTURE_PATTERNS)
        if not institutions or not operations or not infrastructure:
            return ()
        institution = institutions[0].group(0)
        subject = infrastructure[0].group(0)
        return (
            SemanticRelationship(
                source_section=source_section,
                sentence_index=sentence_index,
                relationship_type=(
                    SemanticRelationshipType.INSTITUTION_BELONGS_TO_DOMAIN
                ),
                subject_component=SemanticComponent.AUTHORITY,
                subject_text=institution,
                object_component=SemanticComponent.PRIMARY_SUBJECT,
                object_text=subject,
                strength=EvidenceStrength.STRONG,
                reason_code="PUBLIC_INFRASTRUCTURE_DOMAIN_COMPOSITION",
                evidence_indexes=self._involved_indexes(
                    local_items,
                    institution,
                    operations[0].group(0),
                    subject,
                    role=EvidenceRole.AUTHORITY,
                ),
                supports=("PRIMARY_DOMAIN_GOVERNMENT",),
                suppresses=(),
            ),
        )

    def _economic_indicator_relationships(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[SemanticRelationship, ...]:
        """Compose macroeconomic indicators with the economy domain."""
        indicators = self._pattern_matches(text, _ECONOMIC_INDICATOR_PATTERNS)
        if len(indicators) == 1 and indicators[0].group(0).lower() in {
            "الاستثمار",
            "investment levels",
        }:
            economy_wide = re.search(
                r"(?<!\w)(?:اقتصاد|اقتصادي|دول|سوق العمل|مالي|تقرير دولي)(?!\w)",
                text,
                re.IGNORECASE,
            )
            if economy_wide is None:
                return ()
        return tuple(
            SemanticRelationship(
                source_section=source_section,
                sentence_index=sentence_index,
                relationship_type=(
                    SemanticRelationshipType.INDICATOR_DESCRIBES_DOMAIN
                ),
                subject_component=SemanticComponent.INDICATOR,
                subject_text=indicator.group(0),
                object_component=SemanticComponent.DOMAIN,
                object_text="ECONOMY",
                strength=EvidenceStrength.STRONG,
                reason_code="ECONOMIC_INDICATOR_DOMAIN_COMPOSITION",
                evidence_indexes=self._involved_indexes(
                    local_items,
                    indicator.group(0),
                ),
                supports=("PRIMARY_DOMAIN_ECONOMY",),
                suppresses=(),
            )
            for indicator in indicators
        )

    def _international_negotiation_relationships(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[SemanticRelationship, ...]:
        """Compose interstate negotiations without matching company talks."""
        negotiations = self._pattern_matches(text, _NEGOTIATION_PATTERNS)
        states = self._pattern_matches(text, _STATE_ACTOR_PATTERNS)
        has_plural_state = any(
            value.group(0).lower()
            in {"دولتين", "الدولتين", "حكومتين", "الحكومتين", "دولتان", "حكومتان", "two states", "two governments"}
            for value in states
        )
        if not negotiations or (len(states) < 2 and not has_plural_state):
            return ()
        trade = self._pattern_matches(text, _TRADE_NEGOTIATION_PATTERNS)
        actor_text = " و".join(match.group(0) for match in states[:2])
        supports = ("PRIMARY_DOMAIN_POLITICS",) + (
            ("SECONDARY_DOMAIN_ECONOMY",) if trade else ()
        )
        return (
            SemanticRelationship(
                source_section=source_section,
                sentence_index=sentence_index,
                relationship_type=SemanticRelationshipType.ACTOR_PERFORMS_ACTION,
                subject_component=SemanticComponent.ACTOR,
                subject_text=actor_text,
                object_component=SemanticComponent.ACTION,
                object_text=negotiations[0].group(0),
                strength=EvidenceStrength.STRONG,
                reason_code="INTERNATIONAL_NEGOTIATION_DOMAIN_COMPOSITION",
                evidence_indexes=self._involved_indexes(
                    local_items,
                    *(match.group(0) for match in states),
                    negotiations[0].group(0),
                    *(match.group(0) for match in trade),
                ),
                supports=supports,
                suppresses=(),
            ),
        )

    def _recommendation_relationships(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[SemanticRelationship, ...]:
        """Compose cybersecurity guidance directed to an audience."""
        actors = self._pattern_matches(text, _RECOMMENDATION_ACTOR_PATTERNS)
        audiences = self._pattern_matches(text, _AUDIENCE_PATTERNS)
        directives = self._pattern_matches(text, _DIRECTIVE_PATTERNS)
        cyber = self._pattern_matches(text, _CYBERSECURITY_PATTERNS)
        if not actors or not audiences or not directives or not cyber:
            return ()
        directive = directives[0].group(0)
        audience = audiences[0].group(0)
        return (
            SemanticRelationship(
                source_section=source_section,
                sentence_index=sentence_index,
                relationship_type=(
                    SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE
                ),
                subject_component=SemanticComponent.RECOMMENDED_ACTION,
                subject_text=directive,
                object_component=SemanticComponent.AFFECTED_AUDIENCE,
                object_text=audience,
                strength=EvidenceStrength.STRONG,
                reason_code="RECOMMENDED_ACTION_AUDIENCE_COMPOSITION",
                evidence_indexes=self._involved_indexes(
                    local_items,
                    actors[0].group(0),
                    audience,
                    directive,
                    *(match.group(0) for match in cyber),
                ),
                supports=(
                    "PRIMARY_DOMAIN_TECHNOLOGY",
                    "FORMAT_SERVICE",
                    "INTENT_KNOW_ACTION",
                ),
                suppresses=(),
            ),
        )

    def _weather_event_relationships(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        local_items: tuple[tuple[int, ContextualEvidenceItem], ...],
    ) -> tuple[SemanticRelationship, ...]:
        """Compose immediate weather conditions with local hazardous events."""
        conditions = self._pattern_matches(text, _WEATHER_CONDITION_PATTERNS)
        events = self._pattern_matches(text, _WEATHER_EVENT_PATTERNS)
        immediate = self._pattern_matches(text, _IMMEDIATE_WEATHER_EVENT_PATTERNS)
        science_framing = self._pattern_matches(text, _SCIENCE_FRAMING_PATTERNS)
        if not events or science_framing or (not conditions and not immediate):
            return ()
        outcomes = self._pattern_matches(text, _WEATHER_OUTCOME_PATTERNS)
        condition = (conditions or events)[0].group(0)
        outcome = (outcomes or events)[0].group(0)
        return (
            SemanticRelationship(
                source_section=source_section,
                sentence_index=sentence_index,
                relationship_type=SemanticRelationshipType.EVENT_HAS_OUTCOME,
                subject_component=SemanticComponent.EVENT,
                subject_text=condition,
                object_component=SemanticComponent.OUTCOME,
                object_text=outcome,
                strength=EvidenceStrength.STRONG,
                reason_code="WEATHER_EVENT_DOMAIN_COMPOSITION",
                evidence_indexes=self._involved_indexes(
                    local_items,
                    condition,
                    *(match.group(0) for match in events),
                    *(match.group(0) for match in outcomes),
                ),
                supports=("PRIMARY_DOMAIN_WEATHER",),
                suppresses=(),
            ),
        )

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

    @staticmethod
    def _relationship_supports(
        relationships: Iterable[SemanticRelationship],
        *,
        prefix: str,
    ) -> tuple[str, ...]:
        """Collect unique strong relationship supports for one namespace."""
        return tuple(
            dict.fromkeys(
                support
                for relationship in relationships
                if relationship.strength is EvidenceStrength.STRONG
                for support in relationship.supports
                if support.startswith(prefix)
            )
        )

    def _has_actionable_guide_structure(
        self,
        *,
        source: NormalizedSource,
        contextual_evidence: ContextualEvidence,
        relationships: tuple[SemanticRelationship, ...],
        format_support: tuple[str, ...],
    ) -> bool:
        """Return whether meaningful reader action exists document-wide."""
        if "FORMAT_SERVICE" in format_support or "FORMAT_GUIDE" in format_support:
            return True
        if any(
            relationship.relationship_type
            is SemanticRelationshipType.RECOMMENDATION_TARGETS_AUDIENCE
            or relationship.subject_component
            in {
                SemanticComponent.REQUIREMENT,
                SemanticComponent.DEADLINE,
                SemanticComponent.RECOMMENDED_ACTION,
            }
            or relationship.object_component
            in {
                SemanticComponent.REQUIREMENT,
                SemanticComponent.DEADLINE,
                SemanticComponent.RECOMMENDED_ACTION,
            }
            for relationship in relationships
        ):
            return True
        if any(
            item.role in {EvidenceRole.REQUIREMENT, EvidenceRole.DEADLINE}
            for item in contextual_evidence.all_items
        ):
            return True
        text = f"{source.title}\n{source.body}"
        return bool(self._pattern_matches(text, _ACTIONABLE_GUIDE_PATTERNS))

    def _has_non_actionable_institutional_reporting(
        self,
        *,
        source: NormalizedSource,
        relationships: tuple[SemanticRelationship, ...],
    ) -> bool:
        """Detect strong institutional status reporting without reader action."""
        institutional_relationships = {
            (relationship.source_section, relationship.sentence_index)
            for relationship in relationships
            if relationship.relationship_type
            in {
                SemanticRelationshipType.AUTHORITY_ACTS_ON_SUBJECT,
                SemanticRelationshipType.INSTITUTION_BELONGS_TO_DOMAIN,
                SemanticRelationshipType.INDICATOR_DESCRIBES_DOMAIN,
            }
            and relationship.strength is EvidenceStrength.STRONG
        }
        for source_section, sentence_index, text in self._source_units(source):
            institution = bool(
                self._pattern_matches(text, _REPORTING_INSTITUTION_PATTERNS)
            ) or (source_section, sentence_index) in institutional_relationships
            reporting = bool(
                self._pattern_matches(text, _INSTITUTIONAL_REPORTING_ACTIONS)
            )
            subject = bool(
                self._pattern_matches(text, _NON_ACTIONABLE_REPORTING_SUBJECTS)
            )
            if institution and reporting and subject:
                return True
        return False
