package org.nuxel.penguru;

import android.os.BatteryManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.StatFs;
import android.text.TextUtils;

import java.util.Locale;

/**
 * Native mirror of the WebView's rule-based on-device responder.
 *
 * A wake-word command recognised while PenGuru is in the background can reach
 * the live WebView, but the page's JavaScript timers are suspended while the
 * Activity is stopped. That used to mean the reply was only generated and
 * spoken after the owner brought the app back to the foreground. The SonarBird
 * foreground service instead generates the same spoken answer here and voices
 * it through its own TalkbackEngine, so background answers do not depend on
 * WebView JavaScript being allowed to run.
 */
final class NativeReply {
    private static final String PENGURU_IDENTITY = "I am PenGuru, a virtual penguin and the most "
            + "advanced AI subsystem of NUXAI. NUXAI was originally designed for Nuxel, "
            + "and now I also run on Android.";

    private NativeReply() {
    }

    static String replyFor(Context context, String text, String mode) {
        String value = firstLine(text, 300);
        if (identityQuestion(value)) {
            return identityReply();
        }
        String route = routeFor(value, mode);
        if ("SYSTEM".equals(route)) {
            return formatDevice(context);
        }
        if ("CODE".equals(route)) {
            return codeReply(value);
        }
        if ("ASK".equals(route)) {
            return askReply(value);
        }
        return chatReply(value);
    }

    private static String routeFor(String text, String mode) {
        if ("chatbird".equals(mode)) {
            return "CHAT";
        }
        if ("codebird".equals(mode)) {
            return "CODE";
        }
        String value = text.toLowerCase(Locale.ROOT);
        if (containsWord(value, "code", "function", "method", "class", "bug", "error",
                "exception", "stack trace", "python", "javascript", "typescript", "java",
                "kotlin", "rust", "golang", "sql", "regex", "compile", "refactor", "api", "json")) {
            return "CODE";
        }
        if (containsWord(value, "battery", "storage", "disk", "free space", "device", "android",
                "microphone", "mic", "cpu", "memory", "ram", "model", "download", "install",
                "diagnostic", "folder", "path")) {
            return "SYSTEM";
        }
        if (value.endsWith("?") || value.matches("(?s)^(how|what|why|when|where|who|which|can|does|do|is|are|should)\\b.*")) {
            return "ASK";
        }
        return "CHAT";
    }

    private static String formatDevice(Context context) {
        String manufacturer = Build.MANUFACTURER == null ? "Android" : Build.MANUFACTURER;
        String model = Build.MODEL == null ? "" : Build.MODEL;
        String device = (manufacturer + " " + model).trim();
        int level = -1;
        boolean charging = false;
        try {
            BatteryManager battery = (BatteryManager) context.getSystemService(Context.BATTERY_SERVICE);
            if (battery != null) {
                level = battery.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
            }
            Intent batteryIntent = context.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (batteryIntent != null) {
                int status = batteryIntent.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
                charging = status == BatteryManager.BATTERY_STATUS_CHARGING
                        || status == BatteryManager.BATTERY_STATUS_FULL;
            }
        } catch (RuntimeException ignored) {
            // Battery data is optional.
        }
        long free = 0;
        try {
            StatFs stat = new StatFs(PenGuruStorage.root(context).getAbsolutePath());
            free = stat.getAvailableBytes();
        } catch (RuntimeException ignored) {
            // Storage data is optional.
        }
        String models = PenGuruStorage.dir(context, PenGuruStorage.MODELS_DIR_NAME).getAbsolutePath();
        String runtimes = PenGuruStorage.dir(context, PenGuruStorage.RUNTIMES_DIR_NAME).getAbsolutePath();
        return "On-device diagnostics (read-only): "
                + "Device: " + device + ". "
                + "Android: " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + "). "
                + "Battery: " + (level >= 0 ? level + "%" + (charging ? " charging" : "") : "unknown") + ". "
                + "Free storage: " + bytes(free) + ". "
                + "Models: " + models + ". "
                + "Runtimes: " + runtimes + ".";
    }

