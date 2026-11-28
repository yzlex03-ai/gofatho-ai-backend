package et.gofazone.gofatho_ai

import android.os.Bundle
import android.speech.tts.TextToSpeech
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

class MainActivity : FlutterActivity(), TextToSpeech.OnInitListener {
    private val CHANNEL = "et.gofazone.gofatho_ai/speech"
    private var tts: TextToSpeech? = null
    private var ttsReady: Boolean = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tts = TextToSpeech(this, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            ttsReady = true
            tts?.language = Locale.US
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "speakText" -> {
                        val text = call.argument<String>("text") ?: ""
                        val rate = (call.argument<Double>("rate") ?: 1.0).toFloat()
                        if (!ttsReady || tts == null) {
                            result.success(
                                mapOf(
                                    "status" to "tts_unavailable",
                                    "spoken" to false,
                                    "note" to "Android TextToSpeech engine is not initialized on this device."
                                )
                            )
                        } else {
                            tts?.setSpeechRate(rate.coerceIn(0.5f, 2.0f))
                            val code = tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "gofatho_utt")
                            result.success(
                                mapOf(
                                    "status" to if (code == TextToSpeech.SUCCESS) "spoken_android_tts" else "tts_error",
                                    "spoken" to (code == TextToSpeech.SUCCESS)
                                )
                            )
                        }
                    }
                    "stopSpeech" -> {
                        tts?.stop()
                        result.success(mapOf("status" to "stopped"))
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }
}
