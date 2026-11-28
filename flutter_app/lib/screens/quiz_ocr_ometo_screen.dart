import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../l10n/app_localizations.dart';
import '../services/database_service.dart';
import '../services/g2p_transliterator.dart';
import '../services/speech_service.dart';

typedef CommunityQuizOcrOmetoScreen = QuizOcrOmetoScreen;

class QuizOcrOmetoScreen extends StatefulWidget {
  final GofathoLocalizations? i18n;
  const QuizOcrOmetoScreen({super.key, this.i18n});

  @override
  State<QuizOcrOmetoScreen> createState() => _QuizOcrOmetoScreenState();
}

class _QuizOcrOmetoScreenState extends State<QuizOcrOmetoScreen> {
  String _selectedSubTab = 'FST Paradigms';
  String _fstQuery = '';
  int _quizIndex = 0;
  int _quizScore = 0;
  String? _selectedAnswer;
  String _ocrInputText =
      'Goofatho doonay Dugeha Toophphiyaan Goofa Zooniyan haasayettiyaa doona. Lo77o na7ay timirtte keetha baas.';
  late final TextEditingController _ocrCtrl = TextEditingController(text: _ocrInputText);

  List<Map<String, dynamic>> _fstRows = [];
  List<Map<String, dynamic>> _igtRows = [];

  static const List<Map<String, String>> _fallbackFstRows = [
    {
      'form_type': 'VERB_CONJUGATION',
      'root_or_lemma': 'tamaar- (to learn)',
      'category_or_case': 'PRES_AFF_DCL',
      'png_or_number': '1S (Group A)',
      'surface_latin': 'tamaarays',
      'surface_fidel': 'ታማአራይስ',
      'morpheme_breakdown': 'tamaar-ays',
      'english_gloss': 'I learn / am learning',
      'amharic_gloss': 'እማራለሁ',
      'mp_rules_applied': 'Group A vocalic linker -a-',
    },
    {
      'form_type': 'VERB_CONJUGATION',
      'root_or_lemma': 'b- (to go)',
      'category_or_case': 'PAST_AFF_DCL',
      'png_or_number': '3PL (Group I/O/E)',
      'surface_latin': 'bidosona',
      'surface_fidel': 'ቢዶሶና',
      'morpheme_breakdown': 'b-idosona',
      'english_gloss': 'they went',
      'amharic_gloss': 'ሄዱ',
      'mp_rules_applied': 'Group I/O/E linker -i- + -dosona',
    },
    {
      'form_type': 'NOUN_DECLENSION',
      'root_or_lemma': 'keethi (house)',
      'category_or_case': 'ABL (-ppe)',
      'png_or_number': 'SG.DEF',
      'surface_latin': 'keethappe',
      'surface_fidel': 'ኬꬃፔ',
      'morpheme_breakdown': 'keeth-a-ppe',
      'english_gloss': 'from the house',
      'amharic_gloss': 'ከቤቱ',
      'mp_rules_applied': 'MP-01 Terminal Vowel Replacement',
    },
  ];

  final List<Map<String, dynamic>> _sampleQuizzes = [
    {
      'q': '1. [Minniyaa vs. Leppiya] Which Gofatho word means "ten (10 / አሥር)" as opposed to "fire (እሳት)"?',
      'options': ['tamma (Minniyaa /m:/)', 'tama (Leppiya /m/)', 'taama', 'tamo'],
      'ans': 'tamma (Minniyaa /m:/)',
      'exp': 'tama (singleton /m/) = fire (እሳት); tamma (geminate /m:/) = ten (አሥር).',
    },
    {
      'q': '2. [FST Morphology — Sellassie Cheru 2015] Which suffix marks 3rd Person Plural Past Affirmative ("they did")?',
      'options': ['-idosona', '-oosona', '-ibeenna', '-ays'],
      'ans': '-idosona',
      'exp': '-idosona marks PAST.3PL.AFF.DCL (e.g., b-idosona = they went), while -oosona marks Present/Habitual 3PL.',
    },
    {
      'q': '3. [Grade 10 Aaqeta Idioms] What does the Gofatho idiom "Aawu mithi" (አአዉ ሚꬂ) mean?',
      'options': [
        'Something inevitable / unavoidable duty (የማይቀር ነገር)',
        'A tall forest tree',
        'Building a new house',
        'Market day exchange'
      ],
      'ans': 'Something inevitable / unavoidable duty (የማይቀር ነገር)',
      'exp': 'From Grade 10 p. 88 ("Hayqoy asa na7as aawu mithi" — Death is an inevitable natural duty for humanity).',
    },
    {
      'q': '4. [Converb Harmony — Group A vs. Group I/O/E] Which anterior converb suffix is required for 1st Person Singular ("Taani ...")?',
      'options': ['-ada (Group A: 1S/2S/3FS)', '-idi (Group I/O/E: 3MS/1PL/2PL/3PL)', '-ishin', '-ikko'],
      'ans': '-ada (Group A: 1S/2S/3FS)',
      'exp': 'Sellassie Cheru (2015) Ch. 7: Group A subjects (Taani, Neeni, A [3FS]) take -ada (e.g. b-ada), while 3MS/Plural take -idi (b-idi).',
    },
  ];

