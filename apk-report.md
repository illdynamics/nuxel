# PenGuru Squad — Android APK Port Verification Report

**Date:** 2026-11-24
**Branch checked:** `feat/android-penguru-squad`
**HEAD:** v0.9.9-beta on `feat/android-penguru-squad`
**Working tree:** v0.9.9 wake-word, forced-mode and SonarBird reliability repair
**Artifact:** `dist/android/penguru-squad-debug.apk`
**SHA-256:** `847b68829052059e521bdde3faf2309057fc20ff6400d5b56c237907faca5cf0`
**Package/version:** `org.nuxel.penguru` / `versionCode=909`, `versionName=0.9.9-beta`
**Min/target SDK:** 26 / 35
**Signing:** debug identity, APK Signature Scheme v2 + v3 verified
**Verification device:** headless Android 15 (API 35) x86_64 emulator

---

## v0.9.9-beta — wake commands in every mode and SonarBird reliability

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `847b68829052059e521bdde3faf2309057fc20ff6400d5b56c237907faca5cf0`
- **Version:** `0.9.9-beta` (`versionCode=909`)
- **Min/target SDK:** 26 / 35
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified
- **Native code:** `arm64-v8a` + `x86_64`

  **Wake word in every mic mode.** Toggle, VAD and the five-second mode now
  strip a leading “Penguru” from the transcript and send only the remainder.
  A bare “Penguru” starts the follow-up microphone session instead of being
  sent as text.

  **Forced assistant commands.** “Penguru chat” selects ChatBird and “Penguru
  code” selects CodeBird. A combined command such as “Penguru code write a
  sort function” forces CodeBird and sends “write a sort function”. The
  selected mode survives the short SonarBird follow-up window.

  **Talkback separator cleanup.** The answer header “PenGuru · on-device” is
  spoken as “PenGuru on-device”; middle dots, bullets and arrows are removed in
  both the page and the native TextToSpeech bridge.

  **SonarBird reliability.** The persistent listener now uses the plain
  microphone source (not `VOICE_RECOGNITION`), shares one wake matcher between
  partial and final hypotheses, accepts more renderings of the invented word,
  runs a 15-second health check, recovers a stale in-app hand-off when PenGuru
  is reopened, and falls back to bundled whisper.cpp when Android recognition
  is absent or fails three times.

  **Verification:** `node --check` on all bundled JS, the extended
  `test-voice.mjs` state-machine / wake-mode / talkback checks pass, and the
  APK rebuilt with `versionCode=909`, `versionName=0.9.9-beta`, and v2 + v3
  signatures verified. Physical on-device audio acceptance is still required
  for the recognizer path; the emulator has no microphone input.

---

## v0.9.8-beta — immediate local capture and long-dictation repair

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `b3962f5b1a52585572eadca0167fa658b389f2fbb6ab8319deb43d1258f40395`
- **Version:** `0.9.8-beta` (`versionCode=908`)
- **Size:** 3,762,703 bytes
- **Min/target SDK:** 26 / 35
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified
- **Native code:** `arm64-v8a` + `x86_64`

  **Microphone capture now starts with the first tap.** When the Whisper
  tiny.en model is ready and the engine menu is left on **Automatic**, PenGuru
  uses its own `AudioRecord` capture and bundled whisper.cpp engine instead of
  waiting for Android's recognition service. This removes the late hand-off
  that opened a *new* microphone after the owner had already spoken and then
  returned `no_speech_detected`. The engine menu now distinguishes
  **Automatic** (empty component: local Whisper when installed) from an
  explicit **Android system default recognizer** entry, so the phone service
  can still be forced when preferred.

  **No more silent fallback capture.** If a vendor recognizer fails after the
  owner has spoken, any partial hypothesis is kept. Otherwise the page receives
  `speech_retry_needed` and tells the owner to start a new local recording
  rather than quietly recording silence.

  **Long dictations survive transcription.** The page watchdog after the second
  tap was raised from 14 s to 330 s, and the recording, transcribing and
  ready-to-send states are now distinct. A 56 s dictation is no longer dropped
  while Whisper is still working. Tap-to-talk recording is allowed for three
  minutes; Whisper transcription waits up to five minutes.

  **Recorder hardening.** `AudioSource.MIC` is tried before
  `VOICE_RECOGNITION`, microphone acquisition is retried for about two seconds
  while SonarBird releases the mic, a four-second no-audio guard fails loudly
  instead of recording silence, and the existing noise-suppression / AGC /
  echo-cancellation path is attached when supported. Short real utterances
  such as “okay” and “thank you” are no longer discarded when voice energy was
  detected.

  **Emulator verification (API 35 x86_64, headless, no audio input):**
  installed `versionCode=908` / `versionName=0.9.8-beta`; the page loaded and
  reported `whisper_ready=true`. With the persisted engine set to `whisper`
  and again with the default engine (`""`) the first mic tap immediately
  produced **“Microphone open · recording on this device”** and logcat showed
  `whisper capture started mode=toggle silence=0 fixed=0 deadline=180000`.
  The second tap switched the UI to **“Recorded · transcribing on this
  device…”** (`mic-button transcribing`), the bundled CLI transcribed the
  2.8 s silent emulator capture in 12.1 s, and the session ended cleanly with
  **“No speech detected”** (expected because this emulator was started with
  `-no-audio`). `node pwa/nuxel-apps/penguru/test-voice.mjs` also passes,
  including a late-result check that proves the old 14 s watchdog no longer
  discards a transcript.

---

