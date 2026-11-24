package org.nuxel.penguru;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.audiofx.AcousticEchoCanceler;
import android.media.audiofx.AutomaticGainControl;
import android.media.audiofx.NoiseSuppressor;
import android.speech.RecognitionService;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;
import java.util.Locale;

/** Shared voice preferences and Android speech-engine discovery. */
public final class VoiceSettings {
    public static final String PREFS = "penguru_voice";
    public static final String PREF_ENGINE = "engine_component";
    public static final String PREF_END_SILENCE = "end_silence_ms";
    public static final String PREF_VAD = "vad_enabled";
    public static final String PREF_COMMANDS = "commands_enabled";
    public static final String PREF_NOISE = "noise_suppression";

    public static final int DEFAULT_END_SILENCE_MS = 900;
    /** Persisted engine value for the bundled offline whisper.cpp path. */
    public static final String ENGINE_WHISPER = "whisper";

    private VoiceSettings() { }

    public static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static String engineComponent(Context context) {
        return prefs(context).getString(PREF_ENGINE, "");
    }

    public static void setEngineComponent(Context context, String component) {
        prefs(context).edit().putString(PREF_ENGINE,
                component == null ? "" : component.trim()).apply();
    }

    public static int endSilenceMs(Context context) {
        int value = prefs(context).getInt(PREF_END_SILENCE, DEFAULT_END_SILENCE_MS);
        return Math.max(350, Math.min(5000, value));
    }

    public static void setEndSilenceMs(Context context, int value) {
        prefs(context).edit().putInt(PREF_END_SILENCE,
                Math.max(350, Math.min(5000, value))).apply();
    }

    public static boolean commandsEnabled(Context context) {
        return prefs(context).getBoolean(PREF_COMMANDS, true);
    }

