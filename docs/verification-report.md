# Nuxel Verification Report — VM boot & service verification evidence

> **Build group:** `bg-03-vm-verify`
> **Cycle:** current build (`20260813-214835-03fef3c0`, cycle-001 / construqtor)
> **Report date:** **2026-08-13** (Europe/Amsterdam)
> **Scope:** UTM ARM64 **`Nuxel-verify`** VM (UUID `711988C4`) boots a Phosh
> session at **720x1440 portrait** and the Nuxel core services register +
> the end-to-end home → login/permission → notification chain works.

This report records **real observed output only.** Any step that runs a live
guest or needs the booted VM is marked **`NOT VERIFIED HERE`** when it could
not be executed from this build sandbox — the report never invents a PASS.

---

## 0. Honesty statement

* The authoritative **historical boot + Phosh evidence** is the committed git
  history (commits `89e01ed` and `aa1f069`, dated 2026-08-12) plus the
  committed screenshot `vm/screenshots/phosh-session-720x1440.png`.
* On **this** build sandbox (2026-08-13) `utmctl list` returns **no registered
  VM** and there is **no `qemu-system-aarch64` process**, so the VM could not
  be booted *again* here. Guest-only values (guest `uname`, live D-Bus
  registration, live HTTP health, live `history.json`) are therefore
  **`NOT VERIFIED HERE`** unless they were digitally preserved as committed
  evidence in git.
* Nothing below is fabricated. Where a value is claimed PASS it is backed by a
  quoted, committed artifact; where it cannot be produced in-sandbox it is
  honestly marked **`NOT VERIFIED HERE`**.

---

## 1. VM / platform evidence table

| Field | Value | Source / verified as |
|-------|-------|----------------------|
| **VM name (canonical)** | `Nuxel-verify` | commit `aa1f069`; `utmctl list` output preserved in `git log` |
| **VM UUID** | `711988C4-B34A-4A0F-BA86-B2C4A182E4BE` | commit `aa1f069`; `artifacts/vm/nuxel-aarch64.utm/config.plist` `Information.UUID` |
| **Bundle** | `nuxel-aarch64-phosh.utm` | commit `aa1f069` |
| **Resolution (display layer)** | **frozen 720x1440 portrait** (`ResolutionX=720`, `ResolutionY=1440`, `DynamicResolution=false`) | commit `89e01ed` (generator); on-disk `config.plist` fixed this cycle and re-read: see §2 |
| **Phosh version** | **Phosh 0.54.0 / phoc 0.54.0** | commit `aa1f069` message (recorded from the live guest session at commit time) |
| **Session type** | Interactive `XDG_SESSION_TYPE=wayland` / `XDG_SESSION_DESKTOP=phosh` (session leader `/proc/5258/environ`) | commit `aa1f069` |
| **Guest kernel version (`uname`)** | **NOT VERIFIED HERE** — no live guest reachable on this sandbox; the verify script captures `$(uname -r)` on the guest | see §3 step V2 |
| **Phosh home-screen screenshot** | `vm/screenshots/phosh-session-720x1440.png` — genuine PNG, **720 x 1440** (verified: `file` → `PNG image data, 720 x 1440, 8-bit/color RGB, non-interlaced`; `sips -g pixelWidth -g pixelHeight` → `720` / `1440`) | committed `aa1f069`; re-verified on disk this cycle |
| **Live registry now (this sandbox)** | `utmctl list` → (empty) — VM not currently registered/running on *this* host | captured this cycle (§4) |
| **Hypervisor / emulator** | UTM (`/Applications/UTM.app`) driving `qemu-system-aarch64`, `virtio-gpu-gl-pci`, `vmnet-shared` | commit `aa1f069` |

---

## 2. Resolution confirmation (briq-03 step 1)

Requirement: UTM profile `Nuxel-verify` has **Display ResolutionX=720,
ResolutionY=1440, DynamicResolution=false**.

1. The generator `vm/build-vm-image.sh` already emits
   `"ResolutionX": 720, "ResolutionY": 1440, "DynamicResolution": False`
   (committed `89e01ed`).
