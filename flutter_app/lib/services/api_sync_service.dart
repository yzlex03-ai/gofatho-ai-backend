import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/gofatho_models.dart';
import 'database_service.dart';
import 'g2p_transliterator.dart';

/// Unified 3-Mode Hybrid AI Engine for Gofatho AI (Android & iOS — v6.2):
///   1. Option A (Direct On-Device SQLite RAG + Google Gemini 2.5 Flash API)
///   2. Option B (Cloud FastAPI v6.2 Hybrid RAG Server at `https://gofatho-ai-backend-1.onrender.com`)
///   3. Option C (100% Offline SQLite FTS5 RAG + Verified Morphological Synthesis with strict anti-hallucination uncertainty disclosure)
class GofathoApiSyncService {
  static const String defaultProductionBackendUrl = 'https://gofatho-ai-backend-1.onrender.com';
  static const Duration renderColdStartTimeout = Duration(seconds: 35);

  static final GofathoApiSyncService instance = GofathoApiSyncService._internal();
  factory GofathoApiSyncService({String? baseUrl}) {
    if (baseUrl != null && baseUrl.isNotEmpty) {
      instance.baseUrl = baseUrl;
    }
    return instance;
  }
  GofathoApiSyncService._internal();

  String baseUrl = defaultProductionBackendUrl;
  String geminiApiKey = '';
  String geminiModel = 'gemini-2.5-flash';
  bool lastCloudConnected = false;
  String lastBackendStatusNote = 'Ready (Render Cloud + Offline SQLite RAG)';

  static const String _gofathoSystemPrompt = '''
You are Gofatho AI (Goofatho), an expert native Gofatho (ISO 639-3: gof, North Omotic Ometo cluster, Gofa Zone, South Ethiopia — Sawla, Bulqi/Geze Gofa, Laha/Melekoza, Beto/Zala, Dembba Gofa, Oyda, Uba Debretsehay) linguist, teacher, translator, and cultural assistant.

CRITICAL GRAMMATICAL & ANTI-HALLUCINATION RULES (Sellassie Cheru 2015 & Grade 8-10 Goofatho Doona Textbooks):
1. Strict SOV (Subject-Object-Verb) constituent order: finite main verb MUST come at the end of the clause.
2. Pronouns (Nom/Acc/Poss): Taani/Tana/Ta (1SG), Neeni/Nena/Ne (2SG), I/A/A (3MSG), A/O/I (3FSG), Nuuni/Nuna/Nu (1PL), Intte/Inttena/Intte (2PL), Entti/Enttena/Entta (3PL).
3. Case & Postpositions: Nominative -y/-i, Accusative -a, Dative -s/-ko, Ablative -ppe ('from'), Locative/Instrumental -n/-ra, Abstract Nominalizer -tetha ('-ness').
4. Verbal Agreement: Present/Habitual (-ais/-ays 1SG, -asa 2SG, -ees 3MSG, -ausu/-awsu 3FSG, -oos 1PL, -eeta 2PL, -oosona 3PL); Past/Perfective (-as/-adis 1SG, -adasa 2SG, -is/-ides 3MSG, -asu/-adasu 3FSG, -ida 1PL, -ideta 2PL, -idosona 3PL); Future (-ana); Converbal (-idi for 3MS/PL, -ada for 1S/2S/3FS); Negative Imperative (-oppa/-oppite).
5. Preserve phonemic glottal stop '7' (/ʔ/) in words like lo77o (good), ba7a (not exist), na7a (child), sa7a (earth). Never confuse Gofatho with Oromo; strictly use the verified Gofatho SQLite RAG Context below.
6. STRICT ANTI-HALLUCINATION: Never invent Gofatho vocabulary, dictionary definitions, or Bible verses. If a requested word is absent from the verified RAG context, explicitly state that it is unverified and needs native-speaker review.

Always respond with a valid JSON object containing these exact keys:
{
  "gofatho_latin": "Primary response or translation in authentic Gofatho Latin orthography",
  "gofatho_fidel": "Gofatho Ethiopic Extended-A Fidel script version",
  "amharic": "Complete Amharic (አማርኛ) translation and explanation",
  "english": "Complete English translation and explanation",
  "grammar_notes": "Concise morphological & cultural explanation (highlighting roots, SOV order, suffixes, and Goofa Woga context)",
  "confidence_tier": "verified_corpus | rag_grounded | uncertain_needs_review"
}
''';

