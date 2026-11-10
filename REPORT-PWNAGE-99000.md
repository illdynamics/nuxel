# REPORT-PWNAGE-99000 — Nuxel USB-C HDMI / external display

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Kernel:** Linux 4.14.253-gf7194c1d15ed-dirty  
**Userspace:** Fedora 43 aarch64 / Nuxel  
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Date:** 2026-11-09  

## A. Executive summary

### Initial state

The USB-C-to-HDMI adapter/display was physically attached and a Type-C
partner was visible, but **no DisplayPort link existed**:

- `/sys/class/switch/secdp/state` = `0`
- `/sys/class/extcon/extcon0/state` = `DP=0`
- `/sys/class/sec/ccic/usbpd_ids` = `0000:0000`
- `/sys/class/sec/ccic/usbpd_type` = `0`
- `/sys/class/typec/port0-partner/supports_usb_power_delivery` = `no`
- CCIC state = `3` (`max77705_State_PE_SRC_Send_Capabilities`)

The S10+ vendor display path itself is present and healthy:

- `exynos-displayport` bound at `130b0000.displayport`
- `decon_t` bound at `19050000.decon_t`
- a real external framebuffer `/dev/fb1` (640×480 default mode)
- `DP Audio` PCM present in `/proc/asound/pcm`
- `CONFIG_EXYNOS_DISPLAYPORT=y`, `CONFIG_SND_SOC_SAMSUNG_DISPLAYPORT=y`,
  `CONFIG_USB_TYPEC_MANAGER_NOTIFIER=y`

**Root cause:** the attached adapter never presents a USB-PD identity and
never completes DP Alt Mode VDM negotiation.  DP Alt Mode is negotiated with
USB-PD structured VDM; without it the CCIC never reports a DP pin assignment,
the combo PHY is never switched to DP (`exynos_usbdrd_inform_dp_use dp use=0`),
and AUX/DPCD reads fail.  This is an adapter/hardware-side failure, not a
framebuffer or compositor bug.

### Changes made

A complete userspace external-display layer was implemented and deployed:

- `nuxel-displayd`: authoritative state machine, notification generation,
  mode controller, disconnect/reconnect handling, manual rotation.
- `nuxel-display-ctl`: bounded CLI used by Settings and Home.
- `nuxel-wl-fb-ext`: a real Wayland screencopy → `/dev/fb1` bridge with
  aspect-preserving fit/letterbox, ABGR conversion, rotation, frame pacing and
  a single-writer flock.
- Truthful `DisplayProvider` model of the vendor Type-C → PD/VDM → DP →
  decon_t → fb1 path, plus HDMI audio discovery/routing.
- Actionable notification with **Mirror screen** and **Separate desktop**
  actions; Home renders and invokes the actions.
- Settings controls for Mirror / Separate desktop / Internal only, rotation,
  and HDMI audio.
- A notification-hub hints cap that fixed a pre-existing 19 MB store /
  crash-loop caused by 2.8 MB ZapZap hint payloads.

### Current live state

- All display/audio/notification/bridge services active.
- `display.status` truthfully reports `PARTNER_NO_PD`.
- Internal AMOLED (`/dev/fb0`) and its compositor bridge remain active.
- The external transport was verified end-to-end to `/dev/fb1`.
- The notification path was verified on-device with a fixture connection:
  connect → notification, disconnect → archive, reconnect → new notification.
- No physical external picture, mirroring, separate desktop, orientation or
  HDMI audio could be observed because no DP link exists with this adapter.

### What works / what is blocked

| Item | Status |
|---|---|
| Internal phone display | **Working / preserved** |
| External framebuffer `/dev/fb1` transport | **Verified (systemd service + frames)** |
| Mirror transport to `fb1` | **Verified at framebuffer level** |
| Physical external picture | **Blocked: adapter has no PD/DP link** |
| Separate desktop | **Blocked: no DP link; compositor also exposes only one output** |
| Rotation control | **Implemented and verified via CLI** |
| Notification record + both actions | **Verified in the real notification hub** |
| Physical notification tap | **Not observed: device locked; no credential bypass attempted** |
| HDMI audio | **Implemented/detected; blocked because DP link is down** |
| Physical disconnect/reconnect notification | **Blocked with this adapter; automated on-device integration passed** |

