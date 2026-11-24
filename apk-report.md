# PenGuru Squad — Android APK Port Verification Report

**Date:** 2026-11-23  
**Branch checked:** `feat/android-penguru-squad`  
**HEAD:** `fc0cbc1c718aed8c324542cc425f940d5c9aea9c` — `feat(android): package PenGuru Squad APK with all settings in-app`  
**Working tree:** 15 tracked files modified, plus this report and `QUICKSTART.md`  
**Artifact:** `dist/android/penguru-squad-debug.apk`  
**SHA-256:** `be8e5b2381c81411ccae5f6b529f33d8999f6e893e6dcef8d7d644dc3e5915e8`  
**Package/version:** `org.nuxel.penguru` / `versionCode=809`, `versionName=0.8.9-beta`  
**Min/target SDK:** 26 / 35  
**Signing:** debug identity, APK Signature Scheme v2 + v3 verified  
**Verification device:** headless Android 15 (API 35) x86_64 emulator

---

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
