"""
AgriResolve AI - Combined AI Priority Engine (Step 5)
Synthesizes Routine Monitoring (sensors/weather) and Reported Issue Monitoring (grievances)
into a single, explainable, ranked priority list.

Key Features:
1. Anti-double-counting rule for drought / moisture signals
2. Transparent weighted factor decomposition
3. Capacity-aware inspection recommendation based on RSK staff availability
4. Explainable text narratives and factor breakdowns
"""

from pathlib import Path
import pandas as pd
import numpy as np

def run_priority_engine(
    data_dir: str = "data",
    routine_weight: float = 0.45,
    reported_weight: float = 0.45,
    reliability_weight: float = 0.10,
    staff_weekly_capacity: int = 4  # Typical AO team capacity for high-priority villages
):
    clean_dir = Path(data_dir) / "cleaned"
    derived_dir = Path(data_dir) / "derived"
    synthetic_dir = Path(data_dir) / "synthetic"
    
    # 1. Load Routine & Reported Monitoring Outputs
    df_routine = pd.read_excel(derived_dir / "routine_monitoring_results.xlsx")
    df_reported = pd.read_excel(derived_dir / "reported_monitoring_results.xlsx")
    df_access = pd.read_excel(synthetic_dir / "village_accessibility.xlsx")
    df_reliability = pd.read_excel(derived_dir / "village_reliability_derived.xlsx")
    df_staff = pd.read_excel(synthetic_dir / "staff_roster.xlsx")
    
    # Merge datasets on village_id
    df_merged = df_routine.merge(df_reported, on=["village_id", "village_name"], suffixes=("_routine", "_reported"))
    df_merged = df_merged.merge(df_access[["village_id", "road_distance_km", "est_travel_time_mins", "road_condition"]], on="village_id")
    df_merged = df_merged.merge(df_reliability[["village_id", "overall_reliability_score", "reliability_tier"]], on="village_id")
    
    scored_records = []
    factor_records = []
    
    for _, row in df_merged.iterrows():
        v_id = row["village_id"]
        v_name = row["village_name"]
        
        routine_score = float(row["routine_risk_score"])
        reported_score = float(row["reported_severity_score"])
        
        # -------------------------------------------------------------
        # Anti-Double-Counting Rule (Drought + Water Stress Complaints)
        # -------------------------------------------------------------
        # If both satellite drought and water complaints are present, don't blindly add them
        if (row["rainfall_deficit_risk"] > 30.0 or row["ndvi_decline_risk"] > 30.0) and ("Drought" in str(row["top_issue"]) or "Water" in str(row["top_issue"])):
            combined_agro_risk = max(routine_score, reported_score) + (0.25 * min(routine_score, reported_score))
        else:
            combined_agro_risk = (routine_score * 0.5) + (reported_score * 0.5)
            
        # Road distance is retained as logistics metadata only (excluded from priority score)
        dist_km = float(row["road_distance_km"])
        
        # Reliability factor (High reliability gets full confidence, max 10 pts)
        rel_score = float(row["overall_reliability_score"])
        rel_weighted = rel_score * 10.0
        
        # Final Combined Priority Score (0 to 100) across 3 parameters:
        # 1. Reported Distress (45%), 2. Routine Agro Risk (45%), 3. Data Reliability (10%)
        final_score = round(
            (combined_agro_risk * (routine_weight + reported_weight)) +
            (rel_weighted * (reliability_weight * 10.0)),
            2
        )
        
        # Plain-language justification
        reasons = []
        if reported_score >= 50:
            reasons.append(f"Severe farmer distress ({row['total_complaints']} complaints, {row['critical_complaints_count']} critical)")
        if row["ndvi_decline_risk"] >= 30:
            reasons.append("Notable satellite NDVI vegetative drop")
        if row["inspection_recency_days"] >= 45:
            reasons.append(f"Field visit overdue ({row['inspection_recency_days']} days)")
            
        narrative = ". ".join(reasons) + "." if reasons else "Routine monitoring indicates low immediate priority."
        
        scored_records.append({
            "priority_id": f"PRI_{v_id}",
            "village_id": v_id,
            "village_name": v_name,
            "combined_priority_score": final_score,
            "routine_risk_score": routine_score,
            "reported_severity_score": reported_score,
            "road_distance_km": dist_km,
            "est_travel_time_mins": row["est_travel_time_mins"],
            "data_reliability_score": rel_score,
            "reliability_tier": row["reliability_tier"],
            "human_explanation": narrative,
            "data_type": "Derived",
            "is_synthetic": False
        })
        
        # Store individual factor contributions for explainability chart (3 parameters)
        factor_records.extend([
            {"priority_id": f"PRI_{v_id}", "village_name": v_name, "factor": "Reported Distress", "contribution_pts": round(reported_score * reported_weight, 1)},
            {"priority_id": f"PRI_{v_id}", "village_name": v_name, "factor": "Routine Agro Risk", "contribution_pts": round(routine_score * routine_weight, 1)},
            {"priority_id": f"PRI_{v_id}", "village_name": v_name, "factor": "Data Reliability", "contribution_pts": round(rel_weighted * reliability_weight * 10.0, 1)}
        ])
        
    df_priorities = pd.DataFrame(scored_records).sort_values("combined_priority_score", ascending=False).reset_index(drop=True)
    df_priorities["rank_order"] = range(1, len(df_priorities) + 1)
    
    # Capacity-aware action recommendation
    def assign_action(rank):
        if rank <= 2:
            return "Inspect First (Immediate Dispatch - Tier 1)"
        elif rank <= staff_weekly_capacity:
            return "Schedule Routine Inspection (Tier 2)"
        else:
            return "Monitor Remotely (Tier 3)"
            
    df_priorities["recommendation_action"] = df_priorities["rank_order"].apply(assign_action)
    df_factors = pd.DataFrame(factor_records)
    
    # Save outputs
    output_priorities_xlsx = Path("data/derived/priority_scores.xlsx")
    output_priorities_csv = Path("data/derived/priority_scores.csv")
    output_factors_xlsx = Path("data/derived/priority_factors.xlsx")
    output_factors_csv = Path("data/derived/priority_factors.csv")
    
    df_priorities.to_excel(output_priorities_xlsx, index=False, engine="openpyxl")
    df_priorities.to_csv(output_priorities_csv, index=False)
    df_factors.to_excel(output_factors_xlsx, index=False, engine="openpyxl")
    df_factors.to_csv(output_factors_csv, index=False)
    
    print("\n--- COMBINED AI PRIORITY RANKING (Maddur RSK Cluster) ---")
    for _, r in df_priorities.iterrows():
        print(f"Rank {r['rank_order']}: {r['village_name']} | Score: {r['combined_priority_score']} | {r['recommendation_action']}")
        print(f"   Explanation: {r['human_explanation']}")
        
    return df_priorities, df_factors

if __name__ == "__main__":
    run_priority_engine()
