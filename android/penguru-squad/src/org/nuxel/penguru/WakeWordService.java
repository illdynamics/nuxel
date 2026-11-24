package org.nuxel.penguru;

import android.Manifest;
import android.media.MediaRecorder;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.Log;

import java.util.ArrayList;
import java.util.Locale;

import org.json.JSONObject;

/**
 * Persistent "SonarBird" wake-word listener.
 *
 * A microphone foreground service keeps Android's speech recognizer running
 * while PenGuru is in the background. Each recognition session is short; the
 * service restarts it after a result, an error or a watchdog deadline so the
 * microphone is never held forever by a silently stuck recognizer.
 *
 * Saying "Penguru" alone arms the next utterance; saying "Penguru <question>"
 * sends the question immediately. The command is handed to MainActivity and
 * auto-sent by the PWA. If Android blocks the background activity launch, the
 * ongoing notification still carries the command so tapping it delivers it.
 */
public class WakeWordService extends Service {
    private static final String TAG = "PenGuruWake";

    public static final String ACTION_START = "org.nuxel.penguru.action.WAKE_START";
    public static final String ACTION_STOP = "org.nuxel.penguru.action.WAKE_STOP";
    public static final String ACTION_FINISH = "org.nuxel.penguru.action.WAKE_FINISH";
    public static final String EXTRA_COMMAND = "penguru_command";
    public static final String EXTRA_MODE = "penguru_mode";

    static final String PREFS = "penguru_wake";
    static final String PREF_ENABLED = "enabled";
    private static final String PREF_PENDING = "pending_command";
    private static final String PREF_PENDING_MODE = "pending_mode";
    private static final String PREF_PENDING_AT = "pending_command_at";

    private static final String CHANNEL_ID = "penguru_listening";
    private static final int NOTIFICATION_ID = 8801;
    private static final long SESSION_DEADLINE_MS = 12000L;
    private static final long COMMAND_FOLLOW_UP_MS = 20000L;
    private static final long MIN_SESSION_GAP_MS = 1000L;
    private static volatile WakeWordService instance;
    private static volatile boolean running;
    private static volatile boolean paused;
    // True while MainActivity is visible (reported in status). Visibility does
    // not pause the listener; only an active in-app microphone session does.
    private static volatile boolean appForeground;
    // True only while MainActivity owns the microphone for an in-app speech
    // session. The listener keeps running while the app is merely visible.
    private static volatile boolean inAppSpeech;
    private static volatile long inAppSpeechAt;

    private final Handler handler = new Handler(Looper.getMainLooper());
    // Hand-off callbacks deliberately do not use `handler`: onStartCommand
    // clears that queue, and losing the "recognizer released" callback would
    // leave the in-app microphone waiting forever.
    private static final Handler HANDOFF = new Handler(Looper.getMainLooper());
    /**
     * Last-resort health check for a listener that somehow ended up running,
     * unpaused and not listening. Without it a missed callback could leave
     * SonarBird silently deaf until the app was reopened.
     */
    private final Runnable healthCheck = new Runnable() {
        @Override
        public void run() {
            if (destroyed) {
                return;
            }
            if (running && !paused && !inAppSpeech && !speaking
                    && !listening && !restartQueued) {
                lastError = "Listener watchdog restarted recognition";
                beginListening();
            }
            handler.postDelayed(this, 15000L);
        }
    };
    private SpeechRecognizer recognizer;
    private PowerManager.WakeLock wakeLock;
    private boolean listening;
    private boolean awaitingCommand;
    private boolean restartQueued;
    private boolean destroyed;
    private long awaitingSince;
    private long lastDispatchAt;
    private long lastSessionAt;
    private String lastDispatch = "";
    private String speechLanguage = "";
    private String lastError = "";
    private boolean stayingQuiet;
    private boolean stoppingForHandoff;
    private String lastHeard = "";
    private String lastPartial = "";
    private boolean dispatchedThisSession;
    private Runnable pendingPartialDispatch;
    private int consecutiveErrors;
    private int session;
    // If Android's recognizer is absent or repeatedly fails, the bundled
    // whisper.cpp engine can keep the wake listener alive offline.
    private WhisperRecognizer whisperRecognizer;
    private boolean whisperListening;
    private boolean forceWhisper;
    // Adaptive endpointing and command capture for the persistent listener.
    private VoiceActivityDetector vad;
    private String commandBuffer = "";
    private String capturedMode = "";
    private long commandBufferAt;
    private boolean voiceStopRequested;
    // Reply talkback lives in this foreground service, not the Activity, so an
    // answer is spoken even when PenGuru is not on screen. Recognition is
    // stopped while the engine talks and re-armed afterwards so the owner can
    // answer without repeating the wake word.
    private TalkbackEngine talkback;
    private boolean speaking;

    public static boolean isRunning() {
        return running;
    }

    public static boolean isPaused() {
        return paused;
    }

    public static boolean isAppForeground() {
        return appForeground;
    }

    public static boolean isInAppSpeech() {
        return inAppSpeech;
    }

    /**
     * Track whether MainActivity is visible. Visibility alone no longer pauses
     * SonarBird: the listener stays armed while the app is open and is paused
     * only for the short in-app recognition session. The previous behaviour
     * made "background listening" look completely dead whenever the owner was
     * looking at the app.
     */
    public static void setAppForeground(boolean visible) {
        appForeground = visible;
        WakeWordService service = instance;
        if (visible) {
            // Recover a hand-off that was left behind when Android killed the
            // Activity mid-dictation. A real in-app session still holds the
            // microphone; the 120 s guard only clears a stale pause.
            if (service != null && inAppSpeech
                    && System.currentTimeMillis() - inAppSpeechAt > 120000L) {
                inAppSpeech = false;
                paused = false;
                service.handler.postDelayed(service::beginListening, 250L);
            }
            return;
        }
        if (service != null && !paused && !inAppSpeech) {
            service.scheduleNext(650L);
        }
    }

