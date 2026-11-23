# PenGuru Squad — Android APK

This directory packages the current PenGuru Squad PWA as a standalone Android
application. The APK bundles the app's HTML/CSS/JS and serves it from a private
virtual origin (`https://appassets.androidplatform.net`); it is not a shortcut
to a remote website and does not require Android Studio.

The Nuxel inference service is still the backend. The APK is the owner-facing
client: it talks to the Nuxel HTTP bridge to enable PenGuru, list/download/
verify models, and run local chat. The model library, runtime choice, voice
controls and connection settings all live inside the PenGuru app now; the old
Settings → PenGuru AI panel has been removed.

## Build

Prerequisites on the build host:

- JDK 17 or newer (`JAVA_HOME` or an installed `/usr/lib/jvm/java-*`)
- Android SDK platform 35 and build-tools 35.0.0
- `curl`, `unzip`, `zip`, ImageMagick (only needed to regenerate icons)

If the SDK is not already installed:

```sh
mkdir -p /tmp/android-sdk/cmdline-tools
curl -L -o /tmp/commandlinetools.zip \
  https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip -q /tmp/commandlinetools.zip -d /tmp/android-sdk/cmdline-tools-tmp
mv /tmp/android-sdk/cmdline-tools-tmp/cmdline-tools /tmp/android-sdk/cmdline-tools/latest
export ANDROID_SDK_ROOT=/tmp/android-sdk
yes | /tmp/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root="$ANDROID_SDK_ROOT" --licenses
/tmp/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root="$ANDROID_SDK_ROOT" \
  "platform-tools" "platforms;android-35" "build-tools;35.0.0"
```

Then:

```sh
./android/penguru-squad/scripts/build-apk.sh
```

Output:

```
dist/android/penguru-squad-debug.apk
dist/android/SHA256SUMS
```

The script uses `aapt2`, `javac`, `d8`, `zipalign` and `apksigner` directly.
`assets/public/` is generated from `pwa/nuxel-apps/penguru` and
`pwa/nuxel-common` by `scripts/stage-web.sh`; do not edit the staged copy.

## Install

```sh
adb install -r dist/android/penguru-squad-debug.apk
```

Or copy the APK to the phone and open it. The stable debug signing key is generated under
`android/penguru-squad/.signing/` and is not committed, so repeated builds
upgrade the same install instead of failing the signature check. For a release
identity, create an owner-managed keystore and pass `PENGURU_KEYSTORE` to the
build script; never commit a private signing key.

## Connect to Nuxel

PenGuru RPC is a launcher-authority route. A self-bootstrapped token is not
enough (by design). Mint a one-hour, PenGuru-bound token on the Nuxel host as
root:

```sh
python3 services/nuxel-penguru/tools/mint-android-token.py
```

In PenGuru Squad → Settings → Connection:

1. Enter the bridge URL. On the same handset use
   `http://127.0.0.1:8080/api/v1`; from another device use the host's private
   LAN address, for example `http://192.168.1.20:8080/api/v1`.
2. Paste the printed token.
3. Press **Save & reconnect**.

The token is stored in the app's WebView local storage, bound to
`org.nuxel.PenGuru`, and never shown back in clear text. Re-mint it when the app
reports `launcher_token_required` or when model controls stop responding after
expiry.

The host bridge must allow the APK origin for CORS. The current
`nuxel-http-bridge.service` and `services/nuxel-bridge/src/api.py` include
`https://appassets.androidplatform.net`; `services/nuxel-penguru/tools/
install-device.py` also merges it into an existing unit and restarts the
bridge.

## What is bundled

- `pwa/nuxel-apps/penguru/index.html`, `penguru.js`, `penguru.css`, `voice.js`
- `pwa/nuxel-apps/penguru/model-library.js` (moved out of Settings)
- `pwa/nuxel-apps/penguru/manifest.json` and `app.json`
- `pwa/nuxel-common/bridge.js`, `bridge-version.json`, `theme.css`
- `assets/nuxel-penguru-squad.png` as the launcher/manifest icon

## Verification performed

The APK was installed on a headless Android 15 (API 35) emulator. The activity
resolved, the bundled page loaded from
`https://appassets.androidplatform.net/pwa/nuxel-apps/penguru/index.html`, the
four in-app sections and connection form rendered, and the model library showed
its OFF state. Against a mock bridge on the emulator host, the app fetched the
PenGuru status through the real `bridge.js` path and displayed
`PenGuru is OFF. Enable it to manage models and start a conversation.` No
AndroidRuntime crash or launcher-resource failure was logged.

The signed APK was then reinstalled on the same headless Android 15 emulator
with a loopback mock bridge that enforced the real launcher-authority rule. The
owner-pasted token was carried on `/api/v1/rpc`, a conversation request
completed, **Export response** wrote `Downloads/PenGuru/penguru-response.txt`,
and a Hugging Face provenance link opened the external browser. The APK reports
`versionCode=809` / `versionName=0.8.9-beta`, derived from `VERSION` (which
carries the leading `v`).

## Security and limitations

- Bundled assets only; no remote HTML is loaded in the WebView.
- Cleartext HTTP is permitted because the owner-hosted bridge is local/LAN.
  Use a trusted private network or a TLS-terminating proxy for untrusted Wi-Fi.
- Microphone permission is requested only when the in-app voice control calls
  `getUserMedia`; the transcript is still reviewed and manually sent.
- Model weights are downloaded by the Nuxel PenGuru service, not stored in the
  APK. An enabled, reachable Nuxel host is required for inference, downloads,
  deletion and diagnostics.
- ONNX GenAI, privileged actions and generated-code execution remain
  unavailable, matching the current PenGuru backend gates.
