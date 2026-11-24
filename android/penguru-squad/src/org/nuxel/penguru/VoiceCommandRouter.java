package org.nuxel.penguru;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Small, deterministic voice-command vocabulary shared by the in-app mic and
 * the persistent SonarBird listener.
 *
 * Commands are deliberately matched only as a whole utterance ("stop",
 * "Penguru stop", "that's all") so ordinary sentences such as "stop the music"
 * are not swallowed. Audio never authorizes privileged actions; these command
 * words only control the microphone / conversation.
 */
public final class VoiceCommandRouter {
    public static final String NONE = "";
    public static final String STOP = "stop";
    public static final String SEND = "send";
    public static final String CANCEL = "cancel";

    private static final Pattern WAKE = Pattern.compile(
            "\\b(?:pen[\\s-]?guru|peng[\\s-]?g?u(?:ru|ro|roo)"
            + "|ping[\\s-]?u?ru|pang[\\s-]?u?ru)\\b[\\s,.:;!?\\-]*(.*)$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static final String WAKE_PREFIX =
            "(?:(?:hey|hi|ok|okay|oi)\\s+)?(?:pen[\\s-]?guru|peng[\\s-]?g?u(?:ru|ro|roo)"
            + "|ping[\\s-]?u?ru|pang[\\s-]?u?ru)[\\s,.:;!?\\-]*";

    private static final Pattern STOP_ONLY = Pattern.compile(
            "^(?:" + WAKE_PREFIX + ")?(?:stop(?:\\s+(?:listening|recording|now|it|that|the\\s+mic))?"
            + "|abort|halt|never[\\s-]?mind|that'?s\\s+all|that\\s+is\\s+all|cancel"
            + "|quiet|silence|shut\\s+up|enough)[\\s.!,]*$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static final Pattern SEND_ONLY = Pattern.compile(
            "^(?:" + WAKE_PREFIX + ")?(?:send(?:\\s+(?:it|now|this|that|message))?"
            + "|submit|finish|done|that'?s\\s+it|go\\s+ahead)[\\s.!,]*$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private VoiceCommandRouter() { }

    /** Remove a leading wake phrase. Returns the remainder, possibly "". */
    public static String stripWake(String text) {
        String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return "";
        }
        Matcher match = WAKE.matcher(value);
        if (match.find()) {
            String rest = match.group(1);
            return rest == null ? "" : rest.trim();
        }
        return value;
    }

    public static boolean wakeOnly(String text) {
        String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return false;
        }
        Matcher match = WAKE.matcher(value);
        return match.find() && (match.group(1) == null || match.group(1).trim().isEmpty());
    }

    public static boolean hasWake(String text) {
        return text != null && WAKE.matcher(text).find();
    }

    /** Classify a complete transcript. Returns NONE for ordinary speech. */
    public static String classify(String text) {
        String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return NONE;
        }
        String compact = value.replaceAll("\\s+", " ").trim();
        if (STOP_ONLY.matcher(compact).matches()) {
            return STOP;
        }
        if (SEND_ONLY.matcher(compact).matches()) {
            return SEND;
        }
        return NONE;
    }

    public static boolean isStop(String text) {
        return STOP.equals(classify(text));
    }

    public static boolean isSend(String text) {
        return SEND.equals(classify(text));
    }

    public static String label(String command) {
        if (STOP.equals(command) || "voice_stop_command".equals(command)) {
            return STOP;
        }
        if (SEND.equals(command) || "voice_send_command".equals(command)) {
            return SEND;
        }
        if (CANCEL.equals(command) || "voice_cancel_command".equals(command)) {
            return CANCEL;
        }
        return "";
    }

    /** True for phrases such as "Penguru stop" or "stop listening". */
    public static boolean isWakeStop(String text) {
        String value = text == null ? "" : text.trim().toLowerCase(Locale.ROOT);
        return value.length() <= 48 && STOP_ONLY.matcher(value).matches();
    }
}
