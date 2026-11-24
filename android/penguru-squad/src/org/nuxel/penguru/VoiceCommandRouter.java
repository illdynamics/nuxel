package org.nuxel.penguru;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Small, deterministic voice-command vocabulary shared by the in-app mic and
 * the persistent SonarBird listener.
 *
 * Stop/send commands are matched only as a whole utterance ("stop", "Penguru
 * stop", "that's all") so ordinary sentences such as "stop the music" are not
 * swallowed. Mode commands ("Penguru chat", "Penguru code") select ChatBird or
 * CodeBird for the next request. Audio never authorizes privileged actions;
 * these command words only control the microphone, conversation and assistant
 * mode.
 */
public final class VoiceCommandRouter {
    public static final String NONE = "";
    public static final String STOP = "stop";
    public static final String SEND = "send";
    public static final String CANCEL = "cancel";

    public static final String MODE_SQUAD = "squad";
    public static final String MODE_CHATBIRD = "chatbird";
    public static final String MODE_CODEBIRD = "codebird";

    /**
     * Speech recognizers split and misspell the invented wake word. Accept the
     * common renderings while still requiring a real word boundary, so
     * unrelated words such as "pengurus" are not treated as the wake phrase:
     * Penguru, Pen Guru, Peng Guru, Pengu ru, Penguro, Pinguru, Panguru.
     */
    private static final String WAKE_WORD =
            "(?:pen|peng|ping|pang)[\\s-]*(?:g[uo]{0,2})?[\\s-]*[uo]{0,2}[\\s-]*r[ou]{1,2}";

    private static final Pattern WAKE = Pattern.compile(
            "\\b(?:" + WAKE_WORD + ")\\b[\\s,.:;!?\\-]*(.*)$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static final String WAKE_PREFIX =
            "(?:(?:hey|hi|ok|okay|oi)\\s+)?(?:" + WAKE_WORD + ")\\b[\\s,.:;!?\\-]*";

    private static final Pattern STOP_ONLY = Pattern.compile(
            "^(?:" + WAKE_PREFIX + ")?(?:stop(?:\\s+(?:listening|recording|now|it|that|the\\s+mic))?"
            + "|abort|halt|never[\\s-]?mind|that'?s\\s+all|that\\s+is\\s+all|cancel"
            + "|quiet|silence|shut\\s+up|enough)[\\s.!,]*$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static final Pattern SEND_ONLY = Pattern.compile(
            "^(?:" + WAKE_PREFIX + ")?(?:send(?:\\s+(?:it|now|this|that|message))?"
            + "|submit|finish|done|that'?s\\s+it|go\\s+ahead)[\\s.!,]*$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private static final Pattern MODE_PREFIX = Pattern.compile(
            "^(chat\\s*bird|chatbird|chat|code\\s*bird|codebird|code|squad)"
            + "\\b[\\s,.:;!?\\-]*(.*)$",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);

    private VoiceCommandRouter() { }

    /**
     * Remove a leading wake phrase. Returns the remainder, or the original
     * text when no wake phrase is present.
     */
    public static String stripWake(String text) {
        String rest = wakeRemainder(text);
        if (rest != null) {
            return rest;
        }
        return text == null ? "" : text.trim();
    }

    /**
     * Returns the words after the wake phrase, or null when the utterance does
     * not contain one. This is the single source of truth used by final and
     * partial recognition so both paths accept the same renderings.
     */
    public static String wakeRemainder(String text) {
        String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return null;
        }
        Matcher match = WAKE.matcher(value);
        if (!match.find()) {
            return null;
        }
        String rest = match.group(1);
        return rest == null ? "" : rest.trim();
    }

    public static boolean wakeOnly(String text) {
        String rest = wakeRemainder(text);
        return rest != null && rest.isEmpty();
    }

    public static boolean hasWake(String text) {
        return wakeRemainder(text) != null;
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

    /**
     * Parse "chat", "chatbird", "code", "codebird" or "squad" at the start of
     * a wake-word remainder. Returns null when the text is not a mode command.
     * Any following words are returned as the request to send in that mode.
     */
    public static ModeMatch parseMode(String text) {
        String value = text == null ? "" : text.trim();
        if (value.isEmpty()) {
            return null;
        }
        Matcher match = MODE_PREFIX.matcher(value);
        if (!match.matches()) {
            return null;
        }
        String mode = canonicalMode(match.group(1));
        if (mode.isEmpty()) {
            return null;
        }
        String rest = match.group(2);
        return new ModeMatch(mode, rest == null ? "" : rest.trim());
    }

    /** Returns the mode for a mode-only utterance, otherwise "". */
    public static String modeCommand(String text) {
        ModeMatch match = parseMode(text);
        return match != null && match.rest.isEmpty() ? match.mode : "";
    }

    public static boolean isMode(String mode) {
        return MODE_SQUAD.equals(mode) || MODE_CHATBIRD.equals(mode)
                || MODE_CODEBIRD.equals(mode);
    }

    public static String modeName(String mode) {
        if (MODE_CHATBIRD.equals(mode)) {
            return "ChatBird";
        }
        if (MODE_CODEBIRD.equals(mode)) {
            return "CodeBird";
        }
        if (MODE_SQUAD.equals(mode)) {
            return "PenGuru Squad";
        }
        return "PenGuru";
    }

    private static String canonicalMode(String value) {
        String compact = value == null ? ""
                : value.toLowerCase(Locale.ROOT).replaceAll("\\s+", "");
        if ("chat".equals(compact) || "chatbird".equals(compact)) {
            return MODE_CHATBIRD;
        }
        if ("code".equals(compact) || "codebird".equals(compact)) {
            return MODE_CODEBIRD;
        }
        if ("squad".equals(compact)) {
            return MODE_SQUAD;
        }
        return "";
    }

    public static final class ModeMatch {
        public final String mode;
        public final String rest;

        ModeMatch(String mode, String rest) {
            this.mode = mode;
            this.rest = rest;
        }
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
