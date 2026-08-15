"""Build the offline HKEI-221 WORLD/BUSINESS ontology-boundary analysis."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "benchmark/internal_canary/topic_authority_canary_02_human_audit.json"
OUTPUT_JSON = ROOT / "benchmark/topic_world_business_ontology_boundary_analysis.json"
OUTPUT_MD = ROOT / "benchmark/topic_world_business_ontology_boundary_analysis.md"


SCENARIOS = (
    ("WB-001", "WORLD_PRIMARY", "احتجزت جماعة مسلحة طائرة شحن مملوكة لشركة خاصة قرب حدود دولتين، وتركز التغطية على الأزمة الأمنية وجهود الوساطة الدولية.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-002", "WORLD_PRIMARY", "أجلت سفارة أجنبية رعاياها بحافلات تابعة لشركة سياحية بعد اندلاع اشتباكات، ويتابع الخبر مسار الإجلاء والتصعيد الحدودي.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-003", "WORLD_PRIMARY", "أنقذت قوة بحرية دولية ناقلة تملكها مؤسسة تجارية من محاولة قرصنة، وتتناول المادة أمن الممر البحري والتنسيق بين الدول.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-004", "WORLD_PRIMARY", "جمّدت دولتان أصول شركة اتصالات ضمن نزاع دبلوماسي، ويشرح التقرير الخلاف بين الحكومتين ومسار العقوبات.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-005", "WORLD_PRIMARY", "أصاب صاروخ عابر للحدود مصنعًا تديره مجموعة صناعية، بينما تركز المعالجة على تطور النزاع والتحركات الدولية لوقفه.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-006", "WORLD_PRIMARY", "علقت دولة امتياز شركة أجنبية عقب أزمة بين البلدين، ويتصدر الخبر أثر القرار في العلاقات الدولية لا تفاصيل تشغيل الامتياز.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-007", "BUSINESS_PRIMARY", "افتتحت شركة لوجستية مركزًا إقليميًا جديدًا وشرحت خطة التوسع وعدد الوظائف واستراتيجية خدمة العملاء في أسواق عدة.", "CLEARLY_REPRESENTABLE"),
    ("WB-008", "BUSINESS_PRIMARY", "أعلنت مجموعة طيران نتائجها السنوية وهوامش الربح وخطة تحديث الأسطول بعد نمو الطلب على الرحلات الدولية.", "CLEARLY_REPRESENTABLE"),
    ("WB-009", "BUSINESS_PRIMARY", "استحوذت شركة أغذية على منافس أجنبي، وتفصل المادة قيمة الصفقة وتمويلها وخطة دمج العمليات.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-010", "BUSINESS_PRIMARY", "قرر مجلس إدارة شركة صناعية إعادة هيكلة فروعها الخارجية وخفض التكاليف وتغيير الإدارة التنفيذية.", "CLEARLY_REPRESENTABLE"),
    ("WB-011", "BUSINESS_PRIMARY", "أطلقت شركة برمجيات خدمة مدفوعة في أربع دول، وتتمحور التغطية حول المنتج والتسعير وقنوات البيع.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-012", "BUSINESS_PRIMARY", "عدلت شركة تأمين شروط وثائقها لمحفظة دولية، وتركز المادة على إدارة المخاطر التجارية وربحية النشاط.", "CLEARLY_REPRESENTABLE"),
    ("WB-013", "ECONOMY_PRIMARY", "خفضت شركات كبرى إنتاجها، لكن التقرير يقيس الأثر المجمع على التضخم والناتج المحلي ومستوى الأسعار في الاقتصاد.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-014", "ECONOMY_PRIMARY", "رفعت شركات شحن رسومها، وتتابع المادة مؤشر تكلفة النقل وانعكاسه على التجارة وأسعار المستهلكين.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-015", "ECONOMY_PRIMARY", "أظهرت بيانات آلاف الشركات تباطؤ التوظيف، ويحلل الخبر البطالة وسوق العمل على المستوى الوطني.", "CLEARLY_REPRESENTABLE"),
    ("WB-016", "ECONOMY_PRIMARY", "زادت شركات الطاقة صادراتها، ويركز التقرير على ميزان التجارة وإيرادات الدولة وأسعار النفط العالمية.", "REPRESENTABLE_SECONDARY_DIMENSION_LOST"),
    ("WB-017", "GENUINELY_AMBIGUOUS", "استهدف هجوم دولي خط أنابيب تابعًا لشركة، وتوزعت المعالجة بالتساوي بين التصعيد الأمني وتعطل الإنتاج وخطة استعادة التشغيل.", "GENUINELY_FORCED_CHOICE_AMBIGUOUS"),
    ("WB-018", "GENUINELY_AMBIGUOUS", "فرضت دولة عقوبات على مجموعة صناعية فأغلقت مصانعها الخارجية، ويوازن التقرير بين الصراع السياسي واستمرار أعمال الشركة.", "GENUINELY_FORCED_CHOICE_AMBIGUOUS"),
    ("WB-019", "GENUINELY_AMBIGUOUS", "احتجزت سلطات أجنبية سفينة لشركة نقل، وتمنح المادة وزنًا متساويًا للنزاع الدولي والخسائر والعقود المتوقفة.", "GENUINELY_FORCED_CHOICE_AMBIGUOUS"),
    ("WB-020", "GENUINELY_AMBIGUOUS", "تعرضت شركة بنية تحتية لهجوم سيبراني منسوب إلى دولة، ويتساوى شرح التوتر الدولي مع أثره التشغيلي والتجاري.", "GENUINELY_FORCED_CHOICE_AMBIGUOUS"),
    ("WB-021", "OTHER", "عالج مستشفى تملكه شركة خاصة مرضى بعد تفشي عدوى، وتتمحور المادة حول التشخيص والرعاية الصحية.", "CLEARLY_REPRESENTABLE"),
    ("WB-022", "OTHER", "فاز نادٍ مسجل كشركة بمباراة نهائية، ويركز الخبر على أداء اللاعبين والنتيجة الرياضية.", "CLEARLY_REPRESENTABLE"),
    ("WB-023", "OTHER", "اكتشف باحثون ثغرة في منصة لشركة تقنية، وتشرح المادة الخلل البرمجي وطرق الحماية لا أداء الشركة التجاري.", "CLEARLY_REPRESENTABLE"),
    ("WB-024", "OTHER", "أحالت النيابة مدير شركة إلى المحاكمة في قضية تزوير، ويتصدر التحقيق الجنائي والأدلة معالجة الخبر.", "CLEARLY_REPRESENTABLE"),
)


HISTORICAL_PATTERNS = {
    "WORLD_BUSINESS": ("016", "055", "058", "060", "064", "CANARY2-002"),
    "WORLD_ECONOMY": ("022", "055", "058", "074", "082", "086", "089"),
    "BUSINESS_POLITICS_GOVERNMENT": ("005", "015", "040", "060", "064", "CANARY-004"),
    "COMPANY_ENTITY_EXTERNAL_EVENT": ("055", "060", "064", "089", "CANARY2-002"),
}


def build_analysis():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    case = next(item for item in audit["records"] if item["canary_id"] == "CANARY2-002")
    if case["human_correctness"] != "UNSURE" or case["human_expected_topic"] != "UNREVIEWED":
        raise RuntimeError("CANARY2-002 audit boundary state changed")
    expected_counts = Counter(item[1] for item in SCENARIOS)
    representability = Counter(item[3] for item in SCENARIOS)
    historical_unique = sorted(set().union(*map(set, HISTORICAL_PATTERNS.values())))
    return {
        "analysis_id": "topic_world_business_ontology_boundary_analysis",
        "analysis_type": "OFFLINE_ONTOLOGY_DIAGNOSTIC",
        "case_status": "ONTOLOGY_BOUNDARY_REQUIRES_ANALYSIS",
        "canary2_002_human_status": "UNSURE",
        "canary2_002_expected_topic": "UNREVIEWED",
        "concept_distinctions": {
            "ENTITY_IDENTITY": "Who or what legal/organizational entity appears or owns the affected asset.",
            "EVENT_SUBJECT": "The event or condition the headline and lead primarily report.",
            "EDITORIAL_TREATMENT": "The sustained angle, evidence, and explanatory weight given across the article.",
            "DOWNSTREAM_IMPACT": "Consequences that follow from the event but do not become primary merely by being important.",
        },
        "world_semantics_assessment": {
            "intended": "International affairs are central and no more specific supported Topic applies.",
            "coverage": ["international events", "cross-border security", "geopolitical incidents", "international conflict"],
            "finding": "NOT_MERELY_GEOGRAPHIC_BUT_OPERATIONALLY_UNDERSPECIFIED",
            "ambiguity": "The fallback clause conflicts with BUSINESS when a company is central as an affected entity but corporate activity is not the treatment.",
        },
        "business_semantics_assessment": {
            "intended": "Company or corporate activity is central: operations, strategy, performance, transactions, management, products, services, or commercial assets treated commercially.",
            "rejected_interpretation": "Any event involving a company.",
            "finding": "CONCEPTUALLY_NARROW_BUT_OPERATIONAL_WORDING_AND_SIGNALS_OVERBROAD",
        },
        "economy_boundary_assessment": {
            "finding": "NO_PRIMARY_SUPPORT_WITHOUT_MACRO_OR_MARKET_TREATMENT",
            "required_treatment": ["markets", "prices", "trade", "economic indicators", "aggregate supply or production", "financial consequences"],
            "entity_presence_sufficient": False,
        },
        "role_protection": {
            "entity_vs_subject": "PROTECTION_EXISTS_BUT_INCOMPLETE",
            "owner_vs_subject": "OWNER_ROLE_NOT_PROTECTED",
            "source_vs_subject": "SOURCE_ROLE_PARTIALLY_PROTECTED",
            "event_centrality": "REPRESENTED_BUT_NOT_STRONG_ENOUGH_FOR_EXTERNAL_EVENTS",
            "evidence": [
                "Company tokens are weak ACTOR evidence and tests prevent company actor alone from composing PRIMARY_DOMAIN_BUSINESS.",
                "The lexical Topic classifier still awards BUSINESS support for generic company mentions.",
                "No explicit asset-owner semantic role exists.",
                "Attribution distinguishes announcement structure, but company-as-source still emits BUSINESS support.",
                "Headline/lead primary-subject rules exist, while WORLD security-event vocabulary is sparse.",
            ],
        },
        "treatment_tests": {
            "business_primary": ["operational disruption dominates", "financial loss or performance dominates", "production or commercial continuity dominates", "management response dominates", "corporate asset consequences receive sustained commercial treatment"],
            "world_primary": ["international or security event organizes the story", "geopolitical context dominates", "company is an incidental affected participant or source", "event and location significance dominate commercial implications"],
            "genuine_ambiguity": "International/security centrality and sustained corporate operations or commercial consequences receive comparable editorial weight.",
        },
        "historical_corpus_audit": {
            "method": "Static keyword-assisted candidate retrieval followed by title/body inspection; no labels changed and no classifier executed.",
            "pattern_case_ids": {key:list(value) for key,value in HISTORICAL_PATTERNS.items()},
            "pattern_counts": {key:len(value) for key,value in HISTORICAL_PATTERNS.items()},
            "unique_similar_case_ids": historical_unique,
            "unique_similar_case_count": len(historical_unique),
            "historical_relabeling": False,
        },
        "synthetic_boundary_set": [{"scenario_id":sid, "text":text, "human_conceptual_expected_state":state, "representability":rep} for sid,state,text,rep in SCENARIOS],
        "scenario_distribution": dict(expected_counts),
        "representability_counts": dict(representability),
        "single_label_sufficiency_assessment": "SINGLE_LABEL_ADEQUATE_WITH_CLEARER_RULES",
        "primary_secondary_model_evidence": "MIXED_STORIES_SHOW_INFORMATION_LOSS_BUT_CURRENT_EVIDENCE_SUPPORTS_RESEARCH_NOT_IMPLEMENTATION",
        "boundary_failure_types": ["ENTITY_TYPE_DOMINANCE", "OWNER_ROLE_DOMINANCE", "SOURCE_ROLE_DOMINANCE", "EVENT_CENTRALITY_UNDERWEIGHTED", "BUSINESS_DEFINITION_OVERBROAD", "SINGLE_LABEL_INFORMATION_LOSS"],
        "dominant_boundary_failure_type": "EVENT_CENTRALITY_UNDERWEIGHTED",
        "authority_implications": ["AMBIGUOUS_BOUNDARY_BLOCK", "PRIMARY_TOPIC_ONLY_AUTHORITY", "SECONDARY_DOMAIN_DIAGNOSTIC"],
        "provider_confidence_implication": "CONFIDENCE_INSUFFICIENT_FOR_ONTOLOGY_BOUNDARY",
        "human_unsure_semantics": "Insufficient basis to mark an override correct or incorrect under the current ontology; it is neither success, regression, correct, nor incorrect.",
        "recommended_architecture_direction": "D. COMBINE_SEMANTIC_CLARIFICATION_AND_ROLE_PROTECTION",
        "pilot_implication": "TOPIC_ONTOLOGY_SPECIFICATION_REQUIRED_BEFORE_PILOT",
        "pilot_effective_mode": "SHADOW",
        "pilot_state": "STOPPED",
        "provider_calls": 0,
        "production_files_modified": [],
    }


def render_markdown(data):
    return f"""# WORLD vs BUSINESS Topic Ontology Boundary Analysis

