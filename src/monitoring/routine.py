"""
AgriResolve AI - Routine Monitoring Engine (Step 3)
Flags villages needing inspection without any farmer complaint by synthesizing:
1. Rainfall anomaly deviation (IMD/KSNDMC baseline)
2. Sentinel-2 NDVI decline & vegetation stress drops
3. Field inspection recency (days elapsed)
4. Village data reliability indicators

Outputs transparent risk scores (0-100), contributing factors, and plain-language explanations.
"""

from pathlib import Path
import pandas as pd
import numpy as np

def run_routine_monitoring(
    data_dir: str = "data",
    rainfall_weight: float = 0.35,
    ndvi_weight: float = 0.35,
    recency_weight: float = 0.15,
    reliability_weight: float = 0.15,
    risk_flag_threshold: float = 40.0
):
    clean_dir = Path(data_dir) / "cleaned"
    derived_dir = Path(data_dir) / "derived"
    
    # 1. Load data
    df_villages = pd.read_excel(clean_dir / "villages_cleaned.xlsx")
    df_rain = pd.read_excel(derived_dir / "rainfall_anomaly_derived.xlsx")
    df_ndvi = pd.read_excel(derived_dir / "ndvi_trends_derived.xlsx")
    df_inspections = pd.read_excel(clean_dir / "inspections_cleaned.xlsx")
    df_reliability = pd.read_excel(derived_dir / "village_reliability_derived.xlsx")
    
    # Latest 30-day average rainfall anomaly per village
    recent_rain = df_rain.sort_values("observation_date").groupby("village_id").tail(3)
    rain_summary = recent_rain.groupby("village_id")["rainfall_anomaly_percent"].mean().reset_index()
    
    # Latest NDVI observation and recent delta
    latest_ndvi = df_ndvi.sort_values("observation_date").groupby("village_id").last().reset_index()
    
    # Latest inspection recency
    latest_insp = df_inspections.groupby("village_id")["days_since_last_inspection"].min().reset_index()
    
    results = []
    
    for _, v_row in df_villages.iterrows():
        v_id = v_row["village_id"]
        v_name = v_row["village_name"]
        
        # Factor 1: Rainfall Deficit Factor (0 - 100)
        # Anomaly <= -50% gives 100 pts; normal or positive gives 0 pts
        r_anomaly = rain_summary.loc[rain_summary["village_id"] == v_id, "rainfall_anomaly_percent"].values[0]
        if r_anomaly < 0:
            rain_risk = float(np.clip(abs(r_anomaly) * 1.5, 0.0, 100.0))
        else:
            rain_risk = 0.0
            
        # Factor 2: NDVI Vegetation Decline Factor (0 - 100)
        v_ndvi_row = latest_ndvi.loc[latest_ndvi["village_id"] == v_id].iloc[0]
        mean_ndvi = v_ndvi_row["mean_ndvi"]
        ndvi_pct_change = v_ndvi_row["ndvi_pct_change"]
        
        ndvi_risk = 0.0
        if mean_ndvi < 0.35:
            ndvi_risk += 40.0
        if ndvi_pct_change < 0:
            ndvi_risk += float(np.clip(abs(ndvi_pct_change) * 2.5, 0.0, 60.0))
        ndvi_risk = min(100.0, ndvi_risk)
        
        # Factor 3: Inspection Recency (0 - 100)
        # > 60 days gives 100 pts; < 15 days gives ~15 pts
        days_since = latest_insp.loc[latest_insp["village_id"] == v_id, "days_since_last_inspection"].values[0]
        recency_risk = float(np.clip((days_since / 60.0) * 100.0, 0.0, 100.0))
        
        # Factor 4: Data Reliability Multiplier
        rel_score = df_reliability.loc[df_reliability["village_id"] == v_id, "overall_reliability_score"].values[0]
        
        # Weighted Composite Score
        composite_score = round(
            (rain_risk * rainfall_weight) +
            (ndvi_risk * ndvi_weight) +
            (recency_risk * recency_weight) +
            ((1.0 - rel_score) * 100.0 * reliability_weight),
            2
        )
        
        flagged = composite_score >= risk_flag_threshold
        
        # Construct Plain Language Explanation
        reasons = []
        if rain_risk >= 40:
            reasons.append(f"Cumulative rainfall deficit of {r_anomaly:.1f}%")
        if ndvi_risk >= 35:
            reasons.append(f"Vegetation index drop of {ndvi_pct_change:.1f}% (NDVI: {mean_ndvi:.2f})")
        if days_since >= 45:
            reasons.append(f"Inspection overdue ({days_since} days since last visit)")
            
        explanation = "; ".join(reasons) if reasons else "Parameters within normal seasonal range."
        
        results.append({
            "village_id": v_id,
            "village_name": v_name,
            "routine_flag": flagged,
            "routine_risk_score": composite_score,
            "rainfall_deficit_risk": round(rain_risk, 1),
            "ndvi_decline_risk": round(ndvi_risk, 1),
            "inspection_recency_days": days_since,
            "recency_risk": round(recency_risk, 1),
            "data_reliability_score": rel_score,
            "explanation": explanation,
            "data_type": "Derived",
            "is_synthetic": False
        })
        
    df_routine = pd.DataFrame(results).sort_values("routine_risk_score", ascending=False).reset_index(drop=True)
    
    # Save to Excel and CSV
    output_path_xlsx = Path("data/derived/routine_monitoring_results.xlsx")
    output_path_csv = Path("data/derived/routine_monitoring_results.csv")
    df_routine.to_excel(output_path_xlsx, index=False, engine="openpyxl")
    df_routine.to_csv(output_path_csv, index=False)
    
    print(f"Routine monitoring completed. Flagged {df_routine['routine_flag'].sum()} of {len(df_routine)} villages.")
    return df_routine

if __name__ == "__main__":
    df = run_routine_monitoring()
    print(df[["village_name", "routine_flag", "routine_risk_score", "explanation"]])
