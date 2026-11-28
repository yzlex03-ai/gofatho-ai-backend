import 'package:flutter/material.dart';
import 'l10n/app_localizations.dart';
import 'screens/translator_screen.dart';
import 'screens/dictionary_screen.dart';
import 'screens/audio_bible_screen.dart';
import 'screens/voice_assistant_screen.dart';
import 'screens/quiz_ocr_ometo_screen.dart';
import 'screens/feedback_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const GofathoAIApp());
}

class GofathoAIApp extends StatefulWidget {
  const GofathoAIApp({super.key});

  @override
  State<GofathoAIApp> createState() => _GofathoAIAppState();
}

class _GofathoAIAppState extends State<GofathoAIApp> {
  String _localeCode = 'gof';
  int _selectedIndex = 0;
  ThemeMode _themeMode = ThemeMode.system;

  void _cycleThemeMode() {
    setState(() {
      if (_themeMode == ThemeMode.system) {
        _themeMode = ThemeMode.light;
      } else if (_themeMode == ThemeMode.light) {
        _themeMode = ThemeMode.dark;
      } else {
        _themeMode = ThemeMode.system;
      }
    });
  }

  IconData _themeIcon() {
    switch (_themeMode) {
      case ThemeMode.light:
        return Icons.light_mode;
      case ThemeMode.dark:
        return Icons.dark_mode;
      case ThemeMode.system:
        return Icons.brightness_auto;
    }
  }

  @override
  Widget build(BuildContext context) {
    final i18n = GofathoLocalizations(_localeCode);

    final lightScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1B365D),
      secondary: const Color(0xFFD97706),
      brightness: Brightness.light,
    );
    final darkScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF3B82F6),
      secondary: const Color(0xFFF59E0B),
      brightness: Brightness.dark,
    );

    return MaterialApp(
      title: 'Gofatho AI v6.2',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: ThemeData(
        colorScheme: lightScheme,
        useMaterial3: true,
        cardTheme: CardTheme(
          elevation: 1.5,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      darkTheme: ThemeData(
        colorScheme: darkScheme,
        useMaterial3: true,
        cardTheme: CardTheme(
          elevation: 1.5,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      home: Scaffold(
        appBar: AppBar(
          backgroundColor: const Color(0xFF1B365D),
          foregroundColor: Colors.white,
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(i18n.t('app_title'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Text(i18n.t('app_subtitle'), style: const TextStyle(fontSize: 11, color: Colors.white70)),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'Switch Theme (System / Light / Dark)',
              icon: Icon(_themeIcon(), color: Colors.amberAccent),
              onPressed: _cycleThemeMode,
            ),
            Padding(
              padding: const EdgeInsets.only(right: 10),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: _localeCode,
                  dropdownColor: const Color(0xFF1B365D),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                  items: const [
                    DropdownMenuItem(value: 'gof', child: Text('GOF (Goofatho)')),
                    DropdownMenuItem(value: 'am', child: Text('AM (አማርኛ)')),
                    DropdownMenuItem(value: 'en', child: Text('EN (English)')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => _localeCode = v);
                  },
                ),
              ),
            ),
          ],
        ),
        body: IndexedStack(
          index: _selectedIndex,
          children: [
            TranslatorScreen(i18n: i18n),
            DictionaryAndPhrasebookScreen(i18n: i18n),
            AudioBibleScreen(i18n: i18n),
            VoiceAssistantScreen(i18n: i18n),
            QuizOcrOmetoScreen(i18n: i18n),
            CommunityFeedbackScreen(i18n: i18n),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (idx) => setState(() => _selectedIndex = idx),
          destinations: [
            NavigationDestination(icon: const Icon(Icons.translate), label: i18n.t('tab_translator')),
            NavigationDestination(icon: const Icon(Icons.menu_book), label: i18n.t('tab_dictionary')),
            NavigationDestination(icon: const Icon(Icons.headphones), label: i18n.t('tab_audio_bible')),
            NavigationDestination(icon: const Icon(Icons.mic), label: i18n.t('tab_assistant')),
            NavigationDestination(icon: const Icon(Icons.quiz_outlined), label: i18n.t('tab_quiz_fst')),
            NavigationDestination(icon: const Icon(Icons.verified_user_outlined), label: i18n.t('tab_feedback')),
          ],
        ),
      ),
    );
  }
}
