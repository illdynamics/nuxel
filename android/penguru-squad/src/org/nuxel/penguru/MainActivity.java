package org.nuxel.penguru;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.IntentFilter;
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
import android.os.StatFs;
import android.provider.MediaStore;
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
    private boolean speechRetryUsed;
    private boolean speechPreferOffline = true;

    private final ExecutorService downloadExecutor = Executors.newSingleThreadExecutor();
    private final Map<String, DownloadJob> downloads = new ConcurrentHashMap<>();

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
        downloadExecutor.shutdownNow();
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

    /* ------------------------------------------------------------ storage */

    private File storageDir(String name) {
        File dir = getExternalFilesDir(name);
        if (dir == null) {
            dir = new File(getFilesDir(), name);
        }
        if (!dir.exists() && !dir.mkdirs()) {
            Log.w(TAG, "Could not create storage directory " + dir);
        }
        return dir;
    }

    private static String safeRelative(String raw) {
        if (raw == null) {
            throw new IllegalArgumentException("missing path");
        }
        String path = raw.replace('\\', '/');
        while (path.startsWith("/")) {
            path = path.substring(1);
        }
        if (path.isEmpty() || path.contains("..") || path.indexOf('\0') >= 0) {
            throw new IllegalArgumentException("unsafe path");
        }
        return path;
    }

    private static File safeChild(File root, String relative) throws IOException {
        String clean = safeRelative(relative);
        File child = new File(root, clean);
        String rootPath = root.getCanonicalPath();
        String childPath = child.getCanonicalPath();
        if (!childPath.equals(rootPath) && !childPath.startsWith(rootPath + File.separator)) {
            throw new IOException("path escapes storage root");
        }
        return child;
    }

    private static void deleteRecursively(File file) {
        if (file == null || !file.exists()) {
            return;
        }
        File[] children = file.listFiles();
        if (children != null) {
            for (File child : children) {
                deleteRecursively(child);
            }
        }
        //noinspection ResultOfMethodCallIgnored
        file.delete();
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
                out.put("models_dir", storageDir(MODELS_DIR_NAME).getAbsolutePath());
                out.put("runtimes_dir", storageDir(RUNTIMES_DIR_NAME).getAbsolutePath());
                StatFs stat = new StatFs(getFilesDir().getAbsolutePath());
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
                out.put("models", storageDir(MODELS_DIR_NAME).getAbsolutePath());
                out.put("runtimes", storageDir(RUNTIMES_DIR_NAME).getAbsolutePath());
                out.put("exports", "Downloads/PenGuru");
                return out.toString();
            } catch (JSONException error) {
                return "{}";
            }
        }

        @JavascriptInterface
        public String startDownload(String specJson) {
            try {
                JSONObject spec = new JSONObject(specJson);
                String kind = spec.optString("kind", "model");
                if (!"model".equals(kind) && !"runtime".equals(kind)) {
                    return "";
                }
                String id = safeRelative(spec.optString("id", ""));
                JSONArray rawFiles = spec.optJSONArray("files");
                if (rawFiles == null || rawFiles.length() == 0) {
                    return "";
                }
                List<FileSpec> files = new ArrayList<>();
                long total = 0;
                for (int i = 0; i < rawFiles.length(); i++) {
                    JSONObject raw = rawFiles.getJSONObject(i);
                    FileSpec file = new FileSpec();
                    file.url = raw.optString("url", "");
                    file.path = safeRelative(raw.optString("path", ""));
                    file.sha256 = raw.optString("sha256", "");
                    file.size = raw.optLong("size", 0);
                    if (file.url.isEmpty()) {
                        return "";
                    }
                    total += Math.max(0, file.size);
                    files.add(file);
                }
                File base = "runtime".equals(kind)
                        ? storageDir(RUNTIMES_DIR_NAME) : storageDir(MODELS_DIR_NAME);
                File target = safeChild(base, id);
                String jobId = kind + "-" + id.replace('/', '-') + "-" + UUID.randomUUID().toString().substring(0, 8);
                DownloadJob job = new DownloadJob(jobId, kind, id, target, files, total,
                        spec.optString("extract", ""));
                downloads.put(jobId, job);
                downloadExecutor.execute(() -> runDownload(job));
                return jobId;
            } catch (Exception error) {
                Log.w(TAG, "startDownload rejected: " + error);
                return "";
            }
        }

        @JavascriptInterface
        public String downloadStatus(String jobId) {
            DownloadJob job = downloads.get(jobId);
            return job == null ? "" : job.toJson().toString();
        }

        @JavascriptInterface
        public boolean cancelDownload(String jobId) {
            DownloadJob job = downloads.get(jobId);
            if (job == null) {
                return false;
            }
            job.cancel = true;
            return true;
        }

        @JavascriptInterface
        public boolean isInstalled(String kind, String id) {
            try {
                File base = "runtime".equals(kind)
                        ? storageDir(RUNTIMES_DIR_NAME) : storageDir(MODELS_DIR_NAME);
                File target = safeChild(base, id);
                return new File(target, "installed.json").isFile();
            } catch (Exception error) {
                return false;
            }
        }

        @JavascriptInterface
        public String installedPath(String kind, String id) {
            try {
                File base = "runtime".equals(kind)
                        ? storageDir(RUNTIMES_DIR_NAME) : storageDir(MODELS_DIR_NAME);
                return safeChild(base, id).getAbsolutePath();
            } catch (Exception error) {
                return "";
            }
        }

        @JavascriptInterface
        public boolean deleteInstalled(String kind, String id) {
            try {
                File base = "runtime".equals(kind)
                        ? storageDir(RUNTIMES_DIR_NAME) : storageDir(MODELS_DIR_NAME);
                File target = safeChild(base, id);
                deleteRecursively(target);
                return !target.exists();
            } catch (Exception error) {
                return false;
            }
        }

        @JavascriptInterface
        public String listInstalled(String kind) {
            JSONArray out = new JSONArray();
            try {
                File base = "runtime".equals(kind)
                        ? storageDir(RUNTIMES_DIR_NAME) : storageDir(MODELS_DIR_NAME);
                collectInstalled(base, base, out);
            } catch (Exception error) {
                // Return the entries found so far.
            }
            return out.toString();
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
                cancelSpeechQuietly();
            });
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

    private static void collectInstalled(File root, File dir, JSONArray out) {
        File[] children = dir.listFiles();
        if (children == null) {
            return;
        }
        for (File child : children) {
            if (child.isDirectory()) {
                File marker = new File(child, "installed.json");
                if (marker.isFile()) {
                    try {
                        JSONObject entry = new JSONObject();
                        String path = child.getCanonicalPath();
                        String rootPath = root.getCanonicalPath();
                        entry.put("id", path.equals(rootPath) ? "" : path.substring(rootPath.length() + 1));
                        entry.put("path", path);
                        entry.put("installed_at", marker.lastModified());
                        out.put(entry);
                    } catch (Exception ignored) {
                        // skip unreadable entry
                    }
                }
                collectInstalled(root, child, out);
            }
        }
    }

    /* --------------------------------------------------------- downloads */

    private static final class FileSpec {
        String url;
        String path;
        String sha256;
        long size;
    }

    private static final class DownloadJob {
        final String jobId;
        final String kind;
        final String id;
        final File targetDir;
        final List<FileSpec> files;
        final String extract;
        final long total;
        volatile boolean cancel;
        volatile String state = "queued";
        volatile String detail = "";
        volatile double progress;
        volatile long received;

        DownloadJob(String jobId, String kind, String id, File targetDir,
                    List<FileSpec> files, long total, String extract) {
            this.jobId = jobId;
            this.kind = kind;
            this.id = id;
            this.targetDir = targetDir;
            this.files = files;
            this.total = total;
            this.extract = extract == null ? "" : extract;
        }

        JSONObject toJson() {
            JSONObject out = new JSONObject();
            try {
                out.put("job_id", jobId);
                out.put("kind", kind);
                out.put("id", id);
                out.put("state", state);
                out.put("detail", detail);
                out.put("progress", Math.max(0, Math.min(1, progress)));
                out.put("received_bytes", received);
                out.put("total_bytes", total);
                out.put("path", targetDir.getAbsolutePath());
            } catch (JSONException ignored) {
                // Values are all primitives; this cannot fail in practice.
            }
            return out;
        }
    }

    private static final class CancelledException extends IOException {
        CancelledException() {
            super("cancelled by owner");
        }
    }

    private void runDownload(DownloadJob job) {
        try {
            if (!job.targetDir.exists() && !job.targetDir.mkdirs()) {
                throw new IOException("cannot create " + job.targetDir);
            }
            job.state = "downloading";
            if (job.total > 0) {
                StatFs stat = new StatFs(job.targetDir.getAbsolutePath());
                long reserve = 256L * 1024 * 1024;
                if (stat.getAvailableBytes() < job.total + reserve) {
                    throw new IOException("Not enough free storage: need "
                            + (job.total + reserve) + " bytes, have "
                            + stat.getAvailableBytes());
                }
            }
            long completed = 0;
            for (FileSpec spec : job.files) {
                checkCancel(job);
                File dest = safeChild(job.targetDir, spec.path);
                File parent = dest.getParentFile();
                if (parent != null && !parent.exists() && !parent.mkdirs()) {
                    throw new IOException("cannot create " + parent);
                }
                job.detail = "Downloading " + spec.path;
                downloadOne(job, spec, dest, completed);
                completed += dest.length();
                job.received = completed;
                if (job.total > 0) {
                    job.progress = Math.min(0.99, completed / (double) job.total);
                }
            }
            job.state = "verifying";
            job.detail = "Verifying package";
            if ("tar.gz".equals(job.extract)) {
                File archive = safeChild(job.targetDir, job.files.get(0).path);
                job.detail = "Unpacking " + archive.getName();
                try (InputStream in = new GZIPInputStream(
                        new BufferedInputStream(new FileInputStream(archive)))) {
                    extractTar(job, in, job.targetDir);
                }
                //noinspection ResultOfMethodCallIgnored
                archive.delete();
            } else if ("zip".equals(job.extract)) {
                File archive = safeChild(job.targetDir, job.files.get(0).path);
                job.detail = "Unpacking " + archive.getName();
                try (ZipInputStream in = new ZipInputStream(
                        new BufferedInputStream(new FileInputStream(archive)))) {
                    extractZip(job, in, job.targetDir);
                }
                //noinspection ResultOfMethodCallIgnored
                archive.delete();
            }
            writeInstalledMarker(job);
            job.progress = 1.0;
            job.state = "ready";
            job.detail = "Installed at " + job.targetDir.getAbsolutePath();
        } catch (CancelledException cancelled) {
            job.state = "cancelled";
            job.detail = "Cancelled";
        } catch (Exception error) {
            job.state = "error";
            job.detail = String.valueOf(error.getMessage());
            Log.w(TAG, "download failed: " + error);
        }
    }

    private void downloadOne(DownloadJob job, FileSpec spec, File dest, long completed) throws IOException {
        File part = new File(dest.getAbsolutePath() + ".part");
        long have = part.isFile() ? part.length() : 0;
        HttpURLConnection connection = (HttpURLConnection) new URL(spec.url).openConnection();
        try {
            connection.setConnectTimeout(30000);
            connection.setReadTimeout(30000);
            connection.setInstanceFollowRedirects(true);
            connection.setRequestProperty("User-Agent", "PenGuru-Squad-Android/0.9");
            connection.setRequestProperty("Accept-Encoding", "identity");
            if (have > 0) {
                connection.setRequestProperty("Range", "bytes=" + have + "-");
            }
            int code = connection.getResponseCode();
            if (code == 416 && spec.size > 0 && have == spec.size) {
                finalizePart(part, dest);
                return;
            }
            if (code == 200 && have > 0) {
                have = 0;
                //noinspection ResultOfMethodCallIgnored
                part.delete();
            }
            if (code != 200 && code != 206) {
                throw new IOException("HTTP " + code + " for " + spec.url);
            }
            boolean append = code == 206 && part.isFile();
            try (InputStream in = new BufferedInputStream(connection.getInputStream());
                 FileOutputStream out = new FileOutputStream(part, append)) {
                byte[] buffer = new byte[1 << 18];
                long written = append ? part.length() : 0;
                int read;
                long lastUpdate = 0;
                while ((read = in.read(buffer)) > 0) {
                    checkCancel(job);
                    out.write(buffer, 0, read);
                    written += read;
                    long now = System.currentTimeMillis();
                    if (now - lastUpdate > 250) {
                        lastUpdate = now;
                        job.received = completed + written;
                        if (job.total > 0) {
                            job.progress = Math.min(0.99, job.received / (double) job.total);
                        }
                    }
                }
            }
        } finally {
            connection.disconnect();
        }
        checkCancel(job);
        if (spec.size > 0 && part.length() != spec.size) {
            throw new IOException("incomplete download for " + spec.path
                    + " (" + part.length() + " of " + spec.size + " bytes)");
        }
        if (!spec.sha256.isEmpty()) {
            job.detail = "Verifying SHA-256 for " + spec.path;
            String actual = sha256Hex(job, part);
            if (!actual.equalsIgnoreCase(spec.sha256)) {
                //noinspection ResultOfMethodCallIgnored
                part.delete();
                throw new IOException("SHA-256 mismatch for " + spec.path);
            }
        }
        finalizePart(part, dest);
    }

    private static void finalizePart(File part, File dest) throws IOException {
        if (dest.exists() && !dest.delete()) {
            throw new IOException("cannot replace " + dest);
        }
        if (!part.renameTo(dest)) {
            throw new IOException("cannot move " + part + " to " + dest);
        }
    }

    private static void checkCancel(DownloadJob job) throws CancelledException {
        if (job.cancel || Thread.currentThread().isInterrupted()) {
            throw new CancelledException();
        }
    }

    private static String sha256Hex(DownloadJob job, File file) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream in = new BufferedInputStream(new FileInputStream(file))) {
                byte[] buffer = new byte[1 << 20];
                int read;
                while ((read = in.read(buffer)) > 0) {
                    checkCancel(job);
                    digest.update(buffer, 0, read);
                }
            }
            StringBuilder text = new StringBuilder();
            for (byte value : digest.digest()) {
                text.append(String.format(Locale.US, "%02x", value & 0xff));
            }
            return text.toString();
        } catch (java.security.NoSuchAlgorithmException error) {
            throw new IOException("SHA-256 unavailable", error);
        }
    }

    private void writeInstalledMarker(DownloadJob job) throws IOException {
        try {
            JSONObject marker = new JSONObject();
            marker.put("id", job.id);
            marker.put("kind", job.kind);
            marker.put("installed_at", System.currentTimeMillis());
            marker.put("path", job.targetDir.getAbsolutePath());
            JSONArray files = new JSONArray();
            for (FileSpec spec : job.files) {
                files.put(spec.path);
            }
            marker.put("archives", files);
            File tmp = new File(job.targetDir, "installed.json.tmp");
            try (FileOutputStream out = new FileOutputStream(tmp)) {
                out.write(marker.toString().getBytes(StandardCharsets.UTF_8));
            }
            File markerFile = new File(job.targetDir, "installed.json");
            //noinspection ResultOfMethodCallIgnored
            markerFile.delete();
            if (!tmp.renameTo(markerFile)) {
                throw new IOException("cannot write installed marker");
            }
        } catch (JSONException error) {
            throw new IOException("cannot encode installed marker", error);
        }
    }

    /* ------------------------------------------------------- tar/zip unpack */

    private static void extractTar(DownloadJob job, InputStream in, File dest) throws IOException {
        byte[] header = new byte[512];
        String longName = null;
        while (true) {
            int read = readFully(in, header, 0, header.length);
            if (read == 0) {
                break;
            }
            if (read < header.length) {
                throw new IOException("truncated tar header");
            }
            boolean empty = true;
            for (byte value : header) {
                if (value != 0) {
                    empty = false;
                    break;
                }
            }
            if (empty) {
                break;
            }
            String name = cString(header, 0, 100);
            String prefix = cString(header, 345, 155);
            if (!prefix.isEmpty()) {
                name = prefix + "/" + name;
            }
            long size = parseOctal(header, 124, 12);
            char type = (char) (header[156] & 0xff);
            if (type == 'L') {
                longName = readString(in, size);
                skipPadding(in, size);
                continue;
            }
            if (type == 'x' || type == 'g') {
                skipFully(in, size);
                skipPadding(in, size);
                continue;
            }
            if (longName != null) {
                name = longName;
                longName = null;
            }
            if (type == '5') {
                File dir = safeChild(dest, name);
                if (!dir.exists() && !dir.mkdirs()) {
                    throw new IOException("cannot create " + dir);
                }
                skipFully(in, size);
            } else if (type == '0' || type == 0 || type == '7') {
                File out = safeChild(dest, name);
                File parent = out.getParentFile();
                if (parent != null && !parent.exists() && !parent.mkdirs()) {
                    throw new IOException("cannot create " + parent);
                }
                try (OutputStream stream = new BufferedOutputStream(new FileOutputStream(out))) {
                    copyExactly(job, in, stream, size);
                }
                // Best effort: the extracted CLI binaries are useful when the
                // platform allows execution from an app-owned location.
                //noinspection ResultOfMethodCallIgnored
                out.setExecutable(true, false);
            } else {
                skipFully(in, size);
            }
            skipPadding(in, size);
        }
    }

    private static void extractZip(DownloadJob job, ZipInputStream in, File dest) throws IOException {
        ZipEntry entry;
        while ((entry = in.getNextEntry()) != null) {
            checkCancel(job);
            String name = entry.getName();
            if (name.endsWith("/")) {
                File dir = safeChild(dest, name);
                if (!dir.exists() && !dir.mkdirs()) {
                    throw new IOException("cannot create " + dir);
                }
                continue;
            }
            File out = safeChild(dest, name);
            File parent = out.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                throw new IOException("cannot create " + parent);
            }
            try (OutputStream stream = new BufferedOutputStream(new FileOutputStream(out))) {
                byte[] buffer = new byte[1 << 18];
                int read;
                while ((read = in.read(buffer)) > 0) {
                    checkCancel(job);
                    stream.write(buffer, 0, read);
                }
            }
            in.closeEntry();
        }
    }

    private static int readFully(InputStream in, byte[] buffer, int offset, int length) throws IOException {
        int total = 0;
        while (total < length) {
            int read = in.read(buffer, offset + total, length - total);
            if (read <= 0) {
                break;
            }
            total += read;
        }
        return total;
    }

    private static void copyExactly(DownloadJob job, InputStream in, OutputStream out, long size)
            throws IOException {
        byte[] buffer = new byte[1 << 18];
        long remaining = size;
        while (remaining > 0) {
            checkCancel(job);
            int read = in.read(buffer, 0, (int) Math.min(buffer.length, remaining));
            if (read <= 0) {
                throw new IOException("truncated archive");
            }
            out.write(buffer, 0, read);
            remaining -= read;
        }
    }

    private static void skipFully(InputStream in, long size) throws IOException {
        long remaining = size;
        byte[] buffer = new byte[8192];
        while (remaining > 0) {
            int read = in.read(buffer, 0, (int) Math.min(buffer.length, remaining));
            if (read <= 0) {
                throw new IOException("truncated archive");
            }
            remaining -= read;
        }
    }

    private static void skipPadding(InputStream in, long size) throws IOException {
        long padding = (512 - (size % 512)) % 512;
        if (padding > 0) {
            skipFully(in, padding);
        }
    }

    private static String readString(InputStream in, long size) throws IOException {
        if (size <= 0 || size > 8192) {
            throw new IOException("invalid long name");
        }
        byte[] data = new byte[(int) size];
        if (readFully(in, data, 0, data.length) != data.length) {
            throw new IOException("truncated long name");
        }
        int end = data.length;
        while (end > 0 && data[end - 1] == 0) {
            end--;
        }
        return new String(data, 0, end, StandardCharsets.UTF_8);
    }

    private static String cString(byte[] data, int offset, int length) {
        int end = offset;
        int limit = Math.min(data.length, offset + length);
        while (end < limit && data[end] != 0) {
            end++;
        }
        return new String(data, offset, end - offset, StandardCharsets.UTF_8);
    }

    private static long parseOctal(byte[] data, int offset, int length) {
        long value = 0;
        int end = Math.min(data.length, offset + length);
        int index = offset;
        while (index < end && (data[index] == 0 || data[index] == ' ')) {
            index++;
        }
        while (index < end) {
            int digit = data[index] & 0xff;
            if (digit < '0' || digit > '7') {
                break;
            }
            value = (value << 3) + (digit - '0');
            index++;
        }
        return value;
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

    private void cancelSpeechQuietly() {
        if (speechRecognizer == null) {
            return;
        }
        try {
            speechRecognizer.cancel();
        } catch (RuntimeException ignored) {
            // already stopped
        }
    }

    private static Intent speechIntent(boolean preferOffline) {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        if (preferOffline) {
            intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
        }
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag());
        return intent;
    }

    private void beginSpeech(boolean wake) {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            pendingSpeech = true;
            pendingSpeechWake = wake;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, SPEECH_REQUEST);
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this) || !ensureSpeechRecognizer()) {
            deliverSpeech("", wake, "speech_recognizer_unavailable", speechToken);
            return;
        }
        speechRetryUsed = false;
        speechPreferOffline = true;
        if (speechRunning) {
            // Reusing a recognizer that has not finished its previous session
            // is the usual source of ERROR_CLIENT. Finish it, then start fresh.
            speechRunning = false;
            cancelSpeechQuietly();
            restartSpeech(wake, 350);
            return;
        }
        startSpeechNow(wake);
    }

    private void restartSpeech(final boolean wake, long delayMillis) {
        speechRunning = false;
        cancelSpeechQuietly();
        final int token = ++speechToken;
        mainHandler.postDelayed(() -> {
            if (token != speechToken) {
                return;
            }
            startSpeechNow(wake);
        }, delayMillis);
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
        if (!wake) {
            // The UI calls this the 5-second button; ask the recognizer to
            // finalize after five seconds instead of waiting for a timeout.
            mainHandler.postDelayed(() -> {
                if (token != speechToken || !speechRunning || speechRecognizer == null) {
                    return;
                }
                try {
                    speechRecognizer.stopListening();
                } catch (RuntimeException ignored) {
                    // already finished
                }
            }, 5000);
        }
    }

    private void deliverSpeech(final String text, final boolean wake,
                               final String error, final int token) {
        if (token != speechToken) {
            // A stop or a newer session superseded this callback.
            return;
        }
        speechRunning = false;
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
        @Override public void onEndOfSpeech() { }
        @Override public void onEvent(int eventType, Bundle params) { }
        @Override public void onPartialResults(Bundle partialResults) { }

        @Override
        public void onError(int error) {
            if (token != speechToken || !speechRunning) {
                return;
            }
            if (!speechRetryUsed
                    && (error == SpeechRecognizer.ERROR_CLIENT
                    || error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY)) {
                // Many bundled recognizers reject EXTRA_PREFER_OFFLINE or need
                // a moment after cancel(). Retry once without the offline hint.
                speechRetryUsed = true;
                speechPreferOffline = false;
                restartSpeech(speechWake, 400);
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
            deliverSpeech(text, speechWake, text.isEmpty() ? "no_speech_detected" : null, token);
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