## v0.9.7-beta — Whisper fallback and Silero 404 repair

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `c8105d0b2b3d8b3326b17a0871407affe92c4c3816c0daedc0b0620ad9f44e9d`
- **Version:** `0.9.7-beta` (`versionCode=907`)
- **Size:** 3,758,607 bytes
- **Min/target SDK:** 26 / 35
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified
- **Native code:** `arm64-v8a` + `x86_64`

  **Silero VAD 404 fixed.** The pinned upstream path was wrong. The file is
  `src/silero_vad/data/silero_vad.onnx`, not `src/silero_vad.onnx`. The card now
  pins 2,204,103 bytes and SHA-256
  `f6f4407b41e05e277e7f5cfd9b9ae957b1dfe763c6076a934734c0b448e09b31`.
  Verified on the API 35 emulator through the app's `DownloadService`: job
  `model-silero-vad-silero-vad-onnx-…` reached `ready`, received 2,204,103
  bytes, and installed at `…/Models/silero-vad/silero-vad-onnx`.

  **Whisper is now both an install-list and download-list item.**
  Settings → On-device dependencies shows **Whisper.cpp · on-device speech
  engine**, bundled in this APK for `arm64-v8a` and `x86_64`. Model library
  shows **Whisper · tiny.en speech recognition (SonarBird Voice)** with the
  pinned 77.7 MB `ggml-tiny.en.bin` download.

  **Voice transcription no longer depends on a Google/vendor recognizer.**
  `WhisperRecognizer` records 16 kHz mono PCM with `AudioRecord`, applies
  adaptive RMS endpointing, writes a temporary WAV, and runs the bundled
  whisper.cpp `v1.9.6` CLI against the downloaded model. Android
  `SpeechRecognizer` remains primary; Whisper is selectable in the speech-engine
  picker and is used automatically when no recognizer exists or Android returns
  no speech twice.

  Emulator verification: the bundled `whisper-cli` transcribed the upstream
  `jfk.wav` sample as “And so my fellow Americans ask not what your country can
  do for you, ask what you can do for your country.” in 4.8 s (11 s audio,
  2 threads). The app's own bridge reported `whisper_ready=true`, captured
  89,600 bytes of silence in `toggle` mode, ran transcription, and returned the
  expected `no_speech_detected` for the silent input. The extracted
  `nativeLibraryDir/libwhisper-cli.so` also executed successfully under the
  APK's UID.

## v0.9.6-beta — adaptive VAD, tap-to-send and voice commands

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `bc7e9e29c34f5d61620c4da9a1d9f5f6d7e6f48cd56d1fd980cd5fa841a19fd2`
- **Version:** `0.9.6-beta` (`versionCode=906`)
- **Min/target SDK:** 26 / 35
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified

  Voice activation now has three explicit policies. The Conversation default is
  **tap to talk; tap again to stop, transcribe and send**. `vad` mode uses an
  adaptive RMS voice-activity detector with a configurable 0.5–2.5 s
  end-of-speech window instead of the old fixed 2.5 s recognizer timeout.
  `fixed` mode keeps the microphone open for five seconds and then sends the
  whole window; the **Speak a message · 5 seconds** button always uses it.

  SonarBird now shows the live partial sentence in the persistent notification,
  finalises on VAD-detected end-of-speech, and supports **Send now** and
  **Stop listening** actions. Voice commands `stop`, `stop listening`, `cancel`,
  `never mind`, `that's all`, `send`, `send it`, `Penguru stop` and
  `Penguru send` are recognised natively in both the foreground mic and the
  background listener. Installed GrapheneOS / Google / vendor recognition
  services are selectable in Settings; Android TTS engine discovery continues to
  expose Piper / Spark when the phone installs them as TTS engines. Android
  `NoiseSuppressor`, AGC and echo cancellation are reported, and pinned
  **Silero VAD ONNX** and **RNNoise 0.2** entries are available in the Model
  library.

## v0.9.5-beta — live SonarBird foreground listening and reliable dictation

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `b626669366d684a13910eb3c3df894395db9b6883c1ea8b545fec032cf3fad42`
- **Version:** `0.9.5-beta` (`versionCode=905`)
- **Size:** 1,784,136 bytes
- **Min/target SDK:** 26 / 35
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified
- **Verification device:** headless Android 15 (API 35) x86_64 emulator

  SonarBird is no longer paused for the whole time PenGuru is visible. It stays
  armed while the app is open, pauses only for the in-app microphone session
  (`SonarBird paused · Paused while the in-app microphone is in use`) and
  re-arms about a second after the transcript/error. The Conversation page has
  a live “SonarBird is listening…” row. This removes the previous behaviour in
  which starting background listening while looking at the app appeared to do
  nothing at all.

  Foreground dictation now prefers the phone's normal recognizer instead of
  forcing the offline language pack; partial hypotheses are retained and sent
  when the recognizer ends with `no_speech_detected` or a timeout. The
  `onEndOfSpeech` finalisation is delayed, the second-tap watchdog is 9 s, and
  the JavaScript fallback allows 45–90 s so the visible fallback is not closed
  while the owner is speaking.

  If the in-process recognizer is unavailable, or two consecutive sessions
  hear nothing, the app launches Android's visible
  `ACTION_RECOGNIZE_SPEECH` activity. Its result is delivered through the same
  transcript → auto-send → Conversation path. The system activity is treated as
  a child session, so MainActivity `onStop` and the page's visibility handler
  do not discard its result.

  The wake pattern now accepts `Penguru`, `Peng Guru`, `Pen Guru`, `Penguro`,
  `Pinguru` and `Panguru`, and partial results can hand off “Penguru <question>”
  immediately.

  Emulator verification: notification was **SonarBird is listening** with the
  app open; tapping the mic changed it to **SonarBird paused** and it returned
  to listening after `NO_SPEECH_DETECTED`; a second empty session opened
  Google's voice-input activity; Back returned to PenGuru and SonarBird
  re-armed. A simulated `penguru_command` intent auto-navigated to Conversation
  and sent the transcript. The JS voice state machine was also exercised with a
  mocked native bridge for auto-send, manual second-tap send, “Peng Guru”
  wake-word send, wake-word-only follow-up and no-speech handling.

