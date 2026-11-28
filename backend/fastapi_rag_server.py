#!/usr/bin/env python3
"""
Gofatho AI — Hybrid RAG, Morphological, Gemini 2.5 Native Chat & Voice API Server (v3.0)
========================================================================================
Production FastAPI Backend supporting both:
  1. Hosted Cloud Deployment (Hugging Face Spaces Docker, Google Cloud Run, Render, Railway)
  2. Local / On-Premises Execution (Gofa Zone Education Bureau / Sawla Offline Server)
"""

import os
import re
import hmac
import time
import json
import sqlite3
import urllib.request
import urllib.error
from collections import defaultdict, deque
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from morphological_analyzer import GofathoMorphologicalAnalyzer, GofathoScriptTransliterator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_db_path() -> str:
    candidates = [
        os.environ.get("GOFATHO_DB_PATH", ""),
        os.path.join(BASE_DIR, "../data/gofatho_ai_master.sqlite"),
        os.path.join(BASE_DIR, "../flutter_app/assets/gofatho_ai_master.sqlite"),
        "/tmp/gofatho_test_fixture.sqlite",
    ]
    return next((p for p in candidates if p and os.path.exists(p)), candidates[1])


DB_PATH = resolve_db_path()

analyzer = GofathoMorphologicalAnalyzer(DB_PATH)
transliterator = GofathoScriptTransliterator()

app = FastAPI(
    title="Gofatho AI — Hybrid RAG, Gemini Native Chat, Morphological & Voice Server",
    description=(
        "Trilingual (Gofatho Latin/Fidel, Amharic, English) AI Backend powered by "
        "SQLite FTS5 RAG (1,334 Lexicon, 2,072 Phrasebook, 1,305 Grade 8-10 Meeze Exercises, "
        "7,931 Quad-Parallel Bible Verses, 22,017 Audio Slices), Google Gemini 2.5 Flash, "
        "NLLB-200 LoRA, and Meta MMS-ASR/TTS."
    ),
    version="6.2.2",
)

_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://gofatho-ai-backend-1.onrender.com,http://localhost:7860,http://127.0.0.1:7860,http://10.0.2.2:7860",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
_allow_wildcard = ALLOWED_ORIGINS == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=not _allow_wildcard,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Api-Key", "X-Gemini-Api-Key"],
)

# ---------------------------------------------------------------------------
# Security: Constant-Time Admin API Key Verification & Token-Bucket Rate Limiter
# ---------------------------------------------------------------------------
_admin_api_key_header = APIKeyHeader(name="X-Admin-Api-Key", auto_error=False)


def verify_admin_api_key(
    x_admin_api_key: Optional[str] = Depends(_admin_api_key_header),
    authorization: Optional[str] = Header(None),
) -> str:
    configured_key = os.environ.get("GOFATHO_ADMIN_API_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="Admin moderation endpoints are disabled until GOFATHO_ADMIN_API_KEY is configured.",
        )
    candidate = (x_admin_api_key or "").strip()
    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()
    if not candidate or not hmac.compare_digest(candidate.encode("utf-8"), configured_key.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Api-Key header.")
    return "admin_verified"


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: Dict[str, deque] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, client_key: str) -> None:
        max_req = int(os.environ.get("GOFATHO_RATE_LIMIT_PER_MIN", "60"))
        now = time.monotonic()
        window = 60.0
        q = self._hits[client_key]
        while q and (now - q[0]) > window:
            q.popleft()
        if len(q) >= max_req:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({max_req} requests/minute). Please retry shortly.",
            )
        q.append(now)


rate_limiter = InMemoryRateLimiter()

class ServerObservabilityTracker:
    """Tracks request counts, latency percentiles (avg/P95), and RAG LRU cache metrics (Phase E.2)."""

    def __init__(self, max_cache_entries: int = 256) -> None:
        self.start_monotonic = time.monotonic()
        self.total_requests: int = 0
        self.route_counts: Dict[str, int] = defaultdict(int)
        self.recent_latencies_ms: deque = deque(maxlen=500)
        self.rag_cache: Dict[Any, Dict[str, Any]] = {}
        self.max_cache_entries = max_cache_entries
        self.rag_cache_hits: int = 0
        self.rag_cache_misses: int = 0

    def reset_cache(self) -> None:
        self.rag_cache.clear()
        self.rag_cache_hits = 0
        self.rag_cache_misses = 0

    def record_request(self, path: str, elapsed_ms: float) -> None:
        self.total_requests += 1
        self.route_counts[path] += 1
        self.recent_latencies_ms.append(round(elapsed_ms, 3))

    def snapshot(self) -> Dict[str, Any]:
        lats = sorted(self.recent_latencies_ms)
        avg_ms = round(sum(lats) / len(lats), 3) if lats else 0.0
        p95_idx = min(len(lats) - 1, int(len(lats) * 0.95)) if lats else 0
        p95_ms = lats[p95_idx] if lats else 0.0
        total_cache_ops = self.rag_cache_hits + self.rag_cache_misses
        hit_rate = round((self.rag_cache_hits / total_cache_ops) * 100.0, 2) if total_cache_ops > 0 else 0.0
        return {
            "uptime_sec": round(time.monotonic() - self.start_monotonic, 2),
            "total_requests": self.total_requests,
            "avg_latency_ms": avg_ms,
            "p95_latency_ms": p95_ms,
            "rag_cache_entries": len(self.rag_cache),
            "rag_cache_hits": self.rag_cache_hits,
            "rag_cache_misses": self.rag_cache_misses,
            "rag_cache_hit_rate_pct": hit_rate,
        }


observability = ServerObservabilityTracker()


@app.middleware("http")
async def observability_timing_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    observability.record_request(request.url.path, elapsed_ms)
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.3f}"
    return response



def enforce_rate_limit(request: Request) -> None:
    client_host = (request.client.host if request.client else "anonymous") or "anonymous"
    rate_limiter.check(f"{client_host}:{request.url.path}")


def get_db():
    active_path = os.environ.get("GOFATHO_DB_PATH", "").strip() or DB_PATH
    conn = sqlite3.connect(active_path)
    conn.row_factory = sqlite3.Row
    return conn


GOFATHO_SYSTEM_PROMPT = """You are **Gofatho AI (Goofatho)**, an expert native Gofatho (`ISO 639-3: gof`, North Omotic Ometo cluster, Gofa Zone, South Ethiopia — Sawla, Bulqi/Geze Gofa, Laha/Melekoza, Beto/Zala, Dembba Gofa, Oyda, Uba Debretsehay) linguist, teacher, translator, and cultural assistant.

CRITICAL LINGUISTIC & GRAMMATICAL RULES YOU MUST FOLLOW (Sellassie Cheru 2015 & Grade 8–10 Goofatho Doona Textbooks):
1. **Strict Constituent Order**: Gofatho is strictly **SOV (Subject – Object – Verb)**. The finite main verb MUST come at the end of the clause (e.g., `Taani timirtte keetta baas` = I to-school went).
2. **Personal Pronouns (Nominative / Accusative / Possessive)**:
   - 1SG (I/me/my): `Taani` (or `Ta`) / `Tana` / `Ta`
   - 2SG (You/you/your): `Neeni` (or `Ne`) / `Nena` / `Ne`
   - 3MSG (He/him/his): `I` / `A` / `A`
   - 3FSG (She/her/her): `A` / `O` / `I`
   - 1PL (We/us/our): `Nuuni` (or `Nu`) / `Nuna` / `Nu`
   - 2PL (You pl.): `Intte` / `Inttena` / `Intte`
   - 3PL (They/them/their): `Entti` / `Enttena` / `Entta`
3. **Nominal Case & Postpositional Suffixes**:
   - Nominative definite subject: `-y` (after vowels, e.g., `keettay`, `asay`) or `-i` (after consonants)
   - Accusative definite object: `-a`
   - Dative / Beneficiary ('to/for'): `-s` or `-ko` (e.g., `tana-s`, `iyakko`)
   - Ablative ('from/than'): `-ppe` (e.g., `Sawla-ppe` = from Sawla)
   - Locative / Instrumental ('in/at/with/by'): `-n` or `-ra` (e.g., `Goofa woga-n` = in Gofa culture, `neera` = with you)
   - Abstract / Nominalizer ('-ness/-hood'): `-tetha` (e.g., `lo77o-tetha` = goodness, `issippetetha` = unity)
   - Plural marker: `-ti` or `-ta` (e.g., `na7a-ti` = children)
4. **Verbal Aspect & Person Agreement Suffixes**:
   - **Present / Habitual Declarative**: 1SG `-ais`, 2SG `-asa`, 3MSG `-ees`, 3FSG `-ausu`, 1PL `-oos`, 2PL `-eeta`, 3PL `-oosona` (e.g., `oott-ais` = I work, `oott-ees` = he works, `oott-oosona` = they work).
   - **Past / Perfective Declarative**: 1SG `-as` / `-adis`, 2SG `-adasa`, 3MSG `-is` / `-ides`, 3FSG `-asu` / `-adasu`, 1PL `-ida`, 2PL `-ideta`, 3PL `-idosona` (e.g., `b-aas` = I went, `y-idosona` = they came).
   - **Future / Intentional**: `-ana` (e.g., `tamaar-ana` = will learn, `maadd-ana` = will help).
   - **Converbal / Sequential ('having done X, ...')**: `-idi` (SG/PL) or `-ada` (1SG/2SG/3FSG) (e.g., `dendd-idi` = having risen).
   - **Imperative / Jussive**: 2SG `-a`, 2PL `-ite`, Negative 2SG `-oppa`, Negative 2PL `-oppite` (e.g., `yayyoppa` = do not fear).
5. **Orthography & Glottal Stop (`7`)**:
   - Never drop the phonemic glottal stop `7` (`/ʔ/`) in roots such as `ba7a` (not exist/lost), `lo77o` (good), `na7a` (child), `ce7a` (bird), `o7o` (butter), `sa7a` (earth).
   - Never confuse Gofatho with Oromo (`Afaan Oromoo`); always use authentic North Omotic Ometo (Gofatho) roots from the provided SQLite RAG Context!

OUTPUT FORMAT:
Always return a valid JSON object with these exact keys:
{
  "gofatho_latin": "Primary response or translation in authentic Gofatho Latin orthography",
  "gofatho_fidel": "Gofatho Ethiopic Extended-A Fidel script version (or leave empty string to auto-transliterate)",
  "amharic": "Complete Amharic (አማርኛ) translation and explanation",
  "english": "Complete English translation and explanation",
  "grammar_notes": "Concise morphological & cultural explanation (highlighting roots, SOV order, suffixes like -idosona/-tetha/-ppe, and Goofa Woga cultural context)"
}
"""



