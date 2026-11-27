"""
AgriResolve AI - Automated Database Ingestion Loader & App Repository
Loads cleaned and derived Excel (.xlsx) and CSV datasets into relational tables.
Reads database configuration from .env.
Supports PostgreSQL (default) with automatic SQLite local fallback (db/agriresolve.db).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

_TABLE_TO_EXCEL: dict[str, tuple[str, str]] = {
    "villages": ("cleaned", "villages_cleaned.xlsx"),
    "priorities": ("derived", "priority_scores.xlsx"),
    "factors": ("derived", "priority_factors.xlsx"),
    "routine": ("derived", "routine_monitoring_results.xlsx"),
    "reported": ("derived", "reported_monitoring_results.xlsx"),
    "complaints": ("cleaned", "complaints_cleaned.xlsx"),
    "staff": ("synthetic", "staff_roster.xlsx"),
    "ndvi": ("derived", "ndvi_trends_derived.xlsx"),
    "rain": ("derived", "rainfall_anomaly_derived.xlsx"),
}

_APP_KEY_TO_DB_TABLE: dict[str, str] = {
    "villages": "villages",
    "priorities": "priority_scores",
    "factors": "priority_factors",
    "routine": "routine_monitoring_results",
    "reported": "reported_monitoring_results",
    "complaints": "farmer_complaints",
    "staff": "staff",
    "ndvi": "ndvi_observations",
    "rain": "rainfall_observations",
}

_DISPATCH_COLUMNS: list[str] = [
    "dispatch_id",
    "village_id",
    "village_name",
    "assigned_officer",
    "assigned_officer_id",
    "priority_rank",
    "priority_score",
    "severity_score",
    "target_date",
    "instructions",
    "status",
    "assigned_by",
    "created_at",
]


def get_database_engine(sqlite_path: Path | None = None) -> tuple[Engine, str]:
    """Connect to PostgreSQL from .env, falling back to local SQLite if unreachable."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    db_host = os.getenv("DB_HOST", "localhost").strip()
    db_port = os.getenv("DB_PORT", "5432").strip()
    db_name = os.getenv("DB_NAME", "agriresolve_db").strip()
    db_user = os.getenv("DB_USER", "postgres").strip()
    db_password = os.getenv("DB_PASSWORD", "").strip()

    if db_password and db_name and db_password != "change-me":
        pg_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        try:
            engine = create_engine(pg_url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Connected to PostgreSQL database: {db_name} at {db_host}:{db_port}")
            return engine, "postgresql"
        except Exception as e:
            print(f"PostgreSQL connection not reachable ({e}). Falling back to local SQLite engine.")

    target_sqlite = sqlite_path or (PROJECT_ROOT / "db" / "agriresolve.db")
    target_sqlite.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{target_sqlite.as_posix()}")
    print(f"Using SQLite database engine at {target_sqlite.as_posix()}")
    return engine, "sqlite"


def _ensure_dispatches_table(engine: Engine) -> None:
    """Create or migrate the inspection_dispatches table with priority & severity columns."""
    ddl = """
    CREATE TABLE IF NOT EXISTS inspection_dispatches (
        dispatch_id TEXT PRIMARY KEY,
        village_id TEXT,
        village_name TEXT NOT NULL,
        assigned_officer TEXT NOT NULL,
        assigned_officer_id TEXT,
        priority_rank INTEGER,
        priority_score REAL,
        severity_score REAL,
        target_date TEXT NOT NULL,
        instructions TEXT,
        status TEXT DEFAULT 'Assigned',
        assigned_by TEXT,
        created_at TEXT NOT NULL
    )
    """
    extra_cols = [
        ("village_id", "TEXT"),
        ("assigned_officer_id", "TEXT"),
        ("priority_rank", "INTEGER"),
        ("priority_score", "REAL"),
        ("severity_score", "REAL"),
        ("status", "TEXT DEFAULT 'Assigned'"),
    ]
    with engine.begin() as conn:
        conn.execute(text(ddl))
        for col_name, col_type in extra_cols:
            try:
                conn.execute(text(f"ALTER TABLE inspection_dispatches ADD COLUMN {col_name} {col_type}"))
            except Exception:
                pass


def load_all_data(engine: Engine | None = None) -> tuple[Engine, str]:
    """Load all raw, cleaned, synthetic, and derived tables into the database."""
    dialect = "custom"
    if engine is None:
        engine, dialect = get_database_engine()

    data_root = PROJECT_ROOT / "data"
    clean_dir = data_root / "cleaned"
    derive_dir = data_root / "derived"
    synthetic_dir = data_root / "synthetic"
    raw_dir = data_root / "raw"

    df_rsk = pd.DataFrame(
        [
            {
                "rsk_code": "KA_MDR_01",
                "rsk_name": "Maddur Kasaba RSK",
                "taluk": "Maddur",
                "district": "Mandya",
                "state": "Karnataka",
                "latitude": 12.5839,
                "longitude": 77.0434,
                "contact_phone": "+91 8232 23XXXX",
                "data_type": "Real",
                "is_synthetic": False,
            }
        ]
    )
    df_rsk.to_sql("rsk", engine, if_exists="replace", index=False)
    print("  Loaded table: rsk")

    tables_to_load: list[tuple[str, pd.DataFrame]] = [
        ("villages", pd.read_excel(clean_dir / "villages_cleaned.xlsx")),
        ("crops", pd.read_excel(raw_dir / "crop_statistics_raw.xlsx", sheet_name="Crops_Catalog")),
        ("village_crops", pd.read_excel(raw_dir / "crop_statistics_raw.xlsx", sheet_name="Village_Crops_Area")),
        ("rainfall_observations", pd.read_excel(derive_dir / "rainfall_anomaly_derived.xlsx")),
        ("ndvi_observations", pd.read_excel(derive_dir / "ndvi_trends_derived.xlsx")),
        ("farmer_complaints", pd.read_excel(clean_dir / "complaints_cleaned.xlsx")),
        ("staff", pd.read_excel(synthetic_dir / "staff_roster.xlsx")),
        ("inspections_history", pd.read_excel(clean_dir / "inspections_cleaned.xlsx")),
        ("data_reliability", pd.read_excel(derive_dir / "village_reliability_derived.xlsx")),
        ("village_accessibility", pd.read_excel(synthetic_dir / "village_accessibility.xlsx")),
        ("priority_scores", pd.read_excel(derive_dir / "priority_scores.xlsx")),
        ("priority_factors", pd.read_excel(derive_dir / "priority_factors.xlsx")),
        ("routine_monitoring_results", pd.read_excel(derive_dir / "routine_monitoring_results.xlsx")),
        ("reported_monitoring_results", pd.read_excel(derive_dir / "reported_monitoring_results.xlsx")),
    ]

    for table_name, df in tables_to_load:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"  Loaded table: {table_name} ({len(df)} rows)")

    _ensure_dispatches_table(engine)
    print("  Verified table: inspection_dispatches")
    print("\nDatabase data loading completed successfully.")
    return engine, dialect


