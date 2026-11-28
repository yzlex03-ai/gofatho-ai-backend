# Flutter Wrapper & JNI
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }

# Keep SQLite FTS5 & Tekartik Sqflite classes
-keep class com.tekartik.sqflite.** { *; }
-dontwarn com.tekartik.sqflite.**

# Keep ExoPlayer / JustAudio classes for Chapter MP3 Slicing
-keep class com.ryanheise.just_audio.** { *; }
-keep class androidx.media3.** { *; }
