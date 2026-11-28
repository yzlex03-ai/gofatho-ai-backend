import 'dart:convert';

class DictionaryEntry {
  final int id;
  final String headword;
  final String normalizedForm;
  final String ipa;
  final String pos;
  final String english;
  final String amharic;
  final String gofathoSynonym;
  final String domain;
  final String source;

  const DictionaryEntry({
    required this.id,
    required this.headword,
    required this.normalizedForm,
    required this.ipa,
    required this.pos,
    required this.english,
    required this.amharic,
    required this.gofathoSynonym,
    required this.domain,
    required this.source,
  });

  factory DictionaryEntry.fromMap(Map<String, dynamic> map) {
    return DictionaryEntry(
      id: (map['id'] as num?)?.toInt() ?? 0,
      headword: (map['headword'] ?? '').toString(),
      normalizedForm: (map['normalized_form'] ?? '').toString(),
      ipa: (map['ipa'] ?? '').toString(),
      pos: (map['pos'] ?? '').toString(),
      english: (map['english'] ?? '').toString(),
      amharic: (map['amharic'] ?? '').toString(),
      gofathoSynonym: (map['gofatho_synonym'] ?? '').toString(),
      domain: (map['domain'] ?? 'General Lexicon').toString(),
      source: (map['source'] ?? 'Sellassie Cheru (2015)').toString(),
    );
  }
}

class EverydayPhrase {
  final int id;
  final String phraseCode;
  final String domain;
  final String gofathoLatin;
  final String gofathoFidel;
  final String amharic;
  final String english;
  final String ipaPhonemic;
  final String morphemeBreakdown;
  final String usageContext;
  final String source;

  const EverydayPhrase({
    required this.id,
    required this.phraseCode,
    required this.domain,
    required this.gofathoLatin,
    required this.gofathoFidel,
    required this.amharic,
    required this.english,
    required this.ipaPhonemic,
    required this.morphemeBreakdown,
    required this.usageContext,
    required this.source,
  });

  factory EverydayPhrase.fromMap(Map<String, dynamic> map) {
    return EverydayPhrase(
      id: (map['id'] as num?)?.toInt() ?? 0,
      phraseCode: (map['phrase_code'] ?? '').toString(),
      domain: (map['domain'] ?? '').toString(),
      gofathoLatin: (map['gofatho_latin'] ?? '').toString(),
      gofathoFidel: (map['gofatho_fidel'] ?? '').toString(),
      amharic: (map['amharic'] ?? '').toString(),
      english: (map['english'] ?? '').toString(),
      ipaPhonemic: (map['ipa_phonemic'] ?? '').toString(),
      morphemeBreakdown: (map['morpheme_breakdown'] ?? '').toString(),
      usageContext: (map['usage_context'] ?? '').toString(),
      source: (map['source'] ?? '').toString(),
    );
  }
}

class MeezeExercise {
  final int id;
  final String exerciseCode;
  final String grade;
  final int chapterNum;
  final String chapterTitleGofatho;
  final String exerciseType;
  final String gofathoPromptLatin;
  final String gofathoPromptFidel;
  final String englishTranslation;
  final String amharicTranslation;
  final String morphemeGloss;
  final String grammarFocus;
  final String source;

  const MeezeExercise({
    required this.id,
    required this.exerciseCode,
    required this.grade,
    required this.chapterNum,
    required this.chapterTitleGofatho,
    required this.exerciseType,
    required this.gofathoPromptLatin,
    required this.gofathoPromptFidel,
    required this.englishTranslation,
    required this.amharicTranslation,
    required this.morphemeGloss,
    required this.grammarFocus,
    required this.source,
  });

  factory MeezeExercise.fromMap(Map<String, dynamic> map) {
    return MeezeExercise(
      id: (map['id'] as num?)?.toInt() ?? 0,
      exerciseCode: (map['exercise_code'] ?? '').toString(),
      grade: (map['grade'] ?? 'Grade 8').toString(),
      chapterNum: (map['chapter_num'] as num?)?.toInt() ?? 1,
      chapterTitleGofatho: (map['chapter_title_gofatho'] ?? '').toString(),
      exerciseType: (map['exercise_type'] ?? '').toString(),
      gofathoPromptLatin: (map['gofatho_prompt_latin'] ?? '').toString(),
      gofathoPromptFidel: (map['gofatho_prompt_fidel'] ?? '').toString(),
      englishTranslation: (map['english_translation'] ?? '').toString(),
      amharicTranslation: (map['amharic_translation'] ?? '').toString(),
      morphemeGloss: (map['morpheme_gloss'] ?? '').toString(),
      grammarFocus: (map['grammar_focus'] ?? '').toString(),
      source: (map['source'] ?? '').toString(),
    );
  }
}

