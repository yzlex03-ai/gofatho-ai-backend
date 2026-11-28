import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../l10n/app_localizations.dart';
import '../models/gofatho_models.dart';
import '../services/database_service.dart';
import '../services/g2p_transliterator.dart';
import '../services/speech_service.dart';

/// 4-Mode Offline Linguistic Hub (v6.2.1):
/// 1. 1,334 Trilingual Gofatho–English–Amharic Lexicon
/// 2. 2,072 Everyday Conversational Phrasebook
/// 3. 1,305 Grade 8–10 Textbook Meeze & Barkketho Oysha Exercises
/// 4. 75 Consonant Gemination Minimal Pairs (`Minniyaanne Leppiya Qaalata`)
class DictionaryAndPhrasebookScreen extends StatefulWidget {
  final GofathoLocalizations i18n;
  const DictionaryAndPhrasebookScreen({super.key, required this.i18n});

  @override
  State<DictionaryAndPhrasebookScreen> createState() => _DictionaryAndPhrasebookScreenState();
}

class _DictionaryAndPhrasebookScreenState extends State<DictionaryAndPhrasebookScreen> {
  final TextEditingController _searchCtrl = TextEditingController();
  final GofathoSpeechService _speech = GofathoSpeechService.instance;
  int _activeSubTab = 0; // 0 = Lexicon, 1 = Phrases, 2 = Meeze, 3 = Gemination
  String _searchQuery = '';
  String _selectedGrade = '';
  List<DictionaryEntry> _lexicon = [];
  List<EverydayPhrase> _phrases = [];
  List<MeezeExercise> _meezeList = [];
  List<GeminationMinimalPair> _geminationPairs = [];
  final Set<String> _favoriteLexiconHeadwords = <String>{'lo77o', 'saro', 'na7a'};
  final Set<String> _favoritePhraseCodes = <String>{'PHR-0001'};
  bool _showFavoritesOnly = false;

