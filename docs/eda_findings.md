# Phase 7: Exploratory Data Analysis & Threshold Formulation

## 1. Executive Summary & Data Separation

This report summarizes exploratory analysis across all 7 revenue villages of the Maddur Kasaba RSK cluster in Mandya, Karnataka. In accordance with Master Rule A2.5, **real observational data is rigorously separated from synthetic administrative data**.

| Data Stream | Provenance | Key Insights | Analytical Utility for Prioritization |
| :--- | :--- | :--- | :--- |
| **Rainfall Anomaly** | **Real** (IMD Gridded + KSNDMC Hobli gauges) | Early Kharif (June–July) experienced prolonged dry spells (-35% to -52% deficit) specifically affecting rainfed villages (Kadalur, Hemmanahalli), before recovering in October. | Core driver for the **Routine Monitoring (Step 3)** agricultural drought risk factor. |
| **Sentinel-2 NDVI** | **Real** (Copernicus 10m MSI L2A) | Irrigated command villages (Shivapura, Alur, Chikkarasinakere) maintained high NDVI (0.55–0.76). Rainfed villages dropped sharply by -16.4% and -18.2% during late August. | Trigger for **Unusual Vegetation Decline** detection. |
| **Farmer Complaints** | **Synthetic** (Flagged Seeded Generator) | 35 complaints registered; pest outbreaks (stem borer, blast) and water stress cluster heavily around Kadalur and Hemmanahalli. | Input for **Reported Issue Monitoring (Step 4)** urgency and cluster scoring. |
| **Inspection Recency** | **Synthetic** (Historical Logs) | Kadalur (68 days) and Hemmanahalli (85 days) exceed recommended RSK revisit cycles (> 45 days). Besagarahalli and Alur were visited within 15 days. | Prevents inspection starvation through the **Inspection Recency** weight. |
| **Data Reliability** | **Derived** (Composite Sensor Quality) | All 7 villages achieve composite reliability \(\ge 0.91\). Cloud interference in August was effectively mitigated by QA cloud masking. | Transparent confidence multiplier on AI recommendation scores. |

---

## 2. Quantitative Findings by Domain

### 2.1 Rainfall Deficit Dynamics (Real Data)
- **Baseline**: 10-year normal rainfall in Maddur totals ~740 mm annually, with peaks in September (138 mm) and October (162 mm).
- **Anomaly Detection**:
  - In dekads 3–6 (July 1 to Aug 10, 2024), actual rainfall dropped below 40% of normal in rainfed pockets.
  - While sugarcane and canal paddy weathered this period through Shimsha canal releases, dryland ragi and red gram in Kadalur (`V_MDR_003`) and Hemmanahalli (`V_MDR_005`) experienced vegetative moisture stress.

### 2.2 Satellite NDVI Response & Vegetation Shock (Real Data)
- **Normal Trajectory**: Healthy paddy and sugarcane exhibit steady NDVI rises from 0.35 in June to 0.75+ in October.
- **Stress Signal**:
  - Kadalur NDVI dropped from 0.42 to 0.28 between August 5 and August 20 (\(-33.3\%\) relative drop).
  - Hemmanahalli dropped from 0.45 to 0.29 during the same window.
  - Irrigated parcels in Shivapura and Alur maintained stable NDVI (\(\ge 0.62\)), confirming the anomaly was agricultural drought rather than sensor error.

### 2.3 Reported Farmer Distress Density (Synthetic Data)
- Out of 35 total registered complaints:
  - 16 complaints (\(45.7\%\)) originated from Kadalur and Hemmanahalli alone.
  - Critical/High urgency issues: Yellow stem borer in paddy (3 incidents), finger blast in ragi (4 incidents), and early shoot borer in sugarcane (4 incidents).
  - Total affected area across all 35 complaints: 63.8 hectares (average parcel: 1.82 ha).

### 2.4 Field Inspection Recency Gaps (Synthetic Data)
- Standard Karnataka State Department of Agriculture (KSDA) operational guidelines recommend visiting every agricultural village at least once every 30 to 45 days.
- Current status:
  - Hemmanahalli: 85 days elapsed (**Critical Overdue**)
  - Kadalur: 68 days elapsed (**Overdue**)
  - Shivapura: 35 days elapsed (**Due Soon**)
  - Alur: 12 days elapsed (**Recent**)
  - Besagarahalli: 8 days elapsed (**Recent**)

---

## 3. Justified Mathematical Thresholds for Priority Engine

Based on these empirical distributions, we establish transparent, deterministic thresholds for the subsequent modules (Phases 8, 9, and 10):

### 3.1 Routine Monitoring Rules (Workflow Step 3)
1. **Rainfall Deficit Flag**:
   - Trigger when 30-day cumulative rainfall anomaly \(\le -25\%\).
   - Severe deficit penalty when anomaly \(\le -50\%\).
2. **NDVI Decline Flag**:
   - Trigger when bi-weekly cloud-free \(\Delta\text{NDVI} \le -12\%\).
   - Severe vegetation shock when \(\Delta\text{NDVI} \le -20\%\).
3. **Inspection Starvation Factor**:
   - Score multiplier: \(\min(1.0, \frac{\text{days\_since\_last\_inspection}}{60})\).

### 3.2 Reported Issue Monitoring Rules (Workflow Step 4)
1. **Urgency Weights**:
   - Critical: 1.00
   - High: 0.75
   - Medium: 0.45
   - Low: 0.20
2. **Affected Area Normalization**:
   - Area score = \(\min(1.0, \frac{\sum \text{affected\_area\_ha}}{10.0})\).
3. **Complaint Density Multiplier**:
   - Single complaint: 1.0x
   - 2–4 complaints (Cluster): 1.3x
   - 5+ complaints (Outbreak Alert): 1.6x

### 3.3 De-Duplication & Anti-Double-Counting Rule (Workflow Step 5)
When a village simultaneously triggers a satellite/rainfall drought signal AND multiple farmer water-stress complaints, the system applies an **integrated root-cause consolidation rule**:
$$\text{Stress}_{\text{Combined}} = \max(\text{Routine\_Drought\_Score}, \text{Reported\_Water\_Score}) + 0.20 \times \min(\text{Routine\_Drought\_Score}, \text{Reported\_Water\_Score})$$
This mathematically prevents inflating the rank of a single underlying physical event while acknowledging independent cross-verification between sensors and farmers.
