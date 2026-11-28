# Gofatho AI (`v4.0.0+12`) — Google Play Store Launch Kit & Manual Execution Runbook

## 1. Your 3-Step Manual Execution Runbook (What Requires Your Account Credentials)

Because Google Colab GPU execution, Hugging Face Spaces tokens, and Google Play Console developer sign-in require your personal credentials, everything has been automated so your manual part takes under 10 minutes:

### Step A — Compile Your Signed `v4.0` Android `.apk` & Google Play `.aab` (One Click in Colab)
1. Open `Gofatho_AI_Phases1_to_9_Master_Production_Colab.ipynb` in Google Colab.
2. Click **`Runtime -> Run all`**.
3. The notebook automatically mounts your `Gofa Ai` Google Drive folder, builds all **17 SQLite tables** (including the 200-entry `textbook_chapters_28_deep & sellassie_igt_corpus`), exports the full 34 MB `facebook/mms-tts-gof` `model.int8.onnx` voice checkpoint into `gofatho_sherpa_onnx_tts`, generates your 2048-bit RSA `upload-keystore.jks`, and saves:
   - `Gofatho_AI_v4.0_arm64-v8a_Release.apk` (for modern Android phones in Gofa Zone)
   - `Gofatho_AI_v4.0_armeabi-v7a_Release.apk` (for budget 32-bit Android phones)
   - `Gofatho_AI_v4.0_Universal_Release.apk` (for universal sharing via Telegram / WhatsApp)
   - `Gofatho_AI_v4.0_GooglePlay_Signed.aab` (for Google Play Console upload)

### Step B — Deploy Your 24/7 Cloud Backend (`FastAPI v5.0`) to Hugging Face Spaces
1. Create a free Write Token at `https://huggingface.co/settings/tokens`.
2. Paste `HF_WRITE_TOKEN = "hf_..."` and your `GEMINI_API_KEY = "AIzaSy..."` into **Cell 3** of `Gofatho_AI_Phases1_to_9_Master_Production_Colab.ipynb` and run the cell.
3. Your live API (`https://<your-username>-gofatho-ai.hf.space`) goes online automatically with Swagger docs at `/docs`.

### Step C — Upload `Gofatho_AI_v4.0_GooglePlay_Signed.aab` to Google Play Console
1. Sign in to `https://play.google.com/console` and click **Create app**.
2. Copy-paste the store listing text and Data Safety questionnaire answers from Sections 2 and 3 below.
3. Go to **Production -> Create new release**, upload `Gofatho_AI_v4.0_GooglePlay_Signed.aab` from your Drive `Android_APK_Builds` folder, and click **Start rollout to Production**.

---

## 2. Copy-Paste Trilingual Google Play Store Listing (`et.gofazone.gofatho_ai`)

| Field | Limit | Ready-to-Paste Text |
| :--- | :--- | :--- |
| **App Name** | 30 chars | `Gofatho AI: Gofa Translator` |
| **Short Description (EN)** | 80 chars | `Offline Gofatho ↔ Amharic ↔ English AI Translator, Audio Bible, Legal & Quiz Hub` |
| **Short Description (AM)** | 80 chars | `የጎፋኛ ↔ አማርኛ ↔ እንግሊዝኛ ተርጓሚ፣ የድምፅ መጽሐፍ ቅዱስ፣ የሕግ እና የትምህርት ረዳት` |
| **Short Description (GOF)** | 80 chars | `Goofatho ↔ Amaaratho ↔ Inggilizetho Birshshiyaa, Geeshsha Maxaafaanne Higge Maado` |
| **Primary Category** | — | `Education` (Secondary: `Books & Reference`) |
| **Package ID** | — | `et.gofazone.gofatho_ai` (`versionName: 4.0.0`, `versionCode: 12`) |

### Full Description (English / Amharic / Goofatho)
**Gofatho AI (`v4.0`)** is the complete offline-first AI translation, voice synthesis, literacy, and legal/civic aid platform for the **Gofatho language (`ISO 639-3: gof`)** spoken across Sawla, Bulqi, Laha, Beto, Demba Gofa, Zala, and Oyda in the Gofa Zone, South Ethiopia Regional State.

* **6-Direction Dual-Script Translator**: Translate instantly across **Gofatho Latin (`Ooratha Caaquwa`)**, **Gofatho Ethiopic Fidel (`ኦራꬃ ጫቁዋ`)**, **Amharic**, and **English** with morphological root + suffix glossing (`Sellassie Cheru 2015`).
* **Offline FTS5 Dictionary & 2,072 Everyday Phrases**: Search 1,334 verified headwords, 2,072 domain phrases, and 75 `Minniyaa vs. Leppiya` consonant gemination minimal pairs 100% offline.
* **Synchronized Audio Bible & Old Testament (`GFBLVF` / `GFBEVF`)**: Read and listen to 7,931 New Testament verses, 22,017 sub-verse audio slices, and 120 quad-parallel Old Testament chapters.
* **Grade 8–10 `Meeze` Interactive Exam & Ometo Cognate Bridge**: Practice 250 auto-graded curriculum questions and compare 120 cognates across `Gofatho`, `Gamotho`, `Dawuro`, and `Wolaytta`.

---

## 3. Exact Answers for Google Play Console "Data Safety" & "App Content" Forms

| Google Play Console Questionnaire Section | Question | Exact Selection to Click |
| :--- | :--- | :--- |
| **Data Safety -> Data Collection** | Does your app collect or share any of the required user data types? | **Yes** (Optional community translation feedback and optional voice audio when using cloud ASR) |
| **Data Safety -> Encryption** | Is all of the user data collected by your app encrypted in transit? | **Yes** (HTTPS TLS 1.3 to Hugging Face Spaces & Google Gemini API) |
| **Data Safety -> Data Deletion** | Do you provide a way for users to request that their data is deleted? | **Yes** (Users can clear local SQLite history in-app or request deletion of submitted Woreda dialect feedback) |
| **Data Safety -> Audio Files** | Voice or sound recordings | **Collected optionally, processed ephemerally for speech-to-text transcription, never sold or shared with third parties** |
| **App Access** | All functionality is available without special access? | **Yes — All core translation, dictionary, quiz, legal aid, and offline TTS features work immediately without sign-in** |
| **Ads** | Does your app contain ads? | **No, my app does not contain ads** |
| **Target Audience & Content Rating** | Target Age Group / IARC Category | **13+ and Everyone (Reference / Educational / Dictionary utility with zero violence or restricted content)** |