class PhraseAudioSlice {
  final String phraseTag;
  final double startSec;
  final double endSec;
  final double durationSec;
  final String textLatin;
  final String textFidel;

  const PhraseAudioSlice({
    required this.phraseTag,
    required this.startSec,
    required this.endSec,
    required this.durationSec,
    required this.textLatin,
    required this.textFidel,
  });

  factory PhraseAudioSlice.fromMap(Map<String, dynamic> map) {
    final st = ((map['start_sec'] ?? map['start']) as num?)?.toDouble() ?? 0.0;
    final en = ((map['end_sec'] ?? map['end']) as num?)?.toDouble() ?? 0.0;
    final dur = ((map['duration_sec'] ?? map['duration']) as num?)?.toDouble() ?? (en - st);
    return PhraseAudioSlice(
      phraseTag: (map['phrase_tag'] ?? map['part'] ?? map['phrase_id'] ?? '1a').toString(),
      startSec: st,
      endSec: en,
      durationSec: dur,
      textLatin: (map['text_latin'] ?? map['text_lat'] ?? map['gofatho_latin'] ?? '').toString(),
      textFidel: (map['text_fidel'] ?? map['gofatho_fidel'] ?? '').toString(),
    );
  }
}

class VerseAudioClip {
  final int id;
  final String clipId;
  final String bookId;
  final String bookNameLat;
  final String bookNameFidel;
  final String bookNameEn;
  final int chapter;
  final String verse;
  final String mp3Filename;
  final double startSec;
  final double endSec;
  final double durationSec;
  final int byteStart;
  final int byteEnd;
  final String gofathoLatin;
  final String gofathoFidel;
  final String englishTranslation;
  final String amharicTranslation;
  final List<PhraseAudioSlice> phrases;

  const VerseAudioClip({
    required this.id,
    required this.clipId,
    required this.bookId,
    required this.bookNameLat,
    required this.bookNameFidel,
    required this.bookNameEn,
    required this.chapter,
    required this.verse,
    required this.mp3Filename,
    required this.startSec,
    required this.endSec,
    required this.durationSec,
    required this.byteStart,
    required this.byteEnd,
    required this.gofathoLatin,
    required this.gofathoFidel,
    required this.englishTranslation,
    required this.amharicTranslation,
    required this.phrases,
  });

  factory VerseAudioClip.fromMap(Map<String, dynamic> map) {
    List<PhraseAudioSlice> parsedPhrases = [];
    final rawPhrases = map['phrases'] ?? map['phrases_json'];
    if (rawPhrases is String && rawPhrases.isNotEmpty) {
      final decoded = jsonDecode(rawPhrases) as List<dynamic>;
      parsedPhrases = decoded
          .map((e) => PhraseAudioSlice.fromMap(Map<String, dynamic>.from(e as Map)))
          .toList();
    } else if (rawPhrases is List) {
      parsedPhrases = rawPhrases
          .map((e) => PhraseAudioSlice.fromMap(Map<String, dynamic>.from(e as Map)))
          .toList();
    }
    return VerseAudioClip(
      id: (map['id'] as num?)?.toInt() ?? 0,
      clipId: (map['clip_id'] ?? '').toString(),
      bookId: (map['book_id'] ?? 'MAT').toString(),
      bookNameLat: (map['book_name_lat'] ?? '').toString(),
      bookNameFidel: (map['book_name_fidel'] ?? '').toString(),
      bookNameEn: (map['book_name_en'] ?? '').toString(),
      chapter: (map['chapter'] as num?)?.toInt() ?? 1,
      verse: (map['verse'] ?? '1').toString(),
      mp3Filename: (map['mp3_filename'] ?? '').toString(),
      startSec: (map['start_sec'] as num?)?.toDouble() ?? 0.0,
      endSec: (map['end_sec'] as num?)?.toDouble() ?? 0.0,
      durationSec: (map['duration_sec'] as num?)?.toDouble() ?? 0.0,
      byteStart: ((map['est_byte_start'] ?? map['byte_start']) as num?)?.toInt() ?? 0,
      byteEnd: ((map['est_byte_end'] ?? map['byte_end']) as num?)?.toInt() ?? 0,
      gofathoLatin: (map['gofatho_latin'] ?? '').toString(),
      gofathoFidel: (map['gofatho_fidel'] ?? '').toString(),
      englishTranslation: (map['english_translation'] ?? '').toString(),
      amharicTranslation: (map['amharic_translation'] ?? '').toString(),
      phrases: parsedPhrases,
    );
  }
}

