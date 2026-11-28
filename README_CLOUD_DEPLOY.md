---
title: Gofatho AI RAG & Voice Server
emoji: 🇪🇹
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: true
---

# 🇪🇹 Gofatho AI — Cloud Hybrid RAG + Gemini 2.5 Flash Native Chat Server (v3.0)

This repository contains both:
1. **Option A — Direct On-Device SQLite RAG + Gemini Native Chat** inside the Flutter Android/iOS Mobile App (`flutter_app/`) and Web Studio (`gofatho_ai_studio.html`), where the phone itself queries `gofatho_ai_master.sqlite` locally and connects directly to `gemini-2.5-flash`.
2. **Option B — Hosted Cloud FastAPI RAG + Gemini Server** (`backend/fastapi_rag_server.py` + `Dockerfile`), so public mobile users can chat in native Gofatho without needing their own API key.

## 🚀 Free 2-Minute Cloud Deployment Guide

### Method 1: Deploy Free on Hugging Face Spaces (Recommended — Free 16 GB RAM CPU)
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Name your Space **`gofatho-ai-server`**, select **`Docker`** as the Space SDK, and choose **`Blank`**.
3. Upload `Dockerfile`, `README.md` (with the YAML header above), `backend/`, and `data/gofatho_ai_master.sqlite`.
4. In your Space's **Settings -> Variables and secrets**, click **New secret**:
   - Name: `GEMINI_API_KEY`
   - Value: *(Your free API key from [Google AI Studio](https://aistudio.google.com/apikey))*
5. Once running, your public API URL will be:
   `https://<your-hf-username>-gofatho-ai-server.hf.space`
   Paste this URL into the **AI Settings** modal of your Gofatho AI Android app!

### Method 2: Deploy Free on Render.com (1-Click Blueprint)
1. Push this folder to a GitHub repository.
2. On [dashboard.render.com](https://dashboard.render.com), click **New -> Blueprint** and select your repository (`render.yaml` is detected automatically).
3. Enter your `GEMINI_API_KEY` when prompted and click **Apply**.
