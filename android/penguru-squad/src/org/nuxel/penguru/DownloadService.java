package org.nuxel.penguru;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.StatFs;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
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

/**
 * Foreground service that owns model/runtime downloads and archive extraction.
 *
 * The service holds a partial wake lock and a Wi-Fi lock, so turning the screen
 * off or leaving the WebView no longer pauses multi-gigabyte downloads. The
 * WebView only starts jobs and polls their state; all network and unpacking
 * work is independent of the Activity lifecycle.
 */
public class DownloadService extends Service {
    private static final String TAG = "PenGuruDownload";

    public static final String ACTION_START = "org.nuxel.penguru.action.DOWNLOAD_START";
    public static final String ACTION_CANCEL = "org.nuxel.penguru.action.DOWNLOAD_CANCEL";
    public static final String EXTRA_JOB_ID = "download_job_id";
    public static final String EXTRA_SPEC = "download_spec";

    private static final String CHANNEL_ID = "penguru_downloads";
    private static final int NOTIFICATION_ID = 8805;
    private static final String PREFS = "penguru_download_jobs";
    private static final String PREF_JOB_PREFIX = "job_";

    private static final Map<String, DownloadJob> JOBS = new ConcurrentHashMap<>();
    private static volatile DownloadService instance;

    private final ExecutorService executor = Executors.newFixedThreadPool(2);
    private final Handler handler = new Handler(Looper.getMainLooper());
    private PowerManager.WakeLock wakeLock;
    private WifiManager.WifiLock wifiLock;
    private volatile long lastNotificationAt;

    /* --------------------------------------------------------------- API */

    /** Validate and queue a download. Returns an empty string on rejection. */
    public static String start(Context context, String specJson) {
        try {
            JSONObject spec = new JSONObject(specJson);
            DownloadJob job = buildJob(context, spec);
            DownloadJob active = findActive(job.kind, job.id);
            if (active != null) {
                return active.jobId;
            }
            JOBS.put(job.jobId, job);
            spec.put("job_id", job.jobId);
            context.getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putString(PREF_JOB_PREFIX + job.jobId, spec.toString())
                    .apply();
            Intent intent = new Intent(context, DownloadService.class)
                    .setAction(ACTION_START)
                    .putExtra(EXTRA_JOB_ID, job.jobId);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
            return job.jobId;
        } catch (Exception error) {
            Log.w(TAG, "startDownload rejected: " + error);
            return "";
        }
    }

