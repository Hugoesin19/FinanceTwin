"""Twin Loop orchestration — Decision / ActualResult / Bias / calibración."""

from __future__ import annotations

from datetime import date
from typing import Any

from financetwin_api.db import Store
from financetwin_engine.analytics.bias import (
    CANONICAL_VARIABLE_KEYS,
    DECISION_PACK_IDS,
    DECISION_STATUSES,
    compute_bias_stats,
    deviation_pct,
    key_to_input_for_pack,
    offer_calibration,
)
from financetwin_engine.calc.decimal_money import D

ALLOWED_TRANSITIONS = {
    "draft": {"approved", "rejected", "deferred", "cancelled"},
    "approved": {"executed", "cancelled"},
    "deferred": {"draft", "approved", "cancelled"},
    "rejected": set(),
    "executed": set(),
    "cancelled": set(),
}

TERMINAL_REQUIRE_RATIONALE = {"approved", "rejected", "executed"}
TERMINAL_REQUIRE_RUN = {"approved", "rejected", "executed"}


def _add_months(ym_or_date: str, months: int) -> str:
    """Return YYYY-MM-DD from decision_date or YYYY-MM + months."""
    if len(ym_or_date) == 7:
        y, m = map(int, ym_or_date.split("-"))
        d0 = date(y, m, 1)
    else:
        d0 = date.fromisoformat(ym_or_date[:10])
    y = d0.year + (d0.month - 1 + months) // 12
    m = (d0.month - 1 + months) % 12 + 1
    day = min(d0.day, 28)
    return date(y, m, day).isoformat()


def default_milestones(decision_date: str) -> list[dict[str, str]]:
    return [
        {"due_date": _add_months(decision_date, 3), "label": "Revisión 3 meses", "status": "pending"},
        {"due_date": _add_months(decision_date, 6), "label": "Revisión 6 meses", "status": "pending"},
        {"due_date": _add_months(decision_date, 12), "label": "Revisión 12 meses", "status": "pending"},
    ]


def forecast_metrics_from_run(run: dict[str, Any]) -> dict[str, Any]:
    results = run.get("results") or {}
    return {
        "investment_metrics": results.get("investment_metrics"),
        "financing_need": results.get("financing_need"),
        "policy_checks": results.get("policy_checks"),
        "inputs_hash": run.get("inputs_hash") or results.get("inputs_hash"),
        "result_hash": results.get("result_hash"),
        "engine_version": run.get("engine_version") or results.get("engine_version"),
    }


def register_decision(
    store: Store,
    *,
    company_id: str,
    title: str,
    decision_pack_id: str,
    decision_date: str,
    status: str,
    calculation_run_id: str,
    rationale: str = "",
    owner_user_id: str = "local",
    owner_label: str | None = None,
    discarded_alternatives: list | None = None,
    accepted_risks: list | None = None,
    policy_exceptions: list | None = None,
    conditions: str | None = None,
    calibrated_scenario_id: str | None = None,
    create_default_milestones: bool = True,
) -> dict[str, Any]:
    if store.get_company(company_id) is None:
        raise KeyError("company not found")
    if decision_pack_id not in DECISION_PACK_IDS:
        raise ValueError(f"unknown decision_pack_id: {decision_pack_id}")
    if status not in DECISION_STATUSES:
        raise ValueError(f"unknown status: {status}")

    run = store.get_calculation_run(calculation_run_id)
    if run is None:
        raise KeyError("calculation_run not found")
    if run["company_id"] != company_id:
        raise ValueError("calculation_run does not belong to company")

    if status in TERMINAL_REQUIRE_RATIONALE and not (rationale or "").strip():
        raise ValueError(f"rationale required for status={status}")
    if status in TERMINAL_REQUIRE_RUN and not calculation_run_id:
        raise ValueError("calculation_run_id required")

    number = store.next_decision_number(company_id)
    forecast = forecast_metrics_from_run(run)
    did = store.create_decision(
        {
            "company_id": company_id,
            "number": number,
            "title": title,
            "decision_pack_id": decision_pack_id,
            "decision_date": decision_date,
            "status": status,
            "scenario_id": run["scenario_id"],
            "model_version_id": run["model_version_id"],
            "engine_version": run["engine_version"],
            "calculation_run_id": calculation_run_id,
            "forecast_metrics": forecast,
            "frozen_projection": {
                "cash_flow": (run.get("results") or {}).get("cash_flow"),
            },
            "rationale": rationale or "",
            "owner_user_id": owner_user_id,
            "owner_label": owner_label,
            "discarded_alternatives": discarded_alternatives or [],
            "accepted_risks": accepted_risks or [],
            "policy_exceptions": policy_exceptions or [],
            "conditions": conditions,
            "calibrated_scenario_id": calibrated_scenario_id,
        }
    )
    if create_default_milestones:
        store.add_milestones(did, default_milestones(decision_date))
    out = store.get_decision(did)
    assert out is not None
    return out


