"""
AgriResolve AI - Reported Issue Monitoring Engine (Step 4)
Processes farmer complaints to flag and score villages by evaluating:
1. Complaint urgency (Critical, High, Medium, Low)
2. Cumulative affected crop area (hectares)
3. Cluster density (multiple complaints in the same village)
4. Unresolved complaint aging (days pending)
5. Economic crop importance

Outputs severity scores (0-100), factor breakdowns, and linked complaint IDs.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

def run_reported_monitoring(
    data_dir: str = "data",
    reference_date: str = "2024-11-20",
    severity_flag_threshold: float = 35.0
):
    clean_dir = Path(data_dir) / "cleaned"
    derived_dir = Path(data_dir) / "derived"
    raw_dir = Path(data_dir) / "raw"
    
    # Load data
    df_villages = pd.read_excel(clean_dir / "villages_cleaned.xlsx")
    df_complaints = pd.read_excel(clean_dir / "complaints_cleaned.xlsx")
    df_crops = pd.read_excel(raw_dir / "crop_statistics_raw.xlsx", sheet_name="Crops_Catalog")
    
    crop_weights = dict(zip(df_crops["crop_name"], df_crops["priority_economic_weight"]))
    
    urgency_weights = {
        "Critical": 1.00,
        "High": 0.75,
        "Medium": 0.45,
        "Low": 0.20
    }
    
    ref_dt = datetime.strptime(reference_date, "%Y-%m-%d")
    results = []
    
    for _, v_row in df_villages.iterrows():
        v_id = v_row["village_id"]
        v_name = v_row["village_name"]
        
        v_comp = df_complaints[df_complaints["village_id"] == v_id].copy()
        complaint_count = len(v_comp)
        
        if complaint_count == 0:
            results.append({
                "village_id": v_id,
                "village_name": v_name,
                "reported_flag": False,
                "reported_severity_score": 0.0,
                "total_complaints": 0,
                "critical_complaints_count": 0,
                "total_affected_area_ha": 0.0,
                "linked_complaint_ids": "",
                "top_issue": "None",
                "explanation": "No registered farmer complaints.",
                "data_type": "Derived",
                "is_synthetic": True
            })
            continue
            
        # 1. Urgency Score (0 - 40 pts)
        avg_urgency = v_comp["urgency_level"].map(urgency_weights).mean()
        critical_count = (v_comp["urgency_level"] == "Critical").sum()
        high_count = (v_comp["urgency_level"] == "High").sum()
        urgency_score = min(40.0, (avg_urgency * 30.0) + (critical_count * 5.0))
        
        # 2. Affected Area Score (0 - 30 pts)
        total_area = v_comp["affected_area_hectares"].sum()
        area_score = min(30.0, (total_area / 15.0) * 30.0)
        
        # 3. Cluster Density Multiplier (0 - 20 pts)
        # More complaints in a single village indicate an emerging outbreak
        density_score = min(20.0, (complaint_count / 8.0) * 20.0)
        
        # 4. Aging / Waiting Time Score (0 - 10 pts)
        v_comp["days_pending"] = v_comp["reported_date"].apply(
            lambda d: max(0, (ref_dt - datetime.strptime(str(d), "%Y-%m-%d")).days)
        )
        avg_aging = v_comp["days_pending"].mean()
        aging_score = min(10.0, (avg_aging / 30.0) * 10.0)
        
        # Total Severity Score (0 - 100)
        total_severity = round(urgency_score + area_score + density_score + aging_score, 2)
        flagged = total_severity >= severity_flag_threshold
        
        # Identify top issue
        top_issue = v_comp["issue_category"].mode()[0]
        linked_ids = ", ".join(v_comp["complaint_id"].tolist())
        
        explanation = (
            f"{complaint_count} complaints registered ({critical_count} critical, {high_count} high) "
            f"covering {total_area:.1f} ha. Dominant issue: {top_issue}."
        )
        
        results.append({
            "village_id": v_id,
            "village_name": v_name,
            "reported_flag": flagged,
            "reported_severity_score": total_severity,
            "total_complaints": complaint_count,
            "critical_complaints_count": critical_count,
            "total_affected_area_ha": round(total_area, 2),
            "linked_complaint_ids": linked_ids,
            "top_issue": top_issue,
            "explanation": explanation,
            "data_type": "Derived",
            "is_synthetic": True
        })
        
    df_reported = pd.DataFrame(results).sort_values("reported_severity_score", ascending=False).reset_index(drop=True)
    
    # Save outputs
    output_xlsx = Path("data/derived/reported_monitoring_results.xlsx")
    output_csv = Path("data/derived/reported_monitoring_results.csv")
    df_reported.to_excel(output_xlsx, index=False, engine="openpyxl")
    df_reported.to_csv(output_csv, index=False)
    
    print(f"Reported monitoring completed. Flagged {df_reported['reported_flag'].sum()} of {len(df_reported)} villages.")
    return df_reported

if __name__ == "__main__":
    df = run_reported_monitoring()
    print(df[["village_name", "reported_flag", "reported_severity_score", "explanation"]])
