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
public class WakeWordService extends Service implements RecognitionListener {
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
    private static final Pattern WAKE = Pattern.compile(
            "\\bpen[\\s-]?guru\\b[\\s,.:;!?\\-]*(.*)$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static volatile WakeWordService instance;
    private static volatile boolean running;
    private static volatile boolean paused;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private PowerManager.WakeLock wakeLock;
    private boolean listening;
    private boolean awaitingCommand;
    private boolean restartQueued;
    private boolean destroyed;
    private long awaitingSince;
    private long lastDispatchAt;
    private String lastDispatch = "";
    private int session;

    public static boolean isRunning() {
        return running;
    }

    /** Called when an in-app dictation session needs the only microphone. */
    public static void pauseForActivity() {
        paused = true;
        WakeWordService service = instance;
        if (service != null) {
            service.handler.post(service::stopRecognizer);
        }
    }

    /** Called after the in-app dictation session releases the microphone. */
    public static void resumeFromActivity() {
        paused = false;
        WakeWordService service = instance;
        if (service != null) {
            service.handler.postDelayed(service::beginListening, 700L);
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
        paused = false;
        if (!startInForeground("Listening for “Penguru” · say it, then your message")) {
            stopSelf();
            return START_NOT_STICKY;
        }
        restartQueued = false;
        handler.removeCallbacksAndMessages(null);
        handler.postDelayed(this::beginListening, 250L);
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
        builder.setContentTitle("SonarBird is listening")
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
        if (destroyed || paused) {
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            updateNotification("Microphone permission is missing · open PenGuru");
            scheduleNext(5000L);
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            updateNotification("No Android speech recognition service · open PenGuru");
            scheduleNext(10000L);
            return;
        }
        stopRecognizer();
        final int token = session;
        try {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(this);
        } catch (RuntimeException error) {
            recognizer = null;
            scheduleNext(2000L);
            return;
        }
        listening = true;
        awaitingCommand = awaitingCommand
                && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
        Intent intent = speechIntent();
        try {
            recognizer.startListening(intent);
        } catch (RuntimeException error) {
            listening = false;
            stopRecognizer();
            scheduleNext(1500L);
            return;
        }
        handler.postDelayed(() -> {
            if (token != session || destroyed) {
                return;
            }
            stopRecognizer();
            scheduleNext(250L);
        }, SESSION_DEADLINE_MS);
    }

    private Intent speechIntent() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag());
        // Background wake listening needs the phone's normal recognizer. Many
        // offline-only recognizers have no language pack installed and then
        // hold the microphone open forever, so do not force offline here.
        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, false);
        return intent;
    }

    private void stopRecognizer() {
        session++;
        listening = false;
        if (recognizer != null) {
            try {
                recognizer.cancel();
            } catch (RuntimeException ignored) {
                // already cancelled
            }
            try {
                recognizer.destroy();
            } catch (RuntimeException ignored) {
                // already destroyed
            }
            recognizer = null;
        }
    }

    private void scheduleNext(long delayMillis) {
        if (destroyed || paused || restartQueued) {
            return;
        }
        restartQueued = true;
        handler.postDelayed(() -> {
            restartQueued = false;
            if (!destroyed && !paused) {
                beginListening();
            }
        }, delayMillis);
    }

    private void handleText(String raw) {
        String text = raw == null ? "" : raw.trim();
        if (text.isEmpty()) {
            scheduleNext(350L);
            return;
        }
        Matcher match = WAKE.matcher(text);
        if (match.find()) {
            String rest = match.group(1) == null ? "" : match.group(1).trim();
            if (!rest.isEmpty()) {
                awaitingCommand = false;
                dispatch(rest);
                scheduleNext(800L);
                return;
            }
            awaitingCommand = true;
            awaitingSince = System.currentTimeMillis();
            updateNotification("Heard “Penguru” · listening for your message…");
            scheduleNext(200L);
            return;
        }
        if (awaitingCommand) {
            if (System.currentTimeMillis() - awaitingSince > COMMAND_FOLLOW_UP_MS) {
                awaitingCommand = false;
                scheduleNext(400L);
                return;
            }
            awaitingCommand = false;
            dispatch(text);
            scheduleNext(800L);
            return;
        }
        scheduleNext(350L);
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

    @Override
    public void onReadyForSpeech(Bundle params) {
        updateNotification(awaitingCommand
                ? "Listening for your message…"
                : "Listening for “Penguru” · say it, then your message");
    }

    @Override
    public void onBeginningOfSpeech() { }

    @Override
    public void onRmsChanged(float rmsdB) { }

    @Override
    public void onBufferReceived(byte[] buffer) { }

    @Override
    public void onEndOfSpeech() {
        // Ask the recognizer to return its final hypothesis promptly. This is
        // what releases the microphone on devices that never send onResults
        // after a natural end-of-speech.
        if (listening && recognizer != null) {
            try {
                recognizer.stopListening();
            } catch (RuntimeException ignored) {
                // already stopping
            }
        }
    }

    @Override
    public void onError(int error) {
        if (destroyed) {
            return;
        }
        final boolean keepCommand = awaitingCommand
                && System.currentTimeMillis() - awaitingSince < COMMAND_FOLLOW_UP_MS;
        stopRecognizer();
        if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
            updateNotification("Microphone permission is missing · open PenGuru");
            scheduleNext(5000L);
        } else if (error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                || error == SpeechRecognizer.ERROR_NO_MATCH) {
            awaitingCommand = keepCommand;
            scheduleNext(awaitingCommand ? 250L : 600L);
        } else {
            awaitingCommand = keepCommand;
            scheduleNext(error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ? 1500L : 1000L);
        }
    }

    @Override
    public void onResults(Bundle results) {
        if (destroyed) {
            return;
        }
        ArrayList<String> matches = results == null ? null
                : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        String text = matches == null || matches.isEmpty() ? "" : matches.get(0);
        stopRecognizer();
        handleText(text);
    }

    @Override
    public void onPartialResults(Bundle partialResults) { }

    @Override
    public void onEvent(int eventType, Bundle params) { }

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
