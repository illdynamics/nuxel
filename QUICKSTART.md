# PenGuru Squad — Android Quickstart

## The APK you install

Install this file on your Android phone:

```
dist/android/penguru-squad-debug.apk
```

That is the complete standalone PenGuru Squad Android app (label **PenGuru
Squad**, package `org.nuxel.penguru`, version `0.9.9-beta` / versionCode
`909`). There is no other APK to install. The matching checksum is in
`dist/android/SHA256SUMS`:

```
847b68829052059e521bdde3faf2309057fc20ff6400d5b56c237907faca5cf0  penguru-squad-debug.apk
```

The APK is signed with the repository's stable debug identity, so it installs
as an in-place upgrade over earlier builds of the same app.

## Install it

Phone requirements: Android 8.0 (API 26) or newer, arm64 recommended.

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

## It works without a Nuxel server

The app no longer asks for a Nuxel API URL or launcher token. It starts an
**on-device engine** inside the APK:

- Conversation, routing, device diagnostics and voice work immediately.
- **Model library → Download to this phone** downloads the pinned Hugging Face
  revision directly to the phone, verifies its SHA-256, and records the license
  acknowledgement. Downloads run in a data-sync foreground service and keep
  going with the screen off. **Whisper · tiny.en speech recognition** is in the
  list and powers the bundled offline transcription fallback.
- **Settings → On-device dependencies** includes the bundled whisper.cpp speech
  engine (no runtime download) and installs llama.cpp (arm64 or
  Snapdragon/OpenCL) and ONNX Runtime archives, verifies them, and unpacks them.
  An interrupted download resumes from its `.part` file.
- **Settings → Voice** uses Android's built-in speech recognition, so the
  microphone transcript works without a Nuxel host. It prefers the phone's
  normal online recognizer, keeps partial hypotheses, and falls back to the
  visible Android voice-input screen if the silent recognizer keeps hearing
  nothing. The microphone closes as soon as speech ends and the transcript is
  sent automatically to the Conversation page.
- **Settings → SonarBird background listening** starts a persistent microphone
  foreground service with a notification. Say “Penguru” (or “Peng Guru”,
  “Pen Guru”, “Penguro”, “Pinguru”) and then a question to talk to PenGuru while
  the app is in the background. SonarBird stays armed while the app is open and
  pauses only while the in-app mic is recording; the Conversation page shows its
  live state. Android may require you to allow notifications and to tap the
  ongoing notification to bring the chat forward on some releases/OEMs; the
  heard command is still auto-sent.
- On every launch PenGuru checks microphone, notification, battery and storage
  permissions and restores the listener if you had enabled it. Accept the
  battery-optimization prompt so Android does not stop background work, and
  accept **All files access** so a reinstalled APK can reuse
  `Download/PenGuru` instead of downloading models again.

The optional `Nuxel host` engine mode remains available in Settings for owners
who already run the PenGuru service. It is not required and is not the default.

## First-run checklist

- [ ] App opens to the PenGuru Squad home screen (no blank/white page).
- [ ] Conversation is enabled and a message returns an on-device answer.
- [ ] **Model library** shows ChatBird, CodeBird and SonarBird with
      **Download to this phone** buttons.
- [ ] Tick the license checkbox, download a model, and watch progress.
- [ ] **Settings → On-device dependencies** lists llama.cpp / ONNX Runtime
      install buttons and the storage paths.
- [ ] Tap the Conversation mic (or **Settings → Voice**), grant the
      microphone, and speak a message. The mic should close at the end of
      speech and the message should appear and send on the Conversation page.
      If the silent recognizer hears nothing twice, Android's visible voice
      input screen opens as a fallback; speak there and it still sends.
- [ ] Accept **Settings → Allow all files access** and **Disable battery
      optimization** so reinstall reuse and screen-off downloads work.
- [ ] Tap **Start background listening**, allow the notification permission,
      press Home, say “Penguru, what is the battery?”, and confirm the ongoing
      notification / conversation.
- [ ] **Export response** writes to `Downloads/PenGuru/`.

## Where files go

```
/storage/emulated/0/Download/PenGuru/Models/<model>/<variant>/
/storage/emulated/0/Download/PenGuru/Runtimes/<runtime>/
/storage/emulated/0/Download/PenGuru/            (exported responses)
```

With **All files access**, these files survive an APK uninstall/reinstall.
Without it the app falls back to package-scoped storage, which Android deletes
on uninstall. The exact effective paths are shown inside Settings → Storage.

## Rebuilding the APK

```sh
./android/penguru-squad/scripts/build-apk.sh
```

Output is rewritten to `dist/android/penguru-squad-debug.apk` plus
`dist/android/SHA256SUMS`. See `android/penguru-squad/README.md` for SDK
prerequisites.

## Limitations

- Model weights and runtime archives are not embedded in the APK; the app
  downloads them on demand.
- The built-in responder is the default conversational engine. Neural
  generation requires a native model runtime loaded by the app; the download
  and installation controls stage the model and runtime artifacts on the phone.
- Android blocks executing arbitrary binaries downloaded into app data on
  modern releases. The installer keeps the archives and unpacked files for a
  future bundled/JNI runtime and for inspection.
- Microphone use is foreground-only unless you explicitly start **SonarBird
  background listening**. That mode keeps a microphone foreground service and
  a persistent notification running; grant the battery exemption to reduce the
  chance of Android stopping it.
- **All files access** is optional but required for reinstall-safe downloads.
  PenGuru only reads and writes its own `Download/PenGuru` folder.
- Android 10+ may block a background activity launch. If “Penguru” is heard
  while the app is closed, tap the ongoing notification to open the chat; the
  command is delivered and auto-sent.
- Bundled web assets only — the WebView loads no remote HTML.
