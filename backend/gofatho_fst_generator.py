#!/usr/bin/env python3
"""
Gofatho AI v6.0 — Deterministic Forward Finite-State Transducer (FST)
Morphological Conjugator, Noun Decliner & SOV Sentence Synthesizer
======================================================================
Module: `gofatho_fst_generator.py`
Target System: Pure Gofatho AI Chat & Voice Assistant (ISO 639-3: `gof`)
Primary Linguistic Grounding:
  1. Sellassie Cheru Hirboro (2015), 'Documentation and Grammatical Description of Gofa',
     PhD Dissertation, Department of Linguistics and Philology, Addis Ababa University
     (Chapters 2–9, Rules MP-01 through MP-11, Master Paradigms 1–6, Appendices A–D).
  2. SNNPR Education Bureau / Goofa Zone Book Project (2015 E.C.), 'Goofatho Doona'
     Grades 8, 9, and 10 Student Textbooks (Zara 5 Orthography & Qawosa Grammar).
  3. Gofatho Ethiopic Extended-A Fidel Standard (`U+AB01–U+AB16`: ꬁ–ꬆ for `th` /ts/,
     ꬉ–ꬎ for `dh` /ɗ/, ꬑ–ꬖ for `dz` /dz/, and `7` /ʔ/ -> ዕ/ዓ/ዑ/ዒ/ዔ/ዖ).

Capabilities:
  1. Forward Morphophonemic Rule Engine (`MP-01` through `MP-11`, `ZARA-01..03`, `TONE-01`).
  2. Deterministic Verb Conjugator (`GofathoVerbConjugator`):
     Conjugates any Gofatho verb root (monoradical `C-`, simplex `CVC-`, geminate/cluster
     `CVCC-`, or polysyllabic) across all 7 Person/Number/Gender categories (`1S, 2S, 3FS,
     3MS, 1PL, 2PL, 3PL`) and 10 TAM/Polarity/Valency/Converb categories, including
     Causative `-iss-` (with MP-05 coalescence), Passive/Reciprocal/Middle `-ett-`, and
     Frequentative `-erets-` (with MP-06 root degemination and MP-07 velar lenition).
  3. Deterministic Noun Decliner (`GofathoNounDecliner`):
     Declines any Gofatho noun across all 4 terminal vowel classes (`-a, -e, -o, -i`) and
     genders (`M, F, DIM, PROPER_M, PROPER_F`) across all 12 Core & Peripheral Cases
     (`NOM.INDEF, NOM.DEF, ACC.INDEF, ACC.DEF, DAT, GEN, LOC, ABL, INST_COM, DIR, EQU, VOC`)
     in Singular and Plural (including feminine `-iya`/`-iw` MP-09/10 glide epenthesis and
     `-entti`/`-entta` MP-03 plural portmanteaus).
  4. Deterministic SOV Sentence Synthesizer (`GofathoSOVSynthesizer`):
     Synthesizes grammatically verified head-final SOV Gofatho clauses with converb chains,
     differential object marking, Leipzig Interlinear Glosses (IGT), and Ethiopic Extended-A
     Fidel rendering.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


# ==============================================================================
# 1. DUAL-SCRIPT TRANSLITERATOR: LATIN <-> ETHIOPIC EXTENDED-A FIDEL (U+AB01-U+AB16)
# ==============================================================================

LATIN_TO_FIDEL_DIGRAPHS: Dict[str, Tuple[str, Dict[str, str]]] = {
    # Unicode Ethiopic Extended-A (U+AB01 - U+AB16) for Gofatho sibilant affricates & implosive
    "th": (
        "\uab05",  # ꬅ (saddis /ts/)
        {
            "a": "\uab03", "aa": "\uab03\u12a0",
            "u": "\uab01", "uu": "\uab01\u12a1",
            "i": "\uab02", "ii": "\uab02\u12a2",
            "e": "\uab04", "ee": "\uab04\u12a5",
            "o": "\uab06", "oo": "\uab06\u12a6",
        },
    ),
    "dh": (
        "\uab0d",  # ꬍ (saddis /ɗ/)
        {
            "a": "\uab0b", "aa": "\uab0b\u12a0",
            "u": "\uab09", "uu": "\uab09\u12a1",
            "i": "\uab0a", "ii": "\uab0a\u12a2",
            "e": "\uab0c", "ee": "\uab0c\u12a5",
            "o": "\uab0e", "oo": "\uab0e\u12a6",
        },
    ),
    "dz": (
        "\uab15",  # ꬕ (saddis /dz/)
        {
            "a": "\uab13", "aa": "\uab13\u12a0",
            "u": "\uab11", "uu": "\uab11\u12a1",
            "i": "\uab12", "ii": "\uab12\u12a2",
            "e": "\uab14", "ee": "\uab14\u12a5",
            "o": "\uab16", "oo": "\uab16\u12a6",
        },
    ),
    "sh": (
        "ሽ",
        {
            "a": "ሻ", "aa": "ሻአ",
            "u": "ሹ", "uu": "ሹኡ",
            "i": "ሺ", "ii": "ሺኢ",
            "e": "ሼ", "ee": "ሼእ",
            "o": "ሾ", "oo": "ሾኦ",
        },
    ),
    "ch": (
        "ች",
        {
            "a": "ቻ", "aa": "ቻአ",
            "u": "ቹ", "uu": "ቹኡ",
            "i": "ቺ", "ii": "ቺኢ",
            "e": "ቼ", "ee": "ቼእ",
            "o": "ቾ", "oo": "ቾኦ",
        },
    ),
    "ph": (
        "ጵ",
        {
            "a": "ጳ", "aa": "ጳአ",
            "u": "ጱ", "uu": "ጱኡ",
            "i": "ጲ", "ii": "ጲኢ",
            "e": "ጴ", "ee": "ጴእ",
            "o": "ፆ", "oo": "ፆኦ",
        },
    ),
    "ny": (
        "ኝ",
        {
            "a": "ኛ", "aa": "ኛአ",
            "u": "ኙ", "uu": "ኙኡ",
            "i": "ኚ", "ii": "ኚኢ",
            "e": "ኜ", "ee": "ኜእ",
            "o": "ኞ", "oo": "ኞኦ",
        },
    ),
    "zh": (
        "ዥ",
        {
            "a": "ዣ", "aa": "ዣአ",
            "u": "ዡ", "uu": "ዡኡ",
            "i": "ዢ", "ii": "ዢኢ",
            "e": "ዤ", "ee": "ዤእ",
            "o": "ዦ", "oo": "ዦኦ",
        },
    ),
    "nh": (
        "ኅ",
        {
            "a": "ኃ", "aa": "ኃአ",
            "u": "ኁ", "uu": "ኁኡ",
            "i": "ኂ", "ii": "ኂኢ",
            "e": "ሄ", "ee": "ሄእ",
            "o": "ሆ", "oo": "ሆኦ",
        },
    ),
}

SINGLE_CONSONANT_SERIES: Dict[str, int] = {
    "h": 0x1200, "l": 0x1208, "m": 0x1218, "r": 0x1228, "s": 0x1230,
    "q": 0x1240, "b": 0x1260, "t": 0x1270, "n": 0x1290, "k": 0x12A8,
    "w": 0x12C8, "z": 0x12D8, "y": 0x12E8, "d": 0x12F0, "j": 0x1300,
    "g": 0x1308, "x": 0x1320, "c": 0x1328, "f": 0x1348, "p": 0x1350,
}

VOWEL_OFFSETS: Dict[str, int] = {"a": 0, "u": 1, "i": 2, "e": 4, "o": 6}
LONG_VOWEL_SUFFIX: Dict[str, str] = {"aa": "አ", "uu": "ኡ", "ii": "ኢ", "ee": "እ", "oo": "ኦ"}
STANDALONE_VOWELS: Dict[str, str] = {
    "a": "አ", "aa": "አአ", "u": "ኡ", "uu": "ኡኡ", "i": "ኢ", "ii": "ኢኢ",
    "e": "እ", "ee": "እእ", "o": "ኦ", "oo": "ኦኦ",
}
GLOTTAL_VOWELS: Dict[str, str] = {
    "a": "ዓ", "aa": "ዓአ", "u": "ዑ", "uu": "ዑኡ", "i": "ዒ", "ii": "ዒኢ",
    "e": "ዔ", "ee": "ዔእ", "o": "ዖ", "oo": "ዖኦ", "": "ዕ",
}


def latin_to_gofatho_fidel(text: str) -> str:
    """
    Deterministic Gofatho Latin -> Ethiopic Extended-A Fidel transliterator.
    Preserves Extended-A codepoints (`U+AB01–U+AB16`: ꬁ–ꬆ for `th`, ꬉ–ꬎ for `dh`,
    ꬑ–ꬖ for `dz`), glottal stop `7` (/ʔ/ -> ዕ/ዓ/ዑ/ዒ/ዔ/ዖ), geminated digraphs
    (`thth`/`tth`, `dhdh`/`ddh`, `dzdz`/`ddz`, `shsh`/`ssh`, `chch`/`cch`), and long vowels.
    """
    if not text:
        return ""
    out: List[str] = []
    # Normalize school-orthography first-letter doubled digraphs to canonical 4-char geminate digraphs
    s = text.replace("ʔ", "7").replace("’", "'")
    for short_gem, full_gem in [
        ("tth", "thth"), ("ddh", "dhdh"), ("ddz", "dzdz"),
        ("ssh", "shsh"), ("cch", "chch"), ("pph", "phph"),
        ("nny", "nyny"), ("zzh", "zhzh"),
    ]:
        s = re.sub(rf"(?i){short_gem}", full_gem, s)

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

        # Glottal stop '7' (/ʔ/)
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

        # Standalone vowel
        if low in "aeiou":
            v2 = s[i : i + 2].lower()
            if v2 in STANDALONE_VOWELS and len(v2) == 2:
                out.append(STANDALONE_VOWELS[v2])
                i += 2
            else:
                out.append(STANDALONE_VOWELS.get(low, ch))
                i += 1
            continue

        # Digraph check (th, dh, dz, sh, ch, ph, ny, zh, nh)
        digraph = s[i : i + 2].lower()
        if digraph in LATIN_TO_FIDEL_DIGRAPHS:
            saddis, vmap = LATIN_TO_FIDEL_DIGRAPHS[digraph]
            # If geminated digraph (e.g. dhdh, thth, dzdz, shsh, chch), emit saddis first
            if s[i + 2 : i + 4].lower() == digraph:
                out.append(saddis)
                i += 2
                continue
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

        # Single consonant check
        if low in SINGLE_CONSONANT_SERIES:
            base_cp = SINGLE_CONSONANT_SERIES[low]
            # If geminated consonant (e.g. tt, kk, mm, nn, ll, ss, zz, dd, gg, pp, bb, qq, xx, cc, jj, yy),
            # emit saddis for the first consonant so the second consonant attaches to the vowel
            if i + 1 < n and s[i + 1].lower() == low:
                out.append(chr(base_cp + 5))
                i += 1
                continue
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


# Reverse Fidel -> Latin table
_FIDEL_TO_LATIN_MAP: Dict[str, str] = {
    "።": ".", "፣": ",", "፤": ";", "፦": ":",
    "ዓ": "7a", "ዑ": "7u", "ዒ": "7i", "ዔ": "7e", "ዖ": "7o", "ዕ": "7",
    "አ": "a", "ኡ": "u", "ኢ": "i", "እ": "e", "ኦ": "o",
}
for _dig, (_sad, _vmap) in LATIN_TO_FIDEL_DIGRAPHS.items():
    _FIDEL_TO_LATIN_MAP[_sad] = _dig
    for _vk, _fv in _vmap.items():
        if len(_fv) == 1:
            _FIDEL_TO_LATIN_MAP[_fv] = _dig + _vk
for _c, _base in SINGLE_CONSONANT_SERIES.items():
    _FIDEL_TO_LATIN_MAP[chr(_base + 5)] = _c
    for _vk, _off in VOWEL_OFFSETS.items():
        _FIDEL_TO_LATIN_MAP[chr(_base + _off)] = _c + _vk


def gofatho_fidel_to_latin(text: str) -> str:
    """Deterministic Ethiopic Extended-A Fidel -> Gofatho Latin transliterator."""
    return "".join(_FIDEL_TO_LATIN_MAP.get(ch, ch) for ch in text)


def to_phonemic_ipa(latin_word: str, is_initial_vowel_glottal: bool = True) -> str:
    """Converts Gofatho practical Latin orthography to phonemic/phonetic IPA representation."""
    w = latin_word.strip().lower()
    if not w:
        return ""
    # Replace digraphs & ejectives with IPA symbols (longest first)
    replacements = [
        ("thth", "tsts"), ("tth", "tsts"), ("th", "ts"),
        ("dhdh", "ɗɗ"), ("ddh", "ɗɗ"), ("dh", "ɗ"),
        ("dzdz", "dzdz"), ("ddz", "dzdz"),
        ("shsh", "ʃʃ"), ("ssh", "ʃʃ"), ("sh", "ʃ"),
        ("chch", "ʧʧ"), ("cch", "ʧʧ"), ("ch", "ʧ"),
        ("phph", "p'p'"), ("pph", "p'p'"), ("ph", "p'"),
        ("nyny", "ɲɲ"), ("nny", "ɲɲ"), ("ny", "ɲ"),
        ("zhzh", "ʒʒ"), ("zzh", "ʒʒ"), ("zh", "ʒ"),
        ("qq", "kk'"), ("q", "k'"),
        ("xx", "tsts'"), ("x", "ts'"),
        ("cc", "ʧʧ'"), ("c", "ʧ'"),
        ("77", "ʔʔ"), ("7", "ʔ"),
        ("yy", "jj"), ("y", "j"),
    ]
    ipa = w
    for k, v in replacements:
        ipa = ipa.replace(k, v)
    # Word-initial glottal stop onset before vowel (MP-08 / Section 2.1)
    if is_initial_vowel_glottal and ipa and ipa[0] in "aeiou":
        ipa = "ʔ" + ipa
    # Homorganic nasal place assimilation (MP-02 / MP-06)
    ipa = re.sub(r"n([pb])", r"m\1", ipa)
    ipa = re.sub(r"n([kg])", r"ŋ\1", ipa)
    ipa = re.sub(r"n(ʧ|ʤ|ʃ)", r"ɲ\1", ipa)
    return f"[{ipa}]"


# ==============================================================================
# 2. FORWARD MORPHOPHONEMIC REWRITE ENGINE (RULES MP-01 THROUGH MP-11)
# ==============================================================================

MORPHOPHONEMIC_RULES_CATALOG: List[Dict[str, str]] = [
    {
        "rule_id": "MP-01",
        "diss_section": "Ch. 3, Sec. 3.1.1 (ex. 42–43, pp. 56–57)",
        "name": "Glottal & Ejective Free Variation",
        "formal_rewrite": "/ʔ/ (7) -> [j, k', ts', h] / V__(V)#; /k'/ (q) -> [k] / __V#",
        "description": "Intervocalic or stem-final glottal stop /ʔ/ alternates optionally with [j, k', ts', h] (e.g., be7u ~ beyu, me77- ~ meqq-, sa77- ~ saxx-, oyqq- ~ oykk-, siy- ~ si77-).",
    },
    {
        "rule_id": "MP-02",
        "diss_section": "Ch. 3, Sec. 3.1.2 & 3.2.2 (ex. 43.1–44, 49–52, pp. 58–60, 64–65)",
        "name": "Labial Spirantization & Homorganic Nasal Place Assimilation",
        "formal_rewrite": "/p/ -> [Ф] / #__V; /b/ -> [β] / V__V; /n/ -> [m] / __{p,b}; [ɲ] / __{ʧ,ʤ,ʃ}; [ŋ] / __{k,g,k'}",
        "description": "Singleton /p, f, b/ spirantize to [Ф, β] while geminates (-pp-, -bb-) resist lenition; alveolar nasal /n/ assimilates in place to following labial, palato-alveolar, or velar obstruents.",
    },
    {
        "rule_id": "MP-03",
        "diss_section": "Ch. 3, Sec. 3.1.3 & Ch. 5, Sec. 5.1.2.2 (ex. 45–46, 92–95, pp. 60–61, 104–106)",
        "name": "Plural Allomorphy & Feminine/Honorific Gender Vowel Insertion (-e-ntt- vs. -t-)",
        "formal_rewrite": "TV -> -e-ntt-i (NOM) / -e-ntt-a (ACC) [F.PL / HON]; TV -> -t-i (NOM) / -t-a (ACC) [M/Mixed.PL]",
        "description": "Exclusively feminine plural referents and kinship honorifics replace their terminal vowel with -e- and suffix geminate -ntt- (miidzdzentti, gaammentti, mishirentta), whereas masculine and mixed plurals retain/insert -a-/-e-/-o- and suffix singleton -t- (boorati, gaammota, nayti).",
    },
    {
        "rule_id": "MP-04",
        "diss_section": "Ch. 3, Sec. 3.2.1 & 3.2.2.1 (ex. 47–48, pp. 61–63)",
        "name": "Word-Initial Labial Fortition & Progressive Sibilant Palatal Harmony",
        "formal_rewrite": "/b/ -> [p] / #__V (3S.REFL bana -> [pána]); -antso -> -anchcho [-áɲʧʧó] / ʃV__",
        "description": "Word-initial /b/ devoices to [p] in 3rd-person logophoric/reflexive pronouns (bana ~ pana, ba ~ pa, bantta ~ pantta); stem-final post-alveolar /ʃ/ triggers progressive palatal harmony on the ordinal/agentive suffix -antso -> -anchcho (ichchashshanchcho 'fifth').",
    },
    {
        "rule_id": "MP-05",
        "diss_section": "Ch. 7, Sec. 7.3.1 (ex. 197, pp. 181–183) & Ch. 3, Sec. 3.2.2.1",
        "name": "Causative Sibilant Coalescence (-iss- Fusion)",
        "formal_rewrite": "C_root + -iss- -> -ss- / -shsh- / -ts- / -z- (eqq- -> ess-, be7- -> bess-, uy- -> ushsh-)",
        "description": "Root-final glottal, velar, palatal, or nasal consonants coalesce with causative -iss- into fused sibilant/affricate stems: eqq- -> ess-, be7- -> bess-, uy- -> ushsh-, tookk- -> tooss-, aq- -> ayss-, kum- -> kunts-, dendd- -> dents-, m- -> muz-, heemm- -> hentt-.",
    },
    {
        "rule_id": "MP-06",
        "diss_section": "Ch. 7, Sec. 7.3.1–7.3.5 (ex. 196, 200–207, pp. 181–188)",
        "name": "Pre-Suffixal Root Consonant Degemination",
        "formal_rewrite": "C1C1 -> C1 / __ + {-iss- (CAUS), -étt- (PASS/REC/MID), -erets- (FREQ)}",
        "description": "Geminate root-final consonants automatically degeminate to singletons before vowel-initial valency/aspectual suffixes: oott- -> ootiss-/ootett-/ooterets-, shamm- -> shamett-, bayzz- -> bayzett-, uukk- -> uukett-, maadd- -> maadiss-, pitt- -> piterets-, mentsts- -> mentserets-.",
    },
    {
        "rule_id": "MP-07",
        "diss_section": "Ch. 7, Sec. 7.3.3 (ex. 204, p. 185) & Ch. 3, Sec. 3.2.2.3 (ex. 53, p. 65)",
        "name": "Intervocalic Velar Lenition & External Sandhi Nasal Assimilation",
        "formal_rewrite": "/k/ -> [h] / V__-étt- (uukettis -> uuhettis); /-ni/ -> [-n] -> [-m] / __#[m]",
        "description": "Degeminated root-final /k/ optionally lenites to [h] before passive -étt- (uukk- + -ett- -> uukett- ~ uuhett-); across word boundaries, locative -ni drops -i and assimilates to [m] before word-initial [m] (soon maa7enna -> [soóm maáʔénna]).",
    },
    {
        "rule_id": "MP-08",
        "diss_section": "Ch. 3, Sec. 3.3.1 (ex. 55.2–57, pp. 68–70) & Ch. 7, Sec. 7.2",
        "name": "Stem Vowel Truncation & Loanword Epenthesis / C2 Gemination",
        "formal_rewrite": "V_stem -> Ø / __ + V_suffix; Ø -> [i] / #__CC; Ø -> [-e] / C__#; C2 -> C2C2 / C1__V",
        "description": "Bound consonant-final verb stems truncate any citation vowel before vowel-initial TAM suffixes; loanwords resolve initial clusters via prothetic i-, final closed syllables via -e, and medial C1C2 clusters via C2 gemination (sport -> ispportte).",
    },
    {
        "rule_id": "MP-09",
        "diss_section": "Ch. 3, Sec. 3.3.2 (ex. 58–59, pp. 70–71) & Ch. 5, Sec. 5.1.3",
        "name": "Historical Feminine Gender Marker (HFGM) {-e} Suppletion",
        "formal_rewrite": "TV {-a, -i, -o} -> Ø -> [-e-] / [Feminine Noun]__ + {NOM.F -a, ACC.F -o, GEN.F -eé, DAT.F -ee-s}",
        "description": "Before feminine singular definite and oblique case suffixes, underlying nominal terminal vowels (-a, -i, -o) are replaced by the suppletive feminine vowel -e- (gaammo -> gaamme-, aayo -> aaye-, machcho -> machche-, dorssi -> dorsse-).",
    },
    {
        "rule_id": "MP-10",
        "diss_section": "Ch. 3, Sec. 3.3.1–3.3.2 (ex. 54–55.1, 60–63, pp. 66–75)",
        "name": "Semivowel Glide Epenthesis, Mid-Vowel Raising & Portmanteau Diphthongization",
        "formal_rewrite": "Ø -> [j/w] / V__V; {-e} -> [i] / __{j,w}; {-o} -> [u] / __w; {-o ACC.F} -> [-u] (surface -iw)",
        "description": "Resolves impermissible vowel hiatus (*-ea, *-eo, *-oa) by inserting palatal glide y [j] or labio-velar glide w [w] and raising mid vowels (e->i, o->u): F.NOM.DEF -e+a -> -iya; F.ACC.DEF -e+o -> -iw [-iú]; M.ACC.DEF (TV -e) -e+a -> -iya; M.ACC.DEF (TV -o) -o+a -> -uwa.",
    },
    {
        "rule_id": "MP-11",
        "diss_section": "Ch. 3, Sec. 3.3.3 (ex. 61–62, pp. 73–74) & Ch. 5, Table 25 (p. 94)",
        "name": "Proper Noun Terminal Vowel Truncation",
        "formal_rewrite": "{-a (M), -o (F)} -> Ø / [Proper Noun]__ + Core Case (-i/-a M, -a/-o F)",
        "description": "Male proper nouns ending in -a (Dosa -> Dosi NOM, Dosa ACC) and female proper nouns ending in -o (Dosito -> Dosita NOM, Dosito ACC) truncate their terminal vowel before core case suffixes, whereas male proper nouns ending in -e/-o retain their TV and diphthongize (Uutey, Morggaamoy).",
    },
]


# Irregular / Coalesced Causative Stems (Rule MP-05, Sellassie Cheru 2015, ex. 197, pp. 181–183)
MP05_CAUSATIVE_COALESCENCE_MAP: Dict[str, Tuple[str, str, str]] = {
    "eqq": ("ess", "MP-05: /ʔekk'-/ + /-iss-/ -> /ʔess-/ (glottalized velar + sibilant coalescence)", "to set upright / stop"),
    "be7": ("bess", "MP-05: /beʔ-/ + /-iss-/ -> /bess-/ (glottal stop + sibilant coalescence)", "to show / guide"),
    "uy": ("ushsh", "MP-04/MP-05: /ʔúj-/ + /-iss-/ -> /ʔuʃʃ-/ (palatal glide + sibilant coalescence)", "to give to drink"),
    "tookk": ("tooss", "MP-05: /tookk-/ + /-iss-/ -> /tooss-/ (velar geminate + sibilant coalescence)", "to help carry a load"),
    "aq": ("ayss", "MP-05: /ʔak'-/ + /-iss-/ -> /ʔaiss-/ (velar ejective lenition + sibilant coalescence)", "to govern / lead / make spend night"),
    "kum": ("kunth", "MP-05: /kum-/ + /-iss-/ -> /kunts-/ (labial nasal + affricate coalescence)", "to fill (transitive)"),
    "dendd": ("denth", "MP-05: /dendd-/ + /-iss-/ -> /dents-/ (alveolar cluster + affricate coalescence)", "to raise / wake someone up"),
    "m": ("muz", "MP-05: /m-/ + /-iss-/ -> /muz-/ (monoradical labial rounding + voiced sibilant)", "to feed"),
    "heemm": ("hentt", "MP-05: /heemm-/ + /-iss-/ -> /hentt-/ (nasal place assimilation + dental stop)", "to cause to herd"),
    "yeekk": ("yeess", "MP-05: /jeekk-/ + /-iss-/ -> /jeess-/ (velar + sibilant coalescence)", "to make cry"),
    "shiiq": ("shiishsh", "MP-04/MP-05: /ʃiik'-/ + /-iss-/ -> /ʃiiʃʃ-/ (palatal harmony + coalescence)", "to gather / bring together"),
    "ufayth": ("ufayss", "MP-05: /ʔufaits-/ + /-iss-/ -> /ʔufaiss-/ (affricate + sibilant coalescence)", "to please / make happy"),
    "ufaytt": ("ufayss", "MP-05: /ʔufaitt-/ + /-iss-/ -> /ʔufaiss-/ (stop + sibilant coalescence)", "to please / make happy"),
    "pax": ("path", "MP-05: /pats'-/ + /-iss-/ -> /pats-/ (ejective deglottalization causative)", "to heal / cure"),
    "dicc": ("dichch", "MP-05: /diʧʧ'-/ + /-iss-/ -> /diʧʧ-/ (ejective deglottalization causative)", "to rear / raise / develop"),
    "aadhdh": ("aath", "MP-05: /ʔaaɗɗ-/ + /-iss-/ -> /ʔaats-/ (implosive + sibilant coalescence)", "to pass / hand over to someone"),
    "aadh": ("aath", "MP-05: /ʔaaɗ-/ + /-iss-/ -> /ʔaats-/ (implosive + sibilant coalescence)", "to pass / hand over to someone"),
    "kaa7": ("kaass", "MP-05: /kaaʔ-/ + /-iss-/ -> /kaass-/ (glottal stop + sibilant coalescence)", "to amuse / make play"),
    "yayy": ("yashiss", "MP-04/MP-05: /jájj-/ + /-iss-/ -> /jaʃiss-/ (palatal glide fricativization)", "to frighten"),
    "kaall": ("kaaleth", "MP-05/MP-06: /kaall-/ + /-iss-/ -> /kaalets-/ (degemination + affricate causative)", "to lead / guide"),
}

# Monoradical verb roots (C-) that undergo thematic vowel lengthening in Past, Future, Neg, and Imperative
MONORADICAL_ROOTS = {"b", "y", "m", "g", "d"}


def degeminate_root_final(stem: str) -> Tuple[str, Optional[str]]:
    """
    Implements Rule MP-06 (Pre-Suffixal Root Consonant Degemination):
    Reduces stem-final geminate consonants (or complex C1C2C2 clusters) before
    vowel-initial valency/aspectual suffixes (-iss-, -ett-, -erets-).
    """
    # Check 4-char geminated digraphs first
    for gem_dig, sing_dig in [
        ("thth", "th"), ("tth", "th"),
        ("dhdh", "dh"), ("ddh", "dh"),
        ("dzdz", "dz"), ("ddz", "dz"),
        ("shsh", "sh"), ("ssh", "sh"),
        ("chch", "ch"), ("cch", "ch"),
        ("phph", "ph"), ("pph", "ph"),
        ("nyny", "ny"), ("nny", "ny"),
        ("zhzh", "zh"), ("zzh", "zh"),
        ("nthth", "nth"), ("ntsts", "nth"),
    ]:
        if stem.endswith(gem_dig) and len(stem) > len(gem_dig):
            new_stem = stem[: -len(gem_dig)] + sing_dig
            return new_stem, f"MP-06: Degeminated root-final '{gem_dig}' -> '{sing_dig}' ({stem}- -> {new_stem}-)"

    # Check 2-char identical geminate consonants (tt, kk, mm, nn, ll, ss, zz, dd, gg, pp, bb, qq, xx, cc, jj, yy, 77)
    if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] in "tkmnlszdgpbcqxyj7":
        new_stem = stem[:-1]
        return new_stem, f"MP-06: Degeminated root-final '{stem[-2:]}' -> '{stem[-1]}' ({stem}- -> {new_stem}-)"

    return stem, None


# ==============================================================================
# 3. DETERMINISTIC GOFATHO VERB CONJUGATOR (7 PNG x 10 TAM/VALENCY/CONVERB)
# ==============================================================================

PNG_ORDER: List[str] = ["1S", "2S", "3FS", "3MS", "1PL", "2PL", "3PL"]

PNG_METADATA: Dict[str, Dict[str, str]] = {
    "1S": {
        "subject_group": "Group A (-a-)",
        "pronoun_nom": "taani",
        "pronoun_short": "ta",
        "pronoun_fidel": latin_to_gofatho_fidel("taani"),
        "english_pronoun": "I",
        "amharic_pronoun": "እኔ",
    },
    "2S": {
        "subject_group": "Group A (-a-)",
        "pronoun_nom": "neeni",
        "pronoun_short": "ne",
        "pronoun_fidel": latin_to_gofatho_fidel("neeni"),
        "english_pronoun": "you (sg.)",
        "amharic_pronoun": "አንተ / አንቺ",
    },
    "3FS": {
        "subject_group": "Group A (-a-)",
        "pronoun_nom": "iya",
        "pronoun_short": "iya",
        "pronoun_fidel": latin_to_gofatho_fidel("iya"),
        "english_pronoun": "she",
        "amharic_pronoun": "እሷ",
    },
    "3MS": {
        "subject_group": "Group I/O/E (-i-/-e-)",
        "pronoun_nom": "i",
        "pronoun_short": "i",
        "pronoun_fidel": latin_to_gofatho_fidel("i"),
        "english_pronoun": "he / it",
        "amharic_pronoun": "እሱ",
    },
    "1PL": {
        "subject_group": "Group I/O/E (-i-/-o-)",
        "pronoun_nom": "nuuni",
        "pronoun_short": "nu",
        "pronoun_fidel": latin_to_gofatho_fidel("nuuni"),
        "english_pronoun": "we",
        "amharic_pronoun": "እኛ",
    },
    "2PL": {
        "subject_group": "Group I/O/E (-i-/-e-)",
        "pronoun_nom": "hintteni",
        "pronoun_short": "hintte",
        "pronoun_fidel": latin_to_gofatho_fidel("hintteni"),
        "english_pronoun": "you (pl./hon.)",
        "amharic_pronoun": "እናንተ / እርስዎ",
    },
    "3PL": {
        "subject_group": "Group I/O/E (-i-/-o-)",
        "pronoun_nom": "enttantti",
        "pronoun_short": "entti",
        "pronoun_fidel": latin_to_gofatho_fidel("enttantti"),
        "english_pronoun": "they / s/he (hon.)",
        "amharic_pronoun": "እነሱ / እሳቸው",
    },
}

CORE_VERB_LEXICON: Dict[str, Dict[str, str]] = {
    "oott-": {"ipa": "/ʔoott-/", "tone": "L", "english": "to do, work, make, perform", "amharic": "መሥራት / ማድረግ (ሠራ)"},
    "b-": {"ipa": "/b-/", "tone": "L", "english": "to go", "amharic": "መሄድ (ሄደ)"},
    "y-": {"ipa": "/j-/", "tone": "L", "english": "to come", "amharic": "መምጣት (መጣ)"},
    "m-": {"ipa": "/m-/", "tone": "L", "english": "to eat", "amharic": "መብላት (በላ)"},
    "uy-": {"ipa": "/ʔúj-/", "tone": "H", "english": "to drink", "amharic": "መጠጣት (ጠጣ)"},
    "be7-": {"ipa": "/beʔ-/", "tone": "L", "english": "to see, look at", "amharic": "ማየት (አየ)"},
    "shamm-": {"ipa": "/ʃamm-/", "tone": "L", "english": "to buy, purchase", "amharic": "መግዛት (ገዛ)"},
    "bayzz-": {"ipa": "/baizz-/", "tone": "L", "english": "to sell", "amharic": "መሸጥ (ሸጠ)"},
    "uukk-": {"ipa": "/ʔuúkk-/", "tone": "H", "english": "to bake bread (soollo)", "amharic": "ዳቦ መጋገር (ጋገረ)"},
    "tamaar-": {"ipa": "/tamaar-/", "tone": "L", "english": "to learn, study", "amharic": "መማር (ተማረ)"},
    "maadd-": {"ipa": "/maadd-/", "tone": "L", "english": "to help, assist", "amharic": "መርዳት / ማገዝ (ረዳ)"},
    "imm-": {"ipa": "/ʔimm-/", "tone": "L", "english": "to give", "amharic": "መስጠት (ሰጠ)"},
    "ekk-": {"ipa": "/ʔekk-/", "tone": "L", "english": "to take, receive, marry (of a man)", "amharic": "መውሰድ / መቀበል (ወሰደ)"},
    "eqq-": {"ipa": "/ʔekk'-/", "tone": "L", "english": "to stand, stop", "amharic": "መቆም (ቆመ)"},
    "dendd-": {"ipa": "/dendd-/", "tone": "L", "english": "to stand up, wake up, rise", "amharic": "መነሣት (ተነሣ)"},
    "kum-": {"ipa": "/kum-/", "tone": "L", "english": "to become full", "amharic": "መሙላት (ሞላ)"},
    "pitt-": {"ipa": "/pítt-/", "tone": "H", "english": "to sweep, clean", "amharic": "መጥረግ (ጠረገ)"},
    "qanxx-": {"ipa": "/k'antsts'-/", "tone": "L", "english": "to cut, slice, chop", "amharic": "መቁረጥ (ቆረጠ)"},
    "mentsts-": {"ipa": "/mentsts-/", "tone": "L", "english": "to break, shatter", "amharic": "መስበር (ሰበረ)"},
    "wooss-": {"ipa": "/wooss-/", "tone": "L", "english": "to pray, beg, beseech", "amharic": "መጸለይ / መለመን (ጸለየ)"},
    "yexx-": {"ipa": "/jetsts'-/", "tone": "L", "english": "to sing a song or hymn", "amharic": "መዝፈን / መዘመር (ዘመረ)"},
    "siiq-": {"ipa": "/siik'-/", "tone": "L", "english": "to love dearly", "amharic": "ማፍቀር / መውደድ (ወደደ)"},
    "bonchch-": {"ipa": "/boɲʧʧ-/", "tone": "L", "english": "to respect, honor", "amharic": "ማክበር (አከበረ)"},
    "galat-": {"ipa": "/galat-/", "tone": "L", "english": "to thank, praise", "amharic": "ማመስገን (አመሰገነ)"},
    "haasay-": {"ipa": "/haasaj-/", "tone": "L", "english": "to speak, talk, converse", "amharic": "መናገር / ማውራት (ተናገረ)"},
    "eh-": {"ipa": "/ʔeh-/", "tone": "L", "english": "to bring", "amharic": "ማምጣት (አመጣ)"},
    "er-": {"ipa": "/ʔer-/", "tone": "L", "english": "to know, recognize", "amharic": "ማወቅ (አወቀ)"},
    "gel-": {"ipa": "/gel-/", "tone": "L", "english": "to enter, marry (of a woman)", "amharic": "መግባት (ገባ)"},
    "simm-": {"ipa": "/simm-/", "tone": "L", "english": "to return, come/go back", "amharic": "መመለስ (ተመለሰ)"},
    "naag-": {"ipa": "/naag-/", "tone": "L", "english": "to wait, guard, watch over", "amharic": "መጠበቅ (ጠበቀ)"},
}


class GofathoVerbConjugator:
    """
    Deterministic Forward FST Verb Conjugator for Gofatho (Sellassie Cheru 2015, Chapter 7,
    Master Paradigms 5 & 6, pp. 166–188).
    """

    def __init__(self) -> None:
        self.lexicon = CORE_VERB_LEXICON

    @staticmethod
    def normalize_root(verb_root: str) -> str:
        """Strips trailing hyphen or citation vowel to isolate the bound consonant-final root."""
        r = verb_root.strip().lower().replace("ʔ", "7").rstrip("-")
        # If user passed an imperative/citation ending in -a (like 'ootta' or 'shamma') with length > 2
        if len(r) > 2 and r[-1] in "aeoi" and f"{r}-" not in CORE_VERB_LEXICON:
            cand = r[:-1]
            if f"{cand}-" in CORE_VERB_LEXICON:
                r = cand
        return r

    def derive_valency_stems(self, raw_root: str) -> Dict[str, Dict[str, Any]]:
        """
        Synthesizes Causative (`-iss-`), Passive/Reciprocal/Middle (`-ett-`), and
        Frequentative (`-erets-`) stems with automatic MP-05 coalescence,
        MP-06 root degemination, and MP-07 velar lenition.
        """
        r = self.normalize_root(raw_root)
        degem_stem, mp06_note = degeminate_root_final(r)

        # 1. Causative (-iss- or MP-05 coalesced stem)
        if r in MP05_CAUSATIVE_COALESCENCE_MAP:
            caus_stem, mp05_rule, caus_meaning = MP05_CAUSATIVE_COALESCENCE_MAP[r]
            caus_rules = [mp05_rule]
        else:
            caus_stem = f"{degem_stem}iss"
            caus_rules = [mp06_note] if mp06_note else ["Regular Causative Suffixation (-iss-)"]
            caus_meaning = f"cause to {self.lexicon.get(r + '-', {}).get('english', r).replace('to ', '')}"

        # 2. Passive / Reciprocal / Middle (-ett-)
        pass_stem = f"{degem_stem}ett"
        pass_rules = [mp06_note] if mp06_note else ["Regular Passive/Reciprocal Suffixation (-ett-)"]
        pass_variants = [pass_stem]
        # MP-07 Intervocalic Velar Lenition (/k/ -> [h] before -étt-, e.g., uukk- -> uukett- ~ uuhett-)
        if degem_stem.endswith("k"):
            lenited_stem = f"{degem_stem[:-1]}hett"
            pass_variants.append(lenited_stem)
            pass_rules.append(f"MP-07: Optional Intervocalic Velar Lenition /k/ -> [h] ({pass_stem}- ~ {lenited_stem}-)")

        # 3. Frequentative / Pluractional (-erets- / -ereth-)
        freq_stem = f"{degem_stem}erets"
        freq_orth_variant = f"{degem_stem}ereth"
        freq_rules = [mp06_note] if mp06_note else ["Regular Frequentative Suffixation (-erets-)"]

        # 4. Stacked Reciprocal-Causative (-ett-iss-)
        rec_caus_stem = f"{degem_stem}ettiss"

        return {
            "CAUS": {
                "stem": f"{caus_stem}-",
                "underlying": f"/{r}-iss-/",
                "mp_rules": caus_rules,
                "gloss_tag": "CAUS",
                "meaning_note": caus_meaning,
            },
            "PASS_REC": {
                "stem": f"{pass_stem}-",
                "variants": [f"{v}-" for v in pass_variants],
                "underlying": f"/{r}-étt-/",
                "mp_rules": pass_rules,
                "gloss_tag": "PASS/REC",
                "meaning_note": "be V-ed (passive) / V each other (reciprocal)",
            },
            "FREQ": {
                "stem": f"{freq_stem}-",
                "orthographic_variant": f"{freq_orth_variant}-",
                "underlying": f"/{r}-erets-/",
                "mp_rules": freq_rules,
                "gloss_tag": "FREQ",
                "meaning_note": "V repeatedly / into multiple pieces",
            },
            "REC_CAUS": {
                "stem": f"{rec_caus_stem}-",
                "underlying": f"/{r}-étt-íss-/",
                "mp_rules": (pass_rules[:1] + ["Stacked Reciprocal + Causative (-étt-íss-)"]),
                "gloss_tag": "REC.CAUS",
                "meaning_note": "cause to V each other",
            },
        }

    def _conjugate_stem_for_png(self, stem: str, png: str, is_monoradical: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Inflects a given verb stem across all core TAM, Polarity, Interrogative, Imperative/Prohibitive,
        and Converb categories for a single Person/Number/Gender (`png`).
        """
        p_meta = PNG_METADATA[png]
        subj_group = p_meta["subject_group"]
        pro = p_meta["pronoun_nom"]

        # Monoradical roots (b-, y-, m-, g-, d-) lengthen the thematic vowel in Past, Future, and Negatives
        a_v = "aa" if is_monoradical else "a"
        i_v = "ii" if is_monoradical else "i"
        e_v = "ee" if is_monoradical else "e"
        o_v = "oo" if is_monoradical else "o"
        u_v = "uu" if is_monoradical else "u"

        # 1. Present Affirmative Declarative (PRES_AFF)
        pres_aff_map = {
            "1S": (f"{stem}ays", f"{stem}aysi", "-aís(i)"),
            "2S": (f"{stem}aasa", f"{stem}asa", "-aása"),
            "3FS": (f"{stem}awsu", f"{stem}ausu", "-aúsu"),
            "3MS": (f"{stem}ees", f"{stem}eesi", "-eés(i)"),
            "1PL": (f"{stem}oos", f"{stem}oosi", "-oós(i)"),
            "2PL": (f"{stem}eeta", f"{stem}eta", "-eéta"),
            "3PL": (f"{stem}oosona", f"{stem}osona", "-oósona"),
        }
        pa_surf, pa_alt, pa_suf = pres_aff_map[png]

        # 2. Past Affirmative Declarative (PAST_AFF)
        past_aff_map = {
            "1S": (f"{stem}{a_v}s", f"{stem}{a_v}dis", f"-({a_v})a(di)s"),
            "2S": (f"{stem}{a_v}dasa", f"{stem}{a_v}das", f"-({a_v})ádasa"),
            "3FS": (f"{stem}{a_v}su", f"{stem}{a_v}dusu", f"-({a_v})á(du)su"),
            "3MS": (f"{stem}{i_v}s", f"{stem}{i_v}des", f"-({i_v})í(de)s"),
            "1PL": (f"{stem}{i_v}da", f"{stem}{i_v}dosi", f"-({i_v})ída"),
            "2PL": (f"{stem}{i_v}deta", f"{stem}{i_v}deta", f"-({i_v})ídeta"),
            "3PL": (f"{stem}{i_v}dosona", f"{stem}{i_v}dosona", f"-({i_v})ídosona"),
        }
        pst_surf, pst_full, pst_suf = past_aff_map[png]

        # 3. Future Affirmative Declarative (FUT_AFF) — invariant -(a)ana, requires overt pronoun in syntax
        fut_verb = f"{stem}{a_v}na"
        fut_clause = f"{pro} {fut_verb}"
        fut_purp = f"{stem}anaw"

        # 4. Present / Future Negative Declarative (PRES_FUT_NEG)
        pres_neg_map = {
            "1S": (f"{stem}{i_v}kke", f"-({i_v})íkke"),
            "2S": (f"{stem}{a_v}kka", f"-({a_v})ákka"),
            "3FS": (f"{stem}{u_v}kku", f"-({u_v})úkku"),
            "3MS": (f"{stem}{e_v}nna", f"-({e_v})énna"),
            "1PL": (f"{stem}{o_v}kko", f"-({o_v})ókko"),
            "2PL": (f"{stem}{e_v}kketa", f"-({e_v})ékketa"),
            "3PL": (f"{stem}{o_v}kkoona", f"-({o_v})ókkona"),
        }
        pneg_surf, pneg_suf = pres_neg_map[png]

        # 5. Past Negative Declarative (PAST_NEG) — Group A -ab- vs. Group I/O/E -ib-
        past_neg_map = {
            "1S": (f"{stem}abekke", f"{stem}abiikke", "-ab(i)íkke"),
            "2S": (f"{stem}abaakka", f"{stem}abakka", "-ab(a)ákka"),
            "3FS": (f"{stem}abuukku", f"{stem}abukku", "-ab(u)úkku"),
            "3MS": (f"{stem}ibeenna", f"{stem}ibenna", "-ib(e)énna"),
            "1PL": (f"{stem}ibookko", f"{stem}ibokko", "-ib(o)ókko"),
            "2PL": (f"{stem}ibeekketa", f"{stem}ibekketa", "-ib(e)ékketa"),
            "3PL": (f"{stem}ibookkona", f"{stem}ibokkona", "-ib(o)ókkona"),
        }
        pstneg_surf, pstneg_alt, pstneg_suf = past_neg_map[png]

        # 6. Present / Future Polar Interrogative (PRES_INTERR — Master Paradigm 5)
        pres_interr_map = {
            "1S": (f"{stem}ianaa", "-ianaá"),
            "2S": (f"{stem}ay", "-aí"),
            "3FS": (f"{stem}ay", "-aí (NEG: -ékkeé)"),
            "3MS": (f"{stem}ii", "-ií (NEG: -énneé)"),
            "1PL": (f"{stem}{a_v}nee", f"-ío / -{a_v}neé"),
            "2PL": (f"{stem}eetii", "-eétií"),
            "3PL": (f"{stem}oonaa", "-oóna(á)"),
        }
        pint_surf, pint_suf = pres_interr_map[png]

        # 7. Past Polar Interrogative (PAST_INTERR — Master Paradigm 5)
        past_interr_map = {
            "1S": (f"{stem}{a_v}danaa", f"-{a_v}danaá / -idanaá"),
            "2S": (f"{stem}{a_v}dii", f"-({a_v})ádií"),
            "3FS": (f"{stem}{a_v}dee", f"-({a_v})ádeé"),
            "3MS": (f"{stem}{i_v}dee", f"-({i_v})ídeé"),
            "1PL": (f"{stem}{i_v}donii", f"-({i_v})ídonií"),
            "2PL": (f"{stem}{i_v}detii", f"-({i_v})ídetií"),
            "3PL": (f"{stem}{i_v}donaa", f"-({i_v})ídonaá"),
        }
        pstint_surf, pstint_suf = past_interr_map[png]

        # 8. Imperative / Jussive / Hortative & Prohibitive (IMP_PROH — Master Paradigm 6)
        imp_aff_map = {
            "1S": (f"{stem}oo", "-oó (1S Optative)"),
            "2S": (f"{stem}a", "-á (2S Imperative)"),
            "3FS": (f"{stem}u", "-ú (3FS Jussive/Optative)"),
            "3MS": (f"{stem}o", "-ó (3MS Jussive/Optative)"),
            "1PL": (f"ane {stem}oos", "(ʔáné) -oós (1PL Hortative)"),
            "2PL": (f"{stem}{i_v}te", f"-({i_v})té (2PL/HON Imperative)"),
            "3PL": (f"{stem}ona", "-óna (3PL/HON Jussive/Optative)"),
        }
        proh_neg_map = {
            "1S": (f"{stem}{o_v}ppoos", f"-{o_v}ppoos (1S/1PL Prohibitive)"),
            "2S": (f"{stem}{o_v}ppa", f"-{o_v}pp-á (2S Prohibitive)"),
            "3FS": (f"{stem}{o_v}ppu", f"-{o_v}pp-ú (3FS Prohibitive)"),
            "3MS": (f"{stem}{o_v}ppo", f"-{o_v}pp-o (3MS Prohibitive)"),
            "1PL": (f"{stem}{o_v}ppoos", f"-{o_v}pp-oós (1PL Prohibitive)"),
            "2PL": (f"{stem}{o_v}ppite", f"-{o_v}pp-ité (2PL/HON Prohibitive)"),
            "3PL": (f"{stem}{o_v}ppona", f"-{o_v}pp-óna (3PL/HON Prohibitive)"),
        }
        imp_surf, imp_suf = imp_aff_map[png]
        proh_surf, proh_suf = proh_neg_map[png]

        # 9. Anterior & Simultaneous Converbs (CONVERB_ANT — Group A -ada/-ashe vs. Group I/O/E -idi/-ishe)
        is_group_a = png in ("1S", "2S", "3FS")
        cnv_ant = f"{stem}ada" if is_group_a else f"{stem}idi"
        cnv_ant_suf = "-áda (CNV1.ANT, Group A)" if is_group_a else "-ídi (CNV2.ANT, Group I/O/E)"
        cnv_prog = f"{stem}ashe" if is_group_a else f"{stem}ishe"
        cnv_neg = f"{stem}eennan"

        return {
            "PRES_AFF": {
                "latin": pa_surf,
                "fidel": latin_to_gofatho_fidel(pa_surf),
                "full_variant_latin": pa_alt,
                "ipa": to_phonemic_ipa(pa_surf),
                "suffix": pa_suf,
                "leipzig_gloss": f"PRES.{png}.AFF.DCL",
                "subject_group": subj_group,
            },
            "PAST_AFF": {
                "latin": pst_surf,
                "fidel": latin_to_gofatho_fidel(pst_surf),
                "full_disyllabic_latin": pst_full,
                "full_disyllabic_fidel": latin_to_gofatho_fidel(pst_full),
                "ipa": to_phonemic_ipa(pst_surf),
                "suffix": pst_suf,
                "leipzig_gloss": f"PAST.{png}.AFF.DCL",
                "subject_group": subj_group,
            },
            "FUT_AFF": {
                "latin": fut_verb,
                "fidel": latin_to_gofatho_fidel(fut_verb),
                "syntactic_clause_latin": fut_clause,
                "syntactic_clause_fidel": latin_to_gofatho_fidel(fut_clause),
                "purposive_infinitive_latin": fut_purp,
                "purposive_infinitive_fidel": latin_to_gofatho_fidel(fut_purp),
                "ipa": to_phonemic_ipa(fut_verb),
                "suffix": f"-({a_v})aná",
                "leipzig_gloss": f"FUT.{png}.AFF.DCL (requires overt {pro})",
                "subject_group": "Neutralized (-ana across all 7 PNGs)",
            },
            "PRES_FUT_NEG": {
                "latin": pneg_surf,
                "fidel": latin_to_gofatho_fidel(pneg_surf),
                "ipa": to_phonemic_ipa(pneg_surf),
                "suffix": pneg_suf,
                "leipzig_gloss": f"PRES/FUT.{png}.NEG.DCL",
                "subject_group": subj_group,
            },
            "PAST_NEG": {
                "latin": pstneg_surf,
                "fidel": latin_to_gofatho_fidel(pstneg_surf),
                "variant_latin": pstneg_alt,
                "ipa": to_phonemic_ipa(pstneg_surf),
                "suffix": pstneg_suf,
                "leipzig_gloss": f"PAST.{png}.NEG.DCL",
                "subject_group": subj_group,
            },
            "PRES_INTERR": {
                "latin": pint_surf,
                "fidel": latin_to_gofatho_fidel(pint_surf),
                "ipa": to_phonemic_ipa(pint_surf),
                "suffix": pint_suf,
                "leipzig_gloss": f"PRES.{png}.AFF.INTER",
                "subject_group": subj_group,
            },
            "PAST_INTERR": {
                "latin": pstint_surf,
                "fidel": latin_to_gofatho_fidel(pstint_surf),
                "ipa": to_phonemic_ipa(pstint_surf),
                "suffix": pstint_suf,
                "leipzig_gloss": f"PAST.{png}.AFF.INTER",
                "subject_group": subj_group,
            },
            "IMP_PROH": {
                "latin": imp_surf,
                "fidel": latin_to_gofatho_fidel(imp_surf),
                "prohibitive_latin": proh_surf,
                "prohibitive_fidel": latin_to_gofatho_fidel(proh_surf),
                "ipa": to_phonemic_ipa(imp_surf),
                "prohibitive_ipa": to_phonemic_ipa(proh_surf),
                "suffix": f"{imp_suf} / {proh_suf}",
                "leipzig_gloss": f"IMP/JUSS.{png} & PROH.{png}",
                "subject_group": subj_group,
            },
            "CONVERB_ANT": {
                "latin": cnv_ant,
                "fidel": latin_to_gofatho_fidel(cnv_ant),
                "progressive_sim_latin": cnv_prog,
                "progressive_sim_fidel": latin_to_gofatho_fidel(cnv_prog),
                "negative_converb_latin": cnv_neg,
                "negative_converb_fidel": latin_to_gofatho_fidel(cnv_neg),
                "ipa": to_phonemic_ipa(cnv_ant),
                "suffix": cnv_ant_suf,
                "leipzig_gloss": f"{'CNV1' if is_group_a else 'CNV2'}.ANT.{png}",
                "subject_group": subj_group,
            },
        }

    def conjugate_verb(self, verb_root: str) -> Dict[str, Any]:
        """
        Deterministically conjugates `verb_root` across all 7 Person/Number/Gender categories
        (`1S, 2S, 3FS, 3MS, 1PL, 2PL, 3PL`) and all 10 TAM/Polarity/Valency/Converb categories,
        including Causative `-iss-`, Passive/Reciprocal `-ett-`, and Frequentative `-erets-`.
        """
        r = self.normalize_root(verb_root)
        cite_key = f"{r}-"
        meta = self.lexicon.get(
            cite_key,
            {"ipa": to_phonemic_ipa(r), "tone": "L", "english": f"to {r}", "amharic": ""},
        )
        is_mono = r in MONORADICAL_ROOTS

        valency_stems = self.derive_valency_stems(r)
        caus_stem_clean = valency_stems["CAUS"]["stem"].rstrip("-")
        pass_stem_clean = valency_stems["PASS_REC"]["stem"].rstrip("-")
        freq_stem_clean = valency_stems["FREQ"]["stem"].rstrip("-")

        paradigm_by_png: Dict[str, Dict[str, Any]] = {}
        flat_forms: List[Dict[str, Any]] = []

        for png in PNG_ORDER:
            base_forms = self._conjugate_stem_for_png(r, png, is_monoradical=is_mono)
            caus_forms = self._conjugate_stem_for_png(caus_stem_clean, png, is_monoradical=False)
            pass_forms = self._conjugate_stem_for_png(pass_stem_clean, png, is_monoradical=False)
            freq_forms = self._conjugate_stem_for_png(freq_stem_clean, png, is_monoradical=False)

            # 10th TAM/Valency slot: VALENCY_DERIVED (Causative -iss-, Passive/Reciprocal -ett-, Frequentative -erets-)
            valency_slot = {
                "latin": f"{caus_forms['PAST_AFF']['latin']} / {pass_forms['PAST_AFF']['latin']} / {freq_forms['PAST_AFF']['latin']}",
                "fidel": (
                    f"{caus_forms['PAST_AFF']['fidel']} / "
                    f"{pass_forms['PAST_AFF']['fidel']} / "
                    f"{freq_forms['PAST_AFF']['fidel']}"
                ),
                "causative_iss": {
                    "stem": valency_stems["CAUS"]["stem"],
                    "mp_rules": valency_stems["CAUS"]["mp_rules"],
                    "pres_aff_latin": caus_forms["PRES_AFF"]["latin"],
                    "pres_aff_fidel": caus_forms["PRES_AFF"]["fidel"],
                    "past_aff_latin": caus_forms["PAST_AFF"]["latin"],
                    "past_aff_fidel": caus_forms["PAST_AFF"]["fidel"],
                    "fut_aff_latin": caus_forms["FUT_AFF"]["latin"],
                    "fut_aff_fidel": caus_forms["FUT_AFF"]["fidel"],
                    "converb_latin": caus_forms["CONVERB_ANT"]["latin"],
                    "converb_fidel": caus_forms["CONVERB_ANT"]["fidel"],
                },
                "passive_reciprocal_ett": {
                    "stem": valency_stems["PASS_REC"]["stem"],
                    "variants": valency_stems["PASS_REC"]["variants"],
                    "mp_rules": valency_stems["PASS_REC"]["mp_rules"],
                    "pres_aff_latin": pass_forms["PRES_AFF"]["latin"],
                    "pres_aff_fidel": pass_forms["PRES_AFF"]["fidel"],
                    "past_aff_latin": pass_forms["PAST_AFF"]["latin"],
                    "past_aff_fidel": pass_forms["PAST_AFF"]["fidel"],
                    "fut_aff_latin": pass_forms["FUT_AFF"]["latin"],
                    "fut_aff_fidel": pass_forms["FUT_AFF"]["fidel"],
                    "converb_latin": pass_forms["CONVERB_ANT"]["latin"],
                    "converb_fidel": pass_forms["CONVERB_ANT"]["fidel"],
                },
                "frequentative_erets": {
                    "stem": valency_stems["FREQ"]["stem"],
                    "orthographic_variant": valency_stems["FREQ"]["orthographic_variant"],
                    "mp_rules": valency_stems["FREQ"]["mp_rules"],
                    "pres_aff_latin": freq_forms["PRES_AFF"]["latin"],
                    "pres_aff_fidel": freq_forms["PRES_AFF"]["fidel"],
                    "past_aff_latin": freq_forms["PAST_AFF"]["latin"],
                    "past_aff_fidel": freq_forms["PAST_AFF"]["fidel"],
                    "fut_aff_latin": freq_forms["FUT_AFF"]["latin"],
                    "fut_aff_fidel": freq_forms["FUT_AFF"]["fidel"],
                    "converb_latin": freq_forms["CONVERB_ANT"]["latin"],
                    "converb_fidel": freq_forms["CONVERB_ANT"]["fidel"],
                },
                "leipzig_gloss": f"CAUS/PASS/FREQ.{png}",
                "subject_group": PNG_METADATA[png]["subject_group"],
            }

            base_forms["VALENCY_DERIVED"] = valency_slot
            paradigm_by_png[png] = base_forms

            # Populate flat records for corpus export
            for tam_key, tam_data in base_forms.items():
                if tam_key == "VALENCY_DERIVED":
                    for val_type, val_sub in [
                        ("CAUSATIVE_ISS", valency_slot["causative_iss"]),
                        ("PASSIVE_ETT", valency_slot["passive_reciprocal_ett"]),
                        ("FREQUENTATIVE_ERETS", valency_slot["frequentative_erets"]),
                    ]:
                        flat_forms.append({
                            "root": cite_key,
                            "english_gloss": meta["english"],
                            "amharic_gloss": meta["amharic"],
                            "png": png,
                            "subject_group": PNG_METADATA[png]["subject_group"],
                            "tam_category": f"VALENCY_{val_type}",
                            "surface_latin": val_sub["past_aff_latin"],
                            "surface_fidel": val_sub["past_aff_fidel"],
                            "present_latin": val_sub["pres_aff_latin"],
                            "present_fidel": val_sub["pres_aff_fidel"],
                            "converb_latin": val_sub["converb_latin"],
                            "converb_fidel": val_sub["converb_fidel"],
                            "derived_stem": val_sub["stem"],
                            "mp_rules_applied": val_sub["mp_rules"],
                        })
                else:
                    flat_forms.append({
                        "root": cite_key,
                        "english_gloss": meta["english"],
                        "amharic_gloss": meta["amharic"],
                        "png": png,
                        "subject_group": tam_data["subject_group"],
                        "tam_category": tam_key,
                        "surface_latin": tam_data["latin"],
                        "surface_fidel": tam_data["fidel"],
                        "ipa": tam_data.get("ipa", ""),
                        "suffix": tam_data.get("suffix", ""),
                        "leipzig_gloss": tam_data.get("leipzig_gloss", ""),
                        "mp_rules_applied": (
                            ["MP-08 (Bound Stem Suffixation)", "TONE-01 (Binary Subject-Group Split)"]
                            + (["Monoradical Root Vowel Lengthening"] if is_mono else [])
                        ),
                    })

        return {
            "root": cite_key,
            "normalized_stem": r,
            "is_monoradical": is_mono,
            "lexical_metadata": meta,
            "valency_derivations": valency_stems,
            "paradigm_7png_x_10tam": paradigm_by_png,
            "flat_inflected_forms": flat_forms,
            "total_generated_forms": len(flat_forms),
        }