## B. Initial diagnosis

### Device identity

```
Linux fedora 4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT ... aarch64 GNU/Linux
hostname: fedora
Fedora 43 aarch64
```

### Type-C / DP Alt Mode findings (live)

```
/sys/class/typec/port0/data_role            host
/sys/class/typec/port0/power_role           source
/sys/class/typec/port0/power_operation_mode default
/sys/class/typec/port0-partner/supports_usb_power_delivery no
/sys/class/typec/port0-partner/accessory_mode none
/sys/class/switch/secdp/state               0
/sys/class/extcon/extcon0/state             DP=0
/sys/class/sec/ccic/state                   3
/sys/class/sec/ccic/usbpd_ids               0000:0000
/sys/class/sec/ccic/usbpd_type              0
/sys/class/sec/ccic/rid                     7
/sys/class/sec/ccic/sbu_adc                 10 6
/sys/class/sec/ccic/cc_pin_status           2
/sys/class/sec/ccic/cur_version             1A.00
```

Kernel log at attach time:

```
max77705_get_pd_support: ... usbc_data->pd_support : 0
typec_set_pwr_opmode pwr_opmode=0 opmode=0
typec_register_partner
```

No `VDM`, `Discover_Identity`, `PS_RDY` or DP notification was observed.
The CCIC is waiting in source-capabilities state; the partner never answers.

### HPD / AUX / EDID findings

The DP driver exposes a controlled HPD test.  Forcing HPD high (`dp_test 0,1`)
produced:

```
Displayport: displayport hpd changed 1
Displayport: displayport_reg_wait_phy_pll_lock is timeout 300us
Displayport: CCIC_NOTIFY_DP_PIN_UNKNOWN
Displayport: displayport_reg_dpcd_read_burst fail
Displayport: link_sink_status_read fail
Displayport: link_status_read fail
[exynos_usbdrd_inform_dp_use] dp use = 0, lane_cnt = 2
```

The PHY powers on, but because no CCIC pin assignment exists the combo PHY is
not switched to DP and AUX/DPCD cannot reach a sink.  This is exactly the
missing PD/VDM stage.

`/sys/class/dp_sec/monitor_info` showed `BNQ,0x7f54,0x5445`, but this is the
vendor driver's **built-in unit-test EDID** (BenQ SW320), not the attached
display.  The implementation only trusts a monitor identity when
`secdp=1` and `extcon DP=1`.

### DRM / compositor findings

```
/sys/class/drm: only "version"
CONFIG_DRM=y, CONFIG_DRM_EXYNOS=not_set
/dev/fb0 -> 19030000.decon_f (internal AMOLED)
/dev/fb1 -> 19050000.decon_t (external DP/TV output)
Phoc: HEADLESS-1, 720x1520, one output
nuxel-wl-fb: single /dev/fb0 writer
```

There is no DRM connector/CRTC.  The real external path is the vendor fbdev
`decon_t` output, which is what the new implementation uses.

### Audio findings

```
/proc/asound/pcm:
  00-22: DP Audio snd-soc-dummy-dai-22 : playback 1
/sys/class/switch/ch_hdmi_audio/state: 0
```

The kernel DP audio PCM exists, but `ch_hdmi_audio=0` because no link/audio
infoframe is active.  No HDMI sink is exposed by PipeWire while the DP link is
down; the implementation refuses to invent one.

## C. Implementation

### New service: `services/nuxel-display/`

