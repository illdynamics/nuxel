package org.nuxel.penguru;

import android.content.Context;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;

/**
 * One Android TextToSpeech engine that can be owned by either the visible
 * Activity or the persistent SonarBird service.
 *
 * Keeping the engine in the foreground service is what makes spoken answers
 * work while PenGuru is not on screen: the Activity can be stopped (or never
 * become visible after a wake-word hand-off) without losing the reply voice.
 */
final class TalkbackEngine {
    private static final String TAG = "PenGuruTTS";
    static final String PREFS = "penguru_ui";
    static final String PREF_ENGINE = "tts_engine";
    static final String PREF_RATE = "tts_rate";
    static final String PREF_PITCH = "tts_pitch";
    static final String PREF_LANGUAGE = "tts_language";

    interface Callback {
        /** "speaking", "idle", "error" or "unavailable". */
        void onState(String state);
    }

    private final Context context;
    private final Callback callback;
    private final Handler main = new Handler(Looper.getMainLooper());
    private TextToSpeech tts;
    private boolean ready;
    private boolean initStarted;
    private boolean shutDown;
    private int generation;
    private String lastError = "";
    private String engine = "";
    private String language = "";
    private float rate = 1.0f;
    private float pitch = 1.0f;
    private String pendingText = "";
    private String activeUtterance = "";
    private String state = "idle";

    TalkbackEngine(Context context, Callback callback) {
        this.context = context.getApplicationContext();
        this.callback = callback;
        loadConfig();
    }

    private void loadConfig() {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        engine = prefs.getString(PREF_ENGINE, "");
        language = prefs.getString(PREF_LANGUAGE, "");
        rate = prefs.getFloat(PREF_RATE, 1.0f);
        pitch = prefs.getFloat(PREF_PITCH, 1.0f);
    }

    synchronized void ensure() {
        if (tts != null || initStarted || shutDown) {
            return;
        }
        initStarted = true;
        final int token = ++generation;
        loadConfig();
        final String requestedEngine = engine;
        TextToSpeech.OnInitListener listener = status -> main.post(() -> {
            if (shutDown || token != generation) {
                return;
            }
            if (status == TextToSpeech.SUCCESS && tts != null) {
                ready = true;
                lastError = "";
                attachListener();
                applyConfig();
                String queued = pendingText;
                pendingText = "";
                if (!queued.isEmpty()) {
                    speakNow(queued);
                } else {
                    updateState("idle");
                }
            } else {
                ready = false;
                initStarted = false;
                pendingText = "";
                lastError = "tts_init_failed";
                TextToSpeech failed = tts;
                tts = null;
                if (failed != null) {
                    try {
                        failed.shutdown();
                    } catch (RuntimeException ignored) {
                        // already shut down
                    }
                }
                updateState("unavailable");
            }
        });
        try {
            if (requestedEngine != null && !requestedEngine.isEmpty()) {
                tts = new TextToSpeech(context, listener, requestedEngine);
            } else {
                tts = new TextToSpeech(context, listener);
            }
        } catch (RuntimeException error) {
            tts = null;
            ready = false;
            initStarted = false;
            pendingText = "";
            lastError = String.valueOf(error.getMessage());
            updateState("unavailable");
        }
    }

    /** Queue a complete answer. Returns false only when there is nothing to say. */
    synchronized boolean speak(String text) {
        String value = sanitize(text);
        if (value.isEmpty()) {
            return false;
        }
        if (shutDown) {
            return false;
        }
        if (tts == null) {
            ensure();
        }
        if (!ready) {
            pendingText = value;
            return true;
        }
        return speakNow(value);
    }

    private boolean speakNow(String value) {
        if (tts == null || !ready) {
            pendingText = value;
            return true;
        }
        applyConfig();
        try {
            String utteranceId = "penguru-" + System.currentTimeMillis();
            activeUtterance = utteranceId;
            int result = tts.speak(value, TextToSpeech.QUEUE_FLUSH, null, utteranceId);
            if (result == TextToSpeech.SUCCESS) {
                lastError = "";
                updateState("speaking");
                return true;
            }
            activeUtterance = "";
            lastError = "tts_speak_failed";
        } catch (RuntimeException error) {
            lastError = String.valueOf(error.getMessage());
        }
        updateState("error");
        return false;
    }

    synchronized void stop() {
        pendingText = "";
        activeUtterance = "";
        if (tts != null) {
            try {
                tts.stop();
            } catch (RuntimeException ignored) {
                // already stopped
            }
        }
        updateState("idle");
    }

    synchronized void shutdown() {
        shutDown = true;
        generation++;
        pendingText = "";
        activeUtterance = "";
        TextToSpeech current = tts;
        tts = null;
        ready = false;
        initStarted = false;
        if (current != null) {
            try {
                current.stop();
            } catch (RuntimeException ignored) {
                // already stopped
            }
            try {
                current.shutdown();
            } catch (RuntimeException ignored) {
                // already shut down
            }
        }
    }

    synchronized boolean configure(String optionsJson) {
        try {
            JSONObject options = new JSONObject(optionsJson == null ? "{}" : optionsJson);
            String requestedEngine = options.has("engine")
                    ? options.optString("engine", "") : engine;
            String requestedLanguage = options.has("language")
                    ? options.optString("language", language) : language;
            float requestedRate = options.has("rate")
                    ? (float) Math.max(0.4, Math.min(2.5, options.optDouble("rate", rate)))
                    : rate;
            float requestedPitch = options.has("pitch")
                    ? (float) Math.max(0.4, Math.min(2.5, options.optDouble("pitch", pitch)))
                    : pitch;
            boolean engineChanged = requestedEngine == null
                    ? engine != null && !engine.isEmpty()
                    : !requestedEngine.equals(engine == null ? "" : engine);
            engine = requestedEngine == null ? "" : requestedEngine;
            language = requestedLanguage == null ? "" : requestedLanguage;
            rate = requestedRate;
            pitch = requestedPitch;
            SharedPreferences.Editor editor = context
                    .getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit();
            editor.putString(PREF_ENGINE, engine);
            editor.putString(PREF_LANGUAGE, language);
            editor.putFloat(PREF_RATE, rate);
            editor.putFloat(PREF_PITCH, pitch);
            editor.apply();
            if (engineChanged) {
                main.post(this::reinitialize);
            } else {
                main.post(this::applyConfig);
            }
            return true;
        } catch (Exception error) {
            lastError = String.valueOf(error.getMessage());
            return false;
        }
    }

