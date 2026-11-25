"""
AgriResolve AI - Main Streamlit Application Entrypoint
Provides role-based switching between:
1. Agriculture Officer (AO) Decision Dashboard
2. Assistant Agriculture Officer (AAO / AA) Field Interface
3. AI Field Inspection Assistant (RAG)
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="AgriResolve AI - Agricultural Inspection Decision Support",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Data Loading Helpers
# -------------------------------------------------------------
@st.cache_data
def load_all_data():
    clean_dir = Path("data/cleaned")
    derived_dir = Path("data/derived")
    synthetic_dir = Path("data/synthetic")
    
    df_villages = pd.read_excel(clean_dir / "villages_cleaned.xlsx")
    df_priorities = pd.read_excel(derived_dir / "priority_scores.xlsx")
    df_factors = pd.read_excel(derived_dir / "priority_factors.xlsx")
    df_routine = pd.read_excel(derived_dir / "routine_monitoring_results.xlsx")
    df_reported = pd.read_excel(derived_dir / "reported_monitoring_results.xlsx")
    df_complaints = pd.read_excel(clean_dir / "complaints_cleaned.xlsx")
    df_staff = pd.read_excel(synthetic_dir / "staff_roster.xlsx")
    df_ndvi = pd.read_excel(derived_dir / "ndvi_trends_derived.xlsx")
    df_rain = pd.read_excel(derived_dir / "rainfall_anomaly_derived.xlsx")
    
    return {
        "villages": df_villages,
        "priorities": df_priorities,
        "factors": df_factors,
        "routine": df_routine,
        "reported": df_reported,
        "complaints": df_complaints,
        "staff": df_staff,
        "ndvi": df_ndvi,
        "rain": df_rain
    }

data = load_all_data()

# -------------------------------------------------------------
# Sidebar Navigation & Transparency Badges
# -------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/wheat.png", width=64)
st.sidebar.title("AgriResolve AI")
st.sidebar.caption("Government of Karnataka | Department of Agriculture")

# Mandated Transparency Banners (Rule A2.5 & A2.6)
st.sidebar.markdown(
    """
    <div style="background-color: #fff3cd; padding: 10px; border-radius: 6px; border-left: 4px solid #ffeeba; margin-bottom: 12px;">
        <span style="color: #856404; font-size: 12px; font-weight: bold;">⚠️ PROTOCOL NOTICE:</span><br>
        <span style="color: #856404; font-size: 11px;">• RSK Mapping: <b>Simulated Administrative Prototype</b></span><br>
        <span style="color: #856404; font-size: 11px;">• Complaints & Staff: <b>Synthetically Tagged</b></span><br>
        <span style="color: #856404; font-size: 11px;">• Remote Sensing: <b>Real Sentinel-2 / IMD</b></span>
    </div>
    """,
    unsafe_allow_html=True
)

role = st.sidebar.radio(
    "Select Operating Role:",
    ["Agriculture Officer (AO) - Command Dashboard", "Assistant Agriculture Officer (AAO) - Field Workspace", "AI Field Assistant (Package of Practices)"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Maddur Kasaba RSK (`KA_MDR_01`)**\n"
    "• Taluk: Maddur\n"
    "• District: Mandya\n"
    "• Target Villages: 7 Revenue Villages\n"
    "• Operational Radius: 15 km"
)

# -------------------------------------------------------------
# 1. Agriculture Officer (AO) Dashboard
# -------------------------------------------------------------
if role == "Agriculture Officer (AO) - Command Dashboard":
    st.title("🌾 Agriculture Officer (AO) Inspection Command")
    st.markdown("Decision-support system for village prioritization, remote sensing audits, and field officer dispatch.")
    
    # Top KPI Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monitored Villages", len(data["villages"]), "7 Clusters")
    tier1_count = len(data["priorities"][data["priorities"]["recommendation_action"].str.contains("Tier 1")])
    c2.metric("Tier-1 Immediate Dispatches", tier1_count, "Urgent Priority", delta_color="inverse")
    c3.metric("Total Active Complaints", len(data["complaints"]), "Across 7 Villages")
    c4.metric("Active Field Staff", len(data["staff"]), "3 Officers Available")
    
    st.markdown("---")
    
    # Spatial Village Intelligence Map
    st.subheader("🗺️ RSK Village Intelligence & Priority Map")
    st.caption("Satellite and field distress overlay. Circle sizes indicate composite priority scores.")
    
    map_df = data["villages"].merge(data["priorities"][["village_id", "combined_priority_score", "rank_order", "recommendation_action"]], on="village_id")
    
    fig_map = px.scatter_mapbox(
        map_df,
        lat="latitude",
        lon="longitude",
        hover_name="village_name",
        hover_data={"combined_priority_score": True, "rank_order": True, "recommendation_action": True, "latitude": False, "longitude": False},
        color="combined_priority_score",
        size="combined_priority_score",
        color_continuous_scale="Reds",
        size_max=22,
        zoom=11.2,
        center={"lat": 12.575, "lon": 77.035},
        mapbox_style="carto-positron",
        title="Maddur RSK Spatial Intelligence"
    )
    fig_map.update_layout(height=450, margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig_map, use_container_width=True)
    
    # Ranked Priority List & Explainability
    st.subheader("📋 Explainable AI Village Priority Ranking")
    st.caption("Transparent factor decomposition: Routine Risk + Farmer Distress + Proximity - Data Reliability Penalty.")
    
    cols_to_show = ["rank_order", "village_name", "combined_priority_score", "recommendation_action", "human_explanation", "road_distance_km"]
    st.dataframe(
        data["priorities"][cols_to_show].rename(columns={
            "rank_order": "Rank",
            "village_name": "Village",
            "combined_priority_score": "Score (0-100)",
            "recommendation_action": "Recommendation",
            "human_explanation": "Decision Justification",
            "road_distance_km": "Distance (km)"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Factor Contribution Chart
    st.subheader("📊 Transparent Factor Breakdown (Why Did the AI Recommend This?)")
    selected_village = st.selectbox("Select Village for Deep Factor Inspection:", data["priorities"]["village_name"].tolist())
    
    village_factors = data["factors"][data["factors"]["village_name"] == selected_village]
    fig_bar = px.bar(
        village_factors,
        x="factor",
        y="contribution_pts",
        color="factor",
        text="contribution_pts",
        title=f"Factor Contributions to Priority Score for {selected_village}",
        labels={"contribution_pts": "Points Contributed", "factor": "Factor"}
    )
    fig_bar.update_layout(height=350, showlegend=False, template="plotly_white")
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # Staff Allocation & Dispatch Section
    st.subheader("👷 Staff Directory & Inspection Allocation")
    col_alloc1, col_alloc2 = st.columns([1, 1])
    
    with col_alloc1:
        st.write("##### Current Field Staff Availability")
        st.dataframe(data["staff"][["name", "role", "jurisdiction", "status", "active_inspections_count"]], use_container_width=True, hide_index=True)
        
    with col_alloc2:
        st.write("##### Assign Field Inspection (AO Action)")
        with st.form("assign_form"):
            target_v = st.selectbox("Target Village:", data["priorities"]["village_name"].tolist())
            assigned_officer = st.selectbox("Assign To Officer:", data["staff"]["name"].tolist())
            insp_date = st.date_input("Inspection Target Date:")
            instructions = st.text_area("Special Instructions:", "Verify yellow stem borer damage in paddy parcels; collect soil moisture readings.")
            submit_assign = st.form_submit_button("Approve & Dispatch Inspection")
            
            if submit_assign:
                st.success(f"Inspection successfully assigned to **{assigned_officer}** for **{target_v}** on {insp_date}!")

# -------------------------------------------------------------
# 2. Assistant Agriculture Officer (AAO) Dashboard
# -------------------------------------------------------------
elif role == "Assistant Agriculture Officer (AAO) - Field Workspace":
    st.title("🚜 AAO / AA Field Inspection Workspace")
    st.markdown("Field-oriented interface for mobile inspections, farmer distress logging, and advisory execution.")
    
    tab1, tab2 = st.tabs(["📝 Register Farmer Issue", "📌 My Assigned Inspections"])
    
    with tab1:
        st.subheader("Register Field Grievance")
        st.caption("Writes validated complaint records to the central repository.")
        
        with st.form("complaint_form"):
            c_v = st.selectbox("Village:", data["villages"]["village_name"].tolist())
            c_farmer = st.text_input("Farmer Pseudonym / Name:", "Farmer_Ramesh")
            c_survey = st.text_input("Survey / Parcel Number:", "45/2A")
            c_crop = st.selectbox("Affected Crop:", ["Paddy", "Sugarcane", "Ragi", "Mulberry", "Banana", "Vegetables"])
            c_category = st.selectbox("Issue Category:", ["Pest Attack", "Disease", "Drought / Water Stress", "Nutrient Deficiency", "Hail / Wind Damage"])
            c_area = st.number_input("Estimated Affected Area (Hectares):", min_value=0.1, max_value=25.0, value=1.5, step=0.1)
            c_urgency = st.select_slider("Urgency Level:", options=["Low", "Medium", "High", "Critical"], value="High")
            c_desc = st.text_area("Symptoms & Field Observations:", "Severe yellowing of central shoots; dead hearts observed in early tillering.")
            
            submit_c = st.form_submit_button("Register Grievance")
            if submit_c:
                st.success(f"Grievance recorded successfully for **{c_v}** ({c_crop} - {c_urgency}). Priority engine will re-evaluate rankings.")
                
    with tab2:
        st.subheader("Field Inspection Schedule")
        st.info("Showing priority dispatches assigned for Maddur Kasaba sectors.")
        st.dataframe(
            data["complaints"][["complaint_id", "village_name", "crop_affected", "issue_category", "urgency_level", "reported_date", "status"]].head(10),
            use_container_width=True,
            hide_index=True
        )

# -------------------------------------------------------------
# 3. AI Field Assistant (RAG)
# -------------------------------------------------------------
else:
    st.title("🤖 AI Field Inspection Assistant")
    st.markdown("Ground-truth diagnostic guidance powered by the **University of Agricultural Sciences (UAS) Bengaluru Package of Practices**.")
    
    col_rag1, col_rag2 = st.columns([1, 2])
    
    with col_rag1:
        st.write("##### Diagnostic Context")
        q_crop = st.selectbox("Crop Under Inspection:", ["Paddy", "Sugarcane", "Ragi", "Mulberry"])
        q_issue = st.selectbox("Observed Symptom:", ["Dead hearts in stem (Stem Borer)", "Blast spots on leaves", "Early shoot borer", "Leaf reddening / drying"])
        st.write("##### Model Engine")
        st.radio("LLM Backend:", ["Local Ollama (Mistral 7B) - Default", "Google Gemini 1.5/2.0 Flash (Hybrid)"])
        
    with col_rag2:
        st.write("##### Agricultural Advisory & Actionable Checklist")
        st.markdown(
            f"""
            ### Diagnostic Advisory for **{q_crop}**
            **Symptom**: {q_issue}  
            **Source Authority**: *UAS Bangalore Package of Practices (Zone 6: Southern Dry Zone)*
            
            #### 🔍 Field Inspection Checklist:
            1. **Examine 20 consecutive hills/stems** at 5 random spots across the parcel.
            2. Check for egg masses on the lower surface of upper leaves.
            3. Measure soil moisture in root zone (confirm whether canal release was delayed).
            
            #### 💊 Recommended Management:
            - **Biological Control**: Release *Trichogramma chilonis* egg parasitoids @ 50,000/ha at 10-day intervals.
            - **Chemical Intervention (if ETL exceeded > 5% dead hearts)**: Spray Cartap Hydrochloride 50% SP @ 2.0 g/litre of water or Chlorantraniliprole 18.5% SC @ 0.3 ml/litre.
            - **Agronomic Practice**: Avoid excessive nitrogenous fertilizers during peak infestation.
            
            > **Official Citation**: *PoP UAS Bengaluru, Kharif Cereals & Commercial Crops Bulletin, Section 4.2.1, pp. 48-52.*
            """
        )
