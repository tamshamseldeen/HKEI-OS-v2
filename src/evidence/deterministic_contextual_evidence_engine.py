"""Deterministic analysis of reusable contextual editorial evidence."""

import re
from collections.abc import Iterable
from typing import TypeAlias

from src.intake.normalized_source import NormalizedSource

from .contextual_evidence import ContextualEvidence
from .contextual_evidence_item import ContextualEvidenceItem
from .evidence_level import EvidenceLevel
from .evidence_role import EvidenceRole
from .evidence_strength import EvidenceStrength
from .source_section import SourceSection


_PatternSpec: TypeAlias = tuple[
    tuple[str, ...],
    EvidenceRole,
    EvidenceLevel,
    EvidenceStrength,
    tuple[str, ...],
    str,
]

_SCIENCE_CONTEXT = (
    "علماء الفلك",
    "فريق من العلماء",
    "فريق بحثي",
    "اكتشاف كوكب",
    "كوكب خارجي",
    "المجموعة الشمسية",
    "تقرير علمي",
    "دراسة علمية",
    "المرصد الأوروبي",
)
_TECHNOLOGY_CONTEXT = (
    "الذكاء الاصطناعي",
    "أشباه الموصلات",
    "الرقائق الإلكترونية",
    "البطاريات الصلبة",
    "بطاريات الحالة الصلبة",
    "السيارات الكهربائية",
    "مراكز البيانات",
)
_GOVERNMENT_CONTEXT = (
    "مصلحة الضرائب",
    "وزارة التموين",
    "وزارة النقل",
    "وزارة التعليم",
    "وزارة التعليم العالي",
    "هيئة حكومية",
    "الفاتورة الإلكترونية",
    "التسجيل في منظومة",
)
_CULTURE_CONTEXT = (
    "معرض الكتاب",
    "معرض القاهرة الدولي للكتاب",
    "هيئة الكتاب",
    "اكتشاف أثري",
    "التراث العالمي",
)
_ECONOMY_CONTEXT = (
    "البنك المركزي",
    "أسعار الفائدة",
    "سوق العمل",
    "معدل البطالة",
    "العملات المشفرة",
    "الأصول الرقمية",
    "النظام المالي",
    "الإيرادات السياحية",
)
_WORLD_CONTEXT = (
    "الأمم المتحدة",
    "مؤتمر الأمم المتحدة",
    "قمة المناخ",
    "اتفاق دولي",
    "الدول المشاركة",
)
_SERVICE_CONTEXT = (
    "التسجيل قبل",
    "آخر موعد",
    "باب التسجيل",
    "يجب التسجيل",
    "دعت الشركات",
    "دعت المواطنين",
    "دعت المكلفين",
    "اتخاذ الإجراءات",
    "موعد نهائي",
)
_INTERPRETATION_PATTERNS = (
    "يشير تحليل",
    "يشير التقرير إلى",
    "تشير البيانات إلى",
    "يرى محللون",
    "يرى خبراء",
    "بحسب تحليل",
    "وفق تحليل",
    "يعكس ذلك",
    "يعكس هذا",
    "يعني ذلك",
    "يعني هذا",
    "يشير ذلك إلى",
    "يشير هذا إلى",
)
_PREDICTION_PATTERNS = (
    "قد يسهم",
    "قد تسهم",
    "قد يؤدي",
    "قد تؤدي",
    "قد يدفع",
    "قد تدفع",
    "من المتوقع أن",
    "من المرجح أن",
    "يُتوقع أن",
    "يتوقع أن",
    "يتوقع محللون",
    "تشير التوقعات إلى",
    "خلال السنوات المقبلة",
    "خلال الفترة المقبلة",
    "مستقبلاً",
    "مستقبلًا",
)
_CONSEQUENCE_PATTERNS = (
    "بما يؤدي إلى",
    "مما يؤدي إلى",
    "بما يسهم في",
    "مما يسهم في",
    "يؤدي إلى",
    "تؤدي إلى",
    "يسهم في",
    "تسهم في",
    "ينعكس على",
    "تنعكس على",
    "يدفع إلى",
    "تدفع إلى",
    "يساهم في",
    "تساهم في",
)
_UNCERTAINTY_CONTEXT = (
    "قد",
    "ربما",
    "من المتوقع",
    "تشير التقديرات",
    "رجحت",
    "احتمال",
    "محتمل",
    "غير مؤكد",
)
_ATTRIBUTION_CONTEXT = (
    "قال",
    "أعلن",
    "أعلنت",
    "أوضح",
    "أكد",
    "أكدت",
    "أفاد",
    "أفادت",
    "ذكر",
    "ذكرت",
    "بحسب",
    "وفق",
    "حذر",
    "حذرت",
    "دعا",
    "دعت",
)