  /// Converts local SQLite RAG matches into structured, verifiable source citation chips
  List<Map<String, String>> buildStructuredCitationsFromLocalBundle(Map<String, dynamic> bundle) {
    final citations = <Map<String, String>>[];
    final dictList = (bundle['dictionary'] as List<DictionaryEntry>? ?? []);
    final phraseList = (bundle['phrases'] as List<EverydayPhrase>? ?? []);
    final meezeList = (bundle['meeze'] as List<MeezeExercise>? ?? []);

    for (final d in dictList.take(3)) {
      citations.add({
        'category': 'Dictionary',
        'id': 'LEX-${d.id}',
        'title': '${d.headword} (${d.pos})',
        'excerpt': 'EN: ${d.english} | AM: ${d.amharic} | IPA: ${d.ipa}',
        'source': d.source,
      });
    }
    for (final p in phraseList.take(3)) {
      citations.add({
        'category': 'Phrasebook',
        'id': p.phraseCode.isNotEmpty ? p.phraseCode : 'PHR-${p.id}',
        'title': '${p.domain} (${p.phraseCode})',
        'excerpt': 'GOF: ${p.gofathoLatin} | EN: ${p.english} | AM: ${p.amharic}',
        'source': p.source.isNotEmpty ? p.source : 'Verified Gofatho Everyday Phrasebook',
      });
    }
    for (final m in meezeList.take(2)) {
      citations.add({
        'category': 'Textbook Meeze',
        'id': m.exerciseCode.isNotEmpty ? m.exerciseCode : 'MEEZE-${m.id}',
        'title': '${m.grade} Ch.${m.chapterNum}: ${m.chapterTitleGofatho}',
        'excerpt': 'GOF: ${m.gofathoPromptLatin} | EN: ${m.englishTranslation} | Focus: ${m.grammarFocus}',
        'source': m.source.isNotEmpty ? m.source : 'SNNPR Goofatho Doona Curriculum Textbook',
      });
    }
    return citations;
  }

  /// Extracts structured source citations from Cloud FastAPI `/api/v1/chat` or `/api/v1/chat/deep_rag` response
  List<Map<String, String>> _extractCloudCitations(
    Map<String, dynamic> data,
    List<Map<String, String>> fallbackLocalCitations,
  ) {
    final citations = <Map<String, String>>[];
    final ragEvidence = data['rag_evidence'] as Map<String, dynamic>?;
    final ragCitations = data['rag_citations'] as Map<String, dynamic>?;

    final topLex = (ragEvidence?['top_lexicon'] ?? ragCitations?['top_dictionary']) as List<dynamic>? ?? [];
    for (final raw in topLex.take(3)) {
      if (raw is Map) {
        citations.add({
          'category': 'Dictionary',
          'id': 'LEX-${raw['id'] ?? raw['headword'] ?? ''}',
          'title': '${raw['headword'] ?? ''} (${raw['pos'] ?? ''})',
          'excerpt': 'EN: ${raw['english'] ?? ''} | AM: ${raw['amharic'] ?? ''}',
          'source': (raw['source'] ?? 'Sellassie Cheru (2015) / Textbook Glossary').toString(),
        });
      }
    }

    final topPhr = (ragEvidence?['top_phrases'] ?? ragCitations?['top_phrases']) as List<dynamic>? ?? [];
    for (final raw in topPhr.take(3)) {
      if (raw is Map) {
        citations.add({
          'category': 'Phrasebook',
          'id': (raw['phrase_code'] ?? 'PHR').toString(),
          'title': '${raw['domain'] ?? 'Dialogue'} (${raw['phrase_code'] ?? ''})',
          'excerpt': 'GOF: ${raw['gofatho_latin'] ?? ''} | EN: ${raw['english'] ?? ''}',
          'source': (raw['source'] ?? 'Verified Gofatho Phrasebook & Haasaya Dialogues').toString(),
        });
      }
    }

    final topIgt = (ragEvidence?['top_igt']) as List<dynamic>? ?? [];
    for (final raw in topIgt.take(2)) {
      if (raw is Map) {
        citations.add({
          'category': 'Linguistic IGT',
          'id': (raw['igt_code'] ?? 'IGT').toString(),
          'title': 'Sellassie Cheru (2015) ${raw['igt_code'] ?? ''}',
          'excerpt': '${raw['gofatho_surface'] ?? ''} -> ${raw['leipzig_gloss'] ?? ''} (${raw['english_translation'] ?? ''})',
          'source': (raw['citation'] ?? 'Sellassie Cheru (2015) AAU PhD Dissertation').toString(),
        });
      }
    }

    return citations.isNotEmpty ? citations : fallbackLocalCitations;
  }

