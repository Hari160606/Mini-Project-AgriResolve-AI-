"""Unit tests for Google Earth Engine initialization and NDVI ingestion fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion import ingest_ndvi as ndvi_mod


def test_resolve_ee_project_id_reads_env_and_ignores_placeholders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EE_PROJECT_ID", "your_gee_project_id_here")
    monkeypatch.setenv("GEE_PROJECT_ID", "demo-ee-project-123")
    assert ndvi_mod.resolve_ee_project_id() == "demo-ee-project-123"
    assert ndvi_mod.resolve_ee_project_id("custom-proj-123") == "custom-proj-123"


def test_initialize_earth_engine_passes_project_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EE_PROJECT_ID", "demo-ee-project-123")
    monkeypatch.delenv("EE_SERVICE_ACCOUNT_EMAIL", raising=False)
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT", raising=False)
    monkeypatch.delenv("EE_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("GEE_PRIVATE_KEY_PATH", raising=False)

    mock_ee = MagicMock()
    with patch.dict("sys.modules", {"ee": mock_ee}):
        project = ndvi_mod.initialize_earth_engine()

    assert project == "demo-ee-project-123"
    mock_ee.Initialize.assert_called_once_with(project="demo-ee-project-123")


def test_ingest_ndvi_falls_back_to_offline_when_ee_fails(tmp_path: Path) -> None:
    with patch.object(ndvi_mod, "fetch_sentinel2_ndvi_ee", side_effect=RuntimeError("no auth")):
        df = ndvi_mod.ingest_ndvi(
            output_dir=str(tmp_path),
            use_ee=True,
            project_id="demo-ee-project-123",
            fallback_to_offline=True,
        )

    assert len(df) == 84
    assert (tmp_path / "ndvi_raw.xlsx").is_file()
    assert (tmp_path / "ndvi_raw.csv").is_file()
    assert set(df["village_id"].unique()) == {f"V_MDR_00{i}" for i in range(1, 8)}
