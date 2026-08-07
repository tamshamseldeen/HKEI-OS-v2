"""Tests for deterministic independent editorial format classification."""

from dataclasses import replace

import pytest

from src.assessment.risk_level import RiskLevel
from src.assessment.source_risk_assessment import SourceRiskAssessment
from src.assessment.source_status import SourceStatus
from src.assessment.verification_status import VerificationStatus
from src.classification.classification_confidence import ClassificationConfidence
from src.classification.content_type import ContentType
from src.classification.content_type_classification import ContentTypeClassification
from src.facts.extracted_facts import ExtractedFacts
from src.evidence.contextual_evidence import ContextualEvidence
from src.evidence.contextual_evidence_item import ContextualEvidenceItem
from src.evidence.evidence_level import EvidenceLevel
from src.evidence.evidence_role import EvidenceRole
from src.evidence.evidence_strength import EvidenceStrength
from src.evidence.source_section import SourceSection
from src.formatting.deterministic_editorial_format_classifier import (
    DeterministicEditorialFormatClassifier,
)
from src.formatting.editorial_format import EditorialFormat
from src.formatting.editorial_format_classification import (
    EditorialFormatClassification,
)
from src.formatting.editorial_format_confidence import EditorialFormatConfidence
from src.intake.normalized_source import NormalizedSource


def make_source(
    title: str = "عنوان خبري",
    body: str = "تفاصيل خبرية مؤكدة من المصدر.",
    **changes: object,
) -> NormalizedSource:
    """Create representative normalized source material."""
    source = NormalizedSource(title, body, "وكالة الأنباء")
    return replace(source, **changes)


def make_assessment(
    verification: VerificationStatus = VerificationStatus.VERIFIED_EXTERNALLY,
    risk_level: RiskLevel = RiskLevel.LOW,
) -> SourceRiskAssessment:
    """Create a representative source assessment."""
    return SourceRiskAssessment(
        SourceStatus.IDENTIFIED,
        verification,
        risk_level,
        (),
        (),
        False,
        False,
        True,
        ("SOURCE_OK",),
    )


def make_facts(**changes: object) -> ExtractedFacts:
    """Create facts with enough generic evidence to avoid evidence thinness."""
    facts = ExtractedFacts(
        core_facts=("fact",),
        claims=(),
        quotes=(),
        named_people=(),
        organizations=(),
        government_entities=(),
        locations=(),
        countries=(),
        dates=(),
        times=(),
        numbers=(),
        percentages=(),
        currencies=(),
        laws_and_regulations=(),
        products=(),
        events=("event one", "event two", "event three"),
        unknown_information=(),
        attributions=(),
    )
    return replace(facts, **changes)


def make_content(
    content_type: ContentType = ContentType.STANDARD_NEWS,
    confidence: ClassificationConfidence = ClassificationConfidence.MEDIUM,
) -> ContentTypeClassification:
    """Create a representative existing content classification."""
    return ContentTypeClassification(content_type, confidence, (), (), ())


def classify(
    *,
    source: NormalizedSource | None = None,
    assessment: SourceRiskAssessment | None = None,
    facts: ExtractedFacts | None = None,
    content: ContentTypeClassification | None = None,
    instruction: str | None = None,
    contextual_evidence: ContextualEvidence | None = None,
) -> EditorialFormatClassification:
    """Classify representative inputs with optional replacements."""
    return DeterministicEditorialFormatClassifier().classify(
        source=source or make_source(),
        assessment=assessment or make_assessment(),
        facts=facts or make_facts(),
        content_classification=content or make_content(),
        user_instruction=instruction,
        contextual_evidence=contextual_evidence,
    )


def make_context_item(
    label: str,
    *,
    role: EvidenceRole,
    level: EvidenceLevel = EvidenceLevel.CONTEXT,
    strength: EvidenceStrength = EvidenceStrength.STRONG,
) -> ContextualEvidenceItem:
    """Create one contextual format item for integration tests."""
    return ContextualEvidenceItem(
        source_section=SourceSection.LEAD,
        sentence_index=0,
        matched_text="إشارة سياقية",
        evidence_level=level,
        role=role,
        strength=strength,
        reason_code="TEST_CONTEXT",
        supports=(label,),
        suppresses=(),
    )


def make_context(*items: ContextualEvidenceItem) -> ContextualEvidence:
    """Create an immutable contextual evidence collection."""
    return ContextualEvidence((), items, (), (), (), ())


