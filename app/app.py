"""AgriResolve AI - Main Streamlit Application Entrypoint (Maddur Kasaba RSK).

Provides:
- Separate login pages for AO, AAO / Field Officer, and Farmer Voice Help
- AO Command Dashboard (Google Maps priority & distance map, AAO priority dispatch, AAO-escalated grievances)
- AAO / AA Field Workspace (priority-ordered assigned plan, Google Maps route directions ONLY to assigned places,
  receive & escalate farmer grievances to AO)
- Warm harvest-themed Farmer Voice Chatbot (Kannada + 6 languages, open-domain Gemini + RSK PoP + MP3 voice notes)
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = os.path.normcase(str(Path(__file__).resolve().parent))
_ROOT_NORM = os.path.normcase(str(PROJECT_ROOT))
# Streamlit prepends app/ to sys.path, which makes app/app.py shadow the `app` package.
sys.path[:] = [str(PROJECT_ROOT)] + [
    p for p in sys.path if os.path.normcase(os.path.abspath(p or ".")) not in {_APP_DIR, _ROOT_NORM}
]

load_dotenv(PROJECT_ROOT / ".env", override=False)

from app.auth import _extract_short_role, get_current_user, render_login_page, sign_out  # noqa: E402
from app.theme import inject_rsk_theme, render_gov_footer, render_gov_masthead, render_hero_banner  # noqa: E402
from app.voice_ui import render_farmer_voice_chatbot  # noqa: E402
from db.load_data import (  # noqa: E402
    escalate_complaint_to_ao,
    fetch_dashboard_tables,
    load_all_data as sync_db_tables,
    save_farmer_complaint,
    save_inspection_dispatch,
    save_inspection_dispatches_batch,
    update_dispatch_status,
)
from src.ingestion.ingest_ndvi import (  # noqa: E402
    DEFAULT_EE_PROJECT_ID,
    get_ee_ndvi_tile_url,
    get_latest_s2_window,
    ingest_ndvi,
    resolve_ee_project_id,
)
from src.monitoring.routine import run_routine_monitoring  # noqa: E402
from src.preprocessing.cleaning_and_derivation import clean_and_derive  # noqa: E402
from src.priority_engine.engine import run_priority_engine  # noqa: E402

user = get_current_user()
st.set_page_config(
    page_title="RSK AgriResolve Portal | Maddur Kasaba",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded" if user is not None else "collapsed",
)

_is_farmer_ui = (user is not None) and (
    user.role == "Farmer" or st.session_state.get("portal_nav") == "Farmer Voice Chatbot (Kannada)"
)
inject_rsk_theme(authenticated=(user is not None), farmer_mode=_is_farmer_ui)

_RSK_HUB_LAT = 12.5839
_RSK_HUB_LON = 77.0434


@st.cache_data(ttl=60)
def load_all_data() -> tuple[dict[str, pd.DataFrame], str]:
    return fetch_dashboard_tables()


@st.cache_data(ttl=1800, show_spinner=False)
def load_ee_ndvi_layer(project_id: str) -> tuple[dict[str, object] | None, str | None]:
    """Fetch and cache the live Google Earth Engine Sentinel-2 NDVI tile overlay."""
    try:
        return get_ee_ndvi_tile_url(project_id=project_id), None
    except Exception as exc:
        return None, str(exc)


_ACTIVE_EE_PROJECT = resolve_ee_project_id(use_default=True) or DEFAULT_EE_PROJECT_ID
data, data_source = load_all_data()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute straight-line geodesic distance in kilometres between two lat/lon points."""
    r_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r_km * math.asin(math.sqrt(a)), 2)


def _build_distance_matrix(map_df: pd.DataFrame) -> pd.DataFrame:
    """Build a symmetric village-to-village distance matrix (km)."""
    ordered = map_df.sort_values("rank_order").reset_index(drop=True)
    names = ordered["village_name"].tolist()
    coords = list(zip(ordered["latitude"].astype(float), ordered["longitude"].astype(float)))
    matrix = {
        name_b: [
            0.0 if i == j else _haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            for i in range(len(names))
        ]
        for j, name_b in enumerate(names)
    }
    df_mat = pd.DataFrame(matrix, index=names)
    df_mat.index.name = "From \\ To (km)"
    return df_mat


def _build_map_segments(map_df: pd.DataFrame, route_mode: str) -> list[dict[str, object]]:
    """Build line segments and midpoint distance labels for Priority Route or RSK Hub."""
    ordered = map_df.sort_values("rank_order").reset_index(drop=True)
    segments: list[dict[str, object]] = []

    if route_mode == "From RSK Hub (Maddur)":
        for row in ordered.itertuples():
            lat2, lon2 = float(row.latitude), float(row.longitude)
            dist_km = _haversine_km(_RSK_HUB_LAT, _RSK_HUB_LON, lat2, lon2)
            if dist_km < 0.05:
                continue
            segments.append(
                {
                    "from": "Maddur Kasaba RSK",
                    "to": str(row.village_name),
                    "lat1": _RSK_HUB_LAT,
                    "lon1": _RSK_HUB_LON,
                    "lat2": lat2,
                    "lon2": lon2,
                    "mid_lat": (_RSK_HUB_LAT + lat2) / 2.0,
                    "mid_lon": (_RSK_HUB_LON + lon2) / 2.0,
                    "distance_km": dist_km,
                    "label": f"{dist_km:.1f} km",
                }
            )
    else:
        rows = list(ordered.itertuples())
        for idx in range(len(rows) - 1):
            a, b = rows[idx], rows[idx + 1]
            lat1, lon1 = float(a.latitude), float(a.longitude)
            lat2, lon2 = float(b.latitude), float(b.longitude)
            dist_km = _haversine_km(lat1, lon1, lat2, lon2)
            segments.append(
                {
                    "from": f"#{int(a.rank_order)} {a.village_name}",
                    "to": f"#{int(b.rank_order)} {b.village_name}",
                    "lat1": lat1,
                    "lon1": lon1,
                    "lat2": lat2,
                    "lon2": lon2,
                    "mid_lat": (lat1 + lat2) / 2.0,
                    "mid_lon": (lon1 + lon2) / 2.0,
                    "distance_km": dist_km,
                    "label": f"{dist_km:.1f} km",
                }
            )
    return segments


