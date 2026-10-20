# Nuxel v0.6.3-beta — live S10+ userspace deployment report

**Date:** 2026-10-20  
**Host:** `dextronux` (Linux, repository `/x/nuxel`)  
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora Linux 43 ARM64,
kernel `4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64`  
**Transport:** USB CDC-ACM live console, `/dev/ttyACM0`,
`usb-Nuxel_Nuxel_S10+_Live_Console_NUXEL-S10PLUS-0001-if00`, USB ID `18d1:4ee7`  
**Privilege:** root shell on the device (`uid=0(root)`)  
**Safety:** userspace-only. No flash, partition, bootloader, kernel, modem or
firmware write was performed. No reboot was performed.

Evidence files referenced below are in this directory (`docs/live/v0.6.3-beta-20261020/`).

---

## 1. Active userspace paths (confirmed before deploy)

| Item | Live value | Evidence |
|---|---|---|
| Active static webroot | `/usr/share/nuxel` | `readlink -f /proc/5396/cwd` |
| Actual HTTP server | PID 5396: `python3 -m http.server 8000 --bind 127.0.0.1` | `ss -ltnp`, `ps` |
| Launcher URL | `http://127.0.0.1:8000/pwa/nuxel-home/index.html` | HTTP 200 |
| `nuxel-web.service` | `inactive (dead)`, disabled | `02-nuxel-web-status.txt` |
| Bridge unit | `ExecStart=/usr/bin/nuxel-bridge` | `01-service-units.txt` |
| HTTP bridge unit | `ExecStart=/usr/bin/nuxel-http-bridge` | `01-service-units.txt` |
| Canonical bridge source dir | `/usr/lib/nuxel/nuxel-bridge/` | `03-bridge-paths.txt` |

The deploy document calls for restarting `nuxel-web`, but on this live image
`nuxel-web.service` is disabled/inactive and port 8000 is owned by the
session-managed `python3 -m http.server` started by `/usr/lib/nuxel/nuxel-session.sh`.
Starting `nuxel-web` would have collided with PID 5396. Static files are served
directly from `/usr/share/nuxel`; no web-service restart was required. The two
bridge services were restarted.

Because the running units execute `/usr/bin/nuxel-bridge` and
`/usr/bin/nuxel-http-bridge` (standalone copies), while the payload's documented
destination is `/usr/lib/nuxel/nuxel-bridge/`, the bridge files were installed to
**both** the active `/usr/bin` paths and the canonical `/usr/lib` paths.

---

## 2. Payload integrity

| Check | Result |
|---|---|
| Local tarball SHA256 | `012c14cb74f26098dab965ba04dbbd99fcef53eb4ec654bd246671a2741e52b8` |
| Local `tools/s10plus/a43/verify-live.py` | **PASS** — 19 safe regular files, hashes match |
| Phone tarball SHA256 | `012c14cb74f26098dab965ba04dbbd99fcef53eb4ec654bd246671a2741e52b8` |
| Phone `verify-live.py` | **PASS** — “Verified payload hashes and 19 safe regular files” |
| Transfer | `nuxel-push.py`, base64+gzip, per-block length verification; target-side SHA matched twice |
| `test-a43-source.py` | **FAIL (source gate only)** — assertion `branches: [main]` absent from `.github/workflows/release.yml`; the workflow is manual-dispatch. Not a payload integrity failure. |

---

## 3. Backup and rollback

**Backup directory:** `/var/backups/nuxel/v0.6.3-beta-pre-20261020T123441Z`

- 16 pre-existing webroot files backed up under `webroot/` with original mode/owner.
- `/usr/bin/nuxel-bridge`, `/usr/bin/nuxel-http-bridge` backed up under `bin/`.
- `/usr/lib/nuxel/nuxel-bridge/{bridge.py,api.py}` backed up under `lib/`.
- Unit files, `stat.txt`, `services-before.txt`, `active-paths.txt`, and
  `SHA256SUMS.{webroot,bin,lib}` captured.
- Backup-vs-live checks: **all 16 webroot files OK**, both bridge binaries OK,
  both `/usr/lib` files OK (`07-backup-vs-live-webroot.txt`,
  `08-backup-vs-live-bridge.txt`).
