# Phase 4: Synthetic Data Generation Assumptions & Statistical Constraints

This document details the exact assumptions, distributions, and domain heuristics used in generating synthetic data for **AgriResolve AI** (`src/ingestion/synthetic/synthetic_generator.py`).

---

## 1. Compliance and Ethical Safeguards

1. **Explicit Flagging**: Every generated row explicitly features `is_synthetic = True` and `data_type = 'Synthetic'`.
2. **Privacy Preservation**: Farmer names are strictly pseudonyms (`Farmer_XXX`), and survey numbers are simulated to prevent linking to actual private land registry records.
3. **No False Government Claims**: None of the complaints or staff records represent official state agricultural grievances; they serve exclusively to benchmark and demonstrate the AgriResolve AI decision prioritization engine.

---

## 2. Statistical Distributions & Domain Consistency Rules

### 2.1 Farmer Complaints
- **Temporal Window**: Spans a 65-day observation window from mid-September to late November 2024.
- **Crop-Pest Alignment**:
  - Sugarcane: Early shoot borer, woolly aphids, red rot, tail-end water deficits.
  - Paddy: Yellow stem borer, leaf blast, brown plant hopper (BPH).
  - Ragi: Drought stress, blast, armyworm.
  - Mulberry: Thrips, leaf roller, tukra.
- **Affected Area Distribution**: Bounded between 0.5 ha and 4.2 ha (mean: 1.8 ha), reflecting small and marginal operational landholding sizes in Mandya district.
- **Cluster Spatial Weighting**: Kadalur (`V_MDR_003`) and Hemmanahalli (`V_MDR_005`) are assigned elevated complaint densities (8 complaints each) to simulate a real rainfed dry-spell anomaly, testing the AI's ability to correlate satellite/rainfall signals with field distress.

### 2.2 Staff Workload & Roster
- Modeled after the standard administrative hierarchy of a Karnataka Raitha Samparka Kendra (RSK):
  - 1 Agriculture Officer (AO - Head of RSK)
  - 2 Assistant Agriculture Officers (AAO - Sector Field Officers)
  - 1 Agricultural Assistant (AA - Technical & Sampling Support)
- Inspection capacities are capped at realistic weekly limits (6 to 10 inspections/week) to enable capacity-aware recommendation algorithms.

### 2.3 Previous Inspections History
- Simulates field inspection visits over the past 180 days.
- Designed with realistic inspection recency gaps:
  - Recently inspected: Besagarahalli (8 days ago), Alur (12 days ago).
  - Prolonged neglect / inspection gap: Kadalur (68 days ago), Hemmanahalli (85 days ago).
  - This allows the Priority Engine's `inspection_recency` factor to meaningfully elevate uninspected villages.

### 2.4 Village Accessibility Baseline
- Straight-line and network road distances from Maddur RSK (NH-275 corridor):
  - Shortest: Maddur Kasaba (1.8 km, 6 mins)
  - Longest: Chikkarasinakere (12.6 km, 30 mins)
- Serves as the baseline for travel impedance scoring and will be updated dynamically via Google Routes API.
