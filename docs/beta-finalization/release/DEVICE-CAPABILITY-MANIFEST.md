# NUXEL BETA — DEVICE CAPABILITY MANIFEST

**briq:** `briq-09c-release-deliverables` · **component:** `bg-09-integration-release`
**Machine-readable twin:** [`DEVICE-CAPABILITY-MANIFEST.json`](DEVICE-CAPABILITY-MANIFEST.json) · **Schema:** [`DEVICE-CAPABILITY-MANIFEST.schema.json`](DEVICE-CAPABILITY-MANIFEST.schema.json) · **Validator:** `tools/beta/validate-capability-manifest.py`
**Companion:** [`../testing/TEST-STRATEGY.md`](../testing/TEST-STRATEGY.md) (L1–L6) · [`SOAK-AND-PERFORMANCE.md`](../testing/SOAK-AND-PERFORMANCE.md) · [`REBOOT-ROLLBACK.md`](REBOOT-ROLLBACK.md) · [`ROLLBACK.md`](ROLLBACK.md) · [`../BETA-MANUAL-PROOF-CHECKLIST.md`](../BETA-MANUAL-PROOF-CHECKLIST.md)

**Version:** `v0.4.0-alpha` · **git head at generation:** `94d68b13e64ed195e0c3f3f6d2e21a07f3ae3b19` · **generated:** `2026-10-16T21:02:28+0200`

---

## 1. How to read this manifest

Every row is a *subsystem*, and every row names the **work-queue record** that authorises it. The validator enforces two things mechanically:

1. **Schema validity** — the JSON is validated against its schema (the enforced keyword set is printed by the validator and recorded in the cross-check report).
2. **No claim without a record** — a row's verdict may be **no stronger** than its record, where

```
cap = min( strength(record's latest verdict), strength(record's declared offline ceiling) )
      a record with no verdict at all caps the row at strength 1
      (NEEDS_OWNER_TEST / IMPLEMENTED_NOT_DEPLOYED)

strength:  NOT_SUPPORTED_ON_DEVICE = DEFERRED = FAILED = BLOCKED_* = 0
           NEEDS_OWNER_TEST = IMPLEMENTED_NOT_DEPLOYED = 1
           OFFLINE_TESTED = 2
           DEPLOYED_UNVERIFIED = 3
           VERIFIED_IN_VM_ONLY = 4
           VERIFIED_ON_S10PLUS = 5      (live-device evidence only)
```

This is why the table below contains a lot of `1`s and `2`s and no `5`s: nothing has been promoted on the strength of a file existing. `VERIFIED_ON_S10PLUS` requires live-device evidence for the *promoted* claim, and the live preflight in this pass was read-only.

## 2. Device

