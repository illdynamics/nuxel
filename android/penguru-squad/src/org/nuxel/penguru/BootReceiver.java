package org.nuxel.penguru;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.Log;

/** Re-arms the persistent SonarBird listener after a reboot or app update. */
public class BootReceiver extends BroadcastReceiver {
    private static final String TAG = "PenGuruBoot";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) {
            return;
        }
        String action = intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) {
            return;
        }
        SharedPreferences prefs = context.getSharedPreferences(
                WakeWordService.PREFS, Context.MODE_PRIVATE);
        if (!prefs.getBoolean(WakeWordService.PREF_ENABLED, false)) {
            return;
        }
        Intent service = new Intent(context, WakeWordService.class)
                .setAction(WakeWordService.ACTION_START);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(service);
            } else {
                context.startService(service);
            }
        } catch (RuntimeException error) {
            // Android 14+ can refuse a microphone foreground service that is
            // started from the background. The preference stays on so opening
            // PenGuru arms it again.
            Log.w(TAG, "Could not restart SonarBird listening: " + error);
        }
    }
}
