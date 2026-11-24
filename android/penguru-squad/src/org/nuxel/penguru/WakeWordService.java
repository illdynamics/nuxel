package org.nuxel.penguru;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
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
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.Log;

import java.util.ArrayList;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
    public static final String EXTRA_COMMAND = "penguru_command";

    static final String PREFS = "penguru_wake";
    static final String PREF_ENABLED = "enabled";
    private static final String PREF_PENDING = "pending_command";
    private static final String PREF_PENDING_AT = "pending_command_at";

    private static final String CHANNEL_ID = "penguru_listening";
    private static final int NOTIFICATION_ID = 8801;
    private static final long SESSION_DEADLINE_MS = 12000L;
    private static final long COMMAND_FOLLOW_UP_MS = 20000L;
    private static final long MIN_SESSION_GAP_MS = 650L;
    private static final Pattern WAKE = Pattern.compile(
            "\\bpen[\\s-]?guru\\b[\\s,.:;!?\\-]*(.*)$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static volatile WakeWordService instance;
    private static volatile boolean running;
    private static volatile boolean paused;
    // True while MainActivity is visible. The foreground UI owns the one
    // microphone Android exposes, so the background listener stays paused for
    // the whole time the app is open instead of racing in-app dictation.
    private static volatile boolean appForeground;

    private final Handler handler = new Handler(Looper.getMainLooper());
    // Hand-off callbacks deliberately do not use `handler`: onStartCommand
    // clears that queue, and losing the "recognizer released" callback would
    // leave the in-app microphone waiting forever.
    private static final Handler HANDOFF = new Handler(Looper.getMainLooper());
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
    private String lastHeard = "";
    private int consecutiveErrors;
    private int session;

    public static boolean isRunning() {
        return running;
    }

    public static boolean isPaused() {
        return paused;
    }

    public static boolean isAppForeground() {
        return appForeground;
    }

    /**
     * Tell the listener whether MainActivity is visible. While the app is in
     * the foreground the service releases its recognizer immediately and does
     * not schedule another session. This is the important half of the fix:
     * opening the app used to leave the background recognizer holding the
     * speech service, so the first tap on the microphone failed with
     * ERROR_RECOGNIZER_BUSY ("speech service busy").
     */
    public static void setAppForeground(boolean visible) {
        appForeground = visible;
        WakeWordService service = instance;
        if (!visible) {
            return;
        }
        paused = true;
        if (service == null) {
            return;
        }
        HANDOFF.post(() -> {
            service.stopRecognizer();
            service.listening = false;
            service.restartQueued = false;
            // Do not keep showing a stale "recognizer busy" error while the
            // service is intentionally paused for the in-app microphone.
            service.lastError = "";
            service.updateNotification("Paused while PenGuru is open");
        });
    }

    /** Wait until the service has released the recognizer and microphone. */
    public static void pauseForActivity(Runnable whenPaused) {
        paused = true;
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
     * The listener stays paused while the app is visible; only backgrounding
     * the app hands the microphone back to SonarBird.
     */
    public static void resumeFromActivity() {
        if (appForeground) {
            paused = true;
            return;
        }
        paused = false;
        WakeWordService service = instance;
        if (service != null) {
            service.handler.postDelayed(service::beginListening, 900L);
        }
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
            out.put("last_error", service == null ? "" : service.lastError);
            out.put("last_heard", service == null ? "" : service.lastHeard);
            out.put("sessions", service == null ? 0 : service.session);
        } catch (Exception error) {
            // JSONObject only receives primitive values.
        }
        return out.toString();
    }

    public static void clearPendingCommand(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .remove(PREF_PENDING)
                .remove(PREF_PENDING_AT)
                .apply();
    }

    public static String takePendingCommand(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String text = prefs.getString(PREF_PENDING, "");
        long at = prefs.getLong(PREF_PENDING_AT, 0);
        clearPendingCommand(context);
        if (text == null || text.trim().isEmpty()) {
            return "";
        }
        if (System.currentTimeMillis() - at > 120000L) {
            return "";
        }
        return text.trim();
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        running = true;
        destroyed = false;
        createChannel();
        acquireWakeLock();
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

        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putBoolean(PREF_ENABLED, true)
                .apply();
        // A START command must not steal the microphone back while the
        // Activity is visible. This happened when launch-time permission
        // checks restarted an enabled listener after onStart had paused it.
        paused = appForeground;
        if (!startInForeground(appForeground
                ? "Paused while PenGuru is open"
                : "Listening for “Penguru” · say it, then your message")) {
            lastError = "Android refused to start the microphone foreground service. Open PenGuru while the screen is on and start listening again.";
            stopSelf();
            return START_NOT_STICKY;
        }
        restartQueued = false;
        handler.removeCallbacksAndMessages(null);
        if (appForeground) {
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
        stopRecognizer();
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
        if (pending != null && !pending.isEmpty()) {
            open.putExtra(EXTRA_COMMAND, pending);
        }
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent content = PendingIntent.getActivity(this, 8802, open, flags);
        PendingIntent stop = PendingIntent.getService(this, 8803,
                new Intent(this, WakeWordService.class).setAction(ACTION_STOP), flags);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        builder.setContentTitle(appForeground ? "SonarBird paused" : "SonarBird is listening")
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_stat_penguru)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setContentIntent(content)
                .setCategory(Notification.CATEGORY_SERVICE)
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

    private void beginListening() {
        restartQueued = false;
        if (destroyed || paused || appForeground) {
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            lastError = "Microphone permission is missing";
            updateNotification("Microphone permission is missing · open PenGuru");
            scheduleNext(5000L);
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            lastError = "No Android speech recognition service";
            updateNotification("No Android speech recognition service · open PenGuru");
            scheduleNext(10000L);
            return;
        }
        long sinceLast = System.currentTimeMillis() - lastSessionAt;
        if (sinceLast < MIN_SESSION_GAP_MS) {
            scheduleNext(MIN_SESSION_GAP_MS - sinceLast);
            return;
        }
        stopRecognizer();
        final int token = session;
        try {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(new SessionListener(token));
        } catch (RuntimeException error) {
            recognizer = null;
            lastError = "Speech recognizer unavailable: " + error.getMessage();
            scheduleNext(2500L);
            return;
        }
        listening = true;
        lastSessionAt = System.currentTimeMillis();
        awaitingCommand = awaitingCommand
                && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
        Intent intent = speechIntent();
        try {
            recognizer.startListening(intent);
            lastError = "";
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
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
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
        // Ask compliant recognizers to finish short wake phrases promptly.
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 700L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 700L);
        return intent;
    }

    private void stopRecognizer() {
        session++;
        listening = false;
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

    private void scheduleNext(long delayMillis) {
        if (destroyed || paused || appForeground || restartQueued) {
            return;
        }
        restartQueued = true;
        handler.postDelayed(() -> {
            restartQueued = false;
            if (!destroyed && !paused && !appForeground) {
                beginListening();
            }
        }, delayMillis);
    }

    private void handleText(String raw) {
        String text = raw == null ? "" : raw.trim();
        if (text.isEmpty()) {
            scheduleNext(500L);
            return;
        }
        lastHeard = shorten(text);
        consecutiveErrors = 0;
        Matcher match = WAKE.matcher(text);
        if (match.find()) {
            String rest = match.group(1) == null ? "" : match.group(1).trim();
            if (!rest.isEmpty()) {
                awaitingCommand = false;
                dispatch(rest);
                scheduleNext(900L);
                return;
            }
            awaitingCommand = true;
            awaitingSince = System.currentTimeMillis();
            updateNotification("Heard “Penguru” · listening for your message…");
            scheduleNext(250L);
            return;
        }
        if (awaitingCommand) {
            if (System.currentTimeMillis() - awaitingSince > COMMAND_FOLLOW_UP_MS) {
                awaitingCommand = false;
                scheduleNext(500L);
                return;
            }
            awaitingCommand = false;
            dispatch(text);
            scheduleNext(900L);
            return;
        }
        scheduleNext(500L);
    }

    private void dispatch(String command) {
        final String text = command == null ? "" : command.trim();
        if (text.isEmpty()) {
            return;
        }
        long now = System.currentTimeMillis();
        if (text.equalsIgnoreCase(lastDispatch) && now - lastDispatchAt < 5000L) {
            return;
        }
        lastDispatch = text;
        lastDispatchAt = now;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(PREF_PENDING, text)
                .putLong(PREF_PENDING_AT, now)
                .apply();
        updateNotification("Heard: " + shorten(text) + " · opening PenGuru");

        Intent launch = new Intent(this, MainActivity.class);
        launch.setAction(Intent.ACTION_VIEW);
        launch.putExtra(EXTRA_COMMAND, text);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                | Intent.FLAG_ACTIVITY_SINGLE_TOP
                | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        try {
            startActivity(launch);
        } catch (RuntimeException error) {
            // Android 10+ may block background activity launches. The ongoing
            // notification's content intent carries the command instead.
            Log.w(TAG, "Background activity launch blocked: " + error);
        }
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
        @Override public void onRmsChanged(float rmsdB) { }
        @Override public void onBufferReceived(byte[] buffer) { }
        @Override public void onPartialResults(Bundle partialResults) { }
        @Override public void onEvent(int eventType, Bundle params) { }

        @Override
        public void onEndOfSpeech() {
            if (stale() || !listening || recognizer == null) {
                return;
            }
            // Ask the recognizer to return its final hypothesis promptly. This is
            // what releases the microphone on devices that never send onResults
            // after a natural end-of-speech.
            try {
                recognizer.stopListening();
            } catch (RuntimeException ignored) {
                // already stopping
            }
        }

        @Override
        public void onError(int error) {
            if (stale()) {
                return;
            }
            final boolean keepCommand = awaitingCommand
                    && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
            stopRecognizer();
            lastError = speechErrorName(error);
            consecutiveErrors++;
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
                // The previous recognizer is still releasing, or another app
                // owns the speech service. Back off instead of hammering it.
                awaitingCommand = keepCommand;
                long delay = Math.min(8000L, 1200L * consecutiveErrors);
                updateNotification("Android speech service busy · retrying in "
                        + Math.round(delay / 1000.0) + "s");
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
            ArrayList<String> matches = results == null ? null
                    : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            String text = matches == null || matches.isEmpty() ? "" : matches.get(0);
            stopRecognizer();
            handleText(text);
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
        stopRecognizer();
        handler.removeCallbacksAndMessages(null);
        releaseWakeLock();
        stopForeground(true);
    }
}
