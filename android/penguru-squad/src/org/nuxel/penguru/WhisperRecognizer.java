package org.nuxel.penguru;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.SystemClock;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Local speech recognition through the bundled whisper.cpp CLI.
 *
 * Android's SpeechRecognizer is still the preferred foreground path because it
 * is usually faster and uses the phone's tuned language model. Several builds
 * (notably de-Googled phones) ship no recognition service at all; this class is
 * the fallback that makes the microphone useful there. It records 16 kHz mono
 * PCM with AudioRecord, performs lightweight RMS endpointing, and runs the
 * bundled whisper-cli against the downloaded ggml-tiny.en.bin model.
 *
 * The binary is shipped as libwhisper-cli.so so Android extracts it into the
 * read-only native library directory. Executing binaries from writable app
 * data is blocked on Android 10+, but the extracted native library directory
 * is executable. No audio leaves the phone.
 */
final class WhisperRecognizer {
    private static final String TAG = "PenGuruWhisper";
    static final String MODEL_FILE = "ggml-tiny.en.bin";
    static final String MODEL_ID = "sonarbird/speech-whisper-tiny-en";
    private static final String[] MODEL_IDS = {
            MODEL_ID,
            "whisper/whisper-tiny-en",
            "whisper.cpp/whisper-tiny-en",
    };
    private static final int SAMPLE_RATE = 16000;
    private static final int BYTES_PER_SAMPLE = 2;
    private static final long MAX_CAPTURE_MS = 120000L;

    interface Callback {
        /** text is the transcript; error is null for success. */
        void onResult(String text, String error);
    }

    private final Context context;
    private final AtomicBoolean stopRequested = new AtomicBoolean(false);
    private final AtomicBoolean cancelled = new AtomicBoolean(false);
    private volatile Thread captureThread;
    private volatile Process process;
    private volatile AudioRecord recorder;

    WhisperRecognizer(Context context) {
        this.context = context.getApplicationContext();
    }

    static File runtimeFile(Context context) {
        try {
            File nativeDir = new File(context.getApplicationInfo().nativeLibraryDir);
            File cli = new File(nativeDir, "libwhisper-cli.so");
            if (cli.isFile() && cli.canExecute()) {
                return cli;
            }
            // Some package manager configurations report canExecute false
            // even though the extracted library is runnable. Fall back to the
            // path anyway; the process start result is the real test.
            return cli.isFile() ? cli : null;
        } catch (RuntimeException error) {
            return null;
        }
    }

    static File modelFile(Context context) {
        for (String id : MODEL_IDS) {
            try {
                File dir = PenGuruStorage.targetDir(context, "model", id);
                File model = new File(dir, MODEL_FILE);
                if (model.isFile() && model.length() > 1024L * 1024L) {
                    return model;
                }
            } catch (Exception error) {
                // Try the next alias.
            }
        }
        return null;
    }

    static boolean available(Context context) {
        return runtimeFile(context) != null && modelFile(context) != null;
    }

    static String runtimePath(Context context) {
        File file = runtimeFile(context);
        return file == null ? "" : file.getAbsolutePath();
    }

    static String modelPath(Context context) {
        File file = modelFile(context);
        return file == null ? "" : file.getAbsolutePath();
    }

    static String statusJson(Context context) {
        File runtime = runtimeFile(context);
        File model = modelFile(context);
        return "{\"runtime\":" + quote(runtime == null ? "" : runtime.getAbsolutePath())
                + ",\"model\":" + quote(model == null ? "" : model.getAbsolutePath())
                + ",\"ready\":" + (runtime != null && model != null) + "}";
    }