_PHRASE_SPECS: tuple[_PatternSpec, ...] = (
    (
        _SCIENCE_CONTEXT,
        EvidenceRole.SUBJECT,
        EvidenceLevel.PHRASE,
        EvidenceStrength.STRONG,
        ("TOPIC_SCIENCE",),
        "SCIENCE_CONTEXT_PHRASE",
    ),
    (
        _TECHNOLOGY_CONTEXT,
        EvidenceRole.SUBJECT,
        EvidenceLevel.PHRASE,
        EvidenceStrength.STRONG,
        ("TOPIC_TECHNOLOGY",),
        "TECHNOLOGY_CONTEXT_PHRASE",
    ),
    (
        _GOVERNMENT_CONTEXT,
        EvidenceRole.AUTHORITY,
        EvidenceLevel.PHRASE,
        EvidenceStrength.STRONG,
        ("TOPIC_GOVERNMENT",),
        "GOVERNMENT_CONTEXT_PHRASE",
    ),
    (
        _CULTURE_CONTEXT,
        EvidenceRole.SUBJECT,
        EvidenceLevel.PHRASE,
        EvidenceStrength.STRONG,
        ("TOPIC_CULTURE",),
        "CULTURE_CONTEXT_PHRASE",
    ),
    (
        _ECONOMY_CONTEXT,
        EvidenceRole.SUBJECT,
        EvidenceLevel.PHRASE,
        EvidenceStrength.STRONG,
        ("TOPIC_ECONOMY",),
        "ECONOMY_CONTEXT_PHRASE",
    ),
    (
        _WORLD_CONTEXT,
        EvidenceRole.SUBJECT,
        EvidenceLevel.PHRASE,
        EvidenceStrength.MEDIUM,
        ("TOPIC_WORLD",),
        "WORLD_CONTEXT_PHRASE",
    ),
    (
        _SERVICE_CONTEXT,
        EvidenceRole.REQUIREMENT,
        EvidenceLevel.CONTEXT,
        EvidenceStrength.STRONG,
        ("FORMAT_SERVICE", "INTENT_KNOW_ACTION"),
        "SERVICE_CONTEXT_PATTERN",
    ),
    (
        _UNCERTAINTY_CONTEXT,
        EvidenceRole.UNCERTAINTY,
        EvidenceLevel.CONTEXT,
        EvidenceStrength.STRONG,
        ("CLAIM_UNCERTAIN",),
        "UNCERTAINTY_CONTEXT_PATTERN",
    ),
    (
        _ATTRIBUTION_CONTEXT,
        EvidenceRole.ATTRIBUTION,
        EvidenceLevel.TOKEN,
        EvidenceStrength.MEDIUM,
        ("CLAIM_ATTRIBUTED",),
        "ATTRIBUTION_SIGNAL",
    ),
)

_GENERIC_TOKENS = {
    "فريق": (
        EvidenceRole.ACTOR,
        ("TOPIC_SPORTS",),
        "GENERIC_SPORTS_TOKEN",
    ),
    "هدف": (
        EvidenceRole.SUBJECT,
        ("TOPIC_SPORTS",),
        "GENERIC_SPORTS_TOKEN",
    ),
    "نتيجة": (
        EvidenceRole.SUBJECT,
        ("TOPIC_SPORTS",),
        "GENERIC_SPORTS_TOKEN",
    ),
    "شركة": (
        EvidenceRole.ACTOR,
        ("TOPIC_BUSINESS",),
        "GENERIC_BUSINESS_TOKEN",
    ),
    "شركات": (
        EvidenceRole.ACTOR,
        ("TOPIC_BUSINESS",),
        "GENERIC_BUSINESS_TOKEN",
    ),
    "وزارة": (
        EvidenceRole.AUTHORITY,
        ("TOPIC_GOVERNMENT",),
        "GENERIC_GOVERNMENT_TOKEN",
    ),
}
_DEADLINE_PATTERNS = (
    "قبل نهاية الشهر",
    "حتى يوم",
    "آخر موعد",
    "يغلق يوم",
    "تغلق يوم",
    "قبل يوم",
)
_REQUIREMENT_PATTERNS = (
    "يجب",
    "يتعين",
    "يمكن التسجيل",
    "يستطيع المستخدم",
)
_AFFECTED_AUDIENCE_PATTERNS = (
    "على المواطنين",
    "على الشركات",
    "على الطلاب",
)
_SENTENCE_BOUNDARY = re.compile(r"[.؟!؛\n]+")
_REGISTRATION_INVITATION = re.compile(
    r"(?<!\w)دعت(?!\w).{0,80}?(?<!\w)للتسجيل(?!\w)"
)


