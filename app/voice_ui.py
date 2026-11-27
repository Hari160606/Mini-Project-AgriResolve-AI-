"""Warm harvest-themed regional voice & text chatbot UI for farmers and field officers."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import streamlit as st

from app.auth import AuthenticatedUser
from src.rag_assistant.voice_chat import SUPPORTED_LANGUAGES, answer_farmer_voice

_VOICE_HTML = """
<div class="voice-card">
  <div class="voice-top">
    <div class="voice-actions">
      <button id="mic-btn" type="button" class="vbtn vbtn-mic">🎙️ ಮಾತನಾಡಿ / Speak</button>
      <button id="speak-btn" type="button" class="vbtn vbtn-read">🔊 ಕೇಳಿ / Listen</button>
      <button id="stop-btn" type="button" class="vbtn vbtn-stop">⏹ Stop</button>
    </div>
    <span id="status-pill" class="vpill">Ready</span>
  </div>
  <div id="live-transcript" class="vtranscript">Tap "Speak" and ask your question in Kannada or any selected language.</div>
</div>
"""

_VOICE_CSS = """
.voice-card {
  background: linear-gradient(135deg, #fffdf7 0%, #fef7e6 100%);
  border: 1px solid #f0d799;
  border-left: 5px solid #d97706;
  border-radius: 14px;
  padding: 14px 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  box-shadow: 0 4px 14px rgba(146, 64, 14, 0.08);
}
.voice-top {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.voice-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.vbtn {
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 9px 16px;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.1s ease, background 0.15s ease;
}
.vbtn:active {
  transform: scale(0.98);
}
.vbtn-mic {
  background: linear-gradient(135deg, #166534 0%, #15803d 100%);
  color: #ffffff;
  box-shadow: 0 3px 10px rgba(22, 101, 52, 0.24);
}
.vbtn-mic.listening {
  background: linear-gradient(135deg, #b91c1c 0%, #dc2626 100%);
}
.vbtn-read {
  background: #fef3c7;
  color: #92400e;
  border-color: #f59e0b;
}
.vbtn-read:hover {
  background: #fde68a;
}
.vbtn-stop {
  background: #ffffff;
  color: #374151;
  border-color: #d6d3d1;
}
.vpill {
  font-size: 12px;
  font-weight: 700;
  padding: 5px 12px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #166534;
  border: 1px solid #bbf7d0;
}
.vtranscript {
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px dashed #e7d5a8;
  font-size: 13.5px;
  color: #57534e;
  min-height: 20px;
}
"""

_VOICE_JS = """
export default function(component) {
  const { setTriggerValue, parentElement, data } = component;
  const micBtn = parentElement.querySelector("#mic-btn");
  const speakBtn = parentElement.querySelector("#speak-btn");
  const stopBtn = parentElement.querySelector("#stop-btn");
  const statusEl = parentElement.querySelector("#status-pill");
  const transcriptEl = parentElement.querySelector("#live-transcript");

  const payload = data || {};
  const langCode = payload.bcp47 || "kn-IN";
  const langLabel = payload.label || langCode;
  const speakText = payload.speak_text || "";

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;

  const speakOut = (text) => {
    if (!("speechSynthesis" in window) || !text) {
      statusEl.textContent = "No reply yet";
      return;
    }
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = langCode;
    const voices = window.speechSynthesis.getVoices() || [];
    const match = voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(langCode.split("-")[0].toLowerCase()));
    if (match) utter.voice = match;
    utter.rate = 0.95;
    statusEl.textContent = "Speaking · " + langLabel;
    utter.onend = () => { statusEl.textContent = "Ready"; };
    utter.onerror = () => { statusEl.textContent = "Ready"; };
    window.speechSynthesis.speak(utter);
  };

  if (!SpeechRec) {
    micBtn.disabled = true;
    micBtn.textContent = "🎙️ Mic Unavailable";
    statusEl.textContent = "Use Chrome/Edge for mic";
  } else {
    statusEl.textContent = "Ready · " + langLabel;
    micBtn.onclick = () => {
      if (isListening && recognition) { recognition.stop(); return; }
      recognition = new SpeechRec();
      recognition.lang = langCode;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      isListening = true;
      micBtn.classList.add("listening");
      micBtn.textContent = "⏹ Listening... Stop";
      statusEl.textContent = "Listening (" + langLabel + ")";
      transcriptEl.textContent = "Speak now...";

      let finalText = "";
      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const piece = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalText += piece + " ";
          else interim += piece;
        }
        transcriptEl.textContent = (finalText + interim).trim() || "Listening...";
      };
      recognition.onerror = (event) => {
        isListening = false;
        micBtn.classList.remove("listening");
        micBtn.textContent = "🎙️ ಮಾತನಾಡಿ / Speak";
        statusEl.textContent = "Mic error: " + event.error;
      };
      recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove("listening");
        micBtn.textContent = "🎙️ ಮಾತನಾಡಿ / Speak";
        const cleaned = finalText.trim();
        if (cleaned) {
          statusEl.textContent = "Sending question...";
          setTriggerValue("transcript", { text: cleaned, lang: langCode, ts: Date.now() });
        } else {
          statusEl.textContent = "Ready · " + langLabel;
        }
      };
      recognition.start();
    };
  }

  speakBtn.onclick = () => speakOut(speakText);
  stopBtn.onclick = () => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    statusEl.textContent = "Stopped";
  };

  return () => {
    if (recognition && isListening) {
      try { recognition.stop(); } catch (_) {}
    }
  };
}
"""

_QUICK_PROMPTS_KN: list[tuple[str, str]] = [
    ("🛡️ ಮೂಲ ಕೃಷಿ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು · Basic Farming Precautions", "ಕೃಷಿ ಮಾಡುವಾಗ ತೆಗೆದುಕೊಳ್ಳಬೇಕಾದ ಮೂಲ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು ಯಾವುವು?"),
    ("🧪 ಕೀಟನಾಶಕ ಸಿಂಪಡಣೆ ಸುರಕ್ಷತೆ · Safe Spraying", "ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸುವಾಗ ಯಾವ ಸುರಕ್ಷತಾ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳನ್ನು ಪಾಲಿಸಬೇಕು?"),
    ("🌾 ಭತ್ತದ ಕಾಂಡಕೊರಕ ಹುಳು · Paddy Stem Borer", "ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಕಾಂಡಕೊರಕ ಹುಳು ನಿಯಂತ್ರಣ ಹೇಗೆ?"),
    ("💧 ರಾಗಿ ಬರ ಮತ್ತು ಯೋಜನೆಗಳು · Drought & Schemes", "ರಾಗಿ ಬೆಳೆಯಲ್ಲಿ ಬರ ಒತ್ತಡ ತಪ್ಪಿಸಲು ಯಾವ ಕ್ರಮ ತೆಗೆದುಕೊಳ್ಳಬೇಕು?"),
]


@st.cache_resource(show_spinner=False)
def _voice_component() -> Any:
    return st.components.v2.component(
        "rsk_farmer_voice_widget_v2",
        html=_VOICE_HTML,
        css=_VOICE_CSS,
        js=_VOICE_JS,
    )


def _can_mount_bidi() -> bool:
    from streamlit.components.v2.component_manager import BidiComponentManager
    from streamlit.runtime import Runtime

    return Runtime.exists() and isinstance(
        getattr(Runtime.instance(), "bidi_component_registry", None), BidiComponentManager
    )


def _submit_question(
    question_text: str,
    lang_code: str,
    crop_hint: str,
    village_hint: str,
    user_role: str = "Farmer",
) -> None:
    history = st.session_state.setdefault("voice_chat_history", [])
    history.append({"role": "user", "content": question_text, "lang": lang_code})
    res = answer_farmer_voice(
        question_text,
        lang_code=lang_code,
        crop_hint=crop_hint,
        village_hint=village_hint,
        include_audio=True,
        user_role=user_role,
    )
    history.append(
        {
            "role": "assistant",
            "content": res["answer"],
            "audio_bytes": res.get("audio_bytes"),
            "sources": res["sources"],
            "mode": res["mode"],
            "lang": lang_code,
            "id": str(time.time_ns()),
        }
    )


def render_farmer_voice_chatbot(villages_df: pd.DataFrame, user: AuthenticatedUser | None = None) -> None:
    """Render the warm harvest-themed regional farmer & field officer voice chatbot."""
    st.markdown(
        """
        <div class="farmer-hero">
          <div class="farmer-hero-kicker">🌱 ರೈತ ಧ್ವನಿ ಸಹಾಯ · Raitha Samparka Kendra Voice Desk</div>
          <h2>ಕನ್ನಡ ಮತ್ತು ಪ್ರಾದೇಶಿಕ ಕೃಷಿ ಧ್ವನಿ ಸಹಾಯಕ · Farmer Voice Chatbot</h2>
          <p>Ask any question on crops, pests, fertilizers, soil testing, weather, or government schemes by voice or text — answered in Kannada or your preferred language with a voice note.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_role = user.role if user else "Farmer"
    history: list[dict[str, Any]] = st.session_state.setdefault("voice_chat_history", [])
    last_assistant = next((m for m in reversed(history) if m["role"] == "assistant"), None)

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.1, 1.1], vertical_alignment="bottom")
        lang_codes = list(SUPPORTED_LANGUAGES.keys())
        lang_code = c1.selectbox(
            "Language / ಭಾಷೆ",
            lang_codes,
            index=0,
            format_func=lambda c: SUPPORTED_LANGUAGES[c].label,
            key="voice_chat_lang",
        )
        lang_spec = SUPPORTED_LANGUAGES[lang_code]

        village_options = ["—"] + villages_df["village_name"].tolist()
        v_default = user.village_name if (user and user.village_name in village_options) else "—"
        v_choice = c2.selectbox(
            "Village (optional)",
            village_options,
            index=village_options.index(v_default),
            key="voice_village",
        )
        crop_choice = c3.selectbox(
            "Crop (optional)",
            ["—", "Paddy", "Sugarcane", "Ragi", "Mulberry", "Banana", "Maize", "Groundnut", "Vegetables", "Coconut", "Any / Other"],
            key="voice_crop",
        )
        auto_play = c4.toggle("Auto-play", value=True, key="voice_auto_play")
        if c5.button("Clear", icon=":material/delete_sweep:", width="stretch"):
            st.session_state["voice_chat_history"] = []
            st.session_state.pop("last_voice_ts", None)
            st.rerun()

    village_hint = "" if v_choice == "—" else v_choice
    crop_hint = "" if crop_choice in {"—", "Any / Other"} else crop_choice

    if _can_mount_bidi():
        mount_voice = _voice_component()
        voice_res = mount_voice(
            key="rsk_farmer_voice_mount",
            data={
                "bcp47": lang_spec.bcp47,
                "label": lang_spec.label,
                "speak_text": last_assistant["content"] if last_assistant else "",
            },
            on_transcript_change=lambda: None,
        )
        payload = getattr(voice_res, "transcript", None)
        if isinstance(payload, dict) and payload.get("text"):
            ts = payload.get("ts")
            if ts != st.session_state.get("last_voice_ts"):
                st.session_state["last_voice_ts"] = ts
                _submit_question(str(payload["text"]).strip(), lang_code, crop_hint, village_hint, user_role=user_role)
                st.rerun()

    if not history:
        st.markdown("#### Quick topics · ತ್ವರಿತ ವಿಷಯಗಳು")
        row1 = st.columns(2)
        row2 = st.columns(2)
        grid = [row1[0], row1[1], row2[0], row2[1]]
        for idx, (label, prompt_text) in enumerate(_QUICK_PROMPTS_KN):
            if grid[idx].button(label, width="stretch", key=f"quick_kn_{idx}"):
                query_text = SUPPORTED_LANGUAGES[lang_code].sample_prompt if (idx == 0 and lang_code != "kn") else prompt_text
                _submit_question(query_text, lang_code, crop_hint, village_hint, user_role=user_role)
                st.rerun()

    for idx, msg in enumerate(history):
        avatar = ":material/person:" if msg["role"] == "user" else ":material/agriculture:"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                audio = msg.get("audio_bytes")
                is_latest = last_assistant is not None and msg.get("id") == last_assistant.get("id")
                if audio:
                    st.audio(audio, format="audio/mp3", autoplay=bool(auto_play and is_latest))
                    dl_col, info_col = st.columns([1.4, 4.6], vertical_alignment="center")
                    dl_col.download_button(
                        "Download MP3",
                        data=audio,
                        file_name=f"rsk_voice_{msg.get('lang', 'kn')}_{idx + 1}.mp3",
                        mime="audio/mpeg",
                        icon=":material/download:",
                        key=f"dl_voice_{idx}",
                    )
                    msg_lang = SUPPORTED_LANGUAGES.get(msg.get("lang", "kn"), lang_spec)
                    info_col.caption(f"{msg_lang.english_name} voice note ready")
                else:
                    st.caption("MP3 voice note unavailable offline — use 'Listen' above.")
                sources = msg.get("sources") or []
                if sources:
                    with st.expander(f"Reference sources ({len(sources)})"):
                        for src in sources:
                            st.markdown(
                                f"**{src['citation']} {src['title']}** — {src['citation_ref']}\n\n> {src['excerpt']}"
                            )

    typed = st.chat_input(f"Ask any farming question in {lang_spec.label}…")
    if typed and typed.strip():
        _submit_question(typed.strip(), lang_code, crop_hint, village_hint, user_role=user_role)
        st.rerun()