def service_context() -> ContextualEvidence:
    """Create strong requirement and deadline service evidence."""
    return make_context(
        make_context_item("FORMAT_SERVICE", role=EvidenceRole.REQUIREMENT),
        make_context_item("FORMAT_SERVICE", role=EvidenceRole.DEADLINE),
    )


def analysis_context(*, structural: bool = True) -> ContextualEvidence:
    """Create qualified analytical contextual evidence."""
    items = [
        make_context_item(
            "FORMAT_ANALYSIS",
            role=EvidenceRole.INTERPRETATION,
            level=(EvidenceLevel.STRUCTURAL if structural else EvidenceLevel.CONTEXT),
        )
    ]
    if not structural:
        items.append(
            make_context_item(
                "FORMAT_ANALYSIS",
                role=EvidenceRole.PREDICTION,
                strength=EvidenceStrength.MEDIUM,
            )
        )
    return make_context(*items)


def test_context_argument_is_optional_and_none_preserves_exact_output() -> None:
    """Return the identical legacy result when context is omitted or None."""
    classifier = DeterministicEditorialFormatClassifier()
    arguments = {
        "source": make_source(),
        "assessment": make_assessment(),
        "facts": make_facts(),
        "content_classification": make_content(),
    }

    assert classifier.classify(**arguments) == classifier.classify(
        **arguments,
        contextual_evidence=None,
    )


def test_strong_service_context_selects_service_with_structure_signals() -> None:
    """Select high-confidence service from strong requirement and deadline context."""
    result = classify(contextual_evidence=service_context())

    assert result.editorial_format is EditorialFormat.SERVICE
    assert result.confidence is EditorialFormatConfidence.HIGH
    assert result.reason_codes[-2:] == (
        "CONTEXTUAL_FORMAT_EVIDENCE",
        "CONTEXTUAL_SERVICE_STRUCTURE",
    )
    assert result.supporting_signals[-3:] == (
        "CONTEXTUAL_FORMAT_SUPPORT",
        "CONTEXTUAL_REQUIREMENT_STRUCTURE",
        "CONTEXTUAL_DEADLINE_STRUCTURE",
    )


@pytest.mark.parametrize(
    "role",
    (EvidenceRole.AUTHORITY, EvidenceRole.ATTRIBUTION),
)
def test_service_requires_action_deadline_or_audience_role(
    role: EvidenceRole,
) -> None:
    """Do not infer service from authority or other non-action context alone."""
    context = make_context(make_context_item("FORMAT_SERVICE", role=role))

    assert classify(contextual_evidence=context).editorial_format is EditorialFormat.STANDARD_NEWS


def test_structural_or_multi_role_analysis_context_selects_analysis() -> None:
    """Select analysis from structural evidence or two analytical roles."""
    structural = classify(contextual_evidence=analysis_context())
    multi_role = classify(contextual_evidence=analysis_context(structural=False))

    assert structural.editorial_format is EditorialFormat.ANALYSIS
    assert structural.confidence is EditorialFormatConfidence.HIGH
    assert multi_role.editorial_format is EditorialFormat.ANALYSIS
    assert "CONTEXTUAL_ANALYSIS_STRUCTURE" in multi_role.reason_codes
    assert "CONTEXTUAL_INTERPRETATION_STRUCTURE" in multi_role.supporting_signals
    assert "CONTEXTUAL_PREDICTION_STRUCTURE" in multi_role.supporting_signals


def test_weak_isolated_analysis_and_future_reporting_do_not_select_analysis() -> None:
    """Reject an isolated weak analysis item and ordinary future timing."""
    weak = make_context(
        make_context_item(
            "FORMAT_ANALYSIS",
            role=EvidenceRole.INTERPRETATION,
            level=EvidenceLevel.TOKEN,
            strength=EvidenceStrength.WEAK,
        )
    )

    assert classify(contextual_evidence=weak).editorial_format is EditorialFormat.STANDARD_NEWS
    assert classify(
        source=make_source(body="تبدأ المرحلة الثانية الشهر المقبل"),
        contextual_evidence=make_context(),
    ).editorial_format is EditorialFormat.STANDARD_NEWS