- `pwa/nuxel-apps/settings/wifi-settings.js` did **not** exist before deploy
  (`missing.txt`); rollback moves it out of the webroot into the backup directory
  as `created-by-deploy-wifi-settings.js`.

**Rollback command:**

```sh
sh /var/backups/nuxel/v0.6.3-beta-pre-20261020T123441Z/rollback.sh
```

The rollback restores the 16 pre-existing web files and four bridge files with
atomic same-directory renames, removes the newly created Wi-Fi module from the
active webroot, restarts only `nuxel-bridge` and `nuxel-http-bridge`, and reports
their state.

Runtime side effect (recorded, not a payload file): the Settings Wi-Fi
capability test created `/var/lib/nuxel/permissions/nuxel-settings.json` with
`network:manage` (`duration: session`). It and the pre-existing
`org.nuxel.Home.json` were copied to `runtime/` in the backup directory. This is
the bridge's designed network capability path and is needed for Settings Wi-Fi.

---

## 4. Deployed files and live hashes

Full post-deploy list: `31-post-deploy-hashes-services.txt`.

| File | SHA256 |
|---|---|
| `pwa/nuxel-home/index.html` | `76141ec132ed811614468b94b0a044d1bf4d0d1a214646140b01f6d185c39325` |
| `pwa/nuxel-home/css/launcher.css` | `36a92d1e8c79ef1a2ab246dd6a7f8a99559e7270c1fac8c8a236755142dd2dcc` |
| `pwa/nuxel-home/js/launcher.js` | `296780eecd62e43fb447887628dfa4292afecdfaa57900a140f53fe7d10e3e63` |
| `pwa/nuxel-home/js/gestures.js` | `c56a79782bc39f3f27d299049c40c94d4fca501c07a7dff2232b7b3c3938eb31` |
| `pwa/nuxel-home/js/home-settings.js` | `1ad2afc6a34350142669d9baecec2d14b840e672b18dd972acfa743fc9106a84` |
| `pwa/nuxel-home/js/apps.js` | `c6a72cc0292ea145f59355ddc3dd70cf1640bf9752dbd9e3bee9ffab9a9f3e98` |
| `pwa/nuxel-home/assets/nuxel-bottom-bar.jpg` | `e40c6b64e828fd6bf5e7ff4c9fecd63c6404fb4ccea84716f361b62dcc0db984` |
| `pwa/nuxel-home/assets/nuxel-bottom-bar2.png` | `be60ece34adcf0179d1a94e4cbca309bd8f9bd629c14aedbd00d6b32d1ccf0e3` |
| `assets/nuxel-bottom-bar.jpg` | `e40c6b64e828fd6bf5e7ff4c9fecd63c6404fb4ccea84716f361b62dcc0db984` |
| `assets/nuxel-bottom-bar2.png` | `be60ece34adcf0179d1a94e4cbca309bd8f9bd629c14aedbd00d6b32d1ccf0e3` |
| `pwa/nuxel-apps/settings/index.html` | `1ceea351d3a4e047a2ec8f7b2cfeed2de2fb1d7658fa91cecfd756afbe7aadcc` |
| `pwa/nuxel-apps/settings/settings.css` | `e305a82028ef4e3399e1a553b3c9a0bacf0b05953ac240552ddbf9dd4ffc6fc6` |
| `pwa/nuxel-apps/settings/wifi-settings.js` | `930c1d3aeb29a00d9bafc0fff53cc66fd46ddc1dbfc9207e334efa7bdb8d164c` |
| `pwa/nuxel-common/app-registry.json` | `473a2cd00a4cbbf564577a5a0723fa3641e396886a8f5234c683be377a77d137` |
| `/usr/bin/nuxel-bridge` | `808507afb5b538c56e7ebf82af754163b879210cf7e133784336d46056fbfd48` |
| `/usr/bin/nuxel-http-bridge` | `ae9950f9a0b0a6476adae5c16595f615e015f34f724d45ffe15c1ecddfd6e8d1` |
| `/usr/lib/nuxel/nuxel-bridge/bridge.py` | `808507afb5b538c56e7ebf82af754163b879210cf7e133784336d46056fbfd48` |
| `/usr/lib/nuxel/nuxel-bridge/api.py` | `ae9950f9a0b0a6476adae5c16595f615e015f34f724d45ffe15c1ecddfd6e8d1` |

