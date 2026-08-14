"""Generic document-level Topic subject-versus-consequence composition."""

from __future__ import annotations

import re

from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.intake.normalized_source import NormalizedSource

from .semantic_component import SemanticComponent
from .semantic_relationship import SemanticRelationship
from .semantic_relationship_type import SemanticRelationshipType


_SENTENCE_BOUNDARY = re.compile(r"[.؟!؛\n]+")
_CONSEQUENCE_BOUNDARY = re.compile(
    r"(?:مما|ما)\s+(?:أدى|يؤدي|قد يؤدي|تسبب|يسبب).{0,30}?(?:إلى|في)|"
    r"(?:وأدى|وأدت|وتسبب|وتسببت|وينعكس|وانعكس).{0,30}?(?:إلى|في|على)|"
    r"(?:مع|وسط)\s+(?:تداعيات|آثار|مخاطر)|"
    r"(?:وتشمل|وشملت)\s+(?:الآثار|التداعيات)|"
    r"(?:نتيجة لذلك|ومن آثار ذلك|ومن تداعيات ذلك)",
    re.IGNORECASE,
)

# Bounded editorial concepts, not case phrases. The set deliberately spans the
# legal Topic enum and does not infer centrality from raw occurrence counts.
_DOMAIN_PATTERNS: dict[str, tuple[str, ...]] = {
    "POLITICS": (r"سياس(?:ة|ي|ية)", r"انتخابات", r"برلمان", r"حزب", r"دبلوماسي"),
    "ECONOMY": (r"اقتصاد(?:ي|ية)?", r"تضخم", r"بطالة", r"أسعار", r"سوق العمل", r"النمو"),
    "BUSINESS": (r"شرك(?:ة|ات)", r"الأعمال التجارية", r"نشاط الأعمال", r"مبيعات", r"أرباح", r"استثمار تجاري"),
    "TECHNOLOGY": (r"تقني(?:ة|ات|اً|ا)", r"تكنولوجيا", r"ذكاء اصطناعي", r"منصة رقمية", r"برمجيات"),
    "SPORTS": (r"رياض(?:ة|ي|ية)", r"مباراة", r"بطولة", r"فريق", r"نادي", r"دوري"),
    "GOVERNMENT": (r"حكوم(?:ة|ي|ية)", r"خدمة عامة", r"قرار إداري", r"مرفق عام"),
    "WEATHER": (r"طقس", r"أمطار", r"عاصفة", r"موجة حر", r"درجات الحرارة", r"رياح"),
    "HEALTH": (r"صح(?:ة|ي|ية)", r"مرض", r"وباء", r"عدوى", r"علاج", r"مستشفى", r"تسمم", r"إصابات"),
    "CULTURE": (r"ثقاف(?:ة|ي|ية)", r"تراث", r"متحف", r"فنون", r"أدب"),
    "SCIENCE": (r"علم(?:ي|ية)", r"دراسة بحثية", r"اكتشاف", r"باحثون"),
    "EDUCATION": (r"تعليم", r"مدرس(?:ة|ي|ية)", r"مدارس", r"طلاب", r"جامعة", r"مناهج", r"امتحانات"),
    "CRIME": (r"جريم(?:ة|ةً|ةا|ي)", r"شرطة", r"ضبط", r"اعتقال", r"تحقيق جنائي", r"احتيال", r"مخالفة قانونية", r"إطلاق نار", r"هجوم"),
    "ENTERTAINMENT": (r"ترفيه", r"سينما", r"فيلم", r"مسلسل", r"موسيقى", r"فنان"),
    "WORLD": (r"شؤون دولية", r"نزاع دولي", r"علاقات دولية"),
    "GENERAL": (r"شؤون عامة",),
}