def transition_decision(store: Store, decision_id: str, new_status: str) -> dict[str, Any]:
    dec = store.get_decision(decision_id)
    if dec is None:
        raise KeyError("decision not found")
    allowed = ALLOWED_TRANSITIONS.get(dec["status"], set())
    if new_status not in allowed:
        raise ValueError(f"cannot transition {dec['status']} → {new_status}")
    if new_status in TERMINAL_REQUIRE_RATIONALE and not (dec.get("rationale") or "").strip():
        raise ValueError(f"rationale required for status={new_status}")
    if new_status in TERMINAL_REQUIRE_RUN and not dec.get("calculation_run_id"):
        raise ValueError("calculation_run_id required")
    store.update_decision_status(decision_id, new_status)
    out = store.get_decision(decision_id)
    assert out is not None
    return out


def record_actuals(
    store: Store,
    *,
    decision_id: str,
    period_year_month: str,
    items: list[dict[str, Any]],
    source: str = "manual",
    recorded_by: str | None = None,
) -> dict[str, Any]:
    dec = store.get_decision(decision_id)
    if dec is None:
        raise KeyError("decision not found")
    if dec["status"] != "executed":
        raise ValueError("ActualResult only allowed when decision status=executed")

    warnings: list[str] = []
    saved: list[dict[str, Any]] = []
    for item in items:
        key = item["variable_key"]
        if key not in CANONICAL_VARIABLE_KEYS:
            raise ValueError(
                f"unknown variable_key {key!r}; see MODELO §14 canonical catalog"
            )
        forecast = item["forecast_value"]
        actual = item["actual_value"]
        # Reject floats accidentally passed as JSON numbers → stringify via D
        if isinstance(forecast, float) or isinstance(actual, float):
            raise TypeError("float not allowed in ActualResult; use string Decimal")
        dev = deviation_pct(forecast, actual)
        if dev.warning:
            warnings.append(f"{key}: {dev.warning}")
        rid = store.upsert_actual_result(
            {
                "decision_id": decision_id,
                "period_year_month": period_year_month,
                "variable_key": key,
                "forecast_value": forecast,
                "actual_value": actual,
                "deviation_pct": None if dev.deviation_pct is None else str(dev.deviation_pct),
                "source": item.get("source") or source,
                "recorded_by": recorded_by,
                "notes": item.get("notes"),
            }
        )
        saved.append(
            {
                "id": rid,
                "variable_key": key,
                "forecast_value": str(forecast),
                "actual_value": str(actual),
                "deviation_pct": None if dev.deviation_pct is None else str(dev.deviation_pct),
            }
        )
        _refresh_bias_profile(
            store,
            company_id=dec["company_id"],
            decision_pack_id=dec["decision_pack_id"],
            variable_key=key,
        )

    out = store.get_decision(decision_id)
    assert out is not None
    return {"decision": out, "recorded": saved, "warnings": warnings}


def _refresh_bias_profile(
    store: Store, *, company_id: str, decision_pack_id: str, variable_key: str
) -> None:
    deviations = store.list_deviations_for_pack(company_id, decision_pack_id, variable_key)
    if not deviations:
        store.delete_bias_profile(company_id, decision_pack_id, variable_key)
        return
    stats = compute_bias_stats([D(x) for x in deviations])
    store.upsert_bias_profile(
        {
            "company_id": company_id,
            "decision_pack_id": decision_pack_id,
            "variable_key": variable_key,
            "n_observations": stats.n_observations,
            "median_bias": stats.median_bias,
            "mean_bias": stats.mean_bias,
            "direction": stats.direction,
            "confidence": stats.confidence,
        }
    )


def preview_calibration(
    store: Store,
    *,
    company_id: str,
    decision_pack_id: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    if decision_pack_id not in DECISION_PACK_IDS:
        raise ValueError(f"unknown decision_pack_id: {decision_pack_id}")
    profiles = store.list_bias_profiles(company_id, decision_pack_id)
    key_map = key_to_input_for_pack(decision_pack_id)
    result = offer_calibration(
        inputs=inputs, profiles=profiles, key_to_input=key_map, min_n=3
    )
    result["profiles"] = profiles
    result["decision_pack_id"] = decision_pack_id
    return result
