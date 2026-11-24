package org.nuxel.penguru;

import android.content.Context;
import android.os.Build;
import android.os.Environment;
import android.util.Log;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Canonical on-device storage for downloaded models and runtimes.
 *
 * On Android 11+ files live in /sdcard/Android/media/<package>/ which, unlike
 * /sdcard/Android/data/<package>/, is not wiped when the APK is uninstalled.
 * That lets a rebuilt/reinstalled APK discover multi-gigabyte model packages
 * and llama.cpp runtimes that are already present instead of downloading them
 * again. Older releases keep using the app-specific external directory.
 */
final class PenGuruStorage {
    private static final String TAG = "PenGuruStorage";
    static final String MODELS_DIR_NAME = "Models";
    static final String RUNTIMES_DIR_NAME = "Runtimes";
    private static final String MARKER_NAME = "installed.json";

    private PenGuruStorage() {
    }

    /**
     * Prefer a public Downloads/PenGuru directory when the owner has granted
     * "All files access". Unlike app-specific storage it survives an APK
     * uninstall, so a rebuilt APK finds the models and runtimes again.
     * Without that grant, fall back to Android/media (survives updates but
     * not uninstall) and then app-specific external storage.
     */
    static File root(Context context) {
        if (hasAllFilesAccess(context)) {
            File publicBase = new File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "PenGuru");
            if (usableRoot(publicBase)) {
                return publicBase;
            }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            File shared = Environment.getExternalStorageDirectory();
            if (shared != null) {
                File media = new File(new File(new File(shared, "Android"), "media"),
                        context.getPackageName());
                if (usableRoot(media)) {
                    return media;
                }
            }
        }
        File external = context.getExternalFilesDir(null);
        if (usableRoot(external)) {
            return external;
        }
        File internal = context.getFilesDir();
        if (!internal.exists() && !internal.mkdirs()) {
            Log.w(TAG, "Could not create internal storage root " + internal);
        }
        return internal;
    }

    static boolean hasAllFilesAccess(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            return false;
        }
        try {
            return Environment.isExternalStorageManager();
        } catch (RuntimeException error) {
            return false;
        }
    }

    private static boolean usableRoot(File base) {
        if (base == null) {
            return false;
        }
        try {
            if (!base.exists() && !base.mkdirs()) {
                return false;
            }
            File probe = new File(base, ".pen-guru-write-test");
            if (probe.exists() || probe.createNewFile()) {
                //noinspection ResultOfMethodCallIgnored
                probe.delete();
                return true;
            }
        } catch (IOException | RuntimeException error) {
            Log.w(TAG, "Storage root is not writable: " + base + " (" + error + ")");
        }
        return false;
    }

    static File dir(Context context, String name) {
        File directory = new File(root(context), name);
        if (!directory.exists() && !directory.mkdirs()) {
            Log.w(TAG, "Could not create storage directory " + directory);
        }
        return directory;
    }

    /**
     * Move downloads written by 0.9.x (app-specific external storage) into
     * the reinstall-safe media directory. Same-volume renames are instant.
     */
    static void migrateLegacy(Context context) {
        File currentBase = root(context);
        if (currentBase == null) {
            return;
        }
        List<File> candidates = new ArrayList<>();
        candidates.add(context.getExternalFilesDir(null));
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            File shared = Environment.getExternalStorageDirectory();
            if (shared != null) {
                candidates.add(new File(new File(new File(shared, "Android"), "media"),
                        context.getPackageName()));
            }
        }
        for (File legacyBase : candidates) {
            if (legacyBase == null) {
                continue;
            }
            try {
                if (legacyBase.getCanonicalPath().equals(currentBase.getCanonicalPath())) {
                    continue;
                }
            } catch (IOException ignored) {
                continue;
            }
            for (String name : new String[]{MODELS_DIR_NAME, RUNTIMES_DIR_NAME}) {
                File legacy = new File(legacyBase, name);
                File current = new File(currentBase, name);
                if (!legacy.isDirectory()) {
                    continue;
                }
                if (!current.exists() && legacy.renameTo(current)) {
                    Log.i(TAG, "Migrated " + legacy + " to " + current);
                    continue;
                }
                if (!current.exists() && !current.mkdirs()) {
                    Log.w(TAG, "Could not create migration target " + current);
                    continue;
                }
                if (mergeInto(legacy, current)) {
                    deleteRecursively(legacy);
                } else {
                    Log.w(TAG, "Left partial legacy download at " + legacy);
                }
            }
        }
    }

    private static boolean mergeInto(File source, File destination) {
        File[] children = source.listFiles();
        if (children == null) {
            return true;
        }
        boolean ok = true;
        for (File child : children) {
            File target = new File(destination, child.getName());
            if (target.exists()) {
                continue;
            }
            if (child.isDirectory()) {
                if (child.renameTo(target)) {
                    continue;
                }
                if (!target.mkdirs()) {
                    ok = false;
                    continue;
                }
                if (!mergeInto(child, target)) {
                    ok = false;
                }
            } else if (!child.renameTo(target) && !copyFile(child, target)) {
                ok = false;
            }
        }
        return ok;
    }

    private static boolean copyFile(File source, File destination) {
        File parent = destination.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            return false;
        }
        try (InputStream in = new BufferedInputStream(new FileInputStream(source));
             OutputStream out = new BufferedOutputStream(new FileOutputStream(destination))) {
            byte[] buffer = new byte[1 << 18];
            int read;
            while ((read = in.read(buffer)) > 0) {
                out.write(buffer, 0, read);
            }
            return true;
        } catch (IOException error) {
            Log.w(TAG, "Could not copy " + source + ": " + error);
            return false;
        }
    }

    static String safeRelative(String raw) {
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

    static File safeChild(File root, String relative) throws IOException {
        String clean = safeRelative(relative);
        File child = new File(root, clean);
        String rootPath = root.getCanonicalPath();
        String childPath = child.getCanonicalPath();
        if (!childPath.equals(rootPath) && !childPath.startsWith(rootPath + File.separator)) {
            throw new IOException("path escapes storage root");
        }
        return child;
    }

    static void deleteRecursively(File file) {
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

    static File targetDir(Context context, String kind, String id) throws IOException {
        File base = "runtime".equals(kind)
                ? dir(context, RUNTIMES_DIR_NAME) : dir(context, MODELS_DIR_NAME);
        return safeChild(base, id);
    }

    static String installedPath(Context context, String kind, String id) {
        try {
            return targetDir(context, kind, id).getAbsolutePath();
        } catch (Exception error) {
            return "";
        }
    }

    static boolean hasMarker(File directory) {
        return directory != null && new File(directory, MARKER_NAME).isFile();
    }

    /**
     * True when every expected file exists with the expected byte length.
     * Multi-gigabyte files are not re-hashed here: size equality plus the
     * pinned download verification is enough to avoid a reinstall download.
     */
    static boolean expectedFilesPresent(File directory, List<FileExpectation> expected) {
        if (directory == null || !directory.isDirectory() || expected == null) {
            return false;
        }
        for (FileExpectation file : expected) {
            if (file == null || file.path == null || file.path.isEmpty()) {
                return false;
            }
            File target;
            try {
                target = safeChild(directory, file.path);
            } catch (IOException error) {
                return false;
            }
            if (!target.isFile()) {
                return false;
            }
            if (file.size > 0 && target.length() != file.size) {
                return false;
            }
        }
        return true;
    }

    /** llama.cpp / ONNX archives are unpacked and the archive is removed. */
    static boolean looksLikeExtractedRuntime(String kind, String id, File directory) {
        if (directory == null || !directory.isDirectory()) {
            return false;
        }
        List<String> wanted = new ArrayList<>();
        if (id != null && id.startsWith("llama.cpp")) {
            wanted.add("llama-cli");
            wanted.add("llama-server");
            wanted.add("libllama.so");
        } else if ("onnxruntime".equals(id)) {
            wanted.add("libonnxruntime.so");
            wanted.add("classes.jar");
        }
        return containsAnyFile(directory, wanted, 6);
    }

    private static boolean containsAnyFile(File directory, List<String> names, int depth) {
        if (depth < 0) {
            return false;
        }
        File[] children = directory.listFiles();
        if (children == null) {
            return false;
        }
        for (File child : children) {
            if (child.isFile() && names.contains(child.getName())) {
                return true;
            }
            if (child.isDirectory() && containsAnyFile(child, names, depth - 1)) {
                return true;
            }
        }
        return false;
    }

    static String sha256Hex(File file, CancelCheck check) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream in = new BufferedInputStream(new FileInputStream(file))) {
                byte[] buffer = new byte[1 << 20];
                int read;
                while ((read = in.read(buffer)) > 0) {
                    if (check != null) {
                        check.check();
                    }
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

    interface CancelCheck {
        void check() throws IOException;
    }

    static final class FileExpectation {
        final String path;
        final long size;

        FileExpectation(String path, long size) {
            this.path = path;
            this.size = size;
        }
    }
}
