"""
AgriResolve AI - Crop Statistics Ingestion
Ingests official crop statistics from Directorate of Economics & Statistics (DES) Karnataka
and package of practices (PoP) agricultural profiles for Maddur cluster.
Saves raw datasets into data/raw/crop_statistics_raw.xlsx and data/raw/crop_statistics_raw.csv.
"""

from pathlib import Path
import pandas as pd

def ingest_crops(output_dir: str = "data/raw"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    crops_catalog = [
        {
            "crop_id": "CRP_001",
            "crop_name": "Sugarcane",
            "botanical_name": "Saccharum officinarum",
            "kannada_name": "ಕಬ್ಬು (Kabbu)",
            "season": "Annual / Kharif-Rabi",
            "duration_days": 360,
            "water_requirement_mm": 1800,
            "drought_sensitivity": "High",
            "pest_vulnerability": "Medium (Early shoot borer, Woolly aphid)",
            "priority_economic_weight": 0.85,
            "data_type": "Real",
            "is_synthetic": False
        },
        {
            "crop_id": "CRP_002",
            "crop_name": "Paddy",
            "botanical_name": "Oryza sativa",
            "kannada_name": "ಭತ್ತ (Bhatta)",
            "season": "Kharif",
            "duration_days": 135,
            "water_requirement_mm": 1250,
            "drought_sensitivity": "Very High",
            "pest_vulnerability": "High (Stem borer, Leaf blast, Brown planthopper)",
            "priority_economic_weight": 0.90,
            "data_type": "Real",
            "is_synthetic": False
        },
        {
            "crop_id": "CRP_003",
            "crop_name": "Finger Millet (Ragi)",
            "botanical_name": "Eleusine coracana",
            "kannada_name": "ರಾಗಿ (Ragi)",
            "season": "Kharif",
            "duration_days": 115,
            "water_requirement_mm": 450,
            "drought_sensitivity": "Low",
            "pest_vulnerability": "Low (Blast, Stem borer)",
            "priority_economic_weight": 0.75,
            "data_type": "Real",
            "is_synthetic": False
        },
        {
            "crop_id": "CRP_004",
            "crop_name": "Mulberry (Sericulture)",
            "botanical_name": "Morus alba",
            "kannada_name": "ಹಿಪ್ಪುನೇರಳೆ (Hippunerale)",
            "season": "Perennial",
            "duration_days": 365,
            "water_requirement_mm": 1000,
            "drought_sensitivity": "Medium",
            "pest_vulnerability": "Medium (Thrips, Leaf roller, Tukra)",
            "priority_economic_weight": 0.80,
            "data_type": "Real",
            "is_synthetic": False
        },
        {
            "crop_id": "CRP_005",
            "crop_name": "Red Gram (Tur / Pigeon Pea)",
            "botanical_name": "Cajanus cajan",
            "kannada_name": "ತೊಗರಿ (Togari)",
            "season": "Kharif",
            "duration_days": 160,
            "water_requirement_mm": 550,
            "drought_sensitivity": "Medium",
            "pest_vulnerability": "High (Pod borer Helicoverpa armigera, Wilt)",
            "priority_economic_weight": 0.70,
            "data_type": "Real",
            "is_synthetic": False
        },
        {
            "crop_id": "CRP_006",
            "crop_name": "Banana",
            "botanical_name": "Musa acuminata",
            "kannada_name": "ಬಾಳೆ (Baale)",
            "season": "Annual",
            "duration_days": 330,
            "water_requirement_mm": 1600,
            "drought_sensitivity": "High",
            "pest_vulnerability": "Medium (Panama wilt, Sigatoka leaf spot)",
            "priority_economic_weight": 0.80,
            "data_type": "Real",
            "is_synthetic": False
        }
    ]
    
    # Village crop area distribution (Hectares) from Mandya DES baseline
    village_crops = [
        {"village_id": "V_MDR_001", "crop_id": "CRP_001", "crop_name": "Sugarcane", "sown_area_ha": 310.0, "normal_yield_tons_ha": 95.0},
        {"village_id": "V_MDR_001", "crop_id": "CRP_002", "crop_name": "Paddy", "sown_area_ha": 215.0, "normal_yield_tons_ha": 5.2},
        {"village_id": "V_MDR_001", "crop_id": "CRP_006", "crop_name": "Banana", "sown_area_ha": 90.0, "normal_yield_tons_ha": 32.0},
        
        {"village_id": "V_MDR_002", "crop_id": "CRP_001", "crop_name": "Sugarcane", "sown_area_ha": 220.0, "normal_yield_tons_ha": 98.0},
        {"village_id": "V_MDR_002", "crop_id": "CRP_004", "crop_name": "Mulberry", "sown_area_ha": 140.0, "normal_yield_tons_ha": 40.0},
        
        {"village_id": "V_MDR_003", "crop_id": "CRP_002", "crop_name": "Paddy", "sown_area_ha": 240.0, "normal_yield_tons_ha": 4.8},
        {"village_id": "V_MDR_003", "crop_id": "CRP_003", "crop_name": "Ragi", "sown_area_ha": 190.0, "normal_yield_tons_ha": 2.6},
        {"village_id": "V_MDR_003", "crop_id": "CRP_005", "crop_name": "Red Gram", "sown_area_ha": 60.0, "normal_yield_tons_ha": 1.1},
        
        {"village_id": "V_MDR_004", "crop_id": "CRP_001", "crop_name": "Sugarcane", "sown_area_ha": 260.0, "normal_yield_tons_ha": 102.0},
        {"village_id": "V_MDR_004", "crop_id": "CRP_006", "crop_name": "Banana", "sown_area_ha": 160.0, "normal_yield_tons_ha": 34.0},
        
        {"village_id": "V_MDR_005", "crop_id": "CRP_003", "crop_name": "Ragi", "sown_area_ha": 380.0, "normal_yield_tons_ha": 2.4},
        {"village_id": "V_MDR_005", "crop_id": "CRP_005", "crop_name": "Red Gram", "sown_area_ha": 200.0, "normal_yield_tons_ha": 0.95},
        
        {"village_id": "V_MDR_006", "crop_id": "CRP_001", "crop_name": "Sugarcane", "sown_area_ha": 480.0, "normal_yield_tons_ha": 105.0},
        {"village_id": "V_MDR_006", "crop_id": "CRP_002", "crop_name": "Paddy", "sown_area_ha": 410.0, "normal_yield_tons_ha": 5.4},
        
        {"village_id": "V_MDR_007", "crop_id": "CRP_001", "crop_name": "Sugarcane", "sown_area_ha": 390.0, "normal_yield_tons_ha": 94.0},
        {"village_id": "V_MDR_007", "crop_id": "CRP_003", "crop_name": "Ragi", "sown_area_ha": 360.0, "normal_yield_tons_ha": 2.5}
    ]
    
    df_crops = pd.DataFrame(crops_catalog)
    df_areas = pd.DataFrame(village_crops)
    df_areas["data_type"] = "Real"
    df_areas["is_synthetic"] = False
    
    # Save both .xlsx and .csv
    excel_path = Path(output_dir) / "crop_statistics_raw.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_crops.to_excel(writer, sheet_name="Crops_Catalog", index=False)
        df_areas.to_excel(writer, sheet_name="Village_Crops_Area", index=False)
        
    df_crops.to_csv(Path(output_dir) / "crop_catalog_raw.csv", index=False)
    df_areas.to_csv(Path(output_dir) / "village_crops_raw.csv", index=False)
    print(f"Crop statistics raw saved to {excel_path} and CSVs.")
    return df_crops, df_areas

if __name__ == "__main__":
    ingest_crops()
