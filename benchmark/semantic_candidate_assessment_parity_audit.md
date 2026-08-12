# Semantic Candidate Assessment Parity Audit

```json
{
  "cases_analyzed": 41,
  "assessments_analyzed": 111,
  "batch_metrics": {
    "batch_01": {
      "scientific_status": "HISTORICAL_REGRESSION_CORPUS",
      "case_count": 9,
      "assessment_count": 27,
      "direction_distribution": {
        "SUPPORT": 16,
        "SUPPRESS": 9,
        "NEUTRAL": 0,
        "CONFLICTING": 2
      },
      "strength_distribution": {
        "WEAK": 15,
        "MODERATE": 9,
        "STRONG": 3
      },
      "sufficiency_distribution": {
        "INSUFFICIENT": 15,
        "PARTIAL": 8,
        "SUFFICIENT": 2,
        "CONFLICTED": 2
      },
      "true_sufficient_count": 1,
      "false_sufficient_count": 0,
      "false_sufficiency_rate": 0.0,
      "safe_wrong_counts": {
        "INSUFFICIENT": 8,
        "PARTIAL": 2,
        "SUFFICIENT": 0,
        "CONFLICTED": 0
      },
      "expected_candidate_sufficiency_distribution": {
        "INSUFFICIENT": 2,
        "PARTIAL": 3,
        "SUFFICIENT": 1,
        "CONFLICTED": 1
      },
      "sufficient_precision": 100.0
    },
    "batch_02": {
      "scientific_status": "HISTORICAL_REGRESSION_CORPUS",
      "case_count": 10,
      "assessment_count": 18,
      "direction_distribution": {
        "SUPPORT": 16,
        "SUPPRESS": 1,
        "NEUTRAL": 0,
        "CONFLICTING": 1
      },
      "strength_distribution": {
        "WEAK": 5,
        "MODERATE": 4,
        "STRONG": 9
      },
      "sufficiency_distribution": {
        "INSUFFICIENT": 5,
        "PARTIAL": 6,
        "SUFFICIENT": 6,
        "CONFLICTED": 1
      },
      "true_sufficient_count": 5,
      "false_sufficient_count": 0,
      "false_sufficiency_rate": 0.0,
      "safe_wrong_counts": {
        "INSUFFICIENT": 2,
        "PARTIAL": 1,
        "SUFFICIENT": 0,
        "CONFLICTED": 1
      },
      "expected_candidate_sufficiency_distribution": {
        "INSUFFICIENT": 3,
        "PARTIAL": 3,
        "SUFFICIENT": 5,
        "CONFLICTED": 0
      },
      "sufficient_precision": 100.0
    },
    "batch_03": {
      "scientific_status": "HISTORICAL_REGRESSION_CORPUS",
      "case_count": 8,
      "assessment_count": 22,
      "direction_distribution": {
        "SUPPORT": 15,
        "SUPPRESS": 4,
        "NEUTRAL": 0,
        "CONFLICTING": 3
      },
      "strength_distribution": {
        "WEAK": 8,
        "MODERATE": 8,
        "STRONG": 6
      },
      "sufficiency_distribution": {
        "INSUFFICIENT": 8,
        "PARTIAL": 7,
        "SUFFICIENT": 4,
        "CONFLICTED": 3
      },
      "true_sufficient_count": 4,
      "false_sufficient_count": 0,
      "false_sufficiency_rate": 0.0,
      "safe_wrong_counts": {
        "INSUFFICIENT": 5,
        "PARTIAL": 1,
        "SUFFICIENT": 0,
        "CONFLICTED": 3
      },
      "expected_candidate_sufficiency_distribution": {
        "INSUFFICIENT": 3,
        "PARTIAL": 5,
        "SUFFICIENT": 4,
        "CONFLICTED": 0
      },
      "sufficient_precision": 100.0
    },
    "batch_05": {
      "scientific_status": "SEMANTIC_ADJUDICATION_DEVELOPMENT_CORPUS",
      "case_count": 5,
      "assessment_count": 14,
      "direction_distribution": {
        "SUPPORT": 9,
        "SUPPRESS": 5,
        "NEUTRAL": 0,
        "CONFLICTING": 0
      },
      "strength_distribution": {
        "WEAK": 10,
        "MODERATE": 1,
        "STRONG": 3
      },
      "sufficiency_distribution": {
        "INSUFFICIENT": 10,
        "PARTIAL": 1,
        "SUFFICIENT": 3,
        "CONFLICTED": 0
      },
      "true_sufficient_count": 2,
      "false_sufficient_count": 1,
      "false_sufficiency_rate": 33.33333333333333,
      "safe_wrong_counts": {
        "INSUFFICIENT": 6,
        "PARTIAL": 1,
        "SUFFICIENT": 0,
        "CONFLICTED": 0
      },
      "expected_candidate_sufficiency_distribution": {
        "INSUFFICIENT": 2,
        "PARTIAL": 0,
        "SUFFICIENT": 2,
        "CONFLICTED": 0
      },
      "sufficient_precision": 66.66666666666666
    },
    "batch_06": {
      "scientific_status": "DIAGNOSTIC_DEVELOPMENT_SET",
      "case_count": 9,
      "assessment_count": 30,
      "direction_distribution": {
        "SUPPORT": 21,
        "SUPPRESS": 9,
        "NEUTRAL": 0,
        "CONFLICTING": 0
      },
      "strength_distribution": {
        "WEAK": 21,
        "MODERATE": 5,
        "STRONG": 4
      },
      "sufficiency_distribution": {
        "INSUFFICIENT": 21,
        "PARTIAL": 8,
        "SUFFICIENT": 1,
        "CONFLICTED": 0
      },
      "true_sufficient_count": 1,
      "false_sufficient_count": 0,
      "false_sufficiency_rate": 0.0,
      "safe_wrong_counts": {
        "INSUFFICIENT": 14,
        "PARTIAL": 5,
        "SUFFICIENT": 0,
        "CONFLICTED": 0
      },
      "expected_candidate_sufficiency_distribution": {
        "INSUFFICIENT": 4,
        "PARTIAL": 3,
        "SUFFICIENT": 1,
        "CONFLICTED": 0
      },
      "sufficient_precision": 100.0
    }
  },
  "direction_distribution": {
    "SUPPORT": 77,
    "SUPPRESS": 28,
    "NEUTRAL": 0,
    "CONFLICTING": 6
  },
  "strength_distribution": {
    "WEAK": 59,
    "MODERATE": 27,
    "STRONG": 25
  },
  "sufficiency_distribution": {
    "INSUFFICIENT": 59,
    "PARTIAL": 30,
    "SUFFICIENT": 16,
    "CONFLICTED": 6
  },
  "true_sufficient_count": 13,
  "false_sufficient_count": 1,
  "false_sufficiency_rate": 7.142857142857142,
  "safe_wrong_counts": {
    "INSUFFICIENT": 35,
    "PARTIAL": 10,
    "SUFFICIENT": 0,
    "CONFLICTED": 4
  },
  "expected_candidate_sufficiency_distribution": {
    "INSUFFICIENT": 14,
    "PARTIAL": 14,
    "SUFFICIENT": 13,
    "CONFLICTED": 1,
    "MISSING": 31
  },
  "sufficient_precision": 92.85714285714286,
  "correct_sufficient_preservation": {
    "SUFFICIENT": 12,
    "PARTIAL": 2
  },
  "correct_sufficient_preservation_rate": 85.71428571428571,
  "format_candidate_parity": {
    "ANALYSIS": {
      "assessment_count": 7,
      "sufficient_count": 0,
      "true_sufficient": 0,
      "false_sufficient": 0,
      "partial_count": 2,
      "conflicted_count": 0
    },
    "GUIDE": {
      "assessment_count": 7,
      "sufficient_count": 0,
      "true_sufficient": 0,
      "false_sufficient": 0,
      "partial_count": 0,
      "conflicted_count": 0
    },
    "RESULT_REPORT": {
      "assessment_count": 3,
      "sufficient_count": 0,
      "true_sufficient": 0,
      "false_sufficient": 0,
      "partial_count": 1,
      "conflicted_count": 0
    },
    "SERVICE": {
      "assessment_count": 4,
      "sufficient_count": 0,
      "true_sufficient": 0,
      "false_sufficient": 0,
      "partial_count": 4,
      "conflicted_count": 0
    },
    "STANDARD_NEWS": {
      "assessment_count": 9,
      "sufficient_count": 2,
      "true_sufficient": 1,
      "false_sufficient": 0,
      "partial_count": 0,
      "conflicted_count": 1
    },
    "TREND_UPDATE": {
      "assessment_count": 6,
      "sufficient_count": 0,
      "true_sufficient": 0,
      "false_sufficient": 0,
      "partial_count": 3,
      "conflicted_count": 0
    }
  },
  "topic_role_safety": {
    "AUTHORITY": 0,
    "ACTOR": 0,
    "METHOD": 0
  },
  "competition_metrics": {
    "cases_with_competing_candidates": 20,
    "assessments_with_competitors": 43,
    "conflicted_assessments": 6,
    "cases_where_competition_prevented_sufficient": 20
  },
  "duplicate_evidence_metrics": {
    "cases_with_duplicate_evidence_discounting": 8,
    "cases_where_duplicate_discounting_prevented_strength_inflation": 8,
    "duplicate_only_sufficient": []
  },
  "critical_safety_recheck": {
    "wrong_topic_former_false_resolution": "INSUFFICIENT",
    "wrong_trend_result_boundary": "PARTIAL",
    "wrong_service_fact_check_boundary": "PARTIAL",
    "wrong_temporal_format": "PARTIAL",
    "expected_trend_previously_missing": "NONE"
  },
  "counterfactual_gate_metrics": {
    "counterfactual_wrong_resolved_count": 1,
    "counterfactual_correct_resolved_count": 13,
    "counterfactual_unresolved_wrong_count": 49
  },
  "false_resolution_rate": 2.0,
  "wrong_candidates_kept_unresolved_rate": 98.0,
  "correct_resolution_utility": {
    "correct_resolution_count": 13,
    "correct_candidates_left_partial": 14,
    "correct_candidates_left_insufficient": 14,
    "correct_candidates_left_conflicted": 1,
    "correct_candidates_missing": 31
  },
  "safety_utility_classification": "USEFUL_BUT_UNSAFE",
  "historical_pathologies": [],
  "integration_readiness": "REFINE_ASSESSOR_BEFORE_INTEGRATION",
  "batch_07_required": true,
  "provider_calls": 0
}
```