    public static void setCommandsEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(PREF_COMMANDS, enabled).apply();
    }

    public static boolean vadEnabled(Context context) {
        return prefs(context).getBoolean(PREF_VAD, true);
    }

    public static void setVadEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(PREF_VAD, enabled).apply();
    }

    public static String noiseMode(Context context) {
        return prefs(context).getString(PREF_NOISE, "auto");
    }

    public static void setNoiseMode(Context context, String mode) {
        prefs(context).edit().putString(PREF_NOISE,
                mode == null ? "auto" : mode.trim()).apply();
    }

    /** True when the owner selected the bundled offline Whisper engine. */
    public static boolean usesWhisper(Context context) {
        String raw = engineComponent(context);
        if (raw == null) {
            return false;
        }
        String value = raw.trim().toLowerCase(Locale.ROOT);
        return ENGINE_WHISPER.equals(value) || "whisper.cpp".equals(value)
                || "bundled-whisper".equals(value);
    }

    /** Selected recognizer, or null for the phone's default recognizer. */
    public static ComponentName recognizer(Context context) {
        String raw = engineComponent(context);
        if (raw == null || raw.trim().isEmpty()) {
            return null;
        }
        String value = raw.trim();
        int slash = value.indexOf('/');
        if (slash <= 0 || slash >= value.length() - 1) {
            return null;
        }
        return new ComponentName(value.substring(0, slash), value.substring(slash + 1));
    }

    /**
     * List every installed Android speech-recognition service so a
     * GrapheneOS / Google / vendor recognizer can be chosen explicitly.
     */
    public static String recognitionEnginesJson(Context context) {
        JSONArray out = new JSONArray();
        try {
            JSONObject system = new JSONObject();
            system.put("component", "");
            system.put("label", "System default recognizer");
            system.put("package", "");
            system.put("default", true);
            out.put(system);

            JSONObject whisper = new JSONObject();
            whisper.put("component", ENGINE_WHISPER);
            whisper.put("label", WhisperRecognizer.available(context)
                    ? "Whisper · bundled offline (tiny.en ready)"
                    : "Whisper · bundled offline (download the tiny.en model)");
            whisper.put("package", "org.nuxel.penguru");
            whisper.put("default", usesWhisper(context));
            out.put(whisper);

            PackageManager pm = context.getPackageManager();
            Intent intent = new Intent(RecognitionService.SERVICE_INTERFACE);
            List<ResolveInfo> services = pm.queryIntentServices(intent,
                    PackageManager.MATCH_ALL);
            String selected = engineComponent(context);
            for (ResolveInfo info : services) {
                if (info == null || info.serviceInfo == null) {
                    continue;
                }
                String pkg = info.serviceInfo.packageName;
                String cls = info.serviceInfo.name;
                if (pkg == null || cls == null) {
                    continue;
                }
                String component = pkg + "/" + cls;
                JSONObject entry = new JSONObject();
                entry.put("component", component);
                CharSequence label = info.serviceInfo.applicationInfo == null
                        ? info.loadLabel(pm) : info.serviceInfo.applicationInfo.loadLabel(pm);
                String text = label == null ? pkg : label.toString();
                if (text.trim().isEmpty()) {
                    text = pkg;
                }
                entry.put("label", text + " · " + cls.substring(cls.lastIndexOf('.') + 1));
                entry.put("package", pkg);
                entry.put("default", component.equals(selected));
                out.put(entry);
            }
        } catch (JSONException | RuntimeException error) {
            // Return whatever was discovered.
        }
        return out.toString();
    }

    /**
     * Audio pre-processing availability. Android's NoiseSuppressor is the
     * always-present RNNoise-class path; the downloaded Silero VAD / RNNoise
     * packages are reported separately by the PWA model library.
     */
    public static String audioDiagnosticsJson(Context context) {
        JSONObject out = new JSONObject();
        try {
            out.put("vad", vadEnabled(context) ? "adaptive-rms" : "off");
            out.put("end_silence_ms", endSilenceMs(context));
            out.put("commands", commandsEnabled(context));
            out.put("noise_mode", noiseMode(context));
            out.put("noise_suppressor", NoiseSuppressor.isAvailable());
            out.put("acoustic_echo_canceler", AcousticEchoCanceler.isAvailable());
            out.put("automatic_gain_control", AutomaticGainControl.isAvailable());
            out.put("audio_record_ready", true);
            AudioManager audio = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            out.put("sample_rate", audio == null ? 16000
                    : audio.getProperty(AudioManager.PROPERTY_OUTPUT_SAMPLE_RATE));
            out.put("engine", engineComponent(context));
            out.put("native_silero_installed", DownloadService.isInstalled(context,
                    "model", "silero-vad/silero-vad-onnx"));
            out.put("native_rnnoise_installed", DownloadService.isInstalled(context,
                    "model", "rnnoise/rnnoise-0.2"));
            out.put("whisper_ready", WhisperRecognizer.available(context));
            out.put("whisper_runtime", WhisperRecognizer.runtimePath(context));
            out.put("whisper_model", WhisperRecognizer.modelPath(context));
            out.put("native_whisper_installed", WhisperRecognizer.available(context));
        } catch (JSONException | RuntimeException error) {
            // primitive values only
        }
        return out.toString();
    }

    /**
     * Create pre-processing effects for owners of the direct AudioRecord path
     * (browser fallback / future local decoder). SpeechRecognizer owns its own
     * audio chain, so this is intentionally advisory there.
     */
    public static boolean attachNoiseSuppression(Context context, int audioSession,
                                                 AudioRecord record) {
        if (!"auto".equalsIgnoreCase(noiseMode(context))) {
            return false;
        }
        boolean attached = false;
        try {
            if (NoiseSuppressor.isAvailable()) {
                NoiseSuppressor.create(audioSession).setEnabled(true);
                attached = true;
            }
        } catch (RuntimeException ignored) { }
        try {
            if (AutomaticGainControl.isAvailable()) {
                AutomaticGainControl.create(audioSession).setEnabled(true);
                attached = true;
            }
        } catch (RuntimeException ignored) { }
        try {
            if (AcousticEchoCanceler.isAvailable()) {
                AcousticEchoCanceler.create(audioSession).setEnabled(true);
                attached = true;
            }
        } catch (RuntimeException ignored) { }
        return attached;
    }
}
