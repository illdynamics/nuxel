# PenGuru Squad — Android Quickstart

## The APK you install

Install this file on your Android phone:

```
dist/android/penguru-squad-debug.apk
```

That is the complete PenGuru Squad Android client (app label **PenGuru Squad**,
package `org.nuxel.penguru`, version `0.8.9-beta` / versionCode `809`). There
is no other APK to install. The matching checksum is in
`dist/android/SHA256SUMS`:

```
be8e5b2381c81411ccae5f6b529f33d8999f6e893e6dcef8d7d644dc3e5915e8  penguru-squad-debug.apk
```

The APK is signed with the repository's stable debug identity, so it installs
as an in-place upgrade over earlier builds of the same app.

## Install it

Phone requirements: Android 8.0 (API 26) or newer.

**Option A — USB / ADB (recommended):**

```sh
adb install -r dist/android/penguru-squad-debug.apk
```

**Option B — copy the file:** transfer `dist/android/penguru-squad-debug.apk`
to the phone (USB, `scp`, cloud drive, etc.), tap it in the Files app, and allow
"Install unknown apps" for the file manager when Android asks. Play Protect may
warn that the app is unsigned-by-Play; choose **Install anyway**.

Verify the copy first if you like:

```sh
sha256sum penguru-squad-debug.apk
```

## Point it at your Nuxel host

The APK is the client; inference still runs on the Nuxel host.

1. On the Nuxel host, mint a one-hour PenGuru token as root:

   ```sh
   python3 services/nuxel-penguru/tools/mint-android-token.py
   ```

2. Open **PenGuru Squad → Settings → Connection**.
3. Enter the bridge URL. On the same handset use
   `http://127.0.0.1:8080/api/v1`; from Wi-Fi use the host's LAN address, e.g.
   `http://192.168.1.20:8080/api/v1`.
4. Paste the token and press **Save & reconnect**.

## First-run checklist

- [ ] App opens to the PenGuru Squad home screen (no blank/white page).
- [ ] Connection says connected and the model library lists models.
- [ ] Enable PenGuru, then start a chat.
- [ ] **Export response** writes to `Downloads/PenGuru/`.

If the app reports `launcher_token_required`, the token expired — re-run the
mint command and paste the new one. If the model controls stop responding,
check that the Nuxel bridge is reachable from the phone's network.

## Rebuilding the APK

```sh
./android/penguru-squad/scripts/build-apk.sh
```

Output is rewritten to `dist/android/penguru-squad-debug.apk` plus
`dist/android/SHA256SUMS`. See `android/penguru-squad/README.md` for SDK
prerequisites and `apk-report.md` for the full verification report.

## Limitations

- No model weights are inside the APK; a reachable Nuxel host is required for
  inference, model downloads, deletion and diagnostics.
- Bundled assets only — the WebView loads no remote HTML.
- Cleartext HTTP is allowed for local/LAN bridges; use a trusted network or a
  TLS-terminating proxy on untrusted Wi-Fi.
- Microphone permission is requested only when you use the in-app voice button.