class TopicConsequenceSubjectProtector:
    """Compose primary and consequence roles from bounded document structure."""

    def compose(self, source: NormalizedSource) -> tuple[SemanticRelationship, ...]:
        title = source.title.strip()
        sentences = tuple(
            part.strip() for part in _SENTENCE_BOUNDARY.split(source.body) if part.strip()
        )
        lead = sentences[0] if sentences else ""
        title_primary, title_consequence = self._split_domains(title)
        lead_primary, lead_consequence = self._split_domains(lead)
        has_consequence_structure = any(
            _CONSEQUENCE_BOUNDARY.search(unit)
            for unit in (title, *sentences)
        )
        explicit_dual_central = (
            len(title_primary) > 1
            and bool(re.search(
                r"(?:معا|بالتساوي|على قدم المساواة|دون محور منفرد|موضوعين|محورين|مسارين|متكاملين|في قلب)",
                f"{title} {lead}",
            ))
        )
        if not has_consequence_structure and not explicit_dual_central:
            return ()

        # Headline is the strongest organizing-subject signal. Lead supplies it
        # only for an explicitly elliptical headline.
        primary_occurrences = [
            (domain, SourceSection.HEADLINE, 0) for domain in title_primary
        ]
        repeated_lead_domains = tuple(
            domain for domain in lead_primary if domain in title_primary
        )
        if repeated_lead_domains:
            primary_occurrences.extend(
                (domain, SourceSection.LEAD, 0) for domain in repeated_lead_domains
            )
        elif re.search(r"(?:\.\.\.|…|تفاصيل|تطور جديد)", title):
            primary_occurrences.extend(
                (domain, SourceSection.LEAD, 0) for domain in lead_primary
            )
        consequence_occurrences: list[tuple[str, SourceSection, int]] = [
            (domain, SourceSection.HEADLINE, 0) for domain in title_consequence
        ] + [
            (domain, SourceSection.LEAD, 0) for domain in lead_consequence
        ]
        for index, sentence in enumerate(sentences[1:], start=1):
            _, consequences = self._split_domains(sentence)
            consequence_occurrences.extend(
                (domain, SourceSection.BODY, index) for domain in consequences
            )

        relationships: list[SemanticRelationship] = []
        for domain, primary_section, primary_index in primary_occurrences:
            relationships.append(
                self._relationship(
                    section=primary_section,
                    sentence_index=primary_index,
                    relationship_type=SemanticRelationshipType.SUBJECT_BELONGS_TO_DOMAIN,
                    subject_component=SemanticComponent.PRIMARY_SUBJECT,
                    object_component=SemanticComponent.DOMAIN,
                    domain=domain,
                    reason_code="DOCUMENT_PRIMARY_SUBJECT_DOMAIN",
                    support=f"PRIMARY_DOMAIN_{domain}",
                )
            )
        for domain, section, index in consequence_occurrences:
            relationships.append(
                self._relationship(
                    section=section,
                    sentence_index=index,
                    relationship_type=SemanticRelationshipType.CONSEQUENCE_OF_EVENT,
                    subject_component=SemanticComponent.EVENT,
                    object_component=SemanticComponent.CONSEQUENCE,
                    domain=domain,
                    reason_code="DOCUMENT_CONSEQUENCE_DOMAIN",
                    support=f"SECONDARY_DOMAIN_{domain}",
                )
            )
        return tuple(dict.fromkeys(relationships))

    @classmethod
    def _split_domains(cls, text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        boundary = _CONSEQUENCE_BOUNDARY.search(text)
        if boundary is None:
            return cls._domains(text), ()
        before = text[: boundary.start()]
        after = text[boundary.end() :]
        return cls._domains(before), cls._domains(after)

    @staticmethod
    def _domains(text: str) -> tuple[str, ...]:
        domains = tuple(
            domain
            for domain, patterns in _DOMAIN_PATTERNS.items()
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
        )
        # A school/university used only as the location of an explicit criminal
        # event is an object/location, not independent EDUCATION centrality.
        if (
            "CRIME" in domains
            and "EDUCATION" in domains
            and re.search(r"(?:داخل|في)\s+(?:ال)?(?:مدرسة|جامعة)", text)
        ):
            domains = tuple(domain for domain in domains if domain != "EDUCATION")
        return domains

    @staticmethod
    def _relationship(
        *,
        section: SourceSection,
        sentence_index: int,
        relationship_type: SemanticRelationshipType,
        subject_component: SemanticComponent,
        object_component: SemanticComponent,
        domain: str,
        reason_code: str,
        support: str,
    ) -> SemanticRelationship:
        return SemanticRelationship(
            source_section=section,
            sentence_index=sentence_index,
            relationship_type=relationship_type,
            subject_component=subject_component,
            subject_text="DOCUMENT_EVENT" if subject_component is SemanticComponent.EVENT else domain,
            object_component=object_component,
            object_text=domain,
            strength=EvidenceStrength.STRONG,
            reason_code=reason_code,
            evidence_indexes=(),
            supports=(support,),
            suppresses=(),
        )