Case status: `{data['case_status']}`. CANARY2-002 remains `UNSURE`; no Topic is frozen as truth.

## Finding

The entity, event, treatment, and impact are distinct. A company identity, asset ownership, or announcement source does not by itself make BUSINESS primary. BUSINESS requires sustained corporate or commercial treatment; WORLD requires the international/security event to organize the story; ECONOMY requires macro, market, trade, price, supply, production, or financial-impact treatment.

Current BUSINESS semantics are conceptually narrow but operational signals remain overbroad. WORLD is not merely geographic, yet its international-security boundary is underspecified. Event centrality exists but is underweighted relative to company identity, and no explicit owner role exists.

## Evidence

The historical audit found {data['historical_corpus_audit']['unique_similar_case_count']} unique mixed-pattern candidates without relabeling them. The synthetic set contains 24 new Arabic scenarios: 6 WORLD-primary, 6 BUSINESS-primary, 4 ECONOMY-primary, 4 genuinely ambiguous, and 4 controls.

Representability: {data['representability_counts']['CLEARLY_REPRESENTABLE']} clearly representable, {data['representability_counts']['REPRESENTABLE_SECONDARY_DIMENSION_LOST']} representable with a secondary dimension lost, {data['representability_counts']['GENUINELY_FORCED_CHOICE_AMBIGUOUS']} forced-choice ambiguous, and 0 ontology mismatches.

## Decision

Single-label assessment: `{data['single_label_sufficiency_assessment']}`.

Provider confidence: `{data['provider_confidence_implication']}`.

Architecture direction: `{data['recommended_architecture_direction']}`.

Pilot implication: `{data['pilot_implication']}`. Effective mode remains `SHADOW`; provider calls: 0; production modifications: none.
"""


def main():
    data = build_analysis()
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(data), encoding="utf-8")
    print(data["recommended_architecture_direction"])
    return 0


if __name__ == "__main__": raise SystemExit(main())
