"""
Gofatho (ISO 639-3: gof) Morphological Analyzer & Dual-Script Transliterator
Grounded in Sellassie Cheru (2015), 'Documentation and Grammatical Description of Gofa'
and SNNPR Grade 8-10 Gofatho Textbooks (2015 E.C.).
"""

import re
import sqlite3
from typing import Dict, List, Any

NOMINAL_SUFFIXES = [
    ("tappe", "-t-a-ppe", "PL.ACC.ABL ('from the ...s')"),
    ("tas", "-t-a-s", "PL.ACC.DAT ('to/for the ...s')"),
    ("taw", "-t-a-w", "PL.ACC.DAT ('to/for the ...s')"),
    ("tan", "-t-a-n", "PL.ACC.LOC/INST ('in/by the ...s')"),
    ("tara", "-t-a-ra", "PL.ACC.COM ('with the ...s')"),
    ("ti", "-t-i", "PL.NOM (Plural Subject)"),
    ("ta", "-t-a", "PL.ACC (Plural Object)"),
    ("ppe", "-ppe", "ABL ('from / than')"),
    ("fe", "-fe", "ABL ('from / out of')"),
    ("ra", "-ra", "COM ('with / together with')"),
    ("yssi", "-yss-i", "NMZ.M.SG.NOM ('the one who / that which')"),
    ("yssa", "-yss-a", "NMZ.M.SG.ACC ('the one who / that which')"),
    ("y", "-y", "NOM.M.DEF (Definite Subject)"),
    ("s", "-s", "DAT ('to / for')"),
    ("w", "-w", "DAT ('to / for')"),
    ("n", "-n", "LOC/INST ('in, at, on, with')"),
]

VERBAL_SUFFIXES = [
    ("idosona", "-idosona", "PAST.3PL.AFF.DCL ('they did')"),
    ("oosona", "-oosona", "PRES/IMPF.3PL.AFF.DCL ('they do')"),
    ("ibeenna", "-ibeenna", "PAST.3MS.NEG.DCL ('he did not')"),
    ("abeenna", "-abeenna", "PAST.NEG.DCL ('did not')"),
    ("okkoona", "-okkoona", "PRES.3PL.NEG.DCL ('they do not')"),
    ("ideta", "-ideta", "PAST.2PL.AFF.DCL ('you all did')"),
    ("anaw", "-ana-w", "FUT.PURP / INF ('in order to')"),
    ("anau", "-ana-u", "FUT.PURP / INF ('in order to')"),
    ("ana", "-ana", "FUT.AFF.DCL ('will / shall')"),
    ("ikko", "-ikko", "COND.REAL ('if')"),
    ("iakko", "-iakko", "COND.HYP ('if [counterfactual]')"),
    ("ishin", "-ishin", "CNV.SIM.DS ('while doing')"),
    ("ishe", "-ishe", "CNV.SIM.SS ('while doing')"),
    ("ashe", "-ashe", "CNV.SIM.SS ('while doing')"),
    ("idi", "-idi", "CNV.ANT.3MS/PL ('having done...')"),
    ("ada", "-ada", "CNV.ANT.1S/2S/3FS ('having done...')"),
    ("awsu", "-awsu", "PRES.3FS.AFF.DCL ('she does')"),
    ("asu", "-asu", "PAST.3FS.AFF.DCL ('she did')"),
    ("aasa", "-aasa", "PRES/PAST.2S.AFF.DCL ('you do/did')"),
    ("ays", "-ays", "PRES.1S.AFF.DCL ('I do')"),
    ("oos", "-oos", "PRES.1PL.AFF.DCL ('we do')"),
    ("ees", "-ees", "PRES.3MS.AFF.DCL ('he/it does')"),
    ("enna", "-enna", "PRES.3MS.NEG.DCL ('he/it does not')"),
    ("ofite", "-ofite", "PROH.2PL ('do not! [plural]')"),
    ("oppa", "-oppa", "PROH.2S ('do not! [singular]')"),
    ("ofa", "-ofa", "PROH.2S ('do not! [singular]')"),
    ("ite", "-ite", "IMP.2PL ('do! [plural]')"),
    ("is", "-is", "PAST.3MS.AFF.DCL ('he/it did')"),
]

DERIVATIONAL_SUFFIXES = [
    ("tetha", "-teth-a", "ABSTR.NMZ ('abstract noun: -ness / -hood')"),
    ("tethi", "-teth-i", "ABSTR.NMZ.NOM ('abstract noun: -ness / -hood')"),
    ("ett", "-ett-", "PASS/REFL ('passive / reflexive')"),
    ("iss", "-iss-", "CAUS ('causative')"),
]

