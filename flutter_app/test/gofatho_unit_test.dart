import 'package:flutter_test/flutter_test.dart';
import 'package:gofatho_ai/services/g2p_transliterator.dart';
import 'package:gofatho_ai/services/api_sync_service.dart';
import 'package:gofatho_ai/services/speech_service.dart';

void main() {
  group('GofathoG2PTransliterator Tests', () {
    test('Preserves glottal stop (7) and Extended-A characters in Fidel output', () {
      final fidel = GofathoG2PTransliterator.latinToFidel('Saro pe7adii? Goofatho');
      expect(fidel.contains('ዓ'), isTrue);
      expect(fidel.contains('ꬆ'), isTrue);
    });

    test('Decomposes Gofatho verbal suffixes accurately', () {
      final morph = GofathoG2PTransliterator.analyzeWordMorphemes('gakkidosona');
      expect(morph.length, greaterThanOrEqualTo(2));
      expect(morph.first['morpheme'], equals('gakk'));
      expect(morph.last['morpheme'], equals('-idosona'));
    });
  });

  group('GofathoApiSyncService & SpeechService Configuration Tests (v6.2)', () {
    test('Defaults to production Render backend URL and 35s cold-start timeout', () {
      final api = GofathoApiSyncService.instance;
      expect(api.baseUrl, equals('https://gofatho-ai-backend-1.onrender.com'));
      expect(GofathoApiSyncService.renderColdStartTimeout.inSeconds, greaterThanOrEqualTo(30));
    });

    test('SpeechService normalizes phonemic glottal stop and generates Sherpa tokens', () {
      final speech = GofathoSpeechService.instance;
      expect(speech.preparePhonemicInput('Loʔʔo'), equals('lo77o'));
      expect(speech.toSherpaTokens('Saro pe7adii'), equals('s a r o   p e 7 a d i i'));
    });
  });
}