  /// Checks live Render backend `/api/v1/health` with a 35s timeout for Render Free cold starts
  Future<Map<String, dynamic>> checkCloudHealth() async {
    try {
      final resp = await http
          .get(Uri.parse('$baseUrl/api/v1/health'))
          .timeout(renderColdStartTimeout);
      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body) as Map<String, dynamic>;
        lastCloudConnected = true;
        lastBackendStatusNote = 'Connected to Render Cloud (${body['status'] ?? 'ok'})';
        return {
          'reachable': true,
          'status': body['status'] ?? 'ok',
          'db_ready': body['db_ready'] ?? true,
          'engine': body['engine'] ?? 'Gofatho AI FastAPI v6.2',
        };
      }
    } catch (_) {}
    lastCloudConnected = false;
    lastBackendStatusNote = 'Offline SQLite RAG Active (Cloud server waking or unreachable)';
    return {
      'reachable': false,
      'status': 'offline_fallback',
      'db_ready': false,
    };
  }

  /// Formats the on-device SQLite RAG bundle into a compact grounding block for Gemini 2.5 Flash
  String _formatRagBundleForPrompt(Map<String, dynamic> bundle) {
    final dictList = (bundle['dictionary'] as List<DictionaryEntry>? ?? []);
    final phraseList = (bundle['phrases'] as List<EverydayPhrase>? ?? []);
    final meezeList = (bundle['meeze'] as List<MeezeExercise>? ?? []);

    final sb = StringBuffer('=== VERIFIED ON-DEVICE GOFATHO SQLITE RAG CONTEXT ===\n');
    if (dictList.isNotEmpty) {
      sb.writeln('[1. Matched Lexicon Roots (1,334 Dictionary)]:');
      for (final d in dictList) {
        sb.writeln('  • [LEX-${d.id}] ${d.headword} (${d.pos}): EN="${d.english}" | AM="${d.amharic}" | Source="${d.source}"');
      }
    }
    if (phraseList.isNotEmpty) {
      sb.writeln('[2. Matched Everyday Conversational Phrases (2,072 Phrasebook)]:');
      for (final p in phraseList) {
        sb.writeln('  • [${p.phraseCode} - ${p.domain}] GOF="${p.gofathoLatin}" (${p.gofathoFidel}) | AM="${p.amharic}" | EN="${p.english}"');
      }
    }
    if (meezeList.isNotEmpty) {
      sb.writeln('[3. Matched Grade 8-10 Goofatho Doona Textbook & Cultural Notes (1,305 Meeze)]:');
      for (final m in meezeList) {
        sb.writeln('  • [${m.exerciseCode} - ${m.grade} Ch.${m.chapterNum} - ${m.chapterTitleGofatho}] ${m.gofathoPromptLatin} | AM="${m.amharicTranslation}" | EN="${m.englishTranslation}"');
      }
    }
    return sb.toString();
  }

  /// Calls Google Gemini API directly from the Android/iOS device with On-Device SQLite RAG context
  Future<Map<String, dynamic>?> _callDirectGeminiWithRag({
    required String userPrompt,
    required Map<String, dynamic> ragBundle,
  }) async {
    final key = geminiApiKey.trim();
    if (key.length < 10) return null;

    final uri = Uri.parse(
      'https://generativelanguage.googleapis.com/v1beta/models/$geminiModel:generateContent?key=$key',
    );
    final ragContextText = _formatRagBundleForPrompt(ragBundle);
    final fullPrompt = '$ragContextText\n=== USER REQUEST ===\n$userPrompt';

    try {
      final resp = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'systemInstruction': {
                'parts': [
                  {'text': _gofathoSystemPrompt}
                ]
              },
              'contents': [
                {
                  'role': 'user',
                  'parts': [
                    {'text': fullPrompt}
                  ]
                }
              ],
              'generationConfig': {
                'temperature': 0.2,
                'responseMimeType': 'application/json',
              },
            }),
          )
          .timeout(const Duration(seconds: 25));

      if (resp.statusCode == 200) {
        final decoded = jsonDecode(resp.body) as Map<String, dynamic>;
        final candidates = decoded['candidates'] as List<dynamic>? ?? [];
        if (candidates.isNotEmpty) {
          final content = candidates.first['content'] as Map<String, dynamic>? ?? {};
          final parts = content['parts'] as List<dynamic>? ?? [];
          if (parts.isNotEmpty) {
            final rawJson = (parts.first['text'] ?? '').toString();
            return jsonDecode(rawJson) as Map<String, dynamic>;
          }
        }
      }
    } catch (_) {}
    return null;
  }

  /// Native Gofatho Conversational AI Chat (Option A: On-Device RAG + Gemini -> Option B: Render Cloud Deep RAG -> Option C: Verified Offline RAG)
  Future<Map<String, dynamic>> chatWithNativeGofathoAi({
    required String message,
    String topic = 'general',
    List<Map<String, String>> history = const [],
  }) async {
    // Step 1: Always run On-Device SQLite Multi-Table RAG Retrieval (<5ms)
    final ragBundle = await GofathoDatabaseService.instance.retrieveLocalRagBundle(message);
    final dictList = (ragBundle['dictionary'] as List<DictionaryEntry>? ?? []);
    final phraseList = (ragBundle['phrases'] as List<EverydayPhrase>? ?? []);
    final meezeList = (ragBundle['meeze'] as List<MeezeExercise>? ?? []);
    final localCitations = buildStructuredCitationsFromLocalBundle(ragBundle);
    final hasVerifiedEvidence = dictList.isNotEmpty || phraseList.isNotEmpty || meezeList.isNotEmpty;

    // Step 2 (Option A): Try Direct On-Device Gemini 2.5 Flash + Local SQLite RAG if API key is set
    if (geminiApiKey.trim().length >= 10) {
      final histText = history
          .take(6)
          .map((h) => '${(h['role'] ?? 'user').toUpperCase()}: ${h['latin'] ?? h['text'] ?? ''}')
          .join('\n');
      final gemRes = await _callDirectGeminiWithRag(
        userPrompt: 'Topic Mode: $topic\nHistory:\n$histText\n\nUser Message: $message',
        ragBundle: ragBundle,
      );
      if (gemRes != null && (gemRes['gofatho_latin'] ?? '').toString().isNotEmpty) {
        final gofLat = gemRes['gofatho_latin'].toString();
        final gofFid = GofathoG2PTransliterator.latinToFidel(gofLat);
        return {
          'mode': 'On-Device SQLite RAG + Gemini ($geminiModel)',
          'confidence_tier': gemRes['confidence_tier'] ?? (hasVerifiedEvidence ? 'rag_grounded' : 'uncertain_needs_review'),
          'gofatho_latin': gofLat,
          'gofatho_fidel': gofFid,
          'amharic': (gemRes['amharic'] ?? '').toString(),
          'english': (gemRes['english'] ?? '').toString(),
          'grammar_notes': (gemRes['grammar_notes'] ?? '').toString(),
          'dict_count': dictList.length,
          'phrase_count': phraseList.length,
          'meeze_count': meezeList.length,
          'citations': localCitations,
        };
      }
    }

    // Step 3 (Option B): Try Hosted Render Cloud FastAPI v6.2 Server (`/api/v1/chat` & `/api/v1/chat/deep_rag`)
    // Uses a 35-second timeout to accommodate Render Free Docker cold starts gracefully.
    try {
      final resp = await http
          .post(
            Uri.parse('$baseUrl/api/v1/chat'),
            headers: {
              'Content-Type': 'application/json',
              if (geminiApiKey.trim().isNotEmpty) 'X-Gemini-Api-Key': geminiApiKey.trim(),
            },
            body: jsonEncode({
              'message': message,
              'topic': topic,
              'gemini_api_key': geminiApiKey.trim().isEmpty ? null : geminiApiKey.trim(),
            }),
          )
          .timeout(renderColdStartTimeout);
      if (resp.statusCode == 200) {
        lastCloudConnected = true;
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final citationsMap = data['rag_citations'] as Map<String, dynamic>? ?? {};
        final cloudCitations = _extractCloudCitations(data, localCitations);
        return {
          'mode': 'Render Cloud FastAPI (${data['mode'] ?? 'v6.2'})',
          'confidence_tier': cloudCitations.isNotEmpty ? 'verified_corpus' : 'uncertain_needs_review',
          'gofatho_latin': (data['gofatho_latin'] ?? '').toString(),
          'gofatho_fidel': (data['gofatho_fidel'] ?? '').toString(),
          'amharic': (data['amharic'] ?? '').toString(),
          'english': (data['english'] ?? '').toString(),
          'grammar_notes': (data['grammar_notes'] ?? '').toString(),
          'dict_count': citationsMap['dictionary_count'] ?? dictList.length,
          'phrase_count': citationsMap['phrasebook_count'] ?? phraseList.length,
          'meeze_count': citationsMap['meeze_count'] ?? meezeList.length,
          'citations': cloudCitations,
        };
      }
    } catch (_) {
      lastCloudConnected = false;
    }

    // Step 4 (Option C): 100% Offline On-Device SQLite RAG Synthesis Fallback (with strict uncertainty handling)
    String gofLat;
    String amhTxt;
    String engTxt;
    String grammarNote;
    String confidenceTier = 'verified_corpus';

    if (meezeList.isNotEmpty) {
      final m = meezeList.first;
      gofLat = m.gofathoPromptLatin;
      amhTxt = '[${m.grade} ምዕራፍ ${m.chapterNum} - ${m.chapterTitleGofatho}] ${m.amharicTranslation}';
      engTxt = '[${m.grade} Ch.${m.chapterNum} - ${m.chapterTitleGofatho}] ${m.englishTranslation}';
      grammarNote = 'Textbook Grammar Focus: ${m.grammarFocus} | Morphemes: ${m.morphemeGloss}';
    } else if (phraseList.isNotEmpty) {
      final p = phraseList.first;
      gofLat = p.gofathoLatin;
      amhTxt = '${p.amharic} (${p.domain})';
      engTxt = '${p.english} (${p.domain})';
      grammarNote = 'Morphemes: ${p.morphemeBreakdown} | Context: ${p.usageContext}';
    } else if (dictList.isNotEmpty) {
      final d = dictList.first;
      gofLat = '${d.headword} (${d.pos}) — ${d.gofathoSynonym.isNotEmpty ? "Syn: ${d.gofathoSynonym}" : "Verified Lexicon Entry"}';
      amhTxt = 'ቃል፦ ${d.headword} = ${d.amharic.isNotEmpty ? d.amharic : "(የአማርኛ ፍቺ በመዝገቡ አልተገኘም)"} (${d.pos})';
      engTxt = 'Verified Lexicon Root: ${d.headword} = ${d.english} (${d.pos}, Source: ${d.source})';
      grammarNote = 'Matched ${dictList.length} verified dictionary roots in local SQLite.';
    } else {
      confidenceTier = 'uncertain_needs_review';
      gofLat = '[Unverified / Out-of-Corpus Query] "$message"';
      amhTxt = '⚠️ ማስታወቂያ፦ ለዚህ ጥያቄ የተረጋገጠ የጎፋኛ መዝገበ-ቃላት ወይም የመማሪያ መጽሐፍ ማስረጃ በኦፍላይን ዳታቤዝ ውስጥ አልተገኘም። ያልተረጋገጠ ቃል ከመፍጠር ይልቅ የጎፋኛ ተናጋሪ እርማት እንዲደረግበት ተመዝግቧል።';
      engTxt = '⚠️ Uncertainty Notice: No verified Gofatho dictionary entry, phrasebook record, or Grade 8–10 textbook passage matched "$message" offline, and the cloud RAG server is currently unreachable. To prevent hallucinated Gofatho vocabulary, no unverified translation was fabricated.';
      grammarNote = 'Morphological segmentation preview: ${GofathoG2PTransliterator.analyzeWordMorphemes(message).map((m) => "${m['morpheme']} (${m['gloss']})").join(" • ")}';
    }

    return {
      'mode': 'Offline On-Device SQLite RAG',
      'confidence_tier': confidenceTier,
      'gofatho_latin': gofLat,
      'gofatho_fidel': GofathoG2PTransliterator.latinToFidel(gofLat),
      'amharic': amhTxt,
      'english': engTxt,
      'grammar_notes': grammarNote,
      'dict_count': dictList.length,
      'phrase_count': phraseList.length,
      'meeze_count': meezeList.length,
      'citations': localCitations,
    };
  }

  /// Translates across Gofatho Latin, Gofatho Fidel, Amharic, and English
  /// with strict anti-hallucination verification and structured source citations.
  Future<Map<String, dynamic>> translate({
    required String text,
    required String srcLang,
    required String tgtLang,
  }) async {
    final cleanInput = text.trim();
    // 1. Fast deterministic script conversion between Gofatho Latin and Gofatho Fidel
    if (srcLang == 'gof_Latn' && tgtLang == 'gof_Ethi') {
      final fidel = GofathoG2PTransliterator.latinToFidel(cleanInput);
      return {
        'translation': fidel,
        'fidel_script': fidel,
        'method': 'offline_deterministic_fidel_g2p',
        'confidence_tier': 'verified_corpus',
        'is_uncertain': false,
        'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(cleanInput),
        'citations': <Map<String, String>>[
          {
            'category': 'Orthography Rule',
            'id': 'ZARA-05',
            'title': 'Goofatho Doona Dual-Script Transliterator',
            'excerpt': 'Deterministic Latin <-> Ethiopic Extended-A Fidel (U+AB01–U+AB16) preserving glottal stop 7 (/ʔ/).',
            'source': 'Grade 9 Goofatho Doona Textbook & Sellassie Cheru (2015)',
          }
        ],
      };
    }
    if (srcLang == 'gof_Ethi' && tgtLang == 'gof_Latn') {
      final lat = GofathoG2PTransliterator.fidelToLatin(cleanInput);
      return {
        'translation': lat,
        'fidel_script': cleanInput,
        'method': 'offline_deterministic_fidel_g2p',
        'confidence_tier': 'verified_corpus',
        'is_uncertain': false,
        'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(lat),
        'citations': <Map<String, String>>[
          {
            'category': 'Orthography Rule',
            'id': 'ZARA-05',
            'title': 'Goofatho Doona Dual-Script Transliterator',
            'excerpt': 'Deterministic Ethiopic Extended-A Fidel <-> Latin script conversion.',
            'source': 'Grade 9 Goofatho Doona Textbook & Sellassie Cheru (2015)',
          }
        ],
      };
    }

    final ragBundle = await GofathoDatabaseService.instance.retrieveLocalRagBundle(cleanInput);
    final localCitations = buildStructuredCitationsFromLocalBundle(ragBundle);

    // 2. If On-Device Gemini Key is configured, run On-Device SQLite RAG + Gemini 2.5 Flash Translation
    if (geminiApiKey.trim().length >= 10) {
      final gemRes = await _callDirectGeminiWithRag(
        userPrompt: 'Translate from $srcLang to $tgtLang: "$cleanInput"',
        ragBundle: ragBundle,
      );
      if (gemRes != null && (gemRes['gofatho_latin'] ?? '').toString().isNotEmpty) {
        final gofLat = gemRes['gofatho_latin'].toString();
        final gofFid = GofathoG2PTransliterator.latinToFidel(gofLat);
        String out = (gemRes['english'] ?? '').toString();
        if (tgtLang == 'gof_Latn') out = gofLat;
        if (tgtLang == 'gof_Ethi') out = gofFid;
        if (tgtLang == 'amh_Ethi') out = (gemRes['amharic'] ?? '').toString();
        return {
          'translation': out,
          'fidel_script': gofFid,
          'method': 'on_device_sqlite_rag_gemini_2.5_flash',
          'confidence_tier': gemRes['confidence_tier'] ?? (localCitations.isNotEmpty ? 'rag_grounded' : 'uncertain_needs_review'),
          'is_uncertain': localCitations.isEmpty,
          'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(gofLat),
          'grammar_notes': (gemRes['grammar_notes'] ?? '').toString(),
          'citations': localCitations,
        };
      }
    }

    // 3. Try Cloud FastAPI v6.2 Hybrid RAG + Gemini/NLLB-200 endpoint on Render (35s cold-start timeout)
    try {
      final resp = await http
          .post(
            Uri.parse('$baseUrl/api/v1/translate'),
            headers: {
              'Content-Type': 'application/json',
              if (geminiApiKey.trim().isNotEmpty) 'X-Gemini-Api-Key': geminiApiKey.trim(),
            },
            body: jsonEncode({
              'text': cleanInput,
              'source_lang': srcLang,
              'target_lang': tgtLang,
            }),
          )
          .timeout(renderColdStartTimeout);
      if (resp.statusCode == 200) {
        lastCloudConnected = true;
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final trans = (data['translation'] ?? '').toString();
        final gofLat = (data['gofatho_latin'] ?? cleanInput).toString();
        return {
          'translation': trans,
          'fidel_script': (data['gofatho_fidel'] ?? GofathoG2PTransliterator.latinToFidel(gofLat)).toString(),
          'method': (data['engine_mode'] ?? 'cloud_hybrid_rag_v6.2').toString(),
          'confidence_tier': localCitations.isNotEmpty ? 'verified_corpus' : 'rag_grounded',
          'is_uncertain': false,
          'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(gofLat),
          'citations': localCitations,
        };
      }
    } catch (_) {
      lastCloudConnected = false;
    }

    // 4. Pure On-Device Offline SQLite Phrasebook & Lexicon Fallback
    final phrases = await GofathoDatabaseService.instance.searchPhrasebook(query: cleanInput, limit: 3);
    if (phrases.isNotEmpty) {
      final top = phrases.first;
      String out = top.english;
      if (tgtLang == 'amh_Ethi') out = top.amharic;
      if (tgtLang == 'gof_Latn') out = top.gofathoLatin;
      if (tgtLang == 'gof_Ethi') out = top.gofathoFidel;
      return {
        'translation': out,
        'fidel_script': top.gofathoFidel,
        'method': 'offline_sqlite_phrasebook_rag',
        'confidence_tier': 'verified_corpus',
        'is_uncertain': false,
        'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(top.gofathoLatin),
        'citations': localCitations,
      };
    }

    final lexMatches = await GofathoDatabaseService.instance.searchDictionary(query: cleanInput, limit: 3);
    if (lexMatches.isNotEmpty) {
      final first = lexMatches.first;
      String matchedMeaning;
      if (tgtLang == 'amh_Ethi') {
        matchedMeaning = first.amharic.isNotEmpty
            ? first.amharic
            : '[Amharic gloss not yet verified for "${first.headword}" — EN: ${first.english}]';
      } else if (tgtLang == 'gof_Latn') {
        matchedMeaning = first.headword;
      } else if (tgtLang == 'gof_Ethi') {
        matchedMeaning = GofathoG2PTransliterator.latinToFidel(first.headword);
      } else {
        matchedMeaning = first.english;
      }
      return {
        'translation': matchedMeaning,
        'fidel_script': GofathoG2PTransliterator.latinToFidel(first.headword),
        'method': 'offline_sqlite_verified_lexicon',
        'confidence_tier': 'verified_corpus',
        'is_uncertain': false,
        'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(first.headword),
        'citations': localCitations,
      };
    }

    // 5. Strict Anti-Hallucination Refusal / Uncertainty Notice (NEVER return Fidel transliteration as a fake English/Amharic meaning)
    final uncertaintyMessage = tgtLang == 'amh_Ethi'
        ? '⚠️ ያልተረጋገጠ ቃል/ዓረፍተ ነገር፦ «$cleanInput» በኦፍላይን የጎፋኛ መዝገበ-ቃላት (1,334 ቃላት) ወይም የዕለት ተዕለት ሐረጎች (2,072) ውስጥ አልተገኘም። የተሳሳተ ትርጉም ከመገመት ይልቅ «የተሻለ ትርጉም ጠቁም» በሚለው ለጎፋኛ ተናጋሪዎች ግምገማ ያስገቡ።'
        : '⚠️ Unverified in Offline Corpus: "$cleanInput" was not found in the verified Gofatho dictionary (1,334 headwords) or phrasebook (2,072 phrases), and the cloud RAG server ($baseUrl) is unreachable. No unverified translation was fabricated—use "Suggest Better Translation" to submit for native-speaker review.';

    return {
      'translation': uncertaintyMessage,
      'fidel_script': GofathoG2PTransliterator.latinToFidel(cleanInput),
      'method': 'offline_unverified_needs_review',
      'confidence_tier': 'uncertain_needs_review',
      'is_uncertain': true,
      'morpheme_tokens': GofathoG2PTransliterator.analyzeWordMorphemes(cleanInput),
      'citations': <Map<String, String>>[],
    };
  }

  /// Delta-syncs offline community translation corrections with `/api/v1/feedback`
  Future<int> syncPendingFeedbackToCloud() async {
    final allFeedback = await GofathoDatabaseService.instance.getFeedbackList();
    final unsynced = allFeedback.where((f) => !f.syncedToCloud).toList();
    if (unsynced.isEmpty) return 0;

    int syncedCount = 0;
    for (final f in unsynced) {
      try {
        final resp = await http
            .post(
              Uri.parse('$baseUrl/api/v1/feedback'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'source_text': f.sourceText,
                'source_lang': f.sourceLang,
                'suggested_gofatho_latin': f.suggestedCorrection,
                'suggested_gofatho_fidel': f.fidelScript,
                'contributor_woreda': f.woredaDialect,
                'notes': f.linguisticNote,
              }),
            )
            .timeout(renderColdStartTimeout);
        if (resp.statusCode == 200) {
          syncedCount++;
        }
      } catch (_) {}
    }
    return syncedCount;
  }

  /// Calls Cloud `/api/v1/morph/analyze_sentence` (Phase I.2) or synthesizes a 4-tier
  /// Interlinear Leipzig Glossing (IGT) & SOV Constituent Role analysis locally offline.
  Future<Map<String, dynamic>> analyzeSentenceInterlinearSOV(String sentence) async {
    final clean = sentence.trim();
    if (clean.isEmpty) {
      return {
        'token_count': 0,
        'word_order_typology': 'SOV (Subject-Object-Verb Head-Final North Omotic)',
        'interlinear_tiers': <String, String>{},
        'tokens': <Map<String, dynamic>>[],
        'compositional_english_gloss': '',
      };
    }

    try {
      final resp = await http
          .post(
            Uri.parse('$baseUrl/api/v1/morph/analyze_sentence'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'sentence': clean}),
          )
          .timeout(renderColdStartTimeout);
      if (resp.statusCode == 200) {
        lastCloudConnected = true;
        return jsonDecode(resp.body) as Map<String, dynamic>;
      }
    } catch (_) {
      lastCloudConnected = false;
    }

    // Offline On-Device Fallback using GofathoG2PTransliterator & Local SQLite Dictionary
    final rawWords = clean
        .split(RegExp(r'\s+'))
        .map((w) => w.replaceAll(RegExp(r'[^A-Za-z7\u1200-\u137F\uAB00-\uAB2F]'), ''))
        .where((w) => w.isNotEmpty)
        .toList();
    final total = rawWords.length;
    final surfaceTier = <String>[];
    final morphemeTier = <String>[];
    final leipzigTier = <String>[];
    final tokensOut = <Map<String, dynamic>>[];

    for (var i = 0; i < total; i++) {
      final w = rawWords[i];
      final morphs = GofathoG2PTransliterator.analyzeWordMorphemes(w);
      final rootStem = morphs.isNotEmpty ? (morphs.first['morpheme'] ?? w) : w;
      final lexHits = await GofathoDatabaseService.instance.searchDictionary(query: rootStem, limit: 1);
      final enBase = lexHits.isNotEmpty
          ? lexHits.first.english.split(';').first.split(',').first.trim()
          : (morphs.isNotEmpty ? (morphs.first['gloss'] ?? 'stem') : 'stem');
      final sufBreak = morphs.map((m) => m['morpheme'] ?? '').join('');
      final sufGloss = morphs.map((m) => (m['gloss'] ?? '').split(' ').first).join('-');

      String role = 'CONSTITUENT_STEM';
      if (i == total - 1 && total >= 2) {
        role = 'V_PREDICATE (SOV Clause-Final Finite Verb)';
      } else if (w.toLowerCase().endsWith('ppe') || w.toLowerCase().endsWith('ra') || w.toLowerCase().endsWith('n')) {
        role = 'OBLIQUE_PP (Postpositional / Case-Marked Adjunct)';
      } else if (i == 0) {
        role = 'S_SUBJECT (Nominative Subject NP)';
      } else {
        role = 'O_OBJECT_OR_MODIFIER (Pre-Verbal Object / Nominal Modifier)';
      }

      surfaceTier.add(w);
      morphemeTier.add(sufBreak.isNotEmpty ? sufBreak : w);
      leipzigTier.add(sufGloss.isNotEmpty ? '$enBase-$sufGloss' : enBase);
      tokensOut.add({
        'surface': w,
        'gofatho_fidel': GofathoG2PTransliterator.latinToFidel(w),
        'root_lemma': lexHits.isNotEmpty ? lexHits.first.headword : rootStem,
        'english_gloss': enBase,
        'sov_role': role,
        'morpheme_segmentation': sufBreak.isNotEmpty ? sufBreak : w,
        'leipzig_gloss': sufGloss.isNotEmpty ? '$enBase-$sufGloss' : enBase,
      });
    }

    return {
      'input_sentence': clean,
      'gofatho_latin': clean,
      'gofatho_fidel': GofathoG2PTransliterator.latinToFidel(clean),
      'token_count': total,
      'word_order_typology': 'SOV (Subject-Object-Verb Head-Final North Omotic)',
      'interlinear_tiers': {
        'tier_1_surface_latin': surfaceTier.join('  '),
        'tier_2_surface_fidel': GofathoG2PTransliterator.latinToFidel(clean),
        'tier_3_morpheme_break': morphemeTier.join('  '),
        'tier_4_leipzig_gloss': leipzigTier.join('  '),
      },
      'tokens': tokensOut,
    };
  }
}
