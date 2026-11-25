# Phase 3: Dataset Identification & Provenance Guide

## 1. Real vs. Derived vs. Synthetic Decision Matrix

To ensure absolute transparency and scientific integrity (Rule A2.5 and Rule A2.6), each system component is classified with its exact provenance:

| Data Component | Provenance Class | Primary Source / Basis | Spatial Resolution | Temporal Coverage | Why This Classification? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Village Geographic Metadata** | **Real** | Local Government Directory (LGD), Ministry of Panchayati Raj, GoI & KGIS | Village level (Point / Centroid) | Static (Census 2011 / Current) | Official administrative registry with verified LGD codes and coordinates. |
| **Historical & Current Rainfall** | **Real** | India Meteorological Department (IMD) Gridded 0.25° & KSNDMC Hobli Reports | 0.25° × 0.25° (~27 km) & Hobli-level gauges | 2014 – 2024 (10-year daily/monthly series) | Official meteorological observations mapped to Maddur / Mandya grid cells. |
| **Satellite Vegetation Index (NDVI)** | **Real / Derived** | Copernicus Sentinel-2 MSI via Google Earth Engine / Planetary Computer | 10m Ground Sampling Distance (GSD) | Bi-weekly composites (2023–2024 Kharif & Rabi) | Computed from Band 8 (NIR) and Band 4 (Red) surface reflectance. |
| **Crop Statistics & Area** | **Real** | Directorate of Economics and Statistics (DES), Govt of Karnataka | Taluk / District baseline mapped to villages | Multi-year agricultural census | Official Mandya district crop production and acreages. |
| **Package of Practices (PoP)** | **Real** | University of Agricultural Sciences (UAS), Bengaluru & ICAR | Agro-climatic Zone 6 (Southern Dry Zone) | Published Agricultural Guidelines | Official university package of practices for Sugarcane, Ragi, Paddy, Pulses. |
| **Rainfall Anomaly & Trends** | **Derived** | Computed from Real IMD/KSNDMC baseline | Village level | Computed | Calculated as: \((R_{observed} - R_{normal}) / R_{normal} \times 100\). |
| **NDVI Delta & Vegetation Drops** | **Derived** | Computed from Real Sentinel-2 time series | Village centroid buffer (1000m) | Computed | Computed as: \((NDVI_{t} - NDVI_{t-1}) / NDVI_{t-1}\). |
| **Farmer Complaints** | **Synthetic** | Seeded Generator (`src/ingestion/synthetic/`) | Village & Farmer level | Controlled 90-day simulation | Real farmer complaint databases contain private contact information and are protected under Indian Data Protection laws. |
| **Staff Workload & History** | **Synthetic** | Seeded Generator | RSK Staff level | Controlled 90-day simulation | Government internal staff attendance and leave logs are restricted administrative records. |
| **Inspection Records** | **Synthetic** | Seeded Generator | Field Inspection level | Historical 180 days | Simulated past inspection outcomes for machine calibration. |

---

## 2. Exhaustive Data Source Catalog

### 2.1 Local Government Directory (LGD) - Village Codes
- **Source Organisation**: Ministry of Panchayati Raj, Government of India.
- **Official URL**: [https://lgdirectory.gov.in](https://lgdirectory.gov.in)
- **Geographic Coverage**: All revenue villages in Maddur Taluk, Mandya District, Karnataka.
- **License / Terms**: Open Government Data (OGD) License India.
- **Collection Date**: November 2024.
- **Limitations**: Provides official census codes, names, and administrative hierarchy; centroid coordinates are cross-verified with KGIS.

### 2.2 India Meteorological Department (IMD) - Rainfall
- **Source Organisation**: India Meteorological Department (IMD), Ministry of Earth Sciences, GoI & KSNDMC.
- **Official URL**: [https://mausam.imd.gov.in](https://mausam.imd.gov.in) / [https://www.ksndmc.org](https://www.ksndmc.org)
- **Geographic Coverage**: Latitude 12.50°N - 12.75°N, Longitude 76.75°E - 77.25°E.
- **Temporal Coverage**: 2014 to 2024 daily precipitation observations.
- **Spatial Resolution**: 0.25° gridded products mapped to Maddur hobli rain gauge stations.
- **License / Terms**: Free for research and educational non-commercial use.
- **Limitations**: High temporal accuracy, but gridded data requires hobli gauge calibration for micro-topographic showers.

### 2.3 Copernicus Sentinel-2 MSI - Surface Reflectance (NDVI)
- **Source Organisation**: European Space Agency (ESA) & European Commission / Copernicus Open Access Hub via Google Earth Engine (`COPERNICUS/S2_SR_HARMONIZED`).
- **Official URL**: [https://browser.dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu)
- **Geographic Coverage**: S2 Tile `43PGP` (Mandya, Karnataka).
- **Spatial Resolution**: 10 meters (Red B4: 665 nm, NIR B8: 842 nm).
- **Temporal Resolution**: 5-day revisit cycle.
- **Formula**: \(\text{NDVI} = \frac{\text{B8} - \text{B4}}{\text{B8} + \text{B4}}\). Cloud masking via Scene Classification Layer (SCL) and QA60 band.
- **Limitations**: Cloud cover during southwest monsoon (June-August) produces missing or interpolated observations.

### 2.4 Karnataka Directorate of Economics & Statistics (DES) - Crops
- **Source Organisation**: Directorate of Economics and Statistics, Government of Karnataka.
- **Official URL**: [https://des.karnataka.gov.in](https://des.karnataka.gov.in)
- **Coverage**: Mandya District agricultural season reports.
- **Data Extracted**: Crop classification, normal sown area, yields for Sugarcane (*Saccharum officinarum*), Paddy (*Oryza sativa*), Finger Millet / Ragi (*Eleusine coracana*), and Mulberry.

### 2.5 UAS Bangalore Package of Practices (PoP)
- **Source Organisation**: University of Agricultural Sciences, GKVK, Bengaluru & ICAR.
- **Official URL**: [https://uasbangalore.edu.in](https://uasbangalore.edu.in)
- **Document**: Package of Practices for High Yielding Varieties of Crops - Zone 6.
- **Use in AgriResolve AI**: Ground-truth agricultural guidance for the RAG assistant and crop distress diagnostic rules.

---

## 3. Honest Statement on Resolution & Missing Data

- Rainfall data is aggregated at Hobli/Taluk level and assigned to constituent villages.
- Sentinel-2 NDVI reflects pixel composites within the agricultural parcels of each village boundary.
- All synthetic datasets contain explicit tracking columns: `is_synthetic = TRUE` and `data_type = 'Synthetic'`.
