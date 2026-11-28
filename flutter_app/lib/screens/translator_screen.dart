import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../l10n/app_localizations.dart';
import '../services/api_sync_service.dart';
import '../services/database_service.dart';
import '../services/g2p_transliterator.dart';
import '../services/speech_service.dart';

class TranslatorScreen extends StatefulWidget {
  final GofathoLocalizations i18n;
  const TranslatorScreen({super.key, required this.i18n});

  @override
  State<TranslatorScreen> createState() => _TranslatorScreenState();
}

class _TranslatorScreenState extends State<TranslatorScreen> {
  final TextEditingController _inputCtrl = TextEditingController(
    text: 'Saro pe7adii? Taani Goofatho doonaa tamaarays.',
  );
  final GofathoApiSyncService _api = GofathoApiSyncService();
  final GofathoSpeechService _speech = GofathoSpeechService.instance;

  String _srcLang = 'gof_Latn';
  String _tgtLang = 'eng_Latn';
  bool _showFidelDualScript = true;
  bool _loading = false;
  bool _isUncertain = false;

  String _translatedText = 'Did you spend the night in peace? (Good morning) I am learning the Gofatho language.';
  String _fidelScript = 'ሳሮ ፐዓዲኢ? ታአኒ ጎኦፋꬆ ዶኦናአ ታማአራይስ።';
  String _methodBadge = 'everyday_phrasebook_exact_rag';
  String _confidenceTier = 'verified_corpus';
  List<Map<String, String>> _morphemes = [];
  List<Map<String, String>> _citations = [];
  Map<String, dynamic> _interlinearTiers = {};
  List<Map<String, dynamic>> _sovTokens = [];

  @override
  void initState() {
    super.initState();
    _runTranslation();
  }

  @override
  void dispose() {
    _inputCtrl.dispose();
    super.dispose();
  }

  Future<void> _runTranslation() async {
    final txt = _inputCtrl.text.trim();
    if (txt.isEmpty) return;
    setState(() => _loading = true);
    final res = await _api.translate(text: txt, srcLang: _srcLang, tgtLang: _tgtLang);
    final gofSentenceForIgt = _srcLang.startsWith('gof') ? txt : (res['translation'] ?? txt).toString();
    final sovRes = await _api.analyzeSentenceInterlinearSOV(gofSentenceForIgt);
    final words = txt.split(RegExp(r'\s+'));
    final firstWordMorph = words.isNotEmpty
        ? GofathoG2PTransliterator.analyzeWordMorphemes(words.first)
        : <Map<String, String>>[];
    final rawCits = (res['citations'] as List<dynamic>? ?? [])
        .whereType<Map>()
        .map((m) => m.map((k, v) => MapEntry(k.toString(), v.toString())))
        .toList();
    final rawTiers = (sovRes['interlinear_tiers'] as Map<dynamic, dynamic>? ?? {})
        .map((k, v) => MapEntry(k.toString(), v.toString()));
    final rawSovToks = (sovRes['tokens'] as List<dynamic>? ?? [])
        .whereType<Map>()
        .map((m) => m.map((k, v) => MapEntry(k.toString(), v)))
        .toList();
    if (!mounted) return;
    setState(() {
      _translatedText = (res['translation'] ?? '').toString();
      _fidelScript = (res['fidel_script'] ?? GofathoG2PTransliterator.latinToFidel(txt)).toString();
      _methodBadge = (res['method'] ?? 'hybrid_rag').toString();
      _confidenceTier = (res['confidence_tier'] ?? 'verified_corpus').toString();
      _isUncertain = res['is_uncertain'] == true || _confidenceTier == 'uncertain_needs_review';
      _morphemes = firstWordMorph;
      _citations = rawCits;
      _interlinearTiers = rawTiers;
      _sovTokens = rawSovToks;
      _loading = false;
    });
  }