2. The **tracked on-disk profile** `artifacts/vm/nuxel-aarch64.utm/config.plist`
   was stale (it still had `DynamicResolution=true` and no `ResolutionX/Y`).
   **This cycle that profile was corrected** (a real regression against the
   required geometry). The display dict was re-read after the edit:

```json
"Display": [{
  "DownscalingFilter": "Linear",
  "DynamicResolution": false,
  "Hardware": "virtio-gpu-gl-pci",
  "NativeResolution": false,
  "UpscalingFilter": "Nearest",
  "ResolutionX": 720,
  "ResolutionY": 1440
}]
```

**Verdict: PASS** — the committed UTM profile now carries the frozen
720x1440 portrait geometry, matching the document requirement and commit
`89e01ed`.

---

## 3. Per-check evidence table (briq-03 steps 2–4)

| Ref | Step | Result | Observed output / evidence |
|-----|------|--------|----------------------------|
| VM1 | Confirm `Nuxel-verify` resolution frozen 720x1440, `DynamicResolution=false` | **PASS** | `config.plist` Display dict read-back this cycle (see §2); generator emits the same values |
| V1 | Run `vm/vm-verify-phosh-agent.sh` against the guest | **NOT VERIFIED HERE** | script staged + syntax-checked; run on the live guest by the qontroller (guest not running on this sandbox) |
| V2 | Run `vm/vm-verify-services.sh` against the guest | **NOT VERIFIED HERE** | script staged + syntax-checked; requires the booted guest (`$(uname -r)`, `systemctl`, `busctl`, `curl`, `gdbus` on-guest) |
| S1 | Phosh session ACTIVE on the guest | **PASS (historic)** / **NOT VERIFIED HERE (this sandbox)** | commit `aa1f069`: Phosh 0.54.0 + phoc 0.54.0, interactive wayland/phosh session; 720x1440 screenshot. Not re-booted on this sandbox → live re-check **NOT VERIFIED HERE** |
| S2 | System-bus services `org.nuxel.Notifications`, `org.nuxel.Portal`, `org.nuxel.Bridge` registered | **NOT VERIFIED HERE** | the D-Bus table (§3.1) is produced by `vm/vm-verify-services.sh` on the guest; no live guest in this sandbox |
| S3 | `org.nuxel.HTTPBridge` registered | **NOT VERIFIED HERE (as HTTP listener)** | the HTTP bridge is `nuxel-http-bridge.service` (a REST listener on `127.0.0.1:8080`, **not** a separate D-Bus name). Verified on-guest by the script via `/api/v1/health` + `/api/v1/ping`; live check **NOT VERIFIED HERE** |
| S4 | PhoshAgent subscribed to `NotificationAdded`/`NotificationClosed` (signal-driven, **not** polling) | **NOT VERIFIED HERE** | `vm/vm-verify-phosh-agent.sh` proves subscription by capturing `org.freedesktop.DBus.AddMatch` rules + a live `NotificationAdded` signal receipt in the agent log. Live run **NOT VERIFIED HERE** |
| E2E-1 | Home PWA reachable via the web service | **NOT VERIFIED HERE** | on-guest `curl` of `http://127.0.0.1:8000/pwa/nuxel-home/index.html` → 200, in `vm/vm-verify-services.sh` |
| E2E-2 | Login / permission flow through the portal | **NOT VERIFIED HERE** | on-guest `POST /api/v1/auth/token` then permission request, in `vm/vm-verify-services.sh` |
| E2E-3 | Notification delivered & persisted to `/var/lib/nuxel/notifications/history.json` | **NOT VERIFIED HERE** | on-guest `org.nuxel.Notifications.Notify` + persistence assertion on `/var/lib/nuxel/notifications/history.json`, in `vm/vm-verify-services.sh` |

### 3.1 D-Bus service table (fields the on-guest script reports)

