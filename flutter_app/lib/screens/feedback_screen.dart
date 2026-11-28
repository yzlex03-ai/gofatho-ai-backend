import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../l10n/app_localizations.dart';
import '../models/gofatho_models.dart';
import '../services/api_sync_service.dart';
import '../services/database_service.dart';

class CommunityFeedbackScreen extends StatefulWidget {
  final GofathoLocalizations i18n;
  const CommunityFeedbackScreen({super.key, required this.i18n});

  @override
  State<CommunityFeedbackScreen> createState() => _CommunityFeedbackScreenState();
}

class _CommunityFeedbackScreenState extends State<CommunityFeedbackScreen> {
  final GofathoApiSyncService _api = GofathoApiSyncService();
  List<TranslationFeedback> _items = [];
  String _selectedWoreda = '';

  @override
  void initState() {
    super.initState();
    _loadFeedback();
  }

  Future<void> _loadFeedback() async {
    final rows = await GofathoDatabaseService.instance.getFeedbackList(woreda: _selectedWoreda);
    setState(() => _items = rows);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _selectedWoreda,
                  decoration: const InputDecoration(
                    labelText: 'Filter by Gofa Zone Woreda',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('All Gofa Zone Woredas')),
                    DropdownMenuItem(value: 'Sawula', child: Text('Sawula Town')),
                    DropdownMenuItem(value: 'Bulqi', child: Text('Bulqi (Geze Gofa)')),
                    DropdownMenuItem(value: 'Laha', child: Text('Laha (Melekoza)')),
                    DropdownMenuItem(value: 'Demba Gofa', child: Text('Demba Gofa')),
                    DropdownMenuItem(value: 'Zala', child: Text('Zala Woreda')),
                    DropdownMenuItem(value: 'Oyda', child: Text('Oyda Woreda')),
                  ],
                  onChanged: (v) {
                    setState(() => _selectedWoreda = v ?? '');
                    _loadFeedback();
                  },
                ),
              ),
              const SizedBox(width: 10),
              FilledButton.icon(
                icon: const Icon(Icons.cloud_upload),
                label: Text(widget.i18n.t('sync_btn')),
                onPressed: () async {
                  final count = await _api.syncPendingFeedbackToCloud();
                  await _loadFeedback();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Synced $count pending field corrections to FastAPI v3.0!')),
                    );
                  }
                },
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            itemCount: _items.length,
            itemBuilder: (ctx, idx) {
              final fb = _items[idx];
              return Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Chip(
                            label: Text('${fb.woredaDialect} • ${fb.contributorRole}', style: const TextStyle(fontSize: 11)),
                            visualDensity: VisualDensity.compact,
                          ),
                          const Spacer(),
                          Text('${fb.feedbackCode} • ▲ ${fb.upvotes}', style: const TextStyle(fontWeight: FontWeight.bold)),
                          IconButton(
                            tooltip: 'Copy Community Correction',
                            icon: const Icon(Icons.copy_all_outlined, size: 18),
                            onPressed: () async {
                              await Clipboard.setData(ClipboardData(
                                text: '[${fb.feedbackCode} - ${fb.woredaDialect}] Source: ${fb.sourceText} -> Verified Gofatho: ${fb.suggestedCorrection} (${fb.fidelScript})',
                              ));
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Copied ${fb.feedbackCode} to clipboard')),
                                );
                              }
                            },
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text('Source: ${fb.sourceText}', style: const TextStyle(fontSize: 13, color: Colors.black54)),
                      const SizedBox(height: 4),
                      Text('✅ Verified Gofatho: ${fb.suggestedCorrection}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                      Text('Fidel: ${fb.fidelScript}', style: const TextStyle(fontSize: 14, color: Colors.indigo)),
                      if (fb.linguisticNote.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text('Note: ${fb.linguisticNote}', style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
                      ],
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

typedef FeedbackScreen = CommunityFeedbackScreen;