  Future<void> _speakTranslationAloud() async {
    final targetText = (_tgtLang.startsWith('gof') ? _inputCtrl.text : _translatedText).trim();
    final res = await _speech.speakGofathoOrTrilingual(
      text: targetText,
      langCode: _tgtLang,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text((res['user_notice'] ?? 'Audio guide ready').toString()),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  Future<void> _copyTranslationToClipboard() async {
    final payload = _showFidelDualScript
        ? '$_translatedText\nFidel: $_fidelScript'
        : _translatedText;
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied translation & Fidel script to clipboard')),
    );
  }

  void _showCitationDetailModal(Map<String, String> cit) {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.verified, color: Color(0xFF15803D)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${cit['category'] ?? 'Source'} • ${cit['id'] ?? ''}',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(cit['title'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
            const SizedBox(height: 6),
            Text(cit['excerpt'] ?? '', style: const TextStyle(fontSize: 13)),
            const Divider(height: 20),
            Text('Authority: ${cit['source'] ?? 'Verified Gofatho Corpus'}',
                style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  void _openSuggestModal() {
    final corrCtrl = TextEditingController(text: _isUncertain ? '' : _translatedText);
    final noteCtrl = TextEditingController();
    String selectedWoreda = 'Sawula Town';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Suggest Better Gofatho Translation (Milestone 5.1)',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: corrCtrl,
              decoration: const InputDecoration(
                labelText: 'Verified Translation / Orthography',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              value: selectedWoreda,
              items: const [
                DropdownMenuItem(value: 'Sawula Town', child: Text('Sawula Town')),
                DropdownMenuItem(value: 'Bulqi (Geze Gofa)', child: Text('Bulqi (Geze Gofa)')),
                DropdownMenuItem(value: 'Laha (Melekoza)', child: Text('Laha (Melekoza)')),
                DropdownMenuItem(value: 'Beto (Zala)', child: Text('Beto (Zala)')),
                DropdownMenuItem(value: 'Demba Gofa', child: Text('Demba Gofa')),
                DropdownMenuItem(value: 'Oyda Woreda', child: Text('Oyda Woreda')),
              ],
              onChanged: (v) => selectedWoreda = v ?? 'Sawula Town',
              decoration: const InputDecoration(
                labelText: 'Speaker Woreda / Dialect',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: noteCtrl,
              decoration: const InputDecoration(
                labelText: 'Linguistic / Cultural Note (Optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: const Icon(Icons.check_circle_outline),
                label: const Text('Save to Offline Queue & Sync'),
                onPressed: () async {
                  await GofathoDatabaseService.instance.insertFeedbackOffline(
                    sourceText: _inputCtrl.text.trim(),
                    sourceLang: _srcLang,
                    targetLang: _tgtLang,
                    initialAiOutput: _translatedText,
                    suggestedCorrection: corrCtrl.text.trim(),
                    fidelScript: GofathoG2PTransliterator.latinToFidel(corrCtrl.text.trim()),
                    woredaDialect: selectedWoreda,
                    contributorRole: 'Native Speaker',
                    domainCategory: 'Mobile Translator',
                    linguisticNote: noteCtrl.text.trim(),
                  );
                  if (ctx.mounted) Navigator.pop(ctx);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Saved correction to SQLite feedback queue!')),
                    );
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Language Direction Selector Bar
        Card(
          elevation: 0,
          color: cs.surfaceContainerHighest,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                Expanded(
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _srcLang,
                      isExpanded: true,
                      items: const [
                        DropdownMenuItem(value: 'gof_Latn', child: Text('Gofatho (Latin)')),
                        DropdownMenuItem(value: 'gof_Ethi', child: Text('Gofatho (Fidel ጎፋꬶ)')),
                        DropdownMenuItem(value: 'amh_Ethi', child: Text('Amharic (አማርኛ)')),
                        DropdownMenuItem(value: 'eng_Latn', child: Text('English')),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _srcLang = v);
                      },
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Swap Source and Target Languages',
                  icon: const Icon(Icons.swap_horiz),
                  onPressed: () {
                    setState(() {
                      final tmp = _srcLang;
                      _srcLang = _tgtLang;
                      _tgtLang = tmp;
                    });
                    _runTranslation();
                  },
                ),
                Expanded(
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _tgtLang,
                      isExpanded: true,
                      items: const [
                        DropdownMenuItem(value: 'eng_Latn', child: Text('English')),
                        DropdownMenuItem(value: 'amh_Ethi', child: Text('Amharic (አማርኛ)')),
                        DropdownMenuItem(value: 'gof_Latn', child: Text('Gofatho (Latin)')),
                        DropdownMenuItem(value: 'gof_Ethi', child: Text('Gofatho (Fidel ጎፋꬶ)')),
                      ],
                      onChanged: (v) {
                        if (v != null) setState(() => _tgtLang = v);
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Source Input Box
        TextField(
          controller: _inputCtrl,
          maxLines: 3,
          decoration: InputDecoration(
            labelText: 'Source Text (Preserves Glottal Stop 7 = /ʔ/)',
            border: const OutlineInputBorder(),
            suffixIcon: IconButton(
              tooltip: 'Clear Input',
              icon: const Icon(Icons.clear),
              onPressed: () => _inputCtrl.clear(),
            ),
          ),
        ),
        const SizedBox(height: 10),

        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                icon: _loading
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.translate),
                label: Text(widget.i18n.t('translate_btn')),
                onPressed: _loading ? null : _runTranslation,
              ),
            ),
            const SizedBox(width: 10),
            FilterChip(
              label: const Text('Dual-Script Fidel'),
              selected: _showFidelDualScript,
              onSelected: (v) => setState(() => _showFidelDualScript = v),
            ),
          ],
        ),
        if (_loading) ...[
          const SizedBox(height: 8),
          Text(
            'Querying local SQLite FTS5 & Render Cloud RAG (${_api.baseUrl})...',
            style: TextStyle(fontSize: 12, color: cs.primary),
          ),
        ],
        const SizedBox(height: 16),

        // Output Card
        Card(
          elevation: 2,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  alignment: WrapAlignment.spaceBetween,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Chip(
                          label: Text(_methodBadge, style: const TextStyle(fontSize: 11)),
                          visualDensity: VisualDensity.compact,
                        ),
                        const SizedBox(width: 6),
                        Chip(
                          backgroundColor: _isUncertain ? Colors.amber.shade100 : Colors.green.shade100,
                          label: Text(
                            _isUncertain ? '⚠️ Needs Native Review' : '✅ Verified Grounded',
                            style: TextStyle(
                              fontSize: 11,
                              color: _isUncertain ? Colors.brown.shade900 : Colors.green.shade900,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          visualDensity: VisualDensity.compact,
                        ),
                      ],
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          tooltip: 'Copy Translation & Fidel Script',
                          icon: const Icon(Icons.copy_all_outlined),
                          onPressed: _copyTranslationToClipboard,
                        ),
                        IconButton(
                          tooltip: widget.i18n.t('speak_btn'),
                          icon: const Icon(Icons.volume_up),
                          onPressed: _speakTranslationAloud,
                        ),
                        IconButton(
                          tooltip: widget.i18n.t('suggest_btn'),
                          icon: const Icon(Icons.rate_review_outlined),
                          onPressed: _openSuggestModal,
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SelectableText(
                  _translatedText,
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    color: _isUncertain ? Colors.amber.shade900 : null,
                  ),
                ),
                if (_showFidelDualScript) ...[
                  const Divider(height: 24),
                  Text(
                    'Gofatho Ethiopic Fidel (ኦራꬃ ጫቁዋ Transliteration):',
                    style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
                  ),
                  const SizedBox(height: 4),
                  SelectableText(
                    _fidelScript,
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w500),
                  ),
                ],
                if (_citations.isNotEmpty) ...[
                  const Divider(height: 24),
                  Text(
                    'Verified Corpus Citations (Tap chip to inspect source):',
                    style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: _citations
                        .map((cit) => ActionChip(
                              avatar: const Icon(Icons.menu_book, size: 15),
                              label: Text(
                                '${cit['id']} • ${cit['title']}',
                                style: const TextStyle(fontSize: 11),
                              ),
                              onPressed: () => _showCitationDetailModal(cit),
                            ))
                        .toList(),
                  ),
                ],
                if (_interlinearTiers.isNotEmpty) ...[
                  const Divider(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '4-Tier Interlinear Leipzig Glossing & SOV Constituent Roles:',
                          style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant, fontWeight: FontWeight.w600),
                        ),
                      ),
                      IconButton(
                        tooltip: 'Copy 4-Tier Interlinear Gloss',
                        icon: const Icon(Icons.copy, size: 16),
                        onPressed: () async {
                          final igtCopy = 'Tier 1 (Surface): ${_interlinearTiers['tier_1_surface_latin'] ?? ''}\n'
                              'Tier 2 (Fidel): ${_interlinearTiers['tier_2_surface_fidel'] ?? ''}\n'
                              'Tier 3 (Morphemes): ${_interlinearTiers['tier_3_morpheme_break'] ?? ''}\n'
                              'Tier 4 (Leipzig): ${_interlinearTiers['tier_4_leipzig_gloss'] ?? ''}';
                          await Clipboard.setData(ClipboardData(text: igtCopy));
                          if (!mounted) return;
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Copied 4-Tier Interlinear Gloss to clipboard')),
                          );
                        },
                      ),
                    ],
                  ),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: cs.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SelectableText('1. Surface: ${_interlinearTiers['tier_1_surface_latin'] ?? ''}',
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 12, fontWeight: FontWeight.w600)),
                        SelectableText('2. Fidel:   ${_interlinearTiers['tier_2_surface_fidel'] ?? ''}',
                            style: TextStyle(fontSize: 12, color: cs.primary)),
                        SelectableText('3. Morphs:  ${_interlinearTiers['tier_3_morpheme_break'] ?? ''}',
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
                        SelectableText('4. Leipzig: ${_interlinearTiers['tier_4_leipzig_gloss'] ?? ''}',
                            style: TextStyle(fontFamily: 'monospace', fontSize: 12, color: cs.tertiary)),
                      ],
                    ),
                  ),
                  if (_sovTokens.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: _sovTokens
                          .map((tok) => ActionChip(
                                avatar: const Icon(Icons.account_tree_outlined, size: 14),
                                label: Text(
                                  '${tok['surface']} [${(tok['sov_role'] ?? '').toString().split(' ').first}] • ${tok['leipzig_gloss']}',
                                  style: const TextStyle(fontSize: 11),
                                ),
                                onPressed: () => _speech.speakGofathoOrTrilingual(
                                  text: (tok['surface'] ?? '').toString(),
                                  langCode: 'gof_Latn',
                                ),
                              ))
                          .toList(),
                    ),
                  ],
                ],
                if (_morphemes.isNotEmpty) ...[
                  const Divider(height: 24),
                  Text(
                    'Morphological Decomposition (Sellassie Cheru 2015 Rules):',
                    style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: _morphemes
                        .map((m) => Chip(
                              label: Text('${m['morpheme']} • ${m['gloss']}'),
                              visualDensity: VisualDensity.compact,
                            ))
                        .toList(),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}