def test_context_outweighs_content_type_but_not_explicit_instruction() -> None:
    """Prefer qualified context over transition signals and explicit requests over it."""
    contextual = classify(
        content=make_content(ContentType.EXPLAINER),
        contextual_evidence=analysis_context(),
    )
    explicit = classify(
        instruction="اكتب خبرًا عاجلًا",
        contextual_evidence=service_context(),
    )

    assert contextual.editorial_format is EditorialFormat.ANALYSIS
    assert "CONTEXTUAL_FORMAT_CONFLICT_RESOLVED" in contextual.warnings
    assert explicit.editorial_format is EditorialFormat.BREAKING
    assert "CONTEXTUAL_FORMAT_EVIDENCE" not in explicit.reason_codes


def test_unknown_context_label_is_ignored_without_conflict_warning() -> None:
    """Ignore unsupported labels and avoid inventing a contextual conflict."""
    context = make_context(
        make_context_item("FORMAT_UNKNOWN", role=EvidenceRole.INTERPRETATION)
    )
    result = classify(contextual_evidence=context)

    assert result.editorial_format is EditorialFormat.STANDARD_NEWS
    assert "CONTEXTUAL_FORMAT_CONFLICT_RESOLVED" not in result.warnings


def test_critical_risk_does_not_force_contextual_analysis() -> None:
    """Preserve the critical-risk safety gate for analytical context."""
    result = classify(
        assessment=make_assessment(risk_level=RiskLevel.CRITICAL),
        contextual_evidence=analysis_context(),
    )

    assert result.editorial_format is not EditorialFormat.ANALYSIS


def test_context_input_is_unchanged_and_output_is_deterministic() -> None:
    """Avoid context mutation and return equal output for identical input."""
    context = service_context()
    snapshot = context.all_items

    first = classify(contextual_evidence=context)
    second = classify(contextual_evidence=context)

    assert first == second
    assert context.all_items == snapshot


@pytest.mark.parametrize(
    ("instruction", "facts", "expected", "reason"),
    (
        (
            "تحقق من صحة الادعاء",
            make_facts(claims=("claim",)),
            EditorialFormat.FACT_CHECK,
            "EXPLICIT_FACT_CHECK_FORMAT",
        ),
        (
            "اكتب مقابلة",
            make_facts(quotes=("quote one", "quote two")),
            EditorialFormat.INTERVIEW,
            "EXPLICIT_INTERVIEW_FORMAT",
        ),
        (
            "اكتب دليلًا واضحًا",
            make_facts(dates=("2026-08-05",), numbers=("10",)),
            EditorialFormat.GUIDE,
            "EXPLICIT_GUIDE_FORMAT",
        ),
        (
            "اكتب خبر خدمي",
            make_facts(),
            EditorialFormat.SERVICE,
            "EXPLICIT_SERVICE_FORMAT",
        ),
        (
            "اكتب تقرير نتيجة: من فاز؟",
            make_facts(numbers=("2", "1")),
            EditorialFormat.RESULT_REPORT,
            "EXPLICIT_RESULT_REPORT_FORMAT",
        ),
        (
            "اكتب خبرًا عاجلًا",
            make_facts(),
            EditorialFormat.BREAKING,
            "EXPLICIT_BREAKING_FORMAT",
        ),
        (
            "اشرح الخبر",
            make_facts(),
            EditorialFormat.EXPLAINER,
            "EXPLICIT_EXPLAINER_FORMAT",
        ),
    ),
)
def test_supported_explicit_requests_have_highest_precedence(
    instruction: str,
    facts: ExtractedFacts,
    expected: EditorialFormat,
    reason: str,
) -> None:
    """Select every supported explicit format with high confidence."""
    result = classify(instruction=instruction, facts=facts)

    assert result.editorial_format is expected
    assert result.confidence is EditorialFormatConfidence.HIGH
    assert result.reason_codes == (reason,)


@pytest.mark.parametrize(
    ("instruction", "warning"),
    (
        ("تحقق من صحة الخبر", "FACT_CHECK_EVIDENCE_MISSING"),
        ("اكتب مقابلة", "INTERVIEW_STRUCTURE_MISSING"),
        ("اكتب دليلًا", "GUIDE_STRUCTURE_INSUFFICIENT"),
        ("اكتب تقرير قصصي", "SOURCE_TOO_THIN_FOR_FEATURE"),
        ("اكتب تحليل", "SOURCE_TOO_THIN_FOR_ANALYSIS"),
        ("اكتب بروفايل", "UNSUPPORTED_FORMAT_REQUEST"),
    ),
)
def test_unsupported_explicit_requests_fall_through_safely(
    instruction: str,
    warning: str,
) -> None:
    """Carry exact warnings when explicit formats lack required support."""
    result = classify(instruction=instruction)

    assert result.editorial_format is EditorialFormat.STANDARD_NEWS
    assert warning in result.warnings