    /** Wait until the service has released the recognizer and microphone. */
    public static void pauseForActivity(Runnable whenPaused) {
        paused = true;
        inAppSpeech = true;
        inAppSpeechAt = System.currentTimeMillis();
        WakeWordService service = instance;
        if (service == null) {
            if (whenPaused != null) {
                whenPaused.run();
            }
            return;
        }
        HANDOFF.post(() -> {
            service.stopRecognizer();
            service.listening = false;
            service.lastError = "";
            service.updateNotification("Paused while the in-app microphone is in use");
            if (whenPaused != null) {
                // Give Android's speech service a moment to tear down its
                // binder before the Activity creates a new recognizer.
                HANDOFF.postDelayed(whenPaused, 120L);
            }
        });
    }

    /** Kept for callers that do not need a release callback. */
    public static void pauseForActivity() {
        pauseForActivity(null);
    }

    /**
     * Called after an in-app result or when MainActivity leaves the screen.
     * SonarBird resumes even while the app is visible; the next in-app mic
     * session pauses it again before creating its recognizer.
     */
    public static void resumeFromActivity() {
        inAppSpeech = false;
        paused = false;
        WakeWordService service = instance;
        if (service != null && !destroyedStatic()) {
            service.handler.postDelayed(service::beginListening, 700L);
        }
    }

    private static boolean destroyedStatic() {
        WakeWordService service = instance;
        return service == null || service.destroyed;
    }