All 21 installed paths match the payload manifest exactly. The implementation was
staged, syntax-checked (`py_compile`), then installed with same-directory rename
(`install … .deploy.$$` + `mv -f`).

---

## 5. Services and runtime after deploy

| Unit | State | PID |
|---|---|---|
| `nuxel-bridge` | **active/running** | 18830 |
| `nuxel-http-bridge` | **active/running** | 18855 |
| `nuxel-wayland` | active/running | (session) |
| `NetworkManager` | active/running | — |
| `nuxel-web` | inactive/disabled | — (PID 5396 is the session HTTP server) |

- `/api/v1/ping` → 200 JSON, `service=nuxel-bridge`, `bridge_version=1`,
  `status=ok`.
- `/api/v1/health` → 200 JSON, registry source
  `/usr/share/nuxel/pwa/nuxel-common/app-registry.json`, `available=true`.
- `/api/v1/apps/registry` → 200; Browser is present as
  `org.nuxel.Browser` → `/pwa/nuxel-apps/browser/index.html`.
- Journal shows continuous `POST /api/v1/rpc` 200 and `OPTIONS /api/v1/ping` 204.
- One non-fatal systemd message: `Failed to get CPU usage: No such file or directory`
  for the two bridge units (cgroup accounting unavailable on this kernel).
- The running host binary refused `reload-launcher` (`HOST_ACTION_REFUSED`) because
  it predates that action. The WebKit view was refreshed through the host's
  documented web-process recovery path: `WebKitWebProcess` 5425 was terminated
  once, the host logged `NUXEL_HOME_WEBPROC_TERMINATED reason=0 reload=0`, and new
  `WebKitWebProcess` PIDs 19464/19465 loaded the new assets at 14:40:39–14:40:40.
  localStorage and the web server were not removed.

---

## 6. HTTP / source-level UI verification

| Route | HTTP | Bytes |
|---|---:|---:|
| `/pwa/nuxel-home/index.html` | 200 | 9623 |
| `/pwa/nuxel-home/css/launcher.css` | 200 | 13256 |
| `/pwa/nuxel-home/assets/nuxel-bottom-bar.jpg` | 200 | 572629 |
| `/pwa/nuxel-home/assets/nuxel-bottom-bar2.png` | 200 | 900285 |
| `/pwa/nuxel-apps/settings/index.html` | 200 | 10185 |
| `/pwa/nuxel-apps/settings/wifi-settings.js` | 200 | 4625 |
| `/pwa/nuxel-apps/settings/settings.css` | 200 | 5055 |
| `/pwa/nuxel-apps/browser/index.html` | 200 | 3030 |
| `/pwa/nuxel-common/app-registry.json` | 200 | 18166 |

After the WebKit refresh, the live request log shows:

```
GET /pwa/nuxel-home/index.html?boot=os&v=... 200
GET /pwa/nuxel-home/css/launcher.css 200
GET /pwa/nuxel-home/assets/nuxel-bottom-bar.jpg?v=0.6.3-beta 200
GET /pwa/nuxel-home/assets/nuxel-bottom-bar2.png?v=0.6.3-beta 200
```

The only `css/assets/nuxel-bottom-bar*.png` 404s are timestamped **14:40:33**,
before the reload; they are the stale old page/CSS. No new `css/assets/...`
request appears after the reload.

Source-level confirmations (not a substitute for physical sight):

- `home-settings.js` uses absolute `/pwa/nuxel-home/assets/...` paths for BG1/BG2
  and applies `--dock-art` to **both** `#dock` and `#system-navigation`.
- `launcher.css` uses a pointer-inert `::before` artwork layer
  (`pointer-events:none`) so dock icons remain tappable.
- `index.html` blocks WebKit `gesturestart`/`gesturechange`/`gestureend` and sets
  `user-scalable=no`, so Home pinch zoom is suppressed.
- `gestures.js` starts bottom-half upward swipes on `launcher.advanceDrawer()` and
  upper-half swipes on Quick Settings; it ignores the dock/navigation surfaces.
- `app-registry.json` contains `org.nuxel.Browser` with
  `/pwa/nuxel-apps/browser/index.html`.