## v0.9.4-beta — talkback, conversation mic and silent wake hand-off

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `2cd79bfa2590349f4deb3dcef8d3718e16b1eba56ecfc23ad275e40a02da67bc`
- **Version:** `0.9.4-beta` (`versionCode=904`)
- **Size:** 1,780,040 bytes
- Added a native Android `TextToSpeech` talkback bridge (`ttsStatus`,
  `ttsEngines`, `ttsConfigure`, `ttsSpeak`, `ttsStop`) and the manifest
  `TTS_SERVICE` query. Conversation now has a **Talkback** toggle, and Settings
  has engine, rate, pitch, Test and Stop controls. Completed assistant answers
  are read aloud through an installed engine. On the API 35 emulator the bridge
  reported **Android talkback ready · com.google.android.tts**, and a completed
  answer produced a real Google TTS synthesis request.
- Added pinned talkback voice packages to the Model library:
  **Spark-TTS · 0.5B** (14 files, 3,943,495,496 bytes,
  `SparkAudio/Spark-TTS-0.5B@642071559bfc6346c2359d19dcb6be3f9dd8a05d`,
  CC-BY-NC-SA-4.0) and **Kokoro · 82M** (4 files, 328,261,437 bytes,
  `hexgrad/Kokoro-82M@f3ff3571791e39611d31c381e3a41a3af07b4987`,
  Apache-2.0). Every file has a pinned URL, size and SHA-256; the APK does not
  bundle the weights.
- Added a Conversation mic icon. Tap once to record an ad-hoc request, tap
  again to finalise and send, or auto-send after a configurable silence window
  (off, 1.5 s, 2.5 s, 4 s, 7 s). The same select is in Settings. `voice.js`
  distinguishes `finishSpeechRecognition()` (deliver the hypothesis) from
  `stopSpeechRecognition()` (discard), and preserves a transcript in the
  composer when auto-send is off. The emulator verified both the 2.5-second
  auto-send session and the manual “tap the mic again” path; the second tap
  left `No active record clients`.
- SonarBird no longer writes **“Android speech service busy”** to the ongoing
  notification. Busy/client errors are treated as a normal hand-off: the
  recognizer is released, the notification stays on “Listening for Penguru…”,
  and a fresh session is scheduled with backoff. The notification title is
  **SonarBird paused** while the app is open, **PenGuru request ready** after a
  command is captured, and **SonarBird is listening** otherwise.
- When “Penguru” + the sentence are heard, the service closes the recognizer
  immediately, persists the command and launches PenGuru. A simulated
  `penguru_command` intent on the emulator auto-navigated to Conversation,
  showed **“Heard ‘check the battery’ · sent automatically”**, added the user
  message and rendered the SYSTEM diagnostics reply.
- `versionName`/`versionCode` and the PWA `pwa_version` bumped to
  `0.9.4-beta` / `904`.

## v0.9.3-beta — SonarBird and in-app microphone hand-off

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `0dbc36d14824c349351389ccd8a35ab0ebc71ae534b54530d90910029d8355f1`
- **Version:** `0.9.3-beta` (`versionCode=903`)
- **Size:** 1,767,658 bytes
- MainActivity now pauses the SonarBird service in `onStart` and releases its
  recognizer, so the first in-app microphone tap no longer races the persistent
  listener's session. The service is paused for as long as the app is visible
  and only resumes 900 ms after `onStop`; `onStartCommand` can no longer
  unpause it behind the foreground UI.
- Busy/client errors in the foreground path get six retries with a fresh
  recognizer and a pause hand-off between attempts (`350 ms × n`, capped at
  2.6 s). The PWA also retries `recognizer_busy`/`client_error` three times
  automatically, so the owner is not told to tap again for a transient hand-off.
- While paused, the ongoing notification says “SonarBird paused” and status
  JSON no longer carries a stale `recognizer_busy` error from an earlier
  session.
- `versionName`/`versionCode` and the PWA `pwa_version` were bumped to
  `0.9.3-beta` / `903`.
- Verified on an API 35 x86_64 emulator: with SonarBird running, opening
  PenGuru changed the ongoing notification to **SonarBird paused** / “Paused
  while PenGuru is open”; pressing Home resumed it as **SonarBird is
  listening**; returning to the app paused it again. No recognizer-busy error
  was reported by the service.

## v0.9.2-beta — launch permissions, background downloads and reinstall reuse

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `f2f7446cf1f106240de2fd154c6a01108b594f2ca25a484f2e24f17c98be795e`
- **Version:** `0.9.2-beta` (`versionCode=902`)
- On launch the app requests microphone and notification access, restores a
  previously enabled SonarBird listener, and prompts for the battery exemption
  and (optionally) All files access.
- Downloads and archive extraction moved from `MainActivity` into a `dataSync`
  foreground `DownloadService` with a partial wake lock and Wi-Fi lock, so the
  screen going off no longer interrupts them. Interrupted jobs persist their
  spec and resume from `.part`.
- Foreground speech now waits for the background listener to release its
  recognizer and retries busy/client sessions; the background listener uses a
  per-session token, error backoff and language fallback so stale callbacks no
  longer create competing recognizers.
- With All files access, models and runtimes live in `Download/PenGuru` and are
  discovered after uninstall/reinstall by validating file names and sizes.
  Existing package-scoped downloads are migrated automatically.

The older sections below describe earlier builds and are retained for history.

---