def _render_google_map(
    api_key: str,
    map_df: pd.DataFrame,
    segments: list[dict[str, object]],
    ee_tile_url: str | None = None,
    height: int = 460,
) -> None:
    ordered = map_df.sort_values("rank_order").reset_index(drop=True)
    villages_payload = [
        {
            "lat": float(row.latitude),
            "lng": float(row.longitude),
            "title": str(row.village_name),
            "score": float(row.combined_priority_score),
            "rank": int(row.rank_order),
            "action": str(row.recommendation_action),
            "road_km": float(row.road_distance_km),
            "rsk_km": _haversine_km(_RSK_HUB_LAT, _RSK_HUB_LON, float(row.latitude), float(row.longitude)),
        }
        for row in ordered.itertuples()
    ]
    villages_json = json.dumps(villages_payload)
    segments_json = json.dumps(segments)
    ee_tile_json = json.dumps(ee_tile_url or "")

    html = f"""
    <div id="rsk-map" style="height:{height}px;width:100%;border-radius:12px;border:2px solid #2d6a4f;"></div>
    <script>
      function initMap() {{
        const map = new google.maps.Map(document.getElementById("rsk-map"), {{
          zoom: 12,
          center: {{lat: 12.585, lng: 77.043}},
          mapTypeId: "roadmap"
        }});
        const eeTileTemplate = {ee_tile_json};
        if (eeTileTemplate) {{
          const eeLayer = new google.maps.ImageMapType({{
            getTileUrl: function(coord, zoom) {{
              return eeTileTemplate
                .replace("{{z}}", zoom)
                .replace("{{x}}", coord.x)
                .replace("{{y}}", coord.y);
            }},
            tileSize: new google.maps.Size(256, 256),
            opacity: 0.62,
            name: "Sentinel-2 NDVI"
          }});
          map.overlayMapTypes.insertAt(0, eeLayer);
        }}
        const info = new google.maps.InfoWindow();
        const bounds = new google.maps.LatLngBounds();
        const villages = {villages_json};
        const segments = {segments_json};

        new google.maps.Marker({{
          position: {{lat: {_RSK_HUB_LAT}, lng: {_RSK_HUB_LON}}},
          map: map,
          title: "Maddur Kasaba RSK Hub",
          icon: {{
            path: google.maps.SymbolPath.CIRCLE,
            scale: 9,
            fillColor: "#d4a738",
            fillOpacity: 1,
            strokeColor: "#102e21",
            strokeWeight: 2
          }}
        }});

        segments.forEach(s => {{
          new google.maps.Polyline({{
            path: [{{lat: s.lat1, lng: s.lon1}}, {{lat: s.lat2, lng: s.lon2}}],
            geodesic: true,
            strokeColor: "#1b4332",
            strokeOpacity: 0.78,
            strokeWeight: 3,
            map: map
          }});
          new google.maps.Marker({{
            position: {{lat: s.mid_lat, lng: s.mid_lon}},
            map: map,
            icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 0}},
            label: {{
              text: s.label,
              color: "#102e21",
              fontSize: "11px",
              fontWeight: "700"
            }}
          }});
        }});

        villages.forEach(v => {{
          const pos = {{lat: v.lat, lng: v.lng}};
          bounds.extend(pos);
          const color = v.rank <= 2 ? "#c62828" : (v.rank <= 4 ? "#e07a16" : "#2d6a4f");
          const marker = new google.maps.Marker({{
            position: pos,
            map: map,
            title: v.title,
            label: {{text: String(v.rank), color: "#ffffff", fontWeight: "700"}},
            icon: {{
              path: google.maps.SymbolPath.CIRCLE,
              scale: 13,
              fillColor: color,
              fillOpacity: 0.95,
              strokeColor: "#ffffff",
              strokeWeight: 2
            }}
          }});
          marker.addListener("click", () => {{
            info.setContent(
              `<div style="font-family:sans-serif;padding:4px;min-width:190px;">
                 <strong>#${{v.rank}} ${{v.title}}</strong><br/>
                 Priority Score: <b>${{v.score}}</b><br/>
                 From RSK Hub: <b>${{v.rsk_km}} km</b> (Road: ${{v.road_km}} km)<br/>
                 Action: ${{v.action}}
               </div>`
            );
            info.open(map, marker);
          }});
        }});
        map.fitBounds(bounds, 45);
      }}
    </script>
    <script async src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap"></script>
    """
    st.iframe(html, height=height + 16, alt="Interactive village priority and inter-location distance map")


