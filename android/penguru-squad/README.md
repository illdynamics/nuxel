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
- model downloads go directly from Hugging Face to `Download/PenGuru` (when
  All files access is granted) or app storage;
- llama.cpp and ONNX Runtime installers download, verify and unpack in a
  foreground service, so screen-off does not interrupt them;
- Android `SpeechRecognizer` supplies foreground microphone transcripts;
  every session has a native watchdog and an explicit microphone release;
- a microphone foreground service keeps a persistent SonarBird listener for
  the “Penguru” wake word while the app is in the background;
- on launch the app checks microphone, notification, battery-optimization and
  reinstall-safe storage access, then restores an enabled background listener.

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
| Model library | Shows the pinned ChatBird, CodeBird, SonarBird MiniLM and Voice tiny.en packages, the Spark-TTS 0.5B and Kokoro-82M talkback voice packages, and optional **Silero VAD ONNX** and **RNNoise 0.2** voice components, with **Download to this phone**. |
| Downloads | `DownloadService` (a `dataSync` foreground service) streams from Hugging Face/GitHub, resumes `.part` files, verifies the pinned SHA-256, and writes an `installed.json` marker. It holds a partial wake lock and Wi-Fi lock so locking the screen does not pause or interrupt the transfer. |
| Runtimes | **Settings → On-device dependencies** installs llama.cpp arm64, llama.cpp Snapdragon/OpenCL, and ONNX Runtime Android (AAR), unpacking tar.gz/zip. An interrupted job resumes from the persisted spec after a rebuild or process restart. |
| Voice | Android `SpeechRecognizer` with an adaptive RMS voice-activity detector. The Conversation default is **tap to talk, tap again to stop, transcribe and send**. Settings offers `toggle`, `vad` (auto-send when you stop talking; 0.5–2.5 s end-of-speech window) and `fixed` (record 5 seconds, then send). **Speak a message** always records for five seconds and sends the whole window. The engine picker lists every installed Android recognizer (GrapheneOS / Google / vendor), so the recognizer can be selected explicitly. Voice commands (`stop`, `cancel`, `never mind`, `send`, `send it`, `Penguru stop`, `Penguru send`) work in the foreground and in SonarBird. Noise suppression / AGC / echo cancellation are reported through Android `NoiseSuppressor`, and optional Silero VAD / RNNoise packages are downloadable. Partial hypotheses are kept, the best partial is sent if the final result is lost, and busy/client sessions retry with a fresh recognizer. |
| Background listening | **Settings → SonarBird background listening** starts a microphone foreground service with a persistent notification. Say “Penguru <question>” in one go, or say “Penguru” alone and then the next sentence; common renderings such as “Peng Guru”, “Pen Guru”, “Penguro”, “Pinguru” and “Panguru” are accepted. The notification shows the live partial sentence and finishes as soon as the adaptive VAD detects that you stopped talking. Say **“Penguru stop”** to stop the listener, **“Penguru send”** to send the captured sentence, or use the notification's **Send now** / **Stop listening** actions. SonarBird stays armed while PenGuru is open and pauses only while the in-app microphone records. Each recognizer session has its own token and error backoff, so stale callbacks no longer create competing sessions. Boot/package-replaced receivers re-arm an enabled listener. |
| Talkback | **Conversation → Talkback** and **Settings → Talkback · spoken answers** read each completed assistant answer aloud through an installed Android TextToSpeech engine. The engine, speech rate and pitch are configurable; the Test button speaks a sample. No download is needed. The pinned Spark-TTS and Kokoro packages are staged for the future on-device neural voice runtime. |
| Permissions | On launch the app requests microphone and notification access, restores a previously enabled listener, and prompts once a week for the battery-optimization exemption and All files access until granted. |
| Reinstall reuse | With **All files access**, models and runtimes live in `Download/PenGuru` and are discovered after an uninstall/reinstall by validating each file and byte length. Without it, `Android/media/<package>` survives APK updates but not a full uninstall. |
| Diagnostics | Battery, storage, Android version, CPU ABIs, model/runtime paths. |
| Export | MediaStore `Downloads/PenGuru`; the actual de-duplicated name is reported. |

### Storage paths

```
/storage/emulated/0/Download/PenGuru/Models/<model>/<variant>/
/storage/emulated/0/Download/PenGuru/Runtimes/<runtime>/
/storage/emulated/0/Download/PenGuru/            (exports too)
```

