# AgriResolve AI 🌾
### AI-Powered Decision-Support System for Crop Inspection Prioritization

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Streamlit-1.55-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Core Philosophy**: *"The AI recommends; the Agriculture Officer (AO) decides."*

---

## 📌 Project Overview
**AgriResolve AI** is an explainable decision-support platform designed for the **Department of Agriculture, Government of Karnataka**. It helps Agriculture Officers (AO) and Assistant Agriculture Officers (AAO) at **Raitha Samparka Kendras (RSK)** prioritize villages for proactive crop health inspections.

Instead of relying solely on reactive farmer grievances or ad-hoc field visits, AgriResolve AI continuously synthesizes:
1. **Satellite Remote Sensing (Sentinel-2 MSI 10m NDVI)**: Detects early vegetative distress.
2. **Meteorological Observations (IMD 0.25° Gridded & KSNDMC Hobli Rain Gauges)**: Tracks cumulative precipitation deficits.
3. **Reported Farmer Grievances**: Aggregates verified pest attacks, crop failures, and water stress.
4. **Administrative Logistics**: Factors in inspection recency, staff availability, and road network travel times.

---

## 🏛️ Administrative Study Area: Maddur Kasaba RSK Cluster
- **RSK Name**: Maddur Kasaba Raitha Samparka Kendra (`KA_MDR_01`)
- **Taluk**: Maddur | **District**: Mandya | **State**: Karnataka
- **Villages (7-Cluster)**:
  1. **Maddur (Kasaba)** (LGD: 614488) - Sugarcane, Paddy, Vegetables
  2. **Shivapura** (LGD: 614490) - Sugarcane, Mulberry (Sericulture)
  3. **Kadalur** (LGD: 614498) - Paddy, Ragi, Pulses
  4. **Alur** (LGD: 614502) - Sugarcane, Banana, Paddy
  5. **Hemmanahalli** (LGD: 614510) - Ragi, Maize, Groundnut
  6. **Chikkarasinakere** (LGD: 614515) - Paddy, Sugarcane, Vegetables
  7. **Besagarahalli** (LGD: 614522) - Sugarcane, Ragi, Fodder crops

> [!NOTE]
> **Data Transparency Disclosure**: Village boundaries, LGD codes, coordinates, and district hierarchy are verified from official GoI / KGIS registries. The sub-taluk administrative grouping under Maddur Kasaba RSK is designated as **Simulated (Administrative Prototype)** as RSK digital boundaries are not openly published.

---

## 📁 Repository Directory Structure

```text
AgriResolve-AI/
├── README.md                          # Project documentation and architecture
├── .env.example                       # Sanitized template for environment variables
├── .gitignore                         # Strict exclusion of secrets and cache
├── requirements.txt                   # Dependency specifications
├── docs/                              # Research, specifications, quality reports
│   ├── phase01_repo_audit.md          # Environment & git identity audit
│   ├── rsk_selection.md               # RSK & 7 village cluster selection report
│   ├── data_sources.md                # Real vs synthetic dataset provenance catalog
│   ├── api_setup.md                   # Google APIs, Earth Engine & Ollama setup guide
│   ├── synthetic_assumptions.md       # Statistical generator rules & constraints
│   ├── data_quality_report.md         # Village-level data validation & metrics
│   ├── db_setup.md                    # Database schema and setup instructions
│   ├── db_er_diagram.md               # Entity-relationship architecture (Mermaid)
│   ├── eda_findings.md                # Exploratory data analysis & threshold rules
│   └── eda_charts/                    # Interactive Plotly HTML charts
├── data/
│   ├── raw/                           # Raw Excel (.xlsx) & CSV from real sources (untouched)
│   │   ├── villages_raw.xlsx / .csv
│   │   ├── rainfall_raw.xlsx / .csv
│   │   ├── ndvi_raw.xlsx / .csv
│   │   └── crop_statistics_raw.xlsx / .csv
│   ├── cleaned/                       # Standardized, validated Excel (.xlsx) & CSV datasets
│   │   ├── villages_cleaned.xlsx / .csv
│   │   ├── rainfall_cleaned.xlsx / .csv
│   │   ├── ndvi_cleaned.xlsx / .csv
│   │   ├── complaints_cleaned.xlsx / .csv
│   │   └── inspections_cleaned.xlsx / .csv
│   ├── derived/                       # Derived indicators (.xlsx & .csv)
│   │   ├── rainfall_anomaly_derived.xlsx / .csv
│   │   ├── ndvi_trends_derived.xlsx / .csv
│   │   └── village_reliability_derived.xlsx / .csv
│   └── synthetic/                     # Flagged synthetic datasets (.xlsx & .csv)
│       ├── farmer_complaints.xlsx / .csv
│       ├── staff_roster.xlsx / .csv
│       ├── inspections_history.xlsx / .csv
│       └── village_accessibility.xlsx / .csv
├── db/
│   ├── schema.sql                     # Complete 16-table PostgreSQL DDL
│   └── load_data.py                   # Automated database ingestion loader
├── src/
│   ├── ingestion/                     # Ingestion scripts for villages, rainfall, NDVI, crops
│   │   └── synthetic/                 # Seeded synthetic data generator (Seed: 42)
│   ├── preprocessing/                 # Data cleaning and derivation pipeline
│   └── eda_analysis.py                # EDA Plotly visualization generator
├── notebooks/
│   └── eda.ipynb                      # Interactive exploratory data analysis notebook
└── tests/
    └── test_cleaning.py               # Unit tests for data cleaning & boundary checks
```

