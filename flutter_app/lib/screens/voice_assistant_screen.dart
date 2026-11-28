import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../l10n/app_localizations.dart';
import '../services/api_sync_service.dart';
import '../services/g2p_transliterator.dart';
import '../services/speech_service.dart';

class VoiceAssistantScreen extends StatefulWidget {
  final GofathoLocalizations i18n;
  const VoiceAssistantScreen({super.key, required this.i18n});

  @override
  State<VoiceAssistantScreen> createState() => _VoiceAssistantScreenState();
}

class _VoiceAssistantScreenState extends State<VoiceAssistantScreen> {
  final GofathoApiSyncService _api = GofathoApiSyncService.instance;
  final GofathoSpeechService _speech = GofathoSpeechService.instance;
  final TextEditingController _msgCtrl = TextEditingController();
  bool _isRecording = false;
  bool _isLoading = false;
  String _selectedTopic = 'general';

  static const List<Map<String, String>> _topics = [
    {'id': 'general', 'label': '🌍 All Topics'},
    {'id': 'culture', 'label': '🏛️ Goofa Woga (Culture)'},
    {'id': 'curriculum', 'label': '🎓 Grade 8–10 Tutor'},
    {'id': 'proverbs', 'label': '📜 Tosse (Proverbs)'},
    {'id': 'daily', 'label': '💬 Daily Conversation'},
    {'id': 'grammar', 'label': '🧩 Maara Qaala (Grammar)'},
  ];

  static const List<String> _starterPrompts = [
    'Goofa wogan eko geloy waanidi oosettii?',
    'Teach me 3 Gofatho proverbs (Tosse) with Amharic & English meanings',
    'Explain Grade 9 Bila-Oda conflict resolution in Gofatho',
    'How do I greet elders in Sawla & Bulqi?',
    'Break down grammar: Entti timirtte keettaa bidosona',
  ];

  final List<Map<String, dynamic>> _messages = [
    {
      'role': 'assistant',
      'mode': 'On-Device SQLite RAG + Render Cloud Ready (1,334 Lexicon • 2,072 Phrases • 1,305 Textbook Drills)',
      'confidence_tier': 'verified_corpus',
      'latin': 'Saro pe7adii! Taani Gofatho AI (Goofatho Woga, Maara Qaalanne Timirtte Maaddiyaa). Goofatho, Amaaratho woy Inggilizetho doonan oychcha!',
      'fidel': 'ሳሮ ፐዓዲኢ! ታአኒ ጎፋꬆ ኤአይ። ጎኦፋꬆ፣ አማአራꬆ ዎይ ኢንግጊሊዘꬆ ዶኦናን ኦይችቻ!',
      'amharic': 'እንደምን አደሩ! እኔ የጎፋኛ AI አስተማሪና የባህል ረዳት ነኝ። ስለ ጎፋ ባህል (Goofa Woga)፣ ስለ 8-10ኛ ክፍል ትምህርት ወይም የዕለት ተዕለት ንግግር በጎፋኛ፣ በአማርኛ ወይም በእንግሊዝኛ ይጠይቁኝ!',
      'english': 'Good morning! I am your Native Gofatho AI Tutor & Cultural Assistant, connected to both your offline SQLite corpus and the Render Hybrid RAG server.',
      'grammar_notes': 'Grounded in Sellassie Cheru (2015) SOV grammar + SNNPR Grade 8–10 Goofatho Doona textbooks.',
      'dict_count': 1334,
      'phrase_count': 2072,
      'meeze_count': 1305,
      'citations': <Map<String, String>>[
        {
          'category': 'Dictionary',
          'id': 'LEX-CORPUS',
          'title': 'Sellassie Cheru (2015) & Grade 8–10 Glossaries',
          'excerpt': '1,334 verified Gofatho headwords with IPA, POS, English, and Amharic glosses.',
          'source': 'AAU PhD Dissertation (2015) & SNNPR Goofatho Doona Textbooks',
        },
        {
          'category': 'Phrasebook',
          'id': 'PHR-0001',
          'title': 'Greetings & Daily Courtesies',
          'excerpt': 'Saro pe7adii? = How did you spend the day? / Good morning.',
          'source': 'Verified Gofatho Everyday Phrasebook (2,072 entries)',
        },
      ],
    }
  ];

