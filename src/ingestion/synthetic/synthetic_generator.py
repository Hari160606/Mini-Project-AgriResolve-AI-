"""
AgriResolve AI - Seeded Synthetic Data Generator
Generates realistic, statistically consistent synthetic administrative datasets:
1. Farmer Complaints (with crop-specific pests, dry spell issues, affected area)
2. Historical Inspection Logs (past 180 days)
3. Staff Directory & Workload (AO, AAO, AA)
4. Village Accessibility & RSK Transit Distances

Every single generated record includes:
  `is_synthetic = True`
  `data_type = 'Synthetic'`
"""

import os
from pathlib import Path
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def generate_synthetic_data(output_dir: str = "data/synthetic", seed: int = 42):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    np.random.seed(seed)
    
    villages = [
        ("V_MDR_001", "Maddur (Kasaba)", ["Sugarcane", "Paddy", "Vegetables"]),
        ("V_MDR_002", "Shivapura", ["Sugarcane", "Mulberry"]),
        ("V_MDR_003", "Kadalur", ["Paddy", "Ragi", "Red Gram"]),
        ("V_MDR_004", "Alur", ["Sugarcane", "Banana", "Paddy"]),
        ("V_MDR_005", "Hemmanahalli", ["Ragi", "Red Gram"]),
        ("V_MDR_006", "Chikkarasinakere", ["Paddy", "Sugarcane", "Vegetables"]),
        ("V_MDR_007", "Besagarahalli", ["Sugarcane", "Ragi"])
    ]
    
    issue_catalog = {
        "Sugarcane": [
            ("Pest Attack", "Early shoot borer infestation in young ratoon canes", "High"),
            ("Pest Attack", "Woolly aphid cluster spread across leaf under-surface", "Medium"),
            ("Disease", "Red rot fungal discoloration observed near lower nodes", "High"),
            ("Water Stress", "Tail-end canal water shortage causing leaf drying", "Medium")
        ],
        "Paddy": [
            ("Pest Attack", "Yellow stem borer causing dead heart symptoms in vegetative stage", "High"),
            ("Disease", "Blast lesions on upper leaves following high humidity", "High"),
            ("Pest Attack", "Brown plant hopper (BPH) lodging patches in basin", "Critical"),
            ("Nutrient Deficiency", "Zinc deficiency induced chlorosis in flooded parcels", "Low")
        ],
        "Ragi": [
            ("Drought Stress", "Prolonged dry spell causing wilting and delayed tillering", "High"),
            ("Disease", "Finger blast symptoms on emerging ear heads", "Medium"),
            ("Pest Attack", "Armyworm larval leaf feeding observed after monsoon break", "Medium")
        ],
        "Mulberry": [
            ("Pest Attack", "Thrips and leaf roller damaging leaf yield for silkworms", "Medium"),
            ("Disease", "Tukra (mealybug induced curling) affecting shoot tips", "Medium")
        ],
        "Red Gram": [
            ("Pest Attack", "Pod borer (Helicoverpa armigera) damaging green pods", "High"),
            ("Disease", "Fusarium wilt causing sudden vascular drying", "High")
        ],
        "Banana": [
            ("Disease", "Sigatoka leaf spot spreading after intermittent showers", "Medium"),
            ("Wind / Hail Damage", "Pseudostem breakage due to high gusting convective winds", "High")
        ],
        "Vegetables": [
            ("Pest Attack", "Whitefly and fruit borer damage in tomato and brinjal", "High"),
            ("Disease", "Damping off and powdery mildew in seedling nurseries", "Medium")
        ]
    }
    
    # -------------------------------------------------------------
    # 1. Farmer Complaints Generation (Past 60 days, e.g. Sept 15 - Nov 20, 2024)
    # -------------------------------------------------------------
    complaints = []
    start_date = datetime(2024, 9, 15)
    
    complaint_counter = 1
    # Distribute complaints realistically:
    # Kadalur (V_MDR_003) and Hemmanahalli (V_MDR_005) experience higher cluster frequency due to rainfall stress
    for v_id, v_name, crops in villages:
        num_complaints = 8 if v_id in ["V_MDR_003", "V_MDR_005"] else (5 if v_id in ["V_MDR_006", "V_MDR_001"] else 3)
        
        for _ in range(num_complaints):
            c_date = start_date + timedelta(days=random.randint(0, 65))
            crop = random.choice(crops)
            issue_type, description, default_urgency = random.choice(issue_catalog.get(crop, issue_catalog["Sugarcane"]))
            
            # Area affected: 0.5 to 4.5 hectares
            area_ha = round(random.uniform(0.5, 4.2), 2)
            
            # Urgency weighting
            urgency = default_urgency
            if random.random() < 0.15:
                urgency = "Critical"
                
            complaints.append({
                "complaint_id": f"CMP_2024_{complaint_counter:04d}",
                "village_id": v_id,
                "village_name": v_name,
                "farmer_pseudonym": f"Farmer_{random.randint(100, 999)}",
                "survey_number": f"{random.randint(12, 185)}/{random.choice(['1', '2', 'A', 'B'])}",
                "crop_affected": crop,
                "issue_category": issue_type,
                "issue_description": description,
                "affected_area_hectares": area_ha,
                "urgency_level": urgency,
                "reported_date": c_date.strftime("%Y-%m-%d"),
                "status": random.choice(["Open", "Under Review", "Pending Inspection"]),
                "data_type": "Synthetic",
                "is_synthetic": True
            })
            complaint_counter += 1
            
    df_complaints = pd.DataFrame(complaints).sort_values("reported_date").reset_index(drop=True)
    
    # -------------------------------------------------------------
    # 2. Staff Directory & Workload
    # -------------------------------------------------------------
    staff_members = [
        {
            "staff_id": "STF_001",
            "name": "Dr. Ramesh Gowda",
            "role": "AO (Agriculture Officer)",
            "designation": "Head of RSK, Maddur",
            "jurisdiction": "Maddur Kasaba RSK Hub",
            "phone_masked": "+91 94808 XXXXX",
            "status": "Active / In Office",
            "active_inspections_count": 2,
            "max_weekly_capacity": 6,
            "data_type": "Synthetic",
            "is_synthetic": True
        },
        {
            "staff_id": "STF_002",
            "name": "Smt. Bhavya K.M.",
            "role": "AAO (Assistant Agriculture Officer)",
            "designation": "Field Officer Sector 1",
            "jurisdiction": "Kadalur, Hemmanahalli, Maddur Rural",
            "phone_masked": "+91 94808 XXXXX",
            "status": "Available for Dispatch",
            "active_inspections_count": 3,
            "max_weekly_capacity": 8,
            "data_type": "Synthetic",
            "is_synthetic": True
        },
        {
            "staff_id": "STF_003",
            "name": "Shri Manjunath C.",
            "role": "AAO (Assistant Agriculture Officer)",
            "designation": "Field Officer Sector 2",
            "jurisdiction": "Shivapura, Alur, Chikkarasinakere, Besagarahalli",
            "phone_masked": "+91 94808 XXXXX",
            "status": "On Field Duty",
            "active_inspections_count": 4,
            "max_weekly_capacity": 8,
            "data_type": "Synthetic",
            "is_synthetic": True
        },
        {
            "staff_id": "STF_004",
            "name": "Kumari Anitha S.",
            "role": "AA (Agricultural Assistant)",
            "designation": "Technical Field Assistant",
            "jurisdiction": "General Field Inspection & Soil Sampling",
            "phone_masked": "+91 94808 XXXXX",
            "status": "Available for Dispatch",
            "active_inspections_count": 1,
            "max_weekly_capacity": 10,
            "data_type": "Synthetic",
            "is_synthetic": True
        }
    ]
    df_staff = pd.DataFrame(staff_members)
    
    # -------------------------------------------------------------
    # 3. Previous Inspections History (Past 180 days)
    # -------------------------------------------------------------
    inspections = []
    insp_date_base = datetime(2024, 5, 1)
    
    # Simulate past inspections: Besagarahalli and Alur were inspected recently,
    # while Kadalur and Hemmanahalli haven't been visited in 50+ days (inspection gap!)
    inspection_specs = [
        ("V_MDR_001", 15, "STF_002", "Routine pest surveillance in sugarcane", "Recommended tricho-cards for borer", "Resolved"),
        ("V_MDR_002", 35, "STF_003", "Sericulture mulberry health audit", "Advised neem-oil spray against thrips", "Resolved"),
        ("V_MDR_003", 68, "STF_002", "Paddy early nursery check", "Minor blast observed, fungicide suggested", "Follow-up Overdue"),
        ("V_MDR_004", 12, "STF_003", "Banana pseudostem post-storm assessment", "Estimated loss in 1.2 ha", "Report Submitted"),
        ("V_MDR_005", 85, "STF_002", "Pre-sowing ragi seed distribution verification", "Normal germination confirmed", "Resolved"),
        ("V_MDR_006", 24, "STF_003", "Canal distributary tail-end inspection", "Water release coordinated with AEE Cauvery", "Resolved"),
        ("V_MDR_007", 8, "STF_004", "Sugarcane rust check", "No pathogenic spread found", "Resolved")
    ]
    
    for i, (v_id, days_ago, stf, notes, action, status) in enumerate(inspection_specs, start=1):
        v_name = [v[1] for v in villages if v[0] == v_id][0]
        i_date = datetime(2024, 11, 20) - timedelta(days=days_ago)
        inspections.append({
            "inspection_id": f"INSP_2024_{i:03d}",
            "village_id": v_id,
            "village_name": v_name,
            "inspection_date": i_date.strftime("%Y-%m-%d"),
            "days_since_last_inspection": days_ago,
            "inspecting_officer_id": stf,
            "field_observations": notes,
            "advisory_issued": action,
            "resolution_status": status,
            "data_type": "Synthetic",
            "is_synthetic": True
        })
        
    df_inspections = pd.DataFrame(inspections)
    
    # -------------------------------------------------------------
    # 4. Village Accessibility & RSK Transit Baseline
    # -------------------------------------------------------------
    # Road distances and average transit times from Maddur Kasaba RSK HQ
    accessibility = [
        {"village_id": "V_MDR_001", "village_name": "Maddur (Kasaba)", "road_distance_km": 1.8, "est_travel_time_mins": 6, "road_condition": "Paved Highway (NH-275)", "accessibility_tier": "Very Easy"},
        {"village_id": "V_MDR_002", "village_name": "Shivapura", "road_distance_km": 2.4, "est_travel_time_mins": 8, "road_condition": "Paved Taluk Road", "accessibility_tier": "Very Easy"},
        {"village_id": "V_MDR_003", "village_name": "Kadalur", "road_distance_km": 8.5, "est_travel_time_mins": 22, "road_condition": "Intermediate Rural Road", "accessibility_tier": "Moderate"},
        {"village_id": "V_MDR_004", "village_name": "Alur", "road_distance_km": 5.2, "est_travel_time_mins": 14, "road_condition": "Paved Village Road", "accessibility_tier": "Easy"},
        {"village_id": "V_MDR_005", "village_name": "Hemmanahalli", "road_distance_km": 9.8, "est_travel_time_mins": 26, "road_condition": "Narrow Gravel / Metalled Road", "accessibility_tier": "Moderate"},
        {"village_id": "V_MDR_006", "village_name": "Chikkarasinakere", "road_distance_km": 12.6, "est_travel_time_mins": 30, "road_condition": "Major District Road (MDR)", "accessibility_tier": "Moderate"},
        {"village_id": "V_MDR_007", "village_name": "Besagarahalli", "road_distance_km": 11.2, "est_travel_time_mins": 28, "road_condition": "Paved MDR", "accessibility_tier": "Moderate"}
    ]
    df_access = pd.DataFrame(accessibility)
    df_access["data_type"] = "Synthetic"
    df_access["is_synthetic"] = True
    
    # -------------------------------------------------------------
    # Save Datasets to both Excel (.xlsx) and CSV
    # -------------------------------------------------------------
    excel_path = Path(output_dir) / "synthetic_datasets.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_complaints.to_excel(writer, sheet_name="Farmer_Complaints", index=False)
        df_staff.to_excel(writer, sheet_name="Staff_Roster", index=False)
        df_inspections.to_excel(writer, sheet_name="Inspections_History", index=False)
        df_access.to_excel(writer, sheet_name="Village_Accessibility", index=False)
        
    df_complaints.to_excel(Path(output_dir) / "farmer_complaints.xlsx", index=False, engine="openpyxl")
    df_complaints.to_csv(Path(output_dir) / "farmer_complaints.csv", index=False)
    
    df_staff.to_excel(Path(output_dir) / "staff_roster.xlsx", index=False, engine="openpyxl")
    df_staff.to_csv(Path(output_dir) / "staff_roster.csv", index=False)
    
    df_inspections.to_excel(Path(output_dir) / "inspections_history.xlsx", index=False, engine="openpyxl")
    df_inspections.to_csv(Path(output_dir) / "inspections_history.csv", index=False)
    
    df_access.to_excel(Path(output_dir) / "village_accessibility.xlsx", index=False, engine="openpyxl")
    df_access.to_csv(Path(output_dir) / "village_accessibility.csv", index=False)
    
    print(f"Generated synthetic datasets in {output_dir}:")
    print(f"  - farmer_complaints.xlsx ({len(df_complaints)} rows)")
    print(f"  - staff_roster.xlsx ({len(df_staff)} rows)")
    print(f"  - inspections_history.xlsx ({len(df_inspections)} rows)")
    print(f"  - village_accessibility.xlsx ({len(df_access)} rows)")
    return df_complaints, df_staff, df_inspections, df_access

if __name__ == "__main__":
    generate_synthetic_data()
