# Android persistence regression found during A58

Two APK replacement checks failed before the native preference store was added.
The JS localStorage value had speedIndex 2 (then, on a separate probe, 1),
but relaunch after `adb install -r` recovered the earlier value 4. No uninstall
or data clear was performed. An app-private LevelDB tar readback contained the
new records; the exact WebView recovery mechanism was not established.

This was treated as a real failure, not waived as a test issue. A small native
Capacitor plugin now reads app-private SharedPreferences before UI startup and
commits each settings record before acknowledging the save. Existing localStorage
is migrated, retained and mirrored; the maximum valid high score is preserved.
No new dependency or permission.

The subsequent same-signed APK replacement check retained speedIndex 1 and the
other fields exactly; see android-final-update-and-native.json. Browser/PWA
storage remains on the established v2 key with v1 migration.