  @override
  void dispose() {
    _msgCtrl.dispose();
    super.dispose();
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

  void _openAiSettingsModal() {
    final keyCtrl = TextEditingController(text: _api.geminiApiKey);
    final urlCtrl = TextEditingController(text: _api.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('⚙️ Native Gofatho AI & Cloud Settings'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Option A — Direct On-Device Gemini 2.5 Flash + Local SQLite RAG:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: keyCtrl,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Google AI Studio Gemini API Key (Optional)',
                  hintText: 'Paste key from aistudio.google.com',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Option B — Hosted Render FastAPI v6.2 RAG Server URL:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: urlCtrl,
                decoration: const InputDecoration(
                  labelText: 'Cloud FastAPI Server URL',
                  hintText: GofathoApiSyncService.defaultProductionBackendUrl,
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              setState(() {
                _api.geminiApiKey = keyCtrl.text.trim();
                if (urlCtrl.text.trim().isNotEmpty) {
                  _api.baseUrl = urlCtrl.text.trim();
                }
              });
              Navigator.pop(ctx);
            },
            child: const Text('Save AI Config'),
          ),
        ],
      ),
    );
  }

  void _openVoiceSampleSelectorSheet() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.mic_external_on, color: Color(0xFFD97706)),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Gofatho Voice Input & Meta MMS-1B CTC Rescorer',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Note: Offline microphone capture requires the 60MB Meta MMS-1B ONNX ASR pack or active cloud streaming. Select a verified Gofatho voice query below or type in the chat box:',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _starterPrompts.map((p) {
                return ActionChip(
                  avatar: const Icon(Icons.record_voice_over, size: 15),
                  label: Text(p, style: const TextStyle(fontSize: 12)),
                  onPressed: () {
                    Navigator.pop(ctx);
                    _sendMessage(p);
                  },
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty || _isLoading) return;
    final userTxt = text.trim();
    _msgCtrl.clear();

    final historySnapshot = _messages
        .map((m) => {
              'role': (m['role'] ?? 'user').toString(),
              'latin': (m['latin'] ?? '').toString(),
            })
        .toList();

    setState(() {
      _messages.add({
        'role': 'user',
        'latin': userTxt,
        'fidel': GofathoG2PTransliterator.latinToFidel(userTxt),
      });
      _isLoading = true;
    });

    final res = await _api.chatWithNativeGofathoAi(
      message: userTxt,
      topic: _selectedTopic,
      history: historySnapshot,
    );

    final rawCits = (res['citations'] as List<dynamic>? ?? [])
        .whereType<Map>()
        .map((m) => m.map((k, v) => MapEntry(k.toString(), v.toString())))
        .toList();

    if (!mounted) return;
    setState(() {
      _isLoading = false;
      _messages.add({
        'role': 'assistant',
        'mode': res['mode'] ?? 'Offline SQLite RAG',
        'confidence_tier': res['confidence_tier'] ?? 'verified_corpus',
        'latin': res['gofatho_latin'] ?? '',
        'fidel': res['gofatho_fidel'] ?? '',
        'amharic': res['amharic'] ?? '',
        'english': res['english'] ?? '',
        'grammar_notes': res['grammar_notes'] ?? '',
        'dict_count': res['dict_count'] ?? 0,
        'phrase_count': res['phrase_count'] ?? 0,
        'meeze_count': res['meeze_count'] ?? 0,
        'citations': rawCits,
      });
    });
  }

  Future<void> _speakAssistantMessage(Map<String, dynamic> m) async {
    final gofLat = (m['latin'] ?? '').toString();
    final res = await _speech.speakGofathoOrTrilingual(text: gofLat, langCode: 'gof_Latn');
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text((res['user_notice'] ?? 'Audio guide ready').toString()),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  Future<void> _copyAssistantMessage(Map<String, dynamic> m) async {
    final payload = 'GOF (Latin): ${m['latin'] ?? ''}\n'
        'GOF (Fidel): ${m['fidel'] ?? ''}\n'
        'AM: ${m['amharic'] ?? ''}\n'
        'EN: ${m['english'] ?? ''}';
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied trilingual response to clipboard')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasGeminiKey = _api.geminiApiKey.trim().length >= 10;
    return Column(
      children: [
        // Top Status & Settings Banner
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          color: const Color(0xFF1B365D),
          child: Row(
            children: [
              Icon(
                hasGeminiKey ? Icons.auto_awesome : Icons.cloud_done_outlined,
                color: Colors.amberAccent,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  hasGeminiKey
                      ? '🟢 Gemini 2.5 Flash + On-Device SQLite RAG Active'
                      : '⚡ Render Cloud RAG (${_api.baseUrl}) + Offline SQLite',
                  style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
              TextButton.icon(
                style: TextButton.styleFrom(
                  foregroundColor: Colors.amberAccent,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                ),
                onPressed: _openAiSettingsModal,
                icon: const Icon(Icons.vpn_key, size: 15),
                label: const Text('AI Settings', style: TextStyle(fontSize: 12)),
              ),
            ],
          ),
        ),
        // Topic Selector Bar
        SizedBox(
          height: 44,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            itemCount: _topics.length,
            separatorBuilder: (_, __) => const SizedBox(width: 6),
            itemBuilder: (ctx, idx) {
              final t = _topics[idx];
              final selected = _selectedTopic == t['id'];
              return ChoiceChip(
                label: Text(t['label']!, style: const TextStyle(fontSize: 11)),
                selected: selected,
                onSelected: (_) => setState(() => _selectedTopic = t['id']!),
              );
            },
          ),
        ),
        // Starter Native Prompts Bar
        SizedBox(
          height: 36,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
            itemCount: _starterPrompts.length,
            separatorBuilder: (_, __) => const SizedBox(width: 6),
            itemBuilder: (ctx, idx) {
              final prompt = _starterPrompts[idx];
              return ActionChip(
                label: Text(prompt, style: const TextStyle(fontSize: 11)),
                onPressed: () => _sendMessage(prompt),
              );
            },
          ),
        ),
        const Divider(height: 1),
        // Chat Message Stream
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _messages.length + (_isLoading ? 1 : 0),
            itemBuilder: (ctx, idx) {
              if (idx == _messages.length) {
                return Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Retrieving Gofatho SQLite RAG & querying Render Cloud (${_api.baseUrl} — up to 35s on cold start)...',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                );
              }
              final m = _messages[idx];
              final isUser = m['role'] == 'user';
              if (isUser) {
                return Align(
                  alignment: Alignment.centerRight,
                  child: Card(
                    color: cs.primaryContainer,
                    margin: const EdgeInsets.only(bottom: 10, left: 40),
                    child: Padding(
                      padding: const EdgeInsets.all(10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SelectableText(
                            (m['latin'] ?? '').toString(),
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: cs.onPrimaryContainer),
                          ),
                          SelectableText(
                            (m['fidel'] ?? '').toString(),
                            style: TextStyle(color: cs.primary, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }
              final cits = (m['citations'] as List<dynamic>? ?? [])
                  .whereType<Map>()
                  .map((c) => c.map((k, v) => MapEntry(k.toString(), v.toString())))
                  .toList();
              final isUncertain = m['confidence_tier'] == 'uncertain_needs_review';

              return Align(
                alignment: Alignment.centerLeft,
                child: Card(
                  color: cs.surfaceContainerLow,
                  elevation: 2,
                  margin: const EdgeInsets.only(bottom: 12, right: 16),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: isUncertain ? Colors.amber.shade100 : Colors.teal.shade50,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  '🤖 ${m['mode']} • 📚 ${m['dict_count']} Lexicon • 💬 ${m['phrase_count']} Phrases • 🎓 ${m['meeze_count']} Textbook',
                                  style: TextStyle(
                                    fontSize: 10,
                                    color: isUncertain ? Colors.brown.shade900 : Colors.teal.shade900,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ),
                            IconButton(
                              tooltip: 'Read Gofatho Response Aloud',
                              icon: const Icon(Icons.volume_up, size: 18),
                              onPressed: () => _speakAssistantMessage(m),
                            ),
                            IconButton(
                              tooltip: 'Copy Trilingual Response',
                              icon: const Icon(Icons.copy_all_outlined, size: 18),
                              onPressed: () => _copyAssistantMessage(m),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        SelectableText(
                          (m['latin'] ?? '').toString(),
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: cs.primary),
                        ),
                        const SizedBox(height: 2),
                        SelectableText(
                          (m['fidel'] ?? '').toString(),
                          style: TextStyle(color: cs.tertiary, fontSize: 14),
                        ),
                        if ((m['amharic'] ?? '').toString().isNotEmpty) ...[
                          const Divider(height: 12),
                          SelectableText('🇪🇹 ${(m['amharic'] ?? '')}', style: const TextStyle(fontSize: 13)),
                        ],
                        if ((m['english'] ?? '').toString().isNotEmpty) ...[
                          const SizedBox(height: 4),
                          SelectableText('🇬🇧 ${(m['english'] ?? '')}', style: const TextStyle(fontSize: 13)),
                        ],
                        if ((m['grammar_notes'] ?? '').toString().isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.amber.shade50,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              '🧩 ${m['grammar_notes']}',
                              style: const TextStyle(fontSize: 11, color: Colors.brown),
                            ),
                          ),
                        ],
                        if (cits.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: cits.map((cit) {
                              return ActionChip(
                                visualDensity: VisualDensity.compact,
                                avatar: const Icon(Icons.verified_outlined, size: 14),
                                label: Text(
                                  '${cit['id']} • ${cit['title']}',
                                  style: const TextStyle(fontSize: 10),
                                ),
                                onPressed: () => _showCitationDetailModal(cit),
                              );
                            }).toList(),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        // Bottom Input & Voice Prompt Selector Bar
        Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            children: [
              IconButton.filledTonal(
                tooltip: widget.i18n.t('record_hold'),
                icon: Icon(_isRecording ? Icons.mic : Icons.mic_none),
                onPressed: _openVoiceSampleSelectorSheet,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: _msgCtrl,
                  decoration: const InputDecoration(
                    hintText: 'Ask in Gofatho, Amharic, or English...',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  onSubmitted: _sendMessage,
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                tooltip: 'Send Message',
                icon: const Icon(Icons.send),
                onPressed: () => _sendMessage(_msgCtrl.text),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