class TranslationFeedback {
  final int id;
  final String feedbackCode;
  final String sourceText;
  final String sourceLang;
  final String targetLang;
  final String initialAiOutput;
  final String suggestedCorrection;
  final String fidelScript;
  final String woredaDialect;
  final String contributorRole;
  final String domainCategory;
  final String linguisticNote;
  final String status;
  final int upvotes;
  final bool syncedToCloud;
  final String createdAt;

  const TranslationFeedback({
    required this.id,
    required this.feedbackCode,
    required this.sourceText,
    required this.sourceLang,
    required this.targetLang,
    required this.initialAiOutput,
    required this.suggestedCorrection,
    required this.fidelScript,
    required this.woredaDialect,
    required this.contributorRole,
    required this.domainCategory,
    required this.linguisticNote,
    required this.status,
    required this.upvotes,
    required this.syncedToCloud,
    required this.createdAt,
  });

  factory TranslationFeedback.fromMap(Map<String, dynamic> map) {
    return TranslationFeedback(
      id: (map['id'] as num?)?.toInt() ?? 0,
      feedbackCode: (map['feedback_code'] ?? '').toString(),
      sourceText: (map['source_text'] ?? '').toString(),
      sourceLang: (map['source_lang'] ?? 'eng_Latn').toString(),
      targetLang: (map['target_lang'] ?? 'gof_Latn').toString(),
      initialAiOutput: (map['initial_ai_output'] ?? '').toString(),
      suggestedCorrection: (map['suggested_correction'] ?? '').toString(),
      fidelScript: (map['fidel_script'] ?? '').toString(),
      woredaDialect: (map['woreda_dialect'] ?? 'Sawula Town').toString(),
      contributorRole: (map['contributor_role'] ?? 'Native Speaker').toString(),
      domainCategory: (map['domain_category'] ?? 'General').toString(),
      linguisticNote: (map['linguistic_note'] ?? '').toString(),
      status: (map['status'] ?? 'Pending Review').toString(),
      upvotes: (map['upvotes'] as num?)?.toInt() ?? 1,
      syncedToCloud: ((map['synced_to_cloud'] as num?)?.toInt() ?? 0) == 1,
      createdAt: (map['created_at'] ?? '').toString(),
    );
  }
}


class GeminationMinimalPair {
  final int id;
  final String pairCode;
  final String consonantPhoneme;
  final String phoneticCategory;
  final String leppiyaLatin;
  final String leppiyaFidel;
  final String leppiyaIpa;
  final String leppiyaPos;
  final String leppiyaAmharic;
  final String leppiyaEnglish;
  final String leppiyaExampleGof;
  final String minniyaaLatin;
  final String minniyaaFidel;
  final String minniyaaIpa;
  final String minniyaaPos;
  final String minniyaaAmharic;
  final String minniyaaEnglish;
  final String minniyaaExampleGof;
  final String orthographyRule;

  const GeminationMinimalPair({
    required this.id,
    required this.pairCode,
    required this.consonantPhoneme,
    required this.phoneticCategory,
    required this.leppiyaLatin,
    required this.leppiyaFidel,
    required this.leppiyaIpa,
    required this.leppiyaPos,
    required this.leppiyaAmharic,
    required this.leppiyaEnglish,
    required this.leppiyaExampleGof,
    required this.minniyaaLatin,
    required this.minniyaaFidel,
    required this.minniyaaIpa,
    required this.minniyaaPos,
    required this.minniyaaAmharic,
    required this.minniyaaEnglish,
    required this.minniyaaExampleGof,
    required this.orthographyRule,
  });

  factory GeminationMinimalPair.fromMap(Map<String, dynamic> map) {
    return GeminationMinimalPair(
      id: (map['id'] as num?)?.toInt() ?? 0,
      pairCode: (map['pair_code'] ?? '').toString(),
      consonantPhoneme: (map['consonant_phoneme'] ?? '').toString(),
      phoneticCategory: (map['phonetic_category'] ?? '').toString(),
      leppiyaLatin: (map['leppiya_singleton_latin'] ?? '').toString(),
      leppiyaFidel: (map['leppiya_singleton_fidel'] ?? '').toString(),
      leppiyaIpa: (map['leppiya_ipa'] ?? '').toString(),
      leppiyaPos: (map['leppiya_pos'] ?? '').toString(),
      leppiyaAmharic: (map['leppiya_amharic'] ?? '').toString(),
      leppiyaEnglish: (map['leppiya_english'] ?? '').toString(),
      leppiyaExampleGof: (map['leppiya_example_gof'] ?? '').toString(),
      minniyaaLatin: (map['minniyaa_geminate_latin'] ?? '').toString(),
      minniyaaFidel: (map['minniyaa_geminate_fidel'] ?? '').toString(),
      minniyaaIpa: (map['minniyaa_ipa'] ?? '').toString(),
      minniyaaPos: (map['minniyaa_pos'] ?? '').toString(),
      minniyaaAmharic: (map['minniyaa_amharic'] ?? '').toString(),
      minniyaaEnglish: (map['minniyaa_english'] ?? '').toString(),
      minniyaaExampleGof: (map['minniyaa_example_gof'] ?? '').toString(),
      orthographyRule: (map['orthography_rule'] ?? '').toString(),
    );
  }
}