  final List<Map<String, String>> _sampleOmeto = [
    {
      'gof': 'keethi (ኬꬂ)',
      'gmv': 'keetstsi',
      'dwr': 'keetta',
      'wal': 'keettaa',
      'amh': 'ቤት',
      'eng': 'house (Ometo sibilant/dental correspondence th ↔ ts ↔ tt)'
    },
    {
      'gof': 'lo77o (ሎዖ)',
      'gmv': 'lo77o',
      'dwr': 'lo77o',
      'wal': 'lo77o',
      'amh': 'ጥሩ / መልካም',
      'eng': 'good (shared North Ometo glottal stop 7 = /ʔ/)'
    },
    {
      'gof': 'entti (እንቲ)',
      'gmv': 'isti',
      'dwr': 'unttoo',
      'wal': 'eti',
      'amh': 'እነሱ',
      'eng': 'they (3PL Nominative Pronoun across Ometo cluster)'
    },
  ];

  @override
  void initState() {
    super.initState();
    _loadFstAndIgt();
  }

  Future<void> _loadFstAndIgt() async {
    final fst = await GofathoDatabaseService.instance.searchFstInflections(query: _fstQuery, limit: 40);
    final igt = await GofathoDatabaseService.instance.searchIgtSentences(query: _fstQuery, limit: 30);
    if (!mounted) return;
    setState(() {
      _fstRows = fst.isNotEmpty ? fst : _fallbackFstRows;
      _igtRows = igt;
    });
  }