| File | Purpose |
|---|---|
| `bin/nuxel-displayd` | Authoritative display state machine, sysfs monitoring, notification generation, mode controller, rotation, control socket. |
| `bin/nuxel-display-ctl` | Bounded CLI: `status`, `set-mode`, `set-rotation`, `notify-test`, `outputs`, `stop`. |
| `bin/nuxel-wl-fb-ext.c` | Wayland screencopy → `/dev/fb1` bridge. Adds aspect-preserving fit/letterbox, ABGR conversion, rotation, 20 fps pacing, `/run/nuxel-fb1-owner.lock` single-writer guard, `RUNNING/FAILED/STOPPED` receipts. |
| `bin/build-nuxel-wl-fb-ext.sh` | On-device build using `gcc`, `wayland-scanner`, `pkg-config`; skips when up to date. |
| `lib/nuxel_display.py` | Pure, testable hardware model: parse sysfs, classify `DISCONNECTED → PARTNER_NO_PD → PD_NO_DP → DP_NO_FB → DP_LINK_READY`, state machine, notification planner. |
| `systemd/nuxel-displayd.service` | Starts the manager; sandboxed userspace-only unit. |
| `systemd/nuxel-wl-fb-ext.service` | On-demand external bridge; builds if needed and runs from `/run/nuxel-display/ext-start.sh`. |
| `protocol/wlr-screencopy-unstable-v1.xml` | Protocol input for the bridge build. |
| `tests/test-display-model.py` | Offline model tests (fixture sysfs roots). |
| `tests/test-display-daemon.py` | Offline lifecycle/mode-controller tests with fake systemctl and notification hub. |
| `README.md` | Operator documentation and diagnostics. |

### `services/nuxel-bridge/src/hw_providers.py`

- Replaced the old “no DRM → impossible” DisplayProvider with a truthful model
  of the actual vendor path.
- Reports `PARTNER_NO_PD`, `PD_NO_DP`, `DP_NO_FB`, `DP_LINK_READY`,
  `MIRRORING`, `SEPARATE_DESKTOP`.
- Reports `drm_present=false` unless a real `card*` exists (the `version`
  pseudo-entry is not counted), `drm_exynos_kernel=not_set`, type-C partner,
  PD identity, `secdp`, `extcon`, `decon_t`/`fb1`, modes, audio and exact
  blockers.
- Never uses `monitor_info` without a live DP link.
- Added HDMI/DP audio discovery and `set_output('hdmi'|'speaker')`; refuses
  HDMI with `HDMI_AUDIO_UNAVAILABLE` when no link/sink exists.

### `services/nuxel-bridge/src/api.py`

- Added first-party-only `display.set-mode`, `display.set-rotation`,
  `display.notify-test`, `display.outputs`.  All invoke the canonical
  `nuxel-display-ctl`; failures are returned honestly.
- Added `audio.set-output`.

### Notification integration

- `pwa/nuxel-home/js/status-bar.js`
  - Renders custom notification actions from `n.actions`.
  - `_invokeNotificationAction` calls `bridge.setDisplayMode(key)`.
  - Reduced notification polling from 30 s to 5 s.
- `pwa/nuxel-home/js/app.js`
  - `notifications-panel` now calls `qs.extend()` (level 3), so the extended
    notification list is actually shown below the QS tiles.
- `pwa/nuxel-common/bridge.js`, `pwa/nuxel-home/js/bridge.js`
  - Added `getDisplayStatus`, `setDisplayMode`, `getDisplayOutputs`,
    `notifyTestDisplay`.
- `services/nuxel-notifications/src/notifications.py`
  - Added `MAX_HINTS_BYTES` (64 KiB default) and `_bounded_hints()`.
  - Compacts existing oversized hints on load.
  - This fixed the measured 19 MB store / hub crash-loop caused by 2.8 MB
    ZapZap `image-data` hints.  The hub now stays at `NRestarts=0` with a
    ~10 KB store.

### Settings / UX

- `pwa/nuxel-apps/settings/index.html`, `hardware-settings.js`
  - Mirror / Separate desktop / Internal only buttons.
  - Rotation selector (0/90/180/270).
  - Test notification button.
  - Real DP/PD/DRM/fb1/mode/audio state and exact blockers.
