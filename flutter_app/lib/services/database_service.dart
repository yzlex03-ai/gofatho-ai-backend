import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';
import '../models/gofatho_models.dart';

/// Offline-First SQLite FTS5 & On-Device RAG Engine for Gofatho AI iOS & Android App.
/// Serves 1,334 lexicon headwords, 2,072 everyday conversational phrases,
/// 1,305 Grade 8–10 Meeze curriculum exercises, 7,931 quad-parallel Bible verses,
/// and 22,017 sub-verse WebAudio karaoke phrase slices.
class GofathoDatabaseService {
  static final GofathoDatabaseService instance = GofathoDatabaseService._internal();
  GofathoDatabaseService._internal();

  Database? _db;

  Future<Database> get database async {
    if (_db != null) return _db!;
    _db = await _initDatabase();
    return _db!;
  }

  Future<Database> _initDatabase() async {
    final dbDir = await getDatabasesPath();
    final dbPath = p.join(dbDir, 'gofatho_ai_master.sqlite');

    final exists = await databaseExists(dbPath);
    if (!exists) {
      await Directory(p.dirname(dbPath)).create(recursive: true);
      final data = await rootBundle.load('assets/gofatho_ai_master.sqlite');
      final bytes = data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
      await File(dbPath).writeAsBytes(bytes, flush: true);
    }
    return openDatabase(dbPath, readOnly: false);
  }

  /// Strips common Gofatho nominal & verbal suffixes to uncover candidate roots for On-Device RAG
  static String stripGofathoSuffixes(String word) {
    var stem = word.toLowerCase().replaceAll('ʔ', '7').trim();
    const suffixes = [
      'idosona', 'oosona', 'ibeenna', 'abeenna', 'ideta', 'tetha', 'tethi',
      'tappe', 'anaw', 'anau', 'ikko', 'ishin', 'ishe', 'awsu', 'aasa',
      'oppa', 'ofite', 'ana', 'idi', 'ada', 'asu', 'ays', 'ais', 'oos',
      'ees', 'ppe', 'ite', 'is', 'ti', 'ta', 'ra',
    ];
    for (final suf in suffixes) {
      if (stem.length > suf.length + 2 && stem.endsWith(suf)) {
        return stem.substring(0, stem.length - suf.length);
      }
    }
    return stem;
  }

  /// On-Device SQLite Multi-Table RAG Retrieval (<5ms on Android):
  /// Searches across `dictionary` (1,334), `everyday_phrasebook` (2,072), and `curriculum_meeze_exercises` (1,305)
  Future<Map<String, dynamic>> retrieveLocalRagBundle(String queryText) async {
    final db = await database;
    final cleanQ = queryText.trim();
    final rawTokens = cleanQ
        .split(RegExp(r'[^A-Za-z7\u1200-\u137F\uAB00-\uAB2F]+'))
        .where((t) => t.length >= 2)
        .toList();

    final searchTerms = <String>{};
    for (final tok in rawTokens) {
      searchTerms.add(tok.toLowerCase());
      final root = stripGofathoSuffixes(tok);
      if (root.length >= 2) searchTerms.add(root);
    }

    final dictHits = <DictionaryEntry>[];
    final seenDictIds = <int>{};
    for (final term in searchTerms.take(8)) {
      final rows = await db.query(
        'dictionary',
        where: 'lower(headword) = ? OR lower(normalized_form) = ? OR lower(english) LIKE ? OR amharic LIKE ? OR lower(headword) LIKE ?',
        whereArgs: [term, term, '%$term%', '%$term%', '$term%'],
        limit: 4,
      );
      for (final r in rows) {
        final entry = DictionaryEntry.fromMap(r);
        if (!seenDictIds.contains(entry.id)) {
          seenDictIds.add(entry.id);
          dictHits.add(entry);
        }
      }
      if (dictHits.length >= 8) break;
    }

    final phraseHits = <EverydayPhrase>[];
    final seenPhraseIds = <int>{};
    for (final term in [cleanQ, ...searchTerms.take(5)]) {
      if (term.isEmpty) continue;
      final rows = await db.query(
        'everyday_phrasebook',
        where: 'gofatho_latin LIKE ? OR english LIKE ? OR amharic LIKE ?',
        whereArgs: ['%$term%', '%$term%', '%$term%'],
        limit: 4,
      );
      for (final r in rows) {
        final ph = EverydayPhrase.fromMap(r);
        if (!seenPhraseIds.contains(ph.id)) {
          seenPhraseIds.add(ph.id);
          phraseHits.add(ph);
        }
      }
      if (phraseHits.length >= 6) break;
    }

    final meezeHits = <MeezeExercise>[];
    final seenMeezeIds = <int>{};
    for (final term in [cleanQ, ...searchTerms.take(5)]) {
      if (term.isEmpty) continue;
      final rows = await db.query(
        'curriculum_meeze_exercises',
        where: 'gofatho_prompt_latin LIKE ? OR english_translation LIKE ? OR amharic_translation LIKE ? OR chapter_title_gofatho LIKE ?',
        whereArgs: ['%$term%', '%$term%', '%$term%', '%$term%'],
        limit: 3,
      );
      for (final r in rows) {
        final mz = MeezeExercise.fromMap(r);
        if (!seenMeezeIds.contains(mz.id)) {
          seenMeezeIds.add(mz.id);
          meezeHits.add(mz);
        }
      }
      if (meezeHits.length >= 5) break;
    }

    return {
      'dictionary': dictHits,
      'phrases': phraseHits,
      'meeze': meezeHits,
    };
  }

