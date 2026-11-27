"""Unit tests for Maddur RSK role-based auth and Kannada voice-note chatbot."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from app.auth import verify_credentials
from src.rag_assistant import voice_chat
from src.rag_assistant.voice_chat import SUPPORTED_LANGUAGES, _clean_for_speech, answer_farmer_voice


def _staff_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"staff_id": "STF_001", "name": "Dr. Ramesh Gowda", "role": "AO (Agriculture Officer)", "jurisdiction": "Maddur"},
            {"staff_id": "STF_002", "name": "Smt. Bhavya K.M.", "role": "AAO (Assistant Agriculture Officer)", "jurisdiction": "Sector 1"},
            {"staff_id": "STF_004", "name": "Kumari Anitha S.", "role": "AA (Agricultural Assistant)", "jurisdiction": "General"},
        ]
    )


def test_verify_credentials_supports_maddur_staff_roles() -> None:
    staff = _staff_df()
    ao = verify_credentials("AO", "STF_001", "ao123", staff)
    aao = verify_credentials("AAO", "STF_002", "aao123", staff)
    aa = verify_credentials("AA", "STF_004", "aa123", staff)
    assert ao is not None and ao.role == "AO" and ao.staff_id == "STF_001"
    assert aao is not None and aao.role == "AAO" and aao.staff_id == "STF_002"
    assert aa is not None and aa.role == "AA" and aa.staff_id == "STF_004"
    assert verify_credentials("AO", "STF_001", "wrong", staff) is None
    assert verify_credentials("AAO", "STF_001", "aao123", staff) is None


def test_kannada_farming_precautions_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice_chat, "_ask_llm", lambda _prompt: (None, "guided"))
    res = answer_farmer_voice(
        SUPPORTED_LANGUAGES["kn"].sample_prompt,
        lang_code="kn",
        include_audio=False,
    )
    assert res["sources"]
    assert "ಮಣ್ಣು ಪರೀಕ್ಷೆ" in res["answer"]
    assert res["lang"].bcp47 == "kn-IN"


def test_open_ended_query_outside_datasets_uses_llm() -> None:
    captured: list[str] = []

    def fake_llm(prompt: str) -> tuple[str, str]:
        captured.append(prompt)
        return "Apply Trichoderma viride drenching around tomato roots and maintain raised beds.", "gemini"

    with patch.object(voice_chat, "_ask_llm", side_effect=fake_llm):
        res = answer_farmer_voice(
            "What is the PM-KISAN installment eligibility?",
            lang_code="en",
            crop_hint="Tomato",
            user_role="AAO",
            include_audio=False,
        )

    assert res["mode"] == "gemini+en"
    assert "Trichoderma" in res["answer"]
    assert res["sources"] == []
    assert "role=AAO" in captured[0]


def test_clean_for_speech_strips_markdown() -> None:
    assert _clean_for_speech("- **ಮಣ್ಣು ಪರೀಕ್ಷೆ** [1]") == "- ಮಣ್ಣು ಪರೀಕ್ಷೆ"