## v0.9.1-beta — microphone repair, auto-send and persistent SonarBird

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `6a5860de1e39281ceb5b0221c56f5fce2118318324d4f58a300306d11a985641`
- **Package/version:** `org.nuxel.penguru` / `versionCode=901`, `versionName=0.9.1-beta`
- **Size:** 1,755,370 bytes
- **Min/target SDK:** 26 / 35
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified

### What changed

1. **Microphone cannot hang open.** Every native session now has a native
   16-second watchdog as well as the JavaScript deadline. Dictation asks the
   recognizer to finalize after ten seconds, natural end-of-speech calls
   `stopListening()`, and the recognizer is `cancel()` + `destroy()`ed after
   every result, error, Stop or timeout. A stuck speech service can no longer
   leave the microphone indicator on.
2. **Offline language-pack failures recover.** Android returns error 12/13
   when the selected language has no offline pack; the old build surfaced
   `speech_error_13` and stopped. The app now retries once through the phone's
   normal recognizer without the offline hint, falls back to `en-US`, and maps
   the remaining errors to actionable text.
3. **Transcripts auto-send.** Foreground dictation, in-app “Penguru” and the
   background listener all route through one `sendMessage` path. The transcript
   is placed in the message field, submitted immediately, and appears as the
   normal USER/assistant pair. The engine is enabled automatically if it was
   off.
4. **Persistent SonarBird listener.** New `WakeWordService` is a microphone
   foreground service (`foregroundServiceType="microphone"`) with a persistent,
   low-importance notification (`8801`) and a **Stop listening** action. Say
   “Penguru” alone and the next utterance is sent; say “Penguru <question>” in
   one go. Sessions are short and self-restarting, with a watchdog so a silent
   recognizer cannot hold the mic.
5. **Notification permission + boot/package-replaced re-arm.** The app requests
   `POST_NOTIFICATIONS` on Android 13+, declares `FOREGROUND_SERVICE`,
   `FOREGROUND_SERVICE_MICROPHONE`, `WAKE_LOCK` and `RECEIVE_BOOT_COMPLETED`,
   and `BootReceiver` restarts an enabled listener after reboot or an app
   update. Android may still refuse a microphone FGS started from the
   background; the setting stays enabled and the next in-app Start re-arms it.
6. **No microphone contention.** In-app dictation pauses the background
   recognizer; it resumes about 700 ms after the transcript/error is delivered.
7. **Command hand-off.** The service stores the pending command, launches
   `MainActivity` with `penguru_command`, and also puts it on the notification
   content intent. If Android blocks the background activity launch, opening
   the notification still auto-sends the stored command. A page-load queue
   prevents a command heard during WebView startup from being lost.

### Verification performed

- `node --check` on `penguru.js` and `voice.js`.
- `node pwa/nuxel-common/verify-wiring.js` — all 7 PWA surfaces OK.
- `node pwa/nuxel-common/test-bridge.js` — all shared-bridge tests pass.
- Rebuilt with `android/penguru-squad/scripts/build-apk.sh`; `apksigner verify`
  reports v2 + v3, `versionCode=901`, `versionName=0.9.1-beta`.
- API 35 x86_64 emulator (`-gpu off`):
  - Error 13 now retries through `NetworkSpeechRecognizer`; the 10-second
    endpointing cap stopped the session and released the mic with
    `stopDisabled=true`.
  - Injected native transcript callbacks produced USER “hello from the final
    build” and auto-sent it (“Sent automatically”).
  - “Penguru what is two plus two” sent only the command; “Penguru” alone
    entered follow-up listening and sent the next utterance.
  - Background service status: `running=true`, `listening=true`,
    `microphone=true`, `notifications=true`; `dumpsys` shows
    `isForeground=true`, `types=0x00000080` (microphone), notification `8801`.
  - Pause/resume around in-app dictation verified; Stop from the JS bridge
    removed the service and notification.
  - `am start ... --es penguru_command "what is the battery"` auto-sent
    “what is the battery” through the same hook used by the service.
  - Reinstalling the APK with the preference enabled triggered
    `MY_PACKAGE_REPLACED` and the service came back automatically.
- No `FATAL EXCEPTION` or service crash in logcat.

### Limitations

- The emulator has no audio input, so recognition accuracy was not measured;
  physical-phone audio acceptance is still recommended.
- Android 10+ background activity-launch restrictions may require tapping the
  ongoing notification to bring the conversation forward. The command is kept
  and auto-sent when the app opens.
- The phone's Android speech service may use the network depending on the
  device; PenGuru itself never sends audio to a Nuxel host.

---

## v0.9.0 standalone update — previous artifact

- **Date:** 2026-11-24
- **Artifact:** `dist/android/penguru-squad-debug.apk`
- **SHA-256:** `172f056e198d5e282809376d1e93086864fa8732d346c4cb46ba840e653c48d0`
- **Package/version:** `org.nuxel.penguru` / `versionCode=900`, `versionName=0.9.0-beta`
- **Size:** 1,743,004 bytes
- **Signing:** debug identity, APK Signature Scheme v2 + v3 verified

This release removes the Nuxel host requirement for ordinary Android phones.

### What changed

1. **On-device engine** — `pwa/nuxel-apps/penguru/local-engine.js` implements
   the `penguru` RPC verbs locally (status, models, downloads, conversation,
   diagnostics). The Android default engine mode is now `local`; no API URL,
   token, launcher or server is required.
2. **Real model downloads** — the Model library shows ChatBird, CodeBird,
   SonarBird MiniLM and Voice tiny.en cards with **Download to this phone**.
   `MainActivity` streams the pinned Hugging Face URL, resumes `.part` files,
   verifies the pinned SHA-256, writes `installed.json`, and reports progress.
   Files live under
   `/storage/emulated/0/Android/data/org.nuxel.penguru/files/Models/<model>/<variant>/`.