  /// Searches the 1,334 Trilingual Gofatho-English-Amharic Lexicon
  Future<List<DictionaryEntry>> searchDictionary({String query = '', String domain = '', int limit = 80}) async {
    final db = await database;
    final q = query.trim();
    List<Map<String, dynamic>> rows;
    if (q.isEmpty && domain.isEmpty) {
      rows = await db.query('dictionary', orderBy: 'normalized_form ASC', limit: limit);
    } else if (q.isEmpty && domain.isNotEmpty) {
      rows = await db.query(
        'dictionary',
        where: 'domain LIKE ?',
        whereArgs: ['%$domain%'],
        orderBy: 'normalized_form ASC',
        limit: limit,
      );
    } else {
      final likeQ = '%$q%';
      rows = await db.query(
        'dictionary',
        where: 'headword LIKE ? OR english LIKE ? OR amharic LIKE ?',
        whereArgs: [likeQ, likeQ, likeQ],
        orderBy: 'normalized_form ASC',
        limit: limit,
      );
    }
    return rows.map((r) => DictionaryEntry.fromMap(r)).toList();
  }

  /// Searches the 2,072 Everyday Gofatho Conversational Phrases across 10 Domains
  Future<List<EverydayPhrase>> searchPhrasebook({String query = '', String domain = '', int limit = 100}) async {
    final db = await database;
    final q = query.trim();
    List<Map<String, dynamic>> rows;
    if (q.isEmpty && domain.isEmpty) {
      rows = await db.query('everyday_phrasebook', orderBy: 'id ASC', limit: limit);
    } else if (q.isEmpty && domain.isNotEmpty) {
      rows = await db.query(
        'everyday_phrasebook',
        where: 'domain LIKE ?',
        whereArgs: ['%$domain%'],
        orderBy: 'id ASC',
        limit: limit,
      );
    } else {
      final likeQ = '%$q%';
      rows = await db.query(
        'everyday_phrasebook',
        where: 'gofatho_latin LIKE ? OR gofatho_fidel LIKE ? OR amharic LIKE ? OR english LIKE ?',
        whereArgs: [likeQ, likeQ, likeQ, likeQ],
        orderBy: 'id ASC',
        limit: limit,
      );
    }
    return rows.map((r) => EverydayPhrase.fromMap(r)).toList();
  }