LATIN_TO_FIDEL_BASE = {
    "th": ("ꬅ", {"a": "ꬃ", "aa": "ꬃአ", "u": "ꬁ", "uu": "ꬁኡ", "i": "ꬂ", "ii": "ꬂኢ", "e": "ꬄ", "ee": "ꬄእ", "o": "ꬆ", "oo": "ꬆኦ"}),
    "dh": ("ꬍ", {"a": "ꬋ", "aa": "ꬋአ", "u": "ꬉ", "uu": "ꬉኡ", "i": "ꬊ", "ii": "ꬊኢ", "e": "ꬌ", "ee": "ꬌእ", "o": "ꬎ", "oo": "ꬎኦ"}),
    "dz": ("ꬕ", {"a": "ꬓ", "aa": "ꬓአ", "u": "ꬑ", "uu": "ꬑኡ", "i": "ꬒ", "ii": "ꬒኢ", "e": "ꬔ", "ee": "ꬔእ", "o": "ꬖ", "oo": "ꬖኦ"}),
    "sh": ("ሽ", {"a": "ሻ", "aa": "ሻአ", "u": "ሹ", "uu": "ሹኡ", "i": "ሺ", "ii": "ሺኢ", "e": "ሼ", "ee": "ሼእ", "o": "ሾ", "oo": "ሾኦ"}),
    "ch": ("ች", {"a": "ቻ", "aa": "ቻአ", "u": "ቹ", "uu": "ቹኡ", "i": "ቺ", "ii": "ቺኢ", "e": "ቼ", "ee": "ቼእ", "o": "ቾ", "oo": "ቾኦ"}),
    "ph": ("ጵ", {"a": "ጳ", "aa": "ጳአ", "u": "ጱ", "uu": "ጱኡ", "i": "ጪ", "ii": "ጪኢ", "e": "ጴ", "ee": "ጴእ", "o": "ፆ", "oo": "ፆኦ"}),
    "ny": ("ኝ", {"a": "ኛ", "aa": "ኛአ", "u": "ኙ", "uu": "ኙኡ", "i": "ኚ", "ii": "ኚኢ", "e": "ኜ", "ee": "ኜእ", "o": "ኞ", "oo": "ኞኦ"}),
    "zh": ("ዥ", {"a": "ዣ", "aa": "ዣአ", "u": "ዡ", "uu": "ዡኡ", "i": "ዢ", "ii": "ዢኢ", "e": "ዤ", "ee": "ዤእ", "o": "ዦ", "oo": "ዦኦ"}),
}

SINGLE_CONSONANT_SERIES = {
    "h": 0x1200, "l": 0x1208, "m": 0x1218, "r": 0x1228, "s": 0x1230,
    "q": 0x1240, "b": 0x1260, "t": 0x1270, "n": 0x1290, "k": 0x12A8,
    "w": 0x12C8, "z": 0x12D8, "y": 0x12E8, "d": 0x12F0, "j": 0x1300,
    "g": 0x1308, "x": 0x1320, "c": 0x1328, "f": 0x1348, "p": 0x1350,
}

VOWEL_OFFSETS = {"a": 0, "u": 1, "i": 2, "e": 4, "o": 6}
LONG_VOWEL_SUFFIX = {"aa": "አ", "uu": "ኡ", "ii": "ኢ", "ee": "እ", "oo": "ኦ"}
STANDALONE_VOWELS = {
    "a": "አ", "aa": "አአ", "u": "ኡ", "uu": "ኡኡ", "i": "ኢ", "ii": "ኢኢ",
    "e": "እ", "ee": "እእ", "o": "ኦ", "oo": "ኦኦ",
}
GLOTTAL_VOWELS = {
    "a": "ዓ", "aa": "ዓአ", "u": "ዑ", "uu": "ዑኡ", "i": "ዒ", "ii": "ዒኢ",
    "e": "ዔ", "ee": "ዔእ", "o": "ዖ", "oo": "ዖኦ", "": "ዕ",
}

