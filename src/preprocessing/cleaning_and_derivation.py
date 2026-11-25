"""
AgriResolve AI - Cleaning and Preprocessing Pipeline
Standardizes raw datasets, handles missing values/outliers, and computes
derived indicators (Rainfall Anomaly, NDVI Deltas, Data Reliability Scores).
Saves cleaned and derived tables to Excel (.xlsx) and CSV formats.
"""

from pathlib import Path
import pandas as pd
import numpy as np

def clean_and_derive():
    raw_dir = Path("data/raw")
    synthetic_dir = Path("data/synthetic")
    clean_dir = Path("data/cleaned")
    derive_dir = Path("data/derived")
    docs_dir = Path("docs")
    
    clean_dir.mkdir(parents=True, exist_ok=True)
    derive_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. Clean Villages Metadata
    # -------------------------------------------------------------
    df_villages = pd.read_excel(raw_dir / "villages_raw.xlsx")
    df_villages["village_name"] = df_villages["village_name"].str.strip()
    df_villages["lgd_code"] = df_villages["lgd_code"].astype(int)
    df_villages["latitude"] = df_villages["latitude"].round(4)
    df_villages["longitude"] = df_villages["longitude"].round(4)
    df_villages["cultivated_area_hectares"] = df_villages["cultivated_area_hectares"].clip(lower=0)
    
    df_villages.to_excel(clean_dir / "villages_cleaned.xlsx", index=False, engine="openpyxl")
    df_villages.to_csv(clean_dir / "villages_cleaned.csv", index=False)
    
    # -------------------------------------------------------------
    # 2. Clean & Derive Rainfall Data
    # -------------------------------------------------------------
    df_rain = pd.read_excel(raw_dir / "rainfall_raw.xlsx")
    df_rain["observation_date"] = pd.to_datetime(df_rain["observation_date"]).dt.strftime("%Y-%m-%d")
    df_rain["actual_rainfall_mm"] = df_rain["actual_rainfall_mm"].clip(lower=0.0)
    df_rain["normal_rainfall_mm"] = df_rain["normal_rainfall_mm"].clip(lower=0.1)
    
    df_rain.to_excel(clean_dir / "rainfall_cleaned.xlsx", index=False, engine="openpyxl")
    df_rain.to_csv(clean_dir / "rainfall_cleaned.csv", index=False)
    
    # Derivation: Rainfall Anomaly
    df_rain_derived = df_rain.copy()
    df_rain_derived["rainfall_anomaly_mm"] = (df_rain_derived["actual_rainfall_mm"] - df_rain_derived["normal_rainfall_mm"]).round(2)
    df_rain_derived["rainfall_anomaly_percent"] = (
        (df_rain_derived["rainfall_anomaly_mm"] / df_rain_derived["normal_rainfall_mm"]) * 100.0
    ).round(2)
    
    # IMD Meteorological Drought Classification:
    # Normal: -19% to +19%
    # Excess: >= +20%
    # Deficit: -20% to -59%
    # Severe Deficit: <= -60%
    def classify_rainfall(pct):
        if pct >= 20.0:
            return "Excess"
        elif pct >= -19.0:
            return "Normal"
        elif pct >= -59.0:
            return "Deficit"
        else:
            return "Severe Deficit"
            
    df_rain_derived["rainfall_status"] = df_rain_derived["rainfall_anomaly_percent"].apply(classify_rainfall)
    df_rain_derived["data_type"] = "Derived"
    df_rain_derived["is_synthetic"] = False
    
    df_rain_derived.to_excel(derive_dir / "rainfall_anomaly_derived.xlsx", index=False, engine="openpyxl")
    df_rain_derived.to_csv(derive_dir / "rainfall_anomaly_derived.csv", index=False)
    
    # -------------------------------------------------------------
    # 3. Clean & Derive Sentinel-2 NDVI Data
    # -------------------------------------------------------------
    df_ndvi = pd.read_excel(raw_dir / "ndvi_raw.xlsx")
    df_ndvi["observation_date"] = pd.to_datetime(df_ndvi["observation_date"]).dt.strftime("%Y-%m-%d")
    df_ndvi["mean_ndvi"] = df_ndvi["mean_ndvi"].clip(lower=0.0, upper=1.0).round(3)
    
    # Mask out or flag high cloud contamination
    df_ndvi["is_cloud_masked"] = df_ndvi["cloud_cover_percent"] > 20.0
    
    df_ndvi.to_excel(clean_dir / "ndvi_cleaned.xlsx", index=False, engine="openpyxl")
    df_ndvi.to_csv(clean_dir / "ndvi_cleaned.csv", index=False)
    
    # Derivation: Period-over-period NDVI delta and Vegetation Drops
    df_ndvi_derived = df_ndvi.sort_values(["village_id", "observation_date"]).copy()
    df_ndvi_derived["prev_ndvi"] = df_ndvi_derived.groupby("village_id")["mean_ndvi"].shift(1)
    df_ndvi_derived["ndvi_delta"] = (df_ndvi_derived["mean_ndvi"] - df_ndvi_derived["prev_ndvi"]).round(3)
    df_ndvi_derived["ndvi_pct_change"] = (
        (df_ndvi_derived["ndvi_delta"] / df_ndvi_derived["prev_ndvi"].replace(0, np.nan)) * 100.0
    ).round(2)
    
    # Flag significant drops (> 12% drop between successive observations)
    df_ndvi_derived["vegetation_stress_flag"] = (df_ndvi_derived["ndvi_pct_change"] <= -12.0) & (~df_ndvi_derived["is_cloud_masked"])
    df_ndvi_derived["data_type"] = "Derived"
    df_ndvi_derived["is_synthetic"] = False
    
    df_ndvi_derived.to_excel(derive_dir / "ndvi_trends_derived.xlsx", index=False, engine="openpyxl")
    df_ndvi_derived.to_csv(derive_dir / "ndvi_trends_derived.csv", index=False)
    
    # -------------------------------------------------------------
    # 4. Clean Synthetic Complaints and Inspections
    # -------------------------------------------------------------
    df_complaints = pd.read_excel(synthetic_dir / "farmer_complaints.xlsx")
    df_complaints["reported_date"] = pd.to_datetime(df_complaints["reported_date"]).dt.strftime("%Y-%m-%d")
    df_complaints["affected_area_hectares"] = df_complaints["affected_area_hectares"].clip(lower=0.1, upper=50.0).round(2)
    
    df_complaints.to_excel(clean_dir / "complaints_cleaned.xlsx", index=False, engine="openpyxl")
    df_complaints.to_csv(clean_dir / "complaints_cleaned.csv", index=False)
    
    df_inspections = pd.read_excel(synthetic_dir / "inspections_history.xlsx")
    df_inspections["inspection_date"] = pd.to_datetime(df_inspections["inspection_date"]).dt.strftime("%Y-%m-%d")
    df_inspections.to_excel(clean_dir / "inspections_cleaned.xlsx", index=False, engine="openpyxl")
    df_inspections.to_csv(clean_dir / "inspections_cleaned.csv", index=False)
    
    # -------------------------------------------------------------
    # 5. Derive Per-Village Data Reliability & Completeness Index
    # -------------------------------------------------------------
    # Metrics per village:
    # 1. Clear NDVI observations ratio (clear_count / total_observations)
    # 2. Rainfall observations count completeness
    # 3. Days elapsed since latest satellite / weather observation
    # Overall reliability score = 0.5 * clear_ratio + 0.3 * rainfall_completeness + 0.2 * recency_factor
    reliability_rows = []
    total_ndvi_obs_per_v = len(df_ndvi["observation_date"].unique())
    total_rain_obs_per_v = len(df_rain["observation_date"].unique())
    
    for v_id in df_villages["village_id"]:
        v_name = df_villages.loc[df_villages["village_id"] == v_id, "village_name"].values[0]
        v_ndvi = df_ndvi[df_ndvi["village_id"] == v_id]
        v_rain = df_rain[df_rain["village_id"] == v_id]
        
        clear_ndvi_count = len(v_ndvi[~v_ndvi["is_cloud_masked"]])
        clear_ratio = round(clear_ndvi_count / max(1, total_ndvi_obs_per_v), 3)
        rain_ratio = round(len(v_rain) / max(1, total_rain_obs_per_v), 3)
        
        # Mean cloud cover
        mean_cloud = round(v_ndvi["cloud_cover_percent"].mean(), 1)
        
        # Reliability formula
        reliability_score = round(float(np.clip(0.55 * clear_ratio + 0.35 * rain_ratio + 0.10 * (1 - mean_cloud / 100), 0.50, 1.00)), 2)
        
        reliability_rows.append({
            "village_id": v_id,
            "village_name": v_name,
            "total_satellite_passes": total_ndvi_obs_per_v,
            "clear_satellite_passes": clear_ndvi_count,
            "mean_cloud_cover_percent": mean_cloud,
            "rainfall_observations_count": len(v_rain),
            "data_completeness_ratio": round((clear_ratio + rain_ratio) / 2.0, 3),
            "overall_reliability_score": reliability_score,
            "reliability_tier": "High" if reliability_score >= 0.85 else ("Medium" if reliability_score >= 0.70 else "Low"),
            "data_type": "Derived",
            "is_synthetic": False
        })
        
    df_rel = pd.DataFrame(reliability_rows)
    df_rel.to_excel(derive_dir / "village_reliability_derived.xlsx", index=False, engine="openpyxl")
    df_rel.to_csv(derive_dir / "village_reliability_derived.csv", index=False)
    
    print("Cleaned and derived data saved successfully in both .xlsx and .csv formats.")
    return df_villages, df_rain_derived, df_ndvi_derived, df_complaints, df_rel

if __name__ == "__main__":
    clean_and_derive()