Display bridge state at test time (`/run/nuxel-wl-fb.state`):
`display=on`, `FRAMES_OK total=172116 fps_1s=16 failures=0`,
`decon_pan_failed=0`, `panel=1440x3040`, owner `nuxel-wl-fb`. This proves frames
are reaching the AMOLED output path; it does not replace the owner's visual check.

---

## 7. Wi-Fi / Browser status

**Radio and scan: PASS (software-visible hardware evidence).**

- `nmcli radio all`: `WIFI-HW enabled`, `WIFI enabled`.
- `rfkill`: `phy0` and `brcmfmac-wifi` are not soft/hard blocked.
- `wlan0` / `wlan1`: Wi-Fi devices present, `disconnected`.
- Real scan returned 12 APs, including `Snoerbreuk` (WPA2, signal 79) and
  `Snoerbreuk_ExtraWiFi2G` (WPA2, 79).
- No saved NetworkManager connection exists; every visible AP is WPA2.
- The old read-only check's `*4375*` firmware filename glob found nothing; this is
  not evidence that Wi-Fi is dead, because a real scan succeeded. The exact
  firmware filename was not identified.

**Settings Wi-Fi backend: PASS (software, read-only).**

The full Settings RPC path was exercised:

- `permissions/request` for `network:manage` → `granted` (the bridge auto-grants
  the network capability for the session).
- `phone/status` → real NM state: `wifi_enabled=true`, `wifi_available=true`,
  `wifi_state=enabled_disconnected`, `wlan0`/`wlan1` state 30, connectivity 1.
- `network/wifi-scan` → 11 real APs with SSID, strength, security and AP path.
- `network/wifi-enabled {enabled:true}` → idempotent success,
  `wifi_state=enabled_disconnected`.

Evidence: `36-bridge-wifi-scan.txt`, `37-settings-wifi-rpc.txt`,
`38-settings-wifi-status-radio.txt`.

A direct `network/wifi-scan` call *without* first requesting the capability
returned `Network permission denied`; that is the designed capability gate, not a
driver failure. The Settings client requests `network:manage` before mutations.

**Join / DHCP / DNS / HTTPS: BLOCKED — owner credential or physical entry required.**

No Wi-Fi password was supplied, and guessing/extracting one is not acceptable.
Therefore association, DHCP, DNS and real HTTPS page load remain **UNVERIFIED**.
The owner can complete them during the 90-second test by opening Settings →
Wi-Fi, tapping Scan, selecting an AP, entering the password on the phone, and then
opening Nuxel Browser.

**Browser: software route and registry verified; physical launch pending.**
The Browser app route is 200 and the registry entry is present. Whether it opens
from a physical tap and renders a real top-level HTTPS page is owner-pending.

---

## 8. Audio trace and first hardware blocker

Command run:

```sh
bash /tmp/nuxel-audio-diag.sh pipeline
bash /tmp/nuxel-audio-diag.sh pipeline --json
```

The script returned `BLOCKED_FIRMWARE`, but its firmware candidate list is for
**CS47L93/CS35L40**. The live S10+ uses **CS47L92 + 2× CS35L41**, so that verdict
must not be taken at face value.

Direct read-only trace:

- `/proc/asound/cards`: card 0 `beyond-madera`, card 1 `abox_vdma`, card 2
  `abox_dump`.
- `/sys/kernel/debug/asoc/codecs`: `cs47l92-codec`,
  `cs35l41-codec.0.auto`, `cs35l41-codec.4.auto`.
- Kernel DAI mapping is present: `cs47l92-aif1 <-> UAIF0 mapping ok`,
  `multicodec <-> UAIF1 mapping ok`, etc.
- DAPM state:
  - `SPEAKER: Off  in 0 out 1` (`in "static" "Right AMP SPK"`)
  - `RECEIVER: Off  in 0 out 1` (`in "static" "Left AMP SPK"`)
  - `HEADPHONE: Off`
  - `bias_level: Off`
- No UCM2 profile: `/usr/share/alsa/ucm2` does not exist.
- No audio userspace: `aplay`, `amixer`, `alsactl`, `alsaucm`, `tinymix`,
  `pactl`, `wpctl` and PipeWire/PulseAudio are all absent. `libasound.so.2`
  exists, but there is no player/mixer to open a route.
- Kernel log, first hardware failure:

