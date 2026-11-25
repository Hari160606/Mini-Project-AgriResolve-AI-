# Phase 6: Database Setup & Operations Guide

## 1. Local PostgreSQL Setup (Optional / Recommended)

AgriResolve AI is built to connect natively to PostgreSQL (14+ / 16+ / 18+).

### 1.1 Database Creation
Open your terminal / `psql` shell:
```sql
CREATE DATABASE agriresolve_db;
CREATE USER agri_user WITH ENCRYPTED PASSWORD 'agri_password_123';
GRANT ALL PRIVILEGES ON DATABASE agriresolve_db TO agri_user;
```

### 1.2 Environment Configuration
Add the credentials into your `.env` file:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agriresolve_db
DB_USER=agri_user
DB_PASSWORD=agri_password_123
```

### 1.3 Schema Execution
Execute the master DDL schema:
```bash
psql -h localhost -U agri_user -d agriresolve_db -f db/schema.sql
```

---

## 2. Automated Multi-Format Data Loading

To ingest all cleaned and derived Excel (`.xlsx`) and CSV tables into the database, run:
```bash
python db/load_data.py
```

### Zero-Configuration Local Fallback
If PostgreSQL is not running locally, `db/load_data.py` automatically initializes an embedded SQLite database (`db/agriresolve.db`). This allows developers, evaluators, and the Streamlit dashboard to run without pre-configuring PostgreSQL services!

---

## 3. Database Verification Queries

Run the following queries to verify data loading and table counts:

```sql
-- 1. Check Village Registry & Assigned RSK
SELECT village_id, village_name, lgd_code, soil_type, is_synthetic FROM villages;

-- 2. Check Rainfall Observations and Anomaly Distribution
SELECT rainfall_status, COUNT(*) as observations_count, ROUND(AVG(rainfall_anomaly_percent), 1) as avg_anomaly_pct 
FROM rainfall_observations 
GROUP BY rainfall_status;

-- 3. Check Sentinel-2 NDVI Observations and Stress Flags
SELECT village_id, COUNT(*) as total_scenes, SUM(CASE WHEN vegetation_stress_flag THEN 1 ELSE 0 END) as stress_events
FROM ndvi_observations
GROUP BY village_id;

-- 4. Audit Synthetic vs Real Data Tagging
SELECT 'villages' as table_name, is_synthetic, COUNT(*) FROM villages GROUP BY is_synthetic
UNION ALL
SELECT 'farmer_complaints', is_synthetic, COUNT(*) FROM farmer_complaints GROUP BY is_synthetic;
```
