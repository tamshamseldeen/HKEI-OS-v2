"""Deterministic editorial risk rule evaluation."""

from src.intake.normalized_source import NormalizedSource

from .risk_level import RiskLevel
from .risk_rule import RiskRule


_STANDARD_HIGH_RISK_WARNINGS = (
    "HIGH_RISK_CONTENT",
    "OFFICIAL_SOURCE_REQUIRED",
    "HUMAN_REVIEW_REQUIRED",
)

_MVP_RULES = (
    RiskRule(
        code="MEDICAL_HIGH_RISK",
        topics=("medical",),
        keywords=("دواء", "جرعة", "تشخيص", "علاج", "لقاح", "طبيب", "مريض"),
        risk_level=RiskLevel.HIGH,
        warnings=_STANDARD_HIGH_RISK_WARNINGS,
        requires_official_source=True,
        requires_human_review=True,
    ),
    RiskRule(
        code="LEGAL_HIGH_RISK",
        topics=("legal",),
        keywords=(
            "قانون",
            "محكمة",
            "حكم قضائي",
            "دعوى",
            "نيابة",
            "استئناف",
            "حق قانوني",
            "التزام قانوني",
            "عقوبة جنائية",
            "غرامة قضائية",
        ),
        risk_level=RiskLevel.HIGH,
        warnings=_STANDARD_HIGH_RISK_WARNINGS,
        requires_official_source=True,
        requires_human_review=True,
    ),
    RiskRule(
        code="FINANCIAL_HIGH_RISK",
        topics=("financial",),
        keywords=("استثمار", "أسهم", "بورصة", "قرض", "فائدة", "ضريبة"),
        risk_level=RiskLevel.HIGH,
        warnings=_STANDARD_HIGH_RISK_WARNINGS,
        requires_official_source=True,
        requires_human_review=True,
    ),
    RiskRule(
        code="IMMIGRATION_HIGH_RISK",
        topics=("immigration",),
        keywords=("تأشيرة", "إقامة", "هجرة", "ترحيل", "تصريح عمل"),
        risk_level=RiskLevel.HIGH,
        warnings=_STANDARD_HIGH_RISK_WARNINGS,
        requires_official_source=True,
        requires_human_review=True,
    ),
    RiskRule(
        code="PUBLIC_SAFETY_HIGH_RISK",
        topics=("public_safety",),
        keywords=("طوارئ", "إخلاء", "تحذير أمني", "حريق", "انفجار", "حادث خطير"),
        risk_level=RiskLevel.HIGH,
        warnings=(*_STANDARD_HIGH_RISK_WARNINGS, "TIME_SENSITIVE_INFORMATION"),
        requires_official_source=True,
        requires_human_review=True,
    ),
    RiskRule(
        code="PUBLIC_SERVICE_PENALTY_MEDIUM_RISK",
        topics=("public_service_penalty",),
        keywords=(
            "مخالفة مرورية",
            "غرامة مرورية",
            "مخالفات المرور",
            "رسوم حكومية",
            "غرامة مالية مقررة",
            "مخالفة تنظيمية",
        ),
        risk_level=RiskLevel.MEDIUM,
        warnings=("OFFICIAL_SOURCE_REQUIRED", "TIME_SENSITIVE_INFORMATION"),
        requires_official_source=True,
        requires_human_review=False,
    ),
)


class RiskRuleEngine:
    """Evaluate normalized source text against ordered risk rules."""

    def __init__(self, rules: tuple[RiskRule, ...] | None = None) -> None:
        """Initialize the engine with built-in or supplied rules.

        Args:
            rules: Ordered rules to evaluate, or None to load the MVP rules.
        """
        self._rules = _MVP_RULES if rules is None else rules

    def evaluate(self, source: NormalizedSource) -> tuple[RiskRule, ...]:
        """Return every distinct matching rule in declaration order.

        Args:
            source: Normalized source whose title and body will be evaluated.

        Returns:
            Matching rules in their original declaration order.
        """
        text = f"{source.title}\n{source.body}".lower()
        matches: list[RiskRule] = []
        seen: set[RiskRule] = set()

        for rule in self._rules:
            if rule in seen:
                continue
            if any(keyword.lower() in text for keyword in rule.keywords):
                matches.append(rule)
                seen.add(rule)

        return tuple(matches)