def test_rich_explicit_feature_analysis_and_profile_are_supported() -> None:
    """Support depth-sensitive explicit formats with sufficient rich evidence."""
    rich_body = " ".join(f"word{index}" for index in range(310))
    rich_source = make_source(body=rich_body)

    feature = classify(source=rich_source, instruction="اكتب تقرير قصصي")
    analysis = classify(
        source=rich_source,
        facts=make_facts(numbers=("10",), quotes=("quote",)),
        instruction="اكتب تقرير تحليلي",
    )
    profile = classify(source=rich_source, instruction="اكتب بروفايل")

    assert feature.editorial_format is EditorialFormat.FEATURE
    assert analysis.editorial_format is EditorialFormat.ANALYSIS
    assert profile.editorial_format is EditorialFormat.PROFILE


def test_existing_fact_check_and_interview_structures_are_used() -> None:
    """Infer fact-check and interview formats before lower-precedence formats."""
    fact_check = classify(
        facts=make_facts(claims=("claim",)),
        content=make_content(ContentType.FACT_CHECK),
    )
    interview = classify(
        source=make_source(body="س: سؤال؟\nج: إجابة\nس: سؤال؟\nس: سؤال؟"),
        facts=make_facts(quotes=("one", "two", "three")),
    )

    assert fact_check.editorial_format is EditorialFormat.FACT_CHECK
    assert fact_check.supporting_signals == (
        "CONTENT_TYPE_FACT_CHECK",
        "CLAIMS_PRESENT",
    )
    assert interview.editorial_format is EditorialFormat.INTERVIEW


def test_sports_result_requires_result_evidence() -> None:
    """Separate result reports from general sports-topic material."""
    sports = make_content(ContentType.SPORTS_NEWS)

    result = classify(
        source=make_source(title="انتهت المباراة بنتيجة 2-1"),
        facts=make_facts(numbers=("2", "1")),
        content=sports,
    )
    general = classify(
        source=make_source(title="الفريق يستعد للمباراة"),
        content=sports,
    )

    assert result.editorial_format is EditorialFormat.RESULT_REPORT
    assert result.confidence is EditorialFormatConfidence.HIGH
    assert general.editorial_format is EditorialFormat.STANDARD_NEWS


@pytest.mark.parametrize(
    ("source", "facts", "content_type", "expected"),
    (
        (
            make_source(body="موعد المباراة والقنوات الناقلة"),
            make_facts(dates=("2026-08-05",)),
            ContentType.SPORTS_NEWS,
            EditorialFormat.GUIDE,
        ),
        (
            make_source(body="شروط التقديم وخطوات الخدمة والرسوم"),
            make_facts(currencies=("100 SAR",)),
            ContentType.GOVERNMENT_SERVICE_CONTENT,
            EditorialFormat.GUIDE,
        ),
        (
            make_source(body="تحذير حالي: يجب الالتزام بإجراء السلامة"),
            make_facts(),
            ContentType.GOVERNMENT_SERVICE_CONTENT,
            EditorialFormat.SERVICE,
        ),
        (
            make_source(body="غرامة مخالفة المرور وينصح بالالتزام"),
            make_facts(currencies=("3000 SAR",)),
            ContentType.PUBLIC_SERVICE_NEWS,
            EditorialFormat.SERVICE,
        ),
    ),
)
def test_guide_and_service_structures_are_distinguished(
    source: NormalizedSource,
    facts: ExtractedFacts,
    content_type: ContentType,
    expected: EditorialFormat,
) -> None:
    """Distinguish reusable reference structures from current practical news."""
    result = classify(
        source=source,
        facts=facts,
        content=make_content(content_type),
    )

    assert result.editorial_format is expected