    /**
     * Speak an assistant answer from the persistent listener. MainActivity
     * routes every talkback request here while SonarBird is running, so the
     * answer is voiced even when the Activity is stopped, invisible, or was
     * never brought to the foreground after a wake-word launch.
     */
    public static boolean speakReply(Context context, String text) {
        WakeWordService service = instance;
        if (service == null || !running || service.destroyed) {
            return false;
        }
        final String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return false;
        }
        service.handler.post(() -> service.speakReplyOnMain(value));
        return true;
    }

    public static void stopSpeaking() {
        WakeWordService service = instance;
        if (service != null && !service.destroyed) {
            service.handler.post(service::stopSpeakingOnMain);
        }
    }

    public static String talkbackStatusJson() {
        WakeWordService service = instance;
        return service == null || service.destroyed || service.talkback == null
                ? null : service.talkback.statusJson();
    }

    public static String talkbackEnginesJson() {
        WakeWordService service = instance;
        return service == null || service.destroyed || service.talkback == null
                ? null : service.talkback.enginesJson();
    }

    public static boolean configureTalkback(String optionsJson) {
        WakeWordService service = instance;
        if (service == null || service.destroyed || service.talkback == null) {
            return false;
        }
        return service.talkback.configure(optionsJson);
    }

    public static boolean isSpeaking() {
        WakeWordService service = instance;
        return service != null && service.speaking;
    }

    public static String statusJson(Context context) {
        JSONObject out = new JSONObject();
        try {
            WakeWordService service = instance;
            out.put("running", running);
            out.put("paused", paused);
            out.put("listening", service != null && service.listening);
            out.put("enabled", context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .getBoolean(PREF_ENABLED, false));
            out.put("microphone", context.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED);
            boolean notifications = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                    || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    == PackageManager.PERMISSION_GRANTED;
            out.put("notifications", notifications);
            out.put("awaiting_command", service != null && service.awaitingCommand);
            out.put("handoff", service != null && service.stoppingForHandoff);
            out.put("in_app_speech", inAppSpeech);
            out.put("speaking", service != null && service.speaking);
            out.put("talkback_ready", service != null && service.talkback != null
                    && service.talkback.isReady());
            out.put("last_error", service == null || service.stayingQuiet ? "" : service.lastError);
            out.put("last_heard", service == null ? "" : service.lastHeard);
            out.put("last_partial", service == null ? "" : service.commandBuffer);
            out.put("command_pending", service != null && (!service.commandBuffer.isEmpty()
                    || !service.capturedMode.isEmpty()));
            out.put("pending_mode", service == null ? "" : service.capturedMode);
            out.put("vad", service != null && service.vad != null ? "adaptive-rms" : "idle");
            out.put("engine", VoiceSettings.engineComponent(context));
            out.put("whisper_listening", service != null && service.whisperListening);
            out.put("whisper_fallback", service != null && service.forceWhisper);
            out.put("sessions", service == null ? 0 : service.session);
        } catch (Exception error) {
            // JSONObject only receives primitive values.
        }
        return out.toString();
    }

    public static void clearPendingCommand(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .remove(PREF_PENDING)
                .remove(PREF_PENDING_MODE)
                .remove(PREF_PENDING_AT)
                .apply();
    }

    public static PendingCommand takePendingCommand(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String text = prefs.getString(PREF_PENDING, "");
        String mode = prefs.getString(PREF_PENDING_MODE, "");
        long at = prefs.getLong(PREF_PENDING_AT, 0);
        clearPendingCommand(context);
        if (System.currentTimeMillis() - at > 120000L) {
            return new PendingCommand("", "");
        }
        return new PendingCommand(text == null ? "" : text.trim(),
                VoiceCommandRouter.isMode(mode) ? mode : "");
    }

    /** A wake-word hand-off can carry only a mode ("Penguru chat"), only a
     *  message, or a mode plus the request that follows it. */
    public static final class PendingCommand {
        public final String text;
        public final String mode;

        PendingCommand(String text, String mode) {
            this.text = text == null ? "" : text.trim();
            this.mode = VoiceCommandRouter.isMode(mode) ? mode : "";
        }

        public boolean isEmpty() {
            return text.isEmpty() && mode.isEmpty();
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        running = true;
        destroyed = false;
        talkback = new TalkbackEngine(this, this::onTalkbackState);
        createChannel();
        acquireWakeLock();
        handler.postDelayed(healthCheck, 15000L);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putBoolean(PREF_ENABLED, false)
                    .apply();
            shutdown();
            stopSelf();
            return START_NOT_STICKY;
        }
        if (intent != null && ACTION_FINISH.equals(intent.getAction())) {
            finishFromNotification();
            return START_STICKY;
        }

        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putBoolean(PREF_ENABLED, true)
                .apply();
        // Give the phone's own recognizer a fresh chance whenever the owner
        // (re)starts listening from the UI; repeated hard failures will select
        // the offline Whisper fallback again automatically.
        forceWhisper = false;
        // A START command must not steal the microphone back while the
        // Activity is recording. This happened when launch-time permission
        // checks restarted an enabled listener after the in-app mic began.
        paused = inAppSpeech;
        if (!startInForeground(inAppSpeech
                ? "Paused while the in-app microphone is in use"
                : "Listening for “Penguru” · say it, then your message")) {
            lastError = "Android refused to start the microphone foreground service. Open PenGuru while the screen is on and start listening again.";
            stopSelf();
            return START_NOT_STICKY;
        }
        restartQueued = false;
        handler.removeCallbacksAndMessages(null);
        handler.postDelayed(healthCheck, 15000L);
        if (inAppSpeech) {
            // A queued stop/handoff may have been cleared above; make sure no
            // recognizer survives while the Activity owns the microphone.
            stopRecognizer();
            listening = false;
        } else {
            handler.postDelayed(this::beginListening, 350L);
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        destroyed = true;
        running = false;
        instance = null;
        speaking = false;
        stopRecognizer();
        if (talkback != null) {
            talkback.shutdown();
            talkback = null;
        }
        handler.removeCallbacksAndMessages(null);
        releaseWakeLock();
        stopForeground(true);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "SonarBird listening",
                NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Shows when PenGuru is listening for “Penguru” in the background.");
        channel.setShowBadge(false);
        channel.setSound(null, null);
        manager.createNotificationChannel(channel);
    }

    private void acquireWakeLock() {
        try {
            PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
            if (power == null) {
                return;
            }
            wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PenGuru:SonarBird");
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire();
        } catch (RuntimeException error) {
            wakeLock = null;
        }
    }

    private void releaseWakeLock() {
        if (wakeLock != null) {
            try {
                if (wakeLock.isHeld()) {
                    wakeLock.release();
                }
            } catch (RuntimeException ignored) {
                // already released
            }
            wakeLock = null;
        }
    }

    private boolean startInForeground(String text) {
        Notification notification = buildNotification(text);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
            return true;
        } catch (RuntimeException error) {
            // Android 14+ refuses a microphone foreground service that was
            // started while the app was not in a while-in-use state.
            Log.w(TAG, "startForeground failed: " + error);
            return false;
        }
    }

    private Notification buildNotification(String text) {
        Intent open = new Intent(this, MainActivity.class);
        open.setAction(Intent.ACTION_VIEW);
        open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                | Intent.FLAG_ACTIVITY_SINGLE_TOP
                | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String pending = prefs.getString(PREF_PENDING, "");
        String pendingMode = prefs.getString(PREF_PENDING_MODE, "");
        if (pending != null && !pending.isEmpty()) {
            open.putExtra(EXTRA_COMMAND, pending);
        }
        if (pendingMode != null && VoiceCommandRouter.isMode(pendingMode)) {
            open.putExtra(EXTRA_MODE, pendingMode);
        }
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent content = PendingIntent.getActivity(this, 8802, open, flags);
        PendingIntent stop = PendingIntent.getService(this, 8803,
                new Intent(this, WakeWordService.class).setAction(ACTION_STOP), flags);
        PendingIntent finish = PendingIntent.getService(this, 8804,
                new Intent(this, WakeWordService.class).setAction(ACTION_FINISH), flags);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        String title = inAppSpeech
                ? "SonarBird paused"
                : speaking ? "PenGuru is speaking"
                : paused || stoppingForHandoff ? "PenGuru request ready"
                : "SonarBird is listening";
        builder.setContentTitle(title)
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_stat_penguru)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setContentIntent(content)
                .setCategory(Notification.CATEGORY_SERVICE)
                .addAction(0, "Send now", finish)
                .addAction(0, "Stop listening", stop);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.setColor(0xFF0B1422);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
        }
        return builder.build();
    }

    private void updateNotification(String text) {
        if (destroyed) {
            return;
        }
        try {
            NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (manager != null) {
                manager.notify(NOTIFICATION_ID, buildNotification(text));
            }
        } catch (RuntimeException error) {
            Log.w(TAG, "Could not update notification: " + error);
        }
    }

    /* ------------------------------------------------------------ talkback */

    /**
     * Speak a completed answer while the listener owns the microphone. The
     * recognizer is torn down first so PenGuru does not hear its own voice,
     * then a short follow-up window is opened when the utterance finishes.
     */
    private void speakReplyOnMain(String text) {
        if (destroyed || talkback == null) {
            return;
        }
        final String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return;
        }
        // A new answer supersedes any sentence still being captured.
        speaking = true;
        restartQueued = false;
        awaitingCommand = false;
        commandBuffer = "";
        capturedMode = "";
        lastPartial = "";
        cancelPendingPartial();
        stopRecognizer();
        listening = false;
        updateNotification("Speaking the answer · listening resumes after");
        // Give Android a moment to release the microphone before the voice
        // engine starts, otherwise the first syllable can be captured by the
        // recognizer and trigger a spurious wake command.
        handler.postDelayed(() -> {
            if (destroyed || !speaking) {
                return;
            }
            if (!talkback.speak(value)) {
                lastError = "Talkback is unavailable on this phone";
                speaking = false;
                if (!paused && !inAppSpeech) {
                    awaitingCommand = true;
                    awaitingSince = System.currentTimeMillis();
                    updateNotification("Talkback unavailable · microphone open");
                    scheduleNext(400L);
                }
            }
        }, 260L);
    }

    private void onTalkbackState(String state) {
        if (destroyed) {
            return;
        }
        if ("speaking".equals(state)) {
            speaking = true;
            updateNotification("Speaking the answer · listening resumes after");
            return;
        }
        if ("idle".equals(state) || "error".equals(state)
                || "unavailable".equals(state)) {
            finishSpeaking();
        }
    }

    private void finishSpeaking() {
        if (!speaking) {
            return;
        }
        speaking = false;
        if (destroyed) {
            return;
        }
        if (voiceStopRequested) {
            updateNotification("Stopped listening by voice command");
            return;
        }
        if (paused || inAppSpeech) {
            updateNotification(inAppSpeech
                    ? "Paused while the in-app microphone is in use"
                    : "Listening paused");
            return;
        }
        // Interactive follow-up: the owner can answer the spoken reply without
        // saying "Penguru" again. The next wake word still resets this window.
        awaitingCommand = true;
        awaitingSince = System.currentTimeMillis();
        capturedMode = "";
        commandBuffer = "";
        lastPartial = "";
        updateNotification("Listening for your reply · say anything, or “Penguru stop”");
        scheduleNext(450L);
    }

    private void stopSpeakingOnMain() {
        speaking = false;
        if (talkback != null) {
            talkback.stop();
        }
        if (!destroyed) {
            updateNotification(paused || inAppSpeech
                    ? "Listening paused"
                    : "Listening for “Penguru” · say it, then your message");
            if (!paused && !inAppSpeech) {
                scheduleNext(350L);
            }
        }
    }

    private void beginListening() {
        restartQueued = false;
        stoppingForHandoff = false;
        // If the Activity was killed before it could release the hand-off,
        // never leave the background listener paused forever.
        if (inAppSpeech && System.currentTimeMillis() - inAppSpeechAt > 120000L) {
            inAppSpeech = false;
            paused = false;
        }
        if (destroyed || paused || inAppSpeech || speaking) {
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            lastError = "Microphone permission is missing";
            updateNotification("Microphone permission is missing · open PenGuru");
            scheduleNext(5000L);
            return;
        }
        if (forceWhisper || !SpeechRecognizer.isRecognitionAvailable(this)) {
            if (WhisperRecognizer.available(this)) {
                beginWhisperListening();
                return;
            }
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                lastError = "No Android speech recognition service";
                updateNotification("No Android speech recognition service · open PenGuru");
                scheduleNext(10000L);
                return;
            }
            forceWhisper = false;
        }
        long sinceLast = System.currentTimeMillis() - lastSessionAt;
        if (sinceLast < MIN_SESSION_GAP_MS) {
            scheduleNext(MIN_SESSION_GAP_MS - sinceLast);
            return;
        }
        stopRecognizer();
        final int token = session;
        try {
            ComponentName engine = VoiceSettings.recognizer(this);
            if (engine != null) {
                try {
                    recognizer = SpeechRecognizer.createSpeechRecognizer(this, engine);
                } catch (RuntimeException unavailable) {
                    recognizer = null;
                }
            }
            if (recognizer == null) {
                recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            }
            recognizer.setRecognitionListener(new SessionListener(token));
        } catch (RuntimeException error) {
            recognizer = null;
            lastError = "Speech recognizer unavailable: " + error.getMessage();
            scheduleNext(2500L);
            return;
        }
        listening = true;
        dispatchedThisSession = false;
        lastPartial = "";
        commandBuffer = "";
        if (!awaitingCommand) {
            // A mode chosen by "Penguru chat"/"Penguru code" survives the
            // short follow-up session until the request is actually sent.
            capturedMode = "";
        }
        commandBufferAt = 0L;
        voiceStopRequested = false;
        vad = new VoiceActivityDetector(
                Math.max(450L, Math.min(2500L, VoiceSettings.endSilenceMs(this))), 15000L);
        cancelPendingPartial();
        lastSessionAt = System.currentTimeMillis();
        awaitingCommand = awaitingCommand
                && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
        Intent intent = speechIntent();
        try {
            recognizer.startListening(intent);
            lastError = "";
            stayingQuiet = false;
        } catch (RuntimeException error) {
            listening = false;
            lastError = "Speech start failed: " + error.getMessage();
            stopRecognizer();
            scheduleNext(1800L);
            return;
        }
        handler.postDelayed(() -> {
            if (token != session || destroyed) {
                return;
            }
            lastError = "Session watchdog released the microphone";
            stopRecognizer();
            scheduleNext(500L);
        }, SESSION_DEADLINE_MS);
    }

    private Intent speechIntent() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        // Use partial hypotheses for an immediate "Penguru <question>"
        // hand-off. Waiting for onResults alone made the wake listener look
        // unresponsive on devices that frequently time out after a partial.
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        String language = speechLanguage;
        if (language == null || language.isEmpty()) {
            language = Locale.getDefault().toLanguageTag();
        }
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, language);
        // Background wake listening needs the phone's normal recognizer. Many
        // offline-only recognizers have no language pack installed and then
        // hold the microphone open forever, so do not force offline here.
        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, false);
        // VOICE_RECOGNITION is intended for vendor speech services. On
        // several phones a background recognizer fed from that source returns
        // silence, which made SonarBird look completely deaf. The plain
        // microphone source is the reliable choice here.
        intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE,
                MediaRecorder.AudioSource.MIC);
        // Ask compliant recognizers to finish at our adaptive endpoint. The
        // RMS detector below catches services that ignore these hints.
        long silence = Math.max(450L, Math.min(2500L, VoiceSettings.endSilenceMs(this)));
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, silence);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, silence);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 400L);
        return intent;
    }

    private void cancelPendingPartial() {
        if (pendingPartialDispatch != null) {
            handler.removeCallbacks(pendingPartialDispatch);
            pendingPartialDispatch = null;
        }
    }

    private void schedulePartialDispatch(final String command) {
        cancelPendingPartial();
        pendingPartialDispatch = () -> {
            pendingPartialDispatch = null;
            if (!destroyed && !paused && !inAppSpeech) {
                dispatch(command);
            } else {
                scheduleNext(400L);
            }
        };
        // Give the recognizer a moment to finish the sentence or send a final
        // result before committing a partial hypothesis.
        handler.postDelayed(pendingPartialDispatch, 700L);
    }

    private void stopRecognizer() {
        session++;
        listening = false;
        stopWhisper();
        SpeechRecognizer current = recognizer;
        recognizer = null;
        if (current != null) {
            try {
                current.cancel();
            } catch (RuntimeException ignored) {
                // already cancelled
            }
            try {
                current.destroy();
            } catch (RuntimeException ignored) {
                // already destroyed
            }
        }
    }

    private void stopWhisper() {
        whisperListening = false;
        WhisperRecognizer current = whisperRecognizer;
        whisperRecognizer = null;
        if (current != null) {
            current.cancel();
        }
    }

    /**
     * Offline fallback for phones with no Android recognition service (or one
     * that keeps failing). It records a bounded wake phrase with AudioRecord and
     * transcribes it with the bundled whisper.cpp engine. This is slower than
     * the vendor recognizer but keeps SonarBird functional without Google.
     */
    private void beginWhisperListening() {
        restartQueued = false;
        stoppingForHandoff = false;
        if (destroyed || paused || inAppSpeech || speaking) {
            return;
        }
        if (!WhisperRecognizer.available(this)) {
            forceWhisper = false;
            lastError = "Whisper model is not installed";
            updateNotification("Listening needs Android speech or the Whisper tiny.en model");
            scheduleNext(6000L);
            return;
        }
        long sinceLast = System.currentTimeMillis() - lastSessionAt;
        if (sinceLast < MIN_SESSION_GAP_MS) {
            scheduleNext(MIN_SESSION_GAP_MS - sinceLast);
            return;
        }
        stopRecognizer();
        final int token = session;
        WhisperRecognizer engine = new WhisperRecognizer(this);
        whisperRecognizer = engine;
        whisperListening = true;
        listening = true;
        dispatchedThisSession = false;
        lastPartial = "";
        commandBuffer = "";
        commandBufferAt = 0L;
        voiceStopRequested = false;
        vad = null;
        cancelPendingPartial();
        lastSessionAt = System.currentTimeMillis();
        awaitingCommand = awaitingCommand
                && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
        if (!awaitingCommand) {
            capturedMode = "";
        }
        updateNotification(awaitingCommand
                ? "Listening for your message · offline Whisper"
                : "Listening for “Penguru” · offline Whisper");
        int silence = Math.max(450, Math.min(2500, VoiceSettings.endSilenceMs(this)));
        String error = engine.start("wake", silence, 0L, 16000L,
                new WhisperRecognizer.Callback() {
                    @Override
                    public void onResult(String text, String failure) {
                        handler.post(() -> {
                            if (destroyed || token != session) {
                                return;
                            }
                            whisperListening = false;
                            listening = false;
                            whisperRecognizer = null;
                            if (failure != null) {
                                lastError = failure;
                                updateNotification("Offline listener retrying · " + failure);
                                scheduleNext(1200L);
                                return;
                            }
                            lastError = "";
                            handleText(text == null ? "" : text);
                        });
                    }

                    @Override
                    public void onTranscribing() {
                        handler.post(() -> {
                            if (!destroyed && token == session) {
                                updateNotification("Heard you · transcribing offline…");
                            }
                        });
                    }
                });
        if (error != null) {
            whisperListening = false;
            listening = false;
            whisperRecognizer = null;
            forceWhisper = false;
            lastError = error;
            updateNotification("Offline listener unavailable · " + error);
            scheduleNext(5000L);
        }
    }

    private void scheduleNext(long delayMillis) {
        if (destroyed || paused || inAppSpeech || restartQueued) {
            return;
        }
        restartQueued = true;
        handler.postDelayed(() -> {
            restartQueued = false;
            if (!destroyed && !paused && !inAppSpeech && !speaking) {
                beginListening();
            }
        }, delayMillis);
    }

    private void handleText(String raw) {
        handleText(raw, "");
    }

    private void handleText(String raw, String carriedMode) {
        String text = raw == null ? "" : raw.trim();
        String inheritedMode = VoiceCommandRouter.isMode(carriedMode)
                ? carriedMode
                : (VoiceCommandRouter.isMode(capturedMode) ? capturedMode : "");
        if (text.isEmpty()) {
            // If a wake phrase was already heard, keep the follow-up window
            // open rather than dropping the owner's next sentence.
            if (awaitingCommand
                    && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS) {
                capturedMode = inheritedMode;
                scheduleNext(350L);
            } else {
                awaitingCommand = false;
                commandBuffer = "";
                capturedMode = "";
                scheduleNext(500L);
            }
            return;
        }
        lastHeard = shorten(text);
        consecutiveErrors = 0;

        String withoutWake = VoiceCommandRouter.stripWake(text);
        if (VoiceCommandRouter.wakeOnly(text)) {
            awaitingCommand = true;
            awaitingSince = System.currentTimeMillis();
            commandBuffer = "";
            capturedMode = inheritedMode;
            commandBufferAt = 0L;
            updateNotification(inheritedMode.isEmpty()
                    ? "Heard “Penguru” · listening for your message…"
                    : "Heard “Penguru” · " + VoiceCommandRouter.modeName(inheritedMode)
                        + " selected · listening…");
            scheduleNext(180L);
            return;
        }

        if (VoiceCommandRouter.hasWake(text)) {
            awaitingCommand = false;
            VoiceCommandRouter.ModeMatch mode = VoiceCommandRouter.parseMode(withoutWake);
            String selectedMode = mode != null ? mode.mode : inheritedMode;
            String rest = mode != null ? mode.rest : withoutWake;
            if (rest.isEmpty()) {
                if (!selectedMode.isEmpty()) {
                    // "Penguru chat" / "Penguru code" selects the assistant
                    // and keeps the follow-up window open for the request.
                    dispatch("", selectedMode);
                    awaitingCommand = true;
                    awaitingSince = System.currentTimeMillis();
                    commandBuffer = "";
                    capturedMode = selectedMode;
                    updateNotification("Heard “Penguru” · "
                            + VoiceCommandRouter.modeName(selectedMode) + " selected · listening…");
                    scheduleNext(180L);
                } else {
                    awaitingCommand = true;
                    awaitingSince = System.currentTimeMillis();
                    commandBuffer = "";
                    capturedMode = "";
                    updateNotification("Heard “Penguru” · listening for your message…");
                    scheduleNext(180L);
                }
                return;
            }
            if (handleVoiceCommand(rest)) {
                return;
            }
            dispatch(rest, selectedMode);
            return;
        }

        if (awaitingCommand) {
            if (System.currentTimeMillis() - awaitingSince > COMMAND_FOLLOW_UP_MS) {
                awaitingCommand = false;
                commandBuffer = "";
                capturedMode = "";
                scheduleNext(500L);
                return;
            }
            awaitingCommand = false;
            VoiceCommandRouter.ModeMatch mode = VoiceCommandRouter.parseMode(text);
            String selectedMode = mode != null ? mode.mode : inheritedMode;
            String rest = mode != null ? mode.rest : text;
            if (rest.isEmpty() && !selectedMode.isEmpty()) {
                dispatch("", selectedMode);
                awaitingCommand = true;
                awaitingSince = System.currentTimeMillis();
                capturedMode = selectedMode;
                updateNotification("Heard “Penguru” · "
                        + VoiceCommandRouter.modeName(selectedMode) + " selected · listening…");
                scheduleNext(180L);
                return;
            }
            if (handleVoiceCommand(rest)) {
                return;
            }
            dispatch(rest, selectedMode);
            return;
        }

        // A bare "stop" / "cancel" is accepted while the listener is armed so
        // the owner can stop it without first saying the wake word.
        if (handleVoiceCommand(text)) {
            return;
        }
        scheduleNext(500L);
    }

    /**
     * Returns true when the transcript was a microphone command rather than a
     * message. "Penguru stop" stops the persistent listener; "Penguru send"
     * sends the sentence captured so far.
     */
    private boolean handleVoiceCommand(String text) {
        String command = VoiceCommandRouter.classify(text);
        if (VoiceCommandRouter.STOP.equals(command)) {
            stopByVoice();
            return true;
        }
        if (VoiceCommandRouter.SEND.equals(command)) {
            String captured = !commandBuffer.isEmpty() ? commandBuffer
                    : (!lastPartial.isEmpty() ? lastPartial : "");
            String mode = capturedMode;
            commandBuffer = "";
            capturedMode = "";
            if (!captured.isEmpty() || !mode.isEmpty()) {
                dispatch(captured, mode);
            } else {
                updateNotification("Nothing to send yet · listening for your message…");
                scheduleNext(250L);
            }
            return true;
        }
        return false;
    }

    private void stopByVoice() {
        voiceStopRequested = true;
        stoppingForHandoff = false;
        awaitingCommand = false;
        commandBuffer = "";
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putBoolean(PREF_ENABLED, false)
                .apply();
        updateNotification("Stopped listening by voice command");
        handler.postDelayed(() -> {
            shutdown();
            stopSelf();
        }, 650L);
    }

    /** Notification "Send now" action: finalise the sentence captured so far. */
    private void finishFromNotification() {
        String captured = !commandBuffer.isEmpty() ? commandBuffer
                : (!lastPartial.isEmpty() ? lastPartial : "");
        String mode = capturedMode;
        commandBuffer = "";
        capturedMode = "";
        if (!captured.isEmpty() || !mode.isEmpty()) {
            dispatch(captured, mode);
            return;
        }
        updateNotification("Nothing to send yet · listening for your message…");
        if (!listening && !paused && !inAppSpeech && !destroyed) {
            scheduleNext(200L);
        }
    }

    /**
     * Feed partial hypotheses into the command buffer as the recognizer hears
     * them. This is what makes the ongoing notification visibly react to
     * "Penguru" and the sentence after it before the final result arrives.
     */
    private void handlePartial(String text) {
        String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return;
        }
        lastPartial = value;
        lastHeard = shorten(value);
        String rest = VoiceCommandRouter.wakeRemainder(value);
        if (rest != null) {
            VoiceCommandRouter.ModeMatch mode = VoiceCommandRouter.parseMode(rest);
            if (mode != null) {
                awaitingCommand = true;
                awaitingSince = System.currentTimeMillis();
                capturedMode = mode.mode;
                commandBuffer = mode.rest;
                commandBufferAt = System.currentTimeMillis();
                updateNotification(mode.rest.isEmpty()
                        ? "Heard “Penguru” · " + VoiceCommandRouter.modeName(mode.mode)
                            + " selected · listening…"
                        : "Heard: " + shorten(mode.rest) + " · "
                            + VoiceCommandRouter.modeName(mode.mode) + " · still listening…");
            } else if (!rest.isEmpty()) {
                awaitingCommand = true;
                awaitingSince = System.currentTimeMillis();
                commandBuffer = rest;
                commandBufferAt = System.currentTimeMillis();
                updateNotification("Heard: " + shorten(rest) + " · still listening…");
            } else if (!awaitingCommand) {
                awaitingCommand = true;
                awaitingSince = System.currentTimeMillis();
                capturedMode = "";
                commandBuffer = "";
                updateNotification("Heard “Penguru” · listening for your message…");
            }
            return;
        }
        if (awaitingCommand) {
            if (!capturedMode.isEmpty()) {
                // The recognizer dropped the wake word from a cumulative
                // partial. Remove a repeated mode word from the buffer.
                VoiceCommandRouter.ModeMatch mode = VoiceCommandRouter.parseMode(value);
                if (mode != null) {
                    capturedMode = mode.mode;
                    value = mode.rest;
                }
            }
            if (value.isEmpty()) {
                return;
            }
            commandBuffer = value;
            commandBufferAt = System.currentTimeMillis();
            updateNotification("Heard: " + shorten(value) + " · finishing when you stop…");
        }
    }

    /** The RMS detector says the owner stopped talking. Finalise quickly. */
    private void onVadEndpoint() {
        if (voiceStopRequested) {
            return;
        }
        if (awaitingCommand && (!commandBuffer.isEmpty() || !capturedMode.isEmpty())) {
            final String captured = commandBuffer;
            final String mode = capturedMode;
            final int token = session;
            // Give onResults a brief head start so the final hypothesis can
            // replace the partial when it is better.
            handler.postDelayed(() -> {
                if (destroyed || paused || inAppSpeech || token != session
                        || (captured.isEmpty() && mode.isEmpty())) {
                    return;
                }
                // onResults may already have dispatched this sentence. The
                // 5-second duplicate guard in dispatch() makes the retry safe.
                commandBuffer = "";
                capturedMode = "";
                awaitingCommand = false;
                dispatch(captured, mode);
            }, 180L);
            return;
        }
        // Wake word alone, or noise-only energy: close this session and keep
        // the follow-up window open for the next sentence.
        if (listening && recognizer != null) {
            try {
                recognizer.stopListening();
            } catch (RuntimeException ignored) {
                // already finishing
            }
        }
    }

    private void dispatch(String command) {
        dispatch(command, "");
    }

    private void dispatch(String command, String requestedMode) {
        String text = command == null ? "" : command.trim();
        text = VoiceCommandRouter.stripWake(text);
        String mode = VoiceCommandRouter.isMode(requestedMode) ? requestedMode : "";
        String classified = VoiceCommandRouter.classify(text);
        if (VoiceCommandRouter.STOP.equals(classified)) {
            stopByVoice();
            return;
        }
        if (VoiceCommandRouter.SEND.equals(classified)) {
            String captured = !commandBuffer.isEmpty() ? commandBuffer
                    : (!lastPartial.isEmpty() ? lastPartial : "");
            String capturedRequestedMode = capturedMode;
            commandBuffer = "";
            capturedMode = "";
            if (captured.isEmpty() || captured.equalsIgnoreCase(text)) {
                if (capturedRequestedMode.isEmpty()) {
                    return;
                }
                text = "";
                mode = capturedRequestedMode;
            } else {
                text = VoiceCommandRouter.stripWake(captured);
                if (mode.isEmpty()) {
                    mode = capturedRequestedMode;
                }
            }
        }
        if (text.isEmpty() && mode.isEmpty()) {
            return;
        }
        long now = System.currentTimeMillis();
        String fingerprint = mode + "|" + text;
        if (fingerprint.equalsIgnoreCase(lastDispatch) && now - lastDispatchAt < 5000L) {
            return;
        }
        lastDispatch = fingerprint;
        lastDispatchAt = now;
        dispatchedThisSession = true;
        cancelPendingPartial();
        commandBuffer = "";
        capturedMode = "";
        awaitingCommand = false;
        restartQueued = false;
        lastError = "";
        stoppingForHandoff = true;
        stopRecognizer();
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(PREF_PENDING, text)
                .putString(PREF_PENDING_MODE, mode)
                .putLong(PREF_PENDING_AT, now)
                .apply();
        updateNotification(text.isEmpty()
                ? VoiceCommandRouter.modeName(mode) + " selected · opening PenGuru"
                : "Heard: " + shorten(text) + " · opening PenGuru");

        Intent launch = new Intent(this, MainActivity.class);
        launch.setAction(Intent.ACTION_VIEW);
        launch.putExtra(EXTRA_COMMAND, text);
        launch.putExtra(EXTRA_MODE, mode);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                | Intent.FLAG_ACTIVITY_SINGLE_TOP
                | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        try {
            startActivity(launch);
        } catch (RuntimeException error) {
            // Android 10+ may block background activity launches. The ongoing
            // notification's content intent carries the command instead.
            Log.w(TAG, "Background activity launch blocked: " + error);
            updateNotification(text.isEmpty()
                    ? VoiceCommandRouter.modeName(mode) + " selected · tap to open PenGuru"
                    : "Heard: " + shorten(text) + " · tap to send");
        }
        handler.postDelayed(() -> {
            stoppingForHandoff = false;
            if (!destroyed && !paused && !inAppSpeech) {
                beginListening();
            }
        }, 2500L);
    }

    private static String shorten(String text) {
        return text.length() <= 60 ? text : text.substring(0, 57) + "…";
    }

    /* ------------------------------------------------------ recognition */

    /**
     * One listener per recognizer session. Stale callbacks from a recognizer
     * that was cancelled or replaced are ignored instead of scheduling two
     * competing sessions (the source of repeated ERROR_RECOGNIZER_BUSY).
     */
    private final class SessionListener implements RecognitionListener {
        private final int token;

        SessionListener(int token) {
            this.token = token;
        }

        private boolean stale() {
            return destroyed || paused || token != session;
        }

        @Override
        public void onReadyForSpeech(Bundle params) {
            if (stale()) {
                return;
            }
            lastError = "";
            updateNotification(awaitingCommand
                    ? "Listening for your message…"
                    : "Listening for “Penguru” · say it, then your message");
        }

        @Override public void onBeginningOfSpeech() { }
        @Override public void onBufferReceived(byte[] buffer) { }
        @Override public void onEvent(int eventType, Bundle params) { }

        @Override
        public void onRmsChanged(float rmsdB) {
            if (stale() || vad == null) {
                return;
            }
            if (vad.update(rmsdB)) {
                onVadEndpoint();
            }
        }

        @Override
        public void onPartialResults(Bundle partialResults) {
            if (stale() || partialResults == null || dispatchedThisSession) {
                return;
            }
            ArrayList<String> matches = partialResults
                    .getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (matches == null || matches.isEmpty()) {
                return;
            }
            String text = matches.get(0) == null ? "" : matches.get(0).trim();
            if (text.isEmpty() || text.equals(lastPartial)) {
                return;
            }
            handlePartial(text);
        }

        @Override
        public void onEndOfSpeech() {
            if (stale() || !listening || recognizer == null) {
                return;
            }
            if (vad != null) {
                vad.onEndOfSpeech();
            }
            // Ask the recognizer to return its final hypothesis promptly. This
            // removes the old fixed multi-second wait after the owner stops
            // talking; the RMS detector has already confirmed real speech.
            handler.postDelayed(() -> {
                if (stale() || !listening || recognizer == null) {
                    return;
                }
                if (awaitingCommand && !commandBuffer.isEmpty()) {
                    updateNotification("Finishing: " + shorten(commandBuffer) + "…");
                }
                try {
                    recognizer.stopListening();
                } catch (RuntimeException ignored) {
                    // already stopping
                }
            }, 140L);
        }

        @Override
        public void onError(int error) {
            if (stale()) {
                return;
            }
            final boolean keepCommand = awaitingCommand
                    && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
            cancelPendingPartial();
            stopRecognizer();
            lastError = speechErrorName(error);
            consecutiveErrors++;
            if (consecutiveErrors >= 3
                    && error != SpeechRecognizer.ERROR_NO_MATCH
                    && error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                    && WhisperRecognizer.available(WakeWordService.this)) {
                forceWhisper = true;
            }
            // A recognizer that times out after partial hypotheses is exactly
            // the "owner stopped talking" case. Send what we captured instead
            // of throwing the sentence away.
            if (error == SpeechRecognizer.ERROR_NO_MATCH
                    || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                String captured = commandBuffer;
                if (awaitingCommand && !captured.isEmpty()) {
                    commandBuffer = "";
                    awaitingCommand = false;
                    dispatch(captured);
                    return;
                }
                commandBuffer = "";
            }
            if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
                updateNotification("Microphone permission is missing · open PenGuru");
                scheduleNext(8000L);
            } else if (error == SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED
                    || error == SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE) {
                awaitingCommand = keepCommand;
                if (!"en-US".equals(speechLanguage)) {
                    speechLanguage = "en-US";
                    scheduleNext(400L);
                } else {
                    scheduleNext(6000L);
                }
            } else if (error == SpeechRecognizer.ERROR_NO_MATCH
                    || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                consecutiveErrors = 0;
                awaitingCommand = keepCommand;
                scheduleNext(awaitingCommand ? 300L : 650L);
            } else if (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY
                    || error == SpeechRecognizer.ERROR_CLIENT) {
                // This is the normal hand-off window while Android tears down
                // the previous recognizer. It is not an owner-facing fault and
                // must not show "speech service busy" in the ongoing
                // notification. Keep the row calm and retry with backoff.
                lastError = "";
                stayingQuiet = true;
                awaitingCommand = keepCommand;
                long delay = Math.min(12000L, 900L * consecutiveErrors);
                updateNotification(awaitingCommand
                        ? "Listening for your message…"
                        : "Listening for “Penguru” · say it, then your message");
                scheduleNext(delay);
            } else {
                awaitingCommand = keepCommand;
                long delay = Math.min(8000L, 1000L * consecutiveErrors);
                updateNotification("Speech service: " + lastError + " · retrying…");
                scheduleNext(delay);
            }
        }

        @Override
        public void onResults(Bundle results) {
            if (stale()) {
                return;
            }
            cancelPendingPartial();
            ArrayList<String> matches = results == null ? null
                    : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            String text = matches == null || matches.isEmpty() ? "" : matches.get(0);
            String captured = commandBuffer;
            String carriedMode = capturedMode;
            stopRecognizer();
            lastError = "";
            stayingQuiet = false;
            if (dispatchedThisSession) {
                dispatchedThisSession = false;
                return;
            }
            if ((text == null || text.trim().isEmpty()) && !lastPartial.isEmpty()) {
                text = lastPartial;
            }
            if (awaitingCommand && !carriedMode.isEmpty()
                    && (text == null || text.trim().isEmpty()
                        || VoiceCommandRouter.wakeOnly(text))) {
                dispatch("", carriedMode);
                return;
            }
            // The final hypothesis can be a bare sentence after a previous
            // "Penguru" session. Prefer the captured partial when it contains
            // more of what the owner actually said.
            if (awaitingCommand && captured != null && !captured.isEmpty()
                    && (text == null || text.trim().isEmpty()
                        || !VoiceCommandRouter.hasWake(text))) {
                text = captured;
            }
            handleText(text, carriedMode);
        }
    }

    private static String speechErrorName(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO: return "audio_error";
            case SpeechRecognizer.ERROR_CLIENT: return "client_error";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "microphone_permission_denied";
            case SpeechRecognizer.ERROR_NETWORK: return "network_error";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "network_timeout";
            case SpeechRecognizer.ERROR_NO_MATCH: return "no_speech_detected";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "recognizer_busy";
            case SpeechRecognizer.ERROR_SERVER: return "speech_service_error";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "speech_timeout";
            case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED: return "language_not_supported";
            case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE: return "language_unavailable";
            default: return "speech_error_" + error;
        }
    }

    private void shutdown() {
        destroyed = true;
        running = false;
        restartQueued = false;
        speaking = false;
        stopRecognizer();
        if (talkback != null) {
            talkback.shutdown();
            talkback = null;
        }
        handler.removeCallbacksAndMessages(null);
        releaseWakeLock();
        stopForeground(true);
    }
}
