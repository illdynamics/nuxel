package org.nuxel.penguru;

import android.os.SystemClock;

/**
 * Adaptive end-of-speech detector for Android's SpeechRecognizer.
 *
 * SpeechRecognizer does not expose audio frames, but it does stream
 * onRmsChanged() levels. Those levels are enough to tell the difference between
 * room noise and an owner who has actually started and stopped talking. This
 * detector learns the local noise floor, arms only after real voice energy and
 * then fires once the owner has been quiet for a configurable window.
 *
 * It is deliberately lightweight: no model download, no JNI and no wake-lock.
 * It is used together with onEndOfSpeech(), which remains the authoritative
 * signal when the phone's recognizer provides it. Silero VAD / RNNoise model
 * packages can still be downloaded from the Model library; this class is the
 * always-available fallback that makes push-to-talk and "Penguru" follow-up
 * listening end as soon as the owner stops speaking instead of waiting for a
 * fixed 2.5-second recognizer timeout.
 */
public final class VoiceActivityDetector {
    private static final float SPEECH_MARGIN_DB = 5.0f;
    private static final float QUIET_MARGIN_DB = 2.4f;
    private static final long MIN_SPEECH_MS = 160L;

    private final long endSilenceMs;
    private final long maxSpeechMs;
    private float noiseFloorDb = 0f;
    private boolean initialized;
    private boolean speechStarted;
    private boolean fired;
    private boolean sawEndOfSpeech;
    private long speechStartAt;
    private long lastVoiceAt;
    private int loudFrames;
    private long lastRmsAt;

    public VoiceActivityDetector(long endSilenceMs, long maxSpeechMs) {
        this.endSilenceMs = Math.max(0L, endSilenceMs);
        this.maxSpeechMs = Math.max(1000L, maxSpeechMs);
    }

    public void reset() {
        noiseFloorDb = 0f;
        initialized = false;
        speechStarted = false;
        fired = false;
        sawEndOfSpeech = false;
        speechStartAt = 0L;
        lastVoiceAt = 0L;
        loudFrames = 0;
        lastRmsAt = 0L;
    }

    /**
     * Feed one onRmsChanged() value. Returns true exactly once, at the moment
     * the owner has stopped talking (or the maximum utterance expired).
     */
    public boolean update(float rmsDb) {
        long now = SystemClock.elapsedRealtime();
        lastRmsAt = now;
        if (Float.isNaN(rmsDb) || Float.isInfinite(rmsDb)) {
            return false;
        }
        // onRmsChanged is documented around -2..10 dB, but vendor services
        // have also shipped dBFS scales (-60..0). Keep the detector relative to
        // the measured room floor so both scales work.
        float level = Math.max(-60f, Math.min(30f, rmsDb));
        if (!initialized) {
            noiseFloorDb = level;
            initialized = true;
            return false;
        }

        if (!speechStarted) {
            float threshold = noiseFloorDb + SPEECH_MARGIN_DB;
            if (level >= threshold) {
                loudFrames++;
                if (loudFrames >= 2) {
                    speechStarted = true;
                    speechStartAt = now;
                    lastVoiceAt = now;
                }
            } else {
                loudFrames = 0;
                // Learn the room. Follow a drop quickly (the first callback may
                // have been speech) and rise only slowly, so a loud sentence
                // cannot permanently raise the threshold above the owner.
                if (level < noiseFloorDb) {
                    noiseFloorDb = noiseFloorDb * 0.75f + level * 0.25f;
                } else if (level <= noiseFloorDb + QUIET_MARGIN_DB) {
                    noiseFloorDb = noiseFloorDb * 0.94f + level * 0.06f;
                }
            }
            return false;
        }

        float quietThreshold = noiseFloorDb + QUIET_MARGIN_DB;
        if (level >= quietThreshold) {
            lastVoiceAt = now;
        }
        if (now - speechStartAt >= maxSpeechMs) {
            return fire();
        }
        if (sawEndOfSpeech) {
            return fire();
        }
        if (endSilenceMs > 0L
                && now - lastVoiceAt >= endSilenceMs
                && now - speechStartAt >= MIN_SPEECH_MS) {
            return fire();
        }
        return false;
    }

    /**
     * The phone's recognizer reported end-of-speech. Treat it as an immediate
     * endpoint when we have seen actual speech; this is what removes the
     * previous fixed multi-second wait.
     */
    public boolean onEndOfSpeech() {
        if (!speechStarted || fired) {
            return false;
        }
        sawEndOfSpeech = true;
        return fire();
    }

    private boolean fire() {
        if (fired) {
            return false;
        }
        fired = true;
        return true;
    }

    public boolean hasSpeech() {
        return speechStarted;
    }

    public boolean fired() {
        return fired;
    }

    public long silenceMs() {
        if (!speechStarted) {
            return 0L;
        }
        long at = lastRmsAt == 0L ? SystemClock.elapsedRealtime() : lastRmsAt;
        return Math.max(0L, at - lastVoiceAt);
    }
}
