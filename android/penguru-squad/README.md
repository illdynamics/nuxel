# PenGuru Squad — Android APK

This directory packages PenGuru Squad as a standalone Android application. The
APK bundles the app's HTML/CSS/JS and serves it from a private virtual origin
(`https://appassets.androidplatform.net`); it is not a shortcut to a remote
website and does not require Android Studio.

Since `0.9.0-beta` the app runs without a Nuxel host. A bundled on-device
engine (`pwa/nuxel-apps/penguru/local-engine.js`) implements the same verbs as
the old `penguru` RPC namespace and delegates Android-only work to the
`NuxelAndroid` bridge in `MainActivity`:

- conversation, routing, device diagnostics and voice work immediately;
- model downloads go directly from Hugging Face to app storage;
- llama.cpp and ONNX Runtime installers download, verify and unpack into app
  storage;
- Android `SpeechRecognizer` supplies foreground microphone transcripts.

The Nuxel connection form remains as an optional engine mode for owners who
already run the PenGuru service. No URL or token is required on a regular
phone.

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

Or copy the APK to the phone and open it. The stable debug signing key is
generated under `android/penguru-squad/.signing/` and is not committed, so
repeated builds upgrade the same install instead of failing the signature
check. For a release identity, create an owner-managed keystore and pass
`PENGURU_KEYSTORE` to the build script; never commit a private signing key.

## On-device engine

The default engine mode is **On this phone**. It requires no server, URL,
token, launcher or root access.

| Feature | How it works |
|---|---|
| Conversation | Local routing plus a built-in responder (device status, code outlines, clarifying questions, chat). |
| Model library | Shows the pinned ChatBird, CodeBird, SonarBird MiniLM and Voice tiny.en packages with **Download to this phone**. |
| Downloads | `MainActivity` streams from Hugging Face/GitHub, resumes `.part` files, verifies the pinned SHA-256, and writes an `installed.json` marker. |
| Runtimes | **Settings → On-device dependencies** installs llama.cpp arm64, llama.cpp Snapdragon/OpenCL, and ONNX Runtime Android (AAR), unpacking tar.gz/zip into app storage. |
| Voice | Android `SpeechRecognizer`; prefers offline, retries once online if the service rejects the offline hint, and always releases the controls on Stop. The transcript is reviewed before Send. |
| Diagnostics | Battery, storage, Android version, CPU ABIs, model/runtime paths. |
| Export | MediaStore `Downloads/PenGuru`; the actual de-duplicated name is reported. |

### Storage paths

```
/storage/emulated/0/Android/data/org.nuxel.penguru/files/Models/<model>/<variant>/
/storage/emulated/0/Android/data/org.nuxel.penguru/files/Runtimes/<runtime>/
/storage/emulated/0/Download/PenGuru/
```

These are app-specific external directories: no `WRITE_EXTERNAL_STORAGE`
permission is needed, and the paths are shown in Settings → Storage.

### Runtime catalog

| Runtime | Source | Size | SHA-256 |
|---|---|---:|---|
| llama.cpp Android arm64 | ggml-org/llama.cpp release `b12675` | 82.5 MB | `fbe76190…58f6c` |
| llama.cpp Snapdragon/OpenCL | ggml-org/llama.cpp release `b12675` | 68.6 MB | `bdd94b31…7ede` |
| ONNX Runtime Android 1.20.0 | Maven Central AAR | 27.9 MB | `07a8f71e…2027` |

Android blocks executing arbitrary binaries downloaded into app data on modern
releases. The installers therefore stage verified, unpacked artifacts for a
future bundled/JNI runtime and for owner inspection; neural generation in this
build is not claimed. The built-in responder makes the app usable immediately.

## Optional Nuxel host mode

Switch **Settings → Engine** to **Nuxel host (optional)** only if you run the
PenGuru service on a Nuxel device. Mint a one-hour, PenGuru-bound token on the
host as root:

```sh
python3 services/nuxel-penguru/tools/mint-android-token.py
```

Then enter the bridge URL and token and press **Save & reconnect**. The host
bridge must allow the APK origin for CORS; the current
`services/nuxel-bridge/src/api.py` includes
`https://appassets.androidplatform.net`.

## What is bundled

- `pwa/nuxel-apps/penguru/index.html`, `penguru.js`, `penguru.css`, `voice.js`
- `pwa/nuxel-apps/penguru/local-engine.js` (standalone RPC engine)
- `pwa/nuxel-apps/penguru/model-library.js`
- `pwa/nuxel-apps/penguru/manifest.json` and `app.json`
- `pwa/nuxel-common/bridge.js`, `bridge-version.json`, `theme.css`
- `assets/nuxel-penguru-squad.png` as the launcher/manifest icon

## Verification performed

- `node --check` on every bundled JS file.
- `node pwa/nuxel-common/verify-wiring.js` — all 7 PWA surfaces OK.
- `node pwa/nuxel-common/test-bridge.js` — all shared-bridge tests pass.
- A Node harness with a mocked `NuxelAndroid` bridge exercised the on-device
  engine: status, model cards, model download spec (pinned URL/SHA-256),
  download-status → installed transition, runtime install spec, SYSTEM and CODE
  replies, and diagnostics.
- APK rebuilt, `apksigner verify` shows v2 + v3 signatures, `versionCode=900`,
  `versionName=0.9.0-beta`.
- A mocked-bridge harness also resolves the SonarBird Voice tiny.en download by
  model **and** variant (pinned `ggml-tiny.en.bin`) while MiniLM still resolves
  its six encoder files.
- System-bar/cutout/IME insets are applied to a container view, so page text
  stays clear of the status bar and the three-button Android navigation row.

The headless emulator available on this build host segfaulted before boot, so
physical-device acceptance of the new download/install/voice flows is still
required.

## Security and limitations

- Bundled assets only; no remote HTML is loaded in the WebView.
- All download/extract paths are canonicalized and must stay inside the app's
  own storage roots; `..` and absolute paths are rejected.
- Runtime archives are pinned by URL and SHA-256 before unpacking.
- Cleartext HTTP is permitted only for the optional local/LAN Nuxel bridge.
- Microphone permission is requested only when the voice button is used.
- Neural inference is not embedded; the runtime installers stage verified
  artifacts and the built-in responder provides the default answers.
