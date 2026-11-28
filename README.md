# Gofatho AI (Goofatho Doona) — Production Flutter Android App & Cloud APK Builder (v1.4.0+5)

Complete Phase 1–5 repository for **Gofatho AI (`et.gofazone.gofatho_ai`)**, an offline-first Android mobile application and hybrid RAG + speech AI suite for the **Gofatho language (`ISO 639-3: gof`)** spoken in the Gofa Zone (Sawula, Bulqi, Laha, Beto, Melo Koza, Demba Gofa, Zala, Geze Gofa, and Oyda), South Ethiopia Regional State.

## 1. Repository Structure

- **`.github/workflows/build_apk.yml`**: Automated GitHub Actions Cloud APK & Google Play AAB CI/CD builder (JDK 17 + Flutter 3.24.3 Stable).
- **`flutter_app/`**: Complete Material 3 Android-first Flutter project:
  - `lib/main.dart`: Trilingual UI shell (`Goofatho`, `አማርኛ`, `English`) + 5-screen `NavigationBar`.
  - `lib/l10n/app_localizations.dart`: Trilingual interface strings (`gof`, `am`, `en`).
  - `lib/models/gofatho_models.dart`: Data models for Lexicon, Everyday Phrasebook, Quad-Parallel Bible, WebAudio Slices, and Field Feedback.
  - `lib/services/database_service.dart`: Offline-first SQLite FTS5 engine (`sqflite`) querying bundled `assets/gofatho_ai_master.sqlite`.
  - `lib/services/g2p_transliterator.dart`: Bidirectional Gofatho Latin <-> Ethiopic Fidel (`ኦራꬃ ጫቁዋ`) G2P & morphological suffix decomposer preserving glottal stop `7 = /ʔ/` and Extended-A `ꬃ / ꬋ / ꬓ`.
  - `lib/services/api_sync_service.dart`: Hybrid Offline SQLite + FastAPI v3.0 RAG client & delta feedback sync.
  - `lib/services/speech_service.dart`: Unified Gofatho voice engine (`just_audio` `ClippingAudioSource` + Meta MMS ASR/TTS).
  - `lib/screens/translator_screen.dart`: **Screen 1** — 6-Direction Bi-Directional Translator with Dual-Script Fidel toggle, morphological chips & "Suggest Better Translation" drawer.
  - `lib/screens/dictionary_screen.dart`: **Screen 2** — Offline FTS5 Lexicon (`1,334 headwords`) & Everyday Conversational Phrasebook (`120 phrases` across 8 domains).
  - `lib/screens/audio_bible_screen.dart`: **Screen 3** — Synchronized Dual-Script Audio Bible (`260 chapters`, `7,931 verses`, `22,017 sub-verse phrase clips`).
  - `lib/screens/voice_assistant_screen.dart`: **Screen 4** — Push-to-Talk Gofatho Voice Assistant (`facebook/mms-1b-all` `gof-script_latin` + `facebook/mms-tts-gof`).
  - `lib/screens/feedback_screen.dart`: **Screen 5** — Community Field-Testing & Woreda Correction Queue (`Milestone 5.1`).
  - `android/`: Complete Gradle 8.2 / SDK 34 configuration, ProGuard rules, permissions, and adaptive `mipmap-*` launcher icons.
- **`backend/`**:
  - `fastapi_rag_server.py`: Unified v3.0 FastAPI server with `/api/v1/translate`, `/api/v1/phrasebook/search`, `/api/v1/feedback/submit`, and `/api/v1/mobile/sync`.
  - `morphological_analyzer.py`: Rule-based Gofatho morphological analyzer & Fidel transliterator.
  - `finetune_nllb_gofatho.py`, `train_mms_asr_gofatho.py`, `train_mms_tts_gofatho.py`: Option 5 GPU training scripts.
- **`scripts/`**:
  - `push_and_build_apk.sh`: One-command script to push to GitHub and trigger the automated Cloud APK & AAB build.
  - `generate_keystore.sh`: Generates a production Android release keystore (`gofatho-release-key.jks`) for Google Play Console.
- **`PLAY_STORE_LISTING.md` & `PRIVACY_POLICY.md`**: Milestone 5.2 Google Play Store metadata in English, Amharic, and Gofatho.

## 2. How to Compile Your Installable `.apk` in the Cloud (Zero Local Android Studio Needed)

```bash
# Step 1: Push this repository to a free GitHub repo:
./scripts/push_and_build_apk.sh https://github.com/YOUR_USERNAME/gofatho-ai-mobile.git

# Step 2: Open your GitHub repository -> "Actions" tab
# Step 3: Click the completed "Build Gofatho AI Android APK & Google Play AAB" run
# Step 4: Download "Gofatho-AI-Android-APKs-v1.4.0.zip" and install app-arm64-v8a-release.apk on your phone!
```