3. **Runtime installers** — Settings → On-device dependencies installs llama.cpp
   arm64, llama.cpp Snapdragon/OpenCL and ONNX Runtime Android (AAR), verifies
   SHA-256, and unpacks tar.gz/zip into
   `/storage/emulated/0/Android/data/org.nuxel.penguru/files/Runtimes/`.
4. **Microphone wiring** — Android `SpeechRecognizer` (prefer-offline) delivers
   transcripts to the PWA through `window.__nuxelSpeechResult`; the existing
   Web Audio path remains a fallback. Wake-phrase review still requires an
   explicit Send.
5. **Optional Nuxel mode** — the old connection form remains under Settings →
   Engine → Nuxel host for owners who run the service. It is no longer the
   default and is not needed on a regular phone.

### Verification performed

- JS syntax checks on all bundled files.
- `verify-wiring.js`: all 7 PWA surfaces OK.
- `test-bridge.js`: all shared bridge tests pass.
- Node harness with a mocked `NuxelAndroid` bridge: status, four model cards,
  pinned download spec, READY/installed transition, runtime install spec,
  SYSTEM reply (device/storage diagnostics), CODE reply, diagnostics.
- APK rebuilt and `apksigner verify` reports v2 + v3.

### Follow-up fixes (2026-11-24, same 0.9.0-beta build)

1. **Voice tiny.en downloads work.** `start_download` now resolves a package by
   `model_id` **and** `variant_id`. Two SonarBird cards legitimately share the
   `sonarbird` model id, so the previous lookup always selected the MiniLM card
   and returned `unknown_package` for `speech-whisper-tiny-en`. A Node harness
   confirms the tiny.en card now produces the pinned
   `ggerganov/whisper.cpp` / `ggml-tiny.en.bin` download spec, and MiniLM still
   resolves its six encoder files.
2. **System bars no longer overlap the UI.** The WebView is wrapped in a padded
   `FrameLayout`; window insets for the status bar, cutout, IME and the Android
   back/home/recents navigation row are applied to that container. The page
   viewport is genuinely reduced, so header text can no longer run under the
   status bar and controls cannot sit under the three-button navigation row.
3. **Speech recognition lifecycle hardened.** Each request is a numbered
   session; stale callbacks and queued restarts are ignored after Stop.
   `ERROR_CLIENT` / `ERROR_RECOGNIZER_BUSY` are retried once without the
   offline-only hint, the 5-second button finalizes via `stopListening()`, and
   Stop always invalidates pending work. The Web UI now re-enables all voice
   controls in a `finally` block and reports actionable errors.

### Known limitation

Android blocks executing arbitrary binaries downloaded into app data on modern
releases. The installers stage verified runtime archives and the built-in
on-device responder provides default answers; full neural generation still
needs a bundled/JNI runtime. The headless emulator on this build host segfaulted
before boot, so physical-device acceptance of the new flows remains required.

The sections below describe the earlier `0.8.9-beta` client-only verification
and are retained for history.

## 1. Executive verdict

### Is this the full APK Android port of PenGuru Squad?

**Yes — as the Android client/front-end port of the current PenGuru Squad application.**  
The APK bundles the complete current PWA surface (HTML/CSS/JS/assets), serves it from a private in-APK `https://appassets.androidplatform.net` origin, and adds the Android-specific actions a bare WebView cannot perform (response export, external provenance links, microphone permission). All four in-app sections, the connection form, the model library, the conversation flow, diagnostics, and the voice UI are present and were exercised on an Android 15 emulator against a mock Nuxel bridge.

**No — if “full AI subsystem” means a self-contained inference product.**  
The APK does **not** contain ChatBird/CodeBird/SonarBird model weights, llama.cpp, ONNX Runtime GenAI, or any inference runtime. It is the owner-facing client for a reachable Nuxel host running the PenGuru backend. No model can run on the Android phone from the APK alone. The current backend itself is still a partially implemented beta, as documented in `services/nuxel-penguru/README.md`.

### Current achievement in one line

**The Android APK port of the PenGuru Squad client is functionally complete for the current PWA surface and verified end-to-end against a mock bridge; the overall PenGuru AI subsystem remains a backend-dependent beta, and the APK is not yet release-signed or physically accepted on the S10+.**

---

## 2. What was verified

### 2.1 Source and static verification

| Check | Result |
|---|---|
| `node --check` on `penguru.js`, `model-library.js`, `voice.js`, `bridge.js` | PASS |
| `node pwa/nuxel-common/verify-wiring.js` | PASS — `ALL 7 PWA SURFACES OK`, including `org.nuxel.PenGuru` |
| `node pwa/nuxel-common/test-bridge.js` | PASS — all bridge/token/version tests, including `standalone android token reaches /rpc ok` |
| `test_registry.py` | PASS — manifest schema, immutable revisions, signature/self-test trust gates |
| `test_routing.py` | PASS — routing, adversarial prompt handling, no SYSTEM dispatch from untrusted text |
| `test_installation.py` | PASS — 6 tests |
| `test_worker_protocol.py` | PASS — 4 tests |
| `test_downloader.py` | PASS — 3 tests |
| `python3 -m compileall -q services/nuxel-penguru` | PASS |
| `git diff --check` | PASS — no whitespace errors |
| Manifest signatures against `services/nuxel-penguru/keys/owner-release-public.pem` | PASS — all 4 repository manifests verify (`chatbird`, `codebird`, `sonarbird-onnx`, `sonarbird-speech`) |

### 2.2 Build and packaging verification

The APK was rebuilt from the current working tree with:

```sh
ANDROID_SDK_ROOT=/tmp/android-sdk ./android/penguru-squad/scripts/build-apk.sh
```

Result:

- `aapt2 compile` and `aapt2 link` succeeded.
- `javac` succeeded (one deprecation note, no errors).
- `d8`, `zipalign`, and `apksigner` succeeded.
- APK verifies with v2 and v3 signatures.
- `versionCode=809` and `versionName=0.8.9-beta` are derived from `VERSION` (`v0.8.9-beta`) using `--replace-version`.
- `android/penguru-squad/assets/public` was regenerated by `scripts/stage-web.sh`.
- Every staged web asset is byte-identical to its source under `pwa/nuxel-apps/penguru` and `pwa/nuxel-common`.
- The assets extracted from the signed APK are byte-identical to the staged tree.

### 2.3 Runtime verification on Android 15 (API 35)

Installed and launched:

```sh
adb install -r dist/android/penguru-squad-debug.apk
adb shell am start -W -n org.nuxel.penguru/.MainActivity
```

Observed:

- `topResumedActivity=org.nuxel.penguru/.MainActivity`
- No `AndroidRuntime` crash.
- WebView loaded `https://appassets.androidplatform.net/pwa/nuxel-apps/penguru/index.html`.
- Page title: `PenGuru Squad`.
- Four sections rendered: **Conversation**, **Model library**, **Settings**, **Diagnostics**.
- In-app connection form rendered with API URL and launcher-token fields.
- `window.NuxelAndroid` bridge present.
- `window.isSecureContext === true`.
- Bridge protocol version `1`; `bridge.js` loaded as the shared module.

### 2.4 End-to-end bridge verification

A mock Nuxel HTTP bridge was run on the host, exposed to the emulator with `adb reverse`, and made to enforce the real launcher-authority rule (`/rpc` with namespace `penguru` requires the owner-pasted launcher token; a self-bootstrap token is refused).

Verified request path:

```text
GET  /api/v1/ping              Authorization: Bearer <owner token>  -> 200
GET  /api/v1/capabilities      Authorization: Bearer <owner token>  -> 200
POST /api/v1/rpc               body={"app_id":"org.nuxel.PenGuru","namespace":"penguru","verb":"status",...}
                               Authorization: Bearer <owner token>  -> 200
```

The mock log confirmed the token was actually attached to `/rpc` (not only `/ping`):

```text
POST path=/api/v1/rpc
body={"app_id": "org.nuxel.PenGuru", "namespace": "penguru", "verb": "status", "params": {}}
auth='Bearer android-token-test'
```

UI results:

| Action | Observed result |
|---|---|
| Initial status | `PenGuru is OFF. Enable it to manage models and start a conversation.` |
| Enable | `IDLE · No model loaded · CPU · local only`; power button changed to `Turn PenGuru off` |
| Model library | 3 model cards rendered from backend status (ChatBird + CodeBird + SonarBird) |
| Provenance link | Model link present; click opened Chrome via `ACTION_VIEW` while the app remained on the asset origin |
| Submit prompt | `submit` sent over `/rpc` with the owner token; response polled through `get` |
| Conversation output | Route/engine/revision metadata and response text rendered |
| Export response | `Response saved to Downloads/PenGuru/penguru-response (2).txt`; file exists on device |
| Repeat export | `Response saved to Downloads/PenGuru/penguru-response (3).txt`; reported name matches actual file |
| Diagnostics | `diagnostics` RPC returned and rendered JSON |
| Clear conversation | `clear_all` sent; message list emptied |
| Disable | `set_enabled` with `enabled=false`; UI returned to OFF |
| Microphone permission | System dialog `Allow PenGuru Squad to record audio?` shown; grant persisted |

Microphone capture itself returned `Could not start audio source` on this emulator because it was started with `-no-audio` (no host audio input). That is an emulator limitation, not a WebView/permission failure; the Android permission request/grant path is verified. Physical microphone capture and wake-word accuracy remain unaccepted, consistent with the backend README.

### 2.5 Security checks performed

- Bundled assets only: the WebView start URL is the in-APK virtual origin; there is no remote HTML URL in the APK.
- `shouldInterceptRequest` serves only files under `assets/public`; path traversal (`..` and backslashes) is rejected with 404.
- External top-level `http`/`https` navigation is redirected to the owner's browser instead of loading in the WebView.
- The JavaScript bridge exposes only two methods: `saveText(filename, text)` and `openExternal(url)`.
- `openExternal` accepts only `http`/`https` URIs.
- Export filenames are sanitized (`[A-Za-z0-9._-]`, max 80 chars) and written only under `Downloads/PenGuru`.
- `android:allowBackup="false"`; the launcher token is stored in WebView local storage and not backed up.
- Cleartext HTTP is intentionally enabled for the local/LAN Nuxel bridge, and documented as a trust-boundary tradeoff.
- The bridge still enforces launcher identity and app binding server-side; CORS is only a transport allowlist.

### 2.6 APK contents

```text
AndroidManifest.xml
res/drawable-nodpi-v4/ic_launcher_foreground.png
res/mipmap-*/ic_launcher.png
res/mipmap-anydpi-v26/ic_launcher.xml
res/xml/network_security_config.xml
assets/public/assets/nuxel-penguru-squad.png
assets/public/pwa/nuxel-apps/penguru/app.json
assets/public/pwa/nuxel-apps/penguru/index.html
assets/public/pwa/nuxel-apps/penguru/manifest.json
assets/public/pwa/nuxel-apps/penguru/model-library.js
assets/public/pwa/nuxel-apps/penguru/penguru.css
assets/public/pwa/nuxel-apps/penguru/penguru.js
assets/public/pwa/nuxel-apps/penguru/voice.js
assets/public/pwa/nuxel-common/bridge-version.json
assets/public/pwa/nuxel-common/bridge.js
assets/public/pwa/nuxel-common/theme.css
classes.dex
META-INF/*
```