With **All files access**, `Download/PenGuru` is reused after an APK
uninstall/reinstall and the runtime/model files stay directly readable. The
app only touches that folder. Without the grant it falls back to
`/storage/emulated/0/Android/media/org.nuxel.penguru/`, and the effective path
is always shown in Settings → Storage. Existing files are migrated
automatically when the grant is enabled.

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

- `pwa/nuxel-apps/penguru/index.html`, `penguru.js`, `penguru.css`, `voice.js`, `talkback.js`
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
- APK rebuilt, `apksigner verify` shows v2 + v3 signatures, `versionCode=905`,
  `versionName=0.9.6-beta`.
- API 35 emulator checks: launch-time microphone/notification prompts, the
  battery dialog, the All files access dialog, a screen-off download that
  completed in the `dataSync` foreground service, and a full
  uninstall/reinstall where the app detected the existing `Download/PenGuru`
  model by file size without downloading it again.
- A mocked-bridge harness also resolves the SonarBird Voice tiny.en download by
  model **and** variant (pinned `ggml-tiny.en.bin`) while MiniLM still resolves
  its six encoder files.
- System-bar/cutout/IME insets are applied to a container view, so page text
  stays clear of the status bar and the three-button Android navigation row.

The API 35 x86_64 emulator was booted with `-gpu off` (the Swiftshader path
segfaulted on this host). It confirmed: the offline language-pack error (13)
now retries through the online recognizer instead of leaving the microphone
open; the 10-second dictation cap and 16-second hard watchdog release the mic;
the transcript auto-send path creates the USER/assistant messages; the
background service starts as `isForeground=true` with
`types=0x00000080` (microphone), posts notification `8801`, pauses and resumes
around in-app dictation, and stops cleanly from the UI and notification action.
The in-app “Listen for Penguru” path now waits for that pause to complete and
retries a busy recognizer instead of surfacing `ERROR_RECOGNIZER_BUSY`.

The v0.9.5-beta emulator run verified the new listening/hand-off state
machine: with SonarBird enabled, the ongoing notification is **SonarBird is
listening** while PenGuru is open (not paused); tapping the Conversation mic
changes it to **SonarBird paused · paused while the in-app microphone is in
use**, and it returns to **SonarBird is listening** after the in-app session
ends. A second empty in-app session opens Android's visible **Google voice
input** activity instead of leaving the owner with a closed microphone; Back
returns to PenGuru and SonarBird re-arms. The foreground recognizer now reports
English (US) to the service with `EXTRA_PREFER_OFFLINE=false` and partial
results enabled. A simulated `penguru_command` intent still auto-navigated to
Conversation and sent the transcript. The regex accepts “Penguru”, “Peng Guru”,
“Pen Guru”, “Penguro”, “Pinguru” and “Panguru”.

The v0.9.4-beta emulator run also verified: the native TextToSpeech bridge
reports **Android talkback ready · com.google.android.tts**; the conversation
Talkback toggle persists and a completed answer issues a real Google TTS
synthesis request; the mic toggle starts a 2.5-second auto-send session and a
manual session that waits for the second tap; choosing **Off · tap mic again**
persists `penguru-voice-autosend=0`; the manual second tap finalises and
releases the microphone (`No active record clients`); the Model library lists
**Spark-TTS · 0.5B talkback voice** (3.94 GB, CC-BY-NC-SA-4.0) and
**Kokoro · 82M talkback voice** (0.33 GB, Apache-2.0) with pinned hashes; a
simulated `penguru_command` intent auto-navigated to Conversation and sent the
transcript; and the SonarBird notification showed only **SonarBird paused** /
**SonarBird is listening** across foreground/background transitions, with no
`busy` text. Audio-in and wake-phrase acceptance on a physical phone is still
recommended.

## Security and limitations

- Bundled assets only; no remote HTML is loaded in the WebView.
- All download/extract paths are canonicalized and must stay inside the app's
  own storage roots; `..` and absolute paths are rejected.
- Runtime archives are pinned by URL and SHA-256 before unpacking.
- Cleartext HTTP is permitted only for the optional local/LAN Nuxel bridge.
- Microphone and notification permissions are checked on launch; the
  background listener and downloads remain explicit foreground services.
- All files access is optional and used only for `Download/PenGuru`; without
  it the app uses package-scoped storage.
- Neural inference is not embedded; the runtime installers stage verified
  artifacts and the built-in responder provides the default answers.
