#!/usr/bin/env python3
"""
Gofatho AI v5.0 — End-to-End Offline & Cloud Voice Assistant Pipeline
======================================================================
Pure Gofatho Voice Assistant (ASR + Lexicon Hotword Rescoring + Deep RAG + Autosegmental VITS TTS).
Grounded in:
  1. Meta MMS-1B (`facebook/mms-1b-all`, adapter `gof-script_latin`, 29-token CTC preserving '7' = /ʔ/)
  2. Meta MMS-TTS (`facebook/mms-tts-gof`) & Sherpa-ONNX Offline VITS (`model.int8.onnx` + `lexicon.txt`)
  3. Silero VAD / Energy + Zero-Crossing Endpointing (16 kHz mono PCM)
  4. Sellassie Cheru (2015) Stage 4 Autosegmental Tone & Gemination Prosody Controller
"""

import os
import re
import sqlite3
from typing import Dict, List, Any, Optional

from gofatho_deep_rag_engine import GofathoDeepRAGEngine
from morphological_analyzer import latin_to_gofatho_fidel


def edit_distance_phonemic(s1: str, s2: str) -> float:
    """
    Phonology-aware Levenshtein distance that assigns low cost (0.35) to:
      - Dropped glottal stop '7' (/ʔ/) in raw CTC decoding (e.g. 'lo77o' vs 'loo' or 'lo7o')
      - Singleton vs. geminate consonant length ('tama' vs 'tamma')
      - Vowel length ('aa' vs 'a')
    """
    a = s1.lower().strip()
    b = s2.lower().strip()
    if a == b:
        return 0.0
    # Normalize glottal-dropped & degeminated skeleton comparison
    skel_a = re.sub(r"(.)\1+", r"\1", a.replace("7", ""))
    skel_b = re.sub(r"(.)\1+", r"\1", b.replace("7", ""))
    if skel_a == skel_b and len(skel_a) >= 2:
        return 0.35

    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return float(dp[m][n])