```
samsung-abox 18c50000.abox: Direct firmware load for calliope_sram.bin failed with error -2
samsung-abox 18c50000.abox: Direct firmware load for calliope_sram_2.bin failed with error -2
samsung-abox 18c50000.abox: Invalid calliope state: 0
samsung-abox-core 18c55000.abox-core: calliope_sram.bin isn't loaded yet
samsung-abox-core 18c55000.abox-core: Direct firmware load for calliope_sram.bin failed with error -2
samsung-vts 15510000.vts: Direct firmware load for vts.bin failed with error -2
```

No `calliope*` or `vts.bin` file exists under `/lib/firmware`, `/usr/lib/firmware`,
or anywhere else on the rootfs (searched with `find / -xdev`).

**First hardware blocker:** missing ABOX/Calliope firmware
(`calliope_sram.bin`, `calliope_sram_2.bin`, and `vts.bin`). The ABOX/DSP route
cannot initialize without it. This is followed by a userspace blocker: no UCM2
speaker profile and no ALSA/PipeWire playback tool, so `SPEAKER` remains `Off` and
cannot be routed or tested. This is **not** an audibility claim and **not** a PASS
from a successful decoder.

No firmware was installed or written. The correct firmware must come from an
authorized vendor/kernel source, not a guessed file.

---

## 9. Physical verification — owner pending

The 90-second owner checklist is in `OWNER-CONFIRMATION.md`. It covers:

1. BG1/BG2 artwork on the bottom navigation dock and app dock.
2. Icon tapping (Phone/Contacts/Settings/Browser).
3. Home pinch/zoom prevention.
4. Bottom-half swipe up → All Apps; second swipe up → Settings.
5. Upper-half gesture → Quick Settings.
6. Wi-Fi scan/join/DHCP/DNS/HTTPS and Browser launch.
7. Audio: audible speaker/cue, or confirmation of silence consistent with the
   ABOX firmware blocker.

No physical item is marked PASS until the owner reports it.

---

## 10. final.md status — honest delta

This deployment resolved the **userspace delivery** of the launcher, dock assets,
Browser registry, Settings Wi-Fi module and NetworkManager bridge. It did **not**
resolve all `final.md` hardware tasks.

| Surface | Status after this run |
|---|---|
| Dock artwork / BG1 / BG2 source + HTTP assets | Software verified; **physical sight pending** |
| Icon tapping / Home zoom / bottom-half gestures | Source verified; **physical touch pending** |
| Wi-Fi radio + scan | **Hardware-visible PASS** |
| Wi-Fi join / DHCP / DNS / HTTPS | **BLOCKED** — owner credentials/physical entry required |
| Browser registry + local route | Software verified; **physical launch pending** |
| Audio speaker / cue / sound modes | **BLOCKED** — ABOX/Calliope firmware missing; no UCM2/userspace player |
| CPU/RAM/GPU/GPU-memory meters | Not addressed by this userspace payload; unverified |
| File Explorer + ZIP | Not addressed by this userspace payload; unverified |
| Bluetooth | Not addressed by this userspace payload; unverified |
| NFC | Not addressed by this userspace payload; unverified |
| GPS / Maps | Not addressed by this userspace payload; unverified |
| Camera | Not addressed by this userspace payload; unverified |
| Hardware buttons / flashlight / screenshot | Not addressed by this userspace payload; unverified |
| Status bar / Quick Settings hardware states | Not addressed by this userspace payload; unverified |
| S10+ release CI / boot artifact | Not claimed; `test-a43-source.py` source gate currently fails |

Known non-blocking issues:

- Bridge version metadata still reports `0.6.1-beta` (D-Bus) and `0.4.0-alpha`
  (HTTP) rather than `0.6.3-beta`; the payload itself is v0.6.3-beta.
- `nuxel-web.service` is disabled/inactive; the actual server is the
  session-managed Python HTTP server. Starting `nuxel-web` would conflict on port
  8000.
- Raw reads of some DAPM widget files can block; subsequent reads used
  `timeout 4` and succeeded.
- The audio diagnostic's firmware-name list does not match this device
  (CS47L93/CS35L40 vs live CS47L92/CS35L41) and missed the real `calliope_sram.bin`
  failure.

**No claim is made that all final.md hardware tasks are resolved.**