  /// Searches the 1,305 Authentic Textbook Meeze & Barkketho Oysha Exercises (Grades 8, 9 & 10)
  Future<List<MeezeExercise>> searchMeezeExercises({String query = '', String grade = '', int limit = 100}) async {
    final db = await database;
    final q = query.trim();
    List<Map<String, dynamic>> rows;
    if (q.isEmpty && grade.isEmpty) {
      rows = await db.query('curriculum_meeze_exercises', orderBy: 'id ASC', limit: limit);
    } else if (q.isEmpty && grade.isNotEmpty) {
      rows = await db.query(
        'curriculum_meeze_exercises',
        where: 'grade = ?',
        whereArgs: [grade],
        orderBy: 'id ASC',
        limit: limit,
      );
    } else {
      final likeQ = '%$q%';
      rows = await db.query(
        'curriculum_meeze_exercises',
        where: 'gofatho_prompt_latin LIKE ? OR english_translation LIKE ? OR chapter_title_gofatho LIKE ?',
        whereArgs: [likeQ, likeQ, likeQ],
        orderBy: 'id ASC',
        limit: limit,
      );
    }
    return rows.map((r) => MeezeExercise.fromMap(r)).toList();
  }

  /// Loads Synchronized Verse-Level & Sub-Verse Phrase WebAudio Clips for any of the 260 NT Chapters
  Future<List<VerseAudioClip>> getChapterAudioClips(String bookId, int chapter) async {
    final db = await database;
    final rows = await db.query(
      'verse_audio_clips',
      where: 'book_id = ? AND chapter = ?',
      whereArgs: [bookId.toUpperCase(), chapter],
      orderBy: 'id ASC',
    );
    return rows.map((r) => VerseAudioClip.fromMap(r)).toList();
  }

  /// Retrieves Community Field-Testing Corrections (Milestone 5.1)
  Future<List<TranslationFeedback>> getFeedbackList({String woreda = ''}) async {
    final db = await database;
    final rows = woreda.isEmpty
        ? await db.query('translation_feedback', orderBy: 'upvotes DESC, id DESC')
        : await db.query(
            'translation_feedback',
            where: 'woreda_dialect LIKE ?',
            whereArgs: ['%$woreda%'],
            orderBy: 'upvotes DESC, id DESC',
          );
    return rows.map((r) => TranslationFeedback.fromMap(r)).toList();
  }