    private synchronized void reinitialize() {
        if (shutDown) {
            return;
        }
        generation++;
        TextToSpeech current = tts;
        tts = null;
        ready = false;
        initStarted = false;
        if (current != null) {
            try {
                current.stop();
            } catch (RuntimeException ignored) {
                // already stopped
            }
            try {
                current.shutdown();
            } catch (RuntimeException ignored) {
                // already shut down
            }
        }
        ensure();
    }

    synchronized boolean isReady() {
        return ready;
    }

    synchronized String statusJson() {
        if (tts == null && !initStarted) {
            main.post(this::ensure);
        }
        JSONObject out = new JSONObject();
        try {
            boolean available = ready;
            if (!available && tts != null) {
                try {
                    available = tts.getEngines() != null && !tts.getEngines().isEmpty();
                } catch (RuntimeException ignored) {
                    available = false;
                }
            }
            String defaultEngine = "";
            if (tts != null && ready) {
                try {
                    defaultEngine = tts.getDefaultEngine();
                } catch (RuntimeException ignored) {
                    defaultEngine = "";
                }
            }
            out.put("available", available);
            out.put("ready", ready);
            out.put("engine", defaultEngine == null ? "" : defaultEngine);
            out.put("language", language);
            out.put("rate", rate);
            out.put("pitch", pitch);
            out.put("speaking", tts != null && ready && tts.isSpeaking());
            out.put("state", state);
            out.put("error", lastError);
        } catch (Exception error) {
            // JSONObject only receives primitive values.
        }
        return out.toString();
    }

    synchronized String enginesJson() {
        if (tts == null && !initStarted) {
            main.post(this::ensure);
        }
        JSONArray out = new JSONArray();
        try {
            JSONObject system = new JSONObject();
            system.put("name", "");
            system.put("label", "System default engine");
            out.put(system);
            if (tts == null) {
                return out.toString();
            }
            for (TextToSpeech.EngineInfo info : tts.getEngines()) {
                JSONObject entry = new JSONObject();
                entry.put("name", info.name);
                String label = info.label == null || info.label.trim().isEmpty()
                        ? info.name : info.label;
                entry.put("label", label);
                out.put(entry);
            }
        } catch (Exception error) {
            // Return the entries found so far.
        }
        return out.toString();
    }

    private void attachListener() {
        if (tts == null) {
            return;
        }
        try {
            tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override public void onStart(String utteranceId) {
                    main.post(() -> {
                        if (utteranceId != null && utteranceId.equals(activeUtterance)) {
                            updateState("speaking");
                        }
                    });
                }
                @Override public void onDone(String utteranceId) {
                    main.post(() -> {
                        if (utteranceId != null && utteranceId.equals(activeUtterance)) {
                            activeUtterance = "";
                            updateState("idle");
                        }
                    });
                }
                @Override public void onError(String utteranceId) {
                    main.post(() -> {
                        if (utteranceId != null && utteranceId.equals(activeUtterance)) {
                            activeUtterance = "";
                            lastError = "tts_error";
                            updateState("error");
                        }
                    });
                }
                @Override public void onError(String utteranceId, int errorCode) {
                    main.post(() -> {
                        if (utteranceId != null && utteranceId.equals(activeUtterance)) {
                            activeUtterance = "";
                            lastError = "tts_error_" + errorCode;
                            updateState("error");
                        }
                    });
                }
            });
        } catch (RuntimeException error) {
            lastError = String.valueOf(error.getMessage());
        }
    }

    private synchronized void applyConfig() {
        if (tts == null || !ready) {
            return;
        }
        // The Activity and the background service share these preferences;
        // reload them so whichever engine is active uses the latest settings.
        loadConfig();
        try {
            int result;
            if (language != null && !language.isEmpty()) {
                result = tts.setLanguage(Locale.forLanguageTag(language));
            } else {
                result = tts.setLanguage(Locale.getDefault());
            }
            if (result == TextToSpeech.LANG_MISSING_DATA
                    || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                lastError = "language_not_supported";
            }
            tts.setSpeechRate(rate);
            tts.setPitch(pitch);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                tts.setAudioAttributes(new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANT)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build());
            }
        } catch (RuntimeException error) {
            lastError = String.valueOf(error.getMessage());
        }
    }

    private void updateState(String next) {
        if (shutDown) {
            return;
        }
        boolean changed = state == null || !state.equals(next);
        state = next;
        if (changed && callback != null) {
            try {
                callback.onState(next);
            } catch (RuntimeException error) {
                Log.w(TAG, "Talkback callback failed: " + error);
            }
        }
    }

    /** Android TTS otherwise pronounces decorative separators literally. */
    static String sanitize(String text) {
        if (text == null) {
            return "";
        }
        String value = text.replace('·', ' ').replace('•', ' ')
                .replace('…', '.').replace('\n', ' ').replace('\r', ' ');
        value = value.replaceAll("[\t ]{2,}", " ").trim();
        if (value.length() > 12000) {
            value = value.substring(0, 11999) + "…";
        }
        return value;
    }
}