class DeterministicContextualEvidenceEngine:
    """Extract reusable contextual evidence from supplied source text."""

    def analyze(
        self,
        *,
        source: NormalizedSource,
        user_instruction: str | None = None,
    ) -> ContextualEvidence:
        """Analyze one source into deterministic contextual evidence.

        Args:
            source: Normalized source material to analyze without mutation.
            user_instruction: Optional supplied editorial instruction.

        Returns:
            Exactly one sectioned contextual evidence collection.
        """
        headline_items = self._analyze_units(
            ((0, source.title),),
            SourceSection.HEADLINE,
        )
        body_sentences = self._segment_sentences(source.body)
        lead_items = self._analyze_units(
            ((0, body_sentences[0]),) if body_sentences else (),
            SourceSection.LEAD,
        )
        body_items = self._analyze_units(
            tuple(enumerate(body_sentences[1:])),
            SourceSection.BODY,
        )
        instruction_sentences = self._segment_sentences(user_instruction or "")
        user_instruction_items = self._analyze_units(
            tuple(enumerate(instruction_sentences)),
            SourceSection.USER_INSTRUCTION,
        )
        all_items = (
            headline_items
            + lead_items
            + body_items
            + user_instruction_items
        )
        return ContextualEvidence(
            headline_items=headline_items,
            lead_items=lead_items,
            body_items=body_items,
            metadata_items=(),
            user_instruction_items=user_instruction_items,
            warnings=() if all_items else ("CONTEXTUAL_EVIDENCE_EMPTY",),
        )

    @staticmethod
    def _segment_sentences(text: str) -> tuple[str, ...]:
        """Split supplied text at supported boundaries in original order.

        Args:
            text: Supplied body or instruction text.

        Returns:
            Non-empty trimmed text segments in discovery order.
        """
        return tuple(
            segment.strip()
            for segment in _SENTENCE_BOUNDARY.split(text)
            if segment.strip()
        )

    def _analyze_units(
        self,
        units: Iterable[tuple[int, str]],
        source_section: SourceSection,
    ) -> tuple[ContextualEvidenceItem, ...]:
        """Analyze ordered bounded units for one structural section."""
        items: list[ContextualEvidenceItem] = []
        for sentence_index, text in units:
            items.extend(
                self._analyze_text(
                    text=text,
                    source_section=source_section,
                    sentence_index=sentence_index,
                )
            )
        return self._deduplicate(items)

    def _analyze_text(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
    ) -> tuple[ContextualEvidenceItem, ...]:
        """Create phrase, context, token, and suppression evidence for one unit."""
        contextual_matches: list[tuple[int, int, ContextualEvidenceItem]] = []
        sequence = 0
        science_context_present = False
        for spec in _PHRASE_SPECS:
            terms, role, level, base_strength, supports, reason_code = spec
            for term in terms:
                for match in self._term_matches(text, term):
                    strength = self._adjust_strength(
                        base_strength,
                        source_section,
                    )
                    contextual_matches.append(
                        (
                            match.start(),
                            sequence,
                            ContextualEvidenceItem(
                                source_section=source_section,
                                sentence_index=sentence_index,
                                matched_text=match.group(0),
                                evidence_level=(
                                    EvidenceLevel.PHRASE
                                    if reason_code == "ATTRIBUTION_SIGNAL"
                                    and " " in match.group(0).strip()
                                    else level
                                ),
                                role=role,
                                strength=strength,
                                reason_code=reason_code,
                                supports=supports,
                                suppresses=(),
                            ),
                        )
                    )
                    sequence += 1
                    if reason_code == "SCIENCE_CONTEXT_PHRASE":
                        science_context_present = True

        contextual_matches.extend(
            self._special_context_matches(
                text=text,
                source_section=source_section,
                sentence_index=sentence_index,
                sequence_start=sequence,
            )
        )
        items = [
            item
            for _, _, item in sorted(
                contextual_matches,
                key=lambda value: (value[0], value[1]),
            )
        ]

        token_matches: list[tuple[int, int, ContextualEvidenceItem]] = []
        for token_sequence, (token, details) in enumerate(_GENERIC_TOKENS.items()):
            role, supports, reason_code = details
            for match in self._term_matches(text, token):
                token_item = ContextualEvidenceItem(
                    source_section=source_section,
                    sentence_index=sentence_index,
                    matched_text=match.group(0),
                    evidence_level=EvidenceLevel.TOKEN,
                    role=role,
                    strength=EvidenceStrength.WEAK,
                    reason_code=reason_code,
                    supports=supports,
                    suppresses=(),
                )
                token_matches.append((match.start(), token_sequence, token_item))
                if token == "فريق" and science_context_present:
                    token_matches.append(
                        (
                            match.start(),
                            token_sequence + len(_GENERIC_TOKENS),
                            ContextualEvidenceItem(
                                source_section=source_section,
                                sentence_index=sentence_index,
                                matched_text=text,
                                evidence_level=EvidenceLevel.CONTEXT,
                                role=EvidenceRole.ACTOR,
                                strength=EvidenceStrength.STRONG,
                                reason_code=(
                                    "SCIENCE_CONTEXT_SUPPRESSES_GENERIC_TEAM"
                                ),
                                supports=(),
                                suppresses=("TOPIC_SPORTS",),
                            ),
                        )
                    )
        items.extend(
            item
            for _, _, item in sorted(
                token_matches,
                key=lambda value: (value[0], value[1]),
            )
        )
        return self._deduplicate(items)

    def _special_context_matches(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        sequence_start: int,
    ) -> list[tuple[int, int, ContextualEvidenceItem]]:
        """Create special service and analytical contextual evidence."""
        matches: list[tuple[int, int, ContextualEvidenceItem]] = []
        sequence = sequence_start

        def append_matches(
            patterns: Iterable[str],
            *,
            role: EvidenceRole,
            strength: EvidenceStrength,
            supports: tuple[str, ...],
            reason_code: str,
        ) -> None:
            nonlocal sequence
            for pattern in patterns:
                for match in self._term_matches(text, pattern):
                    matches.append(
                        (
                            match.start(),
                            sequence,
                            ContextualEvidenceItem(
                                source_section=source_section,
                                sentence_index=sentence_index,
                                matched_text=match.group(0),
                                evidence_level=EvidenceLevel.CONTEXT,
                                role=role,
                                strength=self._adjust_strength(
                                    strength,
                                    source_section,
                                ),
                                reason_code=reason_code,
                                supports=supports,
                                suppresses=(),
                            ),
                        )
                    )
                    sequence += 1

        append_matches(
            _DEADLINE_PATTERNS,
            role=EvidenceRole.DEADLINE,
            strength=EvidenceStrength.STRONG,
            supports=(
                "FORMAT_SERVICE",
                "INTENT_KNOW_ACTION",
                "INTENT_VERIFY_REQUIREMENTS",
            ),
            reason_code="DEADLINE_CONTEXT_PATTERN",
        )
        append_matches(
            _REQUIREMENT_PATTERNS,
            role=EvidenceRole.REQUIREMENT,
            strength=EvidenceStrength.STRONG,
            supports=("FORMAT_SERVICE", "INTENT_KNOW_ACTION"),
            reason_code="REQUIREMENT_CONTEXT_PATTERN",
        )
        append_matches(
            _AFFECTED_AUDIENCE_PATTERNS,
            role=EvidenceRole.AFFECTED_AUDIENCE,
            strength=EvidenceStrength.MEDIUM,
            supports=("FORMAT_SERVICE", "INTENT_KNOW_ACTION"),
            reason_code="AFFECTED_AUDIENCE_CONTEXT_PATTERN",
        )
        analytical_matches = self._analytical_context_matches(
            text=text,
            source_section=source_section,
            sentence_index=sentence_index,
            sequence_start=sequence,
        )
        matches.extend(analytical_matches)
        sequence += len(analytical_matches)

        for registration_match in _REGISTRATION_INVITATION.finditer(text):
            matches.append(
                (
                    registration_match.start(),
                    sequence,
                    ContextualEvidenceItem(
                        source_section=source_section,
                        sentence_index=sentence_index,
                        matched_text=registration_match.group(0),
                        evidence_level=EvidenceLevel.CONTEXT,
                        role=EvidenceRole.REQUIREMENT,
                        strength=EvidenceStrength.STRONG,
                        reason_code="REQUIREMENT_CONTEXT_PATTERN",
                        supports=("FORMAT_SERVICE", "INTENT_KNOW_ACTION"),
                        suppresses=(),
                    ),
                )
            )
            sequence += 1
        return matches

    def _analytical_context_matches(
        self,
        *,
        text: str,
        source_section: SourceSection,
        sentence_index: int,
        sequence_start: int,
    ) -> list[tuple[int, int, ContextualEvidenceItem]]:
        """Create non-overlapping analytical items and one combined item."""
        matches: list[tuple[int, int, ContextualEvidenceItem]] = []
        sequence = sequence_start
        role_spans: dict[EvidenceRole, list[tuple[int, int]]] = {}
        specifications = (
            (
                _INTERPRETATION_PATTERNS,
                EvidenceRole.INTERPRETATION,
                EvidenceStrength.MEDIUM,
                ("FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT"),
                "INTERPRETATION_CONTEXT_PATTERN",
            ),
            (
                _PREDICTION_PATTERNS,
                EvidenceRole.PREDICTION,
                EvidenceStrength.STRONG,
                (
                    "CLAIM_UNCERTAIN",
                    "FORMAT_ANALYSIS",
                    "INTENT_UNDERSTAND_IMPACT",
                ),
                "PREDICTION_CONTEXT_PATTERN",
            ),
            (
                _CONSEQUENCE_PATTERNS,
                EvidenceRole.CONSEQUENCE,
                EvidenceStrength.MEDIUM,
                ("FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT"),
                "CONSEQUENCE_CONTEXT_PATTERN",
            ),
        )
        for patterns, role, strength, supports, reason_code in specifications:
            occupied = role_spans.setdefault(role, [])
            candidates = sorted(
                (
                    match
                    for pattern in patterns
                    for match in self._analytical_term_matches(text, pattern)
                ),
                key=lambda match: (match.start(), -(match.end() - match.start())),
            )
            for match in candidates:
                span = (match.start(), match.end())
                if any(span[0] < end and start < span[1] for start, end in occupied):
                    continue
                occupied.append(span)
                matches.append(
                    (
                        match.start(),
                        sequence,
                        ContextualEvidenceItem(
                            source_section=source_section,
                            sentence_index=sentence_index,
                            matched_text=match.group(0),
                            evidence_level=EvidenceLevel.CONTEXT,
                            role=role,
                            strength=self._adjust_strength(
                                strength,
                                source_section,
                            ),
                            reason_code=reason_code,
                            supports=supports,
                            suppresses=(),
                        ),
                    )
                )
                sequence += 1

        if len(role_spans) >= 2 and sum(bool(spans) for spans in role_spans.values()) >= 2:
            matches.append(
                (
                    0,
                    sequence,
                    ContextualEvidenceItem(
                        source_section=source_section,
                        sentence_index=sentence_index,
                        matched_text=text,
                        evidence_level=EvidenceLevel.STRUCTURAL,
                        role=EvidenceRole.INTERPRETATION,
                        strength=EvidenceStrength.STRONG,
                        reason_code="COMBINED_ANALYTICAL_CONTEXT",
                        supports=("FORMAT_ANALYSIS", "INTENT_UNDERSTAND_IMPACT"),
                        suppresses=(),
                    ),
                )
            )
        return matches

    @staticmethod
    def _analytical_term_matches(text: str, term: str) -> tuple[re.Match[str], ...]:
        """Match an analytical phrase, allowing an attached Arabic conjunction."""
        tokens = term.split()
        expression = r"[\W_]+".join(re.escape(token) for token in tokens)
        return tuple(
            re.finditer(
                rf"(?<!\w)(?:و(?={expression}))?{expression}(?!\w)",
                text,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _term_matches(text: str, term: str) -> tuple[re.Match[str], ...]:
        """Find a literal token or phrase only at complete token boundaries."""
        tokens = term.split()
        expression = r"[\W_]+".join(re.escape(token) for token in tokens)
        return tuple(
            re.finditer(
                rf"(?<!\w){expression}(?!\w)",
                text,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _adjust_strength(
        strength: EvidenceStrength,
        source_section: SourceSection,
    ) -> EvidenceStrength:
        """Apply deterministic structural strength rules without numeric scores."""
        if source_section is SourceSection.USER_INSTRUCTION:
            return EvidenceStrength.STRONG
        if (
            source_section is SourceSection.HEADLINE
            and strength is EvidenceStrength.MEDIUM
        ):
            return EvidenceStrength.STRONG
        return strength

    @staticmethod
    def _deduplicate(
        items: Iterable[ContextualEvidenceItem],
    ) -> tuple[ContextualEvidenceItem, ...]:
        """Remove identical immutable items while preserving first occurrence."""
        return tuple(dict.fromkeys(items))
