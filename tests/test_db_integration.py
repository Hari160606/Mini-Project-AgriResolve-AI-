"""Integration tests for PostgreSQL / SQLite dashboard loading and persistence."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine

from db.load_data import (
    escalate_complaint_to_ao,
    fetch_dashboard_tables,
    load_all_data,
    save_farmer_complaint,
    save_inspection_dispatch,
    save_inspection_dispatches_batch,
    update_dispatch_status,
)


def test_load_fetch_and_persist_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "test_agriresolve.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    load_all_data(engine=engine)
    data, dialect = fetch_dashboard_tables(engine=engine)

    assert dialect == "custom"
    assert len(data["villages"]) == 7
    assert len(data["priorities"]) == 7
    assert len(data["factors"]) >= 21
    assert len(data["complaints"]) == 35

    ok_c, _ = save_farmer_complaint(
        {
            "complaint_id": "CMP_TEST_001",
            "village_id": "V_MDR_001",
            "village_name": "Maddur (Kasaba)",
            "farmer_pseudonym": "Farmer_Test",
            "survey_number": "12/1",
            "crop_affected": "Paddy",
            "issue_category": "Pest Attack",
            "issue_description": "Stem borer check",
            "affected_area_hectares": 1.2,
            "urgency_level": "High",
            "reported_date": "2026-11-27",
            "status": "Registered (DB)",
            "data_type": "Field Report",
            "is_synthetic": False,
        },
        engine=engine,
    )
    assert ok_c is True

    ok_e, _ = escalate_complaint_to_ao("CMP_TEST_001", "Smt. Bhavya K.M.", "Verified in field", engine=engine)
    assert ok_e is True

    ok_d, _ = save_inspection_dispatch(
        {
            "dispatch_id": "DSP_TEST_001",
            "village_id": "V_MDR_003",
            "village_name": "Kadalur",
            "assigned_officer": "Smt. Bhavya K.M.",
            "assigned_officer_id": "STF_002",
            "priority_rank": 1,
            "priority_score": 62.46,
            "severity_score": 81.33,
            "target_date": "2026-11-28",
            "instructions": "Inspect paddy plots",
            "status": "Assigned",
            "assigned_by": "STF_001",
            "created_at": "2026-11-27T16:45:00",
        },
        engine=engine,
    )
    assert ok_d is True

    ok_b, _ = save_inspection_dispatches_batch(
        [
            {
                "dispatch_id": "DSP_TEST_002",
                "village_id": "V_MDR_005",
                "village_name": "Hemmanahalli",
                "assigned_officer": "Shri Manjunath R.",
                "assigned_officer_id": "STF_003",
                "priority_rank": 2,
                "priority_score": 55.38,
                "severity_score": 86.19,
                "target_date": "2026-11-28",
                "instructions": "Inspect ragi plots",
                "status": "Assigned",
                "assigned_by": "STF_001",
                "created_at": "2026-11-27T16:46:00",
            }
        ],
        engine=engine,
    )
    assert ok_b is True

    ok_u, _ = update_dispatch_status("DSP_TEST_001", "Completed", engine=engine)
    assert ok_u is True

    updated, _ = fetch_dashboard_tables(engine=engine)
    row_c = updated["complaints"][updated["complaints"]["complaint_id"] == "CMP_TEST_001"].iloc[0]
    assert row_c["status"] == "Sent to AO"
    assert "Verified in field" in row_c["issue_description"]

    dispatches = updated["dispatches"]
    assert set(dispatches["dispatch_id"]) >= {"DSP_TEST_001", "DSP_TEST_002"}
    assert dispatches.loc[dispatches["dispatch_id"] == "DSP_TEST_001", "status"].iloc[0] == "Completed"
