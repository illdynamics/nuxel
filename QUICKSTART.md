# PenGuru Squad — Android Quickstart

## The APK you install

Install this file on your Android phone:

```
dist/android/penguru-squad-debug.apk
```

That is the complete standalone PenGuru Squad Android app (label **PenGuru
Squad**, package `org.nuxel.penguru`, version `0.9.0-beta` / versionCode
`900`). There is no other APK to install. The matching checksum is in
`dist/android/SHA256SUMS`:

```
83a24496632cdf0922ca860c47f830f5aa2e8895916b68b78de8521af990cb8b  penguru-squad-debug.apk
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
  revision directly to app storage, verifies its SHA-256, and records the
  license acknowledgement.
- **Settings → On-device dependencies** installs llama.cpp (arm64 or
  Snapdragon/OpenCL) and ONNX Runtime archives, verifies them, and unpacks them
  in app storage.
- **Settings → Voice** uses Android's built-in speech recognition, so the
  microphone transcript works without a Nuxel host.

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
- [ ] Open **Settings → Voice**, grant the microphone, and speak a message.
- [ ] **Export response** writes to `Downloads/PenGuru/`.

## Where files go

```
/storage/emulated/0/Android/data/org.nuxel.penguru/files/Models/<model>/<variant>/
/storage/emulated/0/Android/data/org.nuxel.penguru/files/Runtimes/<runtime>/
/storage/emulated/0/Download/PenGuru/            (exported responses)
```

The exact paths are shown inside Settings → Storage.

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
- Microphone use is foreground-only; listening stops when the app is hidden.
- Bundled web assets only — the WebView loads no remote HTML.