- `pwa/nuxel-apps/settings/index.html` sound card
  - HDMI audio / Phone speaker buttons.

### Deploy tooling

- `scripts/nuxel-deploy-live.py`: maps and deploys the new service files.
- `scripts/nuxel-live-install.py`: allows `/usr/share/doc/nuxel/`.
- `tools/s10plus/a43/package-live.py`: includes the new service, bridge
  source, protocol, units and documentation in the live payload.

## D. Test evidence

### Automated tests (host)

```
services/nuxel-display/tests/test-display-model.py      ALL PASS
services/nuxel-display/tests/test-display-daemon.py     ALL PASS
services/nuxel-bridge/test-hw-providers.py              ALL PASS
node --check (all modified JS files)                    OK
```

The model tests cover every classification stage, fb mode parsing, output
selection, generation/reconnect semantics, notification actions and refusal
paths.  The daemon tests cover notification dedupe, disconnect archive,
reconnect generation, mirror/desktop start, desktop-without-second-output
refusal, not-ready refusal and rotation validation.

Existing regression run:

```
pytest tests/pwnage93000 tests/pwnage96000 tests/pwnage97000 tests/pwnage89000
93 passed, 4 pre-existing failures
```

The four failures are unrelated to this work:
`test_flatpak_launch_flags_do_not_disable_sandboxes`,
`test_remote_desktop_uses_standard_direct_lan_ports_and_password_vnc`,
`test_vnc_geometry_validation_is_landscape_only`, and
`test_notifications_render_below_qs_controls_in_expanded_panel` (the last one
checks an older QS DOM arrangement).  They were present before this mission and
do not touch the new display path.

### Automated test on-device (notification hints)

```
ALL PASS notification hints are bounded on device
```

### Runtime (live S10+)

```
nuxel-wayland.service       active
nuxel-wl-fb.service         active
nuxel-notifications.service active  (NRestarts=0, ExecMainStatus=0)
nuxel-http-bridge.service   active
nuxel-bridge.service        active
nuxel-displayd.service      active
```

Provider truth after the final deploy:

```
state             PARTNER_NO_PD
drm_present       false
drm_exynos_kernel not_set
type_c_port_count 1
partner           true
pd_identity       false
pd_ids            0000:0000
dp_link           false
secdp             0
extcon_dp         false
external_fb       /dev/fb1 via 19050000.decon_t
mirror_supported  false
desktop_supported false
rotation          0
```

### External transport (systemd + fb1)

The installed `nuxel-wl-fb-ext.service` was started with a mirror start script
against the live compositor:

```
ext_active=active
state RUNNING mode=mirror output=HEADLESS-1 fb=/dev/fb1
      src=720x1520 dst=640x480 fps=20 rot=0 frames=1
/dev/fb0 sampled 17100 nonzero 17100
/dev/fb1 sampled 19200 nonzero 6840
  (12360 letterbox-black samples; 6840 content samples)
internal_wayland=active
internal_bridge=active
```

The bridge produced 48 frames in the service run and 29 frames in an earlier
run.  `fb1` content occupies the expected centered 227×480 region
(720×1520 fitted into 640×480), and the remaining area is black.  The bridge
uses the DECON ABGR order (`R@0 G@8 B@16`), matching `fb0`.

Evidence: `evidence/pwnage-99000/fb1-mirror-live.ppm` / `.png`,
`fb0-internal-live.ppm` / `.png`, `ext-service-test.txt`.

This verifies the **transport to the external framebuffer**.  It does not
verify a physical TV picture because no DP link exists.

### Notification path

On-device fixture integration using the real daemon and real notification hub:

```
notification #31: External display connected  (generation 1)
event disconnected generation=1 state=PD_NO_DP
archived notification #31
event connected generation=2 state=DP_LINK_READY
notification #32: External display connected  (generation 2)
```

