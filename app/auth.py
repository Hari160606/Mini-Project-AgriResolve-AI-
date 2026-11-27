"""Role-based authentication with dedicated login screens for AO, AAO/Field, and Farmer portals."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

import pandas as pd
import streamlit as st

ROLE_OPTIONS: tuple[str, ...] = ("AO", "AAO", "AA", "Farmer")

ROLE_LABELS: dict[str, str] = {
    "AO": "AO — Agriculture Officer",
    "AAO": "AAO — Assistant Agriculture Officer",
    "AA": "AA — Agricultural Assistant",
    "Farmer": "Farmer — ಕನ್ನಡ ಧ್ವನಿ ಸಹಾಯ (Voice Help)",
}

_PORTAL_TABS: tuple[str, ...] = (
    "AO Login",
    "AAO / Field Login",
    "Farmer Voice Help",
)

_DEFAULT_PASSWORDS: dict[str, str] = {
    "AO": "ao123",
    "AAO": "aao123",
    "AA": "aa123",
}


@dataclass(frozen=True)
class AuthenticatedUser:
    """Signed-in user stored in ``st.session_state['auth_user']``."""

    role: str
    staff_id: str | None
    name: str
    jurisdiction: str | None = None
    village_name: str | None = None


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _extract_short_role(raw_role: object) -> str:
    """Normalize roles like 'AO (Agriculture Officer)' or 'AAO' into short codes."""
    text = str(raw_role).strip().upper()
    if text.startswith("AAO"):
        return "AAO"
    if text.startswith("AO"):
        return "AO"
    if text.startswith("AA"):
        return "AA"
    return text


def expected_password_hash(role: str) -> str:
    """Return SHA-256 digest for the configured demo password of ``role``."""
    env_key = f"DEMO_{role.upper()}_PASSWORD"
    raw = os.getenv(env_key, _DEFAULT_PASSWORDS.get(role.upper(), "")).strip()
    return _hash_secret(raw)


def verify_credentials(
    role: str,
    staff_id: str,
    password: str,
    staff_df: pd.DataFrame,
) -> AuthenticatedUser | None:
    """Validate officer role, staff_id, and password."""
    norm_role = role.strip().upper()
    if norm_role not in {"AO", "AAO", "AA"} or not password:
        return None
    normalized_roles = staff_df["role"].apply(_extract_short_role)
    matches = staff_df[(staff_df["staff_id"] == staff_id) & (normalized_roles == norm_role)]
    if matches.empty:
        return None
    if not hmac.compare_digest(_hash_secret(password), expected_password_hash(norm_role)):
        return None
    row = matches.iloc[0]
    return AuthenticatedUser(
        role=norm_role,
        staff_id=str(row["staff_id"]),
        name=str(row["name"]),
        jurisdiction=str(row.get("jurisdiction", "")),
    )


def get_current_user() -> AuthenticatedUser | None:
    user = st.session_state.get("auth_user")
    return user if isinstance(user, AuthenticatedUser) else None


def sign_out() -> None:
    st.session_state.pop("auth_user", None)


def _combined_staff(staff_df: pd.DataFrame) -> pd.DataFrame:
    extra = st.session_state.get("registered_demo_staff", [])
    return pd.concat([staff_df, pd.DataFrame(extra)], ignore_index=True) if extra else staff_df


def _staff_for_role(staff_df: pd.DataFrame, role: str) -> pd.DataFrame:
    combined = _combined_staff(staff_df)
    mask = combined["role"].apply(_extract_short_role) == role.upper()
    return combined[mask].reset_index(drop=True)


def _render_officer_login_page(
    role_code: str,
    title: str,
    subtitle: str,
    staff_df: pd.DataFrame,
    allow_aa_switch: bool = False,
) -> None:
    """Render a dedicated, clean login screen for AO or AAO/Field Officers."""
    st.markdown(
        f'<div class="rsk-login-header"><h3>{title}</h3><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )

    active_role = role_code
    if allow_aa_switch:
        active_role = (
            st.segmented_control(
                "Officer cadre",
                ["AAO", "AA"],
                default="AAO",
                format_func=lambda r: ROLE_LABELS[r],
                key="field_officer_cadre",
                width="stretch",
            )
            or "AAO"
        )

    signin_tab, signup_tab = st.tabs(["Sign In", "Register Demo Officer"])
    role_staff = _staff_for_role(staff_df, active_role)

    with signin_tab:
        if role_staff.empty:
            st.warning(f"No {active_role} accounts found in staff roster.")
        else:
            with st.form(f"officer_login_form_{active_role}"):
                options = (role_staff["staff_id"] + " · " + role_staff["name"]).tolist()
                chosen = st.selectbox(f"Select {active_role} officer", options)
                password = st.text_input("Password / PIN", type="password", placeholder="Enter password")
                submitted = st.form_submit_button(
                    f"Sign in to {active_role} portal",
                    type="primary",
                    width="stretch",
                )
            if submitted:
                staff_id = chosen.split(" · ")[0]
                user = verify_credentials(active_role, staff_id, password, _combined_staff(staff_df))
                if user is None:
                    st.error("Invalid password for the selected officer.")
                else:
                    st.session_state["auth_user"] = user
                    st.rerun()

    with signup_tab:
        with st.form(f"officer_signup_form_{active_role}"):
            new_name = st.text_input("Officer full name", placeholder=f"e.g. Shri Kiran ({active_role})")
            new_sector = st.text_input("Sector / Jurisdiction", value="Maddur Kasaba Sector")
            default_pw = _DEFAULT_PASSWORDS[active_role]
            st.caption(f"Demo {active_role} accounts use password `{default_pw}`.")
            create_btn = st.form_submit_button(
                f"Create & sign in as {active_role}",
                width="stretch",
            )
        if create_btn:
            if len(new_name.strip()) < 3:
                st.error("Enter a name of at least 3 characters.")
            else:
                extra = st.session_state.setdefault("registered_demo_staff", [])
                existing_ids = set(_combined_staff(staff_df)["staff_id"])
                idx = len(existing_ids) + 1
                while f"STF_{idx:03d}" in existing_ids:
                    idx += 1
                new_id = f"STF_{idx:03d}"
                extra.append(
                    {
                        "staff_id": new_id,
                        "name": new_name.strip(),
                        "role": f"{active_role} (Demo)",
                        "designation": f"Demo {active_role}",
                        "jurisdiction": new_sector.strip() or "Maddur Kasaba RSK",
                        "phone_masked": "+91 94808 XXXXX",
                        "status": "Available for Dispatch",
                        "active_inspections_count": 0,
                        "max_weekly_capacity": 6,
                        "data_type": "Synthetic",
                        "is_synthetic": True,
                    }
                )
                st.session_state["auth_user"] = AuthenticatedUser(
                    role=active_role,
                    staff_id=new_id,
                    name=new_name.strip(),
                    jurisdiction=new_sector.strip() or "Maddur Kasaba RSK",
                )
                st.rerun()


def _render_farmer_login_page(villages_df: pd.DataFrame) -> None:
    """Render the dedicated passwordless Farmer Voice Help entry screen."""
    st.markdown(
        '<div class="rsk-login-header">'
        '<h3>🌱 Farmer Voice Help Portal (ರೈತ ಧ್ವನಿ ಸಹಾಯ)</h3>'
        '<p>No password required. Enter directly to ask crop, pest, soil, weather, or scheme questions in Kannada or your regional language.</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    with st.form("farmer_login_form"):
        farmer_name = st.text_input("Your name (optional)", placeholder="e.g. Ramesh")
        village_choices = ["All / Not specified"] + villages_df["village_name"].tolist()
        village_pick = st.selectbox("Village (optional)", village_choices)
        submitted = st.form_submit_button(
            "Open Farmer Voice Chatbot",
            type="primary",
            width="stretch",
        )
    if submitted:
        st.session_state["auth_user"] = AuthenticatedUser(
            role="Farmer",
            staff_id=None,
            name=farmer_name.strip() or "Farmer Guest",
            village_name=None if village_pick.startswith("All") else village_pick,
        )
        st.rerun()


def render_login_page(staff_df: pd.DataFrame, villages_df: pd.DataFrame) -> None:
    """Render clean, separate login pages for AO, AAO/Field Officer, and Farmer portals."""
    portal = (
        st.segmented_control(
            "Select login portal",
            list(_PORTAL_TABS),
            default="AO Login",
            key="login_portal",
            bind="query-params",
            width="stretch",
            label_visibility="collapsed",
        )
        or "AO Login"
    )

    if portal == "AO Login":
        _render_officer_login_page(
            role_code="AO",
            title="🌾 Agriculture Officer (AO) Login",
            subtitle="Sign in to access the Maddur Kasaba RSK Command Dashboard, spatial priority map, and inspection dispatch.",
            staff_df=staff_df,
            allow_aa_switch=False,
        )
    elif portal == "AAO / Field Login":
        _render_officer_login_page(
            role_code="AAO",
            title="🚜 Assistant Agriculture Officer (AAO / AA) Login",
            subtitle="Sign in to access the Field Inspection Workspace, register farmer grievances, and review assigned visits.",
            staff_df=staff_df,
            allow_aa_switch=True,
        )
    else:
        _render_farmer_login_page(villages_df)

    with st.expander("Demo login credentials", expanded=False):
        st.markdown(
            """
| Portal | Officer IDs | Password |
|---|---|---|
| **AO** | `STF_001` (Dr. Ramesh Gowda) | `ao123` |
| **AAO** | `STF_002`, `STF_003` | `aao123` |
| **AA** | `STF_004` (Kumari Anitha S.) | `aa123` |
| **Farmer** | No password required | Direct entry |
            """
        )