def latin_to_gofatho_fidel(text: str) -> str:
    """Deterministic Gofatho Latin -> Ethiopic Fidel transliterator preserving Extended-A & Glottal Stop (7)."""
    if not text:
        return ""
    out = []
    s = text.replace("ʔ", "7")
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        low = ch.lower()
        if not (low.isalpha() or low == "7"):
            if ch == ".":
                out.append("።")
            elif ch == ",":
                out.append("፣")
            elif ch == ";":
                out.append("፤")
            elif ch == ":":
                out.append("፦")
            else:
                out.append(ch)
            i += 1
            continue

        if low == "7":
            if i + 1 < n and s[i + 1] == "7":
                out.append("ዕ")
                i += 1
            v2 = s[i + 1 : i + 3].lower() if i + 2 <= n else ""
            v1 = s[i + 1 : i + 2].lower() if i + 1 <= n else ""
            if v2 in GLOTTAL_VOWELS and len(v2) == 2 and v2[0] == v2[1]:
                out.append(GLOTTAL_VOWELS[v2])
                i += 3
            elif v1 in GLOTTAL_VOWELS and len(v1) == 1:
                out.append(GLOTTAL_VOWELS[v1])
                i += 2
            else:
                out.append("ዕ")
                i += 1
            continue

        if low in "aeiou":
            v2 = s[i : i + 2].lower()
            if v2 in STANDALONE_VOWELS and len(v2) == 2:
                out.append(STANDALONE_VOWELS[v2])
                i += 2
            else:
                out.append(STANDALONE_VOWELS.get(low, ch))
                i += 1
            continue

        digraph = s[i : i + 2].lower()
        if digraph in LATIN_TO_FIDEL_BASE:
            saddis, vmap = LATIN_TO_FIDEL_BASE[digraph]
            v2 = s[i + 2 : i + 4].lower()
            v1 = s[i + 2 : i + 3].lower()
            if v2 in vmap and len(v2) == 2:
                out.append(vmap[v2])
                i += 4
            elif v1 in vmap and len(v1) == 1:
                out.append(vmap[v1])
                i += 3
            else:
                out.append(saddis)
                i += 2
            continue

        if low in SINGLE_CONSONANT_SERIES:
            base_cp = SINGLE_CONSONANT_SERIES[low]
            v2 = s[i + 1 : i + 3].lower()
            v1 = s[i + 1 : i + 2].lower()
            if v2 in LONG_VOWEL_SUFFIX and len(v2) == 2:
                v_char = chr(base_cp + VOWEL_OFFSETS[v2[0]])
                out.append(v_char + LONG_VOWEL_SUFFIX[v2])
                i += 3
            elif v1 in VOWEL_OFFSETS and len(v1) == 1:
                out.append(chr(base_cp + VOWEL_OFFSETS[v1]))
                i += 2
            else:
                out.append(chr(base_cp + 5))
                i += 1
            continue

        out.append(ch)
        i += 1
    return "".join(out)


def analyze_gofatho_word(word: str, db_conn: sqlite3.Connection = None) -> Dict[str, Any]:
    clean = re.sub(r"[^a-zA-Z7ʔ]", "", word).strip()
    lower = clean.lower().replace("ʔ", "7")
    morphemes = []
    stem = lower

    matched_verb = False
    for suf, gloss_form, meaning in VERBAL_SUFFIXES:
        if len(stem) >= len(suf) + 1 and stem.endswith(suf):
            stem = stem[:-len(suf)]
            morphemes.insert(0, {"morpheme": gloss_form, "gloss": meaning, "type": "Verbal Inflection"})
            matched_verb = True
            break

    if not matched_verb:
        for suf, gloss_form, meaning in NOMINAL_SUFFIXES:
            if len(stem) > len(suf) + 1 and stem.endswith(suf):
                stem = stem[:-len(suf)]
                morphemes.insert(0, {"morpheme": gloss_form, "gloss": meaning, "type": "Nominal Case/Number"})
                break

    for dsuf, dform, dmeaning in DERIVATIONAL_SUFFIXES:
        if len(stem) > len(dsuf) + 1 and stem.endswith(dsuf):
            stem = stem[:-len(dsuf)]
            morphemes.insert(0, {"morpheme": dform, "gloss": dmeaning, "type": "Derivational Suffix"})

    lex_match = None
    if db_conn is not None:
        cur = db_conn.cursor()
        cands = [lower, stem, stem + "-", stem + "a", stem + "e", stem + "o", stem + "i"]
        if len(stem) >= 2:
            # MP-06 pre-suffixal gemination restoration & -tt- <-> -th- orthographic alternation
            cands.extend([stem + stem[-1], stem + stem[-1] + "-", stem + stem[-1] + "a", stem + stem[-1] + "e", stem + stem[-1] + "o"])
        if "tt" in stem:
            st_th = stem.replace("tt", "th")
            cands.extend([st_th, st_th + "a", st_th + "e", st_th + "o"])
        if len(stem) >= 3 and stem[-1] in "aeiou" and stem[-2] == stem[-1]:
            # Long final vowel shortened to dictionary citation vowel (e.g. keettaa -> keetta)
            short_v = stem[:-1]
            cands.extend([short_v, short_v.replace("tt", "th"), short_v.replace("tt", "th")[:-1] + "e"])
        for cand in cands:
            row = cur.execute(
                "SELECT id, headword, ipa, pos, english, amharic, source FROM dictionary WHERE lower(headword) = ? OR lower(normalized_form) = ? LIMIT 1",
                (cand, cand)
            ).fetchone()
            if row:
                lex_match = {
                    "id": row[0],
                    "headword": row[1],
                    "ipa": row[2],
                    "pos": row[3],
                    "english": row[4],
                    "amharic": row[5],
                    "source": row[6] or "Sellassie Cheru (2015)",
                }
                break

    morphemes.insert(0, {
        "morpheme": stem,
        "gloss": lex_match["english"] if lex_match else "Lexical Root / Stem",
        "type": f"Root ({lex_match['pos']})" if lex_match else "Root"
    })

    return {
        "surface": word,
        "surface_form": word,
        "fidel": latin_to_gofatho_fidel(word),
        "normalized": lower,
        "root": stem,
        "lexical_match": lex_match,
        "lexicon_entry": lex_match,
        "morphemes": morphemes
    }