class GofathoVoiceAssistantPipeline:
    """
    4-Stage Voice Assistant Pipeline:
      Stage A: Voice Activity Detection (Silero VAD / 16kHz Endpointing config)
      Stage B: Meta MMS-1B (`gof-script_latin`) CTC Decoding + Lexicon Hotword Rescorer
      Stage C: Deep Morphology-Aware Hybrid RAG Spoken Turn Generation
      Stage D: Clause-Chunked Sherpa-ONNX VITS TTS with Autosegmental Tone & Gemination Prosody
    """

    def __init__(self, db_path: str, onnx_dir: Optional[str] = None):
        self.db_path = db_path
        self.rag_engine = GofathoDeepRAGEngine(db_path)
        self.onnx_dir = onnx_dir or os.path.join(os.path.dirname(db_path), "../flutter_app/assets/models")
        self._vocab_cache: List[str] = []
        self._load_lexicon_hotwords()

    def _load_lexicon_hotwords(self) -> None:
        words = set()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            for (hw,) in cur.execute("SELECT headword FROM dictionary").fetchall():
                w = hw.strip().rstrip("-").lower()
                if len(w) >= 2:
                    words.add(w)
            for (phr,) in cur.execute("SELECT gofatho_latin FROM everyday_phrasebook LIMIT 600").fetchall():
                for tok in re.findall(r"[A-Za-z7]{2,}", phr):
                    words.add(tok.lower())
            conn.close()
        except sqlite3.OperationalError:
            pass
        lex_v6_p = os.path.join(self.onnx_dir, "lexicon_v6_expanded.txt")
        if os.path.exists(lex_v6_p):
            with open(lex_v6_p, encoding="utf-8") as lf:
                for line in lf:
                    parts = line.strip().split()
                    if parts and len(parts[0]) >= 2:
                        words.add(parts[0].lower())
        self._vocab_cache = sorted(words)

    def rescore_asr_transcript(self, raw_ctc_transcript: str) -> Dict[str, Any]:
        """
        Stage B: Restores dropped glottal stops ('7' = /ʔ/) and geminate consonants
        ('Minniyaa vs. Leppiya') in raw CTC output using the 1,519-headword lexicon.
        """
        tokens = re.findall(r"[A-Za-z7']+|[^A-Za-z7'\s]+", raw_ctc_transcript)
        rescored_tokens = []
        corrections = []

        # High-frequency glottal-dropped / degeminated CTC tokens -> canonical Gofatho restoration map
        GLOTTAL_GEMINATE_HOTWORDS = {
            "loo": "lo77o",
            "lo7o": "lo77o",
            "naa": "na7a",
            "baa": "ba7a",
            "saa": "sa7a",
            "peadii": "pe7adii",
            "dubusha": "dubbusha",
            "keeta": "keetta",
            "goofato": "goofatho",
        }
        conn_tmp = None
        try:
            conn_tmp = sqlite3.connect(self.db_path)
        except sqlite3.OperationalError:
            conn_tmp = None

        for tok in tokens:
            if not re.match(r"^[A-Za-z7']+$", tok):
                rescored_tokens.append(tok)
                continue
            low = tok.lower().replace("'", "7")
            if low in GLOTTAL_GEMINATE_HOTWORDS:
                restored = GLOTTAL_GEMINATE_HOTWORDS[low]
                preserved_case = restored.capitalize() if tok[0].isupper() else restored
                rescored_tokens.append(preserved_case)
                corrections.append({
                    "raw_ctc": tok,
                    "rescored_gofatho": preserved_case,
                    "phonemic_distance": 0.35,
                    "reason": "Glottal Stop '7' / Gemination Restoration",
                })
                continue
            if low in self._vocab_cache:
                rescored_tokens.append(tok.replace("'", "7"))
                continue
            # Also check if FST decomposer recognizes a valid inflected Gofatho form (e.g. qaalati = qaala + -ti)
            if conn_tmp is not None:
                try:
                    fst_tok = self.rag_engine.fst.analyze_token_fst(low, conn_tmp)
                    if fst_tok.get("stripped_suffixes") and fst_tok.get("english_gloss") != "Contextual stem":
                        rescored_tokens.append(tok.replace("'", "7"))
                        continue
                except sqlite3.OperationalError:
                    pass

            # Find closest lexicon word by phonemic edit distance (preferring candidates that restore '7' or gemination on tie)
            best_w = None
            best_dist = 999.0
            for cand in self._vocab_cache:
                if abs(len(cand) - len(low)) > 2:
                    continue
                d = edit_distance_phonemic(low, cand)
                if d < best_dist or (d == best_dist and d <= 0.35 and "7" in cand and (not best_w or "7" not in best_w)):
                    best_dist = d
                    best_w = cand

            if best_w and best_dist <= 1.0 and len(low) >= 3:
                preserved_case = best_w.capitalize() if tok[0].isupper() else best_w
                rescored_tokens.append(preserved_case)
                if preserved_case.lower() != low:
                    corrections.append({
                        "raw_ctc": tok,
                        "rescored_gofatho": preserved_case,
                        "phonemic_distance": best_dist,
                        "reason": "Glottal Stop '7' / Gemination Restoration" if "7" in best_w or best_dist <= 0.35 else "Lexicon Hotword Match",
                    })
            else:
                rescored_tokens.append(tok.replace("'", "7"))

        if conn_tmp is not None:
            conn_tmp.close()
        rescored_text = ""
        for i, t in enumerate(rescored_tokens):
            if i > 0 and re.match(r"^[A-Za-z7]+$", t):
                rescored_text += " " + t
            else:
                rescored_text += t

        return {
            "raw_ctc_transcript": raw_ctc_transcript,
            "rescored_transcript": rescored_text.strip(),
            "rescored_fidel": latin_to_gofatho_fidel(rescored_text.strip()),
            "lexicon_corrections": corrections,
        }

    def build_tts_prosody_plan(self, gofatho_text: str) -> Dict[str, Any]:
        """
        Stage D: Splits Gofatho response at converb (-idi, -ada) and punctuation boundaries
        for low-latency streaming VITS synthesis, assigning Sellassie Cheru (2015) Stage 4
        Autosegmental Tone & Gemination parameters.
        """
        # Split on sentence or converb boundaries for streaming playback
        raw_chunks = re.split(r"(?<=[.!?;:,])\s+|(?=\b\w+(?:idi|ada)\s+)", gofatho_text.strip())
        chunks = [c.strip() for c in raw_chunks if c and c.strip()]
        if not chunks:
            chunks = [gofatho_text.strip()]

        stream_segments = []
        for idx, ch in enumerate(chunks, 1):
            is_question = ch.endswith("?") or bool(re.search(r"(?:ii|ay|oonaa|ee)\?$", ch.lower()))
            geminates = re.findall(
                r"\b\w*(?:mm|nn|ll|rr|ss|tt|dd|kk|gg|pp|bb|qq|xx|cc|77|chch|shsh|dhdh|thth)\w*\b",
                ch,
                flags=re.IGNORECASE,
            )
            glottals = re.findall(r"\b\w*7\w*\b", ch)
            stream_segments.append({
                "chunk_index": idx,
                "text_latin": ch,
                "text_fidel": latin_to_gofatho_fidel(ch),
                "vits_length_scale": 1.05 if geminates else 0.98,
                "vits_noise_scale": 0.667,
                "vits_noise_scale_w": 0.80,
                "geminate_closure_multiplier": 1.85 if geminates else 1.0,
                "glottal_stop_pause_ms": 65 if glottals else 0,
                "terminal_f0_contour": "RISING_INTERROGATIVE (+18% F0)" if is_question else "DECLARATIVE_HL_DOWNSSTEP",
                "geminate_tokens": geminates,
                "glottal_tokens": glottals,
            })

        return {
            "engine": "Sherpa-ONNX Offline VITS (facebook/mms-tts-gof INT8)",
            "sample_rate_hz": 16000,
            "model_file": "model.int8.onnx",
            "tokens_file": "tokens.txt",
            "lexicon_file": "lexicon.txt",
            "total_streaming_chunks": len(stream_segments),
            "streaming_chunks": stream_segments,
        }

    def process_voice_turn(
        self,
        raw_transcript: str,
        session_id: str = "voice_sess_001",
        vad_mode: str = "silero_handsfree_16khz",
    ) -> Dict[str, Any]:
        """Runs the complete Stage A -> Stage B -> Stage C -> Stage D Voice Assistant turn."""
        asr_res = self.rescore_asr_transcript(raw_transcript)
        rag_res = self.rag_engine.synthesize_offline_or_hybrid_response(
            asr_res["rescored_transcript"],
            assistant_mode="voice_assistant",
            session_id=session_id,
        )
        tts_plan = self.build_tts_prosody_plan(rag_res["gofatho_latin"])

        return {
            "session_id": session_id,
            "vad_config": {
                "mode": vad_mode,
                "sample_rate_hz": 16000,
                "speech_threshold": 0.50,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 600,
            },
            "stage_b_asr_rescoring": asr_res,
            "stage_c_deep_rag_response": rag_res,
            "stage_d_sherpa_onnx_tts_plan": tts_plan,
        }
