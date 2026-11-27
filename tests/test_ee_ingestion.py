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


def test_default_ee_project_id_and_tile_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)
    assert ndvi_mod.resolve_ee_project_id(use_default=True) == "gmp-demo-project-960615751"

    mock_ee = MagicMock()
    mock_col = MagicMock()
    mock_col.size.return_value.getInfo.return_value = 12
    mock_composite = mock_col.map.return_value.median.return_value.clip.return_value
    mock_composite.getMapId.return_value = {
        "tile_fetcher": MagicMock(url_format="https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}")
    }
    mock_ee.ImageCollection.return_value.filterBounds.return_value.filterDate.return_value.filter.return_value = mock_col

    with patch.dict("sys.modules", {"ee": mock_ee}):
        res = ndvi_mod.get_ee_ndvi_tile_url(start_date="2024-06-05", end_date="2024-11-20")

    assert res["project"] == "gmp-demo-project-960615751"
    assert res["image_count"] == 12
    assert "{z}/{x}/{y}" in res["tile_url"]