# Build reverse Fidel -> Latin table for GofathoScriptTransliterator
_FIDEL_TO_LATIN_MAP: Dict[str, str] = {
    "።": ".", "፣": ",", "፤": ";", "፦": ":",
    "ዓ": "7a", "ዑ": "7u", "ዒ": "7i", "ዔ": "7e", "ዖ": "7o", "ዕ": "7",
    "አ": "a", "ኡ": "u", "ኢ": "i", "እ": "e", "ኦ": "o",
}
for _dig, (_sad, _vmap) in LATIN_TO_FIDEL_BASE.items():
    _FIDEL_TO_LATIN_MAP[_sad] = _dig
    for _vk, _fv in _vmap.items():
        if len(_fv) == 1:
            _FIDEL_TO_LATIN_MAP[_fv] = _dig + _vk
for _c, _base in SINGLE_CONSONANT_SERIES.items():
    _FIDEL_TO_LATIN_MAP[chr(_base + 5)] = _c
    for _vk, _off in VOWEL_OFFSETS.items():
        _FIDEL_TO_LATIN_MAP[chr(_base + _off)] = _c + _vk


def gofatho_fidel_to_latin(text: str) -> str:
    out = []
    for ch in text:
        out.append(_FIDEL_TO_LATIN_MAP.get(ch, ch))
    return "".join(out)


class GofathoScriptTransliterator:
    @staticmethod
    def is_ethiopic(text: str) -> bool:
        return any(
            (0x1200 <= ord(c) <= 0x137F) or (0xAB00 <= ord(c) <= 0xAB2F)
            for c in text
        )

    @staticmethod
    def latin_to_fidel(text: str) -> str:
        return latin_to_gofatho_fidel(text)

    @staticmethod
    def fidel_to_latin(text: str) -> str:
        return gofatho_fidel_to_latin(text)


class GofathoMorphologicalAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def analyze_sentence(self, sentence: str, conn: sqlite3.Connection = None) -> List[Dict[str, Any]]:
        tokens = [t for t in re.findall(r"[A-Za-z7ʔ']+", sentence) if t]
        own_conn = conn is None
        try:
            if own_conn:
                conn = sqlite3.connect(self.db_path)
            results = []
            for tok in tokens:
                res = analyze_gofatho_word(tok, conn)
                lex = res.get("lexical_match") or {}
                affixes = [
                    {"affix": m["morpheme"], "function": m["gloss"], "type": m["type"]}
                    for m in res.get("morphemes", [])[1:]
                ]
                results.append({
                    "surface": res["surface"],
                    "fidel": res["fidel"],
                    "root": lex.get("headword") or res["root"],
                    "lex_id": lex.get("id"),
                    "source": lex.get("source"),
                    "english_gloss": lex.get("english"),
                    "amharic_gloss": lex.get("amharic"),
                    "pos": lex.get("pos"),
                    "affixes": affixes,
                })
            return results
        finally:
            if own_conn and conn:
                conn.close()