    private static String codeReply(String text) {
        String value = text.toLowerCase(Locale.ROOT);
        if (value.contains("sort") && value.contains("python")) {
            return "CodeBird on-device assistant. A small, dependency-free Python example: "
                    + "def quicksort(items): if len(items) <= 1: return items. "
                    + "pivot = items[len(items) // 2]. "
                    + "lower = [x for x in items if x < pivot]. "
                    + "same = [x for x in items if x == pivot]. "
                    + "higher = [x for x in items if x > pivot]. "
                    + "return quicksort(lower) + same + quicksort(higher).";
        }
        if (containsWord(value, "fetch", "http", "api", "request")
                && containsWord(value, "javascript", "typescript", "js", "node")) {
            return "CodeBird on-device assistant. A minimal fetch example with error handling: "
                    + "async function getJson(url) { const response = await fetch(url); "
                    + "if (!response.ok) throw new Error('HTTP ' + response.status); "
                    + "return response.json(); }";
        }
        return "CodeBird on-device assistant. Request: " + firstLine(text, 300)
                + ". A practical outline: state the input, the expected output and the failure cases. "
                + "Keep the smallest reproduction alongside the fix. Add one automated check for the bug, "
                + "then re-run it after each change.";
    }

    private static String chatReply(String text) {
        String value = text.toLowerCase(Locale.ROOT);
        if (value.matches("^(hi|hello|hey|yo|good morning|good evening)\\b.*")) {
            return "Hi. " + PENGURU_IDENTITY + " I can report device status, outline code, help route "
                    + "a request, and keep the conversation local.";
        }
        if (containsWord(value, "what can you do", "help", "capabilit", "feature")) {
            return "This standalone build works without a Nuxel host. Conversation: local routing plus a "
                    + "built-in responder. Model library: download verified model files from Hugging Face to "
                    + "this phone. Dependencies: install llama.cpp and ONNX Runtime archives. Voice: Android "
                    + "speech recognition. Diagnostics: read-only device and storage status.";
        }
        if (containsWord(value, "time", "date", "today")) {
            return "On this phone it is " + java.text.DateFormat.getDateTimeInstance(
                    java.text.DateFormat.MEDIUM, java.text.DateFormat.SHORT,
                    Locale.getDefault()).format(new java.util.Date()) + ".";
        }
        return "PenGuru on-device. I received: " + firstLine(text, 300)
                + ". I am PenGuru, the NUXAI penguin running on this phone. This standalone build keeps "
                + "the conversation on the handset and answers with local logic. Ask about device status, "
                + "request a code outline, or use the voice button.";
    }

    private static String askReply(String text) {
        return "I am PenGuru, and I can help. I need one detail first. You asked: "
                + firstLine(text, 300) + ". Which outcome do you want: a short explanation, a code example, "
                + "or a device or storage check?";
    }

    private static String identityReply() {
        return PENGURU_IDENTITY + " I can chat, outline code, check this phone's status and keep the "
                + "conversation on-device. What would you like to do?";
    }

    private static boolean identityQuestion(String text) {
        String value = text.toLowerCase(Locale.ROOT);
        return containsWord(value, "who are you", "what are you", "your name", "introduce yourself",
                "tell me about yourself")
                || containsWord(value, "who is penguru", "what is penguru", "nuxai", "nux ai");
    }

    private static boolean containsWord(String value, String... words) {
        for (String word : words) {
            if (value.contains(word)) {
                return true;
            }
        }
        return false;
    }

    private static String firstLine(String text, int max) {
        String clean = text == null ? "" : text.replaceAll("\\s+", " ").trim();
        if (clean.length() > max) {
            return clean.substring(0, max - 1) + "…";
        }
        return clean;
    }

    private static String bytes(long value) {
        if (value >= 1_000_000_000L) {
            return String.format(Locale.ROOT, "%.2f GB", value / 1_000_000_000.0);
        }
        if (value >= 1_000_000L) {
            return String.format(Locale.ROOT, "%.1f MB", value / 1_000_000.0);
        }
        if (value >= 1_000L) {
            return String.format(Locale.ROOT, "%.1f KB", value / 1_000.0);
        }
        return value + " B";
    }
}