    private static String quote(String value) {
        if (value == null) {
            return "\"\"";
        }
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '"' || c == '\\') {
                out.append('\\');
            }
            out.append(c);
        }
        return out.append('"').toString();
    }

    /**
     * Start one bounded capture. Returns null when capture started, otherwise
     * a short error code the UI can translate.
     */
    String start(final String mode, final int endSilenceMs, final long recordMs,
                 final long maxMs, final Callback callback) {
        File runtime = runtimeFile(context);
        if (runtime == null) {
            return "whisper_runtime_missing";
        }
        final File model = modelFile(context);
        if (model == null) {
            return "whisper_model_missing";
        }
        cancel();
        stopRequested.set(false);
        cancelled.set(false);
        final String captureMode = mode == null ? "toggle" : mode;
        final long silence = Math.max(0L, endSilenceMs);
        final long fixedMs = recordMs > 0L ? Math.min(recordMs, MAX_CAPTURE_MS) : 0L;
        final long deadline = Math.max(2000L, Math.min(maxMs, MAX_CAPTURE_MS));
        Thread thread = new Thread(() -> capture(runtime, model, captureMode, silence,
                fixedMs, deadline, callback), "penguru-whisper");
        thread.setDaemon(true);
        captureThread = thread;
        thread.start();
        return null;
    }

    /** Owner tapped the mic a second time: transcribe what was captured. */
    void finish() {
        stopRequested.set(true);
    }

    /** Discard the session without producing a transcript. */
    void cancel() {
        cancelled.set(true);
        stopRequested.set(true);
        AudioRecord active = recorder;
        if (active != null) {
            try {
                active.stop();
            } catch (RuntimeException ignored) {
                // already stopped
            }
        }
        Thread thread = captureThread;
        if (thread != null && thread != Thread.currentThread()) {
            try {
                thread.join(400L);
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            }
        }
        Process running = process;
        if (running != null) {
            try {
                running.destroy();
            } catch (RuntimeException ignored) {
                // already exited
            }
        }
    }

    private void capture(File runtime, File model, String mode, long endSilenceMs,
                         long fixedMs, long deadlineMs, Callback callback) {
        int minBuffer = AudioRecord.getMinBufferSize(SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        if (minBuffer <= 0) {
            callback.onResult("", "whisper_audio_unavailable");
            return;
        }
        int bufferBytes = Math.max(minBuffer, SAMPLE_RATE / 5 * BYTES_PER_SAMPLE);
        AudioRecord record = null;
        ByteArrayOutputStream pcm = new ByteArrayOutputStream(SAMPLE_RATE * BYTES_PER_SAMPLE * 8);
        try {
            AudioFormat format = new AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                    .build();
            record = new AudioRecord.Builder()
                    .setAudioSource(MediaRecorder.AudioSource.VOICE_RECOGNITION)
                    .setAudioFormat(format)
                    .setBufferSizeInBytes(bufferBytes * 2)
                    .build();
            recorder = record;
            if (record.getState() != AudioRecord.STATE_INITIALIZED) {
                callback.onResult("", "whisper_audio_unavailable");
                return;
            }
            record.startRecording();
            Log.i(TAG, "whisper capture started mode=" + mode + " silence=" + endSilenceMs
                    + " fixed=" + fixedMs + " deadline=" + deadlineMs);
            byte[] chunk = new byte[Math.max(1600, bufferBytes / 2)];
            long startedAt = SystemClock.elapsedRealtime();
            long lastVoiceAt = startedAt;
            long speechStartedAt = 0L;
            double noiseFloorDb = -58.0;
            int voicedChunks = 0;
            boolean speechStarted = false;

            while (!cancelled.get()) {
                int read = record.read(chunk, 0, chunk.length);
                if (read <= 0) {
                    if (read == AudioRecord.ERROR_INVALID_OPERATION
                            || read == AudioRecord.ERROR_BAD_VALUE
                            || read == AudioRecord.ERROR_DEAD_OBJECT) {
                        break;
                    }
                    continue;
                }
                pcm.write(chunk, 0, read);
                long now = SystemClock.elapsedRealtime();
                double level = rmsDb(chunk, read);
                if (!speechStarted) {
                    if (level < noiseFloorDb) {
                        noiseFloorDb = noiseFloorDb * 0.85 + level * 0.15;
                    } else if (level < noiseFloorDb + 3.0) {
                        noiseFloorDb = noiseFloorDb * 0.98 + level * 0.02;
                    }
                    if (level >= Math.max(-45.0, noiseFloorDb + 7.0)) {
                        voicedChunks++;
                        if (voicedChunks >= 2) {
                            speechStarted = true;
                            speechStartedAt = now - (voicedChunks * 100L);
                            lastVoiceAt = now;
                        }
                    } else {
                        voicedChunks = 0;
                    }
                } else {
                    if (level >= Math.max(-47.0, noiseFloorDb + 4.0)) {
                        lastVoiceAt = now;
                    }
                }

                if (fixedMs > 0L && now - startedAt >= fixedMs) {
                    break;
                }
                if (deadlineMs > 0L && now - startedAt >= deadlineMs) {
                    break;
                }
                if (stopRequested.get()) {
                    break;
                }
                boolean autoEndpoint = "vad".equals(mode) || "wake".equals(mode)
                        || "followup".equals(mode);
                if (autoEndpoint && speechStarted && endSilenceMs > 0L
                        && now - lastVoiceAt >= endSilenceMs
                        && now - speechStartedAt >= 180L) {
                    break;
                }
            }
            if (!cancelled.get()) {
                Log.i(TAG, "whisper capture stopped bytes=" + pcm.size()
                        + " speech=" + speechStarted);
                if (pcm.size() < SAMPLE_RATE * BYTES_PER_SAMPLE / 2) {
                    callback.onResult("", "no_speech_detected");
                    return;
                }
                if (!speechStarted && "fixed".equals(mode) == false
                        && "toggle".equals(mode) == false) {
                    // Auto-endpoint modes only send after actual voice energy.
                    callback.onResult("", "no_speech_detected");
                    return;
                }
                transcribe(runtime, model, pcm.toByteArray(), callback);
            }
        } catch (SecurityException error) {
            callback.onResult("", "microphone_permission_denied");
        } catch (Exception error) {
            Log.w(TAG, "Whisper capture failed", error);
            if (!cancelled.get()) {
                callback.onResult("", "whisper_capture_failed");
            }
        } finally {
            recorder = null;
            if (record != null) {
                try {
                    record.stop();
                } catch (RuntimeException ignored) {
                    // not recording
                }
                try {
                    record.release();
                } catch (RuntimeException ignored) {
                    // already released
                }
            }
            captureThread = null;
        }
    }

    private void transcribe(File runtime, File model, byte[] pcm, Callback callback) {
        File wav = null;
        File outBase = null;
        File log = null;
        try {
            File dir = new File(context.getCacheDir(), "whisper");
            if (!dir.exists() && !dir.mkdirs()) {
                callback.onResult("", "whisper_storage_failed");
                return;
            }
            String base = "speech-" + System.currentTimeMillis();
            wav = new File(dir, base + ".wav");
            outBase = new File(dir, base);
            log = new File(dir, base + ".log");
            writeWav(wav, pcm);

            List<String> command = new ArrayList<>();
            command.add(runtime.getAbsolutePath());
            command.add("-m");
            command.add(model.getAbsolutePath());
            command.add("-f");
            command.add(wav.getAbsolutePath());
            command.add("-l");
            command.add("en");
            command.add("-t");
            command.add("2");
            command.add("-nt");
            command.add("-otxt");
            command.add("-of");
            command.add(outBase.getAbsolutePath());
            command.add("--no-gpu");
            command.add("--prompt");
            command.add("Penguru is the name of this assistant.");

            ProcessBuilder builder = new ProcessBuilder(command);
            builder.redirectErrorStream(true);
            builder.redirectOutput(log);
            Process running = builder.start();
            process = running;
            Log.i(TAG, "whisper transcribing pcm=" + pcm.length + " bytes");
            boolean completed = running.waitFor(90L, TimeUnit.SECONDS);
            if (!completed) {
                running.destroyForcibly();
                if (!cancelled.get()) {
                    callback.onResult("", "whisper_timeout");
                }
                return;
            }
            if (cancelled.get()) {
                return;
            }
            File transcript = new File(outBase.getAbsolutePath() + ".txt");
            String text = transcript.isFile()
                    ? new String(Files.readAllBytes(transcript.toPath()), StandardCharsets.UTF_8)
                    : "";
            text = cleanTranscript(text);
            if (text.isEmpty()) {
                String detail = readLog(log);
                Log.w(TAG, "Whisper produced no transcript"
                        + (detail.isEmpty() ? "" : ": " + detail));
                callback.onResult("", "no_speech_detected");
                return;
            }
            Log.i(TAG, "whisper transcript chars=" + text.length());
            callback.onResult(text, null);
        } catch (Exception error) {
            Log.w(TAG, "Whisper transcription failed", error);
            if (!cancelled.get()) {
                callback.onResult("", "whisper_failed");
            }
        } finally {
            process = null;
            deleteQuietly(wav);
            deleteQuietly(log);
            if (outBase != null) {
                deleteQuietly(new File(outBase.getAbsolutePath() + ".txt"));
                deleteQuietly(new File(outBase.getAbsolutePath() + ".srt"));
                deleteQuietly(new File(outBase.getAbsolutePath() + ".vtt"));
                deleteQuietly(new File(outBase.getAbsolutePath() + ".json"));
            }
        }
    }

    private static void writeWav(File file, byte[] pcm) throws IOException {
        int dataLength = pcm.length;
        try (FileOutputStream out = new FileOutputStream(file)) {
            byte[] header = new byte[44];
            putAscii(header, 0, "RIFF");
            putInt(header, 4, dataLength + 36);
            putAscii(header, 8, "WAVE");
            putAscii(header, 12, "fmt ");
            putInt(header, 16, 16);
            putShort(header, 20, 1);
            putShort(header, 22, 1);
            putInt(header, 24, SAMPLE_RATE);
            putInt(header, 28, SAMPLE_RATE * BYTES_PER_SAMPLE);
            putShort(header, 32, BYTES_PER_SAMPLE);
            putShort(header, 34, 16);
            putAscii(header, 36, "data");
            putInt(header, 40, dataLength);
            out.write(header);
            out.write(pcm);
        }
    }

    private static void putAscii(byte[] buffer, int at, String value) {
        for (int i = 0; i < value.length(); i++) {
            buffer[at + i] = (byte) value.charAt(i);
        }
    }

    private static void putShort(byte[] buffer, int at, int value) {
        buffer[at] = (byte) (value & 0xff);
        buffer[at + 1] = (byte) ((value >> 8) & 0xff);
    }

    private static void putInt(byte[] buffer, int at, int value) {
        buffer[at] = (byte) (value & 0xff);
        buffer[at + 1] = (byte) ((value >> 8) & 0xff);
        buffer[at + 2] = (byte) ((value >> 16) & 0xff);
        buffer[at + 3] = (byte) ((value >> 24) & 0xff);
    }

    private static double rmsDb(byte[] pcm, int length) {
        long sum = 0L;
        int samples = Math.max(1, length / 2);
        for (int i = 0; i + 1 < length; i += 2) {
            int sample = (short) ((pcm[i] & 0xff) | (pcm[i + 1] << 8));
            sum += (long) sample * sample;
        }
        double rms = Math.sqrt((double) sum / samples);
        return 20.0 * Math.log10(Math.max(1.0, rms) / 32768.0);
    }

    private static String cleanTranscript(String raw) {
        if (raw == null) {
            return "";
        }
        String text = raw.replace("\r", "\n");
        text = text.replaceAll("\\[(?:BLANK_AUDIO|silence|Silence|MUSIC|music)\\]", " ");
        text = text.replaceAll("\\((?:silence|Silence)\\)", " ");
        text = text.replaceAll("\\s+", " ").trim();
        if (text.toLowerCase(Locale.ROOT).matches("^(you|thank you|thanks|bye|okay|ok)\\.?$")) {
            // Whisper tiny sometimes emits these on silence. They are safe to
            // drop because the owner can simply speak again.
            return "";
        }
        return text;
    }

    private static String readLog(File file) {
        try {
            if (file == null || !file.isFile() || file.length() > 32768L) {
                return "";
            }
            String text = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8)
                    .replaceAll("\\s+", " ").trim();
            return text.length() > 400 ? text.substring(text.length() - 400) : text;
        } catch (Exception error) {
            return "";
        }
    }

    private static void deleteQuietly(File file) {
        try {
            if (file != null && file.exists()) {
                //noinspection ResultOfMethodCallIgnored
                file.delete();
            }
        } catch (RuntimeException ignored) {
            // best-effort temporary cleanup
        }
    }
}