Permissions: `INTERNET`, `ACCESS_NETWORK_STATE`, `RECORD_AUDIO`.  
Microphone hardware is declared `required=false`.

---

## 3. Feature / capability scorecard

| Area | Status | Notes |
|---|---|---|
| Android APK shell and packaging | **Complete** | WebView shell, private asset origin, signed APK, versioning, icons, cleartext policy |
| Current PWA feature parity | **Complete** | Every current `pwa/nuxel-apps/penguru` file and shared bridge/theme asset is bundled |
| Conversation UI | **Complete (client)** | Submit, poll, cancel, clear, metadata, export; generation requires backend and models |
| Model library UI | **Complete (client)** | Cards, revision/license acknowledgement, download/cancel/delete, runtime override, progress polling; backend-gated |
| Settings / connection | **Complete** | API URL, launcher token, save/reconnect, forget; manual token re-mint needed after expiry |
| Diagnostics UI | **Complete (client)** | Fetch/render diagnostics JSON; backend-gated |
| Response export | **Complete** | MediaStore `Downloads/PenGuru`; actual de-duplicated name reported |
| External provenance links | **Complete** | `ACTION_VIEW` opens the owner's browser |
| Microphone permission flow | **Complete (framework)** | Dialog and grant verified; capture not physically accepted |
| Voice speech/wake UI | **Partial / beta** | UI and `getUserMedia` path present; depends on optional Voice tiny.en backend package; no always-on wake word |
| Launcher-bound token authority | **Complete** | Owner token carried on `/rpc`; self-bootstrap token refused by bridge |
| Standalone inference in APK | **Not implemented** | No llama.cpp/ONNX runtime or model weights in APK |
| Model downloads to phone | **Not applicable** | Downloads go to the Nuxel host, not stored in the APK |
| ONNX Runtime GenAI | **Not implemented** | Backend returns explicit unavailable; UI says so |
| Privileged writes / approvals | **Not implemented** | Backend gates remain closed |
| Generated-code execution | **Not implemented** | Responses are reviewable only |
| Background/always-on wake word | **Out of scope** | Foreground beta only |
| Release signing | **Not done** | Debug key only; release keystore must be owner-managed |
| Physical S10+ acceptance | **Not done here** | Verified on Android 15 emulator only |
| Full soak/thermal/suspend-resume | **Not done** | Backend release notes already list this as open |

---

## 4. Issues found and resolved

These were the substantive gaps between the branch tip and a working APK. They are now present in the working tree, rebuilt into the APK, and verified.

1. **Launcher token was not sent on `/rpc` in the standalone WebView.**
   - `bridge.js` only used the launcher-relay token for authority RPCs; a standalone WebView has no launcher parent frame.
   - Fixed by falling back to the owner-configured token resolved from in-app settings. The bridge still enforces `issuer == nuxel-launcher` and `token.app_id == body.app_id`, so a self-bootstrap token cannot gain authority.
   - Added a regression test in `pwa/nuxel-common/test-bridge.js` that asserts `/rpc` carries the owner token.
   - Verified on the emulator: the mock bridge logged `Authorization: Bearer <owner token>` on `penguru.status`.

2. **Response export did not work inside a bare WebView.**
   - Added `NuxelAndroid.saveText(filename, text)` using MediaStore on Android 10+ and app-scoped external Downloads on older versions.
   - The page prefers the Android bridge and falls back to a Blob download elsewhere.
   - Fixed a follow-on issue: when MediaStore de-duplicates a repeated filename, the bridge now queries the actual `DISPLAY_NAME` and reports the real saved name (for example `penguru-response (2).txt`), not the requested name.
   - Verified twice on the emulator with matching UI notice and on-disk filename.

3. **Hugging Face provenance links did not open from the WebView.**
   - Added `NuxelAndroid.openExternal(url)` and `shouldOverrideUrlLoading` handling.
   - Only `http`/`https` are accepted.
   - Verified: Chrome received `ACTION_VIEW` for the Hugging Face URL and PenGuru stayed on the bundled origin.

4. **APK version metadata was stale and not tied to the repository version.**
   - `build-apk.sh` now derives `versionCode`/`versionName` from `VERSION`, strips the leading `v`, and passes `--replace-version`.
   - Result: `versionCode=809`, `versionName=0.8.9-beta`.
   - `app.json` is now bundled, and the microphone capability is aligned between the app manifest and registry.

5. **Documentation drift: the top-level README claimed the GGUF manifests were unsigned.**
   - All four repository manifests actually verify against `keys/owner-release-public.pem`.
   - Corrected the README statement to say the manifests are owner-release signed and still require revision/license acknowledgement.

No blocker was found in the APK packaging, asset loading, token transport, export, external-link handling, or WebView lifecycle.

---

## 5. How it works

```text
Android APK (org.nuxel.penguru)
  └─ MainActivity (single WebView)
       ├─ loads https://appassets.androidplatform.net/pwa/nuxel-apps/penguru/index.html
       ├─ shouldInterceptRequest serves bundled assets/public/* only
       ├─ PenGuruChromeClient handles RECORD_AUDIO permission
       └─ NuxelAndroid JS bridge
            ├─ saveText()      -> MediaStore Downloads/PenGuru
            └─ openExternal()  -> ACTION_VIEW browser

Bundled PWA
  └─ pwa/nuxel-common/bridge.js
       ├─ /ping, /capabilities            -> Nuxel HTTP bridge
       └─ /rpc {namespace:"penguru", ...} -> requires launcher-bound token

Nuxel host (separate Linux/Nuxel OS)
  ├─ services/nuxel-bridge/src/api.py + penguru_api.py
  ├─ services/nuxel-penguru/service.py + scheduler + runtimes
  ├─ llama.cpp / model packages
  └─ minted one-hour launcher token
```

