# 08 — WEBKIT HOST, PERMISSIONS, MEDIA AND THE APPLICATION BRIDGE (P5 / §14–§16)

## 14.1 What the VM has vs what the handset had

| Piece (VM, measured this cycle) | VM | Handset before | Handset now |
|---|---|---|---|
| `nuxel-web.service` static server on `127.0.0.1:8000` | active | provided by `nuxel-session.sh` (`python3 -m http.server`, docroot `/usr/share/nuxel`) | same |
| `nuxel-http-bridge.service` on `127.0.0.1:8080` | active (dev mode, per-session tokens, CORS `http://127.0.0.1:8000`) | **not installed** | **not installed** (see below) |
| `nuxel-bridge.service` (D-Bus permission broker) | active | not installed | not installed |
| `nuxel-notifications` / `nuxel-portal` | active | not installed | not installed |
| `pwa/nuxel-apps/*` app pages | served | **404 — never staged on the live phone** | staged this cycle (see 14.3) |

The bridge python module requires `python3-dbus` **and** the D-Bus broker/portal
stack (`nuxel-bridge`, `nuxel-portal`, `nuxel-notifications`). This image has
`dbus-daemon` but not `python3-dbus`, and it has no portal/notification
infrastructure; the HTTP bridge alone would therefore answer 5xx for every
capability call. Rather than ship a half-installed API (which the mission
explicitly warns against), the handset keeps the launcher's own local-only
behaviour and reports capabilities truthfully:

* `js/app.js _requestCoreCapabilities()` calls `bridge.requestCapability()` for
  `phone:status` / `notifications:receive`; with no bridge the promise rejects and
  the launcher continues (it does not depend on it to render or to launch apps).
* Native-scheme registry entries (`nuxel-dialer://`, `nuxel-messages://`,
  `nuxel-contacts://`, `nuxel-camera://`, `nuxel-settings://`) have **no handler
  on this device** — there is no telephony/camera/modem userspace yet — so they
  stay visibly unimplemented rather than returning invented success.
* The four **PWA** registry entries (Mail, Calendar, Notes, Files) load as real
  pages from the same docroot, which is the "-PWA apps actually open" part of the
  application acceptance list.

This is deliberately *not* an attempt to fake VM parity. Bringing the real bridge
over means shipping `python3-dbus` + the bridge/portal/notifications services and
their D-Bus policy into the image; that is tracked as an explicit remaining item
(doc 12) rather than claimed.

## 14.3 The application payload was missing (found and fixed)

```
curl …/pwa/nuxel-apps/mail/index.html      -> 404
curl …/pwa/nuxel-apps/calendar/index.html  -> 404
curl …/pwa/nuxel-apps/notes/index.html     -> 404
curl …/pwa/nuxel-apps/files/index.html     -> 404
```

The live phone's docroot only ever received `pwa/nuxel-home` + `pwa/nuxel-common`
(the A29b live fix), while the **registry** addresses
`/pwa/nuxel-apps/<app>/index.html`. The five application trees (78 code files,
their own icons; 448 KB of real source) were staged to
`/usr/share/nuxel/pwa/nuxel-apps/` this cycle from a single verified tarball, and
the per-app `assets/` files are satisfied by the canonical single-source assets
already on the device (`nuxel-background.png`, `nuxel-boot-animation.mp4`)
instead of duplicating ~10 MB per app. Verified by HTTP afterwards (doc 10).

## 15 Media / web-process stability

Re-verified in the running runtime:

```
/run/nuxel-home.state  NUXEL_HOME_MEDIA enable_media=0 audio_sink=0
                       WebKitWebProcess alive (1), WebKitNetworkProcess alive (1)
```

`audio_sink_available()` checks for `libgstautodetect.so` (the sink whose absence
made WebKit 2.52 abort the web process in A29b); media is enabled only where it
exists, and the decision is written to the state file instead of assumed. Because
the phone launch mode removes the splash element entirely (doc 05), the
`<video>` never even starts here — belt and braces on top of the media gate.

New in A31: **web-process supervision**. The host now subscribes to
`web-process-terminated` and reloads the view (bounded to 5 attempts) instead of
leaving a blank screen forever, recording
`NUXEL_HOME_WEBPROC_TERMINATED reason=<code> reload=<n>` and
`NUXEL_HOME_WEBPROC_GIVEUP` if the bound is hit.

## 16 Security review outcome

1. **WebKit permissions — fixed.** A29's handler called
   `webkit_permission_request_allow()` for *every* request from *any* page. A31
   denies by default, allows only from the trusted local origin
   (`NUXEL_TRUSTED_ORIGIN`, default `http://127.0.0.1:8000`), and only for the
   capability the launcher actually uses (notifications). User-media
   (camera/microphone) is explicitly denied because this kernel has no working
   media path — the launcher then reports it truthfully instead of holding a
   permission it cannot use. Every decision is logged:
   `NUXEL_PERMISSION type=… uri=… trusted=0|1 allow=0|1 reason=…`.
2. **HTTP bridge** — not installed on the handset, so there is no local API
   surface to restrict. The VM's configuration (bind `127.0.0.1`, explicit CORS
   allow-list, per-session tokens) is recorded in doc 01 as the reference for
   when it is ported.
3. **Live console** — unchanged; the USB CDC-ACM console remains the only
   external channel and is preserved throughout (no new network exposure was
   introduced: the phone still has only `lo` up).
4. **Deployment** — every file moved with gzip+base64 chunking, per-chunk
   acknowledgement against the cumulative file length, final gunzip + SHA-256
   comparison, `install` (atomic) and a re-hash **of the installed path**; the
   transfer tool's length-accounting bug found this cycle is fixed in the repo.
5. **Restarts** — all launcher units now carry bounded restart policy (doc 06 §10.4).
6. **Display** — no periodic panel re-initialisation (doc 06 §10.2) and paced
   presentation.
7. **Touchscreen** — armed exactly once at startup, then read-only; no repeated
   `fb0/blank` transitions while the launcher runs (mission §11.4).