Both notifications carried:

```
["mirror", "Mirror screen", "desktop", "Separate desktop",
 "settings", "Display settings"]
```

Evidence: `evidence/pwnage-99000/disconnect-reconnect-integration.log`,
`notification-hub-before-cleanup.json`.

The HTTP bridge action path was also exercised:

```
display.set-mode mirror  -> EXTERNAL_DISPLAY_NOT_READY
  detail: Type-C partner has no USB-PD identity ...
display.set-mode desktop -> EXTERNAL_DISPLAY_NOT_READY
display.set-mode off     -> success
unauthorized app         -> CAPABILITY_DENIED
```

This proves the notification actions invoke the canonical display manager and
report the real failure rather than pretending.

### HDMI audio

```
hdmi_audio.available   false
dp_audio_pcm           true
pcm                    00-22: DP Audio snd-soc-dummy-dai-22 : playback 1
ch_hdmi_audio          0
blocker                DP link is not ready (secdp=0, extcon=DP=0);
                       DP audio infoframe is not active (ch_hdmi_audio=0)
audio.set-output hdmi  HDMI_AUDIO_UNAVAILABLE
```

The phone speaker remains the selected PipeWire sink.  No dummy HDMI sink was
created.  Evidence: `evidence/pwnage-99000/audio-hdmi-status.txt`.

### Physical observations

| Test | Result | Evidence |
|---|---|---|
| HDMI detection | Type-C partner detected; **no DP link** | `secdp=0`, `extcon DP=0`, `usbpd_ids=0000:0000` |
| EDID | **Not read from the adapter** | AUX/DPCD reads fail; `monitor_info` is the driver unit-test EDID |
| External picture | **Not observed** | No DP link |
| Mirroring | **Not physically observed** | `fb1` transport verified, no DP sink |
| Separate desktop | **Not physically observed** | No DP link; only `HEADLESS-1` exists |
| Phone portrait/landscape | **Not physically observed** | Rotation control works, no external output |
| Mirror rotation | **Not physically observed** | Rotation CLI verified |
| Phone touch / navigation | Internal services active; **not physically tapped** | `nuxel-wayland`/`nuxel-wl-fb` active |
| External input | **Not applicable / not observed** | No external display link |
| HDMI audio | **Not heard** | `ch_hdmi_audio=0`, no DP link |
| Phone speaker | **Still selected** | PipeWire `S10+ speaker (RDMA1, 48 kHz)` |
| Disconnect/reconnect | **Automated fixture integration passed; physical cable test blocked** | generation 1 → archived → generation 2 |
| Notification tap | **Not physically tapped** | Device locked; host unlock correctly refused by credential check |

### Final live state at end of mission

```
nuxel-wayland.service        active
nuxel-wl-fb.service          active
nuxel-notifications.service  active  (NRestarts=0, ExecMainStatus=0)
nuxel-http-bridge.service    active
nuxel-bridge.service         active
nuxel-displayd.service       active
nuxel-wl-fb-ext.service      inactive (correct: no DP link / no mode selected)
display state                 PARTNER_NO_PD
mode                          off
rotation                      0
mirror_supported              false
desktop_supported             false
notification store            ~9.5 KB, hub stable
```

The internal AMOLED framebuffer `/dev/fb0`, the Phoc session and the internal
`screencopy -> fb0` bridge were never stopped or reconfigured.

## E. Limitations

### 1. The attached adapter does not negotiate USB-PD / DP Alt Mode (primary blocker)

- **Exact failure point:** CCIC never receives a USB-PD identity or DP VDM.
- **Evidence:** `usbpd_ids=0000:0000`, `usbpd_type=0`,
  `supports_usb_power_delivery=no`, CCIC state `3`, no `PS_RDY`/VDM logs,
  `secdp=0`, `extcon DP=0`.