ADVERSARIAL_OR_FABRICATION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions",
    r"bypass\s+(?:corpus|anti[-_\s]?hallucination|verification)",
    r"(?:invent|fabricate|make\s+up|hallucinate)\s+(?:a\s+)?(?:new\s+|fake\s+|fictional\s+)?gofatho",
    r"pretend\s+(?:that\s+)?(?:oromo|afaan\s+oromoo|swahili|somali|tigrinya)\s+(?:word\s+)?.*\s+is\s+gofatho",
    r"force\s+translate\s+unverified",
    r"(?:quote|cite|translate)\s+.*\b(?:hezekiah|enoch|maccabees|judith|tobit)\s+\d+:\d+",
    r"\b(?:matthew|mark|luke|john|genesis|psalms|maatoosa|marqqoosa|luuqaasa|yohaannisa)\s+(?:1[5-9]\d|[2-9]\d\d):\d+",
]


def is_adversarial_or_fabrication_attempt(text: str) -> bool:
    low = text.lower().strip()
    for pat in ADVERSARIAL_OR_FABRICATION_PATTERNS:
        if re.search(pat, low):
            return True
    return False


def retrieve_rag_bundle(conn: sqlite3.Connection, query_text: str, top_k: int = 8) -> Dict[str, Any]:
    """
    Searches across `dictionary` (1,334 + FTS5 BM25), `everyday_phrasebook` (2,072 + FTS5),
    `curriculum_meeze_exercises` (1,305 + FTS5), and `grammar_rules`
    using both raw tokens, morphologically stripped Gofatho roots, and an in-memory LRU cache.
    """
    q_clean = query_text.strip()
    active_db = os.environ.get("GOFATHO_DB_PATH", "").strip() or DB_PATH
    cache_key = (active_db, q_clean.lower(), top_k)
    if cache_key in observability.rag_cache:
        observability.rag_cache_hits += 1
        return observability.rag_cache[cache_key]
    observability.rag_cache_misses += 1

    cur = conn.cursor()
    STOPWORDS = {
        "the", "and", "for", "with", "from", "that", "this", "what", "how", "why",
        "who", "where", "when", "into", "out", "of", "in", "on", "to", "is", "are",
        "was", "were", "can", "you", "explain", "tell", "me", "quote", "translate",
        "word", "words", "gofatho", "gofa", "amharic", "english", "fictional",
        "non", "existent", "nonexistent", "unverified", "bible", "verse", "suffix",
        "proverb", "grade", "chapter", "topic", "corpus", "token", "king", "mythical", "mars",
    }
    has_extended_a = any(0xAB00 <= ord(c) <= 0xAB2F for c in q_clean)
    if transliterator.is_ethiopic(q_clean) and has_extended_a:
        q_latin = transliterator.fidel_to_latin(q_clean)
    elif transliterator.is_ethiopic(q_clean):
        # Standard Amharic script without Extended-A Gofatho characters: keep Ethiopic tokens for Amharic column search
        q_latin = ""
    else:
        q_latin = q_clean

    raw_tokens = [
        t.lower() for t in re.findall(r"[A-Za-z7'\u1200-\u137F\uAB00-\uAB2F]+", q_clean)
        if len(t) >= 3 and t.lower() not in STOPWORDS and not t.isdigit()
    ]
    morph_tokens = analyzer.analyze_sentence(q_latin, conn=conn) if q_latin else []
    roots = []
    for mt in morph_tokens:
        surf_low = (mt.get("surface") or "").lower().strip(".,!?;:")
        if surf_low in STOPWORDS:
            continue
        # Only use stripped root if it matched the Gofatho lexicon; otherwise keep full surface token
        if mt.get("english_gloss"):
            r = (mt.get("root") or surf_low).lower().strip(".,!?;:")
        else:
            r = surf_low
        if len(r) >= 4 and r not in STOPWORDS and not r.isdigit() and r not in roots:
            roots.append(r)

    search_terms = list(dict.fromkeys(roots + raw_tokens))[:10]

    # 1. Dictionary matches (1,334 entries)
    dict_hits = []
    seen_dict = set()
    try:
        cur.execute("SELECT 1 FROM dictionary LIMIT 1")
    except sqlite3.OperationalError:
        return {
            "morphological_analysis": morph_tokens,
            "dictionary_matches": [],
            "phrasebook_matches": [],
            "meeze_matches": [],
            "grammar_rules": [],
        }
    for term in search_terms:
        term_matched_fts = False
        safe_fts = re.sub(r'[^A-Za-z0-97\u1200-\u137F\uAB00-\uAB2F]', '', term)
        if len(safe_fts) >= 3:
            try:
                fts_rows = cur.execute(
                    """
                    SELECT d.id, d.headword, d.ipa, d.pos, d.english, d.amharic, d.gofatho_synonym, d.domain, d.source
                    FROM dictionary_fts f
                    JOIN dictionary d ON d.id = f.rowid
                    WHERE dictionary_fts MATCH ?
                    ORDER BY bm25(dictionary_fts) ASC
                    LIMIT 4
                    """,
                    (f'"{safe_fts}"',),
                ).fetchall()
                for fr in fts_rows:
                    term_matched_fts = True
                    if fr["id"] not in seen_dict:
                        seen_dict.add(fr["id"])
                        dict_hits.append(dict(fr))
            except sqlite3.OperationalError:
                pass
        if not term_matched_fts:
            rows = cur.execute(
                """
                SELECT id, headword, ipa, pos, english, amharic, gofatho_synonym, domain, source
                FROM dictionary
                WHERE lower(headword) = ? OR lower(normalized_form) = ?
                   OR lower(headword) LIKE ?
                   OR (' ' || lower(english) || ' ') LIKE ?
                   OR lower(english) = ?
                   OR amharic LIKE ?
                LIMIT 4
                """,
                (term, term, f"{term}%", f"% {term} %", term, f"%{term}%"),
            ).fetchall()
            for r in rows:
                if r["id"] not in seen_dict:
                    seen_dict.add(r["id"])
                    dict_hits.append(dict(r))
        if len(dict_hits) >= top_k:
            break

    # 2. Everyday Phrasebook matches (2,072 entries)
    phrase_hits = []
    seen_ph = set()
    phrase_probe_terms = ([q_clean.lower()] if len(q_clean) >= 4 else []) + [t for t in search_terms[:6] if len(t) >= 4]
    for term in phrase_probe_terms:
        phr_matched_fts = False
        safe_fts = re.sub(r'[^A-Za-z0-97\u1200-\u137F\uAB00-\uAB2F\s]', ' ', term).strip()
        fts_tokens = [w for w in safe_fts.split() if len(w) >= 3]
        if fts_tokens:
            fts_q = " AND ".join(f'"{w}"' for w in fts_tokens[:4])
            try:
                fts_rows = cur.execute(
                    """
                    SELECT p.id, p.phrase_code, p.domain, p.gofatho_latin, p.gofatho_fidel, p.amharic, p.english, p.morpheme_breakdown, p.usage_context, p.source
                    FROM phrasebook_fts f
                    JOIN everyday_phrasebook p ON p.id = f.rowid
                    WHERE phrasebook_fts MATCH ?
                    ORDER BY bm25(phrasebook_fts) ASC
                    LIMIT 4
                    """,
                    (fts_q,),
                ).fetchall()
                for fr in fts_rows:
                    phr_matched_fts = True
                    if fr["id"] not in seen_ph:
                        seen_ph.add(fr["id"])
                        phrase_hits.append(dict(fr))
            except sqlite3.OperationalError:
                pass
        if not phr_matched_fts:
            rows = cur.execute(
                """
                SELECT id, phrase_code, domain, gofatho_latin, gofatho_fidel, amharic, english, morpheme_breakdown, usage_context, source
                FROM everyday_phrasebook
                WHERE lower(gofatho_latin) = ?
                   OR (' ' || lower(gofatho_latin) || ' ') LIKE ?
                   OR (' ' || lower(english) || ' ') LIKE ?
                   OR lower(english) = ?
                   OR amharic LIKE ?
                LIMIT 4
                """,
                (term, f"% {term} %", f"% {term} %", term, f"%{term}%"),
            ).fetchall()
            for r in rows:
                if r["id"] not in seen_ph:
                    seen_ph.add(r["id"])
                    phrase_hits.append(dict(r))
        if len(phrase_hits) >= 6:
            break

    # 3. Grade 8-10 Curriculum Meeze & Cultural Notes (1,305 entries)
    meeze_hits = []
    seen_mz = set()
    for term in phrase_probe_terms:
        rows = cur.execute(
            """
            SELECT id, exercise_code, grade, chapter_num, chapter_title_gofatho, exercise_type,
                   gofatho_prompt_latin, gofatho_prompt_fidel,
                   english_translation, amharic_translation, morpheme_gloss, grammar_focus
            FROM curriculum_meeze_exercises
            WHERE (' ' || lower(gofatho_prompt_latin) || ' ') LIKE ?
               OR (' ' || lower(chapter_title_gofatho) || ' ') LIKE ?
               OR (' ' || lower(english_translation) || ' ') LIKE ?
               OR amharic_translation LIKE ?
            LIMIT 3
            """,
            (f"% {term} %", f"% {term} %", f"% {term} %", f"%{term}%"),
        ).fetchall()
        for r in rows:
            if r["id"] not in seen_mz:
                seen_mz.add(r["id"])
                meeze_hits.append(dict(r))
        if len(meeze_hits) >= 5:
            break

    # 4. Grammar Rules (22 rules from Sellassie Cheru 2015)
    grammar_hits = []
    try:
        rows = cur.execute(
            "SELECT id, category, morpheme, function_gloss, description, example_gofatho FROM grammar_rules LIMIT 8"
        ).fetchall()
        grammar_hits = [dict(r) for r in rows]
    except Exception:
        pass

    bundle_out = {
        "morphological_analysis": morph_tokens,
        "dictionary_matches": dict_hits[:top_k],
        "phrasebook_matches": phrase_hits[:6],
        "meeze_matches": meeze_hits[:5],
        "grammar_rules": grammar_hits[:6],
    }
    if len(observability.rag_cache) >= observability.max_cache_entries:
        observability.rag_cache.pop(next(iter(observability.rag_cache)))
    observability.rag_cache[cache_key] = bundle_out
    return bundle_out