def render_village_map(
    map_df: pd.DataFrame,
    route_mode: str,
    ee_tile_url: str | None = None,
) -> go.Figure | None:
    """Render Google Maps JS when GOOGLE_MAPS_API_KEY is set, otherwise Plotly OpenStreetMap with distances."""
    segments = _build_map_segments(map_df, route_mode)
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if maps_key:
        _render_google_map(maps_key, map_df, segments, ee_tile_url=ee_tile_url)
        return None

    ordered = map_df.sort_values("rank_order").reset_index(drop=True)
    if hasattr(px, "scatter_map"):
        fig = px.scatter_map(
            ordered,
            lat="latitude",
            lon="longitude",
            hover_name="village_name",
            hover_data={
                "combined_priority_score": True,
                "rank_order": True,
                "road_distance_km": True,
                "recommendation_action": True,
                "latitude": False,
                "longitude": False,
            },
            color="combined_priority_score",
            size="combined_priority_score",
            color_continuous_scale="Reds",
            size_max=22,
            zoom=11.1,
            center={"lat": 12.585, "lon": 77.043},
            map_style="open-street-map",
        )
        for seg in segments:
            fig.add_trace(
                go.Scattermap(
                    lat=[seg["lat1"], seg["lat2"]],
                    lon=[seg["lon1"], seg["lon2"]],
                    mode="lines",
                    line={"width": 2.5, "color": "#1b4332"},
                    hoverinfo="text",
                    text=f"{seg['from']} → {seg['to']}: {seg['label']}",
                    showlegend=False,
                )
            )
        if segments:
            fig.add_trace(
                go.Scattermap(
                    lat=[s["mid_lat"] for s in segments],
                    lon=[s["mid_lon"] for s in segments],
                    mode="text",
                    text=[s["label"] for s in segments],
                    textfont={"size": 11, "color": "#102e21"},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
    else:
        fig = px.scatter(
            ordered,
            x="longitude",
            y="latitude",
            text="village_name",
            color="combined_priority_score",
            size="combined_priority_score",
            color_continuous_scale="Reds",
            title="Village Coordinates & Priority Scores",
        )
    fig.update_layout(height=470, margin={"r": 0, "t": 12, "l": 0, "b": 0})
    if ee_tile_url and hasattr(px, "scatter_map"):
        fig.update_layout(
            map_layers=[{"sourcetype": "raster", "source": [ee_tile_url], "opacity": 0.62, "below": "traces"}]
        )
    return fig


def _google_maps_directions_url(assigned_df: pd.DataFrame) -> str:
    """Build a direct Google Maps turn-by-turn directions URL for the assigned priority stops."""
    stops = [f"{float(r.latitude)},{float(r.longitude)}" for r in assigned_df.itertuples()]
    params: dict[str, str] = {
        "api": "1",
        "origin": f"{_RSK_HUB_LAT},{_RSK_HUB_LON}",
        "destination": stops[-1],
        "travelmode": "driving",
    }
    if len(stops) > 1:
        params["waypoints"] = "|".join(stops[:-1])
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def _render_aao_directions_map(
    assigned_df: pd.DataFrame,
    ee_tile_url: str | None = None,
    height: int = 440,
) -> None:
    """Render Google Maps route directions ONLY to AO-assigned villages in priority order."""
    stops_payload = [
        {
            "lat": float(r.latitude),
            "lng": float(r.longitude),
            "title": str(r.village_name),
            "rank": int(r.priority_rank) if pd.notna(r.priority_rank) else (idx + 1),
            "order": idx + 1,
            "severity": round(float(r.severity_score), 1) if pd.notna(r.severity_score) else 0.0,
            "priority_score": round(float(r.priority_score), 1) if pd.notna(r.priority_score) else 0.0,
            "status": str(r.status or "Assigned"),
            "road_km": float(r.road_distance_km) if pd.notna(r.road_distance_km) else 0.0,
        }
        for idx, r in enumerate(assigned_df.itertuples())
    ]

    maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if maps_key:
        stops_json = json.dumps(stops_payload)
        ee_tile_json = json.dumps(ee_tile_url or "")
        html = f"""
        <div id="aao-route-map" style="height:{height}px;width:100%;border-radius:12px;border:2px solid #1b4332;"></div>
        <div id="aao-route-status" style="font-family:sans-serif;font-size:12px;color:#365243;margin-top:6px;"></div>
        <script>
          function initAaoMap() {{
            const origin = {{lat: {_RSK_HUB_LAT}, lng: {_RSK_HUB_LON}}};
            const stops = {stops_json};
            const map = new google.maps.Map(document.getElementById("aao-route-map"), {{
              zoom: 12,
              center: origin,
              mapTypeId: "roadmap"
            }});
            const eeTileTemplate = {ee_tile_json};
            if (eeTileTemplate) {{
              const eeLayer = new google.maps.ImageMapType({{
                getTileUrl: function(coord, zoom) {{
                  return eeTileTemplate
                    .replace("{{z}}", zoom)
                    .replace("{{x}}", coord.x)
                    .replace("{{y}}", coord.y);
                }},
                tileSize: new google.maps.Size(256, 256),
                opacity: 0.60,
                name: "Sentinel-2 NDVI"
              }});
              map.overlayMapTypes.insertAt(0, eeLayer);
            }}
            const info = new google.maps.InfoWindow();
            const statusEl = document.getElementById("aao-route-status");

            function drawFallbackRoute(note) {{
              const bounds = new google.maps.LatLngBounds();
              bounds.extend(origin);
              new google.maps.Marker({{
                position: origin,
                map: map,
                title: "Maddur Kasaba RSK (Start)",
                label: {{text: "RSK", color: "#102e21", fontSize: "10px", fontWeight: "700"}},
                icon: {{
                  path: google.maps.SymbolPath.CIRCLE,
                  scale: 13,
                  fillColor: "#d4a738",
                  fillOpacity: 1,
                  strokeColor: "#102e21",
                  strokeWeight: 2
                }}
              }});

              const pathCoords = [origin];
              stops.forEach(s => {{
                const p = {{lat: s.lat, lng: s.lng}};
                pathCoords.push(p);
                bounds.extend(p);
                const m = new google.maps.Marker({{
                  position: p,
                  map: map,
                  title: s.title,
                  label: {{text: String(s.order), color: "#ffffff", fontWeight: "700"}},
                  icon: {{
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 13,
                    fillColor: s.status === "Completed" ? "#2d6a4f" : "#c62828",
                    fillOpacity: 0.95,
                    strokeColor: "#ffffff",
                    strokeWeight: 2
                  }}
                }});
                m.addListener("click", () => {{
                  info.setContent(
                    `<div style="font-family:sans-serif;padding:4px;">
                       <strong>Stop #${{s.order}} (Priority #${{s.rank}}): ${{s.title}}</strong><br/>
                       Severity: <b>${{s.severity}}</b> | Priority: <b>${{s.priority_score}}</b><br/>
                       Status: ${{s.status}} | Road Dist: ${{s.road_km}} km
                     </div>`
                  );
                  info.open(map, m);
                }});
              }});

              new google.maps.Polyline({{
                path: pathCoords,
                geodesic: true,
                strokeColor: "#1b4332",
                strokeOpacity: 0.85,
                strokeWeight: 3.5,
                map: map
              }});
              map.fitBounds(bounds, 45);
              if (note) statusEl.textContent = note;
            }}

            if (stops.length === 0) return;

            const ds = new google.maps.DirectionsService();
            const dr = new google.maps.DirectionsRenderer({{
              map: map,
              suppressMarkers: false,
              polylineOptions: {{strokeColor: "#1b4332", strokeWeight: 4}}
            }});
            const destination = {{lat: stops[stops.length - 1].lat, lng: stops[stops.length - 1].lng}};
            const waypoints = stops.slice(0, -1).map(s => ({{
              location: {{lat: s.lat, lng: s.lng}},
              stopover: true
            }}));

            ds.route({{
              origin: origin,
              destination: destination,
              waypoints: waypoints,
              optimizeWaypoints: false,
              travelMode: google.maps.TravelMode.DRIVING
            }}, (result, status) => {{
              if (status === "OK") {{
                dr.setDirections(result);
                const legs = result.routes[0].legs || [];
                const totalKm = (legs.reduce((acc, l) => acc + l.distance.value, 0) / 1000).toFixed(1);
                const totalMin = Math.round(legs.reduce((acc, l) => acc + l.duration.value, 0) / 60);
                statusEl.textContent = `Turn-by-turn priority route ready: ${{stops.length}} assigned stop(s) · ${{totalKm}} km · ~${{totalMin}} mins driving`;
              }} else {{
                drawFallbackRoute("Showing priority-ordered route line (open Turn-by-Turn link below for full road navigation).");
              }}
            }});
          }}
        </script>
        <script async src="https://maps.googleapis.com/maps/api/js?key={maps_key}&callback=initAaoMap"></script>
        """
        st.iframe(html, height=height + 42, alt="AAO Google Maps directions to assigned priority villages")
        return

    # Plotly fallback restricted strictly to RSK Hub + AO-assigned priority stops
    fig = go.Figure()
    lats = [_RSK_HUB_LAT] + [float(r.latitude) for r in assigned_df.itertuples()]
    lons = [_RSK_HUB_LON] + [float(r.longitude) for r in assigned_df.itertuples()]
    labels = ["RSK Hub"] + [f"#{i + 1} {r.village_name}" for i, r in enumerate(assigned_df.itertuples())]

    if hasattr(go, "Scattermap"):
        fig.add_trace(
            go.Scattermap(
                lat=lats,
                lon=lons,
                mode="lines+markers+text",
                line={"width": 3, "color": "#1b4332"},
                marker={"size": 13, "color": ["#d4a738"] + ["#c62828"] * len(assigned_df)},
                text=labels,
                textposition="top center",
            )
        )
        fig.update_layout(
            map={"style": "open-street-map", "center": {"lat": 12.585, "lon": 77.043}, "zoom": 11.2},
            height=height,
            margin={"r": 0, "t": 8, "l": 0, "b": 0},
        )
    else:
        fig.add_trace(go.Scatter(x=lons, y=lats, mode="lines+markers+text", text=labels))
        fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch")


# -------------------------------------------------------------
# Unauthenticated Entry: Show Login Page Only (No Sidebar)
# -------------------------------------------------------------
role_badge = f"{user.name} ({user.role})" if user else None
render_gov_masthead(role_badge=role_badge)

if user is None:
    render_login_page(data["staff"], data["villages"])
    st.stop()


# -------------------------------------------------------------
# Authenticated Sidebar (Clean, Minimal, High-Contrast)
# -------------------------------------------------------------
st.sidebar.markdown(
    """
    <div style="padding:4px 4px 12px 4px;border-bottom:1px solid rgba(255,255,255,0.18);margin-bottom:12px;">
      <div style="font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#f3d778;font-weight:700;">
        Dept. of Agriculture
      </div>
      <div style="font-size:18px;font-weight:800;color:#ffffff;margin-top:2px;">🌾 RSK AgriResolve</div>
      <div style="font-size:12px;color:#d6e6da;">Maddur Kasaba RSK (KA_MDR_01)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

sub_info = f"Role: <strong>{user.role}</strong>"
if user.staff_id:
    sub_info += f" · {user.staff_id}"
elif user.village_name:
    sub_info += f" · {user.village_name}"

st.sidebar.markdown(
    f"""
    <div style="background:rgba(255,255,255,0.10);border:1px solid rgba(212,167,56,0.50);
                border-radius:10px;padding:10px 12px;margin-bottom:14px;">
      <div style="font-size:11px;color:#f3d778;font-weight:700;text-transform:uppercase;">Signed In</div>
      <div style="font-size:15px;font-weight:700;color:#ffffff;margin-top:2px;">{user.name}</div>
      <div style="font-size:12px;color:#dcebe0;margin-top:2px;">{sub_info}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if user.role == "AO":
    nav_options = [
        "Command Dashboard (AO)",
        "Farmer Voice Chatbot (Kannada)",
    ]
elif user.role in {"AAO", "AA"}:
    nav_options = [
        "Field Workspace (AAO / AA)",
        "Farmer Voice Chatbot (Kannada)",
    ]
else:
    nav_options = ["Farmer Voice Chatbot (Kannada)"]

selected_view = st.sidebar.radio("Navigation", nav_options, key="portal_nav")

st.sidebar.space("small")
if st.sidebar.button("Sign out", icon=":material/logout:", width="stretch"):
    sign_out()
    st.session_state.pop("portal_nav", None)
    st.rerun()

st.sidebar.caption(f"Data store: `{data_source.upper()}`")


# Merge DB + session records
all_complaints = data["complaints"].copy()
extra_complaints = st.session_state.get("session_complaints", [])
if extra_complaints:
    all_complaints = pd.concat([all_complaints, pd.DataFrame(extra_complaints)], ignore_index=True)

escalated_overrides = st.session_state.get("session_escalated_ids", {})
if escalated_overrides and not all_complaints.empty:
    for cid, note in escalated_overrides.items():
        mask = all_complaints["complaint_id"] == cid
        all_complaints.loc[mask, "status"] = "Sent to AO"

all_dispatches = data.get("dispatches", pd.DataFrame()).copy()
session_dispatches = st.session_state.get("session_dispatches", [])
if session_dispatches:
    all_dispatches = pd.concat([all_dispatches, pd.DataFrame(session_dispatches)], ignore_index=True)
status_overrides = st.session_state.get("session_dispatch_status", {})
if status_overrides and not all_dispatches.empty:
    for did, new_st in status_overrides.items():
        all_dispatches.loc[all_dispatches["dispatch_id"] == did, "status"] = new_st


# -------------------------------------------------------------
# Views
# -------------------------------------------------------------
if selected_view == "Command Dashboard (AO)":
    render_hero_banner(
        tag="🌾 AO Command Centre · Maddur Kasaba RSK (KA_MDR_01)",
        title="Village Risk Intelligence & AAO Inspection Dispatch",
        subtitle="Prioritise 7 Mandya villages by severity & satellite risk, assign AAOs in priority order, and review escalated grievances.",
    )
    st.title("🌾 Agriculture Officer (AO) Inspection Command")

    escalated_df = all_complaints[all_complaints["status"].astype(str).str.contains("Sent to AO", case=False, na=False)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monitored Villages", len(data["villages"]), "7 Revenue Villages")
    tier1_count = len(data["priorities"][data["priorities"]["recommendation_action"].str.contains("Tier 1")])
    c2.metric("Tier-1 Immediate Dispatches", tier1_count, "Urgent Priority")
    c3.metric("Grievances Sent by AAO", len(escalated_df), f"{len(all_complaints)} Total")
    c4.metric("Active AO Dispatches", len(all_dispatches), "Assigned to Field")

    st.subheader(":material/map: Spatial Priority Map & Inter-Location Distances")
    map_ctrl1, map_ctrl2 = st.columns([3, 2], vertical_alignment="center")
    route_mode = (
        map_ctrl1.segmented_control(
            "Map distance overlay",
            ["Priority Route (Rank #1 → #7)", "From RSK Hub (Maddur)"],
            default="Priority Route (Rank #1 → #7)",
            key="map_route_mode",
            label_visibility="collapsed",
        )
        or "Priority Route (Rank #1 → #7)"
    )
    ee_overlay_on = map_ctrl2.toggle(
        "🛰️ Live Earth Engine Sentinel-2 NDVI Overlay",
        value=True,
        key="ao_ee_overlay",
    )

    ee_layer_info, ee_layer_err = load_ee_ndvi_layer(_ACTIVE_EE_PROJECT) if ee_overlay_on else (None, None)
    ee_tile_url = str(ee_layer_info["tile_url"]) if (ee_overlay_on and ee_layer_info) else None

    map_df = data["villages"].merge(
        data["priorities"][["village_id", "combined_priority_score", "rank_order", "recommendation_action", "road_distance_km"]],
        on="village_id",
    )
    fig_map = render_village_map(map_df, route_mode, ee_tile_url=ee_tile_url)
    if fig_map is not None:
        st.plotly_chart(fig_map, width="stretch")

    if ee_overlay_on and ee_layer_info:
        st.caption(
            f"🛰️ Live Earth Engine NDVI (`{_ACTIVE_EE_PROJECT}`) · "
            f"{ee_layer_info['image_count']} Sentinel-2 L2A scenes ({ee_layer_info['start_date']} to {ee_layer_info['end_date']}) · "
            "Scale: 🔴 0.10 (Stressed/Bare) → 🟡 0.45 → 🟢 0.85 (Dense Healthy Crop)"
        )
    elif ee_overlay_on and ee_layer_err:
        st.caption(f"Earth Engine tile overlay unavailable offline ({ee_layer_err}). Showing village priority map.")

    with st.expander("Inter-location distance matrix (km)", expanded=False):
        st.caption("Straight-line geodesic distances (km) between each village in the Maddur Kasaba RSK cluster.")
        st.dataframe(_build_distance_matrix(map_df), width="stretch")

    st.subheader("📋 Explainable AI Village Priority Ranking")
    cols_to_show = [
        "rank_order",
        "village_name",
        "combined_priority_score",
        "reported_severity_score",
        "recommendation_action",
        "human_explanation",
        "road_distance_km",
    ]
    st.dataframe(
        data["priorities"][cols_to_show].rename(
            columns={
                "rank_order": "Priority Rank",
                "village_name": "Village",
                "combined_priority_score": "Priority Score",
                "reported_severity_score": "Severity Score",
                "recommendation_action": "Recommendation",
                "human_explanation": "Decision Justification",
                "road_distance_km": "RSK Distance (km)",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("📊 Transparent Factor Breakdown")
    selected_village = st.selectbox(
        "Select Village for Deep Factor Inspection:", data["priorities"]["village_name"].tolist()
    )
    village_factors = data["factors"][data["factors"]["village_name"] == selected_village]
    fig_bar = px.bar(
        village_factors,
        x="factor",
        y="contribution_pts",
        color="factor",
        text="contribution_pts",
        title=f"Factor Contributions to Priority Score for {selected_village}",
        labels={"contribution_pts": "Points Contributed", "factor": "Factor"},
    )
    fig_bar.update_layout(height=340, showlegend=False, template="plotly_white")
    st.plotly_chart(fig_bar, width="stretch")

    st.subheader("🛰️ Google Earth Engine — Sentinel-2 NDVI Intelligence")
    ndvi_df = data["ndvi"].copy()
    latest_ndvi_df = ndvi_df.sort_values("observation_date").groupby("village_id").last().reset_index()
    min_ndvi_row = latest_ndvi_df.loc[latest_ndvi_df["mean_ndvi"].idxmin()]

    with st.container(border=True):
        ee_c1, ee_c2, ee_c3, ee_c4 = st.columns(4)
        ee_c1.metric("Earth Engine Project", _ACTIVE_EE_PROJECT, "COPERNICUS/S2_SR_HARMONIZED")
        ee_c2.metric("Latest Cluster Avg NDVI", f"{latest_ndvi_df['mean_ndvi'].mean():.3f}", "10m Sentinel-2 MSI")
        ee_c3.metric("Lowest Village NDVI", f"{min_ndvi_row['mean_ndvi']:.3f}", str(min_ndvi_row["village_name"]))
        ee_c4.metric("NDVI Observations", len(ndvi_df), f"{ndvi_df['observation_date'].nunique()} Composite Dates")

        sync_col1, sync_col2 = st.columns([2.2, 1.8], vertical_alignment="bottom")
        ndvi_window = sync_col1.selectbox(
            "Satellite composite window:",
            ["Latest Available 120 Days (Live)", "Kharif 2024 Season (2024-06-05 to 2024-11-20)"],
            key="ee_sync_window",
        )
        if sync_col2.button(
            "Sync Live Sentinel-2 NDVI & Refresh Priorities",
            icon=":material/satellite_alt:",
            type="primary",
            width="stretch",
        ):
            with st.spinner(f"Fetching Sentinel-2 L2A NDVI from Google Earth Engine ({_ACTIVE_EE_PROJECT})..."):
                try:
                    if ndvi_window.startswith("Latest"):
                        s_date, e_date = get_latest_s2_window(_ACTIVE_EE_PROJECT, lookback_days=120)
                    else:
                        s_date, e_date = "2024-06-05", "2024-11-20"
                    ingest_ndvi(
                        use_ee=True,
                        project_id=_ACTIVE_EE_PROJECT,
                        fallback_to_offline=False,
                        start_date=s_date,
                        end_date=e_date,
                    )
                    clean_and_derive()
                    run_routine_monitoring()
                    run_priority_engine()
                    sync_db_tables()
                    load_all_data.clear()
                    load_ee_ndvi_layer.clear()
                    st.success(f"Synced live Sentinel-2 NDVI ({s_date} to {e_date}) and updated priorities!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Earth Engine sync failed: {exc}")

        fig_ndvi = px.line(
            ndvi_df.sort_values("observation_date"),
            x="observation_date",
            y="mean_ndvi",
            color="village_name",
            markers=True,
            title="Sentinel-2 NDVI Vegetation Trend Across Maddur RSK Villages",
            labels={"observation_date": "Observation Date", "mean_ndvi": "Mean NDVI", "village_name": "Village"},
        )
        fig_ndvi.add_hline(y=0.35, line_dash="dash", line_color="#c62828", annotation_text="Vegetation Stress Threshold (0.35)")
        fig_ndvi.update_layout(height=340, template="plotly_white", yaxis_range=[0.05, 0.95])
        st.plotly_chart(fig_ndvi, width="stretch")

    st.subheader("👷 Assign AAOs by Priority Order")
    field_staff = data["staff"][data["staff"]["role"].apply(_extract_short_role).isin({"AAO", "AA"})].reset_index(drop=True)
    if field_staff.empty:
        field_staff = data["staff"].copy()

    # Compute live assigned counts per officer
    active_counts = (
        all_dispatches[all_dispatches["status"] != "Completed"].groupby("assigned_officer").size().to_dict()
        if not all_dispatches.empty
        else {}
    )
    staff_view = field_staff[["staff_id", "name", "role", "jurisdiction", "status"]].copy()
    staff_view["ao_assigned_villages"] = staff_view["name"].map(lambda n: int(active_counts.get(n, 0)))

    ordered_priorities = data["priorities"].sort_values("rank_order").reset_index(drop=True)
    col_alloc1, col_alloc2 = st.columns([1, 1], gap="large")

    with col_alloc1:
        st.write("##### Available Field Officers (AAO / AA)")
        st.dataframe(staff_view, width="stretch", hide_index=True)

        st.write("##### Auto-Assign Unassigned Villages by Priority")
        already_assigned_villages = (
            set(all_dispatches[all_dispatches["status"] != "Completed"]["village_name"].astype(str))
            if not all_dispatches.empty
            else set()
        )
        unassigned_rows = ordered_priorities[~ordered_priorities["village_name"].isin(already_assigned_villages)]
        st.caption(f"{len(unassigned_rows)} of {len(ordered_priorities)} villages currently unassigned.")
        auto_date = st.date_input("Batch target date:", key="auto_assign_date")
        if st.button(
            "Auto-Assign Priority Villages to AAOs",
            icon=":material/auto_fix_high:",
            width="stretch",
            disabled=unassigned_rows.empty,
        ):
            aao_pool = field_staff[field_staff["role"].apply(_extract_short_role) == "AAO"]
            if aao_pool.empty:
                aao_pool = field_staff
            batch_records = []
            now_tag = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
            now_iso = pd.Timestamp.now().isoformat(timespec="seconds")
            for i, p_row in enumerate(unassigned_rows.itertuples()):
                officer = aao_pool.iloc[i % len(aao_pool)]
                batch_records.append(
                    {
                        "dispatch_id": f"DSP_{now_tag}_{i + 1:02d}",
                        "village_id": str(p_row.village_id),
                        "village_name": str(p_row.village_name),
                        "assigned_officer": str(officer["name"]),
                        "assigned_officer_id": str(officer["staff_id"]),
                        "priority_rank": int(p_row.rank_order),
                        "priority_score": float(p_row.combined_priority_score),
                        "severity_score": float(p_row.reported_severity_score),
                        "target_date": str(auto_date),
                        "instructions": f"Priority #{int(p_row.rank_order)} inspection: {p_row.human_explanation}",
                        "status": "Assigned",
                        "assigned_by": user.staff_id or user.name,
                        "created_at": now_iso,
                    }
                )
            saved_db, backend = save_inspection_dispatches_batch(batch_records)
            if saved_db:
                load_all_data.clear()
                st.success(f"Auto-assigned {len(batch_records)} priority villages to AAOs ({backend.upper()})!")
            else:
                st.session_state.setdefault("session_dispatches", []).extend(batch_records)
                st.success(f"Auto-assigned {len(batch_records)} priority villages to AAOs (session)!")
            st.rerun()

    with col_alloc2:
        st.write("##### Assign Single Village by Priority (AO Action)")
        priority_labels = {
            row.village_name: (
                f"#{int(row.rank_order)} {row.village_name} "
                f"(Priority {row.combined_priority_score:.1f} · Severity {row.reported_severity_score:.1f})"
            )
            for row in ordered_priorities.itertuples()
        }
        with st.form("assign_form"):
            target_v = st.selectbox(
                "Target Village (sorted by priority):",
                ordered_priorities["village_name"].tolist(),
                format_func=lambda v: priority_labels.get(v, v),
            )
            officer_choices = (field_staff["staff_id"] + " · " + field_staff["name"] + " (" + field_staff["role"] + ")").tolist()
            chosen_officer_label = st.selectbox("Assign To Officer (AAO / AA):", officer_choices)
            insp_date = st.date_input("Inspection Target Date:")
            instructions = st.text_area(
                "Inspection Plan & Special Instructions:",
                "Verify crop stress & active farmer grievances; collect soil moisture & pest ETL readings.",
            )
            submit_assign = st.form_submit_button("Approve & Assign AAO", type="primary", width="stretch")
            if submit_assign:
                chosen_id = chosen_officer_label.split(" · ")[0]
                off_row = field_staff[field_staff["staff_id"] == chosen_id].iloc[0]
                p_row = ordered_priorities[ordered_priorities["village_name"] == target_v].iloc[0]
                dispatch_rec = {
                    "dispatch_id": f"DSP_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}",
                    "village_id": str(p_row["village_id"]),
                    "village_name": target_v,
                    "assigned_officer": str(off_row["name"]),
                    "assigned_officer_id": str(off_row["staff_id"]),
                    "priority_rank": int(p_row["rank_order"]),
                    "priority_score": float(p_row["combined_priority_score"]),
                    "severity_score": float(p_row["reported_severity_score"]),
                    "target_date": str(insp_date),
                    "instructions": instructions,
                    "status": "Assigned",
                    "assigned_by": user.staff_id or user.name,
                    "created_at": pd.Timestamp.now().isoformat(timespec="seconds"),
                }
                saved_db, backend = save_inspection_dispatch(dispatch_rec)
                if saved_db:
                    load_all_data.clear()
                    st.success(
                        f"Assigned **#{int(p_row['rank_order'])} {target_v}** to **{off_row['name']}** on {insp_date} "
                        f"(saved to `{backend.upper()}`)!"
                    )
                else:
                    st.session_state.setdefault("session_dispatches", []).append(dispatch_rec)
                    st.success(f"Assigned **#{int(p_row['rank_order'])} {target_v}** to **{off_row['name']}** (session)!")

    if not all_dispatches.empty:
        st.write("##### Active AO → AAO Assignment Plan")
        disp_cols = [c for c in ["priority_rank", "village_name", "severity_score", "priority_score", "assigned_officer", "target_date", "status"] if c in all_dispatches.columns]
        st.dataframe(
            all_dispatches[disp_cols].sort_values(["priority_rank", "severity_score"], ascending=[True, False]),
            width="stretch",
            hide_index=True,
        )

    st.subheader("📩 Farmer Grievances Received from AAOs")
    if escalated_df.empty:
        st.caption("No new grievances escalated by AAOs yet. Grievances forwarded from AAO Field Workspace will appear here.")
    else:
        st.dataframe(
            escalated_df[
                ["complaint_id", "village_name", "crop_affected", "issue_category", "urgency_level", "issue_description", "reported_date", "status"]
            ],
            width="stretch",
            hide_index=True,
        )

elif selected_view == "Field Workspace (AAO / AA)":
    render_hero_banner(
        tag=f"🚜 Field Officer Workspace · {user.role}",
        title=f"Welcome, {user.name}",
        subtitle="Inspect villages strictly in AO priority & severity order, follow Google Maps route directions, and send farmer grievances to the AO.",
    )
    st.title("🚜 AAO / AA Field Inspection Plan & Grievance Desk")

    # Enrich dispatches with village coords, priority, severity, and road distance
    enriched_dispatches = all_dispatches.copy()
    if not enriched_dispatches.empty:
        enriched_dispatches = enriched_dispatches.merge(
            data["villages"][["village_name", "latitude", "longitude", "soil_type", "primary_irrigation_source", "major_crops"]],
            on="village_name",
            how="left",
        ).merge(
            data["priorities"][
                ["village_name", "rank_order", "combined_priority_score", "reported_severity_score", "routine_risk_score", "road_distance_km", "est_travel_time_mins", "human_explanation", "recommendation_action"]
            ],
            on="village_name",
            how="left",
        )
        enriched_dispatches["priority_rank"] = enriched_dispatches["priority_rank"].fillna(enriched_dispatches["rank_order"])
        enriched_dispatches["priority_score"] = enriched_dispatches["priority_score"].fillna(enriched_dispatches["combined_priority_score"])
        enriched_dispatches["severity_score"] = enriched_dispatches["severity_score"].fillna(enriched_dispatches["reported_severity_score"])
        enriched_dispatches = enriched_dispatches.sort_values(
            ["priority_rank", "severity_score"], ascending=[True, False]
        ).reset_index(drop=True)

    tab1, tab2 = st.tabs(["🗺️ Assigned Priority Plan & Route Directions", "📩 Farmer Grievances → Send to AO"])

    with tab1:
        scope = (
            st.segmented_control(
                "Dispatch scope",
                ["Assigned to Me", "All AO Dispatches"],
                default="Assigned to Me",
                key="aao_dispatch_scope",
                label_visibility="collapsed",
            )
            or "Assigned to Me"
        )

        if enriched_dispatches.empty:
            my_plan = enriched_dispatches
        elif scope == "Assigned to Me":
            mask = (enriched_dispatches["assigned_officer"] == user.name) | (
                enriched_dispatches.get("assigned_officer_id", pd.Series("", index=enriched_dispatches.index)) == (user.staff_id or "")
            )
            my_plan = enriched_dispatches[mask].reset_index(drop=True)
        else:
            my_plan = enriched_dispatches

        if my_plan.empty:
            st.info(
                "No villages have been assigned to you by the Agriculture Officer (AO) yet. "
                "Once the AO assigns villages in priority order on the Command Dashboard, your inspection plan and route directions will appear here."
            )
        else:
            pending_cnt = int((my_plan["status"] != "Completed").sum())
            completed_cnt = int((my_plan["status"] == "Completed").sum())
            top_row = my_plan.iloc[0]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Assigned Villages", len(my_plan), f"{pending_cnt} Pending")
            m2.metric("First Priority Stop", str(top_row["village_name"]), f"Rank #{int(top_row['priority_rank'])}")
            m3.metric("Top Severity Score", f"{float(top_row['severity_score']):.1f}", "Highest Assigned")
            m4.metric("Completed Visits", completed_cnt, f"of {len(my_plan)} Assigned")

            st.subheader(":material/directions: Google Maps Directions (Assigned Priority Order Only)")
            aao_ee_overlay = st.toggle(
                "🛰️ Overlay Live Earth Engine Sentinel-2 NDVI",
                value=True,
                key="aao_ee_overlay",
            )
            aao_ee_info, _ = load_ee_ndvi_layer(_ACTIVE_EE_PROJECT) if aao_ee_overlay else (None, None)
            aao_ee_tile = str(aao_ee_info["tile_url"]) if (aao_ee_overlay and aao_ee_info) else None
            active_stops = my_plan[my_plan["status"] != "Completed"]
            route_stops = active_stops if not active_stops.empty else my_plan
            _render_aao_directions_map(route_stops, ee_tile_url=aao_ee_tile)
            st.link_button(
                "Open Turn-by-Turn Route in Google Maps",
                _google_maps_directions_url(route_stops),
                icon=":material/navigation:",
                type="primary",
            )

            st.subheader(":material/checklist: Complete Village Inspection Plan (Sorted by Priority & Severity)")
            summary_cols = [
                "priority_rank",
                "village_name",
                "severity_score",
                "priority_score",
                "road_distance_km",
                "est_travel_time_mins",
                "target_date",
                "status",
            ]
            st.dataframe(
                my_plan[summary_cols].rename(
                    columns={
                        "priority_rank": "Priority #",
                        "village_name": "Village",
                        "severity_score": "Severity Score",
                        "priority_score": "Priority Score",
                        "road_distance_km": "Distance (km)",
                        "est_travel_time_mins": "Travel (mins)",
                        "target_date": "Target Date",
                        "status": "Status",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

            latest_ndvi_map = (
                data["ndvi"].sort_values("observation_date").groupby("village_name")["mean_ndvi"].last().to_dict()
                if not data["ndvi"].empty
                else {}
            )
            for idx, row in enumerate(my_plan.itertuples(), start=1):
                v_name = str(row.village_name)
                v_factors = data["factors"][data["factors"]["village_name"] == v_name]
                v_complaints = all_complaints[all_complaints["village_name"] == v_name]
                v_ndvi = latest_ndvi_map.get(v_name)
                ndvi_text = f"{v_ndvi:.3f}" if v_ndvi is not None else "N/A"
                with st.container(border=True):
                    h1, h2 = st.columns([4, 1.5], vertical_alignment="center")
                    h1.markdown(
                        f"#### Stop #{idx} · {v_name} "
                        f"(`Priority #{int(row.priority_rank)}` · `Severity {float(row.severity_score):.1f}` · `Score {float(row.priority_score):.1f}`)"
                    )
                    h2.markdown(f"**Status:** `{row.status}`")
                    st.markdown(
                        f"- **AO Instructions:** {row.instructions or 'Conduct standard crop-health & grievance verification.'}\n"
                        f"- **Justification:** {row.human_explanation}\n"
                        f"- **Village Profile:** Crops: *{row.major_crops}* | Soil: *{row.soil_type}* | Latest Sentinel-2 NDVI: **{ndvi_text}**\n"
                        f"- **Logistics:** {row.road_distance_km} km from RSK (~{int(row.est_travel_time_mins)} mins) | Target Date: **{row.target_date}** | Active Complaints: **{len(v_complaints)}**"
                    )
                    if not v_factors.empty:
                        factor_summary = " · ".join(
                            f"{f.factor}: {f.contribution_pts:.1f} pts" for f in v_factors.itertuples()
                        )
                        st.caption(f"Score breakdown: {factor_summary}")

                    b1, b2, _ = st.columns([1.4, 1.5, 3])
                    if b1.button("Start Inspection", key=f"start_{row.dispatch_id}", disabled=(row.status != "Assigned")):
                        ok, _ = update_dispatch_status(str(row.dispatch_id), "In Progress")
                        if ok:
                            load_all_data.clear()
                        else:
                            st.session_state.setdefault("session_dispatch_status", {})[str(row.dispatch_id)] = "In Progress"
                        st.rerun()
                    if b2.button("Mark Completed", type="primary", key=f"done_{row.dispatch_id}", disabled=(row.status == "Completed")):
                        ok, _ = update_dispatch_status(str(row.dispatch_id), "Completed")
                        if ok:
                            load_all_data.clear()
                        else:
                            st.session_state.setdefault("session_dispatch_status", {})[str(row.dispatch_id)] = "Completed"
                        st.rerun()

    with tab2:
        st.subheader("Receive Farmer Grievances & Send to AO")
        col_g1, col_g2 = st.columns([1, 1], gap="large")

        with col_g1:
            st.markdown("##### 1. Escalate Incoming Farmer Grievance to AO")
            pending_grievances = all_complaints[
                ~all_complaints["status"].astype(str).str.contains("Sent to AO", case=False, na=False)
            ].sort_values("reported_date", ascending=False)

            if pending_grievances.empty:
                st.success("All recorded farmer grievances have already been sent to the AO.")
            else:
                with st.form("escalate_grievance_form"):
                    g_options = (
                        pending_grievances["complaint_id"]
                        + " · "
                        + pending_grievances["village_name"]
                        + " ("
                        + pending_grievances["crop_affected"]
                        + " - "
                        + pending_grievances["urgency_level"]
                        + ")"
                    ).tolist()
                    chosen_g = st.selectbox("Select farmer grievance:", g_options)
                    aao_note = st.text_area(
                        "AAO Field Verification Note:",
                        "Verified farmer grievance; recommending AO review and priority inspection.",
                    )
                    send_btn = st.form_submit_button("Send Grievance to AO", type="primary", width="stretch")
                    if send_btn:
                        cid = chosen_g.split(" · ")[0]
                        ok, backend = escalate_complaint_to_ao(cid, user.name, aao_note)
                        if ok:
                            load_all_data.clear()
                            st.success(f"Grievance `{cid}` sent to AO (saved to `{backend.upper()}`).")
                        else:
                            st.session_state.setdefault("session_escalated_ids", {})[cid] = aao_note
                            st.success(f"Grievance `{cid}` marked as Sent to AO (session).")
                        st.rerun()

        with col_g2:
            st.markdown("##### 2. Register New Farmer Grievance & Send to AO")
            with st.form("complaint_form"):
                c_v = st.selectbox("Village:", data["villages"]["village_name"].tolist())
                c_farmer = st.text_input("Farmer Name / Pseudonym:", "Farmer_Ramesh")
                c_survey = st.text_input("Survey / Parcel Number:", "45/2A")
                c_crop = st.selectbox("Affected Crop:", ["Paddy", "Sugarcane", "Ragi", "Mulberry", "Banana", "Vegetables"])
                c_category = st.selectbox(
                    "Issue Category:",
                    ["Pest Attack", "Disease", "Drought / Water Stress", "Nutrient Deficiency", "Hail / Wind Damage"],
                )
                c_area = st.number_input("Affected Area (Hectares):", min_value=0.1, max_value=25.0, value=1.5, step=0.1)
                c_urgency = st.select_slider("Urgency Level:", options=["Low", "Medium", "High", "Critical"], value="High")
                c_desc = st.text_area(
                    "Symptoms & Farmer Report:",
                    "Severe yellowing of central shoots; dead hearts observed in early tillering.",
                )
                send_to_ao_now = st.checkbox("Send directly to Agriculture Officer (AO)", value=True)
                submit_c = st.form_submit_button("Submit & Send to AO", type="primary", width="stretch")
                if submit_c:
                    new_id = f"CMP_NEW_{len(all_complaints) + 1:03d}"
                    v_match = data["villages"].loc[data["villages"]["village_name"] == c_v, "village_id"]
                    village_id = str(v_match.iloc[0]) if not v_match.empty else "V_MDR_001"
                    status_val = "Sent to AO" if send_to_ao_now else "Registered (DB)"
                    complaint_rec = {
                        "complaint_id": new_id,
                        "village_id": village_id,
                        "village_name": c_v,
                        "farmer_pseudonym": c_farmer.strip() or "Farmer_Guest",
                        "survey_number": c_survey.strip() or "N/A",
                        "crop_affected": c_crop,
                        "issue_category": c_category,
                        "issue_description": f"{c_desc.strip()} [Recorded by AAO {user.name}]",
                        "affected_area_hectares": float(c_area),
                        "urgency_level": c_urgency,
                        "reported_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        "status": status_val,
                        "data_type": "Field Report",
                        "is_synthetic": False,
                    }
                    saved_db, backend = save_farmer_complaint(complaint_rec)
                    if saved_db:
                        load_all_data.clear()
                        st.success(f"Grievance `{new_id}` saved and `{status_val}` in `{backend.upper()}`.")
                    else:
                        st.session_state.setdefault("session_complaints", []).append(complaint_rec)
                        st.success(f"Grievance `{new_id}` recorded as `{status_val}` (session).")
                    st.rerun()

        sent_to_ao_df = all_complaints[all_complaints["status"].astype(str).str.contains("Sent to AO", case=False, na=False)]
        st.markdown("##### Sent to AO Log")
        if sent_to_ao_df.empty:
            st.caption("No grievances marked 'Sent to AO' yet.")
        else:
            st.dataframe(
                sent_to_ao_df[
                    ["complaint_id", "village_name", "crop_affected", "issue_category", "urgency_level", "reported_date", "status"]
                ],
                width="stretch",
                hide_index=True,
            )

else:
    render_farmer_voice_chatbot(data["villages"], user=user)

render_gov_footer()