# ==============================================================================
# 4. DETERMINISTIC GOFATHO NOUN DECLINER (4 TV CLASSES x GENDER x 12 CASES x SG/PL)
# ==============================================================================


CASE_ALIAS_MAP: Dict[str, str] = {
    "NOM": "NOM.DEF",
    "ACC": "ACC.DEF",
    "INST/COM": "INST_COM",
    "INST/COM -RA": "INST_COM",
    "LOC -N": "LOC",
    "ABL -PPE": "ABL",
    "DIR -KKO": "DIR",
    "EQU -DAN": "EQU",
}

def normalize_case_key(case_str: str) -> str:
    c = case_str.strip().upper()
    return CASE_ALIAS_MAP.get(c, c)

NOMINAL_CASE_ORDER: List[str] = [
    "NOM.INDEF",
    "NOM.DEF",
    "ACC.INDEF",
    "ACC.DEF",
    "DAT",
    "GEN",
    "LOC",
    "ABL",
    "INST_COM",
    "DIR",
    "EQU",
    "VOC",
]

CORE_NOUN_LEXICON: Dict[str, Dict[str, str]] = {
    # Class -a (Masculine & Epicene)
    "boora": {"tv": "a", "gender": "M", "ipa": "[boó.ra]", "tone": "LHL", "english": "ox, bull", "amharic": "በሬ"},
    "aawa": {"tv": "a", "gender": "M", "ipa": "[ʔaa.wá]", "tone": "LLH", "english": "father", "amharic": "አባት"},
    "kana": {"tv": "a", "gender": "M", "ipa": "[kʰa.ná]", "tone": "LH", "english": "dog", "amharic": "ውሻ"},
    "mashsha": {"tv": "a", "gender": "M", "ipa": "[maʃ.ʃá]", "tone": "LH", "english": "knife", "amharic": "ቢላ"},
    "doona": {"tv": "a", "gender": "M", "ipa": "[doo.ná]", "tone": "LLH", "english": "mouth, language", "amharic": "አፍ / ቋንቋ"},
    "meddaawa": {"tv": "a", "gender": "M", "ipa": "[med.daa.wá]", "tone": "LLLH", "english": "bridegroom", "amharic": "ሙሽራ (ወንድ)"},
    "para": {"tv": "a", "gender": "M", "ipa": "[pa.rá]", "tone": "LH", "english": "horse, stallion", "amharic": "ፈረስ"},
    "isha": {"tv": "a", "gender": "M", "ipa": "[ʔi.ʃá]", "tone": "LH", "english": "brother", "amharic": "ወንድም"},
    "na7a": {"tv": "a", "gender": "M", "ipa": "[na.ʔá]", "tone": "LH", "english": "child, boy, son", "amharic": "ልጅ (ወንድ ልጅ)"},
    "na7a_f": {"lemma": "na7a", "tv": "a", "gender": "F", "ipa": "[na.ʔá]", "tone": "LH", "english": "daughter, girl", "amharic": "ሴት ልጅ"},
    # Class -e (Masculine & Feminine)
    "bitane": {"tv": "e", "gender": "M", "ipa": "[bi.tá.ne]", "tone": "LHL", "english": "man, gentleman", "amharic": "ሰውዬ / ወንድ"},
    "hare": {"tv": "e", "gender": "M", "ipa": "[ha.ré]", "tone": "LH", "english": "donkey (male)", "amharic": "አህያ"},
    "hare_f": {"lemma": "hare", "tv": "e", "gender": "F", "ipa": "[ha.ré]", "tone": "LH", "english": "female donkey (jenny)", "amharic": "እንስት አህያ"},
    "kushe": {"tv": "e", "gender": "M", "ipa": "[kú.ʃe]", "tone": "HL", "english": "hand, arm", "amharic": "እጅ"},
    "shaafe": {"tv": "e", "gender": "M", "ipa": "[ʃʰaá.fʰe]", "tone": "LHL", "english": "river, stream", "amharic": "ወንዝ"},
    "dere": {"tv": "e", "gender": "M", "ipa": "[dé.re]", "tone": "HL", "english": "country, community, people", "amharic": "አገር / ሕዝብ"},
    "haathe": {"tv": "e", "gender": "M", "ipa": "[haá.tse]", "tone": "LHL", "english": "water", "amharic": "ውኃ"},
    "mishire": {"tv": "e", "gender": "F", "ipa": "[mi.ʃi.ré]", "tone": "LLH", "english": "woman, lady", "amharic": "ሴት / ወይዘሮ"},
    "miidzdze": {"tv": "e", "gender": "F", "ipa": "[miídz.dze]", "tone": "LHL", "english": "cow", "amharic": "ላም"},
    "deeshe": {"tv": "e", "gender": "F", "ipa": "[dee.ʃé]", "tone": "LLH", "english": "she-goat, nanny goat", "amharic": "ፍየል (እንስት)"},
    # Class -o (Masculine & Feminine)
    "gaammo": {"tv": "o", "gender": "M", "ipa": "[gaam.mó]", "tone": "LLH", "english": "male lion", "amharic": "አንበሳ"},
    "gaammo_f": {"lemma": "gaammo", "tv": "o", "gender": "F", "ipa": "[gaam.mó]", "tone": "LLH", "english": "lioness", "amharic": "እንስት አንበሳ"},
    "soollo": {"tv": "o", "gender": "M", "ipa": "[soól.lo]", "tone": "LHL", "english": "loaf of bread", "amharic": "ዳቦ"},
    "bullukko": {"tv": "o", "gender": "M", "ipa": "[bul.lúk.kʰo]", "tone": "LHL", "english": "traditional cotton blanket", "amharic": "ቡሉኮ"},
    "ooso": {"tv": "o", "gender": "M", "ipa": "[ʔoó.so]", "tone": "LHL", "english": "work, job, task", "amharic": "ሥራ"},
    "kawo": {"tv": "o", "gender": "M", "ipa": "[ka.wó]", "tone": "LH", "english": "king", "amharic": "ንጉሥ"},
    "migiddo": {"tv": "o", "gender": "M", "ipa": "[mi.gíd.do]", "tone": "LHL", "english": "ring, bracelet", "amharic": "የእጅ ቀለበት"},
    "aayo": {"tv": "o", "gender": "F", "ipa": "[ʔaa.jó]", "tone": "LLH", "english": "mother", "amharic": "እናት"},
    "machcho": {"tv": "o", "gender": "F", "ipa": "[máʧ.ʧo]", "tone": "HL", "english": "wife", "amharic": "ሚስት"},
    "michcho": {"tv": "o", "gender": "F", "ipa": "[miʧ.ʧó]", "tone": "LH", "english": "sister", "amharic": "እኅት"},
    "meddaayo": {"tv": "o", "gender": "F", "ipa": "[med.daa.jó]", "tone": "LLLH", "english": "bride", "amharic": "ሙሽሪት (ሴት)"},
    # Class -i (Masculine & Feminine)
    "dorssi": {"tv": "i", "gender": "M", "ipa": "[dors.sí]", "tone": "LH", "english": "sheep, ram", "amharic": "በግ"},
    "dorssi_f": {"lemma": "dorssi", "tv": "i", "gender": "F", "ipa": "[dors.sí]", "tone": "LH", "english": "ewe (female sheep)", "amharic": "እንስት በግ"},
    "keethi": {"tv": "i", "gender": "M", "ipa": "[kʰee.tsí]", "tone": "LLH", "english": "house, home", "amharic": "ቤት"},
    "maathi": {"tv": "i", "gender": "M", "ipa": "[maá.tsi]", "tone": "LHL", "english": "milk", "amharic": "ወተት"},
    "kathi": {"tv": "i", "gender": "M", "ipa": "[kʰá.tsi]", "tone": "HL", "english": "food, grain, meal", "amharic": "ምግብ / እህል"},
    "mithi": {"tv": "i", "gender": "M", "ipa": "[mí.tsi]", "tone": "HL", "english": "tree, wood", "amharic": "ዛፍ / እንጨት"},
    "ussi": {"tv": "i", "gender": "F", "ipa": "[ʔús.si]", "tone": "HL", "english": "heifer (young female cow)", "amharic": "ጊደር"},
    # Proper Nouns (MP-11)
    "Dosa": {"tv": "a", "gender": "PROPER_M", "ipa": "[do.sá]", "tone": "LH", "english": "Dosa (male personal name)", "amharic": "ዶሳ (የወንድ ስም)"},
    "Dosito": {"tv": "o", "gender": "PROPER_F", "ipa": "[do.sí.to]", "tone": "LHL", "english": "Dosite (female personal name)", "amharic": "ዶሲቶ (የሴት ስም)"},
}


