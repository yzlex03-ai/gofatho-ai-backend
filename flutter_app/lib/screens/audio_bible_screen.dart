import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../l10n/app_localizations.dart';
import '../models/gofatho_models.dart';
import '../services/database_service.dart';
import '../services/speech_service.dart';

/// Option 4 Interactive WebAudio Karaoke Player Screen for iOS & Android.
/// Synchronizes 260 chapters, 7,931 verse clips, and 22,017 sub-verse phrase slices (`1a -> 1b -> 1c`)
/// with a 96-bar interactive CustomPainter waveform scrubber and real-time sub-phrase karaoke highlighting.
class AudioBibleScreen extends StatefulWidget {
  final GofathoLocalizations i18n;
  const AudioBibleScreen({super.key, required this.i18n});

  @override
  State<AudioBibleScreen> createState() => _AudioBibleScreenState();
}

class _AudioBibleScreenState extends State<AudioBibleScreen> {
  static const Map<String, Map<String, dynamic>> _ntBooks = {
    'MAT': {'lat': 'Maatoosa', 'fid': 'ማቶሳ', 'ch': 28},
    'MRK': {'lat': 'Marqqoosa', 'fid': 'ማርቆሳ', 'ch': 16},
    'LUK': {'lat': 'Luuqaasa', 'fid': 'ሉቃሳ', 'ch': 24},
    'JHN': {'lat': 'Yohaannisa', 'fid': 'ዮሃኒሳ', 'ch': 21},
    'ACT': {'lat': 'Hawaareta Oosuwa', 'fid': 'ሃዋሬታ ኦሱዋ', 'ch': 28},
    'ROM': {'lat': 'Roome', 'fid': 'ሮሜ', 'ch': 16},
    '1CO': {'lat': '1 Qoronttoosa', 'fid': '1 ቆሮንቶሳ', 'ch': 16},
    '2CO': {'lat': '2 Qoronttoosa', 'fid': '2 ቆሮንቶሳ', 'ch': 13},
    'GAL': {'lat': 'Galaatiya', 'fid': 'ጋላቲያ', 'ch': 6},
    'EPH': {'lat': 'Efesoona', 'fid': 'ኤፌሶና', 'ch': 6},
    'PHP': {'lat': 'Filphisiyuusa', 'fid': 'ፊልጲሲዩሳ', 'ch': 4},
    'COL': {'lat': 'Qolaasiyasa', 'fid': 'ቆላሲያሳ', 'ch': 4},
    '1TH': {'lat': '1 Teselonqe', 'fid': '1 ቴሴሎንቄ', 'ch': 5},
    '2TH': {'lat': '2 Teselonqe', 'fid': '2 ቴሴሎንቄ', 'ch': 3},
    '1TI': {'lat': '1 Ximotiyoosa', 'fid': '1 ፂሞቲዮሳ', 'ch': 6},
    '2TI': {'lat': '2 Ximotiyoosa', 'fid': '2 ፂሞቲዮሳ', 'ch': 4},
    'TIT': {'lat': 'Tito', 'fid': 'ቲቶ', 'ch': 3},
    'PHM': {'lat': 'Filmmoona', 'fid': 'ፊልሞና', 'ch': 1},
    'HEB': {'lat': 'Ibraawe', 'fid': 'ኢብራዌ', 'ch': 13},
    'JAS': {'lat': 'Yayqooba', 'fid': 'ያይቆባ', 'ch': 5},
    '1PE': {'lat': '1 Phexiroosa', 'fid': '1 ጴፂሮሳ', 'ch': 5},
    '2PE': {'lat': '2 Phexiroosa', 'fid': '2 ጴፂሮሳ', 'ch': 3},
    '1JN': {'lat': '1 Yohaannisa', 'fid': '1 ዮሃኒሳ', 'ch': 5},
    '2JN': {'lat': '2 Yohaannisa', 'fid': '2 ዮሃኒሳ', 'ch': 1},
    '3JN': {'lat': '3 Yohaannisa', 'fid': '3 ዮሃኒሳ', 'ch': 1},
    'JUD': {'lat': 'Yihuda', 'fid': 'ዪሁዳ', 'ch': 1},
    'REV': {'lat': 'Yohaannisa Qonccethaa', 'fid': 'ዮሃኒሳ ቆንጬꬃ', 'ch': 22},
  };

  String _selectedBook = 'MAT';
  int _selectedChapter = 1;
  List<VerseAudioClip> _clips = [];
  final Set<String> _bookmarkedVerses = <String>{};