- **What was attempted:** a controlled HPD-high test through the vendor DP
  driver; PHY powered but AUX/DPCD failed and the combo PHY stayed in USB mode
  (`exynos_usbdrd_inform_dp_use dp use=0`).
- **What remains necessary:** use a USB-C **DisplayPort Alt Mode** adapter
  that implements USB-PD structured VDM (and, for audio, advertises audio in
  its EDID/DPCD).  A charge-only or passive USB-C-to-HDMI adapter cannot carry
  video on this device.  This is not a userspace or framebuffer defect.

### 2. Separate desktop needs a second compositor output

The live Phoc session exposes only `HEADLESS-1` (720×1520).  The daemon
correctly returns:

```
DESKTOP_OUTPUT_UNAVAILABLE
Separate desktop needs a second compositor output; only HEADLESS-1 is currently exposed.
```

The implementation supports `HEADLESS-2` if present, but the current session
was not restarted (the mission prohibits an unnecessary graphics-stack restart
and there is no DP link to test against).  To enable separate desktop, a
controlled compositor start with `WLR_HEADLESS_OUTPUTS=2` (and a second output
geometry/arrangement) is required, followed by physical testing with a working
DP adapter.

### 3. Physical notification tap not observed

The phone was on the lockscreen.  Nuxel's own host-unlock path correctly
refused to unlock without the authoritative credential check; no PIN/pattern
bypass was attempted.  The notification record, both action labels, the Home
rendering path and the bridge action path were verified independently.
A physical tap remains unverified.

### 4. HDMI audio physical output not observed

The kernel exposes `DP Audio`, but `ch_hdmi_audio=0` and `secdp=0`.  Without a
DP link there is no HDMI audio device/route.  No audible claim is made.

### 5. No physical external picture / orientation observations

No DP link means no picture, no external EDID mode, and no physical
orientation test.  The `/dev/fb1` transport and manual rotation control are
verified; the display itself is not.

## F. Deployment and rollback

- **Repository:** `/Users/wicked/x/nuxel`
- **Branch:** `feature/v0.8.2-beta-pwnage-97000`
- **Commit:** `b6154b67ec1e421729cea8053839ce9cfae9095d`
- **Payload:** `build/out/s10plus/nuxel-v0.8.2-beta-live-userspace.tar.gz`
- **Deployment script:**
  ```
  scripts/nuxel-deploy-live.py --host 10.20.30.16 --user root \
    --key ~/.ssh/wicked_wqn_id_rsa --apply --no-restart
  ```
- **Install semantics:** userspace-only; every replaced file is backed up by
  the live installer; no kernel, boot, DTB, firmware, modem or partition write.
- **Rollback backup (latest):**
  `/var/lib/nuxel/live-deploy/rollback-20261109T155518Z/` (27 MB)
- **Services installed:** `nuxel-displayd.service`,
  `nuxel-wl-fb-ext.service`.
- **Current deployed version:** `0.8.2-beta` userspace payload.
- **Rollback procedure:**
  1. `systemctl disable --now nuxel-displayd.service`
  2. Restore the previous bytes from
     `/var/lib/nuxel/live-deploy/rollback-20261109T155518Z/<absolute path>`
     for every file listed in that transaction.
  3. `systemctl daemon-reload`
  4. `systemctl restart nuxel-bridge nuxel-http-bridge nuxel-notifications`
  5. The internal display path (`nuxel-wayland` + `nuxel-wl-fb`) was never
     stopped or reconfigured, so it needs no rollback.
- **Built binary:** `nuxel-wl-fb-ext` is built on-device from the deployed C
  source by `build-nuxel-wl-fb-ext.sh`; the service runs `ExecStartPre` to
  rebuild when the source is newer.

## G. Final status

**`BLOCKED_BY_HARDWARE_OR_DRIVER`**