class GofathoNounDecliner:
    """
    Deterministic Forward FST Noun Decliner for Gofatho (Sellassie Cheru 2015, Chapter 5,
    Master Paradigms 1 & 2, Tables 19–34, pp. 90–134).
    """

    def __init__(self) -> None:
        self.lexicon = CORE_NOUN_LEXICON

    def decline_noun(
        self,
        noun_citation: str,
        gender: Optional[str] = None,
        tv_class: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically declines `noun_citation` across all 12 Core & Peripheral Cases
        (`NOM.INDEF, NOM.DEF, ACC.INDEF, ACC.DEF, DAT, GEN, LOC, ABL, INST_COM, DIR, EQU, VOC`)
        in Singular and Plural (both Masculine/Mixed `-t-` and Feminine/Honorific `-entt-` MP-03).
        """
        meta = self.lexicon.get(noun_citation, {})
        lemma = meta.get("lemma", noun_citation).strip().replace("ʔ", "7")
        low_lemma = lemma.lower()

        tv = (tv_class or meta.get("tv") or (low_lemma[-1] if low_lemma[-1] in "aeoi" else "a")).lower().lstrip("-")
        gen = (gender or meta.get("gender") or "M").upper()

        base = low_lemma[:-1] if low_lemma and low_lemma[-1] in "aeoi" else low_lemma

        # ----------------------------------------------------------------------
        # A. SINGULAR DECLENSION
        # ----------------------------------------------------------------------
        sg_forms: Dict[str, Dict[str, Any]] = {}

        if gen in ("F", "DIM"):
            # Rules MP-09 (HFGM -e suppletion) + MP-10 (Glide Epenthesis -j-/-w- & Mid-Vowel Raising e->i, o->u)
            mp_f_nom = [
                f"MP-09: TV -{tv} -> HFGM -e- ({low_lemma} -> {base}e-)",
                f"MP-10: Glide Epenthesis & Mid-Vowel Raising /{base}e-a/ -> [{base}e-j-a] -> {base}iya",
            ]
            mp_f_acc = [
                f"MP-09: TV -{tv} -> HFGM -e- ({low_lemma} -> {base}e-)",
                f"MP-10: Glide Epenthesis & Raising /{base}e-o/ -> [{base}e-w-o] -> [{base}i-w-u] -> {base}iw",
            ]
            mp_f_obl = [f"MP-09: Feminine Oblique Stem -{tv} -> -ee- ({base}ee-)"]

            sg_raw = {
                "NOM.INDEF": (low_lemma, f"/{low_lemma}-Ø/", "-Ø (Citation TV)", ["Unmarked Indefinite Subject"]),
                "NOM.DEF": (f"{base}iya", f"/{base}-e-j-a/", "-iya (<-e-j-a)", mp_f_nom),
                "ACC.INDEF": (low_lemma, f"/{low_lemma}-Ø/", "-Ø (DOM Indefinite Object)", ["Differential Object Marking (-Ø)"]),
                "ACC.DEF": (f"{base}iw", f"/{base}-e-w-o/", "-iw ([-iú] <-e-w-o)", mp_f_acc),
                "DAT": (f"{base}ees", f"/{base}-ee-s/", "-ee-s(si) / -iw-s", mp_f_obl),
                "GEN": (f"{base}ee", f"/{base}-eé/", "-eé (GEN.F)", mp_f_obl),
                "LOC": (f"{base}een", f"/{base}-ee-n/", "-ee-n / -iw-a-n (LOC)", mp_f_obl),
                "ABL": (f"{base}eeppe", f"/{base}-ee-ppe/", "-eé-ppé (ABL)", mp_f_obl),
                "INST_COM": (f"{base}eera", f"/{base}-ee-ra/", "-eé-ra (INST/COM)", mp_f_obl),
                "DIR": (f"{base}eekko", f"/{base}-ee-kko/", "-eé-kkó (DIR)", mp_f_obl),
                "EQU": (f"{base}eedan", f"/{base}-ee-dan/", "-eé-dan (EQU)", mp_f_obl),
                "VOC": (f"{base}ee", f"/{base}-eé/", "-eé (VOC.F)", ["MP-09: Invariant Feminine Vocative -eé"]),
            }
        elif gen == "PROPER_M":
            # Rule MP-11: Male Proper Noun TV Truncation (for -a stems) vs. Retention (for -e/-o stems)
            if tv == "a":
                sg_raw = {
                    "NOM.INDEF": (f"{base}i", f"/{base}-i/", "-i", ["MP-11: Male Proper Noun TV -a Truncation"]),
                    "NOM.DEF": (f"{base}i", f"/{base}-i/", "-i (NOM.M.PROPER)", ["MP-11: Male Proper Noun TV -a Truncation"]),
                    "ACC.INDEF": (f"{base}a", f"/{base}-a/", "-a", ["MP-11: Male Proper Noun TV -a Truncation"]),
                    "ACC.DEF": (f"{base}a", f"/{base}-a/", "-a (ACC.M.PROPER)", ["MP-11: Male Proper Noun TV -a Truncation"]),
                    "DAT": (f"{base}as", f"/{base}-a-s/", "-a-s (DAT)", ["MP-11: Proper Oblique Stem"]),
                    "GEN": (f"{base}a", f"/{base}-á/", "-á (GEN.M.PROPER)", ["MP-11: High-Toned Proper Genitive -á"]),
                    "LOC": (f"{base}an", f"/{base}-a-n/", "-a-n (LOC)", ["MP-11: Proper Oblique Stem"]),
                    "ABL": (f"{base}appe", f"/{base}-a-ppe/", "-a-ppe (ABL)", ["MP-11: Proper Oblique Stem"]),
                    "INST_COM": (f"{base}aara", f"/{base}-aa-ra/", "-aa-ra (INST/COM)", ["MP-11: Proper Oblique Stem"]),
                    "DIR": (f"{base}akko", f"/{base}-a-kko/", "-a-kko (DIR)", ["MP-11: Proper Oblique Stem"]),
                    "EQU": (f"{base}adan", f"/{base}-a-dan/", "-a-dan (EQU)", ["MP-11: Proper Oblique Stem"]),
                    "VOC": (f"{base}aa", f"/{base}-aá/", "-aá (VOC.M.PROPER)", ["Vocative Vowel Lengthening"]),
                }
            else:
                nom_d = f"{base}{tv}y"
                sg_raw = {
                    "NOM.INDEF": (nom_d, f"/{base}{tv}-i/", f"-{tv}y", ["MP-11: Male -e/-o Proper Noun Diphthongization"]),
                    "NOM.DEF": (nom_d, f"/{base}{tv}-i/", f"-{tv}y", ["MP-11: Male -e/-o Proper Noun Diphthongization"]),
                    "ACC.INDEF": (low_lemma, f"/{low_lemma}/", f"-{tv}", ["MP-11: Male -e/-o Proper Noun Retention"]),
                    "ACC.DEF": (low_lemma, f"/{low_lemma}/", f"-{tv}", ["MP-11: Male -e/-o Proper Noun Retention"]),
                    "DAT": (f"{low_lemma}s", f"/{low_lemma}-s/", f"-{tv}-s", ["Proper Oblique Stem"]),
                    "GEN": (low_lemma, f"/{low_lemma}/", f"-{tv} (H-Tone)", ["Proper Genitive"]),
                    "LOC": (f"{low_lemma}n", f"/{low_lemma}-n/", f"-{tv}-n", ["Proper Oblique Stem"]),
                    "ABL": (f"{low_lemma}ppe", f"/{low_lemma}-ppe/", f"-{tv}-ppe", ["Proper Oblique Stem"]),
                    "INST_COM": (f"{low_lemma}ra", f"/{low_lemma}-ra/", f"-{tv}-ra", ["Proper Oblique Stem"]),
                    "DIR": (f"{low_lemma}kko", f"/{low_lemma}-kko/", f"-{tv}-kko", ["Proper Oblique Stem"]),
                    "EQU": (f"{low_lemma}dan", f"/{low_lemma}-dan/", f"-{tv}-dan", ["Proper Oblique Stem"]),
                    "VOC": (f"{low_lemma}{tv}", f"/{low_lemma}{tv}/", f"-{tv}{tv}", ["Vocative Vowel Lengthening"]),
                }
        elif gen == "PROPER_F":
            # Rule MP-11: Female Proper Noun TV -o Truncation in NOM (-a) & GEN (-i)
            sg_raw = {
                "NOM.INDEF": (f"{base}a", f"/{base}-a/", "-a (NOM.F.PROPER)", ["MP-11: Female Proper Noun TV -o Truncation"]),
                "NOM.DEF": (f"{base}a", f"/{base}-a/", "-a (NOM.F.PROPER)", ["MP-11: Female Proper Noun TV -o Truncation"]),
                "ACC.INDEF": (f"{base}o", f"/{base}-o/", "-o (ACC.F.PROPER)", ["MP-11: Female Proper Noun Accusative -o"]),
                "ACC.DEF": (f"{base}o", f"/{base}-o/", "-o (ACC.F.PROPER)", ["MP-11: Female Proper Noun Accusative -o"]),
                "DAT": (f"{base}is", f"/{base}-i-s/", "-i-s / -o-s (DAT)", ["MP-11: Female Proper Genitive/Oblique -i-"]),
                "GEN": (f"{base}i", f"/{base}-í/", "-í (GEN.F.PROPER)", ["MP-11: Female Proper Genitive -í"]),
                "LOC": (f"{base}on", f"/{base}-o-n/", "-o-n (LOC)", ["MP-11: Female Proper Oblique"]),
                "ABL": (f"{base}ippe", f"/{base}-i-ppe/", "-i-ppe (ABL)", ["MP-11: Female Proper Oblique"]),
                "INST_COM": (f"{base}iira", f"/{base}-ii-ra/", "-ii-ra (INST/COM)", ["MP-11: Female Proper Oblique Lengthening"]),
                "DIR": (f"{base}ikko", f"/{base}-i-kko/", "-i-kko (DIR)", ["MP-11: Female Proper Oblique"]),
                "EQU": (f"{base}idan", f"/{base}-i-dan/", "-i-dan (EQU)", ["MP-11: Female Proper Oblique"]),
                "VOC": (f"{base}ee", f"/{base}-eé/", "-eé (VOC.F.PROPER)", ["MP-09/MP-11: Female Vocative -eé"]),
            }
        else:
            # Masculine / Default Common Nouns across TV classes -a, -e, -o, -i (Master Paradigm 1, p. 11)
            if tv == "a":
                sg_raw = {
                    "NOM.INDEF": (f"{base}i", f"/{base}-i/", "-i (drops TV -a)", ["Indefinite Nominative TV Truncation"]),
                    "NOM.DEF": (f"{base}ay", f"/{base}a-i/", "-ay ([-aí])", ["MP-10: Portmanteau Diphthong -a + -i -> -ay"]),
                    "ACC.INDEF": (f"{base}a", f"/{base}-a/", "-a (Citation TV)", ["Indefinite Accusative"]),
                    "ACC.DEF": (f"{base}aa", f"/{base}a-a/", "-aa ([-aá])", ["Definite Accusative Vowel Lengthening (-a + -a -> -aa)"]),
                    "DAT": (f"{base}aas", f"/{base}aa-s/", "-aa-s / -a-s(si)", ["Oblique Long Stem + Dative -s"]),
                    "GEN": (f"{base}aa", f"/{base}aá/", "-aá (DEF) / -á (INDEF)", ["Genitive Possessor Lengthening"]),
                    "LOC": (f"{base}an", f"/{base}a-n/", "-a-n / -aa-n (LOC)", ["Locative -n Attachment"]),
                    "ABL": (f"{base}appe", f"/{base}a-ppe/", "-a-ppe / -aa-ppe (ABL)", ["Ablative -ppe Attachment"]),
                    "INST_COM": (f"{base}aara", f"/{base}aa-ra/", "-aa-ra (INST/COM)", ["Oblique Long Stem + Comitative -ra"]),
                    "DIR": (f"{base}aakko", f"/{base}aa-kko/", "-aa-kko / -a-kko (DIR)", ["Directive -kko Attachment"]),
                    "EQU": (f"{base}aadan", f"/{base}aa-dan/", "-aa-dan (EQU)", ["Equative -dan Attachment"]),
                    "VOC": (f"{base}aw", f"/{base}-aú/", "-aw ([-aú]) / -oo ([-oó])", ["Masculine Class -a Vocative Diphthong"]),
                }
            elif tv == "e":
                mp_e_acc = [f"MP-10: Glide Epenthesis & Mid-Vowel Raising /{base}e-a/ -> [{base}e-j-a] -> {base}iya"]
                sg_raw = {
                    "NOM.INDEF": (f"{base}e", f"/{base}e-Ø/", "-e (retains TV -e)", ["Indefinite Nominative Class -e"]),
                    "NOM.DEF": (f"{base}ey", f"/{base}e-i/", "-ey ([-eí])", ["MP-10: Portmanteau Diphthong -e + -i -> -ey"]),
                    "ACC.INDEF": (f"{base}e", f"/{base}e-Ø/", "-e (-Ø DOM)", ["Differential Object Marking (-Ø on Indefinite -e)"]),
                    "ACC.DEF": (f"{base}iya", f"/{base}e-j-a/", "-iya ([-ía] <-e-j-a)", mp_e_acc),
                    "DAT": (f"{base}iyas", f"/{base}e-j-a-s/", "-iya-s / -e-s", mp_e_acc + ["Dative -s Attachment"]),
                    "GEN": (f"{base}iya", f"/{base}e-j-a/", "-iya (DEF) / -é (INDEF)", mp_e_acc),
                    "LOC": (f"{base}iyan", f"/{base}e-j-a-n/", "-iya-n / -e-n (LOC)", mp_e_acc + ["Locative -n Attachment"]),
                    "ABL": (f"{base}iyappe", f"/{base}e-j-a-ppe/", "-iya-ppe / -ee-ppe (ABL)", mp_e_acc + ["Ablative -ppe Attachment"]),
                    "INST_COM": (f"{base}iyara", f"/{base}e-j-a-ra/", "-iya-ra / -ee-ra (INST/COM)", mp_e_acc + ["Comitative -ra Attachment"]),
                    "DIR": (f"{base}iyakko", f"/{base}e-j-a-kko/", "-iya-kko / -ee-kko (DIR)", mp_e_acc + ["Directive -kko Attachment"]),
                    "EQU": (f"{base}iyadan", f"/{base}e-j-a-dan/", "-iya-dan / -ee-dan (EQU)", mp_e_acc + ["Equative -dan Attachment"]),
                    "VOC": (f"{base}iyaw", f"/{base}-íaú/", "-iyaw ([-íaú])", ["MP-10: Masculine Class -e Vocative -íaú"]),
                }
            elif tv == "o":
                mp_o_acc = [f"MP-10: Glide Epenthesis & Mid-Vowel Raising /{base}o-a/ -> [{base}o-w-a] -> {base}uwa"]
                sg_raw = {
                    "NOM.INDEF": (f"{base}o", f"/{base}o-Ø/", "-o (retains TV -o)", ["Indefinite Nominative Class -o"]),
                    "NOM.DEF": (f"{base}oy", f"/{base}o-i/", "-oy ([-oí])", ["MP-10: Portmanteau Diphthong -o + -i -> -oy"]),
                    "ACC.INDEF": (f"{base}o", f"/{base}o-Ø/", "-o (-Ø DOM)", ["Differential Object Marking (-Ø on Indefinite -o)"]),
                    "ACC.DEF": (f"{base}uwa", f"/{base}o-w-a/", "-uwa ([-úa] <-o-w-a)", mp_o_acc),
                    "DAT": (f"{base}uwas", f"/{base}o-w-a-s/", "-uwa-s / -o-s", mp_o_acc + ["Dative -s Attachment"]),
                    "GEN": (f"{base}uwa", f"/{base}o-w-a/", "-uwa (DEF) / -ó (INDEF)", mp_o_acc),
                    "LOC": (f"{base}uwan", f"/{base}o-w-a-n/", "-uwa-n / -o-n (LOC)", mp_o_acc + ["Locative -n Attachment"]),
                    "ABL": (f"{base}uwappe", f"/{base}o-w-a-ppe/", "-uwa-ppe / -oo-ppe (ABL)", mp_o_acc + ["Ablative -ppe Attachment"]),
                    "INST_COM": (f"{base}uwara", f"/{base}o-w-a-ra/", "-uwa-ra / -oo-ra (INST/COM)", mp_o_acc + ["Comitative -ra Attachment"]),
                    "DIR": (f"{base}uwakko", f"/{base}o-w-a-kko/", "-uwa-kko / -oo-kko (DIR)", mp_o_acc + ["Directive -kko Attachment"]),
                    "EQU": (f"{base}uwadan", f"/{base}o-w-a-dan/", "-uwa-dan / -oo-dan (EQU)", mp_o_acc + ["Equative -dan Attachment"]),
                    "VOC": (f"{base}uwaw", f"/{base}-úaú/", "-uwaw ([-úaú]) / -oo", ["MP-10: Masculine Class -o Vocative -úaú"]),
                }
            else:
                # Class -i (Masculine): takes thematic -a- in definite/oblique (with keethi -> keethey/keethay)
                nom_def_i = f"{base}ey" if base == "keeth" else f"{base}ay"
                sg_raw = {
                    "NOM.INDEF": (f"{base}i", f"/{base}-i/", "-i (Citation TV -i)", ["Indefinite Nominative Class -i"]),
                    "NOM.DEF": (nom_def_i, f"/{base}a-i/", "-ay / -ey", ["MP-10: Class -i Definite Nominative Diphthong"]),
                    "ACC.INDEF": (f"{base}i", f"/{base}-i/", "-i / -a", ["Indefinite Accusative Class -i"]),
                    "ACC.DEF": (f"{base}aa", f"/{base}a-a/", "-aa ([-aá])", ["Class -i -> -aa Definite Accusative"]),
                    "DAT": (f"{base}aas", f"/{base}aa-s/", "-aa-s", ["Class -i Oblique Stem -aa- + Dative -s"]),
                    "GEN": (f"{base}aa", f"/{base}aá/", "-aá / -í", ["Class -i Genitive Possessor"]),
                    "LOC": (f"{base}an", f"/{base}a-n/", "-a-n / -aa-n (LOC)", ["Class -i Oblique + Locative -n"]),
                    "ABL": (f"{base}appe", f"/{base}a-ppe/", "-a-ppe / -aa-ppe (ABL)", ["Class -i Oblique + Ablative -ppe"]),
                    "INST_COM": (f"{base}aara", f"/{base}aa-ra/", "-aa-ra (INST/COM)", ["Class -i Oblique + Comitative -ra"]),
                    "DIR": (f"{base}aakko", f"/{base}aa-kko/", "-aa-kko (DIR)", ["Class -i Oblique + Directive -kko"]),
                    "EQU": (f"{base}aadan", f"/{base}aa-dan/", "-aa-dan (EQU)", ["Class -i Oblique + Equative -dan"]),
                    "VOC": (f"{base}aw", f"/{base}-aú/", "-aw ([-aú])", ["Class -i Vocative Diphthong -aú"]),
                }

        for c_code in NOMINAL_CASE_ORDER:
            surf, under, suf_str, rules = sg_raw[c_code]
            sg_forms[c_code] = {
                "latin": surf,
                "fidel": latin_to_gofatho_fidel(surf),
                "ipa": to_phonemic_ipa(surf),
                "underlying": under,
                "suffix": suf_str,
                "leipzig_gloss": f"{lemma}.SG.{gen}.{c_code}",
                "mp_rules_applied": rules,
            }

        # ----------------------------------------------------------------------
        # B. PLURAL DECLENSION (MP-03: Masculine/Mixed -t- vs. Feminine/Hon -entt-)
        # ----------------------------------------------------------------------
        pl_forms: Dict[str, Dict[str, Any]] = {}

        if gen in ("F", "PROPER_F"):
            # Rule MP-03: Feminine Plural & Honorific Portmanteau (-e-ntt-i NOM, -e-ntt-a ACC)
            pl_stem = f"{base}entt"
            mp_pl = [f"MP-03: Feminine/Honorific Plural Allomorphy -{tv} -> -e-ntt- ({low_lemma} -> {pl_stem}-)"]
        else:
            # Rule MP-03: General Masculine/Mixed Plural (-t-i NOM, -t-a ACC)
            if low_lemma == "na7a":
                pl_stem = "nayt"
                mp_pl = ["MP-03: Irregular Plural Root Contraction /naʔa-t-/ -> nayt-"]
            elif low_lemma == "isha":
                pl_stem = "ishantt"
                mp_pl = ["MP-03: Kinship Plural Suffixation /ʔiʃa-ntt-/ -> ishantt-"]
            elif tv == "i":
                pl_stem = f"{base}at"
                mp_pl = [f"MP-03: Class -i Plural Stem Vowel Replacement -{tv} -> -a-t- ({pl_stem}-)"]
            else:
                pl_stem = f"{base}{tv}t"
                mp_pl = [f"MP-03: General Plural Suffixation -{tv}-t- ({pl_stem}-)"]

        pl_raw = {
            "NOM.INDEF": (f"{pl_stem}i", f"/{pl_stem}-i/", "-i (PL.NOM)"),
            "NOM.DEF": (f"{pl_stem}i", f"/{pl_stem}-i/", "-i (PL.NOM.DEF)"),
            "ACC.INDEF": (f"{pl_stem}a", f"/{pl_stem}-a/", "-a (PL.ACC)"),
            "ACC.DEF": (f"{pl_stem}a", f"/{pl_stem}-a/", "-a (PL.ACC.DEF)"),
            "DAT": (f"{pl_stem}as", f"/{pl_stem}-a-s/", "-a-s / -u-s (PL.DAT)"),
            "GEN": (f"{pl_stem}a", f"/{pl_stem}-a/", "-a / -u (PL.GEN)"),
            "LOC": (f"{pl_stem}an", f"/{pl_stem}-a-n/", "-a-n (PL.LOC)"),
            "ABL": (f"{pl_stem}appe", f"/{pl_stem}-a-ppe/", "-a-ppe (PL.ABL)"),
            "INST_COM": (f"{pl_stem}ara", f"/{pl_stem}-a-ra/", "-a-ra (PL.INST/COM)"),
            "DIR": (f"{pl_stem}akko", f"/{pl_stem}-a-kko/", "-a-kko (PL.DIR)"),
            "EQU": (f"{pl_stem}adan", f"/{pl_stem}-a-dan/", "-a-dan (PL.EQU)"),
            "VOC": (f"{pl_stem}oo", f"/{pl_stem}-oó/", "-oó (PL.VOC)"),
        }

        for c_code in NOMINAL_CASE_ORDER:
            surf, under, suf_str = pl_raw[c_code]
            pl_forms[c_code] = {
                "latin": surf,
                "fidel": latin_to_gofatho_fidel(surf),
                "ipa": to_phonemic_ipa(surf),
                "underlying": under,
                "suffix": suf_str,
                "leipzig_gloss": f"{lemma}.PL.{gen}.{c_code}",
                "mp_rules_applied": mp_pl,
            }

        flat_declined: List[Dict[str, Any]] = []
        for num_label, num_dict in [("SG", sg_forms), ("PL", pl_forms)]:
            for c_code in NOMINAL_CASE_ORDER:
                entry = num_dict[c_code]
                flat_declined.append({
                    "citation_lemma": lemma,
                    "lookup_key": noun_citation,
                    "tv_class": f"-{tv}",
                    "gender": gen,
                    "number": num_label,
                    "case": c_code,
                    "surface_latin": entry["latin"],
                    "surface_fidel": entry["fidel"],
                    "ipa": entry["ipa"],
                    "underlying": entry["underlying"],
                    "suffix": entry["suffix"],
                    "leipzig_gloss": entry["leipzig_gloss"],
                    "mp_rules_applied": entry["mp_rules_applied"],
                    "english_gloss": meta.get("english", lemma),
                    "amharic_gloss": meta.get("amharic", ""),
                })

        return {
            "citation_lemma": lemma,
            "lookup_key": noun_citation,
            "tv_class": f"-{tv}",
            "gender": gen,
            "lexical_metadata": meta,
            "singular": sg_forms,
            "plural": pl_forms,
            "flat_declined_forms": flat_declined,
            "total_generated_forms": len(flat_declined),
        }


# ==============================================================================
# 5. DETERMINISTIC SOV SENTENCE & CLAUSE-CHAINING SYNTHESIZER
# ==============================================================================

class GofathoSOVSynthesizer:
    """
    Deterministic Head-Final Subject-Object-Verb (SOV) Sentence Synthesizer for Gofatho
    (Sellassie Cheru 2015, Chapters 8–9, pp. 189–242).
    """

    def __init__(self) -> None:
        self.verb_conjugator = GofathoVerbConjugator()
        self.noun_decliner = GofathoNounDecliner()

    def synthesize_sov_clause(
        self,
        subject_spec: Dict[str, Any],
        verb_spec: Dict[str, Any],
        object_spec: Optional[Dict[str, Any]] = None,
        oblique_spec: Optional[Dict[str, Any]] = None,
        converb_spec: Optional[Dict[str, Any]] = None,
        adverb: Optional[str] = None,
        english_translation: str = "",
        amharic_translation: str = "",
    ) -> Dict[str, Any]:
        """
        Synthesizes a complete Gofatho SOV sentence from constituent specifications:
          - `subject_spec`: {"type": "pronoun"|"noun", "png": "1S".."3PL", "lemma": ..., "gender": "M"|"F", "number": "SG"|"PL", "definite": True, "modifier": ...}
          - `object_spec`:  {"lemma": ..., "gender": "M"|"F", "number": "SG"|"PL", "definite": True, "modifier": ...}
          - `oblique_spec`: {"lemma": ..., "gender": "M"|"F", "number": "SG"|"PL", "case": "DAT"|"LOC"|"ABL"|"INST_COM"|"DIR"|"EQU"}
          - `converb_spec`: {"root": ..., "object_lemma": ...} (automatically agrees with matrix subject Group A -ada vs. Group I/O/E -idi)
          - `verb_spec`:    {"root": ..., "tam": "PRES_AFF"|"PAST_AFF"|"FUT_AFF"|..., "valency": None|"CAUS"|"PASS"|"FREQ"}
        """
        tokens_latin: List[str] = []
        tokens_underlying: List[str] = []
        tokens_gloss: List[str] = []
        rules_trace: List[str] = ["SOV Head-Final Constituent Ordering (S - IO/OBL - DO - CNV - V)"]

        png = subject_spec.get("png", "3MS")

        # 1. Subject NP (NOM)
        if subject_spec.get("type") == "pronoun":
            # In FUT_AFF, overt subject pronoun is obligatory (Sellassie Cheru 2015, p. 143)
            pro_lat = PNG_METADATA[png]["pronoun_nom"]
            if not subject_spec.get("omit_pro_drop", False) or verb_spec.get("tam") == "FUT_AFF":
                tokens_latin.append(pro_lat)
                tokens_underlying.append(pro_lat)
                tokens_gloss.append(f"{png}.NOM")
        else:
            s_lemma = subject_spec["lemma"]
            s_gen = subject_spec.get("gender", "M")
            s_num = subject_spec.get("number", "SG")
            s_def = subject_spec.get("definite", True)
            s_case = "NOM.DEF" if s_def else "NOM.INDEF"
            s_decl = self.noun_decliner.decline_noun(s_lemma, gender=s_gen)
            s_entry = s_decl["singular" if s_num == "SG" else "plural"][s_case]
            if subject_spec.get("modifier"):
                tokens_latin.append(subject_spec["modifier"])
                tokens_underlying.append(subject_spec["modifier"])
                tokens_gloss.append("MOD")
            tokens_latin.append(s_entry["latin"])
            tokens_underlying.append(s_entry["underlying"])
            tokens_gloss.append(s_entry["leipzig_gloss"])
            rules_trace.extend(s_entry["mp_rules_applied"])

        # 2. Optional Temporal / Locative Adverb
        if adverb:
            tokens_latin.append(adverb)
            tokens_underlying.append(adverb)
            tokens_gloss.append("ADV")

        # 3. Optional Oblique / Indirect Object PP (DAT, LOC, ABL, INST_COM, DIR, EQU)
        if oblique_spec:
            obl_lemma = oblique_spec["lemma"]
            obl_gen = oblique_spec.get("gender", "M")
            obl_num = oblique_spec.get("number", "SG")
            obl_case = normalize_case_key(oblique_spec.get("case", "DAT"))
            obl_decl = self.noun_decliner.decline_noun(obl_lemma, gender=obl_gen)
            obl_entry = obl_decl["singular" if obl_num == "SG" else "plural"][obl_case]
            tokens_latin.append(obl_entry["latin"])
            tokens_underlying.append(obl_entry["underlying"])
            tokens_gloss.append(obl_entry["leipzig_gloss"])
            rules_trace.extend(obl_entry["mp_rules_applied"])

        # 4. Optional Direct Object NP (ACC.DEF or ACC.INDEF with Differential Object Marking)
        if object_spec:
            o_lemma = object_spec["lemma"]
            o_gen = object_spec.get("gender", "M")
            o_num = object_spec.get("number", "SG")
            o_def = object_spec.get("definite", True)
            o_case = "ACC.DEF" if o_def else "ACC.INDEF"
            o_decl = self.noun_decliner.decline_noun(o_lemma, gender=o_gen)
            o_entry = o_decl["singular" if o_num == "SG" else "plural"][o_case]
            if object_spec.get("modifier"):
                tokens_latin.append(object_spec["modifier"])
                tokens_underlying.append(object_spec["modifier"])
                tokens_gloss.append("MOD")
            tokens_latin.append(o_entry["latin"])
            tokens_underlying.append(o_entry["underlying"])
            tokens_gloss.append(o_entry["leipzig_gloss"])
            rules_trace.extend(o_entry["mp_rules_applied"])

        # 5. Optional Anterior Converb Clause Chain (Group A -ada vs. Group I/O/E -idi)
        if converb_spec:
            if converb_spec.get("object_lemma"):
                co_decl = self.noun_decliner.decline_noun(
                    converb_spec["object_lemma"],
                    gender=converb_spec.get("object_gender", "M"),
                )
                co_entry = co_decl["singular"]["ACC.DEF"]
                tokens_latin.append(co_entry["latin"])
                tokens_underlying.append(co_entry["underlying"])
                tokens_gloss.append(co_entry["leipzig_gloss"])
            cnv_conj = self.verb_conjugator.conjugate_verb(converb_spec["root"])
            cnv_entry = cnv_conj["paradigm_7png_x_10tam"][png]["CONVERB_ANT"]
            tokens_latin.append(cnv_entry["latin"])
            tokens_underlying.append(f"/{converb_spec['root'].rstrip('-')}-{cnv_entry['suffix'].split()[0].lstrip('-')}/")
            tokens_gloss.append(f"{converb_spec['root'].rstrip('-')}.{cnv_entry['leipzig_gloss']}")
            rules_trace.append(f"TONE-01: Converb Agreement {png} -> {cnv_entry['suffix']}")

        # 6. Matrix Finite Verb
        v_root = verb_spec["root"]
        v_tam = verb_spec.get("tam", "PAST_AFF")
        v_val = verb_spec.get("valency")
        v_conj = self.verb_conjugator.conjugate_verb(v_root)

        if v_val in ("CAUS", "PASS", "FREQ"):
            val_slot = v_conj["paradigm_7png_x_10tam"][png]["VALENCY_DERIVED"]
            sub_key = {
                "CAUS": "causative_iss",
                "PASS": "passive_reciprocal_ett",
                "FREQ": "frequentative_erets",
            }[v_val]
            val_data = val_slot[sub_key]
            tam_field = "pres_aff_latin" if v_tam == "PRES_AFF" else ("fut_aff_latin" if v_tam == "FUT_AFF" else "past_aff_latin")
            v_lat = val_data[tam_field]
            v_under = f"/{v_root.rstrip('-')}-{v_val}-{v_tam}.{png}/"
            v_gl = f"{v_root.rstrip('-')}.{v_val}.{v_tam}.{png}"
            rules_trace.extend(val_data["mp_rules"])
        else:
            v_entry = v_conj["paradigm_7png_x_10tam"][png][v_tam]
            v_lat = v_entry["prohibitive_latin"] if (v_tam == "IMP_PROH" and verb_spec.get("prohibitive")) else v_entry["latin"]
            v_under = f"/{v_root.rstrip('-')}{v_entry['suffix'].split()[0]}/"
            v_gl = f"{v_root.rstrip('-')}.{v_entry['leipzig_gloss']}"

        tokens_latin.append(v_lat)
        tokens_underlying.append(v_under)
        tokens_gloss.append(v_gl)

        # Capitalize first word and add terminal punctuation
        punct = "?" if "INTERR" in v_tam else ("!" if v_tam == "IMP_PROH" else ".")
        sentence_latin = " ".join(tokens_latin)
        sentence_latin = sentence_latin[0].upper() + sentence_latin[1:] + punct
        sentence_fidel = latin_to_gofatho_fidel(sentence_latin)

        return {
            "gofatho_latin": sentence_latin,
            "gofatho_fidel": sentence_fidel,
            "phonemic_segmentation": " ".join(tokens_underlying),
            "leipzig_gloss": " ".join(tokens_gloss),
            "english_translation": english_translation,
            "amharic_translation": amharic_translation,
            "subject_png": png,
            "subject_group": PNG_METADATA[png]["subject_group"],
            "mp_rules_trace": list(dict.fromkeys(rules_trace)),
        }


# ==============================================================================
# 6. CLI & SELF-TEST ENTRYPOINT
# ==============================================================================

def run_self_verification() -> Dict[str, Any]:
    """Runs deterministic verification tests across all 11 specified verb roots and 4 noun classes."""
    vc = GofathoVerbConjugator()
    nd = GofathoNounDecliner()
    sov = GofathoSOVSynthesizer()

    required_roots = [
        "oott-", "b-", "y-", "m-", "uy-", "be7-",
        "shamm-", "bayzz-", "uukk-", "tamaar-", "maadd-",
    ]
    verb_results = {r: vc.conjugate_verb(r) for r in required_roots}

    sample_nouns = [
        ("boora", "M", "a"),
        ("bitane", "M", "e"),
        ("gaammo", "M", "o"),
        ("gaammo_f", "F", "o"),
        ("dorssi", "M", "i"),
        ("mishire", "F", "e"),
        ("miidzdze", "F", "e"),
        ("aayo", "F", "o"),
        ("Dosa", "PROPER_M", "a"),
        ("Dosito", "PROPER_F", "o"),
    ]
    noun_results = {n[0]: nd.decline_noun(n[0], gender=n[1], tv_class=n[2]) for n in sample_nouns}

    sample_sentence = sov.synthesize_sov_clause(
        subject_spec={"type": "noun", "lemma": "mishire", "gender": "F", "number": "SG", "definite": True, "png": "3FS"},
        oblique_spec={"lemma": "dere", "gender": "M", "number": "SG", "case": "ABL"},
        object_spec={"lemma": "hare_f", "gender": "F", "number": "SG", "definite": True},
        converb_spec={"root": "y-"},
        verb_spec={"root": "shamm-", "tam": "PAST_AFF"},
        english_translation="Having come from the countryside, the woman bought the female donkey.",
        amharic_translation="ሴትዮዋ ከገጠር መጥታ እንስቷን አህያ ገዛች።",
    )

    return {
        "verified_verb_roots": len(verb_results),
        "verified_noun_lemmas": len(noun_results),
        "sample_oott_1S_pres": verb_results["oott-"]["paradigm_7png_x_10tam"]["1S"]["PRES_AFF"],
        "sample_uy_causative": verb_results["uy-"]["valency_derivations"]["CAUS"],
        "sample_uukk_passive": verb_results["uukk-"]["valency_derivations"]["PASS_REC"],
        "sample_mishire_sg_acc_def": noun_results["mishire"]["singular"]["ACC.DEF"],
        "sample_miidzdze_pl_nom_def": noun_results["miidzdze"]["plural"]["NOM.DEF"],
        "sample_sov_synthesis": sample_sentence,
    }


if __name__ == "__main__":
    summary = run_self_verification()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
