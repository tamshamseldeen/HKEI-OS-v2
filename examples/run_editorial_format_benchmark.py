"""Run deterministic editorial format classification benchmark cases."""

from dataclasses import dataclass
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.formatting.editorial_format import EditorialFormat
from src.workflows.editorial_format_workflow import EditorialFormatWorkflow


@dataclass(frozen=True)
class EditorialFormatBenchmarkCase:
    """Represent one immutable editorial format benchmark case.

    Attributes:
        name: Stable case name.
        title: Raw Arabic source title.
        body: Raw Arabic source body.
        source_name: Source attribution.
        source_url: Optional source URL.
        category: Source category.
        tags: Source tags.
        user_instruction: Requested editorial treatment.
        expected_format: Expected deterministic editorial format.
    """

    name: str
    title: str
    body: str
    source_name: str
    source_url: str | None
    category: str
    tags: tuple[str, ...]
    user_instruction: str
    expected_format: EditorialFormat


BENCHMARK_CASES: tuple[EditorialFormatBenchmarkCase, ...] = (
    EditorialFormatBenchmarkCase(
        name="traffic_service",
        title="المرور السعودي يضاعف غرامات المراوغة بين المركبات بسرعة",
        body=(
            "تواصل السلطات الأمنية في المملكة العربية السعودية رفع مستويات "
            "الأمان على الطرقات عبر التصدي للأنماط القيادية الطائشة. وفي هذا "
            "السياق، وجهت الجهات المختصة في المرور السعودي تنبيهاً شديد اللهجة "
            "لكافة مستخدمي الطريق، مسلطة الضوء على مخاطر القيادة والمراوغة بين "
            "المركبات أثناء السير بسرعة.\n\n"
            "أوضحت منصة المرور الرسمية عبر شبكة X أن المراوغة بين المركبات "
            "تصنف كمخالفة مرورية شديدة الخطورة، ويواجه مرتكبها غرامة تبدأ من "
            "3,000 ريال سعودي وتصل إلى 6,000 ريال سعودي.\n\n"
            "تشمل المخاطر المحتملة فقدان السيطرة على المركبة ووقوع تصادمات "
            "وتعريض مستخدمي الطريق للخطر. وينصح بالالتزام بالمسار المحدد وضبط "
            "السرعة وترك مسافة أمان كافية."
        ),
        source_name="المرور السعودي",
        source_url="https://x.com/eMoroor",
        category="public service",
        tags=("المرور", "غرامات", "السلامة المرورية"),
        user_instruction="اكتب خبرًا خدميًا واضحًا للقارئ العام.",
        expected_format=EditorialFormat.SERVICE,
    ),
    EditorialFormatBenchmarkCase(
        name="sports_feature",
        title="طرابزون سبور التركي.. حقائق مثيرة عن فريق محمد صلاح الجديد",
        body=(
            "يتناول التقرير تاريخ نادي طرابزون سبور، وتأسيسه، وعلاقته بمدينة "
            "طرابزون، وتحديه لهيمنة أندية إسطنبول، والرقم 61، وملعبه المقام قرب "
            "البحر الأسود، وأبرز اللاعبين المصريين الذين سبق لهم تمثيل الفريق، "
            "إلى جانب ما ينتظر محمد صلاح داخل النادي."
        ),
        source_name="Editorial benchmark source",
        source_url=None,
        category="sports",
        tags=("محمد صلاح", "طرابزون سبور", "الدوري التركي"),
        user_instruction="اكتب تقريرًا قصصيًا عن النادي الذي ينتظر محمد صلاح.",
        expected_format=EditorialFormat.FEATURE,
    ),
    EditorialFormatBenchmarkCase(
        name="sports_guide",
        title=(
            "السوبر الأوروبي 2026: موعد مباراة باريس سان جيرمان وأستون فيلا "
            "والقنوات الناقلة"
        ),
        body=(
            "تقام مباراة باريس سان جيرمان وأستون فيلا يوم الأربعاء 12 أغسطس "
            "2026 على ملعب ريد بول سالزبورج أرينا. تنطلق المباراة الساعة 22:00 "
            "بتوقيت السعودية و23:00 بتوقيت الإمارات. تنقل المباراة عبر beIN "
            "SPORTS، ويمكن متابعتها عبر TOD وbeIN Connect."
        ),
        source_name="Editorial benchmark source",
        source_url=None,
        category="sports",
        tags=("السوبر الأوروبي", "القنوات الناقلة", "موعد المباراة"),
        user_instruction="اكتب دليلًا يتضمن الموعد والقنوات وطرق المشاهدة.",
        expected_format=EditorialFormat.GUIDE,
    ),
    EditorialFormatBenchmarkCase(
        name="sports_result",
        title="برشلونة يهزم ريال مدريد بثلاثية",
        body=(
            "حسم برشلونة مواجهته أمام ريال مدريد بثلاثة أهداف في مباراة قوية. "
            "لم يذكر المصدر أسماء المسجلين أو توقيت الأهداف أو اسم البطولة أو "
            "ملعب اللقاء."
        ),
        source_name="Editorial benchmark source",
        source_url=None,
        category="sports",
        tags=("برشلونة", "ريال مدريد", "نتيجة المباراة"),
        user_instruction="اكتب تقرير نتيجة مختصرًا.",
        expected_format=EditorialFormat.RESULT_REPORT,
    ),
)


def _print_items(label: str, values: tuple[str, ...]) -> None:
    """Print one labeled tuple as bullet lines or ``None``."""
    print(label)
    if values:
        for value in values:
            print(f"- {value}")
    else:
        print("None")
    print()


def run_benchmark(
    workflow: EditorialFormatWorkflow | None = None,
    cases: tuple[EditorialFormatBenchmarkCase, ...] = BENCHMARK_CASES,
) -> int:
    """Run and print all cases, returning zero only when every case matches.

    Args:
        workflow: Optional workflow supplied for isolated testing.
        cases: Ordered benchmark cases to evaluate.

    Returns:
        Zero when every prediction matches, otherwise one.
    """
    active_workflow = workflow if workflow is not None else EditorialFormatWorkflow()
    matched = 0

    for case in cases:
        result = active_workflow.process(
            title=case.title,
            body=case.body,
            source_name=case.source_name,
            source_url=case.source_url,
            category=case.category,
            tags=case.tags,
            user_instruction=case.user_instruction,
        )
        classification = result.format_classification
        is_match = classification.editorial_format is case.expected_format
        matched += int(is_match)

        print(f"=== {case.name} ===")
        print()
        print("Expected Format:")
        print(case.expected_format.value)
        print()
        print("Predicted Format:")
        print(classification.editorial_format.value)
        print()
        print("Confidence:")
        print(classification.confidence.value)
        print()
        print("Match:")
        print("YES" if is_match else "NO")
        print()
        _print_items("Reason Codes:", classification.reason_codes)
        _print_items("Supporting Signals:", classification.supporting_signals)
        _print_items("Warnings:", classification.warnings)

    total = len(cases)
    mismatched = total - matched
    accuracy = (matched / total * 100.0) if total else 0.0
    print("=== SUMMARY ===")
    print()
    print("Total Cases:")
    print(total)
    print()
    print("Matched:")
    print(matched)
    print()
    print("Mismatched:")
    print(mismatched)
    print()
    print("Accuracy:")
    print(f"{accuracy:.2f}%")

    return 0 if mismatched == 0 else 1


def main() -> int:
    """Run the fixed editorial format benchmark."""
    return run_benchmark()


if __name__ == "__main__":
    raise SystemExit(main())
