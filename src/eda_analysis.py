"""
AgriResolve AI - Exploratory Data Analysis & Visualization
Generates interactive Plotly figures for:
1. Rainfall vs Historical Baseline (Deficit/Excess)
2. Sentinel-2 NDVI Time Series & Vegetation Drops
3. Farmer Complaints Distribution by Crop, Village & Issue Category
4. Field Inspection Recency Gaps
5. Per-Village Data Reliability & Completeness
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def run_eda():
    output_dir = Path("docs/eda_charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    clean_dir = Path("data/cleaned")
    derived_dir = Path("data/derived")
    synthetic_dir = Path("data/synthetic")
    
    # -------------------------------------------------------------
    # 1. Rainfall Anomaly vs Normal Baseline (REAL DATA)
    # -------------------------------------------------------------
    df_rain = pd.read_excel(derived_dir / "rainfall_anomaly_derived.xlsx")
    
    fig_rain = px.bar(
        df_rain,
        x="observation_date",
        y="rainfall_anomaly_percent",
        color="rainfall_status",
        facet_col="village_name",
        facet_col_wrap=3,
        title="Rainfall Anomaly (%) vs 10-Year IMD Baseline by Village (Real Data)",
        color_discrete_map={
            "Excess": "#2ca02c",
            "Normal": "#1f77b4",
            "Deficit": "#ff7f0e",
            "Severe Deficit": "#d62728"
        },
        labels={"rainfall_anomaly_percent": "Anomaly (%)", "observation_date": "Date"}
    )
    fig_rain.update_layout(height=700, template="plotly_white")
    fig_rain.write_html(str(output_dir / "rainfall_anomaly.html"))
    
    # -------------------------------------------------------------
    # 2. Sentinel-2 NDVI Trajectory & Stress Drops (REAL DATA)
    # -------------------------------------------------------------
    df_ndvi = pd.read_excel(derived_dir / "ndvi_trends_derived.xlsx")
    
    fig_ndvi = px.line(
        df_ndvi,
        x="observation_date",
        y="mean_ndvi",
        color="village_name",
        markers=True,
        title="Sentinel-2 MSI 10m NDVI Trajectory (Kharif - Post-Monsoon 2024) (Real Data)",
        labels={"mean_ndvi": "Mean Agricultural NDVI", "observation_date": "Observation Date"}
    )
    fig_ndvi.add_hline(y=0.30, line_dash="dash", line_color="red", annotation_text="Vegetation Stress Threshold (0.30)")
    fig_ndvi.update_layout(height=500, template="plotly_white")
    fig_ndvi.write_html(str(output_dir / "ndvi_trends.html"))
    
    # -------------------------------------------------------------
    # 3. Farmer Complaints Breakdown (SYNTHETIC DATA)
    # -------------------------------------------------------------
    df_complaints = pd.read_excel(clean_dir / "complaints_cleaned.xlsx")
    
    fig_comp = px.sunburst(
        df_complaints,
        path=["village_name", "crop_affected", "issue_category"],
        values="affected_area_hectares",
        color="urgency_level",
        title="Reported Farmer Distress by Village, Crop & Issue Category (Synthetic Data)",
        color_discrete_map={"Low": "#2ca02c", "Medium": "#ffbb78", "High": "#ff7f0e", "Critical": "#d62728"}
    )
    fig_comp.update_layout(height=600)
    fig_comp.write_html(str(output_dir / "complaints_sunburst.html"))
    
    # -------------------------------------------------------------
    # 4. Inspection Recency Gap Analysis (SYNTHETIC DATA)
    # -------------------------------------------------------------
    df_inspections = pd.read_excel(clean_dir / "inspections_cleaned.xlsx")
    
    fig_insp = px.bar(
        df_inspections.sort_values("days_since_last_inspection", ascending=False),
        x="days_since_last_inspection",
        y="village_name",
        orientation="h",
        color="days_since_last_inspection",
        color_continuous_scale="Reds",
        title="Days Elapsed Since Last Field Inspection by Village (Synthetic Data)",
        labels={"days_since_last_inspection": "Days Elapsed", "village_name": "Village"}
    )
    fig_insp.add_vline(x=45, line_dash="dash", line_color="orange", annotation_text="Inspection Gap Warning (45 days)")
    fig_insp.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Critical Overdue (60 days)")
    fig_insp.update_layout(height=450, template="plotly_white")
    fig_insp.write_html(str(output_dir / "inspection_gaps.html"))
    
    # -------------------------------------------------------------
    # 5. Data Reliability Radar / Scatter (DERIVED DATA)
    # -------------------------------------------------------------
    df_rel = pd.read_excel(derived_dir / "village_reliability_derived.xlsx")
    
    fig_rel = px.scatter(
        df_rel,
        x="mean_cloud_cover_percent",
        y="overall_reliability_score",
        size="clear_satellite_passes",
        color="reliability_tier",
        text="village_name",
        title="Data Reliability Score vs Mean Cloud Cover (%) (Derived Metric)",
        labels={
            "mean_cloud_cover_percent": "Mean Cloud Cover (%)",
            "overall_reliability_score": "Overall Data Reliability Score"
        }
    )
    fig_rel.update_traces(textposition="top center")
    fig_rel.update_layout(height=450, template="plotly_white")
    fig_rel.write_html(str(output_dir / "data_reliability.html"))
    
    print("All EDA Plotly HTML visualizations successfully generated in docs/eda_charts/.")
    return True

if __name__ == "__main__":
    run_eda()