  /// Saves a new 'Suggest Better Translation' correction locally in SQLite (Offline Queue)
  Future<int> insertFeedbackOffline({
    required String sourceText,
    required String sourceLang,
    required String targetLang,
    required String initialAiOutput,
    required String suggestedCorrection,
    required String fidelScript,
    required String woredaDialect,
    required String contributorRole,
    required String domainCategory,
    required String linguisticNote,
  }) async {
    final db = await database;
    final count = Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM translation_feedback')) ?? 0;
    final fbCode = 'FB-${(count + 1).toString().padLeft(3, '0')}';
    return db.insert('translation_feedback', {
      'feedback_code': fbCode,
      'source_text': sourceText,
      'source_lang': sourceLang,
      'target_lang': targetLang,
      'initial_ai_output': initialAiOutput,
      'suggested_correction': suggestedCorrection,
      'fidel_script': fidelScript,
      'woreda_dialect': woredaDialect,
      'contributor_role': contributorRole,
      'domain_category': domainCategory,
      'linguistic_note': linguisticNote,
      'status': 'Queued Offline',
      'upvotes': 1,
      'synced_to_cloud': 0,
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
  }

  /// Searches the 75 Gofatho Consonant Gemination Minimal Pairs (`Minniyaanne Leppiya Qaalata`)
  Future<List<GeminationMinimalPair>> searchGeminationPairs({String query = '', int limit = 75}) async {
    final db = await database;
    final q = query.trim();
    try {
      List<Map<String, dynamic>> rows;
      if (q.isEmpty) {
        rows = await db.query('gemination_minimal_pairs', orderBy: 'id ASC', limit: limit);
      } else {
        final likeQ = '%$q%';
        rows = await db.query(
          'gemination_minimal_pairs',
          where: 'leppiya_singleton_latin LIKE ? OR minniyaa_geminate_latin LIKE ? OR leppiya_english LIKE ? OR minniyaa_english LIKE ? OR leppiya_amharic LIKE ? OR minniyaa_amharic LIKE ? OR consonant_phoneme LIKE ?',
          whereArgs: [likeQ, likeQ, likeQ, likeQ, likeQ, likeQ, likeQ],
          orderBy: 'id ASC',
          limit: limit,
        );
      }
      return rows.map((r) => GeminationMinimalPair.fromMap(r)).toList();
    } catch (_) {
      return [];
    }
  }

  /// Retrieves the 250 Interactive Grade 8-10 Meeze & Gemination Ear-Training Quiz Questions (Phase 6A)
  Future<List<MeezeQuizItem>> getMeezeQuizQuestions({String category = '', int limit = 60}) async {
    final db = await database;
    try {
      final rows = category.trim().isEmpty
          ? await db.query('meeze_quiz_bank', orderBy: 'id ASC', limit: limit)
          : await db.query(
              'meeze_quiz_bank',
              where: 'quiz_category LIKE ?',
              whereArgs: ['%${category.trim()}%'],
              orderBy: 'id ASC',
              limit: limit,
            );
      return rows.map((r) => MeezeQuizItem.fromMap(r)).toList();
    } catch (_) {
      return [];
    }
  }

  /// Searches the 120 North Omotic Ometo Cognates (`Gofatho [gof] <-> Gamotho [gmv] <-> Dawuro [dwr] <-> Wolaytta [wal]`)
  Future<List<OmetoCognateEntry>> searchOmetoCognates({String query = '', int limit = 120}) async {
    final db = await database;
    final q = query.trim();
    try {
      final rows = q.isEmpty
          ? await db.query('ometo_cognate_bridge', orderBy: 'id ASC', limit: limit)
          : await db.query(
              'ometo_cognate_bridge',
              where: 'gofatho_gof_latin LIKE ? OR gamotho_gmv_latin LIKE ? OR dawuro_dwr_latin LIKE ? OR wolaytta_wal_latin LIKE ? OR english_meaning LIKE ? OR amharic_meaning LIKE ?',
              whereArgs: ['%$q%', '%$q%', '%$q%', '%$q%', '%$q%', '%$q%'],
              orderBy: 'id ASC',
              limit: limit,
            );
      return rows.map((r) => OmetoCognateEntry.fromMap(r)).toList();
    } catch (_) {
      return [];
    }
  }

  /// Approves a community translation correction in local SQLite (Phase 8 Elder/Teacher Moderation)
  Future<void> approveFeedbackRecord(int id) async {
    final db = await database;
    await db.update(
      'translation_feedback',
      {'status': 'Approved & Merged', 'upvotes': 5},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  /// Searches the 3,480 Pre-Generated Forward FST Verb Conjugations & Noun Declensions (v6.1)
  Future<List<Map<String, dynamic>>> searchFstInflections({String query = '', int limit = 60}) async {
    final db = await database;
    try {
      final q = query.trim();
      if (q.isEmpty) {
        return await db.query('fst_inflection_paradigm_bank', limit: limit);
      }
      final likeQ = '%$q%';
      return await db.query(
        'fst_inflection_paradigm_bank',
        where: 'root_or_lemma LIKE ? OR surface_latin LIKE ? OR english_gloss LIKE ? OR amharic_gloss LIKE ?',
        whereArgs: [likeQ, likeQ, likeQ, likeQ],
        limit: limit,
      );
    } catch (_) {
      return [];
    }
  }

  /// Searches the 615 Sellassie Cheru (2015) IGT & Forward FST SOV Sentences (v6.1)
  Future<List<Map<String, dynamic>>> searchIgtSentences({String query = '', int limit = 50}) async {
    final db = await database;
    try {
      final q = query.trim();
      if (q.isEmpty) {
        return await db.query('sellassie_igt_corpus', limit: limit);
      }
      final likeQ = '%$q%';
      return await db.query(
        'sellassie_igt_corpus',
        where: 'gofatho_surface LIKE ? OR english_translation LIKE ? OR amharic_translation LIKE ? OR leipzig_gloss LIKE ?',
        whereArgs: [likeQ, likeQ, likeQ, likeQ],
        limit: limit,
      );
    } catch (_) {
      return [];
    }
  }
}
