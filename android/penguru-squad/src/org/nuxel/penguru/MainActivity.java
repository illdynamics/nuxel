package org.nuxel.penguru;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.StatFs;
import android.provider.MediaStore;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.text.TextUtils;
import android.util.Log;
import android.view.View;
import android.widget.FrameLayout;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.zip.GZIPInputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Offline-first PenGuru Squad shell.
 *
 * The complete PWA is bundled under assets/public and served from a private
 * https://appassets.androidplatform.net origin. No third-party WebView
 * dependency is used: shouldInterceptRequest reads only files inside the APK.
 *
 * The JavaScript on-device engine (local-engine.js) uses the NuxelAndroid
 * bridge for the work a WebView cannot do itself: verified model/runtime
 * downloads into app-specific storage, device diagnostics, response export,
 * external links and Android speech recognition. A Nuxel host is optional.
 */
public class MainActivity extends Activity {
    private static final String TAG = "PenGuruSquad";
    private static final String ASSET_HOST = "appassets.androidplatform.net";
    private static final String START_PATH = "/pwa/nuxel-apps/penguru/index.html";
    private static final int MIC_REQUEST = 7001;
    private static final int SPEECH_REQUEST = 7002;
    private static final int WAKE_MIC_REQUEST = 7003;
    private static final int WAKE_NOTIFICATION_REQUEST = 7004;
    private static final int STARTUP_PERMISSIONS_REQUEST = 7005;
    private static final String UI_PREFS = "penguru_ui";
    private static final String PREF_BATTERY_PROMPT_AT = "battery_prompt_at";
    private static final String PREF_STORAGE_PROMPT_AT = "storage_prompt_at";
    private static final String MODELS_DIR_NAME = "Models";
    private static final String RUNTIMES_DIR_NAME = "Runtimes";

    private FrameLayout root;
    private WebView webView;
    private PermissionRequest pendingAudio;
    private SpeechRecognizer speechRecognizer;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private boolean speechRunning;
    private boolean speechWake;
    private boolean pendingSpeech;
    private boolean pendingSpeechWake;
    // Each start is a numbered session. Stale SpeechRecognizer callbacks and
    // delayed retries are ignored instead of surfacing as a bogus client_error.
    private int speechToken;
    private int speechRetryCount;
    private boolean speechPreferOffline = true;
    private String speechLanguage = "";
    private boolean pageReady;
    private boolean startupChecked;
    private boolean batteryDialogShowing;
    private boolean storageDialogShowing;
    private boolean batterySettingsOpened;
    private final ArrayDeque<String> pendingWakeCommands = new ArrayDeque<>();

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Draw edge-to-edge on every supported release, then inset a real
        // container view. Padding on the WebView itself is not consistently
        // honoured by Chromium, which let page text run underneath the status
        // bar and the three-button navigation row on Android.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
        getWindow().setStatusBarColor(Color.TRANSPARENT);
        getWindow().setNavigationBarColor(Color.TRANSPARENT);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0b1422"));
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#0b1422"));
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setLoadWithOverviewMode(false);
        settings.setUseWideViewPort(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            // Optional remote bridges and local llama.cpp servers are commonly
            // plain http on loopback or a private LAN; TLS cannot be assumed.
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(
                    (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0);
        }

        webView.setWebViewClient(new LocalAssetClient());
        webView.setWebChromeClient(new PenGuruChromeClient());
        webView.addJavascriptInterface(new AndroidBridge(), "NuxelAndroid");
        applySystemBarInsets(root);
        setContentView(root);

        if (savedInstanceState == null) {
            webView.loadUrl("https://" + ASSET_HOST + START_PATH);
        } else {
            webView.restoreState(savedInstanceState);
        }
        handleWakeIntent(getIntent());
        PenGuruStorage.migrateLegacy(this);
        // Re-queue a download that was interrupted by a rebuild, process death
        // or the Activity being reclaimed while the screen was off.
        mainHandler.postDelayed(() -> DownloadService.resumePending(this), 600L);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleWakeIntent(intent);
    }
    @Override
    protected void onStart() {
        super.onStart();
        // The in-app UI owns the microphone while it is visible. Releasing the
        // SonarBird recognizer here (rather than only on the first mic tap)
        // gives Android's speech service time to tear down its binder, so the
        // first tap no longer reports "speech service is still releasing the
        // previous session" / ERROR_RECOGNIZER_BUSY.
        WakeWordService.setAppForeground(true);
    }

