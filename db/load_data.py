"""
AgriResolve AI - Automated Database Ingestion Loader
Loads cleaned and derived Excel (.xlsx) and CSV datasets into relational tables.
Reads database configuration from .env.
Supports PostgreSQL (default) with automatic SQLite local fallback (db/agriresolve.db).
"""

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text

# Load environment credentials
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "agriresolve_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def get_database_engine():
    """
    Attempts to connect to PostgreSQL.
    If unavailable, falls back gracefully to a local SQLite database file (db/agriresolve.db).
    """
    if DB_PASSWORD and DB_NAME:
        pg_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        try:
            engine = create_engine(pg_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Connected to PostgreSQL database: {DB_NAME} at {DB_HOST}:{DB_PORT}")
            return engine, "postgresql"
        except Exception as e:
            print(f"PostgreSQL connection not reachable ({e}). Falling back to local SQLite engine.")
            
    sqlite_path = Path("db/agriresolve.db")
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    print(f"Using SQLite database engine at {sqlite_path.as_posix()}")
    return engine, "sqlite"

def load_all_data():
    engine, dialect = get_database_engine()
    clean_dir = Path("data/cleaned")
    derive_dir = Path("data/derived")
    synthetic_dir = Path("data/synthetic")
    raw_dir = Path("data/raw")
    
    # 1. Load RSK Center
    df_rsk = pd.DataFrame([{
        "rsk_code": "KA_MDR_01",
        "rsk_name": "Maddur Kasaba RSK",
        "taluk": "Maddur",
        "district": "Mandya",
        "state": "Karnataka",
        "latitude": 12.5844,
        "longitude": 77.0425,
        "contact_phone": "+91 8232 23XXXX",
        "data_type": "Real",
        "is_synthetic": False
    }])
    df_rsk.to_sql("rsk", engine, if_exists="replace", index=False)
    print("  Loaded table: rsk")

    # 2. Load Villages
    df_villages = pd.read_excel(clean_dir / "villages_cleaned.xlsx")
    df_villages.to_sql("villages", engine, if_exists="replace", index=False)
    print(f"  Loaded table: villages ({len(df_villages)} rows)")

    # 3. Load Crops Catalog
    df_crops = pd.read_excel(raw_dir / "crop_statistics_raw.xlsx", sheet_name="Crops_Catalog")
    df_crops.to_sql("crops", engine, if_exists="replace", index=False)
    print(f"  Loaded table: crops ({len(df_crops)} rows)")

    # 4. Load Village Crops Coverage
    df_vc = pd.read_excel(raw_dir / "crop_statistics_raw.xlsx", sheet_name="Village_Crops_Area")
    df_vc.to_sql("village_crops", engine, if_exists="replace", index=False)
    print(f"  Loaded table: village_crops ({len(df_vc)} rows)")

    # 5. Load Rainfall Observations (with anomalies)
    df_rain = pd.read_excel(derive_dir / "rainfall_anomaly_derived.xlsx")
    df_rain.to_sql("rainfall_observations", engine, if_exists="replace", index=False)
    print(f"  Loaded table: rainfall_observations ({len(df_rain)} rows)")

    # 6. Load NDVI Observations (with deltas)
    df_ndvi = pd.read_excel(derive_dir / "ndvi_trends_derived.xlsx")
    df_ndvi.to_sql("ndvi_observations", engine, if_exists="replace", index=False)
    print(f"  Loaded table: ndvi_observations ({len(df_ndvi)} rows)")

    # 7. Load Farmer Complaints
    df_complaints = pd.read_excel(clean_dir / "complaints_cleaned.xlsx")
    df_complaints.to_sql("farmer_complaints", engine, if_exists="replace", index=False)
    print(f"  Loaded table: farmer_complaints ({len(df_complaints)} rows)")

    # 8. Load Staff Directory
    df_staff = pd.read_excel(synthetic_dir / "staff_roster.xlsx")
    df_staff.to_sql("staff", engine, if_exists="replace", index=False)
    print(f"  Loaded table: staff ({len(df_staff)} rows)")

    # 9. Load Previous Inspections History
    df_inspections = pd.read_excel(clean_dir / "inspections_cleaned.xlsx")
    df_inspections.to_sql("inspections_history", engine, if_exists="replace", index=False)
    print(f"  Loaded table: inspections_history ({len(df_inspections)} rows)")

    # 10. Load Data Reliability
    df_reliability = pd.read_excel(derive_dir / "village_reliability_derived.xlsx")
    df_reliability.to_sql("data_reliability", engine, if_exists="replace", index=False)
    print(f"  Loaded table: data_reliability ({len(df_reliability)} rows)")

    # 11. Load Village Accessibility
    df_access = pd.read_excel(synthetic_dir / "village_accessibility.xlsx")
    df_access.to_sql("village_accessibility", engine, if_exists="replace", index=False)
    print(f"  Loaded table: village_accessibility ({len(df_access)} rows)")

    print("\nDatabase data loading completed successfully.")

if __name__ == "__main__":
    load_all_data()