| Property | Value |
|---|---|
| Model | Samsung Galaxy S10+ (SM-G975F) |
| Codename | beyond2lte |
| SoC | Samsung Exynos 9820 |
| Kernel | Linux 4.14.253 (Samsung vendor tree, #15 SMP PREEMPT aarch64) |
| Userspace | Fedora Linux 43 (aarch64) |
| Boot mode at last capture | `androidboot.mode=charger (LPM) at the last capture` |
| Display | /dev/fb0 DECON 1440x3040x32 (virtual 1440x6080), no /dev/dri |
| Storage | /dev/sda31 ext4 3.9 GiB, 47% used (UFS sda1..sda31) |
| Memory | 7420 MiB usable, no swap |
| Init / console | systemd (PID 1), live console /dev/ttyACM0 |

## 3. Subsystem status

`verdict` is the claim; `record` is the evidence gate. Hardware facts and caveats are in §4.

| Subsystem | Verdict | Record (state) | Title |
|---|---|---|---|
| `touchscreen` | **NEEDS_OWNER_TEST** | `briq-01d-touch-owner-test` (implemented) | Touchscreen (sec_ts) controller -> evdev -> libinput -> Phoc -> PWA |
| `display_framebuffer` | **NEEDS_OWNER_TEST** | `briq-02c-fb-colour-conversion` (implemented) | Display path: Phoc (headless) -> Wayland screencopy -> DECON framebuffer |
| `boot_animation_handoff` | **NEEDS_OWNER_TEST** | `briq-02a-readiness-handoff` (implemented) | Boot animation -> launcher display-ownership handoff |
| `launcher` | **OFFLINE_TESTED** | `briq-02d-launcher-parity` (implemented) | Nuxel Home PWA launcher (WebKitGTK kiosk under Phoc) |
| `wallpaper_and_assets` | **OFFLINE_TESTED** | `briq-00d-baseline-protection` (implemented) | Wallpaper and launcher asset integrity |
| `safe_zones` | **OFFLINE_TESTED** | `briq-02e-safe-zones-statusbar` (implemented) | Ten-zone status-bar / camera-cutout safe areas |
| `verbose_boot_setting` | **NEEDS_OWNER_TEST** | `briq-02b-verbose-boot-setting` (implemented) | Verbose boot setting and the one-time Bixby early-hold override |
| `boot_mode_guard` | **BLOCKED_KERNEL** | `briq-01c-chargermode-bootmode` (implemented) | Charger/LPM boot-mode detection and the initramfs-side fix |
| `wifi` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-03a-wifi` (in_progress) | Wi-Fi (Broadcom brcmfmac) enumeration, scan and association |
| `bluetooth` | **NEEDS_OWNER_TEST** | `briq-08d-bluetooth` (pending) | Bluetooth (BlueZ) controller, pairing and profiles |
| `modem_sim` | **NEEDS_OWNER_TEST** | `briq-08i-sim-microsd-modem` (pending) | Shannon LTE modem and SIM (beyond2lte) |
| `microsd` | **NEEDS_OWNER_TEST** | `briq-08i-sim-microsd-modem` (pending) | microSD controller, insertion and safe mount/eject |
| `audio_speaker` | **NEEDS_OWNER_TEST** | `briq-03c-audio-speaker` (in_progress) | Speaker / earpiece audio path (Madera + ABox + CS35L40) |
| `headphones` | **NEEDS_OWNER_TEST** | `briq-03d-headphones-usbc` (pending) | Headphones and USB-C audio accessories |
| `buttons` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-03e-buttons-gestures` (pending) | Hardware buttons: power, volume, Bixby (A32 manager + gesture FSM) |
| `power_menu` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-03e-buttons-gestures` (pending) | Nuxel power menu (lock, off, restart, recovery, Download Mode entries) |
| `power_management` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-08a-power-management` (in_progress) | Power management: governors, idle behaviour, power modes |
| `battery_charging` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-08a-power-management` (in_progress) | Battery and charging telemetry |
| `haptics` | **NEEDS_OWNER_TEST** | `briq-08b-vibration-haptics` (pending) | Vibration / haptics |
| `flashlight` | **NEEDS_OWNER_TEST** | `briq-08c-flashlight-led` (pending) | Camera torch / flashlight |
| `notification_led` | **NOT_SUPPORTED_ON_DEVICE** | `briq-08c-flashlight-led` (pending) | RGB notification LED |
| `sensors` | **NEEDS_OWNER_TEST** | `briq-08g-sensors` (pending) | Sensor inventory and integration |
| `camera` | **NEEDS_OWNER_TEST** | `briq-08h-camera` (pending) | Cameras (V4L2 / media controller) and gallery |
| `gnss` | **NEEDS_OWNER_TEST** | `briq-08f-gps-gnss` (pending) | GNSS / location and the Nuxel Maps app |
| `nfc` | **NEEDS_OWNER_TEST** | `briq-08e-nfc` (pending) | NFC controller and tag support |
| `timekeeping` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-03b-time-rtc-timesync` (in_progress) | Time, RTC persistence and time synchronisation |
| `live_console` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-07e-live-console-app` (in_progress) | Live console over USB CDC-ACM (debug path and app) |
| `permissions` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-05a-permission-manager` (in_progress) | Per-app permissions, privacy controls and global switches |
| `firewall` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-05b-firewall-app` (in_progress) | Firewall app (single authoritative backend) |
| `vpn_remote` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-05c-vpn-tor-remote` (in_progress) | VPN manager, Tor tools, remote access and device connect |
| `security_audit` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-05d-security-auditor` (pending) | Security auditor (read-only) |
| `core_apps` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-06a-core-app-inventory` (pending) | Core phone applications (dialer, messages, contacts, mail, calendar, notes, files, clock, terminal) |
| `keyboard` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-06d-settings-and-keyboard` (in_progress) | Virtual keyboard and physical keyboard support |
| `app_store` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-07a-nuxtore` (in_progress) | NuxTore app store (Flatpak + PWA, no account) |
| `userspace_packages` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-04a-fedora-packages` (in_progress) | Fedora 43 ARM64 userspace and package manifest |
| `services` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-04b-service-definitions` (in_progress) | Service definitions and boot graph |
| `app_infrastructure` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-04c-app-infrastructure` (in_progress) | Application infrastructure: registry, portal, notifications, bridge, local web server |
| `specialty_apps` | **IMPLEMENTED_NOT_DEPLOYED** | `briq-07d-snekbyte` (in_progress) | Specialty applications (media, authenticator, downloader, DevMgmt, cleanup, SnekByte) |
| `release_gate` | **OFFLINE_TESTED** | `briq-09a-test-strategy-soak` (implemented) | Offline release gate, soak harness, reboot policy and rollback discipline |
| `release_reboot_rollback` | **OFFLINE_TESTED** | `briq-09b-reboot-rollback-policy` (implemented) | Autonomous reboot policy and per-component rollback |
| `release_deliverables` | **OFFLINE_TESTED** | `briq-09c-release-deliverables` (implemented) | Reproducible release deliverables and version |

### Detail

#### `touchscreen` — Touchscreen (sec_ts) controller -> evdev -> libinput -> Phoc -> PWA

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-01d-touch-owner-test` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes  ·  **blocked by:** boot mode (LPM/charger): needs a normal boot before the owner test
* **Hardware evidence:** `/proc/cmdline: androidboot.mode=charger, charging_mode=0x3030`; `dmesg: [sec_input] sec_ts_init: Do not load driver due to : lpm 1`; `ls /sys/class/sec/tsp -> No such file or directory`
* **Repository evidence:** `tools/s10plus/a33/nuxel-touch-trace.py`; `tools/s10plus/a33/tests/run-touch-tests.sh`; `tools/s10plus/a33/nuxel-libinput-path.so`; `docs/beta-finalization/preflight/live/batch-5-cycle-003-recheck.out`
* **Owner action:** Reboot into Nuxel without charger mode, then run the finger test in BETA-MANUAL-PROOF-CHECKLIST.md section 1
* **Notes:** The kernel deliberately does not bring sec_ts up while androidboot.mode=charger sets lpcharge=1 ('[sec_input] sec_ts_init: Do not load driver due to : lpm 1'), so no touch evdev node exists in the current boot (/proc/bus/input/devices lists event0-event6 only: meta_event, gpio_keys, grip_sensor, ssp_context, Headset, hall, certify_hall). The trace tool, the libinput path shim, the boot-mode guard and the bounded owner capture harness are implemented and pass their offline suites. A real finger test is the only thing that can promote this, and it needs a NORMAL boot first.

#### `display_framebuffer` — Display path: Phoc (headless) -> Wayland screencopy -> DECON framebuffer

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-02c-fb-colour-conversion` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `fb0 name 1440,6080 32bpp`; `no /dev/dri (CONFIG_DRM is not set)`; `receipt: PHONE_UI_FRAME_COMMITTED ... abgr8888`
* **Repository evidence:** `tools/s10plus/a33/nuxel-wl-fb.c`; `docs/beta-finalization/boot/COLOUR-CONVERSION.md`; `docs/beta-finalization/preflight/live/batch-2-graphics-input.out`; `docs/beta-finalization/preflight/live/batch-4-pkgs-services-receipts.out`
* **Owner action:** Confirm on the panel that the launcher is drawn with correct colours and no animation bleed-through
* **Notes:** There is no DRM/KMS device on this 4.14 vendor tree ('/dev/dri' absent); /dev/fb0 is 1440x6080x32 (double-buffered 1440x3040) and fb1 is the DECON tertiary. The XRGB8888 -> Samsung ABGR8888 conversion is proven at byte level offline and the live receipts record 'PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888'. Single framebuffer ownership is enforced (owner=nuxel-wl-fb). Visual confirmation on the panel is an owner step.

#### `boot_animation_handoff` — Boot animation -> launcher display-ownership handoff

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-02a-readiness-handoff` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `receipt: ANIMATION_STOP_CONFIRMED`; `receipt: LAUNCHER_DISPLAY_OWNER`; `receipt: ANIM_STAGE=ANIMATION_STOPPED ANIM_OWNER=nuxel-wl-fb`
* **Repository evidence:** `tools/s10plus/a33/nuxel-anim-handoff.py`; `tools/s10plus/a33/tests/test-handoff-logic.c`; `docs/beta-finalization/boot/ANIMATION-HANDOFF.md`; `docs/beta-finalization/preflight/live/batch-4-pkgs-services-receipts.out`
* **Owner action:** Watch a full cold boot for flicker, ghost frames or animation running over the launcher (manual proof checklist section 3)
* **Notes:** The handoff is receipt-driven: BOOT_WAIT_LAUNCHER -> LAUNCHER_READY -> ANIMATION_STOP_REQUESTED -> ANIMATION_STOP_CONFIRMED -> LAUNCHER_DISPLAY_OWNER, with a single framebuffer owner. The live receipts show every stage reached on the handset. The artwork is the original assets/nuxel-boot-animation.mp4 (1080x1920, 24 fps, 192 frames) packed into the NUXANM01 container; flicker/ghost-frame judgement needs an eye.

#### `launcher` — Nuxel Home PWA launcher (WebKitGTK kiosk under Phoc)

* **Verdict:** `OFFLINE_TESTED`  ·  **record:** `briq-02d-launcher-parity` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `live: phoc + nuxel-pwa-host + WebKitWebProcess running`; `live: curl 127.0.0.1:8000 answered (http_ok in the soak probe)`
* **Repository evidence:** `pwa/nuxel-home/`; `tools/s10plus/a33/tests/launcher-registry-test.js`; `docs/beta-finalization/vm/`; `docs/beta-finalization/preflight/live/batch-2-graphics-input.out`
* **Owner action:** Run the launcher acceptance items in the manual proof checklist section 2
* **Notes:** The launcher is the authoritative UI (pwa/nuxel-home as single source of truth) served from 127.0.0.1:8000 and rendered by WebKitGTK 2.52.5 inside phoc 0.54.0, with nuxel-pwa-host as the browser host and a legacy framebuffer UI kept only as a non-competing recovery fallback. The record's declared offline ceiling is VERIFIED_IN_VM_ONLY, but the VM tier (X-vm-*) was NOT executed in this repository-only pass, so the claim stops at OFFLINE_TESTED; a phone-level launcher acceptance pass is the owner step.

#### `wallpaper_and_assets` — Wallpaper and launcher asset integrity

* **Verdict:** `OFFLINE_TESTED`  ·  **record:** `briq-00d-baseline-protection` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `assets/nuxel-background.png (1257938 bytes, hash-pinned)`
* **Repository evidence:** `assets/nuxel-background.png`; `docs/beta-finalization/baseline-protection.json`; `tools/beta/regression-guard.sh`
* **Notes:** assets/nuxel-background.png is protected by a recorded hash in the baseline register and is referenced unchanged by the launcher CSS; the regression guard fails if it changes. The asset pipeline is offline-tested; on-panel appearance is part of the display owner step.

#### `safe_zones` — Ten-zone status-bar / camera-cutout safe areas

* **Verdict:** `OFFLINE_TESTED`  ·  **record:** `briq-02e-safe-zones-statusbar` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `/dev/fb0 1440x3040 panel geometry (dual cutout, portrait)`
* **Repository evidence:** `pwa/nuxel-home/js/safe-zones.js`; `configs/nuxel/display/statusbar-safezones.json`; `tools/s10plus/a32/tests/safe-zones-test.js`
* **Notes:** The A32 ten-zone model is preserved with the S10+ portrait preset that excludes the rightmost two zones, a Settings editor and live preview. The layout is verified numerically (zones never overlap the status items). The record's declared offline ceiling is VERIFIED_IN_VM_ONLY, but the VM tier was not executed here, so the claim stays OFFLINE_TESTED; panel rendering is owned by the display step.

#### `verbose_boot_setting` — Verbose boot setting and the one-time Bixby early-hold override

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-02b-verbose-boot-setting` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes  ·  **blocked by:** early-key capture inside the initramfs requires a BOOT image update (not performed)
* **Hardware evidence:** `/proc/cmdline loglevel=4 recorded`; `gpio_keys on event1 (Bixby key present)`
* **Repository evidence:** `configs/nuxel/boot/verbose-boot.json`; `docs/beta-finalization/boot/VERBOSE-BOOT.md`
* **Owner action:** Hold Bixby during the first two seconds of a normal boot and confirm verbose output (checklist section 3)
* **Notes:** Settings -> Developer -> Boot Diagnostics (standard animation, persistent verbose boot, verbosity level) is implemented and persisted in /etc/nuxel/boot/verbose-boot.json. The one-time 'hold Bixby during the first ~2 s' override is implemented in userspace with the evdev keycode and honest limits; the initramfs-side early-key capture would need a BOOT update and is reported as BLOCKED_KERNEL rather than claimed working.

#### `boot_mode_guard` — Charger/LPM boot-mode detection and the initramfs-side fix

* **Verdict:** `BLOCKED_KERNEL`  ·  **record:** `briq-01c-chargermode-bootmode` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes  ·  **blocked by:** kernel/initramfs (BOOT partition) change; not deployed by this run
* **Hardware evidence:** `/proc/cmdline androidboot.mode=charger`; `lpcharge=1 -> sec_ts refused init`
* **Repository evidence:** `configs/nuxel/bootmode/bootmode-guard.json`; `tools/s10plus/a33/nuxel-bootmode-guard.sh`; `docs/beta-finalization/preflight/live/batch-5-cycle-003-recheck.out`
* **Notes:** The guard reads androidboot.mode/charger state and refuses touch-dependent acceptance in LPM instead of pretending. The actual repair (bringing sec_ts up in LPM, or a guaranteed normal-mode boot) lives in the kernel/initramfs and is therefore BLOCKED_KERNEL: this repository may prepare the patch and the exact deploy step, but not deploy it.

#### `wifi` — Wi-Fi (Broadcom brcmfmac) enumeration, scan and association

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-03a-wifi` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `rfkill: phy0 Wireless LAN soft-blocked: no`; `rfkill: brcmfmac-wifi Wireless LAN soft-blocked: no`; `ip -br link: wlan0/wlan1 DOWN`
* **Repository evidence:** `configs/networkmanager/10-nuxel-s10plus-wifi.conf`; `tools/s10plus/a33/nuxel-wifi-diag.sh`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`; `docs/beta-finalization/preflight/live/batch-5-cycle-003-recheck.out`
* **Owner action:** Provide a permitted test SSID (never the owner's production credentials in logs) and run manual proof checklist section 4
* **Notes:** The hardware enumerates: rfkill shows phy0 + brcmfmac-wifi (both unblocked), and wlan0 / wlan1 / p2p0 exist but are DOWN. The config, the diagnostics tool and the association path are written; the association/DHCP/DNS/reconnect acceptance needs a permitted test network and therefore an owner, and the interface is not yet brought up or exposed in NetworkManager. No radio firmware partition is ever modified.

#### `bluetooth` — Bluetooth (BlueZ) controller, pairing and profiles

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08d-bluetooth` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `rfkill: bcm43xx Bluetooth Soft blocked: yes`
* **Repository evidence:** `configs/nuxel/bluetooth/bluetooth.json`; `configs/nuxel/bluetooth/main.conf.d/60-nuxel.conf`
* **Owner action:** Enable Bluetooth and pair a known headset/phone; checklist section 11
* **Notes:** A Bluetooth controller exists in the kernel (rfkill entry 'bcm43xx Bluetooth') but it is SOFT BLOCKED and no BlueZ service was observed running in the live preflight, so no scan, pair, profile or reconnection claim can be made yet. Real pairing needs a second device, which is an owner step.

#### `modem_sim` — Shannon LTE modem and SIM (beyond2lte)

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08i-sim-microsd-modem` (state `pending`, verdict `none`)
* **Hardware present:** yes  ·  **blocked by:** vendor modem interface not consumable by the upstream ModemManager plugin
* **Hardware evidence:** `mmcli -L -> No modems were found`; `ls /sys/class/net -> rmnet0..7, umts_dm0, mcps0`; `ModemManager.service active`
* **Repository evidence:** `configs/nuxel/`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Owner action:** Insert/confirm the SIM tray arrangement and report the carrier; checklist section 16
* **Notes:** The Shannon host transport is exposed to the kernel (rmnet0-rmnet7, umts_dm0, mcps0) but ModemManager reports 'No modems were found', so there is no usable modem object: registration, data, SMS and calls are blocked on a driver/plugin path rather than on userspace. EFS/IMEI/calibration and the radio firmware are never touched, and no IMSI or PIN is ever logged.

#### `microsd` — microSD controller, insertion and safe mount/eject

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08i-sim-microsd-modem` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `lsblk: sda 119.2G with sda1..sda31 (UFS), no mmcblk device present`
* **Repository evidence:** `configs/nuxel/`; `docs/beta-finalization/preflight/live/batch-1-identity.out`
* **Owner action:** Insert a microSD card carrying only disposable data and run checklist section 18
* **Notes:** The partition table shows the UFS device only (sda1..sda31); no removable controller was exercised in the preflight. Detection, filesystem metadata reading, safe mount and eject are implemented against the generic block layer, but physical insertion and the no-auto-format guarantee need a card and an owner.

#### `audio_speaker` — Speaker / earpiece audio path (Madera + ABox + CS35L40)

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-03c-audio-speaker` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `/proc/asound/cards: 0 beyond-madera, 1 abox_vdma, 2 abox_dump`; `aplay: command not found (alsa-utils absent)`
* **Repository evidence:** `configs/alsa-ucm/`; `configs/pipewire/`; `configs/wireplumber/`; `tools/s10plus/a33/nuxel-audio-diag.sh`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Owner action:** Listen for a low-volume test tone with an ear to the earpiece; checklist section 6
* **Notes:** The ALSA cards register (beyond-madera, abox_vdma, abox_dump) with playback and capture PCMs. pipewire, wireplumber and alsa-utils are NOT installed on the phone yet and the live preflight shows no audible-output test, so the honest state is 'codec registered, audibility unproven'. Only low-volume safe tests are permitted; amplifier protection and thermal limits are never disabled.

#### `headphones` — Headphones and USB-C audio accessories

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-03d-headphones-usbc` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `input device 'Headset' -> event4 (jack detection present)`
* **Repository evidence:** `configs/nuxel/audio/jack-routes.json`; `tools/s10plus/a33/nuxel-headphone-diag.sh`; `docs/beta-finalization/preflight/live/batch-2-graphics-input.out`
* **Owner action:** Plug in headphones (and an active USB-C DAC) for checklist sections 6-7; keep the USB console on a separate port/path
* **Notes:** A 'Headset' input device exists (event4 via sec_key_notifier), so the jack detection path is present. USB-C audio is split into UAC (kernel driver + PipeWire/ALSA) and passive analog accessory mode, which may simply not be supported; the USB role conflict with the live-console gadget is documented because losing the console would remove the only way back.

#### `buttons` — Hardware buttons: power, volume, Bixby (A32 manager + gesture FSM)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-03e-buttons-gestures` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `gpio_keys on event1 (power + volume + Bixby)`; `receipt: 2026-09-15T00:01:02Z ACTION source=bixby(short) action=open-terminal`
* **Repository evidence:** `tools/s10plus/a33/nuxel-button-manager.c`; `configs/nuxel/buttons.json`; `docs/beta-finalization/preflight/live/batch-4-pkgs-services-receipts.out`
* **Notes:** The A32 button manager is preserved (not replaced) and runs on the handset: the live receipts contain 'ACTION source=bixby(short) action=open-terminal'. The extended deterministic gesture FSM (chords, long/double press, screenshot, sound-mode cycle) and the power menu are implemented with real evdev keycodes and arbitration priority, and pass their offline state-machine tests; the record has no terminal verdict yet, so the extension is reported as implemented but not yet accepted on the device.

#### `power_menu` — Nuxel power menu (lock, off, restart, recovery, Download Mode entries)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-03e-buttons-gestures` (state `pending`, verdict `none`)
* **Hardware present:** yes  ·  **blocked by:** no verified reboot-to-recovery/download method on this boot chain
* **Repository evidence:** `pwa/nuxel-home/js/qs.js`; `configs/nuxel/buttons/reboot-gate.json`
* **Notes:** The power menu is implemented with confirmation for destructive actions and extra warnings for recovery/Download Mode. Those two entries are offline-tested UI only: no verified Samsung reboot method exists for them, no magic reboot string is guessed, and Nuxel never triggers recovery or Download Mode.

#### `power_management` — Power management: governors, idle behaviour, power modes

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-08a-power-management` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `scaling_available_governors: performance schedutil`; `thermal_zone0 type=BIG temp=39000`; `nproc=8`
* **Repository evidence:** `configs/nuxel/`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Owner action:** Run the power-mode persistence items in checklist section 24
* **Notes:** cpufreq exposes exactly two governors (performance, schedutil) across 8 CPUs with schedutil active, and thermal zone 0 (BIG) reads ~39 C at idle. Performance/Balanced/Power-saving modes can therefore only use governors the kernel really implements. Thermal throttling and charging protection stay untouched; idle-drain and governor persistence tests across a reboot still need the live tier.

#### `battery_charging` — Battery and charging telemetry

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-08a-power-management` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `/sys/class/power_supply/battery: capacity=100 status=Full temp=271`
* **Repository evidence:** `configs/nuxel/`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Notes:** The fuel gauge is readable through the standard interface (capacity 100, status Full, health Good, temp 27.1 C, voltage 4317000 uV, charge_type Fast), and the phone is currently in charger mode. Charging protections are never modified. Presentation in Settings and behaviour across charge cycles is not yet verified.

#### `haptics` — Vibration / haptics

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08b-vibration-haptics` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `/sys/class/timed_output/vibrator present`
* **Repository evidence:** `configs/nuxel/haptics/haptics.json`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Owner action:** Hold the phone and trigger the shortest vibration pattern; checklist section 10
* **Notes:** A real control path exists: /sys/class/timed_output/vibrator (with no /sys/class/vibrator). Enable/disable, vibration-only mode and pattern/strength settings are implemented against that interface rather than by blind register toggles, and the test is bounded. Whether the motor actually buzzes can only be felt by a human.

#### `flashlight` — Camera torch / flashlight

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08c-flashlight-led` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `/sys/class/leds/torch-sec1 present`
* **Repository evidence:** `pwa/nuxel-apps/`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Owner action:** Toggle the torch with the camera app open and closed; checklist section 9
* **Notes:** A torch control path exists (/sys/class/leds/torch-sec1). Toggle, state, auto-timeout, camera-safe brightness and camera/flashlight ownership arbitration are implemented; thermal limits are preserved. The camera flash is never presented as a multi-colour notification LED, and the configuration only exposes what the device really has.

#### `notification_led` — RGB notification LED

* **Verdict:** `NOT_SUPPORTED_ON_DEVICE`  ·  **record:** `briq-08c-flashlight-led` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `/sys/class/leds -> leds-sec1, torch-sec1 (no rgb/multicolour entry)`
* **Repository evidence:** `configs/nuxel/`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`
* **Notes:** The live preflight found only the Samsung LED-class entries leds-sec1 and torch-sec1 with no proven per-colour RGB control path on this unit, and the camera flash is a single-colour torch. Per-colour notification light configuration is therefore reported as not supported on this device instead of being simulated; an optional software edge light, if enabled, is labelled as software.

#### `sensors` — Sensor inventory and integration

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08g-sensors` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `input devices: grip_sensor, ssp_context, hall, certify_hall`; `no /sys/bus/iio device enumeration was observed in the preflight`
* **Repository evidence:** `pwa/nuxel-apps/`; `docs/beta-finalization/preflight/live/batch-2-graphics-input.out`
* **Owner action:** Wave/move the phone and watch the sensors page; checklist section 14
* **Notes:** The live inventory shows grip_sensor (event2), ssp_context (event3), hall (event5) and certify_hall (event6) as evdev sources, plus the metadata node. No accelerometer, gyro, magnetometer, ambient-light, proximity or barometer IIO device was confirmed, so none is claimed. A sensors diagnostic page reports detection, driver, value, units, rate, permission and error state rather than inventing values.

#### `camera` — Cameras (V4L2 / media controller) and gallery

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08h-camera` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `no /dev/video* node was observed in the preflight captures`
* **Repository evidence:** `configs/nuxel/camera/camera.json`; `pwa/nuxel-apps/`
* **Owner action:** Point the camera at a subject and capture a still; checklist section 15
* **Notes:** No V4L2 capture device was enumerated in the live preflight, so no viewfinder, photo or video capability is claimed. The implementation targets the kernel's V4L2/media-controller surface with no Android HAL and no Android framework dependency, keeps explicit user-controlled recording with a visible indicator, and never performs stealth recording. Sensor inventory (front/rear) and capture are unproven.

#### `gnss` — GNSS / location and the Nuxel Maps app

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08f-gps-gnss` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `no GNSS/gnss device was observed in the preflight captures`
* **Repository evidence:** `configs/nuxel/gnss/gnss.json`; `configs/nuxel/gnss/osm-tiles.json`; `pwa/nuxel-apps/`
* **Owner action:** Go outdoors, wait for a fix and check the coordinates; checklist section 13
* **Notes:** No GNSS interface was enumerated in the live preflight, so no position fix is claimed. Maps is built on OpenStreetMap-compatible data with search, zoom/pan, manual location fallback, bookmarks, OSM attribution and a responsible tile-caching policy, and no Google location service is used or required. A fix requires sky view and an owner.

#### `nfc` — NFC controller and tag support

* **Verdict:** `NEEDS_OWNER_TEST`  ·  **record:** `briq-08e-nfc` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `no nfc/nci device node or rfkill entry observed in the preflight`
* **Repository evidence:** `configs/nuxel/`; `docs/beta-finalization/preflight/live/batch-1-identity.out`
* **Owner action:** Offer an NFC tag to the phone's antenna area; checklist section 12
* **Notes:** No NFC controller interface was found in the live preflight, and no NCI-capable device node is created, so tag poll/read/write cannot be claimed. Payment and secure-element use (Google Pay, bank wallets) is explicitly not supported and not implied. Basic tag support is the beta target, pending a real controller path.

#### `timekeeping` — Time, RTC persistence and time synchronisation

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-03b-time-rtc-timesync` (state `in_progress`, verdict `none`)
* **Hardware present:** yes  ·  **blocked by:** no exposed RTC device; must not fabricate a hardware clock
* **Hardware evidence:** `timedatectl: RTC time: n/a, RTC in local TZ: no`; `device date 2026-09-15T00:15:17Z vs host 2026-10-16T18:25:54Z`; `rpm: signature ... invalid: signature is not alive`
* **Repository evidence:** `configs/nuxel/time/`; `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out`; `docs/beta-finalization/preflight/live/batch-1-identity.out`
* **Owner action:** Check the clock after a network connection; checklist section 5
* **Notes:** There is NO battery-backed RTC exposed to this kernel: timedatectl reports 'RTC time: n/a' and the device clock reads 2026-09-15 while the host reads 2026-10-16. The wrong clock already has a visible consequence: RPM refuses a Fedora signature as 'not alive' ('Not live until 2026-09-15T17:18:38Z'), which breaks package verification. The plan is a plausible last-known timestamp plus NTP once the network exists, with the uncertainty reported rather than a fabricated precise time.

#### `live_console` — Live console over USB CDC-ACM (debug path and app)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-07e-live-console-app` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `live batches 1-5 captured over /dev/ttyACM0 with sha_ok=yes per frame`
* **Repository evidence:** `scripts/s10plus-debug-pack/nuxel-live.sh`; `tools/beta/live/nuxel_live.py`; `docs/beta-finalization/preflight/live/batch-1-identity.out`
* **Notes:** The USB CDC-ACM console is proven working: every live preflight batch was captured through /dev/ttyACM0 with framed commands and per-frame sha checks. The console app, the status-bar toggle, the remote-session ownership arbitration and the hard-disable policy are implemented offline; server-side takeover and the emergency disable still need a live rehearsal. The console is the only way back to a broken phone and must be preserved.

#### `permissions` — Per-app permissions, privacy controls and global switches

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-05a-permission-manager` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `kernel 4.14.253 with AppArmor + cgroup v2 (per the preflight and configs)`
* **Repository evidence:** `configs/apparmor.d/`; `configs/nftables/nuxel-app-firewall-cgroupv2.nft`; `shell/nuxel-shell/nuxel-permissions/`
* **Notes:** The permission store, the fail-closed denial path, the revocation flow and the global interface switches are implemented and pass their offline tests against only the confinement Linux 4.14 actually provides (no Landlock). Enforcement is never claimed as 'unbypassable': root and kernel compromise are documented limitations, and the tested attacker is an ordinary sandboxed app.

#### `firewall` — Firewall app (single authoritative backend)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-05b-firewall-app` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `kernel nftables/cgroup-v2 availability recorded in the preflight`
* **Repository evidence:** `configs/nftables/nuxel-app-firewall.nft`; `configs/nftables/nuxel-console-guard.nft`; `tools/s10plus/a33/security-tests/test-firewall.sh`
* **Notes:** nftables is the single chosen backend (never two managers). Rule translation, zones, logging, hosts-file editing with validation and atomic writes, import/export and safe rollback are implemented and offline-tested, including a fail-closed console guard so a rule set cannot cut the only reachable debug session. Live enforcement on the phone is not claimed.

#### `vpn_remote` — VPN manager, Tor tools, remote access and device connect

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-05c-vpn-tor-remote` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `offline suite: honest-enforcement labels under a mock network`
* **Repository evidence:** `tools/s10plus/a33/security-tests/test-vpn-tor.sh`; `configs/nftables/nuxel-vpn-killswitch.nft`
* **Notes:** OpenVPN/WireGuard/ZeroTier profiles, Tor start/stop with SOCKS status and leak prevention, and SSH/SFTP/VNC/RDP file-transfer clients are implemented with explicit honest labels: running tor.service is never presented as 'all traffic anonymised', AirPlay-like protocols are named precisely before any claim, and no always-on listener is started without the user. No third-party account or credential is hardcoded.

#### `security_audit` — Security auditor (read-only)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-05d-security-auditor` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `read-only design: no write path in the audit surface`
* **Repository evidence:** `shell/nuxel-shell/`; `docs/beta-finalization/`
* **Notes:** The auditor is read-only by default (no auto-hardening) and reports coverage, tool versions and exceptions. A generic score is never presented as a certified CIS benchmark result. Its findings on the live phone are not yet produced.

#### `core_apps` — Core phone applications (dialer, messages, contacts, mail, calendar, notes, files, clock, terminal)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-06a-core-app-inventory` (state `pending`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `registry: 11 launcher app ids; verify-app-registry.py gates assets + bridge pin`
* **Repository evidence:** `pwa/nuxel-apps/`; `pwa/nuxel-home/manifest.json`; `tools/s10plus/a33/verify-app-registry.py`
* **Notes:** The canonical app registry, the launch bridge and the applications exist as repository sources with offline tests, and the launcher manifest lists the registry ids. Launch behaviour on the phone and the per-app working state are not yet accepted; an icon is never counted as a working app.

#### `keyboard` — Virtual keyboard and physical keyboard support

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-06d-settings-and-keyboard` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `live: physical keyboard input path over the USB console session`
* **Repository evidence:** `pwa/nuxel-apps/`; `shell/`
* **Notes:** The keyboard work targets the Wayland text-input protocol rather than a DOM-only fake, so it can serve native apps as well as WebKitGTK, with numeric/symbol layouts, shift, backspace, enter, space, key repeat and optional haptics, plus physical USB/Bluetooth keyboard support. Live typing on the phone is not yet verified.

#### `app_store` — NuxTore app store (Flatpak + PWA, no account)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-07a-nuxtore` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `flatpak: command not found (not installed on the handset)`
* **Repository evidence:** `pwa/nuxel-apps/nuxtore/`; `docs/app-store.md`; `pwa/flatpak/`
* **Owner action:** After Flatpak is installed, install one cached package; checklist section 19
* **Notes:** NuxTore has browse/search/categories/type filters/sort, details with permissions, install/uninstall/update, cached offline catalogue and a privileged mediation service so no arbitrary shell is reachable from WebKit. flatpak is NOT installed on the phone and no remote is configured, so no install can be claimed; offline install is never claimed unless packages and runtimes are cached.

#### `userspace_packages` — Fedora 43 ARM64 userspace and package manifest

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-04a-fedora-packages` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `rpm -qa | wc -l -> 410`; `verify-packages.py: resolved=50 missing=0 pin_mismatches=0`; `rpm -q pipewire wireplumber alsa-utils flatpak -> not installed`
* **Repository evidence:** `images/s10plus/packages-manifest.json`; `tools/s10plus/a33/verify-packages.py`; `docs/beta-finalization/preflight/live/batch-4-pkgs-services-receipts.out`
* **Notes:** 410 RPMs are installed and the manifest is resolved against the real Fedora 43 ARM64 repositories (93991 NEVRAs) without --skip-unavailable. Live gaps are recorded rather than hidden: pipewire, wireplumber, alsa-utils and flatpak are NOT installed, and systemd/glibc carry the kernel-4.14 patches. The gap list is the actionable inventory.

#### `services` — Service definitions and boot graph

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-04b-service-definitions` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `systemctl is-system-running -> degraded; 1 failed unit (nuxel-touch-arm)`; `systemctl list-units --state=running -> 16 units including the whole Nuxel stack`
* **Repository evidence:** `services/`; `shell/config/systemd-user/`; `tools/s10plus/a33/verify-service-graph.py`
* **Notes:** The unit set and boot graph pass an offline verifier (no cycles, no unsatisfied units, no system->user enablement). On the handset the live boot is 'degraded' with exactly one failed unit (nuxel-touch-arm.service, which fails *by design* in charger mode) while the core stack runs: dbus, logind, journald, polkit, seatd, NetworkManager, ModemManager, nuxel-wayland, nuxel-wl-fb, nuxel-button-manager.

#### `app_infrastructure` — Application infrastructure: registry, portal, notifications, bridge, local web server

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-04c-app-infrastructure` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `live: python3 -m http.server 8000 --bind 127.0.0.1 serving the launcher`
* **Repository evidence:** `services/nuxel-bridge/`; `services/nuxel-portal/`; `services/nuxel-notifications/`; `pwa/nuxel-common/`
* **Notes:** The bridge, portal (consent + one-shot grants), notification store and the local web server exist with offline contract tests (bridge version pinning is enforced loudly and never silently falls back to mock data). Live end-to-end activation from the launcher is not yet accepted.

#### `specialty_apps` — Specialty applications (media, authenticator, downloader, DevMgmt, cleanup, SnekByte)

* **Verdict:** `IMPLEMENTED_NOT_DEPLOYED`  ·  **record:** `briq-07d-snekbyte` (state `in_progress`, verdict `none`)
* **Hardware present:** yes
* **Hardware evidence:** `offline: parity fixtures + vendored upstream engine tests`
* **Repository evidence:** `pwa/nuxel-apps/snekbyte/`; `tools/s10plus/a33/snekbyte/`; `pwa/nuxel-apps/authenticator/`
* **Notes:** SnekByte is a genuine port of the supplied upstream source (gameplay parity fixtures plus the vendored upstream test suite present in the tree) packaged as a discoverable Nuxel app with touch controls added and the original rules preserved. The media, authenticator (RFC 4226/6238 offline), downloader, DevMgmt, cleanup and root-control apps are repository sources with offline tests. Play on the phone is unverified.

#### `release_gate` — Offline release gate, soak harness, reboot policy and rollback discipline

* **Verdict:** `OFFLINE_TESTED`  ·  **record:** `briq-09a-test-strategy-soak` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `offline: run-all-tests.sh table + summary JSON committed as evidence`; `offline: 22 rollback/reboot scenarios PASS`
* **Repository evidence:** `tools/beta/run-all-tests.sh`; `tools/beta/soak.sh`; `tools/beta/rollback.sh`; `tools/beta/reboot-policy.sh`; `docs/beta-finalization/testing/TEST-STRATEGY.md`; `docs/beta-finalization/release/evidence/run-all-tests-summary.json`; `docs/beta-finalization/release/evidence/soak-selftest.txt`; `docs/beta-finalization/release/evidence/rollback-selftest.txt`
* **Notes:** The L1-L6 hierarchy is implemented and automated: L1 static (syntax, JSON, tree invariants, orphan tests), L2 unit, L3 integration (including the A32 baseline regression guard), L4 VM and L5 live as gated external tiers, L6 owner as the manual checklist. The soak is bounded and its resource/performance criteria are the single source of truth in soak_lib.py; the reboot policy refuses blind repeats and the rollback discipline is proven under mocked failure. The 8 hour device soak and the VM tiers are BLOCKED_EXTERNAL_RESOURCE / unrun in a repository-only pass.

#### `release_reboot_rollback` — Autonomous reboot policy and per-component rollback

* **Verdict:** `OFFLINE_TESTED`  ·  **record:** `briq-09b-reboot-rollback-policy` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `offline: 22 mocked-failure scenarios PASS, reboot dry run inert`
* **Repository evidence:** `tools/beta/reboot-policy.sh`; `tools/beta/rollback.sh`; `tools/beta/health-check.sh`; `docs/beta-finalization/release/REBOOT-ROLLBACK.md`; `docs/beta-finalization/release/evidence/reboot-policy-selftest.txt`
* **Notes:** Record previous hash -> stage -> verify -> atomic install -> restart the smallest affected service -> health check -> roll back on failure, with per-briq baselines under /var/lib/nuxel/rollback/<briq-id>/, a live-console-preserving firewall guard, and a reboot policy with a 3-reboot budget, changed-diagnostic requirement and the three-same-mode-failure guard. Proven offline under mocked failure. The live rehearsal (briq-10c) is the first VERIFIED_ON_S10PLUS opportunity for it.

#### `release_deliverables` — Reproducible release deliverables and version

* **Verdict:** `OFFLINE_TESTED`  ·  **record:** `briq-09c-release-deliverables` (state `implemented`, verdict `OFFLINE_TESTED`)
* **Hardware present:** yes
* **Hardware evidence:** `manifest validated against its schema and the work-queue records`
* **Repository evidence:** `CHANGELOG.md`; `VERSION`; `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json`; `docs/beta-finalization/release/ROLLBACK.md`
* **Notes:** The changelog, the version identifier, this capability manifest (schema-validated and cross-checked against the work queue) and the rollback instructions are repository deliverables. No silent phone-only fix exists: every change in the beta is repository source with a build/test path. Nothing is published and no store submission is made.

## 4. Hardware truth summary

* Touch controller: present in hardware, deliberately NOT initialised in LPM/charger mode; no touch evdev node in the last boot.
* Display: no DRM/KMS; DECON framebuffer with a userspace Wayland->fb bridge; ABGR8888 proven in the commit path.
* Wi-Fi: brcmfmac enumerates (phy0, wlan0/wlan1/p2p0) and is unblocked but DOWN; association unproven.
* Bluetooth: controller present (bcm43xx) but soft-blocked; no BlueZ service observed running.
* Modem: Shannon net devices exposed (rmnet0-7, umts_dm0, mcps0); ModemManager finds no modem object.
* Audio: beyond-madera / abox_vdma / abox_dump cards registered; pipewire, wireplumber and alsa-utils absent; audibility unproven.
* Haptics: /sys/class/timed_output/vibrator present (owner must feel it).
* Torch: /sys/class/leds/torch-sec1 present; RGB notification LED not proven (NOT_SUPPORTED_ON_DEVICE for per-colour config).
* Sensors: grip_sensor, ssp_context, hall, certify_hall as evdev sources; no confirmed IIO motion/light/proximity device.
* Camera: no V4L2 capture node observed; capture capability unproven.
* GNSS: no GNSS interface observed; fix unproven.
* NFC: no controller interface observed; tag support unproven.
* microSD: no removable controller exercised; insertion/eject unproven.
* Timekeeping: no exposed battery-backed RTC (timedatectl: RTC time: n/a); clock is ~31 days behind and already breaks RPM signature verification.
* Battery/charging: fuel gauge readable (100%, Full, 27.1 C); charge protections untouched.
* Buttons: gpio_keys on event1 with a live Bixby press receipt; the A32 button manager runs.
* Live console: USB CDC-ACM /dev/ttyACM0 proven (all five preflight batches captured through it).

## 5. Evidence sources

* `docs/beta-finalization/preflight/live/batch-1-identity.out (device identity, cmdline, storage, kernel)`
* `docs/beta-finalization/preflight/live/batch-2-graphics-input.out (framebuffer, services, input devices)`
* `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out (audio cards, rfkill, battery, cpufreq, LEDs)`
* `docs/beta-finalization/preflight/live/batch-4-pkgs-services-receipts.out (boot receipts, units, packages, sec_ts)`
* `docs/beta-finalization/preflight/live/batch-5-cycle-003-recheck.out (cycle-003 recheck, 10 frames sha-ok)`
* `docs/beta-finalization/workqueue/briq-*.json (the authorising work-queue records)`
* `docs/beta-finalization/release/evidence/ (offline release-gate, soak and rollback transcripts)`

## 6. Verification of this document

```bash
# schema validation + work-queue cross-check (also run by the release gate)
python3 tools/beta/validate-capability-manifest.py \
    --manifest docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json \
    --schema   docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.schema.json \
    --workqueue docs/beta-finalization/workqueue \
    --json     docs/beta-finalization/release/evidence/capability-manifest-crosscheck.json
```

The committed output of that command is
[`evidence/capability-manifest-crosscheck.txt`](evidence/capability-manifest-crosscheck.txt) (human-readable) and `evidence/capability-manifest-crosscheck.json` (machine-readable). A `VALID` verdict means *the manifest is internally consistent with the work queue* — it does **not** upgrade any subsystem's status. Two rules govern promotion:

* an installer/verifier that runs on the handset may promote a row with live evidence;
* a human performing the corresponding item in [`../BETA-MANUAL-PROOF-CHECKLIST.md`](../BETA-MANUAL-PROOF-CHECKLIST.md) may promote a row;
* **nothing else may**, and no automated pass in this repository ever rewrites this file.

## 7. Related deliverables

| Deliverable | Purpose |
|---|---|
| [`../../CHANGELOG.md`](../../../CHANGELOG.md) | the release history and what changed in this version |
| [`../../../VERSION`](../../../VERSION) | the canonical version identifier |
| [`../testing/TEST-STRATEGY.md`](../testing/TEST-STRATEGY.md) | the L1–L6 test hierarchy this manifest is gated by |
| [`../testing/SOAK-AND-PERFORMANCE.md`](../testing/SOAK-AND-PERFORMANCE.md) | the bounded soak and resource/performance criteria |
| [`REBOOT-ROLLBACK.md`](REBOOT-ROLLBACK.md) | the reboot policy and the rollback discipline |
| [`ROLLBACK.md`](ROLLBACK.md) | how to undo a release-level change |
| [`../system/DEPENDENCY-REPORT.md`](../system/DEPENDENCY-REPORT.md) | the Fedora 43 ARM64 dependency report (owned by bg-04; referenced, not duplicated here) |

*Generated from the work-queue records and the live preflight captures; every timestamp in the JSON is a real capture time.*