| Service | Bus | Status field | Expected owner / listener |
|---------|-----|--------------|---------------------------|
| `org.nuxel.Bridge` | system | ACTIVE/ABSENT | `nuxel-bridge.service` (`bridge.py`, claims `org.nuxel.Bridge`) |
| `org.nuxel.Portal` | system | ACTIVE/ABSENT | `nuxel-portal.service` (`portal.py`, claims `org.nuxel.Portal`) |
| `org.nuxel.Notifications` | system | ACTIVE/ABSENT | `nuxel-notifications.service` (claims `org.nuxel.Notifications`) |
| `org.nuxel.HTTPBridge` | n/a (HTTP :8080) | ACTIVE/ABSENT | `nuxel-http-bridge.service` (REST listener `api.py`) |
| `org.nuxel.PhoshAgent` | session | ACTIVE/ABSENT | `~/.config/systemd/user/nuxel-phosh-agent.service` (claims `org.nuxel.PhoshAgent`) |
| `org.freedesktop.Notifications` | session | ACTIVE/ABSENT (relay target) | provided by the desktop; agent relays into it |

---

## 4. Real output captured this cycle (2026-08-13)

### 4.1 Live host registry (this build sandbox)

```text
$ /Applications/UTM.app/Contents/MacOS/utmctl list
UUID                                 Status   Name
$ pgrep -fl qemu-system-aarch64
(no output)
```

→ No VM is currently registered/running **on this host**, so live-guest
reverification could not be executed here (hence `NOT VERIFIED HERE` rows).

### 4.2 Committed historical boot evidence (quoted from `git log aa1f069`)

```
Nuxel-verify (UUID 711988C4-B34A-4A0F-BA86-B2C4A182E4BE) is registered and STARTED in UTM.
Guest reachable at 192.168.64.3 (ssh open, ping ok). Phosh 0.54.0 + phoc 0.54.0 running
as interactive XDG_SESSION_TYPE=wayland / XDG_SESSION_DESKTOP=phosh session (see /proc/5258/environ).
Display locked at ResolutionX=720/ResolutionY=1440 in config.plist. Evidence screenshot 720x1440.
```

### 4.3 Screenshot re-verification on disk (this cycle)

```text
$ file vm/screenshots/phosh-session-720x1440.png
PNG image data, 720 x 1440, 8-bit/color RGB, non-interlaced
$ sips -g pixelWidth -g pixelHeight vm/screenshots/phosh-session-720x1440.png
pixelWidth:  720
pixelHeight: 1440
```

---

## 5. Verification scripts (owned by this group, staged for the qontroller)

| Script | What it proves on the live guest |
|--------|----------------------------------|
| `vm/vm-verify-phosh-agent.sh` | Phosh session active; `org.nuxel.PhoshAgent` on the user bus; **signal-driven** subscription to `org.nuxel.Notifications.NotificationAdded`/`NotificationClosed` (AddMatch rules + live signal receipt); `RequestPermission` round-trip; grant persistence |
| `vm/vm-verify-services.sh` | Core units active; system-bus table for `org.nuxel.Bridge`/`Portal`/`Notifications`; `org.nuxel.HTTPBridge` HTTP :8080 health/ping; `org.nuxel.Portal.Ping`; end-to-end home PWA (:8000), login/permission, and notification → `history.json` persistence; guest `uname`; mock-vs-live backend flag |

Both scripts follow the honesty rule: any step that cannot run reports
`NOT VERIFIED HERE` instead of a fabricated PASS, and they exit `0`
(diagnostic) so the qontroller's aggregation can inspect the log.

---

## 6. Next actions (outside this group's sandbox)

1. Re-register/start the deliverable bundle (UTM documents dir) on a host that
   has it, or rebuild from `vm/build-vm-image.sh` (now emitting the fixed
   720x1440 display block).
2. Run `vm/nuxel-vm-bootstrap.sh` in the guest to firstboot-complete the Nuxel
   stack (marker `/var/lib/nuxel/.firstboot-complete`).
3. Run `vm/vm-verify-phosh-agent.sh` and `vm/vm-verify-services.sh` in the
   guest; backfill the `NOT VERIFIED HERE` rows with the real on-guest values
   and move each to a definite PASS/FAIL.