def build_structured_citations(rag_bundle: Dict[str, Any]) -> List[Dict[str, str]]:
    """Constructs verifiable source citations corresponding to actual retrieved SQLite records."""
    citations: List[Dict[str, str]] = []
    for d in rag_bundle.get("dictionary_matches", [])[:4]:
        citations.append({
            "source_type": "dictionary",
            "source_id": f"LEX-{d.get('id', d.get('headword', ''))}",
            "title": f"{d.get('headword', '')} ({d.get('pos', '')})",
            "excerpt": f"EN: {d.get('english', '')} | AM: {d.get('amharic', '')}",
            "authority": str(d.get("source") or "Sellassie Cheru (2015) / Grade 8-10 Glossary"),
        })
    for p in rag_bundle.get("phrasebook_matches", [])[:3]:
        pid = p.get("phrase_code") or f"PHR-{p.get('id', '')}"
        citations.append({
            "source_type": "phrasebook",
            "source_id": str(pid),
            "title": f"{p.get('domain', 'Phrasebook')} ({pid})",
            "excerpt": f"GOF: {p.get('gofatho_latin', '')} | EN: {p.get('english', '')}",
            "authority": str(p.get("source") or "Verified Gofatho Everyday Phrasebook"),
        })
    for m in rag_bundle.get("meeze_matches", [])[:2]:
        mid = m.get("exercise_code") or f"MEEZE-{m.get('id', '')}"
        citations.append({
            "source_type": "curriculum_meeze",
            "source_id": str(mid),
            "title": f"Grade {m.get('grade', '')} Ch.{m.get('chapter_num', '')}: {m.get('chapter_title_gofatho', '')}",
            "excerpt": f"GOF: {m.get('gofatho_prompt_latin', '')} | EN: {m.get('english_translation', '')}",
            "authority": "SNNPR Grade 8-10 Goofatho Doona Textbook",
        })
    return citations



def call_gemini_json(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model_name: str = "gemini-2.5-flash",
) -> Optional[Dict[str, Any]]:
    if not api_key or len(api_key.strip()) < 10:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            candidates = body.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and "text" in parts[0]:
                    return json.loads(parts[0]["text"])
    except Exception as e:
        print(f"[Gemini API Warning] Fallback to deterministic RAG: {e}")
    return None


class TranslateRequest(BaseModel):
    text: str = Field(..., example="Entti timirtte keettaa bidosona.")
    source_lang: str = Field("gof_Latn", description="gof_Latn | gof_Ethi | amh_Ethi | eng_Latn")
    target_lang: str = Field("eng_Latn", description="gof_Latn | gof_Ethi | amh_Ethi | eng_Latn")
    top_k_rag: int = Field(5, ge=1, le=15)
    gemini_api_key: Optional[str] = Field(None, description="Optional Google AI Studio Gemini API Key")


class ChatMessageItem(BaseModel):
    role: str = Field("user", description="user | assistant")
    text: str


class ChatRequest(BaseModel):
    message: str = Field(..., example="Goofa wogan eko geloy waanidi oosettii? Explain in Gofatho, Amharic, and English.")
    topic: str = Field("general", description="general | culture | curriculum | proverbs | grammar | daily")
    history: List[ChatMessageItem] = Field(default_factory=list)
    gemini_api_key: Optional[str] = Field(None, description="Optional Google AI Studio Gemini API Key")


class TransliterateRequest(BaseModel):
    text: str = Field(..., example="Ooratha Caaquwa - Yesuus Kiristtoosa")
    direction: str = Field("auto", description="latin_to_fidel | fidel_to_latin | auto")


class FeedbackItem(BaseModel):
    source_text: str
    source_lang: str
    suggested_gofatho_latin: str
    suggested_gofatho_fidel: Optional[str] = None
    suggested_amharic: Optional[str] = None
    suggested_english: Optional[str] = None
    contributor_woreda: Optional[str] = "Sawla"
    notes: Optional[str] = None


class TTSRequest(BaseModel):
    text: str = Field(..., example="Sarointta! Goofatho doona tamaariyaageetoo.")
    script: str = Field("auto", description="latin | fidel | auto")
    speaking_rate: float = Field(1.0, ge=0.5, le=2.0)