  @override
  void initState() {
    super.initState();
    _refreshData();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _refreshData() async {
    final db = GofathoDatabaseService.instance;
    final lex = await db.searchDictionary(query: _searchQuery, limit: 80);
    final phr = await db.searchPhrasebook(query: _searchQuery, limit: 80);
    final mze = await db.searchMeezeExercises(query: _searchQuery, grade: _selectedGrade, limit: 80);
    final gem = await db.searchGeminationPairs(query: _searchQuery, limit: 75);
    if (!mounted) return;
    setState(() {
      _lexicon = lex;
      _phrases = phr;
      _meezeList = mze;
      _geminationPairs = gem;
    });
  }

  Future<void> _speakWordOrPhrase(String gofathoText) async {
    final res = await _speech.speakGofathoOrTrilingual(
      text: gofathoText,
      langCode: 'gof_Latn',
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text((res['user_notice'] ?? 'Audio guide ready').toString()),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  Future<void> _copyToClipboard(String payload, String label) async {
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Copied $label to clipboard')),
    );
  }

  Widget _buildEmptySearchState(String categoryName) {
    final cs = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off_rounded, size: 48, color: cs.outline),
            const SizedBox(height: 12),
            Text(
              'No verified $categoryName matched "$_searchQuery"',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              'Try searching a Gofatho root stem (preserving 7 = /ʔ/), an Amharic gloss, or an English keyword.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: cs.onSurfaceVariant),
            ),
            const SizedBox(height: 12),
            FilledButton.tonalIcon(
              icon: const Icon(Icons.refresh),
              label: const Text('Reset Search Filter'),
              onPressed: () {
                _searchCtrl.clear();
                setState(() => _searchQuery = '');
                _refreshData();
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
          child: SegmentedButton<int>(
            segments: const [
              ButtonSegment(value: 0, icon: Icon(Icons.book, size: 15), label: Text('Lexicon (1,334)')),
              ButtonSegment(value: 1, icon: Icon(Icons.forum, size: 15), label: Text('Phrases (2,072)')),
              ButtonSegment(value: 2, icon: Icon(Icons.school, size: 15), label: Text('Meeze (1,305)')),
              ButtonSegment(value: 3, icon: Icon(Icons.graphic_eq, size: 15), label: Text('Gemination (75)')),
            ],
            selected: {_activeSubTab},
            onSelectionChanged: (s) => setState(() => _activeSubTab = s.first),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchCtrl,
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchQuery.isNotEmpty
                        ? IconButton(
                            tooltip: 'Clear Search',
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _searchCtrl.clear();
                              setState(() => _searchQuery = '');
                              _refreshData();
                            },
                          )
                        : null,
                    hintText: _activeSubTab == 0
                        ? 'Search 1,334 Gofatho, English, or Amharic words...'
                        : _activeSubTab == 1
                            ? 'Search 2,072 everyday Gofatho phrases...'
                            : _activeSubTab == 2
                                ? 'Search 1,305 Grade 8–10 Meeze exercises...'
                                : 'Search 75 Leppiya vs. Minniyaa minimal pairs...',
                    isDense: true,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onChanged: (v) {
                    _searchQuery = v;
                    _refreshData();
                  },
                ),
              ),
              if (_activeSubTab == 0 || _activeSubTab == 1) ...[
                const SizedBox(width: 8),
                FilterChip(
                  tooltip: 'Filter Bookmarked Favorites Only',
                  avatar: Icon(
                    _showFavoritesOnly ? Icons.star : Icons.star_border,
                    size: 16,
                  ),
                  label: Text(
                    _activeSubTab == 0
                        ? 'Favorites (${_favoriteLexiconHeadwords.length})'
                        : 'Favorites (${_favoritePhraseCodes.length})',
                    style: const TextStyle(fontSize: 12),
                  ),
                  selected: _showFavoritesOnly,
                  onSelected: (v) => setState(() => _showFavoritesOnly = v),
                ),
              ],
              if (_activeSubTab == 2) ...[
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _selectedGrade,
                  items: const [
                    DropdownMenuItem(value: '', child: Text('All Grades')),
                    DropdownMenuItem(value: 'Grade 8', child: Text('Grade 8')),
                    DropdownMenuItem(value: 'Grade 9', child: Text('Grade 9')),
                    DropdownMenuItem(value: 'Grade 10', child: Text('Grade 10')),
                  ],
                  onChanged: (v) {
                    setState(() => _selectedGrade = v ?? '');
                    _refreshData();
                  },
                ),
              ],
            ],
          ),
        ),
        Expanded(
          child: _activeSubTab == 0
              ? _buildLexiconList()
              : _activeSubTab == 1
                  ? _buildPhrasebookList()
                  : _activeSubTab == 2
                      ? _buildMeezeList()
                      : _buildGeminationList(),
        ),
      ],
    );
  }

  Widget _buildLexiconList() {
    final visibleLexicon = _showFavoritesOnly
        ? _lexicon.where((e) => _favoriteLexiconHeadwords.contains(e.headword)).toList()
        : _lexicon;
    if (visibleLexicon.isEmpty) return _buildEmptySearchState('lexicon entries');
    final cs = Theme.of(context).colorScheme;
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: visibleLexicon.length,
      itemBuilder: (_, idx) {
        final item = visibleLexicon[idx];
        final isFav = _favoriteLexiconHeadwords.contains(item.headword);
        final fidel = GofathoG2PTransliterator.latinToFidel(item.headword);
        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    SelectableText(
                      item.headword,
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: cs.primary),
                    ),
                    const SizedBox(width: 8),
                    SelectableText(
                      fidel,
                      style: TextStyle(fontSize: 15, color: cs.tertiary),
                    ),
                    const SizedBox(width: 8),
                    Text(item.ipa, style: TextStyle(color: cs.onSurfaceVariant, fontSize: 12)),
                    const Spacer(),
                    Chip(
                      label: Text(item.pos, style: const TextStyle(fontSize: 11)),
                      visualDensity: VisualDensity.compact,
                    ),
                    IconButton(
                      tooltip: 'Bookmark Favorite Headword',
                      icon: Icon(isFav ? Icons.star : Icons.star_border, size: 18, color: isFav ? Colors.amber.shade700 : null),
                      onPressed: () {
                        setState(() {
                          if (isFav) {
                            _favoriteLexiconHeadwords.remove(item.headword);
                          } else {
                            _favoriteLexiconHeadwords.add(item.headword);
                          }
                        });
                      },
                    ),
                    IconButton(
                      tooltip: 'Pronounce Gofatho Headword',
                      icon: const Icon(Icons.volume_up, size: 18),
                      onPressed: () => _speakWordOrPhrase(item.headword),
                    ),
                    IconButton(
                      tooltip: 'Copy Lexicon Entry',
                      icon: const Icon(Icons.copy_all_outlined, size: 18),
                      onPressed: () => _copyToClipboard(
                        '${item.headword} ($fidel) [${item.pos}] — EN: ${item.english} | AM: ${item.amharic} (${item.source})',
                        item.headword,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                SelectableText('🇬🇧 EN: ${item.english}', style: const TextStyle(fontSize: 13)),
                if (item.amharic.isNotEmpty)
                  SelectableText('🇪🇹 አማርኛ: ${item.amharic}', style: const TextStyle(fontSize: 13)),
                const SizedBox(height: 2),
                Text('Source: ${item.source} • Domain: ${item.domain}',
                    style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant)),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildPhrasebookList() {
    final visiblePhrases = _showFavoritesOnly
        ? _phrases.where((p) => _favoritePhraseCodes.contains(p.phraseCode)).toList()
        : _phrases;
    if (visiblePhrases.isEmpty) return _buildEmptySearchState('everyday phrases');
    final cs = Theme.of(context).colorScheme;
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: visiblePhrases.length,
      itemBuilder: (_, idx) {
        final p = visiblePhrases[idx];
        final isFav = _favoritePhraseCodes.contains(p.phraseCode);
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      p.phraseCode,
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: cs.secondary),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        p.domain,
                        style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Bookmark Favorite Phrase',
                      icon: Icon(isFav ? Icons.star : Icons.star_border, size: 18, color: isFav ? Colors.amber.shade700 : null),
                      onPressed: () {
                        setState(() {
                          if (isFav) {
                            _favoritePhraseCodes.remove(p.phraseCode);
                          } else {
                            _favoritePhraseCodes.add(p.phraseCode);
                          }
                        });
                      },
                    ),
                    IconButton(
                      tooltip: 'Read Gofatho Phrase Aloud',
                      icon: const Icon(Icons.volume_up, size: 18),
                      onPressed: () => _speakWordOrPhrase(p.gofathoLatin),
                    ),
                    IconButton(
                      tooltip: 'Copy Trilingual Phrase',
                      icon: const Icon(Icons.copy_all_outlined, size: 18),
                      onPressed: () => _copyToClipboard(
                        'GOF: ${p.gofathoLatin}\nFidel: ${p.gofathoFidel}\nAM: ${p.amharic}\nEN: ${p.english}',
                        p.phraseCode,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                SelectableText(p.gofathoLatin, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                SelectableText(p.gofathoFidel, style: TextStyle(fontSize: 14, color: cs.primary)),
                const SizedBox(height: 4),
                SelectableText('🇬🇧 ${p.english}', style: const TextStyle(fontSize: 13)),
                SelectableText('🇪🇹 ${p.amharic}', style: const TextStyle(fontSize: 13)),
                if (p.morphemeBreakdown.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Gloss: ${p.morphemeBreakdown}',
                      style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: cs.onSurfaceVariant),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMeezeList() {
    if (_meezeList.isEmpty) return _buildEmptySearchState('Grade 8–10 Meeze exercises');
    final cs = Theme.of(context).colorScheme;
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _meezeList.length,
      itemBuilder: (_, idx) {
        final m = _meezeList[idx];
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: cs.primaryContainer,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${m.grade} • Ch. ${m.chapterNum}',
                        style: TextStyle(color: cs.onPrimaryContainer, fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        m.exerciseType,
                        style: TextStyle(fontSize: 11, color: cs.secondary, fontWeight: FontWeight.w600),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Read Meeze Prompt Aloud',
                      icon: const Icon(Icons.volume_up, size: 18),
                      onPressed: () => _speakWordOrPhrase(m.gofathoPromptLatin),
                    ),
                    IconButton(
                      tooltip: 'Copy Meeze Exercise',
                      icon: const Icon(Icons.copy_all_outlined, size: 18),
                      onPressed: () => _copyToClipboard(
                        '[${m.grade} Ch.${m.chapterNum}] ${m.gofathoPromptLatin}\nFidel: ${m.gofathoPromptFidel}\nEN: ${m.englishTranslation}\nAM: ${m.amharicTranslation}',
                        m.exerciseCode,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                SelectableText(m.gofathoPromptLatin, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                SelectableText(m.gofathoPromptFidel, style: TextStyle(fontSize: 14, color: cs.primary)),
                const SizedBox(height: 6),
                SelectableText('🇬🇧 EN: ${m.englishTranslation}', style: const TextStyle(fontSize: 13)),
                SelectableText('🇪🇹 AM: ${m.amharicTranslation}', style: const TextStyle(fontSize: 13)),
                const SizedBox(height: 4),
                Text('Qawosa Focus: ${m.grammarFocus}', style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant)),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildGeminationList() {
    if (_geminationPairs.isEmpty) return _buildEmptySearchState('Leppiya vs. Minniyaa minimal pairs');
    final cs = Theme.of(context).colorScheme;
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: _geminationPairs.length,
      itemBuilder: (_, idx) {
        final g = _geminationPairs[idx];
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: cs.secondaryContainer,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${g.pairCode} • ${g.consonantPhoneme}',
                        style: TextStyle(color: cs.onSecondaryContainer, fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(g.phoneticCategory, style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant)),
                    ),
                    IconButton(
                      tooltip: 'Copy Minimal Pair Contrast',
                      icon: const Icon(Icons.copy_all_outlined, size: 18),
                      onPressed: () => _copyToClipboard(
                        '${g.pairCode} (${g.consonantPhoneme}): Leppiya ${g.leppiyaLatin} = ${g.leppiyaEnglish} (${g.leppiyaAmharic}) vs. Minniyaa ${g.minniyaaLatin} = ${g.minniyaaEnglish} (${g.minniyaaAmharic})',
                        g.pairCode,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: cs.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Expanded(
                                  child: Text(
                                    'Leppiya (1.0x Singleton)',
                                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                IconButton(
                                  tooltip: 'Speak Leppiya Singleton',
                                  icon: const Icon(Icons.volume_up, size: 16),
                                  onPressed: () => _speakWordOrPhrase(g.leppiyaLatin),
                                ),
                              ],
                            ),
                            SelectableText(
                              '${g.leppiyaLatin} (${g.leppiyaFidel})',
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                            ),
                            Text('EN: ${g.leppiyaEnglish}', style: const TextStyle(fontSize: 12)),
                            Text('AM: ${g.leppiyaAmharic}', style: const TextStyle(fontSize: 12)),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: cs.tertiaryContainer,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'Minniyaa (1.85x Geminate)',
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: cs.onTertiaryContainer,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  tooltip: 'Speak Minniyaa Geminate',
                                  icon: const Icon(Icons.volume_up, size: 16),
                                  onPressed: () => _speakWordOrPhrase(g.minniyaaLatin),
                                ),
                              ],
                            ),
                            SelectableText(
                              '${g.minniyaaLatin} (${g.minniyaaFidel})',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: cs.onTertiaryContainer,
                              ),
                            ),
                            Text('EN: ${g.minniyaaEnglish}', style: TextStyle(fontSize: 12, color: cs.onTertiaryContainer)),
                            Text('AM: ${g.minniyaaAmharic}', style: TextStyle(fontSize: 12, color: cs.onTertiaryContainer)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text('Rule: ${g.orthographyRule}', style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant)),
              ],
            ),
          ),
        );
      },
    );
  }
}