The Nuxel-side external-display layer is implemented and deployed, and the
`decon_t`/`fb1` transport, notification state machine, reconnect generations,
rotation control and HDMI-audio detection were verified.  The mandatory
physical acceptance criteria (external picture, visible mirroring, independent
desktop, physical orientation, audible HDMI audio, physical disconnect/reconnect
notification) cannot be met with the currently attached adapter because it
does not negotiate USB-PD / DisplayPort Alt Mode.  No physical success is
claimed.

### Acceptance checklist

- [x] Existing USB-C HDMI hardware connection investigated.
- [x] Actual failure point identified (adapter has no PD identity / DP VDM).
- [ ] HDMI output works physically on the connected S10+ — **blocked by adapter**.
- [ ] Mirroring physically observed — **transport verified, physical blocked**.
- [ ] Separate desktop physically observed — **blocked; also needs second compositor output**.
- [x] Both modes can be selected from a real notification record.
- [x] Notification generation verified (connect/reconnect fixture integration).
- [x] Notification reappears on a new connection generation (automated).
- [x] Internal phone display remains functional.
- [x] Rotation control implemented and verified at the manager level.
- [ ] External orientation physically verified — **blocked**.
- [x] Resolution/aspect fit and letterbox policy implemented.
- [x] Touch/pointer ownership preserved (no touchscreen remap).
- [x] HDMI audio detected/refused truthfully; no dummy sink.
- [ ] Physical HDMI audio heard — **blocked**.
- [x] Audio fallback remains the phone speaker.
- [x] External `fb1` ownership is single-writer and cleaned up on stop.
- [x] Repeated fixture hotplug does not duplicate notifications.
- [x] Automated model/daemon/provider/hints tests pass.
- [x] Relevant existing regression tests run (4 pre-existing unrelated failures noted).
- [x] Fix deployed to the actual device via the canonical userspace path.
- [x] Final report contains evidence and accurate limitations.

### 1. The attached adapter does not negotiate USB-PD / DP Alt Mode (primary blocker)

- **Exact failure point:** CCIC never receives a USB-PD identity or DP VDM.
- **Evidence:** `usbpd_ids=0000:0000`, `usbpd_type=0`,
  `supports_usb_power_delivery=no`, CCIC state `3`, no `PS_RDY`/VDM logs,
  `secdp=0`, `extcon DP=0`.
- **What was attempted:** a controlled HPD-high test through the vendor DP
  driver; PHY powered but AUX/DPCD failed and the combo PHY stayed in USB mode
  (`exynos_usbdrd_inform_dp_use dp use=0`).
- **What remains necessary:** use a USB-C **DisplayPort Alt Mode** adapter
  that implements USB-PD structured VDM (and, for audio, advertises audio in
  its EDID/DPCD).  A charge-only or passive USB-C-to-HDMI adapter cannot carry
  video on this device.  This is not a userspace or framebuffer defect.

### 2. Separate desktop needs a second compositor output

The live Phoc session exposes only `HEADLESS-1` (720×1520).  The daemon
correctly returns:

```
DESKTOP_OUTPUT_UNAVAILABLE
Separate desktop needs a second compositor output; only HEADLESS-1 is currently exposed.
```

The implementation supports `HEADLESS-2` if present, but the current session
was not restarted (the mission prohibits an unnecessary graphics-stack restart
and there is no DP link to test against).  To enable separate desktop, a
controlled compositor start with `WLR_HEADLESS_OUTPUTS=2` (and a second output
geometry/arrangement) is required, followed by physical testing with a working
DP adapter.

### 3. Physical notification tap not observed

The phone was on the lockscreen.  Nuxel's own host-unlock path correctly
refused to unlock without the authoritative credential check; no PIN/pattern
bypass was attempted.  The notification record, both action labels, the Home
rendering path and the bridge action path were verified independently.
A physical tap remains unverified.

### 4. HDMI audio physical output not observed

The kernel exposes `DP Audio`, but `ch_hdmi_audio=0` and `secdp=0`.  Without a
DP link there is no HDMI audio device/route.  No audible claim is made.

### 5. No physical external picture / orientation observations