  bool _isPlaying = false;
  double _playbackSpeed = 1.0;
  double _currentTimeSec = 7.96;
  double _targetEndSec = 238.76;
  int _activeVerseIndex = 0;
  String _activePhraseTag = '1';
  String _activeKaraokeLatin = '';
  String _activeKaraokeFidel = '';
  Timer? _karaokeTimer;

  @override
  void initState() {
    super.initState();
    _loadChapter();
  }

  @override
  void dispose() {
    _karaokeTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadChapter() async {
    _stopPlayback();
    final clips = await GofathoDatabaseService.instance.getChapterAudioClips(_selectedBook, _selectedChapter);
    if (!mounted) return;
    setState(() {
      _clips = clips;
      if (clips.isNotEmpty) {
        _activeVerseIndex = 0;
        _currentTimeSec = clips.first.startSec;
        _targetEndSec = clips.last.endSec;
        _syncKaraokeState(_currentTimeSec);
      }
    });
  }

  void _stopPlayback() {
    _karaokeTimer?.cancel();
    _karaokeTimer = null;
    if (mounted) {
      setState(() => _isPlaying = false);
    }
  }

  void _startPlaybackWindow(double startSec, double endSec) {
    _karaokeTimer?.cancel();
    setState(() {
      _currentTimeSec = startSec;
      _targetEndSec = endSec;
      _isPlaying = true;
      _syncKaraokeState(_currentTimeSec);
    });

    _karaokeTimer = Timer.periodic(const Duration(milliseconds: 50), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _currentTimeSec += 0.05 * _playbackSpeed;
        if (_currentTimeSec >= _targetEndSec) {
          _currentTimeSec = _targetEndSec;
          _syncKaraokeState(_currentTimeSec);
          _stopPlayback();
        } else {
          _syncKaraokeState(_currentTimeSec);
        }
      });
    });
  }

  void _toggleChapterPlayback() {
    if (_isPlaying) {
      _stopPlayback();
      return;
    }
    if (_clips.isEmpty) return;
    final start = _currentTimeSec >= _clips.last.endSec ? _clips.first.startSec : _currentTimeSec;
    _startPlaybackWindow(start, _clips.last.endSec);
  }

  Future<void> _playVerseOrPhraseSlice(int verseIdx, PhraseAudioSlice? phrase) async {
    if (_clips.isEmpty) return;
    final clip = _clips[verseIdx];
    final start = phrase != null ? phrase.startSec : clip.startSec;
    final end = phrase != null ? phrase.endSec : clip.endSec;
    final sliceLatin = phrase != null ? phrase.textLatin : clip.gofathoLatin;
    _startPlaybackWindow(start, end);
    await GofathoSpeechService.instance.playTimeSlice(
      audioUrlOrAsset: clip.mp3Filename,
      startSec: start,
      endSec: end,
      sliceTextLatin: sliceLatin,
    );
  }

  void _syncKaraokeState(double tSec) {
    if (_clips.isEmpty) return;
    VerseAudioClip matchedClip = _clips.first;
    PhraseAudioSlice? matchedPhrase;

    for (var i = 0; i < _clips.length; i++) {
      final c = _clips[i];
      if (tSec >= c.startSec && tSec <= c.endSec + 0.05) {
        matchedClip = c;
        _activeVerseIndex = i;
        for (final p in c.phrases) {
          if (tSec >= p.startSec && tSec <= p.endSec + 0.05) {
            matchedPhrase = p;
            break;
          }
        }
        break;
      }
    }

    if (matchedPhrase != null) {
      _activePhraseTag = matchedPhrase.phraseTag;
      _activeKaraokeLatin = matchedPhrase.textLatin;
      _activeKaraokeFidel = matchedPhrase.textFidel;
    } else {
      _activePhraseTag = matchedClip.verse;
      _activeKaraokeLatin = matchedClip.gofathoLatin;
      _activeKaraokeFidel = matchedClip.gofathoFidel;
    }
  }

  String _formatTimestamp(double sec) {
    final s = math.max(0.0, sec);
    final mins = (s ~/ 60).toString().padLeft(2, '0');
    final rem = (s % 60).toStringAsFixed(2).padLeft(5, '0');
    return '$mins:$rem';
  }

  @override
  Widget build(BuildContext context) {
    final maxChapters = (_ntBooks[_selectedBook]?['ch'] as int?) ?? 1;
    final totalDur = _clips.isNotEmpty ? _clips.last.endSec : 240.0;

    return Column(
      children: [
        // Top Interactive WebAudio Karaoke Deck
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF1B365D), Color(0xFF0F213C)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: DropdownButton<String>(
                      value: _selectedBook,
                      isExpanded: true,
                      dropdownColor: const Color(0xFF1B365D),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                      items: _ntBooks.entries.map((e) {
                        return DropdownMenuItem(
                          value: e.key,
                          child: Text('${e.value['lat']} (${e.value['fid']})'),
                        );
                      }).toList(),
                      onChanged: (v) {
                        if (v != null) {
                          setState(() {
                            _selectedBook = v;
                            _selectedChapter = 1;
                          });
                          _loadChapter();
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  DropdownButton<int>(
                    value: _selectedChapter,
                    dropdownColor: const Color(0xFF1B365D),
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    items: List.generate(
                      maxChapters,
                      (i) => DropdownMenuItem(value: i + 1, child: Text('Ch. ${i + 1}')),
                    ),
                    onChanged: (v) {
                      if (v != null) {
                        setState(() => _selectedChapter = v);
                        _loadChapter();
                      }
                    },
                  ),
                  const SizedBox(width: 8),
                  PopupMenuButton<double>(
                    initialValue: _playbackSpeed,
                    onSelected: (spd) => setState(() => _playbackSpeed = spd),
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: 0.75, child: Text('0.75x Slow Study')),
                      PopupMenuItem(value: 1.0, child: Text('1.0x Normal')),
                      PopupMenuItem(value: 1.25, child: Text('1.25x Fast')),
                    ],
                    child: Chip(
                      backgroundColor: Colors.amber.shade700,
                      label: Text('${_playbackSpeed}x', style: const TextStyle(color: Colors.white, fontSize: 11)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              // Interactive 96-Bar Waveform Scrubber
              GestureDetector(
                onTapDown: (details) {
                  if (_clips.isEmpty) return;
                  final box = context.findRenderObject() as RenderBox?;
                  final width = box?.size.width ?? 360.0;
                  final ratio = (details.localPosition.dx / width).clamp(0.0, 1.0);
                  final seekSec = ratio * totalDur;
                  _startPlaybackWindow(seekSec, _clips.last.endSec);
                },
                child: SizedBox(
                  height: 44,
                  width: double.infinity,
                  child: CustomPaint(
                    painter: _WaveformKaraokePainter(
                      progress: totalDur > 0 ? (_currentTimeSec / totalDur).clamp(0.0, 1.0) : 0.0,
                      seedOffset: _selectedChapter * 7 + _clips.length,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 6),
              // Live Sub-Verse Phrase Karaoke Display Banner
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(8),
                  border: const Border(left: BorderSide(color: Color(0xFFD97706), width: 3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          '[$_selectedBook $_selectedChapter:$_activePhraseTag] Karaoke Slice',
                          style: const TextStyle(color: Color(0xFFFBBF24), fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                        const Spacer(),
                        Text(
                          '${_formatTimestamp(_currentTimeSec)} / ${_formatTimestamp(totalDur)}',
                          style: const TextStyle(color: Colors.white70, fontSize: 11, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      _activeKaraokeLatin,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                    Text(
                      _activeKaraokeFidel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  FilledButton.icon(
                    style: FilledButton.styleFrom(backgroundColor: const Color(0xFFB43E27)),
                    icon: Icon(_isPlaying ? Icons.pause : Icons.play_arrow),
                    label: Text(_isPlaying ? 'Pause Karaoke' : 'Play Chapter'),
                    onPressed: _toggleChapterPlayback,
                  ),
                  Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.skip_previous, color: Colors.white),
                        onPressed: () {
                          if (_clips.isEmpty) return;
                          final prev = math.max(0, _activeVerseIndex - 1);
                          _playVerseOrPhraseSlice(prev, null);
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.skip_next, color: Colors.white),
                        onPressed: () {
                          if (_clips.isEmpty) return;
                          final next = math.min(_clips.length - 1, _activeVerseIndex + 1);
                          _playVerseOrPhraseSlice(next, null);
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
        // Synchronized Verse & Sub-Verse Phrase Cards
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _clips.length,
            itemBuilder: (ctx, idx) {
              final clip = _clips[idx];
              final isActiveVerse = idx == _activeVerseIndex;
              return Card(
                elevation: isActiveVerse ? 3 : 1,
                color: isActiveVerse ? const Color(0xFFFFFBEB) : Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                  side: BorderSide(
                    color: isActiveVerse ? const Color(0xFFD97706) : Colors.grey.shade200,
                    width: isActiveVerse ? 2.0 : 1.0,
                  ),
                ),
                margin: const EdgeInsets.only(bottom: 10),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: isActiveVerse ? const Color(0xFFB43E27) : const Color(0xFF1B365D),
                            child: Text(clip.verse, style: const TextStyle(color: Colors.white, fontSize: 11)),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '${clip.startSec.toStringAsFixed(2)}s – ${clip.endSec.toStringAsFixed(2)}s (${clip.durationSec.toStringAsFixed(1)}s)',
                            style: const TextStyle(fontSize: 11, color: Colors.black54, fontFamily: 'monospace'),
                          ),
                          const Spacer(),
                          IconButton(
                            tooltip: 'Bookmark Verse',
                            icon: Icon(
                              _bookmarkedVerses.contains('$_selectedBook.$_selectedChapter.${clip.verse}')
                                  ? Icons.bookmark
                                  : Icons.bookmark_border,
                              size: 19,
                              color: const Color(0xFFD97706),
                            ),
                            onPressed: () {
                              final key = '$_selectedBook.$_selectedChapter.${clip.verse}';
                              setState(() {
                                if (_bookmarkedVerses.contains(key)) {
                                  _bookmarkedVerses.remove(key);
                                } else {
                                  _bookmarkedVerses.add(key);
                                }
                              });
                            },
                          ),
                          IconButton(
                            tooltip: 'Copy Quad-Parallel Verse',
                            icon: const Icon(Icons.copy_all_outlined, size: 18),
                            onPressed: () async {
                              await Clipboard.setData(ClipboardData(
                                text: '[$_selectedBook $_selectedChapter:${clip.verse}]\nGOF: ${clip.gofathoLatin}\nFidel: ${clip.gofathoFidel}\nAM: ${clip.amharicTranslation}\nEN: ${clip.englishTranslation}',
                              ));
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Copied $_selectedBook $_selectedChapter:${clip.verse} to clipboard')),
                                );
                              }
                            },
                          ),
                          FilledButton.tonalIcon(
                            icon: Icon(isActiveVerse && _isPlaying ? Icons.volume_up : Icons.play_circle_outline, size: 18),
                            label: Text('Slice (${clip.phrases.length}p)', style: const TextStyle(fontSize: 12)),
                            onPressed: () => _playVerseOrPhraseSlice(idx, null),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(clip.gofathoLatin, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(clip.gofathoFidel, style: const TextStyle(fontSize: 15, color: Color(0xFF1B365D))),
                      const SizedBox(height: 6),
                      Text('EN: ${clip.englishTranslation}', style: const TextStyle(fontSize: 13, color: Colors.black87)),
                      Text('AM: ${clip.amharicTranslation}', style: const TextStyle(fontSize: 13, color: Color(0xFF15803D))),
                      if (clip.phrases.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: clip.phrases.map((ph) {
                            final activePh = isActiveVerse && _activePhraseTag == ph.phraseTag;
                            return ActionChip(
                              backgroundColor: activePh ? const Color(0xFFFEF3C7) : const Color(0xFFF2ECE1),
                              side: BorderSide(
                                color: activePh ? const Color(0xFFD97706) : Colors.grey.shade400,
                                width: activePh ? 1.5 : 0.8,
                              ),
                              label: Text(
                                '[${ph.phraseTag}] ${ph.startSec.toStringAsFixed(1)}–${ph.endSec.toStringAsFixed(1)}s',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: activePh ? FontWeight.bold : FontWeight.normal,
                                  color: activePh ? const Color(0xFF92400E) : Colors.black87,
                                ),
                              ),
                              onPressed: () => _playVerseOrPhraseSlice(idx, ph),
                            );
                          }).toList(),
                        ),
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

class _WaveformKaraokePainter extends CustomPainter {
  final double progress;
  final int seedOffset;

  const _WaveformKaraokePainter({required this.progress, required this.seedOffset});

  @override
  void paint(Canvas canvas, Size size) {
    const barCount = 96;
    final barWidth = size.width / barCount;
    final activePaint = Paint()..color = const Color(0xFFFBBF24);
    final inactivePaint = Paint()..color = Colors.white24;

    for (var i = 0; i < barCount; i++) {
      final ratio = i / barCount;
      final wave = (math.sin(i * 1.6 + seedOffset) * 0.5 + 0.5);
      final barHeight = 8.0 + wave * (size.height - 12.0);
      final rect = RRect.fromRectAndRadius(
        Rect.fromLTWH(
          i * barWidth + 1.0,
          (size.height - barHeight) / 2.0,
          math.max(1.5, barWidth - 2.0),
          barHeight,
        ),
        const Radius.circular(2),
      );
      canvas.drawRRect(rect, ratio <= progress ? activePaint : inactivePaint);
    }

    final cursorX = (progress * size.width).clamp(0.0, size.width - 2.0);
    final cursorPaint = Paint()..color = const Color(0xFFEF4444);
    canvas.drawRect(Rect.fromLTWH(cursorX, 0, 2.5, size.height), cursorPaint);
  }

  @override
  bool shouldRepaint(covariant _WaveformKaraokePainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.seedOffset != seedOffset;
  }
}
