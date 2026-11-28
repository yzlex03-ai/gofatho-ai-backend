/// Trilingual UI Localization for Gofatho AI v6.2.2 (Goofatho Doona, አማርኛ, English)
/// Tailored for Gofa Zone users across Sawula, Bulqi, Laha, Beto, Melo Koza, Demba Gofa, Zala & Oyda.
class GofathoLocalizations {
  final String localeCode; // 'gof', 'am', or 'en'

  const GofathoLocalizations(this.localeCode);

  static const Map<String, Map<String, String>> _strings = {
    'gof': {
      'app_title': 'Gofatho AI v6.2.2 — Goofatho Doona',
      'app_subtitle': 'Birshshethaa, Qaala-Maxaafaa, FST Qawosa, Geeshsha Maxaafaanne Cenggurssa AI',
      'tab_translator': 'Birshshethaa',
      'tab_dictionary': 'Qaala-Maxaafaa',
      'tab_audio_bible': 'Cenggurssa',
      'tab_assistant': 'Gofa AI Chat',
      'tab_quiz_fst': 'FST & Meeze',
      'tab_feedback': 'Suure Qaala',
      'offline_badge': 'OFFLINE SQLITE (27 TABLES + 6 FTS5)',
      'online_badge': 'HYBRID DEEP RAG v6.2.2',
      'translate_btn': 'Birshsha (Translate)',
      'suggest_btn': 'Suure Birshshethaa Gujja',
      'speak_btn': 'Cenggurssaan Nabbaba (Sherpa-ONNX)',
      'search_hint': 'Goofatho, Amaaratho woy Inggilizetho qaala koyya...',
      'record_hold': 'Cenggurssaan haasayanaw oyqqa (Push-to-Talk)',
      'sync_btn': 'Cloud Sync Ootha',
    },
    'am': {
      'app_title': 'ጎፋቶ ኤአይ v6.2.2 — Goofatho Doona',
      'app_subtitle': 'የጎፋኛ-አማርኛ-እንግሊዝኛ ተርጓሚ፣ መዝገበ ቃላት፣ ሰዋሰውና የድምፅ ረዳት',
      'tab_translator': 'ተርጓሚ',
      'tab_dictionary': 'መዝገበ ቃላት',
      'tab_audio_bible': 'የድምፅ መጽሐፍ',
      'tab_assistant': 'ጎፋ ኤአይ ረዳት',
      'tab_quiz_fst': 'ሰዋሰውና ፈተና',
      'tab_feedback': 'ትርጉም አስተካክል',
      'offline_badge': 'ኦፍላይን SQLITE (27 ሰንጠረዦች)',
      'online_badge': 'ደመና + ኦፍላይን RAG v6.2.2',
      'translate_btn': 'ተርጉም (Translate)',
      'suggest_btn': 'የተሻለ ትርጉም ጠቁም',
      'speak_btn': 'በድምፅ አንብብ (Sherpa-ONNX)',
      'search_hint': 'በጎፋኛ፣ በአማርኛ ወይም በእንግሊዝኛ ፈልግ...',
      'record_hold': 'በጎፋኛ ለመናገር ተጭነው ይቆዩ (Push-to-Talk)',
      'sync_btn': 'ከደመና ጋር አመሳክር (Sync)',
    },
    'en': {
      'app_title': 'Gofatho AI v6.2.2 — Goofatho Doona',
      'app_subtitle': 'Quad-Script Translator, 27-Table FTS5 DB, Forward FST & Sherpa-ONNX Voice AI',
      'tab_translator': 'Translator',
      'tab_dictionary': 'Lexicon',
      'tab_audio_bible': 'Audio Bible',
      'tab_assistant': 'Chat & Voice',
      'tab_quiz_fst': 'FST & Quiz',
      'tab_feedback': 'Feedback',
      'offline_badge': 'OFFLINE SQLITE (27 TABLES + 6 FTS5)',
      'online_badge': 'HYBRID DEEP RAG v6.2.2',
      'translate_btn': 'Translate & Gloss',
      'suggest_btn': 'Suggest Better Translation',
      'speak_btn': 'Read Aloud (Sherpa-ONNX)',
      'search_hint': 'Search 1,698 headwords, 2,072 phrases & 3,480 FST forms...',
      'record_hold': 'Hold to speak Gofatho (Meta MMS-1B ASR)',
      'sync_btn': 'Sync Corrections to Cloud',
    },
  };

  String t(String key) {
    return _strings[localeCode]?[key] ?? _strings['en']![key] ?? key;
  }
}
