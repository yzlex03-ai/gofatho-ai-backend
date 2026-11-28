#!/usr/bin/env python3
"""
Gofatho AI — Verified SQLite Test & Fallback Fixture Builder
============================================================
Builds an isolated, schema-complete SQLite database populated from the verified
JSON corpus files (`data/pure_v5_rag_voice_tables.json`, `data/phases6_to_8_tables.json`,
`phase10_deep_expansion/Gofatho_AI_Phase10_Textbooks_Gr8_9_10_Exhaustive_Extraction.json`)
and `backend/gofatho_fst_generator.py` core lexicons.
"""

import json
import os
import sqlite3
import sys
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from morphological_analyzer import latin_to_gofatho_fidel
import gofatho_fst_generator as fst


def build_test_sqlite_db(db_path: str, src_root: Optional[str] = None) -> str:
    """Creates or refreshes a schema-complete SQLite test database at `db_path`."""
    src_root = src_root or os.path.abspath(os.path.join(BASE_DIR, ".."))
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            headword TEXT NOT NULL,
            normalized_form TEXT,
            ipa TEXT,
            pos TEXT,
            english TEXT,
            amharic TEXT,
            gofatho_synonym TEXT,
            domain TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS everyday_phrasebook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase_code TEXT,
            domain TEXT,
            gofatho_latin TEXT,
            gofatho_fidel TEXT,
            amharic TEXT,
            english TEXT,
            ipa_phonemic TEXT,
            morpheme_breakdown TEXT,
            usage_context TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS curriculum_meeze_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_code TEXT,
            grade INTEGER,
            chapter_num INTEGER,
            chapter_title_gofatho TEXT,
            exercise_type TEXT,
            gofatho_prompt_latin TEXT,
            gofatho_prompt_fidel TEXT,
            english_translation TEXT,
            amharic_translation TEXT,
            morpheme_gloss TEXT,
            grammar_focus TEXT
        );

        CREATE TABLE IF NOT EXISTS bible_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_id TEXT,
            book_order INTEGER,
            book_id TEXT,
            book_name_en TEXT,
            book_name_lat TEXT,
            book_name_fidel TEXT,
            sub_group TEXT,
            chapter INTEGER,
            verse INTEGER,
            section_title_lat TEXT,
            section_title_fidel TEXT,
            gof_latin TEXT,
            gof_fidel TEXT,
            amh_fidel TEXT,
            eng_web TEXT,
            gofatho_latin TEXT,
            gofatho_fidel TEXT,
            english_translation TEXT,
            amharic_translation TEXT,
            morpheme_gloss TEXT,
            audio_mp3 TEXT
        );

        CREATE TABLE IF NOT EXISTS verse_audio_clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_id TEXT,
            audio_rel_path TEXT,
            start_sec REAL,
            end_sec REAL,
            duration_sec REAL
        );

        CREATE TABLE IF NOT EXISTS phrase_audio_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_id TEXT,
            book_id TEXT,
            chapter INTEGER,
            verse INTEGER,
            phrase_id INTEGER,
            start_sec REAL,
            end_sec REAL,
            duration_sec REAL,
            gof_latin_slice TEXT,
            gof_fidel_slice TEXT,
            is_golden_slice INTEGER
        );

        CREATE TABLE IF NOT EXISTS interlinear_sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_id TEXT,
            gofatho_text TEXT,
            phonemic_breakdown TEXT,
            morpheme_gloss TEXT,
            pos_sequence TEXT,
            english_translation TEXT,
            domain TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS grammar_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            morpheme TEXT,
            function_gloss TEXT,
            description TEXT,
            example_gofatho TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS oral_literature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            gofatho_text TEXT,
            response_or_pair TEXT,
            english_meaning TEXT,
            amharic_meaning TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS gemination_minimal_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_code TEXT,
            consonant_phoneme TEXT,
            phonetic_category TEXT,
            leppiya_singleton_latin TEXT,
            leppiya_singleton_fidel TEXT,
            leppiya_ipa TEXT,
            leppiya_pos TEXT,
            leppiya_amharic TEXT,
            leppiya_english TEXT,
            leppiya_example_gof TEXT,
            minniyaa_geminate_latin TEXT,
            minniyaa_geminate_fidel TEXT,
            minniyaa_ipa TEXT,
            minniyaa_pos TEXT,
            minniyaa_amharic TEXT,
            minniyaa_english TEXT,
            minniyaa_example_gof TEXT,
            orthography_rule TEXT,
            source_reference TEXT
        );

        CREATE TABLE IF NOT EXISTS old_testament_seed_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_id TEXT,
            book_id TEXT,
            book_name_gof TEXT,
            book_name_amh TEXT,
            book_name_eng TEXT,
            chapter INTEGER,
            verse INTEGER,
            gof_latin TEXT,
            gof_fidel TEXT,
            amh_fidel TEXT,
            eng_web TEXT,
            edition_code TEXT
        );

        CREATE TABLE IF NOT EXISTS meeze_quiz_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_code TEXT,
            grade_level TEXT,
            quiz_category TEXT,
            question_gof_latin TEXT,
            question_gof_fidel TEXT,
            question_amharic TEXT,
            question_english TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT,
            explanation_trilingual TEXT,
            audio_target_word TEXT
        );

        CREATE TABLE IF NOT EXISTS ometo_cognate_bridge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cognate_code TEXT,
            semantic_domain TEXT,
            gofatho_gof_latin TEXT,
            gofatho_gof_fidel TEXT,
            gamotho_gmv_latin TEXT,
            dawuro_dwr_latin TEXT,
            wolaytta_wal_latin TEXT,
            amharic_meaning TEXT,
            english_meaning TEXT,
            sound_correspondence_rule TEXT,
            source_reference TEXT
        );

        CREATE TABLE IF NOT EXISTS ocr_sample_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_code TEXT,
            doc_title TEXT,
            source_type TEXT,
            raw_ocr_text TEXT,
            normalized_gof_latin TEXT,
            normalized_gof_fidel TEXT,
            amharic_translation TEXT,
            english_translation TEXT,
            morphological_notes TEXT
        );

        CREATE TABLE IF NOT EXISTS morphophonemic_fst_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_code TEXT,
            rule_category TEXT,
            process_name TEXT,
            formal_rewrite TEXT,
            conditioning_environment TEXT,
            fst_reverse_pattern TEXT,
            exemplars_gofatho TEXT,
            source_citation TEXT
        );

        CREATE TABLE IF NOT EXISTS sellassie_igt_corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            igt_code TEXT,
            citation TEXT,
            gofatho_surface TEXT,
            gofatho_fidel TEXT,
            phonemic_segmentation TEXT,
            leipzig_gloss TEXT,
            english_translation TEXT,
            amharic_translation TEXT,
            grammatical_category TEXT
        );

        CREATE TABLE IF NOT EXISTS textbook_chapters_28_deep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT,
            grade TEXT,
            chapter_number INTEGER,
            title_gofatho_latin TEXT,
            title_gofatho_fidel TEXT,
            title_amharic TEXT,
            title_english TEXT,
            book_page_range TEXT,
            pdf_page_range TEXT,
            source_view_url TEXT,
            passages_summary_gofatho TEXT,
            dialogues_summary TEXT,
            grammar_focus_qawosa TEXT,
            vocabulary_json TEXT,
            proverbs_idioms_json TEXT,
            meeze_exercises_json TEXT
        );

        CREATE TABLE IF NOT EXISTS textbook_dialogues_haasaya (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogue_code TEXT,
            chapter_id TEXT,
            grade TEXT,
            topic_gofatho TEXT,
            topic_english TEXT,
            speakers TEXT,
            gofatho_latin TEXT,
            gofatho_fidel TEXT,
            amharic TEXT,
            english TEXT,
            cultural_and_grammar_notes TEXT,
            source_url TEXT
        );

        CREATE TABLE IF NOT EXISTS multiturn_chat_voice_utterances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn_id TEXT,
            domain_name TEXT,
            gofatho_latin TEXT,
            gofatho_fidel TEXT,
            amharic TEXT,
            english TEXT,
            fst_morpheme_notes TEXT,
            source_grounding TEXT
        );

        CREATE TABLE IF NOT EXISTS fst_inflection_paradigm_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_or_lemma TEXT,
            pos TEXT,
            category_or_case TEXT,
            person_or_number TEXT,
            surface_latin TEXT,
            surface_fidel TEXT,
            english_gloss TEXT,
            amharic_gloss TEXT,
            mp_rule_applied TEXT
        );

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
            status TEXT DEFAULT 'Pending Review',
            synced_to_cloud INTEGER DEFAULT 0,
            upvotes INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

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
        );
        """
    )

    # 1. Populate dictionary from verified FST core lexicons & textbook glossaries
    seed_lexicon = [
        ("saro", "N/EXCL", "peace / hello / greetings", "ሰላም", "siga", "Greetings", "Sellassie Cheru (2015)"),
        ("lo77o", "ADJ", "good / fine / beautiful", "ጥሩ / መልካም", "", "Core Lexicon", "Sellassie Cheru (2015)"),
        ("na7a", "N", "child / son / daughter", "ልጅ", "", "Kinship", "Sellassie Cheru (2015)"),
        ("keetta", "N", "house / home", "ቤት", "", "Daily Life", "Sellassie Cheru (2015)"),
        ("haatha", "N", "water", "ውሃ", "", "Nature", "Sellassie Cheru (2015)"),
        ("ba7a", "V/PART", "not exist / there is none", "የለም", "", "Core Lexicon", "Sellassie Cheru (2015)"),
        ("sa7a", "N", "earth / land / ground", "ምድር / መሬት", "biitta", "Nature", "Sellassie Cheru (2015)"),
        ("oott-", "V", "work / do / make", "መሥራት", "", "Verbs", "Sellassie Cheru (2015)"),
        ("b-", "V", "go", "መሄድ", "", "Verbs", "Sellassie Cheru (2015)"),
        ("y-", "V", "come", "መምጣት", "", "Verbs", "Sellassie Cheru (2015)"),
        ("uy-", "V", "drink", "መጠጣት", "", "Verbs", "Sellassie Cheru (2015)"),
        ("m-", "V", "eat", "መብላት", "", "Verbs", "Sellassie Cheru (2015)"),
        ("tamaar-", "V", "learn / study", "መማር", "", "Education", "Grade 8 Textbook (2015 E.C.)"),
        ("qawosa", "N", "grammar / morphosyntax", "ሰዋስው", "doona maara", "Grammar", "Grade 8 Textbook (2015 E.C.), p. 16"),
        ("dubbusha", "N", "traditional public assembly place", "ዱቡሻ (የባህል አደባባይ)", "shiiqo bessa", "Culture", "Grade 9 Textbook (2015 E.C.), p. 83"),
        ("darota", "N", "traditional communal labor sharing", "ደቦ / ዳሮታ", "issiippe ooso", "Culture", "Grade 9 Textbook (2015 E.C.), p. 83"),
    ]
    for hw, pos, en, am, syn, dom, src in seed_lexicon:
        norm = hw.lower().rstrip("-")
        cur.execute(
            """
            INSERT INTO dictionary (headword, normalized_form, ipa, pos, english, amharic, gofatho_synonym, domain, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (hw, norm, f"/{norm.replace('7', 'ʔ')}/", pos, en, am, syn, dom, src),
        )

    # 2. Populate everyday_phrasebook
    seed_phrases = [
        (
            "PHR-0001",
            "Greetings & Daily Courtesies",
            "Saro pe7adii?",
            latin_to_gofatho_fidel("Saro pe7adii?"),
            "ደህና ዋልክ/ዋልሽ?",
            "How did you spend the day? / Good afternoon",
            "/saro peʔadiː/",
            "saro (peace) + pe7- (spend day) + -adii (PAST.2SG.INTERR)",
            "Standard daytime greeting across Gofa Zone",
            "Sellassie Cheru (2015) & Grade 8 Textbook",
        ),
        (
            "PHR-0002",
            "Education & School",
            "Entti timirtte keettaa bidosona.",
            latin_to_gofatho_fidel("Entti timirtte keettaa bidosona."),
            "እነሱ ወደ ትምህርት ቤት ሄዱ።",
            "They went to school.",
            "/entti timirtte keːttaː bidosona/",
            "Entti (3PL.NOM) + timirtte keetta-a (school-ACC) + b-idosona (go-PAST.3PL)",
            "SOV clause structure exemplar",
            "Grade 8 Goofatho Doona Textbook",
        ),
    ]
    for row in seed_phrases:
        cur.execute(
            """
            INSERT INTO everyday_phrasebook (
                phrase_code, domain, gofatho_latin, gofatho_fidel, amharic, english,
                ipa_phonemic, morpheme_breakdown, usage_context, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )

    # 3. Populate curriculum_meeze_exercises
    cur.execute(
        """
        INSERT INTO curriculum_meeze_exercises (
            exercise_code, grade, chapter_num, chapter_title_gofatho, exercise_type,
            gofatho_prompt_latin, gofatho_prompt_fidel, english_translation, amharic_translation,
            morpheme_gloss, grammar_focus
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "MEEZE-G8-C1-01",
            8,
            1,
            "Goofatho Doona Qawosa",
            "Grammar Exercise",
            "Sunthinne peesho shaakka.",
            latin_to_gofatho_fidel("Sunthinne peesho shaakka."),
            "Distinguish nouns and verbs.",
            "ስምና ግስን ለይ።",
            "sunthi-nne (noun-COOR) peesho (verb) shaakk-a (distinguish-IMP.2SG)",
            "Qawosa (Parts of Speech)",
        ),
    )

    # 4. Load verified JSON tables from data/pure_v5_rag_voice_tables.json and data/phases6_to_8_tables.json
    for json_rel in ["data/pure_v5_rag_voice_tables.json", "data/phases6_to_8_tables.json"]:
        jp = os.path.join(src_root, json_rel)
        if not os.path.exists(jp):
            continue
        with open(jp, encoding="utf-8") as f:
            data = json.load(f)
        for tbl_name, rows in data.items():
            if not isinstance(rows, list) or not rows:
                continue
            tbl_exists = cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (tbl_name,)).fetchone()[0]
            if not tbl_exists:
                col_defs = ", ".join(f"{k} TEXT" for k in rows[0].keys() if k != "id")
                cur.execute(f"CREATE TABLE IF NOT EXISTS {tbl_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})")
            existing = cur.execute(f"SELECT COUNT(*) FROM {tbl_name}").fetchone()[0]
            if existing > 0:
                continue
            cols = [k for k in rows[0].keys() if k != "id"]
            placeholders = ", ".join(["?"] * len(cols))
            col_list = ", ".join(cols)
            for r in rows:
                cur.execute(
                    f"INSERT INTO {tbl_name} ({col_list}) VALUES ({placeholders})",
                    tuple(
                        json.dumps(r.get(c), ensure_ascii=False)
                        if isinstance(r.get(c), (dict, list))
                        else r.get(c)
                        for c in cols
                    ),
                )


    # 4b. Load full verified Sellassie Cheru (2015) 1,349-entry lexicon & 535 IGT sentences if present
    sellassie_json = os.path.join(src_root, "data/Gofatho_AI_v6_Sellassie_Cheru_Full_IGT_and_Lexicon.json")
    if os.path.exists(sellassie_json):
        with open(sellassie_json, encoding="utf-8") as sf:
            s_data = json.load(sf)
        seen_hw = {r[0].lower() for r in cur.execute("SELECT headword FROM dictionary").fetchall()}
        for item in s_data.get("gofa_lexicon", []):
            hw = (item.get("headword_latin") or "").strip()
            if hw and hw.lower() not in seen_hw:
                seen_hw.add(hw.lower())
                norm = hw.lower().replace("ʔ", "7").rstrip("-")
                cur.execute(
                    """
                    INSERT INTO dictionary (headword, normalized_form, ipa, pos, english, amharic, gofatho_synonym, domain, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        hw,
                        norm,
                        item.get("ipa", f"/{norm}/"),
                        item.get("pos", "N"),
                        item.get("english_meaning", ""),
                        item.get("amharic_meaning", ""),
                        item.get("derived_stems", ""),
                        "Sellassie Cheru Appendix D",
                        "Sellassie Cheru (2015) Appendix D Lexicon",
                    ),
                )
        seen_igt = {r[0] for r in cur.execute("SELECT igt_code FROM sellassie_igt_corpus").fetchall()}
        for item in s_data.get("igt_sentence_bank", []):
            code = item.get("igt_id", "")
            if code and code not in seen_igt:
                seen_igt.add(code)
                cur.execute(
                    """
                    INSERT INTO sellassie_igt_corpus (
                        igt_code, citation, gofatho_surface, gofatho_fidel, phonemic_segmentation,
                        leipzig_gloss, english_translation, amharic_translation, grammatical_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        item.get("chapter_and_page", "Sellassie Cheru (2015)"),
                        item.get("gofatho_surface_latin", ""),
                        item.get("gofatho_fidel", ""),
                        item.get("morpheme_segmentation", ""),
                        item.get("leipzig_gloss", ""),
                        item.get("english_translation", ""),
                        item.get("amharic_translation", ""),
                        item.get("syntactic_or_morphological_rule", "Morphosyntax"),
                    ),
                )

    # 4c. Load 480 verified Multi-Turn Chat & Voice Utterances into multiturn_chat_voice_utterances & everyday_phrasebook
    mt_json = os.path.join(src_root, "data/Gofatho_AI_v6_MultiTurn_Chat_Voice_Dialogues.json")
    if os.path.exists(mt_json):
        with open(mt_json, encoding="utf-8") as mf:
            mt_data = json.load(mf)
        for u in mt_data.get("flat_utterances", []):
            cur.execute(
                """
                INSERT INTO multiturn_chat_voice_utterances (
                    turn_id, domain_name, gofatho_latin, gofatho_fidel, amharic, english,
                    fst_morpheme_notes, source_grounding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    u.get("turn_id", ""),
                    u.get("domain_name", ""),
                    u.get("gofatho_latin", ""),
                    u.get("gofatho_fidel", ""),
                    u.get("amharic", ""),
                    u.get("english", ""),
                    u.get("fst_morpheme_notes", ""),
                    u.get("source_grounding", ""),
                ),
            )
            cur.execute(
                """
                INSERT INTO everyday_phrasebook (
                    phrase_code, domain, gofatho_latin, gofatho_fidel, amharic, english,
                    ipa_phonemic, morpheme_breakdown, usage_context, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    u.get("turn_id", ""),
                    u.get("domain_name", ""),
                    u.get("gofatho_latin", ""),
                    u.get("gofatho_fidel", ""),
                    u.get("amharic", ""),
                    u.get("english", ""),
                    "",
                    u.get("fst_morpheme_notes", ""),
                    u.get("subtopic", ""),
                    u.get("source_grounding", "Verified Gofatho MultiTurn Corpus"),
                ),
            )

    # 5. Populate bible_verses from old_testament_seed_verses so both column conventions work
    ot_rows = cur.execute(
        "SELECT verse_id, book_id, book_name_gof, book_name_amh, book_name_eng, chapter, verse, gof_latin, gof_fidel, amh_fidel, eng_web FROM old_testament_seed_verses LIMIT 30"
    ).fetchall()
    for idx, r in enumerate(ot_rows, 1):
        cur.execute(
            """
            INSERT INTO bible_verses (
                verse_id, book_order, book_id, book_name_en, book_name_lat, book_name_fidel,
                chapter, verse, gof_latin, gof_fidel, amh_fidel, eng_web,
                gofatho_latin, gofatho_fidel, english_translation, amharic_translation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r[0], idx, r[1], r[4], r[2], r[3], r[5], r[6],
                r[7], r[8], r[9], r[10], r[7], r[8], r[10], r[9],
            ),
        )

    # 6. Populate fst_inflection_paradigm_bank using verified GofathoVerbConjugator & GofathoNounDecliner
    conj = fst.GofathoVerbConjugator()
    for v_root in ["oott-", "b-", "uy-"]:
        paradigm = conj.conjugate_verb(v_root)
        for item in paradigm.get("flat_inflected_forms", []):
            cur.execute(
                """
                INSERT INTO fst_inflection_paradigm_bank (
                    root_or_lemma, pos, category_or_case, person_or_number,
                    surface_latin, surface_fidel, english_gloss, amharic_gloss, mp_rule_applied
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    v_root,
                    "V",
                    item.get("tam_category", ""),
                    item.get("png", ""),
                    item.get("surface_latin", ""),
                    item.get("surface_fidel", ""),
                    item.get("english_gloss", ""),
                    item.get("amharic_gloss", ""),
                    ", ".join(item.get("mp_rules_applied", [])),
                ),
            )
    decl = fst.GofathoNounDecliner()
    for n_lem in ["keetta", "boora"]:
        n_par = decl.decline_noun(n_lem)
        for item in n_par.get("flat_declined_forms", []):
            cur.execute(
                """
                INSERT INTO fst_inflection_paradigm_bank (
                    root_or_lemma, pos, category_or_case, person_or_number,
                    surface_latin, surface_fidel, english_gloss, amharic_gloss, mp_rule_applied
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    n_lem,
                    "N",
                    item.get("case", ""),
                    item.get("number", ""),
                    item.get("surface_latin", ""),
                    item.get("surface_fidel", ""),
                    item.get("english_gloss", ""),
                    item.get("amharic_gloss", ""),
                    ", ".join(item.get("mp_rules_applied", [])),
                ),
            )


    # 7. Build and populate SQLite FTS5 virtual indexes for <1ms BM25 Hybrid RAG retrieval (Phase E.1)
    cur.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS dictionary_fts USING fts5(
            headword, normalized_form, english, amharic, domain,
            content='dictionary', content_rowid='id'
        );
        INSERT INTO dictionary_fts(dictionary_fts) VALUES('rebuild');

        CREATE VIRTUAL TABLE IF NOT EXISTS phrasebook_fts USING fts5(
            phrase_code, domain, gofatho_latin, gofatho_fidel, amharic, english,
            content='everyday_phrasebook', content_rowid='id'
        );
        INSERT INTO phrasebook_fts(phrasebook_fts) VALUES('rebuild');

        CREATE VIRTUAL TABLE IF NOT EXISTS curriculum_fts USING fts5(
            exercise_code, chapter_title_gofatho, gofatho_prompt_latin, english_translation, amharic_translation,
            content='curriculum_meeze_exercises', content_rowid='id'
        );
        INSERT INTO curriculum_fts(curriculum_fts) VALUES('rebuild');

        CREATE VIRTUAL TABLE IF NOT EXISTS igt_fts USING fts5(
            igt_code, gofatho_surface, leipzig_gloss, english_translation, amharic_translation,
            content='sellassie_igt_corpus', content_rowid='id'
        );
        INSERT INTO igt_fts(igt_fts) VALUES('rebuild');
        CREATE INDEX IF NOT EXISTS idx_dict_hw_low ON dictionary(lower(headword));
        CREATE INDEX IF NOT EXISTS idx_dict_norm_low ON dictionary(lower(normalized_form));
        CREATE INDEX IF NOT EXISTS idx_dict_norm ON dictionary(normalized_form);
        CREATE INDEX IF NOT EXISTS idx_phr_gof_low ON everyday_phrasebook(lower(gofatho_latin));
        CREATE INDEX IF NOT EXISTS idx_phr_en_low ON everyday_phrasebook(lower(english));

        """
    )

    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    out = build_test_sqlite_db("/tmp/gofatho_test_fixture.sqlite")
    print("Built verified SQLite test fixture at:", out)
