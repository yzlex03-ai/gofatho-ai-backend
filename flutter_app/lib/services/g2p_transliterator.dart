/// Pure-Dart Bidirectional Gofatho Latin <-> Ethiopic Fidel ('ኦራꬃ ጫቁዋ') Transliterator,
/// Glottal Stop ('7' = /ʔ/) Normalizer, and Rule-Based Morphological Decomposer.
/// Grounded in Sellassie Cheru (2015) and SNNPR Grade 8–10 Goofatho Doona Textbooks.
class GofathoG2PTransliterator {
  static const Map<String, List<dynamic>> _digraphToFidel = {
    'th': ['ꬅ', {'a': 'ꬃ', 'aa': 'ꬃአ', 'u': 'ꬁ', 'uu': 'ꬁኡ', 'i': 'ꬂ', 'ii': 'ꬂኢ', 'e': 'ꬄ', 'ee': 'ꬄእ', 'o': 'ꬆ', 'oo': 'ꬆኦ'}],
    'dh': ['ꬍ', {'a': 'ꬋ', 'aa': 'ꬋአ', 'u': 'ꬉ', 'uu': 'ꬉኡ', 'i': 'ꬊ', 'ii': 'ꬊኢ', 'e': 'ꬌ', 'ee': 'ꬌእ', 'o': 'ꬎ', 'oo': 'ꬎኦ'}],
    'dz': ['ꬕ', {'a': 'ꬓ', 'aa': 'ꬓአ', 'u': 'ꬑ', 'uu': 'ꬑኡ', 'i': 'ꬒ', 'ii': 'ꬒኢ', 'e': 'ꬔ', 'ee': 'ꬔእ', 'o': 'ꬖ', 'oo': 'ꬖኦ'}],
    'sh': ['ሽ', {'a': 'ሻ', 'aa': 'ሻአ', 'u': 'ሹ', 'uu': 'ሹኡ', 'i': 'ሺ', 'ii': 'ሺኢ', 'e': 'ሼ', 'ee': 'ሼእ', 'o': 'ሾ', 'oo': 'ሾኦ'}],
    'ch': ['ች', {'a': 'ቻ', 'aa': 'ቻአ', 'u': 'ቹ', 'uu': 'ቹኡ', 'i': 'ቺ', 'ii': 'ቺኢ', 'e': 'ቼ', 'ee': 'ቼእ', 'o': 'ቾ', 'oo': 'ቾኦ'}],
    'ph': ['ጵ', {'a': 'ጳ', 'aa': 'ጳአ', 'u': 'ጱ', 'uu': 'ጱኡ', 'i': 'ጪ', 'ii': 'ጪኢ', 'e': 'ጴ', 'ee': 'ጴእ', 'o': 'ፆ', 'oo': 'ፆኦ'}],
    'ny': ['ኝ', {'a': 'ኛ', 'aa': 'ኛአ', 'u': 'ኙ', 'uu': 'ኙኡ', 'i': 'ኚ', 'ii': 'ኚኢ', 'e': 'ኜ', 'ee': 'ኜእ', 'o': 'ኞ', 'oo': 'ኞኦ'}],
    'zh': ['ዥ', {'a': 'ዣ', 'aa': 'ዣአ', 'u': 'ዡ', 'uu': 'ዡኡ', 'i': 'ዢ', 'ii': 'ዢኢ', 'e': 'ዤ', 'ee': 'ዤእ', 'o': 'ዦ', 'oo': 'ዦኦ'}],
  };

  static const Map<String, int> _singleConsonantBase = {
    'h': 0x1200, 'l': 0x1208, 'm': 0x1218, 'r': 0x1228, 's': 0x1230,
    'q': 0x1240, 'b': 0x1260, 't': 0x1270, 'n': 0x1290, 'k': 0x12A8,
    'w': 0x12C8, 'z': 0x12D8, 'y': 0x12E8, 'd': 0x12F0, 'j': 0x1300,
    'g': 0x1308, 'x': 0x1320, 'c': 0x1328, 'f': 0x1348, 'p': 0x1350,
  };

