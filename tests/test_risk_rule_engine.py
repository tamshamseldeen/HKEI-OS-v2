"""Tests for deterministic editorial risk rules."""

from src.assessment.risk_level import RiskLevel
from src.assessment.risk_rule import RiskRule
from src.assessment.risk_rule_engine import RiskRuleEngine
from src.intake.normalized_source import NormalizedSource


def make_source(title: str = "Title", body: str = "Body") -> NormalizedSource:
    """Create a normalized source for rule evaluation.

    Args:
        title: Source title.
        body: Source body.

    Returns:
        A normalized source containing the supplied text.
    """
    return NormalizedSource(title=title, body=body, source_name="Source")


def make_rule(code: str, *keywords: str) -> RiskRule:
    """Create a custom low-risk rule for testing.

    Args:
        code: Rule code.
        *keywords: Keywords assigned to the rule.

    Returns:
        A custom deterministic risk rule.
    """
    return RiskRule(
        code=code,
        topics=("custom",),
        keywords=keywords,
        risk_level=RiskLevel.LOW,
        warnings=(),
        requires_official_source=False,
        requires_human_review=False,
    )


def test_no_matching_rule() -> None:
    """Return no rules when source text contains no keyword."""
    assert RiskRuleEngine().evaluate(make_source()) == ()


def test_one_matching_rule() -> None:
    """Return one rule when one rule matches."""
    rule = make_rule("MATCH", "keyword")

    assert RiskRuleEngine((rule,)).evaluate(make_source(body="keyword")) == (rule,)


def test_multiple_matching_rules() -> None:
    """Return all rules with keywords in the source text."""
    first = make_rule("FIRST", "alpha")
    second = make_rule("SECOND", "beta")

    result = RiskRuleEngine((first, second)).evaluate(
        make_source(body="alpha and beta")
    )

    assert result == (first, second)


def test_matching_from_title() -> None:
    """Match keywords that occur in the title."""
    rule = make_rule("TITLE", "headline")

    assert RiskRuleEngine((rule,)).evaluate(make_source(title="Headline")) == (rule,)


def test_matching_from_body() -> None:
    """Match keywords that occur in the body."""
    rule = make_rule("BODY", "details")

    assert RiskRuleEngine((rule,)).evaluate(make_source(body="More details")) == (rule,)


def test_case_insensitive_english_text_behavior() -> None:
    """Match English keywords without regard to letter case."""
    rule = make_rule("ALERT", "ALERT")

    assert RiskRuleEngine((rule,)).evaluate(make_source(body="Alert issued")) == (rule,)


def test_declaration_order_is_preserved() -> None:
    """Preserve configured order rather than source keyword order."""
    first = make_rule("FIRST", "one")
    second = make_rule("SECOND", "two")

    result = RiskRuleEngine((first, second)).evaluate(
        make_source(body="two appears before one")
    )

    assert result == (first, second)


def test_custom_injected_rules_replace_built_in_rules() -> None:
    """Evaluate supplied rules instead of built-in rules."""
    custom = make_rule("CUSTOM", "custom")

    result = RiskRuleEngine((custom,)).evaluate(
        make_source(body="دواء and custom")
    )

    assert result == (custom,)


def test_no_duplicate_rules_are_returned() -> None:
    """Return an equal matching rule only once."""
    rule = make_rule("DUPLICATE", "first", "second")

    result = RiskRuleEngine((rule, rule)).evaluate(
        make_source(body="first and second")
    )

    assert result == (rule,)


def test_built_in_medical_rule() -> None:
    """Match the built-in medical rule."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="جرعة دواء"))

    assert rule.code == "MEDICAL_HIGH_RISK"
    assert rule.topics == ("medical",)
    assert rule.risk_level is RiskLevel.HIGH
    assert rule.warnings == (
        "HIGH_RISK_CONTENT",
        "OFFICIAL_SOURCE_REQUIRED",
        "HUMAN_REVIEW_REQUIRED",
    )
    assert rule.requires_official_source is True
    assert rule.requires_human_review is True


def test_built_in_legal_rule() -> None:
    """Match the built-in legal rule."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="حكم قضائي"))

    assert rule.code == "LEGAL_HIGH_RISK"


def test_isolated_traffic_fine_language_is_not_legal_high_risk() -> None:
    """Do not treat isolated generic fine and penalty words as legal context."""
    matches = RiskRuleEngine().evaluate(
        make_source(body="تبدأ الغرامة من 3,000 ريال وتطبق العقوبة على المخالف")
    )

    assert "LEGAL_HIGH_RISK" not in tuple(rule.code for rule in matches)


def test_public_service_penalty_rule() -> None:
    """Match traffic violations as ordered medium-risk public service content."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="هذه مخالفة مرورية"))

    assert rule.code == "PUBLIC_SERVICE_PENALTY_MEDIUM_RISK"
    assert rule.topics == ("public_service_penalty",)
    assert rule.risk_level is RiskLevel.MEDIUM
    assert rule.warnings == (
        "OFFICIAL_SOURCE_REQUIRED",
        "TIME_SENSITIVE_INFORMATION",
    )
    assert rule.requires_official_source is True
    assert rule.requires_human_review is False


def test_legal_context_fines_and_punishments_remain_high_risk() -> None:
    """Keep judicial fines and criminal punishments in the legal HIGH rule."""
    engine = RiskRuleEngine()

    court = engine.evaluate(make_source(body="أصدرت المحكمة غرامة قضائية"))
    criminal = engine.evaluate(make_source(body="تتضمن القضية عقوبة جنائية"))

    assert tuple(rule.code for rule in court) == ("LEGAL_HIGH_RISK",)
    assert tuple(rule.code for rule in criminal) == ("LEGAL_HIGH_RISK",)


def test_built_in_financial_rule() -> None:
    """Match the built-in financial rule."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="استثمار في أسهم"))

    assert rule.code == "FINANCIAL_HIGH_RISK"


def test_government_fees_use_public_service_penalty_rule() -> None:
    """Treat generic government fees as medium-risk public service content."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="تحديث رسوم حكومية"))

    assert rule.code == "PUBLIC_SERVICE_PENALTY_MEDIUM_RISK"


def test_built_in_immigration_rule() -> None:
    """Match the built-in immigration rule."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="تصريح عمل"))

    assert rule.code == "IMMIGRATION_HIGH_RISK"


def test_built_in_public_safety_rule() -> None:
    """Match the built-in public safety rule and time warning."""
    (rule,) = RiskRuleEngine().evaluate(make_source(body="تحذير أمني"))

    assert rule.code == "PUBLIC_SAFETY_HIGH_RISK"
    assert rule.warnings == (
        "HIGH_RISK_CONTENT",
        "OFFICIAL_SOURCE_REQUIRED",
        "HUMAN_REVIEW_REQUIRED",
        "TIME_SENSITIVE_INFORMATION",
    )
