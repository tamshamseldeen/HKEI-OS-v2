"""Generic entity/owner/source protection and event-centrality composition."""

from __future__ import annotations

import re

from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource

from .semantic_component import SemanticComponent
from .semantic_relationship import SemanticRelationship
from .semantic_relationship_type import SemanticRelationshipType


_SENTENCE_BOUNDARY = re.compile(r"[.؟!؛\n]+")
_ENTITY = re.compile(r"(?:شركة|شركات|مجموعة|مؤسسة|وزارة|هيئة|مستشفى|مدرسة|جامعة|ناد(?:ٍ|ي)|company|corporation|ministry|hospital)", re.I)
_COMPANY = re.compile(r"(?:شركة|شركات|مجموعة(?:\s+تجارية|\s+صناعية)?|مؤسسة تجارية|company|corporation|firm)", re.I)
_OWNER = re.compile(r"(?:تملك(?:ها|ه)?|يمتلك(?:ها|ه)?|مملوك(?:ة|اً|ا)?\s+ل|مملوكة\s+من|تابع(?:ة|اً|ا)?\s+ل|أصول?\s+(?:تابعة|مملوكة)|owned by|belongs to)", re.I)
_SOURCE = re.compile(r"(?:أعلنت|أعلن|قالت|قال|أكدت|أكد|أفادت|أفاد|أوضحت|أوضح|كشفت|كشف|صرح(?:ت)?|announced|said|reported)", re.I)
_EXTERNAL_EVENT = re.compile(r"(?:هجوم|استهداف|قصف|نزاع|صراع|اشتباكات|عقوبات|حصار|قرصنة|احتجاز|اعتراض|إجلاء|أزمة دبلوماسية|توتر(?:ات)? أمنية|حادث أمني|تهديد أمني|معبر حدودي|عبر الحدود|cross-border|attack|conflict|sanctions|piracy|security incident)", re.I)
_INTERNATIONAL = re.compile(r"(?:دولي(?:ة|اً|ا)?|بين دولتين|بين البلدين|عبر الحدود|دبلوماسي(?:ة|اً|ا)?|سفارة|قوة بحرية|مياه إقليمية|ممر بحري|حدود|دولة أجنبية|حكومة أجنبية|الأمم المتحدة|international|foreign|geopolitical)", re.I)
_BUSINESS = re.compile(r"(?:عمليات الشركة|تشغيل|إنتاجها|إنتاج الشركة|خطة(?:\s+التوسع|\s+الشركة)|استراتيجية|إدارة تنفيذية|مجلس الإدارة|أرباح|إيرادات|خسائر|مبيعات|استحواذ|اندماج|صفقة|منتج|خدمة مدفوعة|استمرارية الأعمال|استعادة التشغيل|تعطل الإنتاج|تكاليف التشغيل|حصة سوقية|commercial|earnings|operations|management|acquisition)", re.I)
_ECONOMY = re.compile(r"(?:الأسواق|السوق العالمية|مؤشر الأسعار|أسعار المستهلكين|التضخم|الناتج المحلي|ميزان التجارة|التجارة الخارجية|سوق العمل|البطالة|العرض والطلب|إجمالي الإنتاج|القطاع بأكمله|على مستوى القطاع|السياسة النقدية|السياسة المالية|أسعار الفائدة|سعر الصرف|تكلفة الشحن|اقتصاد(?:ي|ية)?|macro|inflation|market-wide|trade balance)", re.I)