    /** Re-queue jobs that were interrupted by a process death or app update. */
    public static void resumePending(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, MODE_PRIVATE);
        Map<String, ?> stored = prefs.getAll();
        for (Map.Entry<String, ?> entry : stored.entrySet()) {
            if (!entry.getKey().startsWith(PREF_JOB_PREFIX) || !(entry.getValue() instanceof String)) {
                continue;
            }
            String raw = (String) entry.getValue();
            try {
                JSONObject spec = new JSONObject(raw);
                String jobId = spec.optString("job_id", "");
                if (jobId.isEmpty()) {
                    jobId = entry.getKey().substring(PREF_JOB_PREFIX.length());
                    spec.put("job_id", jobId);
                }
                DownloadJob existing = JOBS.get(jobId);
                if (existing != null && !isFinished(existing.state)) {
                    continue;
                }
                if (isInstalled(context, spec.optString("kind", "model"),
                        spec.optString("id", ""))) {
                    prefs.edit().remove(entry.getKey()).apply();
                    continue;
                }
                DownloadJob job = buildJob(context, spec);
                JOBS.put(job.jobId, job);
                Intent intent = new Intent(context, DownloadService.class)
                        .setAction(ACTION_START)
                        .putExtra(EXTRA_JOB_ID, job.jobId);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent);
                } else {
                    context.startService(intent);
                }
            } catch (Exception error) {
                Log.w(TAG, "Could not resume download: " + error);
            }
        }
    }

    private static DownloadJob findActive(String kind, String id) {
        for (DownloadJob job : JOBS.values()) {
            if (!isFinished(job.state) && job.kind.equals(kind) && job.id.equals(id)) {
                return job;
            }
        }
        return null;
    }

    public static String statusJson(String jobId) {
        DownloadJob job = JOBS.get(jobId);
        return job == null ? "" : job.toJson().toString();
    }

    public static String activeJobsJson() {
        JSONArray out = new JSONArray();
        for (DownloadJob job : JOBS.values()) {
            if (!isFinished(job.state)) {
                out.put(job.toJson());
            }
        }
        return out.toString();
    }

    public static boolean cancel(Context context, String jobId) {
        DownloadJob job = JOBS.get(jobId);
        if (job != null) {
            job.cancel = true;
            return true;
        }
        // A queued spec may survive a process restart but not yet be running.
        SharedPreferences prefs = context.getSharedPreferences(PREFS, MODE_PRIVATE);
        if (prefs.contains(PREF_JOB_PREFIX + jobId)) {
            prefs.edit().remove(PREF_JOB_PREFIX + jobId).apply();
            return true;
        }
        return false;
    }

    public static boolean isInstalled(Context context, String kind, String id) {
        try {
            File target = PenGuruStorage.targetDir(context, kind, id);
            if (PenGuruStorage.hasMarker(target) && markerLooksValid(target)) {
                return true;
            }
            if ("runtime".equals(kind)
                    && PenGuruStorage.looksLikeExtractedRuntime(kind, id, target)) {
                writeRepairMarker(target, kind, id, new ArrayList<>(), true);
                return true;
            }
            return false;
        } catch (Exception error) {
            return false;
        }
    }

    /**
     * Checks each expected file's path and byte length so a reinstall finds a
     * complete previous download even if the marker write was interrupted.
     */
    public static boolean isInstalledWithFiles(Context context, String kind, String id,
                                               String filesJson) {
        try {
            File target = PenGuruStorage.targetDir(context, kind, id);
            if (PenGuruStorage.hasMarker(target) && markerLooksValid(target)) {
                return true;
            }
            if ("runtime".equals(kind)) {
                if (PenGuruStorage.looksLikeExtractedRuntime(kind, id, target)) {
                    writeRepairMarker(target, kind, id, new ArrayList<>(), true);
                    return true;
                }
                return false;
            }
            List<PenGuruStorage.FileExpectation> expected = parseExpectations(filesJson);
            if (expected != null && PenGuruStorage.expectedFilesPresent(target, expected)) {
                writeRepairMarker(target, kind, id, expected, false);
                return true;
            }
            return false;
        } catch (Exception error) {
            return false;
        }
    }

    public static String installedPath(Context context, String kind, String id) {
        return PenGuruStorage.installedPath(context, kind, id);
    }

    public static boolean deleteInstalled(Context context, String kind, String id) {
        try {
            File target = PenGuruStorage.targetDir(context, kind, id);
            PenGuruStorage.deleteRecursively(target);
            return !target.exists();
        } catch (Exception error) {
            return false;
        }
    }

    public static String listInstalled(Context context, String kind) {
        JSONArray out = new JSONArray();
        try {
            File base = "runtime".equals(kind)
                    ? PenGuruStorage.dir(context, PenGuruStorage.RUNTIMES_DIR_NAME)
                    : PenGuruStorage.dir(context, PenGuruStorage.MODELS_DIR_NAME);
            collectInstalled(base, base, out);
        } catch (Exception error) {
            // Return the entries found so far.
        }
        return out.toString();
    }

    private static void collectInstalled(File root, File dir, JSONArray out) {
        File[] children = dir.listFiles();
        if (children == null) {
            return;
        }
        for (File child : children) {
            if (!child.isDirectory()) {
                continue;
            }
            if (PenGuruStorage.hasMarker(child)) {
                try {
                    JSONObject entry = new JSONObject();
                    String path = child.getCanonicalPath();
                    String rootPath = root.getCanonicalPath();
                    entry.put("id", path.equals(rootPath) ? "" : path.substring(rootPath.length() + 1));
                    entry.put("path", path);
                    entry.put("installed_at", new File(child, "installed.json").lastModified());
                    out.put(entry);
                } catch (Exception ignored) {
                    // skip unreadable entry
                }
            }
            collectInstalled(root, child, out);
        }
    }

    /* --------------------------------------------------------- lifecycle */

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        createChannel();
        acquireLocks();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_CANCEL.equals(intent.getAction())) {
            String jobId = intent.getStringExtra(EXTRA_JOB_ID);
            DownloadJob job = jobId == null ? null : JOBS.get(jobId);
            if (job != null) {
                job.cancel = true;
            }
            return START_STICKY;
        }
        if (!startForegroundSafely("Preparing on-device download…")) {
            return START_NOT_STICKY;
        }
        if (intent == null) {
            resumePending(this);
            return START_STICKY;
        }
        String jobId = intent.getStringExtra(EXTRA_JOB_ID);
        DownloadJob job = jobId == null ? null : JOBS.get(jobId);
        if (job == null && jobId != null) {
            job = loadStoredJob(jobId);
            if (job != null) {
                JOBS.put(job.jobId, job);
            }
        }
        if (job == null && intent.hasExtra(EXTRA_SPEC)) {
            // Also accepts a direct spec (used by adb/diagnostics and by
            // service restarts that only persisted the request payload).
            try {
                JSONObject spec = new JSONObject(intent.getStringExtra(EXTRA_SPEC));
                job = buildJob(this, spec);
                spec.put("job_id", job.jobId);
                getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                        .putString(PREF_JOB_PREFIX + job.jobId, spec.toString())
                        .apply();
                JOBS.put(job.jobId, job);
            } catch (Exception error) {
                Log.w(TAG, "invalid download spec: " + error);
            }
        }
        if (job == null) {
            maybeStop();
            return START_STICKY;
        }
        startJob(job);
        return START_STICKY;
    }

    private void startJob(final DownloadJob job) {
        if (isFinished(job.state)) {
            maybeStop();
            return;
        }
        job.state = "queued";
        executor.execute(() -> runDownload(job));
        updateNotification(true);
    }

    private DownloadJob loadStoredJob(String jobId) {
        String raw = getSharedPreferences(PREFS, MODE_PRIVATE)
                .getString(PREF_JOB_PREFIX + jobId, "");
        if (raw == null || raw.isEmpty()) {
            return null;
        }
        try {
            JSONObject spec = new JSONObject(raw);
            return buildJob(this, spec);
        } catch (Exception error) {
            return null;
        }
    }

    @Override
    public void onDestroy() {
        instance = null;
        releaseLocks();
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void maybeStop() {
        handler.post(() -> {
            for (DownloadJob job : JOBS.values()) {
                if (!isFinished(job.state)) {
                    return;
                }
            }
            releaseLocks();
            stopForeground(true);
            stopSelf();
        });
    }

    private static boolean isFinished(String state) {
        return "ready".equals(state) || "error".equals(state)
                || "cancelled".equals(state) || "quarantined".equals(state);
    }

    /* ------------------------------------------------------------ locking */

    private void acquireLocks() {
        try {
            PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
            if (power != null) {
                wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "PenGuru:Downloads");
                wakeLock.setReferenceCounted(false);
                wakeLock.acquire();
            }
        } catch (RuntimeException error) {
            wakeLock = null;
        }
        try {
            WifiManager wifi = (WifiManager) getApplicationContext()
                    .getSystemService(Context.WIFI_SERVICE);
            if (wifi != null) {
                wifiLock = wifi.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF,
                        "PenGuru:Downloads");
                wifiLock.setReferenceCounted(false);
                wifiLock.acquire();
            }
        } catch (RuntimeException error) {
            wifiLock = null;
        }
    }

    private void releaseLocks() {
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
        if (wifiLock != null) {
            try {
                if (wifiLock.isHeld()) {
                    wifiLock.release();
                }
            } catch (RuntimeException ignored) {
                // already released
            }
            wifiLock = null;
        }
    }

    /* ------------------------------------------------------- notification */

    private void createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "PenGuru downloads", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Keeps model downloads and runtime installation running with the screen off.");
        channel.setShowBadge(false);
        channel.setSound(null, null);
        manager.createNotificationChannel(channel);
    }

    private boolean startForegroundSafely(String text) {
        try {
            Notification notification = buildNotification(text);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
            return true;
        } catch (RuntimeException error) {
            Log.w(TAG, "startForeground failed: " + error);
            return false;
        }
    }

    private Notification buildNotification(String text) {
        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent content = PendingIntent.getActivity(this, 8806, open, flags);
        Notification.Builder builder = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("PenGuru is downloading")
                .setContentText(text)
                .setSmallIcon(R.drawable.ic_stat_penguru)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setContentIntent(content)
                .setCategory(Notification.CATEGORY_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.setColor(0xFF0B1422);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
        }
        double progress = aggregateProgress();
        if (progress > 0 && progress < 1) {
            builder.setProgress(1000, (int) Math.round(progress * 1000), false);
        }
        return builder.build();
    }

    private double aggregateProgress() {
        double total = 0;
        int count = 0;
        for (DownloadJob job : JOBS.values()) {
            if (!isFinished(job.state)) {
                total += Math.max(0, Math.min(1, job.progress));
                count++;
            }
        }
        return count == 0 ? 0 : total / count;
    }

    private void updateNotification(boolean force) {
        long now = System.currentTimeMillis();
        if (!force && now - lastNotificationAt < 700L) {
            return;
        }
        lastNotificationAt = now;
        String text = "Preparing on-device download…";
        DownloadJob latest = null;
        for (DownloadJob job : JOBS.values()) {
            if (!isFinished(job.state)) {
                latest = job;
            }
        }
        if (latest != null) {
            text = latest.detail == null || latest.detail.isEmpty()
                    ? (latest.state + " · " + Math.round(latest.progress * 100) + "%")
                    : latest.detail + " · " + Math.round(latest.progress * 100) + "%";
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

    /* ---------------------------------------------------------- downloads */

    private static final class FileSpec {
        String url;
        String path;
        String sha256;
        long size;
    }

    static final class DownloadJob {
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

    private static DownloadJob buildJob(Context context, JSONObject spec) throws Exception {
        String kind = spec.optString("kind", "model");
        if (!"model".equals(kind) && !"runtime".equals(kind)) {
            throw new IllegalArgumentException("invalid kind");
        }
        String id = PenGuruStorage.safeRelative(spec.optString("id", ""));
        JSONArray rawFiles = spec.optJSONArray("files");
        if (rawFiles == null || rawFiles.length() == 0) {
            throw new IllegalArgumentException("no files");
        }
        List<FileSpec> files = new ArrayList<>();
        long total = 0;
        for (int i = 0; i < rawFiles.length(); i++) {
            JSONObject raw = rawFiles.getJSONObject(i);
            FileSpec file = new FileSpec();
            file.url = raw.optString("url", "");
            file.path = PenGuruStorage.safeRelative(raw.optString("path", ""));
            file.sha256 = raw.optString("sha256", "");
            file.size = raw.optLong("size", 0);
            if (file.url.isEmpty()) {
                throw new IllegalArgumentException("missing url");
            }
            total += Math.max(0, file.size);
            files.add(file);
        }
        File target = PenGuruStorage.targetDir(context, kind, id);
        String jobId = spec.optString("job_id", "");
        if (jobId.isEmpty()) {
            jobId = kind + "-" + id.replace('/', '-') + "-"
                    + UUID.randomUUID().toString().substring(0, 8);
        }
        return new DownloadJob(jobId, kind, id, target, files, total,
                spec.optString("extract", ""));
    }

    private FileSpec currentSpec(DownloadJob job) {
        return job.files.get(0);
    }

    private void runDownload(DownloadJob job) {
        try {
            if (!job.targetDir.exists() && !job.targetDir.mkdirs()) {
                throw new IOException("cannot create " + job.targetDir);
            }
            if (alreadyComplete(job)) {
                job.progress = 1.0;
                job.state = "ready";
                job.detail = "Already installed at " + job.targetDir.getAbsolutePath();
                persistFinished(job);
                updateNotification(true);
                maybeStop();
                return;
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
                File dest = PenGuruStorage.safeChild(job.targetDir, spec.path);
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
                updateNotification(false);
            }
            job.state = "verifying";
            job.detail = "Verifying package";
            updateNotification(true);
            if ("tar.gz".equals(job.extract)) {
                File archive = PenGuruStorage.safeChild(job.targetDir, currentSpec(job).path);
                job.detail = "Unpacking " + archive.getName();
                try (InputStream in = new GZIPInputStream(
                        new BufferedInputStream(new FileInputStream(archive)))) {
                    extractTar(job, in, job.targetDir);
                }
                //noinspection ResultOfMethodCallIgnored
                archive.delete();
            } else if ("zip".equals(job.extract)) {
                File archive = PenGuruStorage.safeChild(job.targetDir, currentSpec(job).path);
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
            persistFinished(job);
        } catch (CancelledException cancelled) {
            job.state = "cancelled";
            job.detail = "Cancelled";
            persistFinished(job);
        } catch (Exception error) {
            job.state = "error";
            job.detail = String.valueOf(error.getMessage());
            Log.w(TAG, "download failed: " + error);
            persistFinished(job);
        } finally {
            updateNotification(true);
            maybeStop();
        }
    }

    private boolean alreadyComplete(DownloadJob job) {
        if (PenGuruStorage.hasMarker(job.targetDir) && markerLooksValid(job.targetDir)) {
            return true;
        }
        if ("runtime".equals(job.kind)) {
            return PenGuruStorage.looksLikeExtractedRuntime(job.kind, job.id, job.targetDir);
        }
        List<PenGuruStorage.FileExpectation> expected = new ArrayList<>();
        for (FileSpec spec : job.files) {
            expected.add(new PenGuruStorage.FileExpectation(spec.path, spec.size));
        }
        return PenGuruStorage.expectedFilesPresent(job.targetDir, expected);
    }

    private void persistFinished(DownloadJob job) {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .remove(PREF_JOB_PREFIX + job.jobId)
                .apply();
    }

    private void downloadOne(DownloadJob job, FileSpec spec, File dest, long completed)
            throws IOException {
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
                        updateNotification(false);
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
            updateNotification(true);
            String actual = PenGuruStorage.sha256Hex(part, () -> checkCancel(job));
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

    private void writeInstalledMarker(DownloadJob job) throws IOException {
        List<PenGuruStorage.FileExpectation> files = new ArrayList<>();
        for (FileSpec spec : job.files) {
            files.add(new PenGuruStorage.FileExpectation(spec.path, spec.size));
        }
        writeMarker(job.targetDir, job.kind, job.id, files,
                "tar.gz".equals(job.extract) || "zip".equals(job.extract));
    }

    private static void writeRepairMarker(File targetDir, String kind, String id,
                                          List<PenGuruStorage.FileExpectation> files,
                                          boolean extracted) {
        try {
            writeMarker(targetDir, kind, id, files, extracted);
        } catch (IOException error) {
            Log.w(TAG, "Could not write repaired marker: " + error);
        }
    }

    private static void writeMarker(File targetDir, String kind, String id,
                                    List<PenGuruStorage.FileExpectation> files,
                                    boolean extracted) throws IOException {
        try {
            JSONObject marker = new JSONObject();
            marker.put("id", id);
            marker.put("kind", kind);
            marker.put("installed_at", System.currentTimeMillis());
            marker.put("path", targetDir.getAbsolutePath());
            marker.put("extracted", extracted);
            JSONArray list = new JSONArray();
            if (files != null) {
                for (PenGuruStorage.FileExpectation spec : files) {
                    JSONObject entry = new JSONObject();
                    entry.put("path", spec.path);
                    entry.put("size", spec.size);
                    list.put(entry);
                }
            }
            marker.put("files", list);
            File tmp = new File(targetDir, "installed.json.tmp");
            try (FileOutputStream out = new FileOutputStream(tmp)) {
                out.write(marker.toString().getBytes(StandardCharsets.UTF_8));
            }
            File markerFile = new File(targetDir, "installed.json");
            //noinspection ResultOfMethodCallIgnored
            markerFile.delete();
            if (!tmp.renameTo(markerFile)) {
                throw new IOException("cannot write installed marker");
            }
        } catch (JSONException error) {
            throw new IOException("cannot encode installed marker", error);
        }
    }

    private static boolean markerLooksValid(File targetDir) {
        File markerFile = new File(targetDir, "installed.json");
        if (!markerFile.isFile()) {
            return false;
        }
        try {
            String raw = readSmallFile(markerFile);
            JSONObject marker = new JSONObject(raw);
            String kind = marker.optString("kind", "model");
            if ("runtime".equals(kind) || marker.optBoolean("extracted", false)) {
                return true;
            }
            JSONArray files = marker.optJSONArray("files");
            if (files == null || files.length() == 0) {
                // Marker from an older build: trust it rather than forcing a
                // multi-gigabyte re-download.
                return true;
            }
            for (int i = 0; i < files.length(); i++) {
                JSONObject entry = files.getJSONObject(i);
                String path = entry.optString("path", "");
                long size = entry.optLong("size", 0);
                if (path.isEmpty()) {
                    continue;
                }
                File file;
                try {
                    file = PenGuruStorage.safeChild(targetDir, path);
                } catch (IOException error) {
                    return false;
                }
                if (!file.isFile() || (size > 0 && file.length() != size)) {
                    return false;
                }
            }
            return true;
        } catch (Exception error) {
            return true;
        }
    }

    private static String readSmallFile(File file) throws IOException {
        long length = Math.min(file.length(), 64 * 1024);
        byte[] data = new byte[(int) length];
        try (FileInputStream in = new FileInputStream(file)) {
            int offset = 0;
            while (offset < data.length) {
                int read = in.read(data, offset, data.length - offset);
                if (read <= 0) {
                    break;
                }
                offset += read;
            }
            if (offset < data.length) {
                byte[] shorter = new byte[offset];
                System.arraycopy(data, 0, shorter, 0, offset);
                data = shorter;
            }
        }
        return new String(data, StandardCharsets.UTF_8);
    }

    private static List<PenGuruStorage.FileExpectation> parseExpectations(String filesJson) {
        if (filesJson == null || filesJson.isEmpty()) {
            return null;
        }
        try {
            JSONArray array = new JSONArray(filesJson);
            List<PenGuruStorage.FileExpectation> out = new ArrayList<>();
            for (int i = 0; i < array.length(); i++) {
                JSONObject entry = array.getJSONObject(i);
                out.add(new PenGuruStorage.FileExpectation(
                        entry.optString("path", ""), entry.optLong("size", 0)));
            }
            return out;
        } catch (JSONException error) {
            return null;
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
                File dir = PenGuruStorage.safeChild(dest, name);
                if (!dir.exists() && !dir.mkdirs()) {
                    throw new IOException("cannot create " + dir);
                }
                skipFully(in, size);
            } else if (type == '0' || type == 0 || type == '7') {
                File out = PenGuruStorage.safeChild(dest, name);
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
                File dir = PenGuruStorage.safeChild(dest, name);
                if (!dir.exists() && !dir.mkdirs()) {
                    throw new IOException("cannot create " + dir);
                }
                continue;
            }
            File out = PenGuruStorage.safeChild(dest, name);
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

    private static int readFully(InputStream in, byte[] buffer, int offset, int length)
            throws IOException {
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
}