  static const Map<String, int> _vowelOffset = {'a': 0, 'u': 1, 'i': 2, 'e': 4, 'o': 6};
  static const Map<String, String> _longVowelSuffix = {'aa': 'አ', 'uu': 'ኡ', 'ii': 'ኢ', 'ee': 'እ', 'oo': 'ኦ'};
  static const Map<String, String> _standaloneVowels = {
    'a': 'አ', 'aa': 'አአ', 'u': 'ኡ', 'uu': 'ኡኡ', 'i': 'ኢ', 'ii': 'ኢኢ',
    'e': 'እ', 'ee': 'እእ', 'o': 'ኦ', 'oo': 'ኦኦ',
  };
  static const Map<String, String> _glottalVowels = {
    'a': 'ዓ', 'aa': 'ዓአ', 'u': 'ዑ', 'uu': 'ዑኡ', 'i': 'ዒ', 'ii': 'ዒኢ',
    'e': 'ዔ', 'ee': 'ዔእ', 'o': 'ዖ', 'oo': 'ዖኦ', '': 'ዕ',
  };

  /// Converts Gofatho Latin text into Gofatho Ethiopic Fidel ('ኦራꬃ ጫቁዋ')
  static String latinToFidel(String input) {
    if (input.isEmpty) return '';
    final s = input.replaceAll('ʔ', '7');
    final out = StringBuffer();
    int i = 0;
    final n = s.length;

    while (i < n) {
      final ch = s[i];
      final low = ch.toLowerCase();
      final isAlpha = RegExp(r'[a-z]').hasMatch(low);

      if (!isAlpha && low != '7') {
        if (ch == '.') {
          out.write('።');
        } else if (ch == ',') {
          out.write('፣');
        } else if (ch == ';') {
          out.write('፤');
        } else if (ch == ':') {
          out.write('፦');
        } else {
          out.write(ch);
        }
        i++;
        continue;
      }

      if (low == '7') {
        if (i + 1 < n && s[i + 1] == '7') {
          out.write('ዕ');
          i++;
        }
        final v2 = (i + 3 <= n) ? s.substring(i + 1, i + 3).toLowerCase() : '';
        final v1 = (i + 2 <= n) ? s.substring(i + 1, i + 2).toLowerCase() : '';
        if (v2.length == 2 && v2[0] == v2[1] && _glottalVowels.containsKey(v2)) {
          out.write(_glottalVowels[v2]);
          i += 3;
        } else if (v1.length == 1 && _glottalVowels.containsKey(v1)) {
          out.write(_glottalVowels[v1]);
          i += 2;
        } else {
          out.write('ዕ');
          i++;
        }
        continue;
      }

      if ('aeiou'.contains(low)) {
        final v2 = (i + 2 <= n) ? s.substring(i, i + 2).toLowerCase() : '';
        if (v2.length == 2 && _standaloneVowels.containsKey(v2)) {
          out.write(_standaloneVowels[v2]);
          i += 2;
        } else {
          out.write(_standaloneVowels[low] ?? ch);
          i++;
        }
        continue;
      }

      final digraph = (i + 2 <= n) ? s.substring(i, i + 2).toLowerCase() : '';
      if (_digraphToFidel.containsKey(digraph)) {
        final saddis = _digraphToFidel[digraph]![0] as String;
        final vmap = _digraphToFidel[digraph]![1] as Map<String, String>;
        final v2 = (i + 4 <= n) ? s.substring(i + 2, i + 4).toLowerCase() : '';
        final v1 = (i + 3 <= n) ? s.substring(i + 2, i + 3).toLowerCase() : '';
        if (v2.length == 2 && vmap.containsKey(v2)) {
          out.write(vmap[v2]);
          i += 4;
        } else if (v1.length == 1 && vmap.containsKey(v1)) {
          out.write(vmap[v1]);
          i += 3;
        } else {
          out.write(saddis);
          i += 2;
        }
        continue;
      }

      if (_singleConsonantBase.containsKey(low)) {
        final baseCp = _singleConsonantBase[low]!;
        final v2 = (i + 3 <= n) ? s.substring(i + 1, i + 3).toLowerCase() : '';
        final v1 = (i + 2 <= n) ? s.substring(i + 1, i + 2).toLowerCase() : '';
        if (v2.length == 2 && _longVowelSuffix.containsKey(v2)) {
          final vChar = String.fromCharCode(baseCp + _vowelOffset[v2[0]]!);
          out.write('$vChar${_longVowelSuffix[v2]}');
          i += 3;
        } else if (v1.length == 1 && _vowelOffset.containsKey(v1)) {
          out.write(String.fromCharCode(baseCp + _vowelOffset[v1]!));
          i += 2;
        } else {
          out.write(String.fromCharCode(baseCp + 5));
          i++;
        }
        continue;
      }

      out.write(ch);
      i++;
    }
    return out.toString();
  }

