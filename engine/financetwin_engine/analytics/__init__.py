"""Scenarios, bias / Twin Loop analytics, sensitivity."""

from financetwin_engine.analytics.bias import (
    CANONICAL_VARIABLE_KEYS,
    DECISION_PACK_IDS,
    DECISION_STATUSES,
    BiasStats,
    DeviationResult,
    NEW_SITE_KEY_TO_INPUT,
    PACK_KEY_TO_INPUT,
    bias_direction,
    calibrate_value,
    compute_bias_stats,
    confidence_for_n,
    deviation_pct,
    key_to_input_for_pack,
    offer_calibration,
)
from financetwin_engine.analytics.sensitivity import (
    direct_sensitivity,
    inverse_sensitivity,
    run_analysis,
    stress_tests,
)

__all__ = [
    "CANONICAL_VARIABLE_KEYS",
    "DECISION_PACK_IDS",
    "DECISION_STATUSES",
    "BiasStats",
    "DeviationResult",
    "NEW_SITE_KEY_TO_INPUT",
    "PACK_KEY_TO_INPUT",
    "bias_direction",
    "calibrate_value",
    "compute_bias_stats",
    "confidence_for_n",
    "deviation_pct",
    "key_to_input_for_pack",
    "offer_calibration",
    "direct_sensitivity",
    "inverse_sensitivity",
    "run_analysis",
    "stress_tests",
]