class TopicOntologyBoundaryProtector:
    """Compose role-aware primary domains without changing label universes."""

    def compose(self, source: NormalizedSource) -> tuple[SemanticRelationship, ...]:
        title = source.title.strip()
        sentences = tuple(part.strip() for part in _SENTENCE_BOUNDARY.split(source.body) if part.strip())
        lead = sentences[0] if sentences else ""
        later = " ".join(sentences[1:])
        document = " ".join((title, lead, later))

        company = bool(_COMPANY.search(document))
        entity = bool(_ENTITY.search(document))
        owner = bool(_OWNER.search(document))
        source_role = bool(_SOURCE.search(lead) and _ENTITY.search(lead))
        external_framing = bool(_EXTERNAL_EVENT.search(title) and _EXTERNAL_EVENT.search(lead))
        external_continuity = bool(_EXTERNAL_EVENT.search(later) or _INTERNATIONAL.search(later))
        international = bool(_INTERNATIONAL.search(document))
        world_central = external_framing and external_continuity and international
        business_central = self._sustained(_BUSINESS, title, lead, later)
        economy_central = self._sustained(_ECONOMY, title, lead, later)

        relationships: list[SemanticRelationship] = []
        if entity:
            relationships.append(self._secondary_role(
                SemanticRelationshipType.ACTOR_PERFORMS_ACTION,
                SemanticComponent.ACTOR,
                SemanticComponent.OBJECT,
                "ENTITY_TYPE_CONTEXT_ONLY",
                business_context=company,
            ))
        if owner and entity:
            relationships.append(self._secondary_role(
                SemanticRelationshipType.OWNER_CONTROLS_OBJECT,
                SemanticComponent.ACTOR,
                SemanticComponent.OBJECT,
                "OWNER_ROLE_CONTEXT_ONLY",
                business_context=company,
            ))
        if source_role:
            relationships.append(self._secondary_role(
                SemanticRelationshipType.SOURCE_REPORTS_EVENT,
                SemanticComponent.ATTRIBUTION,
                SemanticComponent.EVENT,
                "SOURCE_ROLE_CONTEXT_ONLY",
                business_context=company,
            ))

        domains = []
        if world_central:
            domains.append("WORLD")
        if business_central:
            domains.append("BUSINESS")
        if economy_central:
            domains.append("ECONOMY")
        for domain in domains:
            relationships.append(self._primary_event(domain, competing=len(domains) > 1))
        return tuple(relationships)

    @staticmethod
    def _sustained(pattern: re.Pattern[str], title: str, lead: str, later: str) -> bool:
        """Require coherent treatment across structural sections, not raw counts."""
        sections = sum(bool(pattern.search(section)) for section in (title, lead, later))
        return sections >= 2 and bool(pattern.search(lead))

    @staticmethod
    def _secondary_role(
        relationship_type: SemanticRelationshipType,
        subject_component: SemanticComponent,
        object_component: SemanticComponent,
        reason_code: str,
        *,
        business_context: bool,
    ) -> SemanticRelationship:
        return SemanticRelationship(
            source_section=SourceSection.LEAD,
            sentence_index=0,
            relationship_type=relationship_type,
            subject_component=subject_component,
            subject_text=reason_code.removesuffix("_CONTEXT_ONLY"),
            object_component=object_component,
            object_text=("BUSINESS" if business_context else "NON_TOPIC_ROLE_CONTEXT"),
            strength=EvidenceStrength.WEAK,
            reason_code=reason_code,
            evidence_indexes=(),
            supports=(("SECONDARY_DOMAIN_BUSINESS",) if business_context else ()),
            suppresses=(),
        )

    @staticmethod
    def _primary_event(domain: str, *, competing: bool) -> SemanticRelationship:
        return SemanticRelationship(
            source_section=SourceSection.HEADLINE,
            sentence_index=0,
            relationship_type=SemanticRelationshipType.EVENT_ORGANIZES_SUBJECT,
            subject_component=SemanticComponent.EVENT,
            subject_text="DOCUMENT_PRIMARY_EVENT",
            object_component=SemanticComponent.DOMAIN,
            object_text=domain,
            strength=EvidenceStrength.STRONG,
            reason_code=("TOPIC_BOUNDARY_COMPETING" if competing else "PRIMARY_EVENT_ORGANIZING_DOMAIN"),
            evidence_indexes=(),
            supports=(f"PRIMARY_DOMAIN_{domain}",),
            suppresses=(),
        )