  /// Decomposes a Gofatho word into root + derivational/inflectional morphemes
  static List<Map<String, String>> analyzeWordMorphemes(String word) {
    final clean = word.replaceAll(RegExp(r'[^a-zA-Z7ʔ]'), '').toLowerCase().replaceAll('ʔ', '7');
    if (clean.isEmpty) return [];

    String stem = clean;
    final morphemes = <Map<String, String>>[];

    const verbalSuffixes = [
      ['idosona', '-idosona', 'PAST.3PL.AFF ("they did")'],
      ['oosona', '-oosona', 'PRES.3PL.AFF ("they do")'],
      ['ibeenna', '-ibeenna', 'PAST.3MS.NEG ("he did not")'],
      ['ideta', '-ideta', 'PAST.2PL.AFF ("you all did")'],
      ['anaw', '-ana-w', 'INF.PURP ("in order to")'],
      ['ikko', '-ikko', 'COND ("if")'],
      ['ishin', '-ishin', 'CNV.SIM.DS ("while doing")'],
      ['idi', '-idi', 'CNV.ANT ("having done")'],
      ['ada', '-ada', 'CNV.ANT.1S/2S ("having done")'],
      ['ays', '-ays', 'PRES.1S.AFF ("I do")'],
      ['oos', '-oos', 'PRES.1PL.AFF ("we do")'],
      ['ees', '-ees', 'PRES.3MS.AFF ("he/it does")'],
      ['enna', '-enna', 'PRES.3MS.NEG ("does not")'],
      ['ite', '-ite', 'IMP.2PL ("do! [plural]")'],
      ['iis', '-iis', 'PAST.3MS.AFF ("he/it did")'],
    ];

    const nominalSuffixes = [
      ['tappe', '-t-a-ppe', 'PL.ACC.ABL ("from the ...s")'],
      ['ti', '-t-i', 'PL.NOM (Plural Subject)'],
      ['ta', '-t-a', 'PL.ACC (Plural Object)'],
      ['ppe', '-ppe', 'ABL ("from / than")'],
      ['ra', '-ra', 'COM ("with")'],
      ['yssi', '-yss-i', 'NMZ.M.NOM ("the one who")'],
      ['y', '-y', 'NOM.M.DEF (Subject)'],
      ['n', '-n', 'LOC/INST ("in / with")'],
      ['s', '-s', 'DAT ("to / for")'],
      ['w', '-w', 'DAT ("to / for")'],
    ];

    bool matchedVerb = false;
    for (final s in verbalSuffixes) {
      if (stem.length > s[0].length + 1 && stem.endsWith(s[0])) {
        stem = stem.substring(0, stem.length - s[0].length);
        morphemes.insert(0, {'morpheme': s[1], 'gloss': s[2], 'type': 'Verbal Inflection'});
        matchedVerb = true;
        break;
      }
    }

    if (!matchedVerb) {
      for (final s in nominalSuffixes) {
        if (stem.length > s[0].length + 1 && stem.endsWith(s[0])) {
          stem = stem.substring(0, stem.length - s[0].length);
          morphemes.insert(0, {'morpheme': s[1], 'gloss': s[2], 'type': 'Nominal Case'});
          break;
        }
      }
    }

    morphemes.insert(0, {'morpheme': stem, 'gloss': 'Lexical Root', 'type': 'Root Stem'});
    return morphemes;
  }
}
