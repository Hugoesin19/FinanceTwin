"""Light free accounts — org isolation via opaque token header."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from financetwin_api.db import Store


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class OrgRow:
    id: str
    name: str
    token_hash: str
    created_at: str


def ensure_org_schema(store: Store) -> None:
    with store.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS org (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        cols = {
            r[1]
            for r in conn.execute("PRAGMA table_info(company)").fetchall()
        }
        if "org_id" not in cols:
            conn.execute("ALTER TABLE company ADD COLUMN org_id TEXT")


def create_org(store: Store, name: str) -> dict[str, Any]:
    ensure_org_schema(store)
    org_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(24)
    token_hash = _hash_token(token)
    created = _utcnow()
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO org (id, name, token_hash, created_at) VALUES (?,?,?,?)",
            (org_id, name.strip() or "Org", token_hash, created),
        )
    return {
        "org_id": org_id,
        "name": name.strip() or "Org",
        "token": token,
        "created_at": created,
        "header": "X-Org-Token",
        "note": "Guarda el token; no se vuelve a mostrar. Envíalo en X-Org-Token.",
    }


def resolve_org_id(store: Store, token: str | None) -> str | None:
    if not token:
        return None
    ensure_org_schema(store)
    th = _hash_token(token.strip())
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id FROM org WHERE token_hash=?", (th,)
        ).fetchone()
    return None if row is None else str(row["id"])


def list_companies_for_org(store: Store, org_id: str | None) -> list[Any]:
    ensure_org_schema(store)
    with store.connect() as conn:
        if org_id is None:
            # Legacy / demo: companies without org + all if no auth
            rows = conn.execute(
                "SELECT id, name, country, currency, created_at FROM company "
                "WHERE org_id IS NULL OR org_id = '' ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, country, currency, created_at FROM company "
                "WHERE org_id=? ORDER BY created_at DESC",
                (org_id,),
            ).fetchall()
    from financetwin_api.db import CompanyRow

    return [CompanyRow(**dict(r)) for r in rows]


def company_belongs_to_org(store: Store, company_id: str, org_id: str | None) -> bool:
    """If org_id is set, company must match. If unset, allow (local single-user)."""
    if org_id is None:
        return True
    ensure_org_schema(store)
    with store.connect() as conn:
        row = conn.execute(
            "SELECT org_id FROM company WHERE id=?", (company_id,)
        ).fetchone()
    if row is None:
        return False
    return str(row["org_id"] or "") == org_id


def set_company_org(store: Store, company_id: str, org_id: str | None) -> None:
    ensure_org_schema(store)
    with store.connect() as conn:
        conn.execute(
            "UPDATE company SET org_id=? WHERE id=?",
            (org_id, company_id),
        )