---

## 📊 Real vs. Synthetic Data Provenance

| Data Component | Provenance | Flagged Status | Storage Files |
| :--- | :--- | :--- | :--- |
| **Villages Geography** | **Real** (LGD / KGIS) | `is_synthetic = False` | `data/raw/villages_raw.xlsx`, `data/cleaned/villages_cleaned.xlsx` |
| **Rainfall Series** | **Real** (IMD Gridded + KSNDMC) | `is_synthetic = False` | `data/raw/rainfall_raw.xlsx`, `data/cleaned/rainfall_cleaned.xlsx` |
| **Sentinel-2 NDVI** | **Real** (Copernicus MSI 10m) | `is_synthetic = False` | `data/raw/ndvi_raw.xlsx`, `data/cleaned/ndvi_cleaned.xlsx` |
| **Crop Statistics** | **Real** (DES Karnataka + PoP) | `is_synthetic = False` | `data/raw/crop_statistics_raw.xlsx` |
| **Rainfall Anomaly** | **Derived** (Calculated) | `is_synthetic = False` | `data/derived/rainfall_anomaly_derived.xlsx` |
| **NDVI Drops / Stress**| **Derived** (Calculated) | `is_synthetic = False` | `data/derived/ndvi_trends_derived.xlsx` |
| **Data Reliability** | **Derived** (Calculated) | `is_synthetic = False` | `data/derived/village_reliability_derived.xlsx` |
| **Farmer Complaints** | **Synthetic** (Simulation) | `is_synthetic = True` | `data/synthetic/farmer_complaints.xlsx` |
| **Staff Workload** | **Synthetic** (Simulation) | `is_synthetic = True` | `data/synthetic/staff_roster.xlsx` |
| **Inspection History**| **Synthetic** (Simulation) | `is_synthetic = True` | `data/synthetic/inspections_history.xlsx` |

---

## 🚀 Quickstart Guide

### 1. Prerequisites & Virtual Environment
Ensure Python 3.10+ is installed:
```bash
python -m venv venv
venv\Scripts\activate   # On Windows
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate database credentials and optional Google API keys.

### 3. Ingestion & Data Pipeline
Run the data ingestion and cleaning pipelines:
```bash
# Generate raw datasets
python src/ingestion/ingest_villages.py
python src/ingestion/ingest_rainfall.py
python src/ingestion/ingest_ndvi.py
python src/ingestion/ingest_crops.py
python src/ingestion/synthetic/synthetic_generator.py

# Clean and compute derived indicators
python src/preprocessing/cleaning_and_derivation.py

# Ingest into database
python db/load_data.py
```

### 4. Run Unit Tests
```bash
python -m unittest tests/test_cleaning.py
```