The APK is therefore a **client**, not a container for the AI stack. The phone needs a reachable Nuxel host, a bridge URL, and a freshly minted `org.nuxel.PenGuru` launcher token.

---

## 6. Remaining gaps and risks

### Blocking a “full standalone AI product” claim
- **No inference runtime or model weights in the APK.** ChatBird/CodeBird/SonarBird run on the Nuxel host.
- **No offline AI without a Nuxel host.** The “local” promise applies to the owner’s Nuxel device/service, not to an arbitrary Android phone.
- **Token lifecycle is manual.** Tokens are one-hour, launcher-bound, and must be re-minted after expiry; there is no pairing/refresh flow.
- **No ONNX Runtime GenAI adapter.** Selecting it returns an explicit unavailable error.
- **No privileged writes, approvals/rollback broker, or generated-code execution.** These remain closed by backend design.
- **No physically accepted microphone/wake-word path.** Foreground voice is beta; always-on/background wake word is out of scope.

### Release-readiness gaps
- **Debug signing only.** `CN=Android Debug` is fine for iteration, not release. Use an owner-managed keystore via `PENGURU_KEYSTORE`.
- **Physical S10+ acceptance not performed here.** Runtime verification was on an Android 15 x86_64 emulator.
- **Only API 35 was exercised.** `minSdk=26`; API 26–34 paths are built but not device-tested.
- **Real Nuxel host/model E2E not exercised in this run.** The bridge and model flows were tested with a protocol-compatible mock that enforced the launcher-authority rule.
- **No full soak/thermal/suspend-resume testing.**
- **Cleartext HTTP and mixed content are allowed.** Intended for a private LAN/loopback bridge; use trusted Wi-Fi or TLS termination otherwise.

### Backend status (from `services/nuxel-penguru/README.md`)
The backend is explicitly “a partially implemented, local-first subsystem, not a completed dual-runtime/voice product.” Its open items include real multi-gigabyte download UI acceptance, ChatBird generation on the handset, ONNX GenAI, broader SonarBird evaluation, physical microphone/wake acceptance, privileged writes, and full soak/thermal/UI acceptance. The APK does not hide or bypass those gates.

---

## 7. Artifact details

| Property | Value |
|---|---|
| Path | `dist/android/penguru-squad-debug.apk` |
| Size | 1,718,330 bytes (~1.7 MiB) |
| SHA-256 | `be8e5b2381c81411ccae5f6b529f33d8999f6e893e6dcef8d7d644dc3e5915e8` |
| Package | `org.nuxel.penguru` |
| Version | `0.8.9-beta` (`versionCode=809`) |
| Min / target SDK | 26 / 35 |
| Launch activity | `org.nuxel.penguru.MainActivity` |
| Signature schemes | v2 = true, v3 = true, v1 = false |
| Signer DN | `CN=Android Debug, O=Android, C=US` |
| Signer SHA-256 | `06e8553b4cf04de50cdf7d2ef54c8b2cffcf7f11ef26bfa9b875cb68d01e04d5` |
| Checksum manifest | `dist/android/SHA256SUMS` |

The SHA in `SHA256SUMS` matches the rebuilt APK.

---

## 8. Reproduce

```sh
# Build (expects Android SDK platform 35 + build-tools 35.0.0 and JDK 17+)
ANDROID_SDK_ROOT=/tmp/android-sdk ./android/penguru-squad/scripts/build-apk.sh

# Install
adb install -r dist/android/penguru-squad-debug.apk
adb shell am start -W -n org.nuxel.penguru/.MainActivity

# Local static checks
node --check pwa/nuxel-apps/penguru/penguru.js
node --check pwa/nuxel-apps/penguru/model-library.js
node pwa/nuxel-common/verify-wiring.js
node pwa/nuxel-common/test-bridge.js
python3 services/nuxel-penguru/tests/test_registry.py
python3 services/nuxel-penguru/tests/test_routing.py
python3 services/nuxel-penguru/tests/test_installation.py
python3 services/nuxel-penguru/tests/test_worker_protocol.py
python3 services/nuxel-penguru/tests/test_downloader.py
```

To connect to a real Nuxel host:

```sh
# On the Nuxel host, as root
python3 services/nuxel-penguru/tools/mint-android-token.py
```

Then in PenGuru Squad → Settings → Connection, enter the bridge URL (for example `http://192.168.1.20:8080/api/v1`), paste the token, and press **Save & reconnect**. The host bridge must allow the `https://appassets.androidplatform.net` origin for CORS (already included in the current unit and API code).

---

## 9. Bottom line

**The branch contains a complete Android client port of the current PenGuru Squad app, and the verified APK works as that client.** It loads its own bundled UI, connects to the Nuxel bridge with the owner-pasted launcher token, enables/disables PenGuru, renders the model library, submits and displays conversation responses, saves exports to Downloads, opens provenance links in the browser, and requests microphone permission correctly.

**It is not a full standalone Android port of the PenGuru AI subsystem.** The AI runtime, model weights, scheduler, downloader, and speech backend remain on the Nuxel host. The APK is the polished owner-facing client for that backend, not a replacement for it. The most important remaining work is real-host/model E2E acceptance, physical microphone/wake testing, a release signing identity, and the backend features that are still marked incomplete.

**Important repository-state note:** the fixes described above are currently **uncommitted** in the working tree on `feat/android-penguru-squad`. HEAD `fc0cbc1c` alone does not contain the `/rpc` token fix, export bridge, external-link bridge, or final versioning. Commit the 15 modified tracked files (including the rebuilt APK and `SHA256SUMS`) if you want the branch tip itself to represent this verified state.