def test_rich_feature_and_analysis_require_all_support() -> None:
    """Infer rich feature and analysis only with required grouped evidence."""
    rich_words = " ".join(f"word{index}" for index in range(300))
    feature_text = (
        "تاريخ تأسس النادي وهوية مدينة وجماهير وحكاية لافتة\n\n"
        "قسم أول\n\nقسم ثان\n\n" + rich_words
    )
    analysis_text = "تأثير وتداعيات مستقبلية " + rich_words

    feature = classify(source=make_source(body=feature_text))
    analysis = classify(
        source=make_source(body=analysis_text),
        facts=make_facts(claims=("claim",), quotes=("quote",)),
    )
    thin_feature = classify(
        source=make_source(body="تاريخ وهوية وحكاية\n\nقسم\n\nقسم"),
    )
    thin_analysis = classify(source=make_source(body="تأثير وتداعيات"))

    assert feature.editorial_format is EditorialFormat.FEATURE
    assert analysis.editorial_format is EditorialFormat.ANALYSIS
    assert thin_feature.editorial_format is not EditorialFormat.FEATURE
    assert "SOURCE_TOO_THIN_FOR_FEATURE" in thin_feature.warnings
    assert thin_analysis.editorial_format is not EditorialFormat.ANALYSIS
    assert "SOURCE_TOO_THIN_FOR_ANALYSIS" in thin_analysis.warnings


def test_social_breaking_and_explainer_signals() -> None:
    """Infer trend, breaking, and explainer formats from their exact signals."""
    trend = classify(
        source=make_source(source_url="https://x.com/example"),
        assessment=make_assessment(VerificationStatus.SOURCE_PROVIDED),
    )
    breaking = classify(source=make_source(title="عاجل: قرار الآن"))
    explainer = classify(source=make_source(body="لماذا حدث ذلك وكيف يعمل؟"))
    long_only = classify(
        source=make_source(body=" ".join("خبر" for _ in range(310)))
    )

    assert trend.editorial_format is EditorialFormat.TREND_UPDATE
    assert trend.warnings == ("TREND_VERIFICATION_INCOMPLETE",)
    assert breaking.editorial_format is EditorialFormat.BREAKING
    assert explainer.editorial_format is EditorialFormat.EXPLAINER
    assert long_only.editorial_format is EditorialFormat.STANDARD_NEWS


def test_fallback_confidence_and_topic_independence() -> None:
    """Fallback safely and prevent topic-like types from forcing a format."""
    for content_type in (
        ContentType.HEALTH_CONTENT,
        ContentType.LEGAL_FINANCIAL_HIGH_RISK_CONTENT,
        ContentType.TECHNOLOGY_NEWS,
        ContentType.ECONOMY_NEWS,
    ):
        result = classify(content=make_content(content_type))
        assert result.editorial_format is EditorialFormat.STANDARD_NEWS

    low = classify(
        content=make_content(
            ContentType.STANDARD_NEWS,
            ClassificationConfidence.LOW,
        )
    )
    assert low.confidence is EditorialFormatConfidence.LOW
    assert low.warnings == ("LOW_EDITORIAL_FORMAT_CONFIDENCE",)


def test_exact_precedence_and_explicit_override() -> None:
    """Choose the first supported inferred format unless explicit support wins."""
    source = make_source(
        title="عاجل: انتهت المباراة بنتيجة 2-1",
        body="غرامة وينصح بالالتزام. لماذا وكيف؟",
    )
    facts = make_facts(claims=("claim",), numbers=("2", "1"))
    content = make_content(ContentType.FACT_CHECK)

    inferred = classify(source=source, facts=facts, content=content)
    explicit = classify(
        source=source,
        facts=facts,
        content=content,
        instruction="اكتب خبر خدمي",
    )

    assert inferred.editorial_format is EditorialFormat.FACT_CHECK
    assert explicit.editorial_format is EditorialFormat.SERVICE


def test_outputs_are_deduplicated_deterministic_and_inputs_unchanged() -> None:
    """Return one stable immutable value without changing supplied inputs."""
    source = make_source(body="غرامة غرامة وينصح بالالتزام")
    assessment = make_assessment()
    facts = make_facts(currencies=("3000 SAR", "3000 SAR"))
    content = make_content(ContentType.PUBLIC_SERVICE_NEWS)
    originals = (replace(source), replace(assessment), replace(facts), replace(content))
    classifier = DeterministicEditorialFormatClassifier()

    first = classifier.classify(
        source=source,
        assessment=assessment,
        facts=facts,
        content_classification=content,
    )
    second = classifier.classify(
        source=source,
        assessment=assessment,
        facts=facts,
        content_classification=content,
    )

    assert first == second
    assert isinstance(first, EditorialFormatClassification)
    assert len(first.reason_codes) == len(set(first.reason_codes))
    assert len(first.supporting_signals) == len(set(first.supporting_signals))
    assert len(first.warnings) == len(set(first.warnings))
    assert (source, assessment, facts, content) == originals