    @Override
    protected void onStop() {
        // Leaving the app hands the microphone back to SonarBird. Invalidate
        // every queued foreground start and release any session first so the
        // two recognizers never overlap.
        speechToken++;
        speechRunning = false;
        pendingSpeech = false;
        releaseSpeechRecognizer();
        WakeWordService.setAppForeground(false);
        if (getSharedPreferences(WakeWordService.PREFS, MODE_PRIVATE)
                .getBoolean(WakeWordService.PREF_ENABLED, false)) {
            WakeWordService.resumeFromActivity();
        }
        super.onStop();
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Returning from the "All files access" or battery screens can change
        // where downloads live. Re-run the migration and refresh the UI.
        if (startupChecked) {
            mainHandler.postDelayed(() -> {
                PenGuruStorage.migrateLegacy(MainActivity.this);
                reportWakeStatus(PenGuruStorage.hasAllFilesAccess(MainActivity.this)
                        ? "Downloads are stored in Download/PenGuru and survive reinstalls."
                        : "Downloads are stored in app storage. Allow All files access to reuse them after a reinstall.");
                maybeAskForAllFilesAccess();
            }, 500L);
        }
    }

    /** Keep the page out of the status bar, cutouts and the back/home/recents
     *  navigation row. Applied to the container so Chromium's page viewport is
     *  genuinely reduced rather than drawn under the system bars. */
    private static void applySystemBarInsets(final View view) {
        view.setOnApplyWindowInsetsListener((v, insets) -> {
            int top = 0, bottom = 0, left = 0, right = 0;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                android.graphics.Insets bars = insets.getInsets(
                        android.view.WindowInsets.Type.systemBars()
                                | android.view.WindowInsets.Type.displayCutout());
                top = bars.top;
                bottom = bars.bottom;
                left = bars.left;
                right = bars.right;
                // Keep focused text fields above the on-screen keyboard.
                int ime = insets.getInsets(android.view.WindowInsets.Type.ime()).bottom;
                if (ime > bottom) {
                    bottom = ime;
                }
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                top = insets.getSystemWindowInsetTop();
                bottom = insets.getSystemWindowInsetBottom();
                left = insets.getSystemWindowInsetLeft();
                right = insets.getSystemWindowInsetRight();
            }
            v.setPadding(left, top, right, bottom);
            return insets;
        });
        view.requestApplyInsets();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        if (webView != null) {
            webView.saveState(outState);
        }
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onDestroy() {
        speechToken++;
        speechRunning = false;
        pendingSpeech = false;
        mainHandler.removeCallbacksAndMessages(null);
        if (speechRecognizer != null) {
            try {
                speechRecognizer.cancel();
            } catch (RuntimeException ignored) {
                // already stopped
            }
            speechRecognizer.destroy();
            speechRecognizer = null;
        }
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == STARTUP_PERMISSIONS_REQUEST) {
            boolean mic = checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED;
            boolean notifications = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                    || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    == PackageManager.PERMISSION_GRANTED;
            reportWakeStatus(mic
                    ? "Microphone permission ready. " + (notifications
                        ? "Notifications ready." : "Notifications are disabled; the ongoing rows stay hidden.")
                    : "Microphone permission is required for voice and background listening.");
            mainHandler.postDelayed(this::afterStartupPermissions, 400L);
            return;
        }
        boolean granted = results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED;
        if (requestCode == SPEECH_REQUEST) {
            boolean wake = pendingSpeechWake;
            boolean shouldStart = pendingSpeech;
            pendingSpeech = false;
            if (!granted) {
                deliverSpeech("", wake, "microphone_permission_denied", speechToken);
            } else if (shouldStart) {
                beginSpeech(wake);
            }
            return;
        }
        if (requestCode == WAKE_MIC_REQUEST) {
            if (!granted) {
                WakeWordService.clearPendingCommand(this);
                reportWakeStatus("Microphone permission denied. Enable it for PenGuru Squad in Android Settings.");
            } else {
                continueWakeStart();
            }
            return;
        }
        if (requestCode == WAKE_NOTIFICATION_REQUEST) {
            // The foreground service still runs when notifications are denied;
            // Android simply hides the ongoing row from the notification shade.
            finishWakeStart();
            return;
        }
        if (requestCode != MIC_REQUEST || pendingAudio == null) {
            return;
        }
        if (granted) {
            pendingAudio.grant(pendingAudio.getResources());
        } else {
            pendingAudio.deny();
        }
        pendingAudio = null;
    }

    /* ---------------------------------------------- startup permissions */

    /**
     * Runs once when the app page has loaded. Android requires microphone and
     * notification permissions plus a battery-optimization exemption for a
     * persistent background listener and screen-off downloads.
     */
    private void runStartupChecks() {
        if (startupChecked) {
            return;
        }
        startupChecked = true;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED
                || (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                    && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED)) {
            List<String> missing = new ArrayList<>();
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                missing.add(Manifest.permission.RECORD_AUDIO);
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                    && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                missing.add(Manifest.permission.POST_NOTIFICATIONS);
            }
            reportWakeStatus("PenGuru needs microphone and notification access for voice and background listening.");
            requestPermissions(missing.toArray(new String[0]), STARTUP_PERMISSIONS_REQUEST);
            return;
        }
        afterStartupPermissions();
    }

    private void afterStartupPermissions() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            reportWakeStatus("Microphone permission is missing. Open Android Settings → Apps → PenGuru Squad → Permissions.");
            return;
        }
        // Restore a listener the owner previously enabled (also after an APK
        // update or process restart) now that permissions are definitely on.
        SharedPreferences prefs = getSharedPreferences(WakeWordService.PREFS, MODE_PRIVATE);
        if (prefs.getBoolean(WakeWordService.PREF_ENABLED, false)
                && !WakeWordService.isRunning()) {
            finishWakeStart();
        }
        maybeAskForBatteryExemption();
        mainHandler.postDelayed(this::maybeAskForAllFilesAccess, 1200L);
    }

    private boolean isIgnoringBatteryOptimizations() {
        try {
            PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
            return power != null && power.isIgnoringBatteryOptimizations(getPackageName());
        } catch (RuntimeException error) {
            return false;
        }
    }

    private void maybeAskForBatteryExemption() {
        if (isIgnoringBatteryOptimizations()) {
            reportWakeStatus("Background listening and downloads are protected from battery saver.");
            return;
        }
        if (batteryDialogShowing || isFinishing()) {
            return;
        }
        SharedPreferences prefs = getSharedPreferences(UI_PREFS, MODE_PRIVATE);
        long last = prefs.getLong(PREF_BATTERY_PROMPT_AT, 0L);
        // Ask on first launch and then at most once a week until the owner
        // grants the exemption; never nag on every activity resume.
        if (last > 0 && System.currentTimeMillis() - last < 7L * 24L * 60L * 60L * 1000L) {
            return;
        }
        batteryDialogShowing = true;
        prefs.edit().putLong(PREF_BATTERY_PROMPT_AT, System.currentTimeMillis()).apply();
        new AlertDialog.Builder(this)
                .setTitle("Keep PenGuru running")
                .setMessage("Android battery optimization can stop background listening and interrupt model downloads when the screen turns off.\n\nAllow PenGuru Squad to ignore battery optimization?")
                .setPositiveButton("Open settings", (dialog, which) -> {
                    batterySettingsOpened = true;
                    requestBatteryExemption();
                })
                .setNegativeButton("Later", null)
                .setOnDismissListener(dialog -> {
                    batteryDialogShowing = false;
                    if (!batterySettingsOpened) {
                        mainHandler.postDelayed(MainActivity.this::maybeAskForAllFilesAccess, 400L);
                    }
                    batterySettingsOpened = false;
                })
                .show();
    }

    private void requestBatteryExemption() {
        try {
            Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
            intent.setData(Uri.parse("package:" + getPackageName()));
            startActivity(intent);
        } catch (RuntimeException error) {
            try {
                startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
            } catch (RuntimeException unavailable) {
                reportWakeStatus("Open Android Settings → Battery → Battery optimization to allow PenGuru Squad.");
            }
        }
    }

    private boolean hasAllFilesAccess() {
        return PenGuruStorage.hasAllFilesAccess(this);
    }

    private void maybeAskForAllFilesAccess() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R || hasAllFilesAccess()) {
            return;
        }
        if (storageDialogShowing || batteryDialogShowing || isFinishing()) {
            return;
        }
        SharedPreferences prefs = getSharedPreferences(UI_PREFS, MODE_PRIVATE);
        long last = prefs.getLong(PREF_STORAGE_PROMPT_AT, 0L);
        if (last > 0 && System.currentTimeMillis() - last < 7L * 24L * 60L * 60L * 1000L) {
            return;
        }
        storageDialogShowing = true;
        prefs.edit().putLong(PREF_STORAGE_PROMPT_AT, System.currentTimeMillis()).apply();
        new AlertDialog.Builder(this)
                .setTitle("Reuse downloads after reinstalling")
                .setMessage("Android normally deletes app storage when an APK is uninstalled, which forces every model and llama.cpp runtime to be downloaded again.\n\nAllow All files access so PenGuru can keep models in Download/PenGuru and find them after the APK is reinstalled. PenGuru only reads and writes its own PenGuru folder.")
                .setPositiveButton("Open settings", (dialog, which) -> requestAllFilesAccess())
                .setNegativeButton("Not now", null)
                .setOnDismissListener(dialog -> storageDialogShowing = false)
                .show();
    }

    private void requestAllFilesAccess() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            return;
        }
        try {
            Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
            intent.setData(Uri.parse("package:" + getPackageName()));
            startActivity(intent);
        } catch (RuntimeException error) {
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));
            } catch (RuntimeException unavailable) {
                reportWakeStatus("Open Android Settings → Apps → Special access → All files access → PenGuru Squad.");
            }
        }
    }

    /* ------------------------------------------------ background listener */

    private void requestWakeStart() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            reportWakeStatus("Waiting for microphone permission…");
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, WAKE_MIC_REQUEST);
            return;
        }
        continueWakeStart();
    }

    private void continueWakeStart() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            reportWakeStatus("Waiting for notification permission…");
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    WAKE_NOTIFICATION_REQUEST);
            return;
        }
        finishWakeStart();
    }

    private void finishWakeStart() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            reportWakeStatus("Microphone permission is required for background listening.");
            return;
        }
        try {
            Intent service = new Intent(this, WakeWordService.class)
                    .setAction(WakeWordService.ACTION_START);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(service);
            } else {
                startService(service);
            }
            getSharedPreferences(WakeWordService.PREFS, MODE_PRIVATE).edit()
                    .putBoolean(WakeWordService.PREF_ENABLED, true)
                    .apply();
            reportWakeStatus("SonarBird background listening started. The persistent notification means the microphone is in use.");
        } catch (RuntimeException error) {
            reportWakeStatus("Could not start background listening: " + error.getMessage());
        }
    }

    private void reportWakeStatus(final String text) {
        final WebView view = webView;
        if (view == null) {
            return;
        }
        final String script = "window.__penguruWakeStatus && window.__penguruWakeStatus("
                + JSONObject.quote(text) + ")";
        view.post(() -> {
            if (webView != null) {
                webView.evaluateJavascript(script, null);
            }
        });
    }

    private void handleWakeIntent(Intent intent) {
        if (intent == null) {
            return;
        }
        String command = intent.getStringExtra(WakeWordService.EXTRA_COMMAND);
        if (command != null && !command.trim().isEmpty()) {
            intent.removeExtra(WakeWordService.EXTRA_COMMAND);
            WakeWordService.clearPendingCommand(this);
            queueWakeCommand(command.trim());
            return;
        }
        String pending = WakeWordService.takePendingCommand(this);
        if (!pending.isEmpty()) {
            queueWakeCommand(pending);
        }
    }

    private void queueWakeCommand(String text) {
        if (text == null) {
            return;
        }
        String command = text.trim();
        if (command.isEmpty()) {
            return;
        }
        if (!pageReady) {
            synchronized (pendingWakeCommands) {
                pendingWakeCommands.addLast(command);
            }
            reportWakeStatus("Wake-word command queued until PenGuru finishes loading…");
            return;
        }
        dispatchWakeCommand(command);
    }

    private void flushPendingWakeCommands() {
        for (;;) {
            String next;
            synchronized (pendingWakeCommands) {
                next = pendingWakeCommands.pollFirst();
            }
            if (next == null) {
                return;
            }
            dispatchWakeCommand(next);
        }
    }

    private void dispatchWakeCommand(final String text) {
        final WebView view = webView;
        if (view == null) {
            return;
        }
        // Queue inside the page if the ES module has not installed its hook
        // yet. This makes a command heard during page load survive instead of
        // being dropped by evaluateJavascript.
        final String script = "(function(t){if(window.__penguruWakeCommand){"
                + "window.__penguruWakeCommand(t);return true;}"
                + "(window.__penguruWakeQueue=window.__penguruWakeQueue||[]).push(t);"
                + "return false;})(" + JSONObject.quote(text) + ")";
        view.post(() -> {
            if (webView != null) {
                webView.evaluateJavascript(script, null);
            }
        });
        reportWakeStatus("Heard via SonarBird · sending automatically");
    }

    /* --------------------------------------------------------- JS bridge */

    /**
     * Narrow JS bridge. It is exposed only to the bundled app origin; the
     * WebView never navigates to remote HTML. All writes stay inside the app's
     * own external files directory or the owner-visible MediaStore Downloads
     * folder.
     */
    private final class AndroidBridge {
        @JavascriptInterface
        public boolean isStandalone() {
            return true;
        }

        @JavascriptInterface
        public String deviceInfo() {
            try {
                JSONObject out = new JSONObject();
                out.put("manufacturer", Build.MANUFACTURER);
                out.put("model", Build.MODEL);
                out.put("device", Build.DEVICE);
                out.put("release", Build.VERSION.RELEASE);
                out.put("sdk", Build.VERSION.SDK_INT);
                out.put("abis", TextUtils.join(",", Build.SUPPORTED_ABIS));
                out.put("models_dir", PenGuruStorage.dir(MainActivity.this, PenGuruStorage.MODELS_DIR_NAME).getAbsolutePath());
                out.put("runtimes_dir", PenGuruStorage.dir(MainActivity.this, PenGuruStorage.RUNTIMES_DIR_NAME).getAbsolutePath());
                StatFs stat = new StatFs(PenGuruStorage.root(MainActivity.this).getAbsolutePath());
                out.put("free_storage", stat.getAvailableBytes());
                out.put("speech_available", SpeechRecognizer.isRecognitionAvailable(MainActivity.this));
                BatteryManager battery = (BatteryManager) getSystemService(BATTERY_SERVICE);
                int level = battery == null ? -1 : battery.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
                out.put("battery", level);
                Intent batteryIntent = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
                int status = batteryIntent == null ? -1
                        : batteryIntent.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
                out.put("charging", status == BatteryManager.BATTERY_STATUS_CHARGING
                        || status == BatteryManager.BATTERY_STATUS_FULL);
                return out.toString();
            } catch (JSONException | RuntimeException error) {
                return "{}";
            }
        }

        @JavascriptInterface
        public String storagePaths() {
            try {
                JSONObject out = new JSONObject();
                out.put("models", PenGuruStorage.dir(MainActivity.this, PenGuruStorage.MODELS_DIR_NAME).getAbsolutePath());
                out.put("runtimes", PenGuruStorage.dir(MainActivity.this, PenGuruStorage.RUNTIMES_DIR_NAME).getAbsolutePath());
                out.put("exports", "Downloads/PenGuru");
                return out.toString();
            } catch (JSONException error) {
                return "{}";
            }
        }

        @JavascriptInterface
        public String startDownload(String specJson) {
            return DownloadService.start(MainActivity.this, specJson);
        }

        @JavascriptInterface
        public String downloadStatus(String jobId) {
            return DownloadService.statusJson(jobId);
        }

        @JavascriptInterface
        public String downloadJobs() {
            return DownloadService.activeJobsJson();
        }

        @JavascriptInterface
        public boolean cancelDownload(String jobId) {
            return DownloadService.cancel(MainActivity.this, jobId);
        }

        @JavascriptInterface
        public boolean isInstalled(String kind, String id) {
            return DownloadService.isInstalled(MainActivity.this, kind, id);
        }

        @JavascriptInterface
        public boolean isInstalledWithFiles(String kind, String id, String filesJson) {
            return DownloadService.isInstalledWithFiles(MainActivity.this, kind, id, filesJson);
        }

        @JavascriptInterface
        public String installedPath(String kind, String id) {
            return DownloadService.installedPath(MainActivity.this, kind, id);
        }

        @JavascriptInterface
        public boolean deleteInstalled(String kind, String id) {
            return DownloadService.deleteInstalled(MainActivity.this, kind, id);
        }

        @JavascriptInterface
        public String listInstalled(String kind) {
            return DownloadService.listInstalled(MainActivity.this, kind);
        }

        @JavascriptInterface
        public String permissionStatus() {
            try {
                JSONObject out = new JSONObject();
                boolean mic = checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                        == PackageManager.PERMISSION_GRANTED;
                boolean notifications = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                        || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                        == PackageManager.PERMISSION_GRANTED;
                out.put("microphone", mic);
                out.put("notifications", notifications);
                out.put("battery_optimized", !isIgnoringBatteryOptimizations());
                out.put("all_files_access", hasAllFilesAccess());
                out.put("storage_root", PenGuruStorage.root(MainActivity.this).getAbsolutePath());
                out.put("wake_service", WakeWordService.isRunning());
                out.put("downloads", DownloadService.activeJobsJson());
                return out.toString();
            } catch (JSONException error) {
                return "{}";
            }
        }

        @JavascriptInterface
        public boolean requestBatteryExemption() {
            runOnUiThread(MainActivity.this::requestBatteryExemption);
            return true;
        }

        @JavascriptInterface
        public boolean requestAppPermissions() {
            runOnUiThread(() -> {
                startupChecked = false;
                runStartupChecks();
            });
            return true;
        }

        @JavascriptInterface
        public boolean hasBatteryExemption() {
            return isIgnoringBatteryOptimizations();
        }

        @JavascriptInterface
        public boolean hasAllFilesAccess() {
            return MainActivity.this.hasAllFilesAccess();
        }

        @JavascriptInterface
        public boolean requestAllFilesAccess() {
            runOnUiThread(MainActivity.this::requestAllFilesAccess);
            return true;
        }

        @JavascriptInterface
        public boolean speechAvailable() {
            try {
                return SpeechRecognizer.isRecognitionAvailable(MainActivity.this);
            } catch (RuntimeException error) {
                return false;
            }
        }

        @JavascriptInterface
        public boolean startSpeechRecognition(final boolean wake) {
            if (!speechAvailable()) {
                return false;
            }
            runOnUiThread(() -> {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                        != PackageManager.PERMISSION_GRANTED) {
                    pendingSpeech = true;
                    pendingSpeechWake = wake;
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, SPEECH_REQUEST);
                    return;
                }
                beginSpeech(wake);
            });
            return true;
        }

        @JavascriptInterface
        public void stopSpeechRecognition() {
            runOnUiThread(() -> {
                pendingSpeech = false;
                speechRunning = false;
                // Invalidate any queued restart so a stop is final even if the
                // recognizer was still connecting or a permission dialog was open.
                speechToken++;
                releaseSpeechRecognizer();
                WakeWordService.resumeFromActivity();
            });
        }

        @JavascriptInterface
        public boolean startWakeWordService() {
            runOnUiThread(MainActivity.this::requestWakeStart);
            return true;
        }

        @JavascriptInterface
        public void stopWakeWordService() {
            runOnUiThread(() -> {
                getSharedPreferences(WakeWordService.PREFS, MODE_PRIVATE).edit()
                        .putBoolean(WakeWordService.PREF_ENABLED, false)
                        .apply();
                WakeWordService.clearPendingCommand(MainActivity.this);
                stopService(new Intent(MainActivity.this, WakeWordService.class));
                reportWakeStatus("Background SonarBird listening stopped.");
            });
        }

        @JavascriptInterface
        public String wakeServiceStatus() {
            return WakeWordService.statusJson(MainActivity.this);
        }

        @JavascriptInterface
        public String saveText(String filename, String text) {
            if (text == null) {
                return null;
            }
            try {
                String safe = sanitizeFilename(filename);
                if (safe.isEmpty()) {
                    safe = "penguru-response.txt";
                }
                if (!safe.contains(".")) {
                    safe += ".txt";
                }
                byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.MediaColumns.DISPLAY_NAME, safe);
                    values.put(MediaStore.MediaColumns.MIME_TYPE, "text/plain");
                    values.put(MediaStore.MediaColumns.RELATIVE_PATH,
                            Environment.DIRECTORY_DOWNLOADS + "/PenGuru");
                    values.put(MediaStore.MediaColumns.IS_PENDING, 1);
                    Uri uri = getContentResolver().insert(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                    if (uri == null) {
                        return null;
                    }
                    try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                        if (out == null) {
                            getContentResolver().delete(uri, null, null);
                            return null;
                        }
                        out.write(bytes);
                    } catch (IOException error) {
                        getContentResolver().delete(uri, null, null);
                        return null;
                    }
                    values.clear();
                    values.put(MediaStore.MediaColumns.IS_PENDING, 0);
                    try {
                        getContentResolver().update(uri, values, null, null);
                    } catch (RuntimeException error) {
                        getContentResolver().delete(uri, null, null);
                        return null;
                    }
                    return "Downloads/PenGuru/" + mediaDisplayName(uri, safe);
                }
                File base = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (base == null) {
                    return null;
                }
                File dir = new File(base, "PenGuru");
                if (!dir.exists() && !dir.mkdirs()) {
                    return null;
                }
                File target = new File(dir, safe);
                try (FileOutputStream out = new FileOutputStream(target)) {
                    out.write(bytes);
                } catch (IOException error) {
                    return null;
                }
                return target.getAbsolutePath();
            } catch (RuntimeException error) {
                return null;
            }
        }

        @JavascriptInterface
        public boolean openExternal(String url) {
            if (url == null) {
                return false;
            }
            Uri uri = Uri.parse(url);
            String scheme = uri.getScheme();
            if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
                return false;
            }
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, uri));
                return true;
            } catch (RuntimeException unavailable) {
                return false;
            }
        }

        private String mediaDisplayName(Uri uri, String fallback) {
            try (Cursor cursor = getContentResolver().query(
                    uri, new String[]{MediaStore.MediaColumns.DISPLAY_NAME},
                    null, null, null)) {
                if (cursor != null && cursor.moveToFirst()) {
                    String name = cursor.getString(0);
                    if (name != null && !name.isEmpty()) {
                        return name;
                    }
                }
            } catch (RuntimeException ignored) {
                // The export succeeded; fall back to the requested name.
            }
            return fallback;
        }

        private String sanitizeFilename(String filename) {
            if (filename == null) {
                return "";
            }
            String safe = filename.replaceAll("[^A-Za-z0-9._-]", "_");
            while (safe.startsWith(".")) {
                safe = safe.substring(1);
            }
            return safe.length() > 80 ? safe.substring(0, 80) : safe;
        }
    }

    /* ----------------------------------------------------------- speech */

    private boolean ensureSpeechRecognizer() {
        if (speechRecognizer != null) {
            return true;
        }
        try {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
            return true;
        } catch (RuntimeException error) {
            speechRecognizer = null;
            return false;
        }
    }

    /**
     * Destroy the recognizer after every session. Reusing an instance that
     * ended in ERROR_CLIENT or was cancelled is the common source of a
     * microphone that appears to stay open forever.
     */
    private void releaseSpeechRecognizer() {
        SpeechRecognizer recognizer = speechRecognizer;
        speechRecognizer = null;
        if (recognizer == null) {
            return;
        }
        try {
            recognizer.cancel();
        } catch (RuntimeException ignored) {
            // already stopped
        }
        try {
            recognizer.destroy();
        } catch (RuntimeException ignored) {
            // already destroyed
        }
    }

    private Intent speechIntent(boolean preferOffline) {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, preferOffline);
        String language = speechLanguage;
        if (language == null || language.isEmpty()) {
            language = Locale.getDefault().toLanguageTag();
        }
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, language);
        return intent;
    }

    private void beginSpeech(final boolean wake) {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            pendingSpeech = true;
            pendingSpeechWake = wake;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, SPEECH_REQUEST);
            return;
        }
        pendingSpeech = false;
        // Cancel any previous foreground session immediately so its callbacks
        // cannot race the new one or surface a bogus client_error.
        final int requestToken = ++speechToken;
        speechRunning = false;
        releaseSpeechRecognizer();
        // The persistent SonarBird listener and this foreground session share
        // the one microphone Android exposes. Wait until the service has
        // actually destroyed its recognizer before creating ours; starting
        // immediately is what produced ERROR_RECOGNIZER_BUSY ("speech service
        // busy") when both paths overlapped.
        WakeWordService.pauseForActivity(() -> mainHandler.postDelayed(() -> {
            if (requestToken != speechToken || isFinishing()) {
                return;
            }
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                deliverSpeech("", wake, "microphone_permission_denied", requestToken);
                return;
            }
            if (!SpeechRecognizer.isRecognitionAvailable(this) || !ensureSpeechRecognizer()) {
                deliverSpeech("", wake, "speech_recognizer_unavailable", requestToken);
                return;
            }
            speechRetryCount = 0;
            speechPreferOffline = true;
            speechLanguage = "";
            startSpeechNow(wake);
        }, 420L));
    }

    private void restartSpeech(final boolean wake, long delayMillis) {
        speechRunning = false;
        releaseSpeechRecognizer();
        final int token = ++speechToken;
        // A busy/client error means the speech binder from the previous
        // session (usually SonarBird's recognizer) has not finished releasing.
        // Pause the service again and re-check before each retry instead of
        // immediately creating another recognizer.
        WakeWordService.pauseForActivity(() -> mainHandler.postDelayed(() -> {
            if (token != speechToken || isFinishing()) {
                return;
            }
            startSpeechNow(wake);
        }, delayMillis));
    }

    private void startSpeechNow(boolean wake) {
        if (!SpeechRecognizer.isRecognitionAvailable(this) || !ensureSpeechRecognizer()) {
            deliverSpeech("", wake, "speech_recognizer_unavailable", speechToken);
            return;
        }
        final int token = ++speechToken;
        speechWake = wake;
        speechRunning = true;
        speechRecognizer.setRecognitionListener(new PenGuruSpeechListener(token));
        try {
            speechRecognizer.startListening(speechIntent(speechPreferOffline));
        } catch (RuntimeException error) {
            deliverSpeech("", wake, "speech_start_failed", token);
            return;
        }
        // Native hard deadline: no matter what the speech service does, the
        // mic is cancelled and the UI is told the session ended.
        mainHandler.postDelayed(() -> {
            if (token != speechToken || !speechRunning) {
                return;
            }
            deliverSpeech("", wake, "speech_timeout", token);
        }, 16000L);
        // Ask a dictation session to finalize after ten seconds even if the
        // recognizer never reports end-of-speech. Wake sessions use the hard
        // deadline because the user may still be saying the phrase.
        if (!wake) {
            mainHandler.postDelayed(() -> {
                if (token != speechToken || !speechRunning || speechRecognizer == null) {
                    return;
                }
                try {
                    speechRecognizer.stopListening();
                } catch (RuntimeException ignored) {
                    // already finished
                }
            }, 10000L);
        }
    }

    private void deliverSpeech(final String text, final boolean wake,
                               final String error, final int token) {
        if (token != speechToken) {
            // A stop or a newer session superseded this callback.
            return;
        }
        speechRunning = false;
        releaseSpeechRecognizer();
        try {
            JSONObject result = new JSONObject();
            result.put("ok", error == null);
            if (error == null) {
                result.put("text", text == null ? "" : text);
                result.put("wake", wake);
            } else {
                result.put("error", error);
            }
            final String script = "window.__nuxelSpeechResult && window.__nuxelSpeechResult("
                    + result.toString() + ")";
            if (webView != null) {
                webView.post(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript(script, null);
                    }
                });
            }
        } catch (JSONException ignored) {
            // primitive values only
        }
        WakeWordService.resumeFromActivity();
    }

    private final class PenGuruSpeechListener implements RecognitionListener {
        private final int token;

        PenGuruSpeechListener(int token) {
            this.token = token;
        }

        @Override public void onReadyForSpeech(Bundle params) { }
        @Override public void onBeginningOfSpeech() { }
        @Override public void onRmsChanged(float rmsdB) { }
        @Override public void onBufferReceived(byte[] buffer) { }
        @Override public void onEvent(int eventType, Bundle params) { }
        @Override public void onPartialResults(Bundle partialResults) { }

        @Override
        public void onEndOfSpeech() {
            if (token != speechToken || !speechRunning || speechRecognizer == null) {
                return;
            }
            // Natural end of speech: request the final hypothesis instead of
            // waiting for a watchdog to cancel a recognizer that already
            // stopped producing audio.
            try {
                speechRecognizer.stopListening();
            } catch (RuntimeException ignored) {
                // already stopping
            }
        }

        @Override
        public void onError(int error) {
            if (token != speechToken || !speechRunning) {
                return;
            }
            final boolean transientBusy = error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY
                    || error == SpeechRecognizer.ERROR_CLIENT;
            // Busy/client errors are a hand-off race with the background
            // listener or the previous in-app session, so retry long enough
            // for Android to release the recognizer instead of surfacing the
            // old "wait a moment and tap again" message on the first tap.
            final int maxRetries = transientBusy ? 6 : 2;
            if (speechRetryCount < maxRetries && shouldRetrySpeech(error)) {
                // Offline-only recognition frequently fails with error 12/13
                // when no language pack is installed. Busy/client errors are
                // usually the previous recognizer still releasing. Retry with
                // a fresh instance, the normal recognizer and en-US fallback.
                speechRetryCount++;
                speechPreferOffline = false;
                if (error == SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE
                        || error == SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED
                        || error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY) {
                    speechLanguage = "en-US";
                }
                long delay = transientBusy
                        ? Math.min(2600L, 350L * speechRetryCount)
                        : 700L * speechRetryCount;
                restartSpeech(speechWake, delay);
                return;
            }
            deliverSpeech("", speechWake, speechErrorName(error), token);
        }

        @Override
        public void onResults(Bundle results) {
            if (token != speechToken || !speechRunning) {
                return;
            }
            ArrayList<String> matches = results == null ? null
                    : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            String text = matches == null || matches.isEmpty() ? "" : matches.get(0);
            deliverSpeech(text, speechWake,
                    text == null || text.trim().isEmpty() ? "no_speech_detected" : null, token);
        }
    }

    private static boolean shouldRetrySpeech(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
            case SpeechRecognizer.ERROR_NO_MATCH:
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                return false;
            default:
                return true;
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
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "no_speech_detected";
            case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED: return "language_not_supported";
            case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE: return "language_unavailable";
            default: return "speech_error_" + error;
        }
    }

    private final class PenGuruChromeClient extends WebChromeClient {
        @Override
        public void onPermissionRequest(final PermissionRequest request) {
            boolean wantsAudio = false;
            for (String resource : request.getResources()) {
                if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                    wantsAudio = true;
                }
            }
            if (!wantsAudio || request.getOrigin() == null
                    || !ASSET_HOST.equals(request.getOrigin().getHost())) {
                request.deny();
                return;
            }
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED) {
                request.grant(request.getResources());
                return;
            }
            if (pendingAudio != null) {
                pendingAudio.deny();
            }
            pendingAudio = request;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_REQUEST);
        }

        @Override
        public boolean onConsoleMessage(ConsoleMessage message) {
            if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
                Log.d(TAG, message.message() + " @" + message.lineNumber());
            }
            return true;
        }
    }

    private final class LocalAssetClient extends WebViewClient {
        @Override
        public void onPageFinished(WebView view, String url) {
            pageReady = true;
            flushPendingWakeCommands();
            mainHandler.postDelayed(MainActivity.this::runStartupChecks, 500L);
        }

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (uri == null || !ASSET_HOST.equals(uri.getHost())) {
                return null;
            }
            String path = uri.getPath();
            if (path == null || path.isEmpty() || "/".equals(path)) {
                path = START_PATH;
            }
            while (path.startsWith("/")) {
                path = path.substring(1);
            }
            if (path.isEmpty() || path.contains("..") || path.contains("\\")) {
                return notFound();
            }
            try {
                InputStream stream = getAssets().open("public/" + path);
                WebResourceResponse response = new WebResourceResponse(
                        mimeFor(path), "UTF-8", stream);
                Map<String, String> headers = new HashMap<>();
                headers.put("Cache-Control", "no-store");
                headers.put("X-Content-Type-Options", "nosniff");
                response.setResponseHeaders(headers);
                return response;
            } catch (IOException missing) {
                return notFound();
            }
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (uri == null) {
                return false;
            }
            if (ASSET_HOST.equals(uri.getHost())) {
                return false;
            }
            String scheme = uri.getScheme();
            if ("http".equals(scheme) || "https".equals(scheme)) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (RuntimeException ignored) {
                    // No browser installed; keep the app responsive.
                }
                return true;
            }
            return false;
        }

        private WebResourceResponse notFound() {
            Map<String, String> headers = new HashMap<>();
            headers.put("Cache-Control", "no-store");
            return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found",
                    headers, new ByteArrayInputStream(
                            "Not found".getBytes(StandardCharsets.UTF_8)));
        }
    }

    private static String mimeFor(String path) {
        String extension = MimeTypeMap.getFileExtensionFromUrl(path);
        if (extension != null && !extension.isEmpty()) {
            String mime = MimeTypeMap.getSingleton()
                    .getMimeTypeFromExtension(extension.toLowerCase());
            if (mime != null) {
                return mime;
            }
        }
        if (path.endsWith(".js") || path.endsWith(".mjs")) return "text/javascript";
        if (path.endsWith(".css")) return "text/css";
        if (path.endsWith(".json") || path.endsWith(".webmanifest")) return "application/json";
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".png")) return "image/png";
        if (path.endsWith(".svg")) return "image/svg+xml";
        return "application/octet-stream";
    }
}
