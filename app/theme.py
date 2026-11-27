"""Government RSK visual theme, including distinct Farmer Voice Portal warm theme."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSETS_DIR: Path = Path(__file__).resolve().parent / "assets"


@lru_cache(maxsize=4)
def _image_data_uri(filename: str) -> str | None:
    """Load a local image from ``app/assets`` as a base64 data URI."""
    path = ASSETS_DIR / filename
    if not path.exists():
        return None
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{encoded}"


def inject_rsk_theme(authenticated: bool = False, farmer_mode: bool = False) -> None:
    """Apply the RSK portal theme; use warm harvest theme for Farmer Voice Chatbot."""
    if farmer_mode:
        bg_layer = (
            "background: radial-gradient(circle at top right, #fff8e7 0%, #faf4e4 45%, #eef4ea 100%);"
        )
    else:
        bg_uri = _image_data_uri("rsk_farmland_bg.jpg") or _image_data_uri("rsk_farmland_bg.png")
        if bg_uri:
            bg_layer = (
                f'background-image: linear-gradient(180deg, rgba(244, 248, 242, 0.88) 0%, '
                f'rgba(239, 245, 236, 0.92) 100%), url("{bg_uri}");'
                "background-size: cover; background-position: center; background-attachment: fixed;"
            )
        else:
            bg_layer = "background: linear-gradient(180deg, #eff6ec 0%, #f7faf5 50%, #e7f1e4 100%);"

    if not authenticated:
        sidebar_css = """
            section[data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            .main .block-container {
                max-width: 860px;
                padding-top: 1.5rem;
                padding-bottom: 2.5rem;
            }
        """
    else:
        max_w = "1040px" if farmer_mode else "1280px"
        sidebar_bg = (
            "linear-gradient(180deg, #1b3a24 0%, #244e30 60%, #2b5c39 100%)"
            if farmer_mode
            else "linear-gradient(180deg, #102e21 0%, #163d2c 60%, #1c4c37 100%)"
        )
        sidebar_css = f"""
            .main .block-container {{
                max-width: {max_w};
                padding-top: 1.15rem;
                padding-bottom: 2.5rem;
            }}
            section[data-testid="stSidebar"] {{
                background: {sidebar_bg} !important;
                border-right: 2px solid #c89d28;
            }}
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
                padding-top: 0.5rem;
            }}
            section[data-testid="stSidebar"] .stMarkdown p,
            section[data-testid="stSidebar"] .stMarkdown span,
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
                color: #eef5ef !important;
            }}
            section[data-testid="stSidebar"] div[role="radiogroup"] label {{
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px 10px;
                margin-bottom: 4px;
            }}
            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
                background: rgba(212, 167, 56, 0.22);
                border-color: #d4a738;
            }}
            section[data-testid="stSidebar"] button {{
                background: rgba(255, 255, 255, 0.12) !important;
                border: 1px solid rgba(255, 255, 255, 0.28) !important;
                color: #ffffff !important;
                border-radius: 8px !important;
            }}
            section[data-testid="stSidebar"] button:hover {{
                background: #d4a738 !important;
                border-color: #d4a738 !important;
                color: #102e21 !important;
            }}
        """

    masthead_bg = (
        "linear-gradient(135deg, #1b4332 0%, #2d6a4f 55%, #b45309 125%)"
        if farmer_mode
        else "linear-gradient(135deg, #133827 0%, #1d5038 65%, #266447 100%)"
    )

    st.markdown(
        f"""
        <style>
        .stApp {{
            {bg_layer}
        }}
        {sidebar_css}

        /* Official Government Masthead */
        .rsk-tricolor {{
            height: 4px;
            width: 100%;
            border-radius: 6px 6px 0 0;
            background: linear-gradient(90deg, #ff9933 0%, #ff9933 33.3%, #ffffff 33.3%, #ffffff 66.6%, #138808 66.6%, #138808 100%);
        }}
        .rsk-masthead {{
            background: {masthead_bg};
            color: #ffffff;
            padding: 14px 20px;
            border-radius: 0 0 12px 12px;
            border-bottom: 3px solid #c89d28;
            box-shadow: 0 6px 18px rgba(16, 46, 33, 0.14);
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 1rem;
        }}
        .rsk-masthead-left {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .rsk-emblem {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.12);
            border: 2px solid #e6b83a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }}
        .rsk-dept-kicker {{
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #f3d778;
            font-weight: 700;
            margin-bottom: 2px;
        }}
        .rsk-portal-title {{
            font-size: 19px;
            font-weight: 800;
            line-height: 1.2;
            color: #ffffff;
            margin: 0;
        }}
        .rsk-portal-sub {{
            font-size: 12.5px;
            color: #dcebe0;
            margin-top: 2px;
        }}
        .rsk-badge {{
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(230, 184, 58, 0.55);
            color: #ffffff;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
        }}

        /* Photographic RSK Hero Banner */
        .rsk-hero {{
            position: relative;
            border-radius: 14px;
            overflow: hidden;
            padding: 22px 26px;
            margin-bottom: 1.1rem;
            color: #ffffff;
            border: 1px solid rgba(27, 67, 50, 0.22);
            box-shadow: 0 6px 20px rgba(16, 46, 33, 0.12);
        }}
        .rsk-hero-tag {{
            display: inline-block;
            background: rgba(200, 157, 40, 0.94);
            color: #102e21;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 999px;
            margin-bottom: 8px;
        }}
        .rsk-hero h2 {{
            margin: 0 0 6px 0;
            font-size: 23px;
            font-weight: 800;
            color: #ffffff;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
        }}
        .rsk-hero p {{
            margin: 0;
            font-size: 14px;
            color: #eef6ef;
            max-width: 780px;
            line-height: 1.5;
        }}

        /* Farmer Voice Portal Dedicated Hero */
        .farmer-hero {{
            background: linear-gradient(125deg, #164e2e 0%, #1e6b3f 55%, #b45309 130%);
            border-radius: 16px;
            padding: 22px 26px;
            color: #ffffff;
            border-bottom: 4px solid #f59e0b;
            box-shadow: 0 8px 24px rgba(22, 78, 46, 0.16);
            margin-bottom: 1rem;
        }}
        .farmer-hero-kicker {{
            display: inline-block;
            background: #fef3c7;
            color: #92400e;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 999px;
            margin-bottom: 8px;
        }}
        .farmer-hero h2 {{
            margin: 0 0 6px 0;
            font-size: 22px;
            font-weight: 800;
            color: #ffffff;
        }}
        .farmer-hero p {{
            margin: 0;
            font-size: 14px;
            color: #fefce8;
            line-height: 1.5;
        }}

        /* Elevated KPI Cards & Containers */
        [data-testid="stMetric"] {{
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid #d5e3d2;
            border-left: 5px solid #2d6a4f;
            border-radius: 12px;
            padding: 14px 16px;
            box-shadow: 0 3px 10px rgba(20, 54, 40, 0.06);
        }}
        [data-testid="stMetricLabel"] {{
            font-weight: 600;
            color: #365243 !important;
        }}
        [data-testid="stMetricValue"] {{
            color: #133827 !important;
            font-weight: 800 !important;
        }}
        [data-testid="stForm"],
        [data-testid="stExpander"] {{
            background: rgba(255, 255, 255, 0.97);
            border: 1px solid #d5e3d2;
            border-radius: 12px;
            box-shadow: 0 3px 12px rgba(20, 54, 40, 0.05);
        }}
        [data-testid="stForm"] {{
            padding: 18px 20px;
        }}
        [data-testid="stDataFrame"] {{
            background: rgba(255, 255, 255, 0.97);
            border-radius: 10px;
            border: 1px solid #d5e3d2;
            padding: 4px;
        }}
        .rsk-login-header {{
            background: rgba(255, 255, 255, 0.97);
            border: 1px solid #d5e3d2;
            border-top: 4px solid #1b4332;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 14px rgba(16, 46, 33, 0.07);
        }}
        .rsk-login-header h3 {{
            margin: 0 0 4px 0;
            color: #133827;
            font-size: 18px;
            font-weight: 800;
        }}
        .rsk-login-header p {{
            margin: 0;
            color: #415a4c;
            font-size: 13.5px;
        }}
        .rsk-footer {{
            margin-top: 2rem;
            padding: 10px 16px;
            border-radius: 10px;
            background: rgba(19, 56, 39, 0.92);
            color: #dcebe0;
            font-size: 12px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 8px;
            border-top: 2px solid #c89d28;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_gov_masthead(
    rsk_label: str = "Maddur Kasaba RSK (KA_MDR_01) · Mandya",
    role_badge: str | None = None,
) -> None:
    """Render the official Raitha Samparka Kendra (RSK) government portal header."""
    role_html = f'<span class="rsk-badge">👤 {role_badge}</span>' if role_badge else ""
    st.markdown(
        f"""
        <div class="rsk-tricolor"></div>
        <div class="rsk-masthead">
          <div class="rsk-masthead-left">
            <div class="rsk-emblem">🌾</div>
            <div>
              <div class="rsk-dept-kicker">Department of Agriculture · Government of Karnataka</div>
              <div class="rsk-portal-title">ರೈತ ಸಂಪರ್ಕ ಕೇಂದ್ರ · RSK AgriResolve Portal</div>
              <div class="rsk-portal-sub">{rsk_label} · 7 Revenue Villages</div>
            </div>
          </div>
          <div>{role_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero_banner(tag: str, title: str, subtitle: str) -> None:
    """Render a photographic farmland & trees hero banner."""
    banner_uri = (
        _image_data_uri("rsk_banner_trees.jpg")
        or _image_data_uri("rsk_banner_trees.png")
        or _image_data_uri("rsk_farmland_bg.jpg")
    )
    if banner_uri:
        bg_style = (
            f'background-image: linear-gradient(95deg, rgba(13, 44, 30, 0.88) 0%, '
            f'rgba(19, 58, 40, 0.72) 55%, rgba(22, 66, 45, 0.45) 100%), url("{banner_uri}");'
            "background-size: cover; background-position: center;"
        )
    else:
        bg_style = "background: linear-gradient(120deg, #123626 0%, #245c42 100%);"

    st.markdown(
        f"""
        <div class="rsk-hero" style='{bg_style}'>
          <div class="rsk-hero-tag">{tag}</div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_gov_footer() -> None:
    """Render the government-portal footer."""
    st.markdown(
        """
        <div class="rsk-footer">
          <span>🌾 <strong>AgriResolve AI — Maddur Kasaba RSK (KA_MDR_01)</strong></span>
          <span>📞 RSK Farmer &amp; Field Voice Help · ಕನ್ನಡ ಧ್ವನಿ ಸಹಾಯಕ</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