class MeezeQuizItem {
  final int id;
  final String quizCode;
  final String gradeLevel;
  final String quizCategory;
  final String questionGofLatin;
  final String questionGofFidel;
  final String questionAmharic;
  final String questionEnglish;
  final String optionA;
  final String optionB;
  final String optionC;
  final String optionD;
  final String correctOption;
  final String explanationTrilingual;
  final String audioTargetWord;

  const MeezeQuizItem({
    required this.id,
    required this.quizCode,
    required this.gradeLevel,
    required this.quizCategory,
    required this.questionGofLatin,
    required this.questionGofFidel,
    required this.questionAmharic,
    required this.questionEnglish,
    required this.optionA,
    required this.optionB,
    required this.optionC,
    required this.optionD,
    required this.correctOption,
    required this.explanationTrilingual,
    required this.audioTargetWord,
  });

  factory MeezeQuizItem.fromMap(Map<String, dynamic> map) {
    return MeezeQuizItem(
      id: (map['id'] as num?)?.toInt() ?? 0,
      quizCode: (map['quiz_code'] ?? '').toString(),
      gradeLevel: (map['grade_level'] ?? 'Grade 9').toString(),
      quizCategory: (map['quiz_category'] ?? '').toString(),
      questionGofLatin: (map['question_gof_latin'] ?? '').toString(),
      questionGofFidel: (map['question_gof_fidel'] ?? '').toString(),
      questionAmharic: (map['question_amharic'] ?? '').toString(),
      questionEnglish: (map['question_english'] ?? '').toString(),
      optionA: (map['option_a'] ?? '').toString(),
      optionB: (map['option_b'] ?? '').toString(),
      optionC: (map['option_c'] ?? '').toString(),
      optionD: (map['option_d'] ?? '').toString(),
      correctOption: (map['correct_option'] ?? 'A').toString(),
      explanationTrilingual: (map['explanation_trilingual'] ?? '').toString(),
      audioTargetWord: (map['audio_target_word'] ?? '').toString(),
    );
  }
}

class OmetoCognateEntry {
  final int id;
  final String cognateCode;
  final String semanticDomain;
  final String gofathoLatin;
  final String gofathoFidel;
  final String gamothoLatin;
  final String dawuroLatin;
  final String wolayttaLatin;
  final String amharicMeaning;
  final String englishMeaning;
  final String soundRule;

  const OmetoCognateEntry({
    required this.id,
    required this.cognateCode,
    required this.semanticDomain,
    required this.gofathoLatin,
    required this.gofathoFidel,
    required this.gamothoLatin,
    required this.dawuroLatin,
    required this.wolayttaLatin,
    required this.amharicMeaning,
    required this.englishMeaning,
    required this.soundRule,
  });

  factory OmetoCognateEntry.fromMap(Map<String, dynamic> map) {
    return OmetoCognateEntry(
      id: (map['id'] as num?)?.toInt() ?? 0,
      cognateCode: (map['cognate_code'] ?? '').toString(),
      semanticDomain: (map['semantic_domain'] ?? '').toString(),
      gofathoLatin: (map['gofatho_gof_latin'] ?? '').toString(),
      gofathoFidel: (map['gofatho_gof_fidel'] ?? '').toString(),
      gamothoLatin: (map['gamotho_gmv_latin'] ?? '').toString(),
      dawuroLatin: (map['dawuro_dwr_latin'] ?? '').toString(),
      wolayttaLatin: (map['wolaytta_wal_latin'] ?? '').toString(),
      amharicMeaning: (map['amharic_meaning'] ?? '').toString(),
      englishMeaning: (map['english_meaning'] ?? '').toString(),
      soundRule: (map['sound_correspondence_rule'] ?? '').toString(),
    );
  }
}