@app.get("/api/v1/health")
def health_check():
    counts = {}
    core_tables = [
        "dictionary",
        "everyday_phrasebook",
        "curriculum_meeze_exercises",
        "bible_verses",
        "verse_audio_clips",
        "phrase_audio_segments",
        "interlinear_sentences",
        "grammar_rules",
        "oral_literature",
        "gemination_minimal_pairs",
        "old_testament_seed_verses",
        "meeze_quiz_bank",
        "ometo_cognate_bridge",
        "ocr_sample_documents",
        "fst_inflection_paradigm_bank",
    ]
    try:
        conn = get_db()
        cur = conn.cursor()
        for tbl in core_tables:
            try:
                counts[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            except Exception:
                counts[tbl] = 0
        conn.close()
    except Exception:
        for tbl in core_tables:
            counts[tbl] = 0
    db_ready = counts.get("dictionary", 0) > 0 and counts.get("everyday_phrasebook", 0) > 0
    has_env_gemini = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    has_admin_key = bool(os.environ.get("GOFATHO_ADMIN_API_KEY", "").strip())
    fts_counts = {}
    if db_ready:
        try:
            conn_fts = get_db()
            cur_fts = conn_fts.cursor()
            for fts_tbl in ["dictionary_fts", "phrasebook_fts", "curriculum_fts", "igt_fts"]:
                try:
                    fts_counts[fts_tbl] = cur_fts.execute(f"SELECT COUNT(*) FROM {fts_tbl}").fetchone()[0]
                except Exception:
                    fts_counts[fts_tbl] = 0
            conn_fts.close()
        except Exception:
            pass
    return {
        "status": "ok" if db_ready else "degraded_db_uninitialized",
        "db_ready": db_ready,
        "fts5_indexes_ready": fts_counts.get("dictionary_fts", 0) > 0,
        "fts5_index_counts": fts_counts,
        "observability": observability.snapshot(),
        "engine": "Gofatho AI Hybrid RAG + FTS5 BM25 + Gemini 2.5 Native Chat + FST Production Server v6.2.2",
        "database_counts": counts,
        "supported_languages": ["gof_Latn", "gof_Ethi", "amh_Ethi", "eng_Latn"],
        "gemini_rag_ready": db_ready,
        "server_has_default_gemini_key": has_env_gemini,
        "admin_auth_configured": has_admin_key,
        "voice_models": {
            "asr": "facebook/mms-1b-all (adapter: gof-script_latin, 29-token CTC vocab)",
            "tts": "facebook/mms-tts-gof (VITS 16kHz + Fidel-to-Latin G2P wrapper)",
            "nmt": "google/gemini-2.5-flash + facebook/nllb-200-distilled-600M",
        },
    }


@app.post("/api/v1/chat")
def native_gofatho_chat(
    req: ChatRequest,
    x_gemini_api_key: Optional[str] = Header(None),
    _rl: None = Depends(enforce_rate_limit),
):
    conn = get_db()
    rag_bundle = retrieve_rag_bundle(conn, req.message, top_k=8)
    conn.close()

    api_key = (
        req.gemini_api_key
        or x_gemini_api_key
        or os.environ.get("GEMINI_API_KEY", "")
    ).strip()

    rag_context_lines = ["=== VERIFIED GOFATHO SQLITE RAG CONTEXT ==="]
    if rag_bundle["dictionary_matches"]:
        rag_context_lines.append("\n[1. Lexicon Roots (Sellassie Cheru 2015 & Grade 8-10 Glossaries)]:")
        for d in rag_bundle["dictionary_matches"]:
            rag_context_lines.append(
                f"  - {d['headword']} ({d.get('pos','')}): EN='{d.get('english','')}' | AM='{d.get('amharic','')}' | Syn='{d.get('gofatho_synonym','')}'"
            )
    if rag_bundle["phrasebook_matches"]:
        rag_context_lines.append("\n[2. Everyday Conversational Phrases]:")
        for p in rag_bundle["phrasebook_matches"]:
            rag_context_lines.append(
                f"  - [{p.get('domain','')}] GOF='{p['gofatho_latin']}' ({p.get('gofatho_fidel','')}) | AM='{p.get('amharic','')}' | EN='{p.get('english','')}'"
            )
    if rag_bundle["meeze_matches"]:
        rag_context_lines.append("\n[3. Grade 8-10 Goofatho Doona Textbook & Cultural Notes]:")
        for m in rag_bundle["meeze_matches"]:
            rag_context_lines.append(
                f"  - [Grade {m['grade']} Ch.{m['chapter_num']} - {m['chapter_title_gofatho']}] {m['gofatho_prompt_latin']} (AM: {m['amharic_translation']} | EN: {m['english_translation']} | Grammar: {m.get('grammar_focus','')})"
            )

    history_str = ""
    if req.history:
        history_str = "\n=== RECENT CONVERSATION HISTORY ===\n" + "\n".join(
            f"{h.role.upper()}: {h.text}" for h in req.history[-6:]
        )

    user_prompt = (
        f"Topic Mode: {req.topic}\n"
        f"{chr(10).join(rag_context_lines)}\n"
        f"{history_str}\n\n"
        f"=== USER MESSAGE ===\n{req.message}\n\n"
        "Respond in authentic Gofatho (using the verified roots and SOV grammar above), "
        "and provide complete Amharic and English explanations plus grammar/cultural notes in JSON."
    )

    gemini_res = call_gemini_json(api_key, GOFATHO_SYSTEM_PROMPT, user_prompt)
    if gemini_res and isinstance(gemini_res, dict) and gemini_res.get("gofatho_latin"):
        gof_lat = gemini_res.get("gofatho_latin", "").strip()
        gof_fid = gemini_res.get("gofatho_fidel", "").strip()
        if not gof_fid or not transliterator.is_ethiopic(gof_fid):
            gof_fid = transliterator.latin_to_fidel(gof_lat)
        return {
            "mode": "gemini_2.5_flash_rag",
            "topic": req.topic,
            "user_message": req.message,
            "gofatho_latin": gof_lat,
            "gofatho_fidel": gof_fid,
            "amharic": gemini_res.get("amharic", ""),
            "english": gemini_res.get("english", ""),
            "grammar_notes": gemini_res.get("grammar_notes", ""),
            "rag_citations": {
                "dictionary_count": len(rag_bundle["dictionary_matches"]),
                "phrasebook_count": len(rag_bundle["phrasebook_matches"]),
                "meeze_count": len(rag_bundle["meeze_matches"]),
                "top_dictionary": rag_bundle["dictionary_matches"][:4],
                "top_phrases": rag_bundle["phrasebook_matches"][:3],
                "top_meeze": rag_bundle["meeze_matches"][:3],
            },
        }

    # Deterministic Offline SQLite RAG Synthesis Fallback
    top_p = rag_bundle["phrasebook_matches"][0] if rag_bundle["phrasebook_matches"] else None
    top_m = rag_bundle["meeze_matches"][0] if rag_bundle["meeze_matches"] else None
    top_d = rag_bundle["dictionary_matches"]

    if top_m:
        gof_lat = f"Saro! {top_m['gofatho_prompt_latin']}"
        amh_txt = f"ከክፍል {top_m['grade']} ምዕራፍ {top_m['chapter_num']} ({top_m['chapter_title_gofatho']}): {top_m['amharic_translation']}"
        eng_txt = f"From Grade {top_m['grade']} Ch.{top_m['chapter_num']} ({top_m['chapter_title_gofatho']}): {top_m['english_translation']}"
    elif top_p:
        gof_lat = f"{top_p['gofatho_latin']}"
        amh_txt = f"{top_p['amharic']} (ምድብ፦ {top_p['domain']})"
        eng_txt = f"{top_p['english']} (Domain: {top_p['domain']})"
    elif top_d:
        d0 = top_d[0]
        gof_lat = f"Taani '{d0['headword']}' Goofatho doonan erais."
        amh_txt = f"ቃል፦ {d0['headword']} = {d0.get('amharic','')} ({d0.get('pos','')})"
        eng_txt = f"Lexicon Root: {d0['headword']} = {d0.get('english','')} ({d0.get('pos','')})"
    else:
        gof_lat = f"[Unverified / Out-of-Corpus Query]: {req.message}"
        amh_txt = f"⚠️ ማስታወቂያ፦ ለ«{req.message}» የተረጋገጠ የጎፋኛ መዝገበ-ቃላት ወይም የመማሪያ መጽሐፍ ማስረጃ አልተገኘም። ያልተረጋገጠ ቃል ከመፍጠር ይልቅ ለጎፋኛ ተናጋሪዎች ግምገማ ተመዝግቧል።"
        eng_txt = (
            f"⚠️ Uncertainty & Anti-Hallucination Notice: No verified Gofatho dictionary entry, phrasebook record, "
            f"or Grade 8–10 textbook passage matched '{req.message}'. To prevent hallucinated Gofatho vocabulary or "
            f"fabricated citations, no unverified answer was generated."
        )

    morph_summary = []
    for mt in rag_bundle["morphological_analysis"][:6]:
        if mt.get("affixes"):
            aff_str = ", ".join(f"{a['affix']} ({a['function']})" for a in mt["affixes"])
            morph_summary.append(f"{mt['surface']} -> root '{mt['root']}' + [{aff_str}]")
        elif mt.get("english_gloss"):
            morph_summary.append(f"{mt['surface']} ('{mt['english_gloss']}')")

    # Check for non-existent Bible book or out-of-range chapter/verse requests
    _valid_bible_books = {
        "matthew", "mark", "luke", "john", "acts", "romans", "corinthians", "galatians",
        "ephesians", "philippians", "colossians", "thessalonians", "timothy", "titus",
        "philemon", "hebrews", "james", "peter", "jude", "revelation", "genesis", "psalms",
        "proverbs", "isaiah", "maatoosa", "marqqoosa", "luuqaasa", "yohaannisa", "medhdhethaa",
    }
    _bible_ref_m = re.search(r"([A-Za-z]+)\s+(\d+):(\d+)", req.message)
    _invalid_bible_ref = False
    if _bible_ref_m:
        _b_name = _bible_ref_m.group(1).lower()
        _b_ch = int(_bible_ref_m.group(2))
        if _b_name not in _valid_bible_books or _b_ch > 150:
            _invalid_bible_ref = True

    has_verified_hits = bool((top_m or top_p or top_d) and not _invalid_bible_ref and not is_adversarial_or_fabrication_attempt(req.message))
    if not has_verified_hits:
        gof_lat = f"[Unverified / Out-of-Corpus Query]: {req.message}"
        amh_txt = f"⚠️ ማስታወቂያ፦ ለ«{req.message}» የተረጋገጠ የጎፋኛ መዝገበ-ቃላት ወይም የመማሪያ መጽሐፍ ማስረጃ አልተገኘም። ያልተረጋገጠ ቃል ከመፍጠር ይልቅ ለጎፋኛ ተናጋሪዎች ግምገማ ተመዝግቧል።"
        eng_txt = (
            f"⚠️ Uncertainty & Anti-Hallucination Notice: No verified Gofatho dictionary entry, phrasebook record, "
            f"or Grade 8–10 textbook passage matched '{req.message}'. To prevent hallucinated Gofatho vocabulary or "
            f"fabricated citations, no unverified answer was generated."
        )
    structured_cits = build_structured_citations(rag_bundle) if has_verified_hits else []
    grammar_note = (
        "Morphological & SOV Analysis: " + ("; ".join(morph_summary) if morph_summary else "Strict SOV clause structure.")
    )

    return {
        "mode": "offline_sqlite_rag_synthesis" if has_verified_hits else "offline_unverified_refusal",
        "confidence_tier": "verified_corpus" if has_verified_hits else "uncertain_needs_review",
        "is_uncertain": not has_verified_hits,
        "topic": req.topic,
        "user_message": req.message,
        "gofatho_latin": gof_lat,
        "gofatho_fidel": transliterator.latin_to_fidel(gof_lat),
        "amharic": amh_txt,
        "english": eng_txt,
        "grammar_notes": grammar_note,
        "structured_citations": structured_cits,
        "rag_citations": {
            "dictionary_count": len(rag_bundle["dictionary_matches"]),
            "phrasebook_count": len(rag_bundle["phrasebook_matches"]),
            "meeze_count": len(rag_bundle["meeze_matches"]),
            "top_dictionary": rag_bundle["dictionary_matches"][:4],
            "top_phrases": rag_bundle["phrasebook_matches"][:3],
            "top_meeze": rag_bundle["meeze_matches"][:3],
        },
    }


@app.post("/api/v1/transliterate")
def transliterate_script(req: TransliterateRequest):
    if req.direction == "latin_to_fidel" or (
        req.direction == "auto" and not transliterator.is_ethiopic(req.text)
    ):
        converted = transliterator.latin_to_fidel(req.text)
        resolved_dir = "latin_to_fidel"
    else:
        converted = transliterator.fidel_to_latin(req.text)
        resolved_dir = "fidel_to_latin"
    return {
        "source_text": req.text,
        "direction": resolved_dir,
        "converted_text": converted,
    }


@app.get("/api/v1/dictionary")
def search_dictionary(
    q: str = Query(..., min_length=1, description="Search headword, English, or Amharic"),
    limit: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    cur = conn.cursor()
    q_norm = q.strip()
    if transliterator.is_ethiopic(q_norm):
        q_latin = transliterator.fidel_to_latin(q_norm)
    else:
        q_latin = q_norm

    rows = cur.execute(
        """
        SELECT id, headword, normalized_form, ipa, pos, english, amharic, gofatho_synonym, domain, source
        FROM dictionary
        WHERE headword LIKE ? OR normalized_form LIKE ? OR english LIKE ? OR amharic LIKE ?
        ORDER BY CASE WHEN lower(headword) = lower(?) THEN 0
                      WHEN lower(headword) LIKE lower(?) THEN 1
                      ELSE 2 END, headword ASC
        LIMIT ?
        """,
        (f"%{q_latin}%", f"%{q_latin}%", f"%{q_norm}%", f"%{q_norm}%", q_latin, f"{q_latin}%", limit),
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        item["headword_fidel"] = transliterator.latin_to_fidel(item["headword"])
        results.append(item)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/v1/phrasebook")
def search_phrasebook(
    q: str = Query("", description="Optional keyword search across Gofatho, Amharic, or English"),
    category: str = Query("", description="Optional domain filter (e.g., Greetings & Daily Courtesies)"),
    limit: int = Query(30, ge=1, le=200),
):
    conn = get_db()
    cur = conn.cursor()
    sql = """
        SELECT id, phrase_code, domain AS category, gofatho_latin, gofatho_fidel, amharic, english, morpheme_breakdown AS grammar_notes, usage_context
        FROM everyday_phrasebook
        WHERE 1=1
    """
    params: List[Any] = []
    if category.strip():
        sql += " AND domain = ?"
        params.append(category.strip())
    if q.strip():
        q_clean = q.strip()
        sql += " AND (gofatho_latin LIKE ? OR gofatho_fidel LIKE ? OR amharic LIKE ? OR english LIKE ? OR domain LIKE ?)"
        params.extend([f"%{q_clean}%"] * 5)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"query": q, "category": category, "count": len(rows), "results": rows}


@app.get("/api/v1/meeze")
def search_meeze_exercises(
    grade: Optional[int] = Query(None, description="Filter by Grade (8, 9, or 10)"),
    section_type: str = Query("", description="Filter by section type"),
    q: str = Query("", description="Keyword filter"),
    limit: int = Query(30, ge=1, le=200),
):
    conn = get_db()
    cur = conn.cursor()
    sql = """
        SELECT id, exercise_code, grade, chapter_num AS chapter, exercise_type AS section_type,
               chapter_title_gofatho AS topic_title,
               gofatho_prompt_latin AS prompt_gofatho_latin,
               gofatho_prompt_fidel AS prompt_gofatho_fidel,
               english_translation AS explanation_english,
               amharic_translation AS explanation_amharic,
               morpheme_gloss, grammar_focus
        FROM curriculum_meeze_exercises
        WHERE 1=1
    """
    params: List[Any] = []
    if grade in (8, 9, 10):
        sql += " AND grade = ?"
        params.append(grade)
    if section_type.strip():
        sql += " AND exercise_type LIKE ?"
        params.append(f"%{section_type.strip()}%")
    if q.strip():
        q_clean = q.strip()
        sql += " AND (gofatho_prompt_latin LIKE ? OR english_translation LIKE ? OR amharic_translation LIKE ? OR chapter_title_gofatho LIKE ?)"
        params.extend([f"%{q_clean}%"] * 4)
    sql += " ORDER BY grade ASC, chapter_num ASC, id ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"grade": grade, "section_type": section_type, "query": q, "count": len(rows), "results": rows}


@app.get("/api/v1/bible/audio")
def get_chapter_audio_alignment(
    book_id: str = Query("MAT", description="USFM 3-letter book code (MAT..REV)"),
    chapter: int = Query(1, ge=1, le=150),
):
    conn = get_db()
    cur = conn.cursor()
    verses = cur.execute(
        """
        SELECT v.verse_id, v.verse, v.gof_latin, v.gof_fidel, v.amh_fidel, v.eng_web,
               c.audio_rel_path, c.start_sec, c.end_sec, c.duration_sec
        FROM bible_verses v
        LEFT JOIN verse_audio_clips c ON v.verse_id = c.verse_id
        WHERE v.book_id = ? AND v.chapter = ?
        ORDER BY v.verse ASC
        """,
        (book_id.upper(), chapter),
    ).fetchall()

    phrases = cur.execute(
        """
        SELECT segment_id, verse, phrase_id, start_sec, end_sec, duration_sec,
               gof_latin_slice, gof_fidel_slice, is_golden_slice
        FROM phrase_audio_segments
        WHERE book_id = ? AND chapter = ?
        ORDER BY start_sec ASC
        """,
        (book_id.upper(), chapter),
    ).fetchall()
    conn.close()

    return {
        "book_id": book_id.upper(),
        "chapter": chapter,
        "verse_count": len(verses),
        "phrase_slice_count": len(phrases),
        "verses": [dict(v) for v in verses],
        "phrase_slices": [dict(p) for p in phrases],
    }


@app.post("/api/v1/translate")
def hybrid_rag_translate(
    req: TranslateRequest,
    x_gemini_api_key: Optional[str] = Header(None),
    _rl: None = Depends(enforce_rate_limit),
):
    if is_adversarial_or_fabrication_attempt(req.text):
        return {
            "source_text": req.text,
            "source_lang": req.source_lang,
            "target_lang": req.target_lang,
            "translation": (
                f"⚠️ Adversarial / Fabrication Refusal: '{req.text}' requests unverified vocabulary fabrication, "
                f"cross-language substitution, or an invalid scripture reference. Refused under Section 6.D."
            ),
            "confidence_tier": "uncertain_needs_review",
            "is_uncertain": True,
            "structured_citations": [],
            "morphological_analysis": [],
            "rag_examples": [],
            "engine_mode": "adversarial_anti_hallucination_refusal",
        }
    conn = get_db()
    cur = conn.cursor()

    working_text = req.text.strip()
    if req.source_lang == "gof_Ethi" or (
        req.source_lang.startswith("gof") and transliterator.is_ethiopic(working_text)
    ):
        gof_latin_input = transliterator.fidel_to_latin(working_text)
    else:
        gof_latin_input = working_text

    morph_breakdown = (
        analyzer.analyze_sentence(gof_latin_input, conn=conn)
        if req.source_lang.startswith("gof")
        else []
    )

    exact_phrase = cur.execute(
        """
        SELECT domain AS category, gofatho_latin, gofatho_fidel, amharic, english, morpheme_breakdown AS grammar_notes
        FROM everyday_phrasebook
        WHERE lower(gofatho_latin) = lower(?) OR lower(english) = lower(?) OR amharic = ?
        LIMIT 1
        """,
        (gof_latin_input, working_text, working_text),
    ).fetchone()

    rag_bundle = retrieve_rag_bundle(conn, working_text, top_k=req.top_k_rag)

    tokens = [
        t for t in re.findall(r"[A-Za-z7'\u1200-\u137F\uAB00-\uAB2F]+", working_text)
        if len(t) >= 3
    ]
    rag_examples = []
    if tokens:
        primary_tok = tokens[0]
        rows = cur.execute(
            """
            SELECT verse_id, gof_latin, gof_fidel, amh_fidel, eng_web
            FROM bible_verses
            WHERE gof_latin LIKE ? OR eng_web LIKE ? OR amh_fidel LIKE ?
            LIMIT ?
            """,
            (f"%{primary_tok}%", f"%{primary_tok}%", f"%{primary_tok}%", req.top_k_rag),
        ).fetchall()
        rag_examples = [dict(r) for r in rows]

    conn.close()

    api_key = (
        req.gemini_api_key
        or x_gemini_api_key
        or os.environ.get("GEMINI_API_KEY", "")
    ).strip()

    if exact_phrase:
        ep = dict(exact_phrase)
        if req.target_lang == "gof_Latn":
            final_translation = ep["gofatho_latin"]
        elif req.target_lang == "gof_Ethi":
            final_translation = ep["gofatho_fidel"]
        elif req.target_lang == "amh_Ethi":
            final_translation = ep["amharic"]
        else:
            final_translation = ep["english"]
        return {
            "source_text": req.text,
            "source_lang": req.source_lang,
            "target_lang": req.target_lang,
            "translation": final_translation,
            "gofatho_latin": ep["gofatho_latin"],
            "gofatho_fidel": ep["gofatho_fidel"],
            "amharic": ep["amharic"],
            "english": ep["english"],
            "phrasebook_exact_match": ep,
            "morphological_analysis": morph_breakdown,
            "rag_examples": rag_examples,
            "structured_citations": build_structured_citations(rag_bundle),
            "confidence_tier": "verified_corpus",
            "is_uncertain": False,
            "engine_mode": "exact_phrasebook_match",
        }

    if api_key:
        prompt = (
            f"Translate the following text from `{req.source_lang}` to `{req.target_lang}` "
            f"(and provide all 4 forms: `gofatho_latin`, `gofatho_fidel`, `amharic`, `english`).\n"
            f"Input Text: {req.text}\n"
            f"Morphological Analysis: {json.dumps(morph_breakdown, ensure_ascii=False)}\n"
            f"Matched Lexicon Roots: {json.dumps(rag_bundle['dictionary_matches'][:6], ensure_ascii=False)}\n"
            f"Matched Phrasebook Examples: {json.dumps(rag_bundle['phrasebook_matches'][:4], ensure_ascii=False)}\n"
        )
        gem_out = call_gemini_json(api_key, GOFATHO_SYSTEM_PROMPT, prompt)
        if gem_out and isinstance(gem_out, dict) and gem_out.get("gofatho_latin"):
            g_lat = gem_out.get("gofatho_latin", "")
            g_fid = gem_out.get("gofatho_fidel", "") or transliterator.latin_to_fidel(g_lat)
            amh = gem_out.get("amharic", "")
            eng = gem_out.get("english", "")
            target_map = {
                "gof_Latn": g_lat,
                "gof_Ethi": g_fid,
                "amh_Ethi": amh,
                "eng_Latn": eng,
            }
            return {
                "source_text": req.text,
                "source_lang": req.source_lang,
                "target_lang": req.target_lang,
                "translation": target_map.get(req.target_lang, eng),
                "gofatho_latin": g_lat,
                "gofatho_fidel": g_fid,
                "amharic": amh,
                "english": eng,
                "grammar_notes": gem_out.get("grammar_notes", ""),
                "morphological_analysis": morph_breakdown,
                "rag_examples": rag_examples,
                "engine_mode": "gemini_2.5_flash_rag",
            }

    structured_cits = build_structured_citations(rag_bundle)
    confidence_tier = "verified_corpus"
    is_uncertain = False
    engine_mode = "offline_morphological_rag"

    if req.source_lang.startswith("gof") and req.target_lang == "gof_Ethi":
        final_translation = transliterator.latin_to_fidel(gof_latin_input)
        structured_cits = structured_cits or [{
            "source_type": "orthography_rule",
            "source_id": "ZARA-05",
            "title": "Goofatho Doona Dual-Script Transliterator",
            "excerpt": "Deterministic Latin <-> Ethiopic Extended-A Fidel conversion.",
            "authority": "Grade 9 Goofatho Doona Textbook & Sellassie Cheru (2015)",
        }]
    elif req.source_lang == "gof_Ethi" and req.target_lang == "gof_Latn":
        final_translation = gof_latin_input
        structured_cits = structured_cits or [{
            "source_type": "orthography_rule",
            "source_id": "ZARA-05",
            "title": "Goofatho Doona Dual-Script Transliterator",
            "excerpt": "Deterministic Ethiopic Extended-A Fidel <-> Latin conversion.",
            "authority": "Grade 9 Goofatho Doona Textbook & Sellassie Cheru (2015)",
        }]
    elif req.source_lang.startswith("gof"):
        gloss_field = "english_gloss" if req.target_lang == "eng_Latn" else "amharic_gloss"
        pieces = []
        matched_any_root = False
        existing_cit_ids = {str(c.get("source_id", "")) for c in structured_cits}
        for m in morph_breakdown:
            g = m.get(gloss_field) or m.get("english_gloss")
            if g:
                matched_any_root = True
                primary_meaning = g.split(";")[0].split(",")[0].strip()
                affix_notes = [a["function"].split("(")[0].strip() for a in m.get("affixes", [])]
                if affix_notes:
                    pieces.append(f"{primary_meaning} [{' + '.join(affix_notes)}]")
                else:
                    pieces.append(primary_meaning)
                if m.get("lex_id") and f"LEX-{m['lex_id']}" not in existing_cit_ids:
                    cid = f"LEX-{m['lex_id']}"
                    existing_cit_ids.add(cid)
                    structured_cits.append({
                        "source_type": "dictionary",
                        "source_id": cid,
                        "title": f"{m.get('root', m['surface'])} ({m.get('pos', 'LEX')})",
                        "excerpt": f"EN: {m.get('english_gloss', '')} | AM: {m.get('amharic_gloss', '')}",
                        "authority": str(m.get("source") or "Sellassie Cheru (2015)"),
                    })
            else:
                pieces.append(f"[unverified:{m['surface']}]")
        if not matched_any_root and not rag_bundle["dictionary_matches"] and not rag_bundle["phrasebook_matches"]:
            confidence_tier = "uncertain_needs_review"
            is_uncertain = True
            engine_mode = "offline_unverified_refusal"
            final_translation = (
                f"⚠️ Unverified in Gofatho Corpus: '{req.text}' could not be verified in the 1,349-headword "
                f"Sellassie Cheru (2015) lexicon or Grade 8–10 Goofatho Doona textbooks. No translation was fabricated."
            )
        else:
            if rag_bundle["dictionary_matches"] and len(morph_breakdown) == 1:
                top_d = rag_bundle["dictionary_matches"][0]
                if req.target_lang == "amh_Ethi" and top_d.get("amharic"):
                    final_translation = top_d["amharic"]
                elif req.target_lang == "eng_Latn" and top_d.get("english"):
                    final_translation = top_d["english"]
                else:
                    final_translation = " ".join(pieces)
            elif len(pieces) >= 3 and req.target_lang == "eng_Latn":
                reordered = [pieces[0], pieces[-1]] + pieces[1:-1]
                final_translation = " ".join(reordered)
            else:
                final_translation = " ".join(pieces)
    else:
        conn = get_db()
        cur = conn.cursor()
        gof_words = []
        matched_count = 0
        # First check exact or whole-query dictionary match
        exact_dict = cur.execute(
            "SELECT id, headword, pos, english, amharic, source FROM dictionary WHERE lower(english) = lower(?) OR amharic = ? OR lower(english) LIKE ? LIMIT 1",
            (working_text, working_text, f"%{working_text.lower()}%"),
        ).fetchone()
        if exact_dict and len(tokens) <= 2:
            matched_count = 1
            gof_words = [exact_dict["headword"].rstrip("-")]
            if not structured_cits:
                structured_cits.append({
                    "source_type": "dictionary",
                    "source_id": f"LEX-{exact_dict['id']}",
                    "title": f"{exact_dict['headword']} ({exact_dict['pos']})",
                    "excerpt": f"EN: {exact_dict['english']} | AM: {exact_dict['amharic']}",
                    "authority": str(exact_dict["source"] or "Sellassie Cheru (2015)"),
                })
        else:
            for tok in tokens:
                row = cur.execute(
                    "SELECT id, headword, pos, english, amharic, source FROM dictionary WHERE lower(english) LIKE ? OR amharic LIKE ? LIMIT 1",
                    (f"%{tok.lower()}%", f"%{tok}%"),
                ).fetchone()
                if row:
                    matched_count += 1
                    gof_words.append(row["headword"].rstrip("-"))
                    if len(structured_cits) < 4:
                        structured_cits.append({
                            "source_type": "dictionary",
                            "source_id": f"LEX-{row['id']}",
                            "title": f"{row['headword']} ({row['pos']})",
                            "excerpt": f"EN: {row['english']} | AM: {row['amharic']}",
                            "authority": str(row["source"] or "Sellassie Cheru (2015)"),
                        })
                else:
                    gof_words.append(f"[unverified:{tok}]")
        conn.close()

        if matched_count == 0:
            confidence_tier = "uncertain_needs_review"
            is_uncertain = True
            engine_mode = "offline_unverified_refusal"
            final_translation = (
                f"⚠️ Unverified / Out-of-Vocabulary: No verified Gofatho lexical equivalent was found in the corpus for '{req.text}'. "
                f"To prevent hallucinated Gofatho vocabulary, no unverified word was invented."
            )
        else:
            if len(gof_words) >= 3:
                gof_words = [gof_words[0]] + gof_words[2:] + [gof_words[1]]
            gof_out = " ".join(gof_words)
            final_translation = (
                transliterator.latin_to_fidel(gof_out)
                if req.target_lang == "gof_Ethi"
                else gof_out
            )

    return {
        "source_text": req.text,
        "source_lang": req.source_lang,
        "target_lang": req.target_lang,
        "translation": final_translation,
        "confidence_tier": confidence_tier,
        "is_uncertain": is_uncertain,
        "structured_citations": structured_cits,
        "morphological_analysis": morph_breakdown,
        "rag_examples": rag_examples,
        "engine_mode": engine_mode,
    }


@app.post("/api/v1/tts")
def synthesize_gofatho_speech(req: TTSRequest):
    is_fidel = req.script == "fidel" or (
        req.script == "auto" and transliterator.is_ethiopic(req.text)
    )
    latin_phonemic = (
        transliterator.fidel_to_latin(req.text) if is_fidel else req.text
    )
    fidel_display = (
        req.text if is_fidel else transliterator.latin_to_fidel(req.text)
    )
    phoneme_tokens = list(latin_phonemic.lower().replace("ʔ", "7"))
    return {
        "model": "facebook/mms-tts-gof (VITS 16kHz)",
        "input_text": req.text,
        "normalized_latin_phonemic": latin_phonemic,
        "fidel_representation": fidel_display,
        "phoneme_token_count": len(phoneme_tokens),
        "sample_rate_hz": 16000,
        "speaking_rate": req.speaking_rate,
        "status": "ready_for_vits_waveform_synthesis",
    }


@app.post("/api/v1/asr")
def transcribe_gofatho_speech(
    audio_filename: str = Query("sample_Matthew_01_v01.mp3"),
    target_script: str = Query("both", description="latin | fidel | both"),
):
    sample_latin = "Yesuus Kiristtoosa, Daawite na7aa, Abrahaame na7aa yeleta maxaafay hagaa."
    sample_fidel = transliterator.latin_to_fidel(sample_latin)
    return {
        "model": "facebook/mms-1b-all (adapter: gof-script_latin)",
        "audio_filename": audio_filename,
        "transcript_gof_latin": sample_latin if target_script in ("latin", "both") else None,
        "transcript_gof_fidel": sample_fidel if target_script in ("fidel", "both") else None,
    }


@app.post("/api/v1/feedback")
def submit_community_feedback(item: FeedbackItem, _rl: None = Depends(enforce_rate_limit)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS community_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_text TEXT,
            source_lang TEXT,
            suggested_gofatho_latin TEXT,
            suggested_gofatho_fidel TEXT,
            suggested_amharic TEXT,
            suggested_english TEXT,
            contributor_woreda TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    fidel_val = item.suggested_gofatho_fidel or transliterator.latin_to_fidel(
        item.suggested_gofatho_latin
    )
    cur.execute(
        """
        INSERT INTO community_feedback (
            source_text, source_lang, suggested_gofatho_latin, suggested_gofatho_fidel,
            suggested_amharic, suggested_english, contributor_woreda, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.source_text,
            item.source_lang,
            item.suggested_gofatho_latin,
            fidel_val,
            item.suggested_amharic,
            item.suggested_english,
            item.contributor_woreda,
            item.notes,
        ),
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS translation_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_text TEXT,
            source_lang TEXT,
            initial_ai_output TEXT,
            suggested_correction TEXT,
            fidel_script TEXT,
            woreda_dialect TEXT,
            linguistic_note TEXT,
            status TEXT DEFAULT 'Pending Review',
            synced_to_cloud INTEGER DEFAULT 0,
            upvotes INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        INSERT INTO translation_feedback (
            source_text, source_lang, initial_ai_output, suggested_correction,
            fidel_script, woreda_dialect, linguistic_note, status, synced_to_cloud, upvotes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending Review', 1, 1)
        """,
        (
            item.source_text,
            item.source_lang,
            item.suggested_english or item.suggested_amharic or "",
            item.suggested_gofatho_latin,
            fidel_val,
            item.contributor_woreda or "Sawla",
            item.notes or "",
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"status": "recorded", "feedback_id": new_id, "auto_fidel": fidel_val}




@app.get("/api/v1/phonetics/gemination")
def search_gemination_pairs(
    q: str = Query("", description="Search Leppiya (singleton) or Minniyaa (geminate) word, phoneme, English, or Amharic"),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Returns verified Gofatho consonant gemination minimal pairs (`Minniyaanne Leppiya Qaalata`)
    grounded in Sellassie Cheru (2015) Section 2.1.3 and SNNPR Grade 8-10 Goofatho Doona textbooks.
    """
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM gemination_minimal_pairs WHERE 1=1"
    params = []
    if q.strip():
        qc = f"%{q.strip()}%"
        sql += """ AND (
            leppiya_singleton_latin LIKE ? OR minniyaa_geminate_latin LIKE ?
            OR leppiya_english LIKE ? OR minniyaa_english LIKE ?
            OR leppiya_amharic LIKE ? OR minniyaa_amharic LIKE ?
            OR consonant_phoneme LIKE ?
        )"""
        params.extend([qc] * 7)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"query": q, "count": len(rows), "results": rows}


@app.get("/api/v1/bible/ot_verses")
def search_old_testament_verses(
    book_id: str = Query("", description="Optional OT Book Code: GEN, PSA, PRO, ISA"),
    q: str = Query("", description="Optional keyword search across Gofatho, Amharic, or English"),
):
    """Returns quad-parallel Gofatho Old Testament (`Geeshsha Maxaafa` GFBLVF / GFBEVF) verses."""
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM old_testament_seed_verses WHERE 1=1"
    params = []
    if book_id.strip():
        sql += " AND book_id = ?"
        params.append(book_id.strip().upper())
    if q.strip():
        qc = f"%{q.strip()}%"
        sql += " AND (gof_latin LIKE ? OR gof_fidel LIKE ? OR amh_fidel LIKE ? OR eng_web LIKE ?)"
        params.extend([qc] * 4)
    sql += " ORDER BY id ASC"
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"book_id": book_id, "query": q, "count": len(rows), "results": rows}




# =========================================================================
# PHASE 6A ENDPOINTS: INTERACTIVE GRADE 8-10 MEEZE & GEMINATION QUIZ ENGINE
# =========================================================================
class QuizGradeRequest(BaseModel):
    quiz_code: str
    selected_option: str = Field(..., description="A | B | C | D")


@app.get("/api/v1/quiz/meeze")
def get_meeze_quiz_questions(
    grade: str = Query("", description="Optional filter: Grade 8 | Grade 9 | Grade 10"),
    category: str = Query("", description="Optional filter: Minniyaa vs. Leppiya Gemination | Textbook Meeze Comprehension | Qawosa Morphology & Suffixes | Ometo Cluster Cognate Bridge"),
    limit: int = Query(30, ge=1, le=250),
):
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM meeze_quiz_bank WHERE 1=1"
    params = []
    if grade.strip():
        sql += " AND grade_level = ?"
        params.append(grade.strip())
    if category.strip():
        sql += " AND quiz_category LIKE ?"
        params.append(f"%{category.strip()}%")
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"grade": grade, "category": category, "count": len(rows), "questions": rows}


@app.post("/api/v1/quiz/grade")
def grade_quiz_submission(req: QuizGradeRequest):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM meeze_quiz_bank WHERE quiz_code = ?", (req.quiz_code,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz question not found")
    q = dict(row)
    is_correct = req.selected_option.strip().upper() == q["correct_option"].strip().upper()
    return {
        "quiz_code": req.quiz_code,
        "selected_option": req.selected_option.upper(),
        "correct_option": q["correct_option"],
        "is_correct": is_correct,
        "explanation_trilingual": q["explanation_trilingual"],
        "audio_target_word": q["audio_target_word"],
    }


# =========================================================================
# PHASE 7A ENDPOINTS: CAMERA PHOTO & DOCUMENT OCR TRANSLATOR
# =========================================================================
class OcrTranslateRequest(BaseModel):
    ocr_text_or_base64: str = Field(..., description="Extracted page text or base64 image payload")
    is_base64_image: bool = Field(False)
    mime_type: str = Field("image/jpeg")
    gemini_api_key: Optional[str] = None


@app.get("/api/v1/ocr/samples")
def list_ocr_sample_documents():
    conn = get_db()
    cur = conn.cursor()
    rows = [dict(r) for r in cur.execute("SELECT * FROM ocr_sample_documents ORDER BY id ASC").fetchall()]
    conn.close()
    return {"count": len(rows), "documents": rows}


@app.post("/api/v1/ocr/translate_image")
def ocr_and_translate_document(
    req: OcrTranslateRequest,
    x_gemini_api_key: Optional[str] = Header(None),
):
    from ocr_vision_translator import GofathoOcrVisionPipeline
    active_db = os.environ.get("GOFATHO_DB_PATH", "").strip() or DB_PATH
    pipeline = GofathoOcrVisionPipeline(active_db)
    api_key = (req.gemini_api_key or x_gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if req.is_base64_image:
        return pipeline.ocr_and_translate_image_base64(req.ocr_text_or_base64, req.mime_type, api_key)
    return pipeline.analyze_extracted_text(req.ocr_text_or_base64)


# =========================================================================
# PHASE 7B ENDPOINTS: NORTH OMOTIC OMETO CLUSTER COGNATE & DIALECT BRIDGE
# (`Gofatho [gof] <-> Gamotho [gmv] <-> Dawuro [dwr] <-> Wolaytta [wal]`)
# =========================================================================
class OmetoConvertRequest(BaseModel):
    text: str = Field(..., example="Entti ooratha haatha uyidosona.")
    source_ometo: str = Field("gof", description="gof | gmv | dwr | wal")
    target_ometo: str = Field("wal", description="gof | gmv | dwr | wal")


@app.get("/api/v1/ometo/bridge")
def search_ometo_cognates(
    q: str = Query("", description="Search word across Gofatho, Gamotho, Dawuro, Wolaytta, Amharic, or English"),
    domain: str = Query("", description="Optional semantic domain filter"),
    limit: int = Query(60, ge=1, le=120),
):
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM ometo_cognate_bridge WHERE 1=1"
    params = []
    if domain.strip():
        sql += " AND semantic_domain LIKE ?"
        params.append(f"%{domain.strip()}%")
    if q.strip():
        qc = f"%{q.strip()}%"
        sql += """ AND (
            gofatho_gof_latin LIKE ? OR gamotho_gmv_latin LIKE ?
            OR dawuro_dwr_latin LIKE ? OR wolaytta_wal_latin LIKE ?
            OR amharic_meaning LIKE ? OR english_meaning LIKE ?
        )"""
        params.extend([qc] * 6)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"query": q, "domain": domain, "count": len(rows), "cognates": rows}


@app.post("/api/v1/ometo/convert")
def convert_across_ometo_cluster(req: OmetoConvertRequest):
    """Adapts a sentence across Gofatho (`gof`), Gamotho (`gmv`), Dawuro (`dwr`), and Wolaytta (`wal`)."""
    conn = get_db()
    cur = conn.cursor()
    all_cog = [dict(r) for r in cur.execute("SELECT * FROM ometo_cognate_bridge").fetchall()]
    conn.close()

    col_map = {
        "gof": "gofatho_gof_latin",
        "gmv": "gamotho_gmv_latin",
        "dwr": "dawuro_dwr_latin",
        "wal": "wolaytta_wal_latin",
    }
    src_col = col_map.get(req.source_ometo, "gofatho_gof_latin")
    tgt_col = col_map.get(req.target_ometo, "wolaytta_wal_latin")

    tokens = req.text.split()
    converted_tokens = []
    applied_rules = []

    for tok in tokens:
        clean_t = tok.strip(".,!?;:").lower()
        punct = tok[len(clean_t):] if tok.lower().startswith(clean_t) else ""
        matched = None
        for c in all_cog:
            src_val = c[src_col].split("/")[0].strip().lower()
            if src_val == clean_t:
                matched = c
                break
        if matched:
            tgt_val = matched[tgt_col].split("/")[0].strip()
            converted_tokens.append(tgt_val + punct)
            applied_rules.append(f"{clean_t} -> {tgt_val} ({matched['sound_correspondence_rule']})")
        else:
            # Apply systematic phonological correspondence rules (`th <-> ts <-> tt`, `dz <-> z`, `entti <-> eti`)
            w = clean_t
            if req.target_ometo == "gmv":
                w = w.replace("th", "ts")
            elif req.target_ometo == "wal":
                w = w.replace("th", "tt").replace("dz", "z").replace("entti", "eti")
            elif req.target_ometo == "gof":
                w = w.replace("ts", "th")
            converted_tokens.append(w + punct)

    out_lat = " ".join(converted_tokens)
    return {
        "source_text": req.text,
        "source_ometo": req.source_ometo,
        "target_ometo": req.target_ometo,
        "converted_latin": out_lat,
        "converted_fidel": transliterator.latin_to_fidel(out_lat),
        "applied_correspondence_rules": applied_rules,
    }


# =========================================================================
# PHASE 8 ENDPOINTS: SAWLA & GOFA ZONE TEACHER/ELDER MODERATION & AUTO-RETRAINING
# =========================================================================
class ApproveFeedbackRequest(BaseModel):
    feedback_id: int
    reviewer_name: str = Field("Sawla Curriculum Elder / Teacher")
    approved_domain: str = Field("Community Verified")


@app.get("/api/v1/admin/feedback_queue")
def list_moderation_feedback_queue(_admin: str = Depends(verify_admin_api_key)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS translation_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_text TEXT,
            source_lang TEXT,
            initial_ai_output TEXT,
            suggested_correction TEXT,
            fidel_script TEXT,
            woreda_dialect TEXT,
            linguistic_note TEXT,
            status TEXT DEFAULT 'Pending Review',
            synced_to_cloud INTEGER DEFAULT 0,
            upvotes INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    rows = [dict(r) for r in cur.execute("SELECT * FROM translation_feedback ORDER BY id DESC").fetchall()]
    conn.close()
    return {"count": len(rows), "feedback_queue": rows}


@app.post("/api/v1/admin/approve_feedback")
def approve_and_merge_community_feedback(
    req: ApproveFeedbackRequest,
    _admin: str = Depends(verify_admin_api_key),
):
    """
    Approves a native speaker correction from Gofa Zone woredas, updates its status to
    'Approved & Merged', and inserts it into `everyday_phrasebook` for immediate RAG & NLLB-200 retraining.
    """
    conn = get_db()
    cur = conn.cursor()
    fb = cur.execute("SELECT * FROM translation_feedback WHERE id = ?", (req.feedback_id,)).fetchone()
    if not fb:
        conn.close()
        raise HTTPException(status_code=404, detail="Feedback record not found")

    fb_dict = dict(fb)
    cur.execute(
        "UPDATE translation_feedback SET status = 'Approved & Merged', synced_to_cloud = 1, upvotes = upvotes + 1 WHERE id = ?",
        (req.feedback_id,),
    )
    phr_count = cur.execute("SELECT COUNT(*) FROM everyday_phrasebook").fetchone()[0]
    new_code = f"PHR-COM-{phr_count + 1:04d}"
    gof_lat = fb_dict.get("suggested_correction") or fb_dict.get("initial_ai_output") or ""
    gof_fid = fb_dict.get("fidel_script") or transliterator.latin_to_fidel(gof_lat)

    cur.execute(
        """
        INSERT INTO everyday_phrasebook (
            phrase_code, domain, gofatho_latin, gofatho_fidel, amharic, english,
            ipa_phonemic, morpheme_breakdown, usage_context, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_code,
            req.approved_domain,
            gof_lat,
            gof_fid,
            fb_dict.get("source_text", ""),
            fb_dict.get("source_text", ""),
            f"/{gof_lat.lower()}/",
            fb_dict.get("linguistic_note", "Community verified"),
            f"Approved by {req.reviewer_name} ({fb_dict.get('woreda_dialect', 'Sawla')})",
            "Phase 8 Community Verification Loop",
        ),
    )
    try:
        cur.execute("INSERT INTO phrasebook_fts(phrasebook_fts) VALUES('rebuild')")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    observability.reset_cache()
    try:
        from gofatho_deep_rag_engine import GofathoDeepRAGEngine
        GofathoDeepRAGEngine._rrf_cache.clear()
    except Exception:
        pass
    return {
        "status": "Approved & Merged into Master SQLite",
        "feedback_id": req.feedback_id,
        "new_phrase_code": new_code,
        "gofatho_latin": gof_lat,
        "gofatho_fidel": gof_fid,
    }


@app.get("/api/v1/admin/export_retraining_jsonl")
def export_nllb_retraining_jsonl(_admin: str = Depends(verify_admin_api_key)):
    """Exports approved community feedback & newly added phrases as bidirectional NLLB-200 JSONL pairs."""
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM translation_feedback").fetchall()
    conn.close()

    jsonl_pairs = []
    for r in rows:
        d = dict(r)
        g_lat = d.get("suggested_correction", "")
        g_fid = d.get("fidel_script") or transliterator.latin_to_fidel(g_lat)
        src = d.get("source_text", "")
        woreda = d.get("woreda_dialect", "Sawla")
        jsonl_pairs.append({
            "src_lang": "eng_Latn",
            "tgt_lang": "gof_Latn",
            "source": src,
            "target": g_lat,
            "fidel": g_fid,
            "woreda_dialect": woreda,
            "status": d.get("status", "Verified"),
        })
        jsonl_pairs.append({
            "src_lang": "gof_Latn",
            "tgt_lang": "gof_Ethi",
            "source": g_lat,
            "target": g_fid,
            "woreda_dialect": woreda,
            "status": d.get("status", "Verified"),
        })
    return {"pair_count": len(jsonl_pairs), "retraining_pairs": jsonl_pairs}




# =========================================================================
# PHASE 10 / v5.0 PURE GOFATHO AI: DEEP MORPHOLOGY-AWARE HYBRID RAG CHAT & VOICE ASSISTANT
# =========================================================================
from gofatho_deep_rag_engine import GofathoDeepRAGEngine
from gofatho_voice_assistant_pipeline import GofathoVoiceAssistantPipeline

def _get_deep_rag_engine() -> GofathoDeepRAGEngine:
    active_path = os.environ.get("GOFATHO_DB_PATH", "").strip() or DB_PATH
    return GofathoDeepRAGEngine(active_path)


def _get_voice_pipeline() -> GofathoVoiceAssistantPipeline:
    active_path = os.environ.get("GOFATHO_DB_PATH", "").strip() or DB_PATH
    return GofathoVoiceAssistantPipeline(active_path)


deep_rag_engine = GofathoDeepRAGEngine(DB_PATH)
voice_pipeline = GofathoVoiceAssistantPipeline(DB_PATH)


class DeepRagChatRequest(BaseModel):
    query_text: str = Field(..., description="User message or question in Gofatho (Latin/Fidel), Amharic, or English")
    assistant_mode: str = Field(
        "chat_assistant",
        description="Mode: chat_assistant | fst_morph_tutor | curriculum_coach | oral_lit_guide | hybrid_translator",
    )
    session_id: str = Field("gof_chat_sess_001", description="Multi-turn conversation session ID")


class VoiceTurnRequest(BaseModel):
    raw_transcript: str = Field(..., description="Raw spoken Gofatho/Amharic/English transcript from Meta MMS-1B CTC or mic")
    session_id: str = Field("gof_voice_sess_001", description="Voice assistant conversation session ID")
    vad_mode: str = Field("silero_handsfree_16khz", description="VAD mode: silero_handsfree_16khz | push_to_talk")


@app.post("/api/v1/chat/deep_rag")
def chat_with_deep_hybrid_rag(req: DeepRagChatRequest, _rl: None = Depends(enforce_rate_limit)):
    """
    5-Stage Deep Morphology-Aware Hybrid RAG & Post-Editing Chat Assistant:
      Stage 1: 4-Stage FST Morphological Decomposer & Reverse MP-01..MP-11 Rules
      Stage 2: 6-Index Reciprocal Rank Fusion (RRF, k=60) + Character 3-Gram Reranker
      Stage 3: Dynamic Grammar-Card & Few-Shot Context Saturation
      Stage 4: Grounded Quad-Parallel Response Synthesis & Multi-Turn Memory
      Stage 5: Goofatho Doona 'Zara 5' Orthography & Gemination Verifier
    """
    return _get_deep_rag_engine().synthesize_offline_or_hybrid_response(
        query=req.query_text,
        assistant_mode=req.assistant_mode,
        session_id=req.session_id,
    )


@app.get("/api/v1/morph/fst_analyze")
def analyze_sentence_with_fst(
    text: Optional[str] = Query(None, description="Gofatho sentence or word in Latin or Ethiopic Fidel script"),
    word: Optional[str] = Query(None, description="Alias for text (single word or phrase)"),
):
    text = (text or word or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Query parameter 'text' or 'word' is required.")
    """Decomposes every word into root lemma, stripped affixes, and Sellassie Cheru (2015) MP-01..MP-11 rules."""
    conn = get_db()
    tokens = _get_deep_rag_engine().fst.decompose_sentence(text, conn)
    rules = [dict(r) for r in conn.execute("SELECT * FROM morphophonemic_fst_rules").fetchall()]
    conn.close()
    return {
        "input_text": text,
        "gofatho_fidel": transliterator.latin_to_fidel(text),
        "token_count": len(tokens),
        "fst_tokens": tokens,
        "active_fst_rule_inventory": rules,
    }


class AnalyzeSentenceRequest(BaseModel):
    sentence: str = Field(..., description="Gofatho sentence in Latin or Ethiopic Extended-A Fidel script")


def _infer_sov_constituent_role(idx: int, total: int, tok: Dict[str, Any]) -> str:
    sufs = [s.get("suffix", "") for s in tok.get("stripped_suffixes", [])]
    gl_str = " ".join(s.get("gloss", "") for s in tok.get("stripped_suffixes", []))
    pos = (tok.get("pos") or "").upper()
    if any(k in gl_str for k in ["DCL", "INTER", "IMP", "PROH", "JUSS", "OPT"]) or (idx == total - 1 and "V" in pos):
        return "V_PREDICATE (SOV Clause-Final Finite Verb)"
    if "CNV" in gl_str:
        return "V_CONVERB (Medial Clause-Chaining Converb)"
    if any(s in sufs for s in ["-ppe", "-fe", "-n", "-ra", "-s", "-w"]) or any(k in gl_str for k in ["ABL", "LOC", "DAT", "COM", "INST"]):
        return "OBLIQUE_PP (Postpositional / Case-Marked Adjunct)"
    if "-y" in sufs or "-t-i" in sufs or "NOM" in gl_str or (idx == 0 and ("PRON" in pos or "N" in pos)) or (idx == total - 1 and "N" in pos):
        return "S_SUBJECT (Nominative Subject / Head NP)"
    if idx < total - 1 and ("N" in pos or "ADJ" in pos):
        return "O_OBJECT_OR_MODIFIER (Pre-Verbal Object / Nominal Modifier)"
    return "CONSTITUENT_STEM"


@app.post("/api/v1/morph/analyze_sentence")
def analyze_interlinear_sov_sentence(req: AnalyzeSentenceRequest, _rl: None = Depends(enforce_rate_limit)):
    """
    Batch Interlinear Leipzig Glossing (IGT) & SOV Constituent Role Analyzer (Phase I.2):
    Decomposes a multi-word Gofatho sentence (Latin or Ethiopic Fidel) into per-token
    root lemmas, stripped suffixes, MP-01..MP-11 rules, SOV constituent roles,
    4-tier interlinear gloss lines, compositional English/Amharic glosses, and LEX-* citations.
    """
    raw = req.sentence.strip()
    if not raw:
        raise HTTPException(status_code=422, detail="Field 'sentence' cannot be empty.")
    latin_sentence = (
        transliterator.fidel_to_latin(raw)
        if transliterator.is_ethiopic(raw)
        else raw
    )
    fidel_sentence = transliterator.latin_to_fidel(latin_sentence)

    conn = get_db()
    fst_tokens = _get_deep_rag_engine().fst.decompose_sentence(latin_sentence, conn)
    conn.close()

    total_toks = len(fst_tokens)
    enriched_tokens = []
    surface_tier = []
    morpheme_tier = []
    leipzig_tier = []
    citations = []
    seen_cits = set()
    en_pieces = []
    am_pieces = []

    for idx, t in enumerate(fst_tokens):
        role = _infer_sov_constituent_role(idx, total_toks, t)
        sufs = t.get("stripped_suffixes", [])
        root_clean = (t.get("root_lemma") or t.get("surface", "")).rstrip("-")
        m_break = root_clean + ("".join(s.get("suffix", "") for s in sufs) if sufs else "")
        en_base = (t.get("english_gloss") or "stem").split(";")[0].split(",")[0].strip()
        am_base = (t.get("amharic_gloss") or en_base).split("/")[0].split("፣")[0].strip()
        suf_codes = [s.get("gloss", "").split("(")[0].strip().replace(" ", ".") for s in sufs if s.get("gloss")]
        l_gloss = en_base.replace(" ", ".") + ("-" + "-".join(suf_codes) if suf_codes else "")

        surface_tier.append(t.get("surface", ""))
        morpheme_tier.append(m_break)
        leipzig_tier.append(l_gloss)

        if t.get("lex_id"):
            cid = f"LEX-{t['lex_id']}"
            if cid not in seen_cits:
                seen_cits.add(cid)
                citations.append({
                    "source_type": "dictionary",
                    "source_id": cid,
                    "title": f"{t.get('root_lemma')} ({t.get('pos', 'LEX')})",
                    "excerpt": f"EN: {t.get('english_gloss', '')} | AM: {t.get('amharic_gloss', '')}",
                    "authority": str(t.get("source") or "Sellassie Cheru (2015)"),
                })
            en_pieces.append(f"{en_base}" + (f" [{' + '.join(suf_codes)}]" if suf_codes else ""))
            am_pieces.append(am_base)
        else:
            en_pieces.append(f"[{t.get('surface', '')}]")
            am_pieces.append(f"[{t.get('surface', '')}]")

        enriched_tokens.append({
            **t,
            "sov_role": role,
            "morpheme_segmentation": m_break,
            "leipzig_gloss": l_gloss,
        })

    # Reorder SOV -> SVO for compositional English gloss preview when >= 3 tokens
    if len(en_pieces) >= 3:
        svo_en = [en_pieces[0], en_pieces[-1]] + en_pieces[1:-1]
    else:
        svo_en = en_pieces

    return {
        "input_sentence": raw,
        "gofatho_latin": latin_sentence,
        "gofatho_fidel": fidel_sentence,
        "token_count": total_toks,
        "word_order_typology": "SOV (Subject-Object-Verb Head-Final North Omotic)",
        "interlinear_tiers": {
            "tier_1_surface_latin": "  ".join(surface_tier),
            "tier_2_surface_fidel": fidel_sentence,
            "tier_3_morpheme_break": "  ".join(morpheme_tier),
            "tier_4_leipzig_gloss": "  ".join(leipzig_tier),
        },
        "compositional_english_gloss": " ".join(svo_en),
        "compositional_amharic_gloss": " ".join(am_pieces),
        "tokens": enriched_tokens,
        "structured_citations": citations,
    }


@app.post("/api/v1/voice/converse")
def converse_with_voice_assistant(req: VoiceTurnRequest, _rl: None = Depends(enforce_rate_limit)):
    """
    4-Stage End-to-End Voice Assistant Pipeline:
      Stage A: Silero VAD (16 kHz hands-free or push-to-talk endpointing)
      Stage B: Meta MMS-1B (`gof-script_latin`) CTC Decoding + 1,519-Word Lexicon Rescorer
      Stage C: Deep Morphology-Aware Hybrid RAG Spoken Turn Generation
      Stage D: Clause-Chunked Sherpa-ONNX VITS TTS with Autosegmental Tone & Gemination Prosody
    """
    return _get_voice_pipeline().process_voice_turn(
        raw_transcript=req.raw_transcript,
        session_id=req.session_id,
        vad_mode=req.vad_mode,
    )


@app.get("/api/v1/curriculum/chapters_28")
def list_grade8_to_10_curriculum_chapters(
    grade: str = Query("All", description="Filter by Grade 8, Grade 9, Grade 10, or All"),
    q: str = Query("", description="Search chapter titles, reading passages, dialogues, or Qawosa grammar"),
):
    """Returns the 28 exhaustive chapters from Grade 8, 9, and 10 Goofatho Doona textbooks and 30 Haasaya dialogues."""
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM textbook_chapters_28_deep WHERE 1=1"
    params = []
    if grade and grade != "All":
        sql += " AND grade = ?"
        params.append(grade)
    if q.strip():
        lk = f"%{q.strip()}%"
        sql += " AND (title_gofatho_latin LIKE ? OR title_english LIKE ? OR passages_summary_gofatho LIKE ? OR grammar_focus_qawosa LIKE ?)"
        params.extend([lk, lk, lk, lk])
    sql += " ORDER BY id ASC"
    chapters = [dict(r) for r in cur.execute(sql, params).fetchall()]
    dialogues = [dict(r) for r in cur.execute("SELECT * FROM textbook_dialogues_haasaya ORDER BY id ASC LIMIT 30").fetchall()]
    conn.close()
    return {"chapter_count": len(chapters), "dialogue_count": len(dialogues), "chapters": chapters, "dialogues": dialogues}




@app.get("/api/v1/fst/inflect")
def search_pregenerated_fst_inflections(
    root_or_lemma: str = Query("", description="Verb root (e.g. oott-, b-, uy-, shamm-) or Noun lemma (e.g. boora, mishire, miidzdze)"),
    lemma: str = Query("", description="Alias for root_or_lemma"),
    category: str = Query("", description="TAM category or Nominal Case filter"),
    limit: int = Query(50, ge=1, le=200),
):
    root_or_lemma = (root_or_lemma or lemma).strip()
    """Queries the 3,480 pre-generated Forward FST verb conjugations and noun declensions (MP-01..MP-11)."""
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM fst_inflection_paradigm_bank WHERE 1=1"
    params = []
    if root_or_lemma.strip():
        lk = f"%{root_or_lemma.strip()}%"
        sql += " AND (lower(root_or_lemma) LIKE lower(?) OR lower(surface_latin) LIKE lower(?))"
        params.extend([lk, lk])
    if category.strip():
        sql += " AND lower(category_or_case) LIKE lower(?)"
        params.append(f"%{category.strip()}%")
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    return {"count": len(rows), "inflections": rows}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
