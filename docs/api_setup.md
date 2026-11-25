# Phase 3: External API & AI Engine Setup Guide

This document provides step-by-step instructions for enabling Google Cloud Platform (GCP) APIs and local/hosted AI engines, following the strict rule to prefer free quotas and clear cost restrictions.

---

## 1. Google Cloud Platform (GCP) APIs Setup

### 1.1 APIs Required
1. **Google Maps JavaScript API**: For interactive village spatial mapping in the AO/AAO Streamlit dashboard.
2. **Google Routes API (Compute Routes)**: For computing travel distances, drive times, and optimized inspection routing from Maddur RSK to flagged villages.
3. **Google Weather API (or Open-Meteo fallback)**: For real-time temperature, relative humidity, wind speed, and precipitation forecasts.

### 1.2 Step-by-Step Enablement in Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `AgriResolve-AI-Mandya`).
3. Enable Billing on the project (Required by GCP to activate Maps & Routes APIs, even though the monthly free quota covers all development and demo needs).
4. Navigate to **APIs & Services > Library**:
   - Search for **"Maps JavaScript API"** and click **Enable**.
   - Search for **"Routes API"** and click **Enable**.
5. Navigate to **APIs & Services > Credentials**:
   - Click **Create Credentials > API key**.
   - Rename key to `agriresolve-maps-routes-key`.
6. **Key Restrictions (Crucial Security Best Practice)**:
   - Under **API restrictions**, select **Restrict key** and tick *Maps JavaScript API* and *Routes API*.
   - Never remove restrictions for production keys.
7. Copy the key and place it into your `.env` file:
   ```env
   GOOGLE_MAPS_API_KEY=AIzaSy...
   GOOGLE_ROUTES_API_KEY=AIzaSy...
   ```

### 1.3 Free Quota & Billing Safeguards
- **Maps JavaScript API**: Provides \$200 monthly free credit from Google (~28,500 map loads per month free).
- **Routes API**: Tier 1 provides up to 10,000 route computations free under the monthly \$200 credit.
- **Quota Safeguard**: To prevent accidental charges, go to **APIs & Services > Quotas & System Limits** and cap daily requests to 500 requests/day.
- **Zero-Cost Fallback**: If an API key is not provided, AgriResolve AI automatically degrades gracefully to interactive Plotly Express open-source maps and Euclidean distance approximations.

---

## 2. Google Earth Engine (Sentinel-2 NDVI) Setup

1. Sign up at [earthengine.google.com](https://earthengine.google.com/) using an academic or standard Google account.
2. Register a Google Cloud Project for Earth Engine access (Free for academic and research use).
3. Authenticate locally via command line:
   ```bash
   earthengine authenticate
   ```
4. AgriResolve AI provides an offline pre-extracted Sentinel-2 NDVI dataset (`data/raw/sentinel2_ndvi_raw.xlsx`), so Earth Engine live authentication is optional during local evaluations.

---

## 3. Local LLM (Ollama) vs. Google Gemini API Evaluation

### 3.1 Decision & Justification
- **Primary / Default Engine**: **Ollama (Local LLM)**.
  - **Model**: `mistral:7b` or `llama3:8b`.
  - **Reason**: 100% offline, zero API costs, zero data leakage, works in remote rural centers without high-bandwidth internet.
  - **Setup**: Install Ollama from [ollama.com](https://ollama.com) and run:
    ```bash
    ollama run mistral
    ```
- **Optional Hybrid Engine**: **Google Gemini (Gemini 1.5 / 2.0 Flash)**.
  - **Reason**: Useful when the local machine lacks a dedicated GPU or has constrained RAM (< 8GB), or when rapid low-latency multimodal analysis is requested.
  - **Setup**: Get a free API key from [Google AI Studio](https://aistudio.google.com/). Set `GEMINI_API_KEY=AIzaSy...` in `.env`.
  - **Architecture**: The AI Field Assistant module (`src/rag_assistant/`) is designed with a pluggable interface supporting both Ollama and Gemini with strict source citations.