  @override
  Widget build(BuildContext context) {
    const tabs = ['FST Paradigms', 'Meeze Quiz', 'Ometo Bridge', 'Fidel & OCR'];
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Wrap(
            spacing: 8,
            children: tabs
                .map((t) => ChoiceChip(
                      label: Text(t),
                      selected: _selectedSubTab == t,
                      onSelected: (_) => setState(() => _selectedSubTab = t),
                    ))
                .toList(),
          ),
        ),
        Expanded(
          child: _selectedSubTab == 'FST Paradigms'
              ? _buildFstParadigmTab()
              : _selectedSubTab == 'Meeze Quiz'
                  ? _buildQuizTab()
                  : _selectedSubTab == 'Ometo Bridge'
                      ? _buildOmetoTab()
                      : _buildOcrTab(),
        ),
      ],
    );
  }

  Widget _buildFstParadigmTab() {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        const Text(
          '🔬 Forward FST Conjugator/Decliner (3,480 Forms) & Sellassie Cheru (2015) IGT Bank',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        TextField(
          decoration: InputDecoration(
            prefixIcon: const Icon(Icons.search),
            hintText: 'Search 3,480 verb/noun inflections or 615 IGT sentences...',
            isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
          ),
          onChanged: (v) {
            _fstQuery = v;
            _loadFstAndIgt();
          },
        ),
        const SizedBox(height: 10),
        ..._fstRows.map((item) {
          final surfLat = (item['surface_latin'] ?? '').toString();
          final surfFid = (item['surface_fidel'] ?? '').toString().isNotEmpty
              ? item['surface_fidel'].toString()
              : GofathoG2PTransliterator.latinToFidel(surfLat);
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(surfLat, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1B365D))),
                      const SizedBox(width: 8),
                      Text(surfFid, style: const TextStyle(fontSize: 15, color: Colors.deepPurple)),
                      const Spacer(),
                      Chip(
                        label: Text('${item['category_or_case'] ?? ''} • ${item['png_or_number'] ?? item['person_or_number'] ?? ''}', style: const TextStyle(fontSize: 10)),
                        visualDensity: VisualDensity.compact,
                      ),
                      IconButton(
                        tooltip: 'Pronounce FST Inflected Form',
                        icon: const Icon(Icons.volume_up, size: 18),
                        onPressed: () async {
                          final res = await GofathoSpeechService.instance.speakGofathoOrTrilingual(text: surfLat);
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text((res['user_notice'] ?? 'Audio guide ready').toString())),
                            );
                          }
                        },
                      ),
                      IconButton(
                        tooltip: 'Copy FST Paradigm Entry',
                        icon: const Icon(Icons.copy_all_outlined, size: 18),
                        onPressed: () async {
                          await Clipboard.setData(ClipboardData(text: '$surfLat ($surfFid) — ${item['english_gloss']} | ${item['amharic_gloss']}'));
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Copied $surfLat to clipboard')),
                            );
                          }
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text('Root: ${item['root_or_lemma']}  |  Morphemes: ${item['morpheme_breakdown']}', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                  Text('🇬🇧 ${item['english_gloss']}  •  🇪🇹 ${item['amharic_gloss']}', style: const TextStyle(fontSize: 13)),
                  if ((item['mp_rules_applied'] ?? '').toString().isNotEmpty)
                    Text('Rule: ${item['mp_rules_applied']}', style: const TextStyle(fontSize: 11, color: Colors.black54)),
                ],
              ),
            ),
          );
        }),
        if (_igtRows.isNotEmpty) ...[
          const Divider(height: 24),
          const Text('📖 Matched Interlinear Glossed Sentences (IGT):', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          ..._igtRows.take(10).map((r) => Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text('${r['gofatho_surface']} (${r['igt_code']})', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('Morph: ${r['phonemic_segmentation']}\nGloss: ${r['leipzig_gloss']}\nEN: ${r['english_translation']} | AM: ${r['amharic_translation']}'),
                ),
              )),
        ],
      ],
    );
  }

  Widget _buildQuizTab() {
    final q = _sampleQuizzes[_quizIndex % _sampleQuizzes.length];
    final opts = List<String>.from(q['options'] as List);
    return ListView(
      padding: const EdgeInsets.all(14),
      children: [
        Text(
            '🎓 Grade 8–10 Meeze, FST Grammar & Gemination Quiz (Score: $_quizScore)',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(q['q'] as String,
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                ...opts.map((opt) => RadioListTile<String>(
                      title: Text(opt),
                      value: opt,
                      groupValue: _selectedAnswer,
                      onChanged: (v) {
                        setState(() {
                          _selectedAnswer = v;
                          if (v == q['ans']) _quizScore++;
                        });
                      },
                    )),
                if (_selectedAnswer != null) ...[
                  const Divider(),
                  Text('Explanation: ${q['exp']}',
                      style: const TextStyle(
                          color: Colors.teal, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  ElevatedButton(
                    onPressed: () => setState(() {
                      _quizIndex++;
                      _selectedAnswer = null;
                    }),
                    child: const Text('Next Question ->'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildOmetoTab() {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        const Text(
            '🌍 North Omotic Ometo Cluster Bridge (Gofa ↔ Gamo ↔ Dawuro ↔ Wolaytta)',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        ..._sampleOmeto.map((r) => Card(
              child: ListTile(
                title: Text('Gofatho: ${r['gof']}  |  Gamotho: ${r['gmv']}'),
                subtitle: Text(
                    'Dawuro: ${r['dwr']}  |  Wolaytta: ${r['wal']}\nAmharic: ${r['amh']} • English: ${r['eng']}'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      tooltip: 'Pronounce Gofatho Cognate',
                      icon: const Icon(Icons.volume_up, size: 18),
                      onPressed: () async {
                        final res = await GofathoSpeechService.instance.speakGofathoOrTrilingual(text: r['gof'] ?? '');
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text((res['user_notice'] ?? 'Audio guide ready').toString())),
                          );
                        }
                      },
                    ),
                    IconButton(
                      tooltip: 'Copy Ometo Cognate Row',
                      icon: const Icon(Icons.copy_all_outlined, size: 18),
                      onPressed: () async {
                        await Clipboard.setData(ClipboardData(
                            text: 'GOF: ${r['gof']} | GMV: ${r['gmv']} | DWR: ${r['dwr']} | WAL: ${r['wal']} — ${r['eng']} (${r['amh']})'));
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Copied Ometo cognate comparison to clipboard')),
                          );
                        }
                      },
                    ),
                  ],
                ),
              ),
            )),
      ],
    );
  }

  Widget _buildOcrTab() {
    final fidelOut = GofathoG2PTransliterator.latinToFidel(_ocrInputText);
    final morphs = _ocrInputText
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty)
        .take(6)
        .map((w) => '$w -> ${GofathoG2PTransliterator.analyzeWordMorphemes(w).map((m) => m['morpheme']).join('+')}')
        .toList();
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        const Text('📷 Dual-Script Ethiopic Extended-A Fidel & Morpheme Scanner',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        TextField(
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Enter Gofatho Latin Text (Preserves Glottal Stop 7 = /ʔ/)',
            border: OutlineInputBorder(),
          ),
          controller: _ocrCtrl,
          onChanged: (v) => setState(() => _ocrInputText = v),
        ),
        const SizedBox(height: 10),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Gofatho Ethiopic Fidel (ኦራꬃ ጫቁዋ) Output:',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                SelectableText(fidelOut, style: const TextStyle(fontSize: 16, color: Color(0xFF1B365D))),
                const Divider(height: 20),
                const Text('Morpheme Decomposition Preview:',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: morphs.map((m) => Chip(label: Text(m, style: const TextStyle(fontSize: 11)))).toList(),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
