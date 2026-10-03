"""Unit tests — bias / V5 formulas (MODELO §8, DECISION_PACKS §2.6)."""

from __future__ import annotations

from decimal import Decimal

from financetwin_engine.analytics.bias import (
    calibrate_value,
    compute_bias_stats,
    confidence_for_n,
    deviation_pct,
    offer_calibration,
)


def test_deviation_pct_formula() -> None:
    r = deviation_pct("40000", "32800")
    assert r.deviation_pct is not None
    assert abs(r.deviation_pct - Decimal("0.18")) < Decimal("1e-9")
    assert r.warning is None


def test_deviation_pct_underestimate() -> None:
    r = deviation_pct("100", "109")
    assert r.deviation_pct is not None
    assert abs(r.deviation_pct - Decimal("-0.09")) < Decimal("1e-9")


def test_deviation_pct_forecast_zero() -> None:
    r = deviation_pct("0", "10")
    assert r.deviation_pct is None
    assert r.warning


def test_calibrate_value_section_26() -> None:
    assert abs(calibrate_value("40000", "0.18") - Decimal("32800")) < Decimal("0.01")
    assert abs(calibrate_value("100000", "-0.09") - Decimal("109000")) < Decimal("0.01")


def test_bias_stats_median_and_confidence() -> None:
    s2 = compute_bias_stats([Decimal("0.10"), Decimal("0.20")])
    assert s2.n_observations == 2
    assert s2.median_bias == Decimal("0.15")
    assert s2.confidence == "low"
    assert confidence_for_n(2) == "low"

    s3 = compute_bias_stats([Decimal("0.10"), Decimal("0.18"), Decimal("0.20")])
    assert s3.n_observations == 3
    assert s3.median_bias == Decimal("0.18")
    assert s3.confidence == "medium"
    assert s3.direction == "overestimate"


def test_offer_calibration_empty_mapping() -> None:
    out = offer_calibration(
        inputs={"x": "1"},
        profiles=[
            {"variable_key": "sales_monthly", "n_observations": 5, "median_bias": "0.1"}
        ],
        key_to_input={},
    )
    assert out["offered"] is False
    assert "mapping" in out["reason"]


def test_offer_calibration_gate_n3() -> None:
    inputs = {"sales_run_rate": "40000", "capex_total": "350000"}
    out2 = offer_calibration(
        inputs=inputs,
        profiles=[
            {
                "variable_key": "sales_monthly",
                "n_observations": 2,
                "median_bias": "0.18",
            }
        ],
    )
    assert out2["offered"] is False
    assert out2["calibrated_inputs"] is None

    out3 = offer_calibration(
        inputs=inputs,
        profiles=[
            {
                "variable_key": "sales_monthly",
                "n_observations": 3,
                "median_bias": "0.18",
            }
        ],
    )
    assert out3["offered"] is True
    assert out3["calibrated_inputs"]["sales_run_rate"] == str(
        calibrate_value("40000", "0.18")
    )
    assert out3["calibrated_inputs"]["capex_total"] == "350000"