No DP link means no picture, no external EDID mode, and no physical
orientation test.  The `/dev/fb1` transport and manual rotation control are
verified; the display itself is not.

## F. Deployment and rollback

- **Repository:** `/Users/wicked/x/nuxel`
- **Branch:** `feature/v0.8.2-beta-pwnage-97000`
- **Commit:** `b6154b67ec1e421729cea8053839ce9cfae9095d`
- **Payload:** `build/out/s10plus/nuxel-v0.8.2-beta-live-userspace.tar.gz`
- **Deployment script:**
  ```
  scripts/nuxel-deploy-live.py --host 10.20.30.16 --user root \
    --key ~/.ssh/wicked_wqn_id_rsa --apply --no-restart
  ```
- **Install semantics:** userspace-only; every replaced file is backed up by
  the live installer; no kernel, boot, DTB, firmware, modem or partition write.
- **Rollback backup (latest):**
  `/var/lib/nuxel/live-deploy/rollback-20261109T155518Z/` (27 MB)
- **Services installed:** `nuxel-displayd.service`,
  `nuxel-wl-fb-ext.service`.
- **Current deployed version:** `0.8.2-beta` userspace payload.
- **Rollback procedure:**
  1. `systemctl disable --now nuxel-displayd.service`
  2. Restore the previous bytes from
     `/var/lib/nuxel/live-deploy/rollback-20261109T155518Z/<absolute path>`
     for every file listed in that transaction.
  3. `systemctl daemon-reload`
  4. `systemctl restart nuxel-bridge nuxel-http-bridge nuxel-notifications`
  5. The internal display path (`nuxel-wayland` + `nuxel-wl-fb`) was never
     stopped or reconfigured, so it needs no rollback.
- **Built binary:** `nuxel-wl-fb-ext` is built on-device from the deployed C
  source by `build-nuxel-wl-fb-ext.sh`; the service runs `ExecStartPre` to
  rebuild when the source is newer.

## G. Final status

**`BLOCKED_BY_HARDWARE_OR_DRIVER`**

The Nuxel-side external-display layer is implemented and deployed, and the
`decon_t`/`fb1` transport, notification state machine, reconnect generations,
rotation control and HDMI-audio detection were verified.  The mandatory
physical acceptance criteria (external picture, visible mirroring, independent
desktop, physical orientation, audible HDMI audio, physical disconnect/reconnect
notification) cannot be met with the currently attached adapter because it
does not negotiate USB-PD / DisplayPort Alt Mode.  No physical success is
claimed.

### Acceptance checklist

- [x] Existing USB-C HDMI hardware connection investigated.
- [x] Actual failure point identified (adapter has no PD identity / DP VDM).
- [ ] HDMI output works physically on the connected S10+ — **blocked by adapter**.
- [ ] Mirroring physically observed — **transport verified, physical blocked**.
- [ ] Separate desktop physically observed — **blocked; also needs second compositor output**.
- [x] Both modes can be selected from a real notification record.
- [x] Notification generation verified (connect/reconnect fixture integration).
- [x] Notification reappears on a new connection generation (automated).
- [x] Internal phone display remains functional.
- [x] Rotation control implemented and verified at the manager level.
- [ ] External orientation physically verified — **blocked**.
- [x] Resolution/aspect fit and letterbox policy implemented.
- [x] Touch/pointer ownership preserved (no touchscreen remap).
- [x] HDMI audio detected/refused truthfully; no dummy sink.
- [ ] Physical HDMI audio heard — **blocked**.
- [x] Audio fallback remains the phone speaker.
- [x] External `fb1` ownership is single-writer and cleaned up on stop.
- [x] Repeated fixture hotplug does not duplicate notifications.
- [x] Automated model/daemon/provider/hints tests pass.
- [x] Relevant existing regression tests run (4 pre-existing unrelated failures noted).
- [x] Fix deployed to the actual device via the canonical userspace path.
- [x] Final report contains evidence and accurate limitations.