def _load_excel_tables() -> dict[str, pd.DataFrame]:
    data_root = PROJECT_ROOT / "data"
    return {
        key: pd.read_excel(data_root / folder / filename)
        for key, (folder, filename) in _TABLE_TO_EXCEL.items()
    }


def fetch_dashboard_tables(engine: Engine | None = None) -> tuple[dict[str, pd.DataFrame], str]:
    """Load dashboard tables from PostgreSQL (or SQLite), falling back to Excel if unavailable."""
    try:
        dialect = "custom"
        if engine is None:
            engine, dialect = get_database_engine()
        data = {
            app_key: pd.read_sql_table(db_table, engine)
            for app_key, db_table in _APP_KEY_TO_DB_TABLE.items()
        }
        try:
            _ensure_dispatches_table(engine)
            data["dispatches"] = pd.read_sql_table("inspection_dispatches", engine)
        except Exception:
            data["dispatches"] = pd.DataFrame(columns=_DISPATCH_COLUMNS)
        return data, dialect
    except Exception:
        data = _load_excel_tables()
        data["dispatches"] = pd.DataFrame(columns=_DISPATCH_COLUMNS)
        return data, "excel"


def save_farmer_complaint(record: dict[str, Any], engine: Engine | None = None) -> tuple[bool, str]:
    """Persist a newly registered farmer complaint to the configured database."""
    try:
        dialect = "custom"
        if engine is None:
            engine, dialect = get_database_engine()
        pd.DataFrame([record]).to_sql("farmer_complaints", engine, if_exists="append", index=False)
        return True, dialect
    except Exception:
        return False, "session"


def escalate_complaint_to_ao(
    complaint_id: str,
    escalated_by: str,
    aao_note: str = "",
    engine: Engine | None = None,
) -> tuple[bool, str]:
    """Mark an existing farmer complaint as Sent to AO with optional AAO field note."""
    try:
        dialect = "custom"
        if engine is None:
            engine, dialect = get_database_engine()
        note_suffix = f" [AAO {escalated_by}: {aao_note.strip()}]" if aao_note.strip() else f" [Escalated by AAO {escalated_by}]"
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE farmer_complaints "
                    "SET status = :status, "
                    "issue_description = COALESCE(issue_description, '') || :note "
                    "WHERE complaint_id = :cid"
                ),
                {"status": "Sent to AO", "note": note_suffix, "cid": complaint_id},
            )
        return True, dialect
    except Exception:
        return False, "session"


def save_inspection_dispatch(record: dict[str, Any], engine: Engine | None = None) -> tuple[bool, str]:
    """Persist a newly assigned field inspection dispatch to the configured database."""
    try:
        dialect = "custom"
        if engine is None:
            engine, dialect = get_database_engine()
        _ensure_dispatches_table(engine)
        normalized = {col: record.get(col) for col in _DISPATCH_COLUMNS}
        if not normalized.get("status"):
            normalized["status"] = "Assigned"
        pd.DataFrame([normalized]).to_sql("inspection_dispatches", engine, if_exists="append", index=False)
        return True, dialect
    except Exception:
        return False, "session"


def save_inspection_dispatches_batch(records: list[dict[str, Any]], engine: Engine | None = None) -> tuple[bool, str]:
    """Persist multiple AO priority dispatches at once."""
    if not records:
        return True, "noop"
    try:
        dialect = "custom"
        if engine is None:
            engine, dialect = get_database_engine()
        _ensure_dispatches_table(engine)
        rows = []
        for rec in records:
            normalized = {col: rec.get(col) for col in _DISPATCH_COLUMNS}
            if not normalized.get("status"):
                normalized["status"] = "Assigned"
            rows.append(normalized)
        pd.DataFrame(rows).to_sql("inspection_dispatches", engine, if_exists="append", index=False)
        return True, dialect
    except Exception:
        return False, "session"


def update_dispatch_status(
    dispatch_id: str,
    new_status: str,
    engine: Engine | None = None,
) -> tuple[bool, str]:
    """Update the inspection status of an AO-assigned dispatch."""
    try:
        dialect = "custom"
        if engine is None:
            engine, dialect = get_database_engine()
        _ensure_dispatches_table(engine)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE inspection_dispatches SET status = :status WHERE dispatch_id = :did"),
                {"status": new_status, "did": dispatch_id},
            )
        return True, dialect
    except Exception:
        return False, "session"


if __name__ == "__main__":
    load_all_data()
