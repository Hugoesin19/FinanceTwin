"""SQLite persistence — MODELO Company / ModelVersion / Scenario / CalculationRun."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from financetwin_api.serialize import to_jsonable


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


@dataclass
class CompanyRow:
    id: str
    name: str
    country: str
    currency: str
    created_at: str


class Store:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS company (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    country TEXT NOT NULL DEFAULT 'ES',
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_version (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES company(id),
                    parent_id TEXT,
                    label TEXT,
                    is_current INTEGER NOT NULL DEFAULT 0,
                    snapshot_json TEXT NOT NULL,
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenario (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES company(id),
                    name TEXT NOT NULL,
                    scenario_type TEXT NOT NULL,
                    base_model_version_id TEXT NOT NULL REFERENCES model_version(id),
                    anchor_year_month TEXT NOT NULL,
                    horizon_months INTEGER NOT NULL,
                    discount_rate_annual TEXT NOT NULL,
                    auto_finance_deficits INTEGER NOT NULL DEFAULT 0,
                    overrides_json TEXT NOT NULL,
                    locked INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT NOT NULL DEFAULT 'system',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS calculation_run (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL REFERENCES scenario(id),
                    company_id TEXT NOT NULL REFERENCES company(id),
                    engine_version TEXT NOT NULL,
                    model_version_id TEXT NOT NULL REFERENCES model_version(id),
                    inputs_hash TEXT NOT NULL,
                    calculation_input_json TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    computed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decision (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES company(id),
                    number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    decision_pack_id TEXT NOT NULL,
                    decision_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scenario_id TEXT NOT NULL REFERENCES scenario(id),
                    model_version_id TEXT NOT NULL REFERENCES model_version(id),
                    engine_version TEXT NOT NULL,
                    calculation_run_id TEXT REFERENCES calculation_run(id),
                    forecast_metrics_json TEXT NOT NULL,
                    frozen_projection_json TEXT,
                    rationale TEXT NOT NULL DEFAULT '',
                    owner_user_id TEXT NOT NULL,
                    owner_label TEXT,
                    discarded_alternatives_json TEXT NOT NULL,
                    accepted_risks_json TEXT NOT NULL,
                    conditions TEXT,
                    policy_exceptions_json TEXT NOT NULL,
                    calibrated_scenario_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (company_id, number)
                );

                CREATE TABLE IF NOT EXISTS decision_milestone (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL REFERENCES decision(id),
                    due_date TEXT NOT NULL,
                    label TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS actual_result (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL REFERENCES decision(id),
                    period_year_month TEXT NOT NULL,
                    variable_key TEXT NOT NULL,
                    forecast_value TEXT NOT NULL,
                    actual_value TEXT NOT NULL,
                    deviation_pct TEXT,
                    source TEXT NOT NULL,
                    recorded_by TEXT,
                    recorded_at TEXT NOT NULL,
                    notes TEXT,
                    UNIQUE (decision_id, period_year_month, variable_key)
                );

                CREATE TABLE IF NOT EXISTS bias_profile (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL REFERENCES company(id),
                    decision_pack_id TEXT NOT NULL,
                    variable_key TEXT NOT NULL,
                    n_observations INTEGER NOT NULL,
                    median_bias TEXT NOT NULL,
                    mean_bias TEXT,
                    std_dev TEXT,
                    direction TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (company_id, decision_pack_id, variable_key)
                );

                -- MODELO §13.1: a lo sumo una ModelVersion current por company
                CREATE UNIQUE INDEX IF NOT EXISTS ux_model_version_one_current
                ON model_version(company_id) WHERE is_current = 1;
                """
            )

    def create_company(self, name: str, country: str = "ES", currency: str = "EUR") -> CompanyRow:
        row = CompanyRow(
            id=_id(),
            name=name,
            country=country,
            currency=currency,
            created_at=_utcnow(),
        )
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO company (id, name, country, currency, created_at) VALUES (?,?,?,?,?)",
                (row.id, row.name, row.country, row.currency, row.created_at),
            )
        return row

    def get_company(self, company_id: str) -> CompanyRow | None:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM company WHERE id=?", (company_id,)).fetchone()
        if not r:
            return None
        return CompanyRow(**dict(r))

    def put_current_snapshot(
        self,
        company_id: str,
        snapshot: dict[str, Any],
        *,
        label: str | None = None,
        created_by: str = "system",
    ) -> str:
        """Create new ModelVersion as current (never mutates referenced versions)."""
        if self.get_company(company_id) is None:
            raise KeyError(f"company not found: {company_id}")
        mv_id = _id()
        now = _utcnow()
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        with self.connect() as conn:
            prev = conn.execute(
                "SELECT id FROM model_version WHERE company_id=? AND is_current=1",
                (company_id,),
            ).fetchone()
            parent_id = prev["id"] if prev else None
            conn.execute(
                "UPDATE model_version SET is_current=0 WHERE company_id=? AND is_current=1",
                (company_id,),
            )
            conn.execute(
                """
                INSERT INTO model_version
                (id, company_id, parent_id, label, is_current, snapshot_json, created_by, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (mv_id, company_id, parent_id, label, payload, created_by, now),
            )
        return mv_id

    def get_model_version_meta(self, model_version_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT id, company_id, parent_id, label, is_current, created_at "
                "FROM model_version WHERE id=?",
                (model_version_id,),
            ).fetchone()
        return dict(r) if r else None

    def get_current_snapshot(self, company_id: str) -> tuple[str, dict[str, Any]] | None:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT id, snapshot_json FROM model_version WHERE company_id=? AND is_current=1",
                (company_id,),
            ).fetchone()
        if not r:
            return None
        return r["id"], json.loads(r["snapshot_json"])

    def create_scenario(
        self,
        *,
        company_id: str,
        name: str,
        scenario_type: str,
        base_model_version_id: str,
        anchor_year_month: str,
        horizon_months: int,
        discount_rate_annual: str,
        overrides: list[dict[str, Any]],
        auto_finance_deficits: bool = False,
        created_by: str = "system",
    ) -> str:
        sid = _id()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO scenario (
                    id, company_id, name, scenario_type, base_model_version_id,
                    anchor_year_month, horizon_months, discount_rate_annual,
                    auto_finance_deficits, overrides_json, locked, created_by, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,0,?,?)
                """,
                (
                    sid,
                    company_id,
                    name,
                    scenario_type,
                    base_model_version_id,
                    anchor_year_month,
                    horizon_months,
                    discount_rate_annual,
                    1 if auto_finance_deficits else 0,
                    json.dumps(to_jsonable(overrides), ensure_ascii=False),
                    created_by,
                    _utcnow(),
                ),
            )
        return sid

    def create_calculation_run(
        self,
        *,
        scenario_id: str,
        company_id: str,
        engine_version: str,
        model_version_id: str,
        inputs_hash: str,
        calculation_input: dict[str, Any],
        results: dict[str, Any],
        status: str = "completed",
        error_message: str | None = None,
    ) -> str:
        rid = _id()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO calculation_run (
                    id, scenario_id, company_id, engine_version, model_version_id,
                    inputs_hash, calculation_input_json, results_json,
                    status, error_message, computed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rid,
                    scenario_id,
                    company_id,
                    engine_version,
                    model_version_id,
                    inputs_hash,
                    json.dumps(to_jsonable(calculation_input), ensure_ascii=False),
                    json.dumps(to_jsonable(results), ensure_ascii=False),
                    status,
                    error_message,
                    _utcnow(),
                ),
            )
        return rid

    def get_calculation_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT * FROM calculation_run WHERE id=?", (run_id,)
            ).fetchone()
        if not r:
            return None
        d = dict(r)
        d["calculation_input"] = json.loads(d.pop("calculation_input_json"))
        d["results"] = json.loads(d.pop("results_json"))
        return d

    def next_decision_number(self, company_id: str) -> int:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT COALESCE(MAX(number), 0) AS m FROM decision WHERE company_id=?",
                (company_id,),
            ).fetchone()
        return int(r["m"]) + 1

    def create_decision(self, row: dict[str, Any]) -> str:
        did = row.get("id") or _id()
        now = _utcnow()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO decision (
                    id, company_id, number, title, decision_pack_id, decision_date,
                    status, scenario_id, model_version_id, engine_version,
                    calculation_run_id, forecast_metrics_json, frozen_projection_json,
                    rationale, owner_user_id, owner_label,
                    discarded_alternatives_json, accepted_risks_json, conditions,
                    policy_exceptions_json, calibrated_scenario_id, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    did,
                    row["company_id"],
                    row["number"],
                    row["title"],
                    row["decision_pack_id"],
                    row["decision_date"],
                    row["status"],
                    row["scenario_id"],
                    row["model_version_id"],
                    row["engine_version"],
                    row.get("calculation_run_id"),
                    json.dumps(to_jsonable(row.get("forecast_metrics") or {}), ensure_ascii=False),
                    json.dumps(to_jsonable(row["frozen_projection"]), ensure_ascii=False)
                    if row.get("frozen_projection") is not None
                    else None,
                    row.get("rationale") or "",
                    row["owner_user_id"],
                    row.get("owner_label"),
                    json.dumps(to_jsonable(row.get("discarded_alternatives") or []), ensure_ascii=False),
                    json.dumps(to_jsonable(row.get("accepted_risks") or []), ensure_ascii=False),
                    row.get("conditions"),
                    json.dumps(to_jsonable(row.get("policy_exceptions") or []), ensure_ascii=False),
                    row.get("calibrated_scenario_id"),
                    now,
                    now,
                ),
            )
        return did

    def add_milestones(self, decision_id: str, milestones: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            for m in milestones:
                conn.execute(
                    """
                    INSERT INTO decision_milestone (id, decision_id, due_date, label, status, notes)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        _id(),
                        decision_id,
                        m["due_date"],
                        m["label"],
                        m.get("status") or "pending",
                        m.get("notes"),
                    ),
                )

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM decision WHERE id=?", (decision_id,)).fetchone()
            if not r:
                return None
            d = dict(r)
            milestones = conn.execute(
                "SELECT * FROM decision_milestone WHERE decision_id=? ORDER BY due_date",
                (decision_id,),
            ).fetchall()
            actuals = conn.execute(
                "SELECT * FROM actual_result WHERE decision_id=? ORDER BY period_year_month, variable_key",
                (decision_id,),
            ).fetchall()
        d["forecast_metrics"] = json.loads(d.pop("forecast_metrics_json"))
        fp = d.pop("frozen_projection_json")
        d["frozen_projection"] = json.loads(fp) if fp else None
        d["discarded_alternatives"] = json.loads(d.pop("discarded_alternatives_json"))
        d["accepted_risks"] = json.loads(d.pop("accepted_risks_json"))
        d["policy_exceptions"] = json.loads(d.pop("policy_exceptions_json"))
        d["milestones"] = [dict(m) for m in milestones]
        d["actual_results"] = [
            {
                **{k: v for k, v in dict(a).items()},
            }
            for a in actuals
        ]
        return d

    def update_decision_status(self, decision_id: str, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE decision SET status=?, updated_at=? WHERE id=?",
                (status, _utcnow(), decision_id),
            )

    def upsert_actual_result(self, row: dict[str, Any]) -> str:
        rid = row.get("id") or _id()
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM actual_result
                WHERE decision_id=? AND period_year_month=? AND variable_key=?
                """,
                (row["decision_id"], row["period_year_month"], row["variable_key"]),
            ).fetchone()
            if existing:
                rid = existing["id"]
                conn.execute(
                    """
                    UPDATE actual_result SET
                        forecast_value=?, actual_value=?, deviation_pct=?,
                        source=?, recorded_by=?, recorded_at=?, notes=?
                    WHERE id=?
                    """,
                    (
                        str(row["forecast_value"]),
                        str(row["actual_value"]),
                        None if row.get("deviation_pct") is None else str(row["deviation_pct"]),
                        row["source"],
                        row.get("recorded_by"),
                        row.get("recorded_at") or _utcnow(),
                        row.get("notes"),
                        rid,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO actual_result (
                        id, decision_id, period_year_month, variable_key,
                        forecast_value, actual_value, deviation_pct,
                        source, recorded_by, recorded_at, notes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rid,
                        row["decision_id"],
                        row["period_year_month"],
                        row["variable_key"],
                        str(row["forecast_value"]),
                        str(row["actual_value"]),
                        None if row.get("deviation_pct") is None else str(row["deviation_pct"]),
                        row["source"],
                        row.get("recorded_by"),
                        row.get("recorded_at") or _utcnow(),
                        row.get("notes"),
                    ),
                )
        return rid

    def list_deviations_for_pack(
        self, company_id: str, decision_pack_id: str, variable_key: str
    ) -> list[str]:
        """
        Una desviación por decisión executed (la más reciente).
        n_observations del BiasProfile = nº de decisiones similares, no filas.
        """
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT a.deviation_pct
                FROM (
                    SELECT
                        a.decision_id AS decision_id,
                        a.deviation_pct AS deviation_pct,
                        ROW_NUMBER() OVER (
                            PARTITION BY a.decision_id
                            ORDER BY a.recorded_at DESC, a.period_year_month DESC
                        ) AS rn
                    FROM actual_result a
                    JOIN decision d ON d.id = a.decision_id
                    WHERE d.company_id=?
                      AND d.decision_pack_id=?
                      AND d.status='executed'
                      AND a.variable_key=?
                      AND a.deviation_pct IS NOT NULL
                ) a
                WHERE a.rn = 1
                ORDER BY a.decision_id
                """,
                (company_id, decision_pack_id, variable_key),
            ).fetchall()
        return [r["deviation_pct"] for r in rows]

    def upsert_bias_profile(self, row: dict[str, Any]) -> str:
        now = _utcnow()
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM bias_profile
                WHERE company_id=? AND decision_pack_id=? AND variable_key=?
                """,
                (row["company_id"], row["decision_pack_id"], row["variable_key"]),
            ).fetchone()
            if existing:
                pid = existing["id"]
                conn.execute(
                    """
                    UPDATE bias_profile SET
                        n_observations=?, median_bias=?, mean_bias=?, std_dev=?,
                        direction=?, confidence=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        row["n_observations"],
                        str(row["median_bias"]),
                        None if row.get("mean_bias") is None else str(row["mean_bias"]),
                        None if row.get("std_dev") is None else str(row["std_dev"]),
                        row["direction"],
                        row["confidence"],
                        now,
                        pid,
                    ),
                )
                return pid
            pid = _id()
            conn.execute(
                """
                INSERT INTO bias_profile (
                    id, company_id, decision_pack_id, variable_key,
                    n_observations, median_bias, mean_bias, std_dev,
                    direction, confidence, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    pid,
                    row["company_id"],
                    row["decision_pack_id"],
                    row["variable_key"],
                    row["n_observations"],
                    str(row["median_bias"]),
                    None if row.get("mean_bias") is None else str(row["mean_bias"]),
                    None if row.get("std_dev") is None else str(row["std_dev"]),
                    row["direction"],
                    row["confidence"],
                    now,
                ),
            )
            return pid

    def list_bias_profiles(self, company_id: str, decision_pack_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM bias_profile
                WHERE company_id=? AND decision_pack_id=?
                ORDER BY variable_key
                """,
                (company_id, decision_pack_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_bias_profile(
        self, company_id: str, decision_pack_id: str, variable_key: str
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                DELETE FROM bias_profile
                WHERE company_id=? AND decision_pack_id=? AND variable_key=?
                """,
                (company_id, decision_pack_id, variable_key),
            )
