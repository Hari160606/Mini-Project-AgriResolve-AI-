"""Multilingual farmer voice & text RAG assistant with Kannada MP3 voice notes.

Integrates with ``src.rag_assistant.assistant.OFFICIAL_GUIDELINES_KB`` (UAS Bengaluru
Package of Practices Zone 6) plus general basic farming precautions & safe spraying
guidance. Supports Kannada, English, Hindi, Tamil, Telugu, Marathi, and Malayalam,
synthesising playable MP3 voice notes via ``gTTS``.
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import Any

import requests

from src.rag_assistant.assistant import OFFICIAL_GUIDELINES_KB


@dataclass(frozen=True)
class LanguageSpec:
    code: str
    bcp47: str
    label: str
    english_name: str
    sample_prompt: str


SUPPORTED_LANGUAGES: dict[str, LanguageSpec] = {
    "kn": LanguageSpec(
        code="kn",
        bcp47="kn-IN",
        label="ಕನ್ನಡ (Kannada)",
        english_name="Kannada",
        sample_prompt="ಕೃಷಿ ಮಾಡುವಾಗ ತೆಗೆದುಕೊಳ್ಳಬೇಕಾದ ಮೂಲ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು ಯಾವುವು?",
    ),
    "en": LanguageSpec(
        code="en",
        bcp47="en-IN",
        label="English",
        english_name="English",
        sample_prompt="What basic precautions should farmers take while farming?",
    ),
    "hi": LanguageSpec(
        code="hi",
        bcp47="hi-IN",
        label="हिन्दी (Hindi)",
        english_name="Hindi",
        sample_prompt="खेती करते समय किसानों को कौन सी बुनियादी सावधानियां बरतनी चाहिए?",
    ),
    "ta": LanguageSpec(
        code="ta",
        bcp47="ta-IN",
        label="தமிழ் (Tamil)",
        english_name="Tamil",
        sample_prompt="விவசாயம் செய்யும்போது கடைப்பிடிக்க வேண்டிய அடிப்படை முன்னெச்சரிக்கைகள் என்ன?",
    ),
    "te": LanguageSpec(
        code="te",
        bcp47="te-IN",
        label="తెలుగు (Telugu)",
        english_name="Telugu",
        sample_prompt="వ్యవసాయం చేసేటప్పుడు తీసుకోవాల్సిన ప్రాథమిక జాగ్రత్తలు ఏమిటి?",
    ),
    "mr": LanguageSpec(
        code="mr",
        bcp47="mr-IN",
        label="मराठी (Marathi)",
        english_name="Marathi",
        sample_prompt="शेती करताना कोणती मूलभूत काळजी घ्यावी?",
    ),
    "ml": LanguageSpec(
        code="ml",
        bcp47="ml-IN",
        label="മലയാളം (Malayalam)",
        english_name="Malayalam",
        sample_prompt="കൃഷി ചെയ്യുമ്പോൾ എടുക്കേണ്ട അടിസ്ഥാന മുൻകരുതലുകൾ എന്തൊക്കെയാണ്?",
    ),
}

PRECAUTIONS_KB: list[dict[str, str]] = [
    {
        "doc_id": "RSK_SAFETY_GENERAL_01",
        "title": "Basic Farming Precautions & Crop Hygiene Checklist",
        "source": "RSK Farmer Extension Advisory (Mandya / Karnataka)",
        "crop": "General",
        "category": "Basic Farming Precautions",
        "symptoms": "General pre-sowing, field scouting, irrigation, and weather safety.",
        "advisory": (
            "1. Test soil before sowing and apply balanced fertilizers based on soil health cards.\n"
            "2. Use certified, disease-free seeds with recommended spacing for airflow.\n"
            "3. Inspect 10-20 random plants weekly for leaf spots, dead hearts, or wilting.\n"
            "4. Keep bunds weed-free and maintain open drainage channels during heavy monsoon rain.\n"
            "5. Check weather forecasts before sowing, fertilizing, or spraying."
        ),
        "citation": "RSK Field Safety Checklist (Demo Extension Note), Sec. 1",
    },
    {
        "doc_id": "RSK_SAFETY_SPRAY_02",
        "title": "Safe Pesticide Mixing & Spraying Precautions",
        "source": "RSK Farmer Extension Advisory (Mandya / Karnataka)",
        "crop": "General",
        "category": "Safe Spraying Precautions",
        "symptoms": "Personal protection, wind safety, and beneficial insect protection.",
        "advisory": (
            "1. Confirm Economic Threshold Level (ETL) with your RSK officer before spraying.\n"
            "2. Wear gloves, face mask, full sleeves, and eye protection while mixing and spraying.\n"
            "3. Never exceed the label dosage; spray only in calm morning or evening hours.\n"
            "4. Walk cross-wind so spray mist does not drift onto your face; wash with soap afterwards.\n"
            "5. Keep children and livestock away from freshly sprayed fields."
        ),
        "citation": "RSK Field Safety Checklist (Demo Extension Note), Sec. 2",
    },
]

_TOPIC_RESPONSES: dict[str, dict[str, str]] = {
    "general_precautions": {
        "kn": (
            "ರೈತರು ಕೃಷಿ ಮಾಡುವಾಗ ತೆಗೆದುಕೊಳ್ಳಬೇಕಾದ ಪ್ರಮುಖ ಮೂಲ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು:\n"
            "- ಬಿತ್ತನೆಗೂ ಮೊದಲು ಮಣ್ಣು ಪರೀಕ್ಷೆ ಮಾಡಿಸಿ ಸಮತೋಲಿತ ಗೊಬ್ಬರ ಬಳಸಿ [1].\n"
            "- ಪ್ರಮಾಣೀಕೃತ, ರೋಗರಹಿತ ಬೀಜಗಳನ್ನು ಆಯ್ಕೆ ಮಾಡಿ ಸರಿಯಾದ ಅಂತರದಲ್ಲಿ ಬಿತ್ತನೆ ಮಾಡಿ [1].\n"
            "- ವಾರಕ್ಕೊಮ್ಮೆ ಗದ್ದೆಯಲ್ಲಿ 10-20 ಗಿಡಗಳನ್ನು ಪರಿಶೀಲಿಸಿ ಎಲೆ ಚುಕ್ಕೆ, ಕಾಂಡಕೊರಕ ಅಥವಾ ಒಣಗುವಿಕೆ ಗಮನಿಸಿ [1].\n"
            "- ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸುವ ಮೊದಲು RSK ಕೃಷಿ ಅಧಿಕಾರಿಯ ಸಲಹೆ ಪಡೆಯಿರಿ; ಕೈಗವಸು ಮತ್ತು ಮಾಸ್ಕ್ ಧರಿಸಿ [1][2].\n"
            "- ಗದ್ದೆಯಲ್ಲಿ ನೀರು ನಿಲ್ಲದಂತೆ ಬಸಿಗಾಲುವೆ ಸ್ವಚ್ಛವಾಗಿಡಿ ಮತ್ತು ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ ನೋಡಿ ಕೆಲಸ ಮಾಡಿ [1]."
        ),
        "hi": (
            "खेती करते समय किसानों को ये बुनियादी सावधानियां रखनी चाहिए:\n"
            "- बुवाई से पहले मिट्टी की जांच कराएं और संतुलित खाद डालें [1].\n"
            "- प्रमाणित, रोग-मुक्त बीज चुनें और सही दूरी पर बुवाई करें [1].\n"
            "- हर सप्ताह 10-20 पौधों की जांच करें और खरपतवार व जलभराव से बचाव करें [1].\n"
            "- छिड़काव से पहले RSK अधिकारी से सलाह लें, मास्क व दस्ताने पहनें और मौसम देखकर ही छिड़काव करें [1][2]."
        ),
        "en": (
            "Basic precautions every farmer should follow:\n"
            "- Test soil before sowing and use certified, disease-free seeds with proper spacing [1].\n"
            "- Scout 10-20 random plants weekly and keep bunds & drainage channels clear [1].\n"
            "- Confirm ETL thresholds with your RSK officer before spraying; wear gloves & mask and avoid windy or rainy hours [1][2]."
        ),
    },
    "spraying_safety": {
        "kn": (
            "ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸುವಾಗ ಪಾಲಿಸಬೇಕಾದ ಸುರಕ್ಷತಾ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು:\n"
            "- ಸಿಂಪಡಣೆಗೂ ಮೊದಲು RSK ಅಧಿಕಾರಿಯಿಂದ ETL ಮಟ್ಟ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ [1].\n"
            "- ಮಿಶ್ರಣ ಮತ್ತು ಸಿಂಪಡಣೆ ವೇಳೆ ಕೈಗವಸು, ಮಾಸ್ಕ್, ಪೂರ್ಣ ತೋಳಿನ ಬಟ್ಟೆ ಧರಿಸಿ [1].\n"
            "- ಲೇಬಲ್‌ನಲ್ಲಿರುವ ಪ್ರಮಾಣ ಮೀರಬೇಡಿ; ಶಾಂತ ಬೆಳಿಗ್ಗೆ ಅಥವಾ ಸಂಜೆ ವೇಳೆ ಗಾಳಿಯ ವಿರುದ್ಧ ಸಿಂಪಡಿಸದೆ ಕೆಲಸ ಮಾಡಿ [1].\n"
            "- ಸಿಂಪಡಣೆಯ ನಂತರ ಸಾಬೂನಿನಿಂದ ಕೈ-ಮುಖ ತೊಳೆಯಿರಿ ಮತ್ತು ಮಕ್ಕಳನ್ನು ಹಾಗೂ ಜಾನುವಾರುಗಳನ್ನು ದೂರವಿಡಿ [1]."
        ),
        "hi": (
            "कीटनाशक छिड़काव की सुरक्षा सावधानियां:\n"
            "- छिड़काव से पहले RSK अधिकारी से कीट सीमा (ETL) की पुष्टि करें [1].\n"
            "- दस्ताने, मास्क और पूरी बाजू के कपड़े पहनें, और शांत सुबह या शाम के समय ही छिड़काव करें [1].\n"
            "- काम के बाद साबुन से हाथ-मुंह धोएं और बच्चों व मवेशियों को खेत से दूर रखें [1]."
        ),
        "en": (
            "Safe spraying precautions:\n"
            "- Confirm ETL with your RSK officer before spraying and never exceed label dosage [1].\n"
            "- Wear gloves, mask, and full sleeves; spray in calm morning/evening hours cross-wind [1].\n"
            "- Wash thoroughly with soap after spraying and keep children and livestock away [1]."
        ),
    },
    "paddy": {
        "kn": (
            "ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಕಾಂಡಕೊರಕ ಹುಳು (Yellow Stem Borer) ಮತ್ತು ರಕ್ಷಣೆ:\n"
            "- ನಾಟಿ ಮಾಡುವ ಮೊದಲು ಸಸಿಗಳ ಎಲೆ ತುದಿಯನ್ನು ಕತ್ತರಿಸಿ ಮೊಟ್ಟೆ ಗುಂಪುಗಳನ್ನು ನಾಶಪಡಿಸಿ [1].\n"
            "- ಮೇಲ್ವಿಚಾರಣೆಗಾಗಿ ಹೆಕ್ಟೇರ್‌ಗೆ 12 ಫೆರೋಮೋನ್ ಬಲೆಗಳನ್ನು ಅಳವಡಿಸಿ [1].\n"
            "- ಶೇ. 5 ಕ್ಕಿಂತ ಹೆಚ್ಚು ಸತ್ತ ಸುಳಿ (dead hearts) ಕಂಡರೆ ಮಾತ್ರ RSK ಸಲಹೆಯಂತೆ ನಿಯಂತ್ರಣ ಕ್ರಮ ಕೈಗೊಳ್ಳಿ ಮತ್ತು ಹೆಚ್ಚಿನ ನೈಟ್ರೋಜನ್ ಗೊಬ್ಬರ ತಪ್ಪಿಸಿ [1]."
        ),
        "en": (
            "Paddy Yellow Stem Borer guidance (UAS Bengaluru PoP):\n"
            "- Clip seedling leaf tips before transplanting and install 12 pheromone traps/ha [1].\n"
            "- Act only when dead hearts exceed 5% ETL, confirm approved spray with your RSK officer, and avoid excess nitrogen [1]."
        ),
    },
    "sugarcane": {
        "kn": (
            "ಕಬ್ಬು ಬೆಳೆಯಲ್ಲಿ ಆರಂಭಿಕ ಸುಳಿ ಕೊರಕ ಹುಳು ಮುನ್ನೆಚ್ಚರಿಕೆ (UAS ಬೆಂಗಳೂರು):\n"
            "- ನಾಟಿ ಮಾಡಿದ 45 ದಿನಗಳಲ್ಲಿ ಮಣ್ಣು ಏರಿಸುವಿಕೆ (earthing-up) ಮಾಡಿ [1].\n"
            "- 30 ದಿನಗಳ ನಂತರ 10 ದಿನಗಳ ಅಂತರದಲ್ಲಿ ಟ್ರೈಕೋಗ್ರಾಮ ಪರಾವಲಂಬಿಗಳನ್ನು ಬಿಡುಗಡೆ ಮಾಡಿ [1].\n"
            "- ಶೇ. 15 ಕ್ಕಿಂತ ಹೆಚ್ಚು ಹಾನಿ ಕಂಡರೆ RSK ಅಧಿಕಾರಿಯ ಮಾರ್ಗದರ್ಶನ ಪಡೆಯಿರಿ [1]."
        ),
    },
    "ragi": {
        "kn": (
            "ರಾಗಿ ಬೆಳೆಯಲ್ಲಿ ಬರ ಒತ್ತಡ ಮತ್ತು ತೇವಾಂಶ ಸಂರಕ್ಷಣೆ (UAS ಬೆಂಗಳೂರು):\n"
            "- ಪ್ರತಿ 6-8 ಸಾಲುಗಳ ನಡುವೆ ತೇವಾಂಶ ಸಂರಕ್ಷಣಾ ಸಾಲು (furrow) ತೆರೆಯಿರಿ [1].\n"
            "- ಬೋರ್‌ವೆಲ್ ಸೌಲಭ್ಯವಿದ್ದರೆ ತೆನೆ ಬರುವ ಮತ್ತು ಹೂ ಬಿಡುವ ಹಂತದಲ್ಲಿ 5 ಸೆಂ.ಮೀ ರಕ್ಷಣಾತ್ಮಕ ನೀರಾವರಿ ನೀಡಿ [1].\n"
            "- ಎಲೆ ಸುರುಳಿಯಾಗುವ ಒತ್ತಡದಲ್ಲಿ ಅಧಿಕಾರಿಯ ಸಲಹೆಯಂತೆ ಶೇ. 2 ಯೂರಿಯಾ ಅಥವಾ ಶೇ. 1 KNO3 ಎಲೆ ಸಿಂಪಡಣೆ ಮಾಡಿ [1]."
        ),
    },
    "mulberry": {
        "kn": (
            "ಹಿಪ್ಪುನೇರಳೆ (Mulberry) ಬೆಳೆ ರಕ್ಷಣೆ ಮತ್ತು ರೇಷ್ಮೆ ಹುಳು ಸುರಕ್ಷತೆ:\n"
            "- ಥ್ರಿಪ್ಸ್ ಮತ್ತು ಎಲೆ ಸುರುಳಿ ಕೀಟಕ್ಕೆ 0.1% ಬೇವಿನ ಎಣ್ಣೆ ಸಿಂಪಡಿಸಿ ಅಥವಾ ಪರಭಕ್ಷಕ ಮಿಟೆಗಳನ್ನು ಬಳಸಿ [1].\n"
            "- ಯಾವುದೇ ರಾಸಾಯನಿಕ ಸಿಂಪಡಿಸಿದರೆ ಕನಿಷ್ಠ 10 ದಿನಗಳ ಕಾಯುವ ಅವಧಿ ಮುಗಿದ ನಂತರವೇ ರೇಷ್ಮೆ ಹುಳುಗಳಿಗೆ ಎಲೆ ನೀಡಿ [1]."
        ),
    },
}

_MULTILINGUAL_HINTS: dict[str, str] = {
    "ಮುನ್ನೆಚ್ಚರಿಕೆ": "precautions safety",
    "ಕೃಷಿ": "farming precautions",
    "ಸಿಂಪಡಣೆ": "spraying safety",
    "ಕೀಟನಾಶಕ": "pesticide spraying",
    "ಭತ್ತ": "paddy",
    "ಕಾಂಡಕೊರಕ": "paddy stem borer",
    "ಕಬ್ಬು": "sugarcane",
    "ರಾಗಿ": "ragi drought",
    "ಬರ": "ragi drought",
    "ಹಿಪ್ಪುನೇರಳೆ": "mulberry",
    "ರೇಷ್ಮೆ": "mulberry",
    "सावधान": "precautions safety",
    "छिड़काव": "spraying safety",
    "धान": "paddy",
    "गन्ना": "sugarcane",
    "रागी": "ragi drought",
}

_NOT_COVERED: dict[str, str] = {
    "kn": "ನೀಡಲಾದ ಮಾರ್ಗಸೂಚಿಗಳಲ್ಲಿ ಈ ವಿಷಯ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಮದ್ದೂರು RSK ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
    "en": "This topic is outside the loaded guidelines. Please consult your Maddur RSK Agriculture Officer.",
    "hi": "दी गई मार्गदर्शिका में यह विषय शामिल नहीं है। कृपया अपने RSK कृषि अधिकारी से संपर्क करें।",
    "ta": "வழங்கப்பட்ட வழிகாட்டுதல்களில் இந்த தலைப்பு இல்லை. உங்கள் RSK வேளாண் அதிகாரியை அணுகவும்.",
    "te": "ఇచ్చిన మార్గదర్శకాలలో ఈ అంశం లేదు. దయచేసి మీ RSK వ్యవసాయ అధికారిని సంప్రదించండి.",
    "mr": "दिलेल्या मार्गदर्शक सूचनांमध्ये हा विषय समाविष्ट नाही. कृपया तुमच्या RSK कृषी अधिकाऱ्याशी संपर्क साधा.",
    "ml": "നൽകിയിട്ടുള്ള മാർഗ്ഗനിർദ്ദേശങ്ങളിൽ ഈ വിഷയം ഉൾപ്പെടുന്നില്ല. ദയവായി നിങ്ങളുടെ RSK കൃഷി ഓഫീസറെ ബന്ധപ്പെടുക.",
}


def _clean_for_speech(text: str) -> str:
    cleaned = re.sub(r"\[\d+\]", "", text)
    cleaned = re.sub(r"[#*_`>]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def synthesize_voice_note(text: str, lang_code: str = "kn") -> bytes | None:
    """Generate an MP3 voice note in ``lang_code`` using gTTS."""
    spoken = _clean_for_speech(text)
    if not spoken:
        return None
    try:
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text=spoken[:1200], lang=lang_code, slow=False).write_to_fp(buf)
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


def _augment_query(question: str) -> str:
    q = question.lower()
    extras = [eng for tok, eng in _MULTILINGUAL_HINTS.items() if tok in q or tok in question]
    return f"{question} {' '.join(extras)}".strip() if extras else question


_STOPWORDS = {"the", "and", "for", "with", "what", "how", "are", "can", "you", "this", "that", "from", "into"}


def _retrieve_docs(query: str, crop_hint: str = "") -> list[dict[str, str]]:
    augmented = _augment_query(f"{crop_hint} {query}".strip()).lower()
    tokens = {
        t for t in re.findall(r"[a-zA-Z0-9]+", augmented) if len(t) > 2 and t not in _STOPWORDS
    }
    corpus = PRECAUTIONS_KB + OFFICIAL_GUIDELINES_KB
    scored: list[tuple[int, dict[str, str]]] = []
    for doc in corpus:
        blob = f"{doc['crop']} {doc['category']} {doc['title']} {doc['symptoms']} {doc['advisory']}".lower()
        score = sum(
            2 if tok in doc["crop"].lower() or tok in doc["category"].lower() else 1
            for tok in tokens
            if re.search(rf"\b{re.escape(tok)}", blob)
        )
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:3]]


def _detect_topic(question: str, docs: list[dict[str, str]], crop_hint: str = "") -> str:
    q = f"{crop_hint} {question}".lower()
    if any(k in q for k in ("spray", "pesticide", "gloves", "mask", "ಸಿಂಪಡಣೆ", "ಕೀಟನಾಶಕ", "छिड़काव")):
        return "spraying_safety"
    if any(k in q for k in ("paddy", "rice", "stem borer", "ಭತ್ತ", "ಕಾಂಡಕೊರಕ", "धान")):
        return "paddy"
    if any(k in q for k in ("sugarcane", "shoot borer", "ಕಬ್ಬು", "गन्ना")):
        return "sugarcane"
    if any(k in q for k in ("ragi", "drought", "millet", "ರಾಗಿ", "ಬರ", "रागी")):
        return "ragi"
    if any(k in q for k in ("mulberry", "silkworm", "thrips", "ಹಿಪ್ಪುನೇರಳೆ", "ರೇಷ್ಮೆ")):
        return "mulberry"
    if any(k in q for k in ("precaution", "safety", "farming", "basic", "ಮುನ್ನೆಚ್ಚರಿಕೆ", "ಕೃಷಿ", "सावधान", "खेती")):
        return "general_precautions"
    if docs:
        crop = docs[0]["crop"].lower()
        if crop in {"paddy", "sugarcane", "ragi", "mulberry"}:
            return crop
    return "general_precautions"


def _ask_llm(prompt: str) -> tuple[str | None, str]:
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            from google import genai

            client = genai.Client(api_key=gemini_key)
            for model_name in ("gemini-3.5-flash-lite", "gemini-3.8-flash"):
                try:
                    resp = client.models.generate_content(model=model_name, contents=prompt)
                    if resp and resp.text:
                        return resp.text.strip(), "gemini"
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"
    model = os.getenv("OLLAMA_MODEL", "llama3").strip() or "llama3"
    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
            timeout=25,
        )
        r.raise_for_status()
        txt = str(r.json().get("response", "")).strip()
        if txt:
            return txt, f"ollama ({model})"
    except Exception:  # noqa: BLE001
        pass
    return None, "guided"


def answer_farmer_voice(
    question: str,
    lang_code: str = "kn",
    crop_hint: str = "",
    village_hint: str = "",
    include_audio: bool = True,
    user_role: str = "Farmer",
) -> dict[str, Any]:
    """Answer any farmer or field-officer query in ``lang_code`` with optional MP3 voice note.

    Uses retrieved RSK / UAS Bengaluru PoP documents as grounding context when relevant,
    and answers open-ended queries across any crop or agricultural topic via LLM even when
    no local dataset document matches.
    """
    lang = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES["kn"])
    docs = _retrieve_docs(question, crop_hint=crop_hint)

    audience = (
        f"an Agriculture Field Officer ({user_role})"
        if user_role in {"AO", "AAO", "AA"}
        else "a farmer"
    )
    role_style = (
        "Provide practical, field-actionable diagnostic and management points (under 180 words)."
        if user_role in {"AO", "AAO", "AA"}
        else "Write clearly in simple, spoken-friendly bullet points (under 150 words)."
    )

    if docs:
        context_block = (
            "Optional RSK / UAS Bengaluru Reference Context (cite [1], [2] when used):\n"
            + "\n\n".join(
                f"[{i}] {d['title']} ({d['citation']})\nSymptoms/Scope: {d['symptoms']}\nAdvisory:\n{d['advisory']}"
                for i, d in enumerate(docs, start=1)
            )
        )
    else:
        context_block = (
            "Local RSK reference documents do not have an exact match for this query. "
            "Answer directly using your agricultural, agronomic, and general extension knowledge."
        )

    prompt = (
        f"You are an AI agricultural and RSK field assistant at Maddur Kasaba RSK (Mandya, Karnataka) "
        f"helping {audience} in {lang.english_name}. "
        f"Answer ANY farming, crop, pest, disease, soil, fertilizer, irrigation, weather, livestock, "
        f"market, government scheme, or field-inspection question accurately in {lang.english_name}, "
        f"even if it is outside the reference passages below. Never refuse just because a crop or topic "
        f"is not in the local context. {role_style} "
        f"Context: village={village_hint or 'Maddur'}, crop={crop_hint or 'any'}, role={user_role}.\n\n"
        f"{context_block}\n\nUser question: {question}\nAnswer in {lang.english_name}:"
    )

    llm_answer, llm_mode = _ask_llm(prompt)
    if llm_answer:
        answer = llm_answer
        mode = f"{llm_mode}+{lang.code}"
    else:
        topic = _detect_topic(question, docs, crop_hint=crop_hint)
        topic_map = _TOPIC_RESPONSES.get(topic, _TOPIC_RESPONSES["general_precautions"])
        if lang.code in topic_map:
            answer = topic_map[lang.code]
        elif lang.code == "kn":
            answer = _TOPIC_RESPONSES["general_precautions"]["kn"]
        else:
            answer = topic_map.get("en") or (docs[0]["advisory"] if docs else _TOPIC_RESPONSES["general_precautions"]["en"])
        mode = f"guided+{lang.code}"

    sources = [
        {
            "citation": f"[{i}]",
            "title": d["title"],
            "document": d["source"],
            "citation_ref": d["citation"],
            "excerpt": d["advisory"],
        }
        for i, d in enumerate(docs, start=1)
    ]
    audio_bytes = synthesize_voice_note(answer, lang.code) if include_audio else None
    return {
        "answer": answer,
        "audio_bytes": audio_bytes,
        "sources": sources,
        "mode": mode,
        "lang": lang,
    }
