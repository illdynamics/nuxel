# PWNAGE 29000 — NUXEL TOTAL HARDWARE UBERFIXER report

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Kernel:** Linux 4.14.253 (Samsung-derived baseline, untouched)
**Userspace:** Fedora 43 aarch64
**Date:** 2026-10-27
**Scope:** userspace only. No kernel, boot image, partition, modem or firmware
was flashed; no user data was wiped; no device was invented.

## 1. Root causes (with physical-device evidence)

| Symptom | Evidence (serial console on `/dev/ttyACM0`) | Root cause | Repair |
|---|---|---|---|
| Bluetooth QS `UNCHANGED: NO_ADAPTER` | `rfkill list`: `0: bcm43xx Bluetooth`, soft-blocked; `/sys/class/bluetooth/` empty (no `hci0`); `bluetooth.service` inactive; `dmesg` shows only `[BT] Bluetooth Power On.` on unblock; `/lib/firmware` has no `*.hcd`; platform driver `bcm43xx_bluetooth` bound at `/sys/bus/platform/drivers/bcm43xx_bluetooth/bluetooth` | Kernel has `CONFIG_BT_BCM43XX=y` and the driver powers the radio, but the BCM43xx HCD firmware blob is **missing**, so no `hci0` ever registers | Added firmware-presence/blatant `BLOCKED_FIRMWARE` reporting + a real privileged `bluetooth.power` actuator (rfkill unblock/block + `bluetooth.service` start/stop). QS now shows the concrete blocker, not a bare `NO_ADAPTER` |
| Location QS collapsed states | `GeoClue2` installed but `GetClient` returns `NoReply`; `/dev/ttyBCM` exists (0600 root) but no GNSS firmware in `/lib/firmware`; `spi17.0` bound to `brcm gps spi` | No GNSS firmware/reader; GeoClue has no working backend on this handset | (Prior 27000 work) explicit state machine kept; verified bridge reports `state=disabled/unavailable` and `gnss.blocker=no GNSS/sensor-hub firmware` |
| Audio Settings dash | `/proc/asound/cards`: `beyond-madera`, `abox_vdma`, `abox_dump`; `aplay -l` lists RDMA0-11/WDMA0-7; `pipewire`/`pipewire-pulse` binaries exist but **no systemd units** (so no sound server) | No audio provider in the bridge; Settings showed `—` | Added real ALSA provider: cards, playback/capture endpoints, service state, discovered `HPOUT1 Digital` control, volume read/set (15% verified) |
| HDMI/USB-C display | `/sys/class/drm` absent; `/proc/config.gz`: `CONFIG_DRM` **not set**, `CONFIG_EXYNOS_DISPLAYPORT=y`, `CONFIG_TYPEC=y`; `/sys/class/typec/port0` = `max77705-usbc`; `/sys/class/extcon/extcon0` = `130b0000.displayport` state `DP=0`; phoc runs with `--no-xwayland` and a framebuffer backend | Kernel has no DRM/KMS, so there is no connector/CRTC for USB-C DP Alt Mode; Mirror/Desktop cannot be driven by userspace | Added honest Displays page recording the exact missing layer |

## 2. Bluetooth deep-dive

The `bcm43xx_bluetooth` platform driver is bound and its rfkill write actually powers
the radio (`dmesg` prints `[BT] Bluetooth Power On.`), but no `hci0` is created
because the Samsung vendor HCD (`bcm4375B1_semco.hcd`) is absent from every
candidate directory (`/lib/firmware/brcm`, `/lib/firmware`,
`/usr/lib/firmware`, `/vendor/firmware`). This is **BLOCKED_FIRMWARE**, not a
missing package and not something userspace can invent.

New behavior (verified on-device):
- `BluetoothGetStatus` now returns `firmware_present: false`, `firmware_found: []`,
  `blocker: "BLOCKED_FIRMWARE"`, and a human detail line naming the missing HCD.
- `bluetooth.power` (root HTTP-bridge actuator) is gated by `bluetooth:manage`
  (`evil-app` → `CAPABILITY_DENIED`). Authorized `org.nuxel.Home` call produced:
  `steps: ["rfkill soft-block=False", "bluetooth.service started"]`, then honest
  `blocker: BLOCKED_FIRMWARE`. Disable restored `rfkill soft-block=True` +
  `bluetooth.service stopped`.
- QS tile reads `bluetooth.status` (authoritative) and calls `bluetooth.power`
  for toggles; its tooltip shows the blocker.

## 3. Audio deep-dive

The kernel ALSA path is present (`beyond-madera` = CS47L93 MADERA + 2x CS35L40 +
ABox), but the image ships no PipeWire/WirePlumber units, so the backend is
**ALSA-direct**. The provider discovers the playback control by probing observed
candidate names (never inventing one) and found **`HPOUT1 Digital`**.

Physical-device results:
- `audio.status`: cards `beyond-madera / abox_vdma / abox_dump`, playback
  RDMA0-11, capture WDMA0-7, backend `alsa-direct`, `volume_supported: true`.
- `audio.set-volume 15` → readback `volume_percent: 15` (success).
- `amixer -c 0 sset 'HPOUT1 Digital' mute` works (~12 s), but
  `... unmute` **hangs in kernel D-state** (>40 s, then leaves the codec control
  wedged). Therefore the provider reports `mute_supported: false`,
  `unmute_supported: false`, and refuses `set-muted(false)` with
  `UNMUTE_UNSUPPORTED` — it never half-offers a one-way mute.
- All amixer subprocesses are bounded (4 s) with a non-blocking select-based
  reader that abandons a D-state child instead of blocking the single-threaded
  HTTP bridge.

## 4. Display / USB-C deep-dive

- No `/sys/class/drm`; `CONFIG_DRM` is `not_set`. The image renders through the
  framebuffer (wl-fb) and phoc `--no-xwayland`.
- `CONFIG_EXYNOS_DISPLAYPORT=y`, `CONFIG_SND_SOC_SAMSUNG_DISPLAYPORT=y`,
  `CONFIG_TYPEC=y` exist, and a `130b0000.displayport` extcon + `max77705-usbc`
  Type-C port are present, but there is no DRM consumer for them.
- The standard Type-C Alt Mode stack (`CONFIG_TYPEC_TCPM`, `CONFIG_TYPEC_DP_ALTMODE`)
  is also absent.
- Therefore Mirror/Desktop are reported `supported: false` with blocker
  `no /sys/class/drm: kernel CONFIG_DRM=not_set ...`. No monitor was fabricated.

## 5. Files changed

- `services/nuxel-bridge/src/hw_providers.py` (new): `AudioProvider`,
  `DisplayProvider`, `bluetooth_set_power` — root-only, bounded, no shell.
- `services/nuxel-bridge/src/api.py`: import `hw_providers`; in-process RPC
  handlers for `audio.status/set-volume/set-muted`, `display.status`,
  `bluetooth.power` (capability-gated).
- `services/nuxel-bridge/src/bridge.py`: `BluetoothConnector` now reports HCD
  firmware presence, a machine-readable `blocker`, and attempts rfkill unblock
  even without an adapter (best-effort; the root HTTP bridge owns the real write).
- `pwa/nuxel-apps/settings/index.html`: added Bluetooth + Displays tabs; enhanced
  Sound tab with real device/service inventory; renamed `Display` → `Screen`.
- `pwa/nuxel-apps/settings/hardware-settings.js` (new): Bluetooth, Displays and
  Audio Settings wiring (same providers as QS).
- `pwa/nuxel-apps/settings/settings.js`: removed the OSD `volume-state` overwrite
  so `hardware-settings.js` owns the real ALSA volume display.
- `pwa/nuxel-apps/settings/app.json`: declare `bluetooth:manage/scan`.
- `configs/nuxel/permissions/nuxel-settings.json`: first-party
  `bluetooth:manage/scan` grants.
- `pwa/nuxel-home/js/qs.js`: Bluetooth QS toggle uses the privileged
  `bluetooth.power` actuator and shows the firmware blocker.
- `pwa/nuxel-common/bridge.js`: new verbs fail honestly when the bridge is
  offline (no mock success).
- `services/nuxel-bridge/test-hw-providers.py` (new): offline provider tests.
- `tests/a72/test_maps_location_integration.py`: extended the first-party grant
  scope assertion for the two new Bluetooth capabilities.
- `tools/beta/live/nuxel-29000-hardware-uberfixer-manifest.json` (new): deploy
  manifest used for the on-device install.

## 6. Tests

Host (offline, no device):
- `python3 services/nuxel-bridge/test-hw-providers.py` → ALL PASS
  (audio inventory, volume discovery/clamp, missing hardware, unmute refusal,
  display no-DRM blocker, bluetooth power rfkill+systemctl).
- `python3 services/nuxel-bridge/test-bluetooth-location.py` → ALL PASS.
- `python3 -m pytest tests/ -q` → **56 passed**.

Physical S10+ (serial console, deployed):
- `systemctl is-active nuxel-bridge nuxel-http-bridge nuxel-wayland` → all active;
  `nuxel-web` inactive (unchanged).
- `BluetoothGetStatus` → `firmware_present:false`, `blocker:BLOCKED_FIRMWARE`.
- `bluetooth.power` enable/disable → correct steps + honest readback (above).
- `audio.status` → real cards/devices, `HPOUT1 Digital` at 15%, muted.
- `audio.set-volume 15` → success; `audio.set-muted(false)` → `UNMUTE_UNSUPPORTED`.
- `display.status` → `drm_present:false`, Mirror/Desktop `false`, CONFIG_DRM blocker.
- `bluetooth.power` with `app_id=evil-app` → `CAPABILITY_DENIED`.
- Settings PWA serves 200 and contains `tab-bluetooth`/`tab-displays`.

## 7. Capability matrix

| Feature | Hardware detection | Provider/state | UI integration | Physical test | Blocker |
|---|---|---|---|---|---|
| Bluetooth | BCM4375 rfkill present, driver bound | `BLOCKED_FIRMWARE` (no hci0, HCD missing) | QS + Settings page | power toggle verified; no pairing possible | Missing `bcm4375B1_semco.hcd` |
| GPS/GNSS | `/dev/ttyBCM` + `brcm gps spi` bound | GeoClue unavailable; GNSS firmware missing | QS + Location page | none (no fix) | Missing BCM4773 GNSS firmware/reader |
| Audio | beyond-madera + RDMA/WDMA | ALSA-direct, no sound server | Settings page | volume read/set 15% verified; unmute hangs | MADERA `HPOUT1 Digital` unmute D-state hang |
| USB-C HDMI | max77705 Type-C + displayport extcon present | `BLOCKED_KERNEL` (no DRM) | Displays page | none (no monitor path) | `CONFIG_DRM not_set`, no DP Alt Mode stack |

## 8. Operator instructions

- Bluetooth: open Settings → Bluetooth, or Quick Settings → Bluetooth. The page
  shows the real controller/driver/rfkill/firmware state and the exact blocker.
- Location: Settings → Location & Maps (same provider state as the QS tile).
- Audio: Settings → Sound. Shows real cards/devices; Volume −/+ writes ALSA
  (≤25% cap); Mute is reported unavailable because unmute wedges the codec.
- Displays: Settings → Displays. Shows DRM/Type-C/extcon evidence and why
  Mirror/Desktop are unavailable.
- Regression: Wi-Fi, browser, shell, lockscreen, charging indicator and the
  serial Live Console were not modified by this work.

## 9. Rollback

The on-device install used `nuxel-live-deploy.py` with SHA-256 staging, atomic
install and rollback backups (`*.nuxel-rollback.pre-deploy-*`). To roll back:

```sh
sudo systemctl reset-failed nuxel-web 2>/dev/null || true
# restore each deployed file from its .nuxel-rollback.pre-deploy-* backup, then:
sudo systemctl restart nuxel-bridge nuxel-http-bridge
```

Repository rollback: `git checkout --` the changed files (or revert the diff),
remove the new files (`hw_providers.py`, `hardware-settings.js`, the manifest),
and re-run the relevant tests.

## 10. Scoped follow-up (genuinely missing kernel/driver capability)

1. **Bluetooth (BLOCKED_FIRMWARE):** obtain a licence/provenance-verified
   `bcm4375B1_semco.hcd` (or equivalent BCM4375 HCD) and install it to
   `/lib/firmware/brcm/` (userspace file copy, never a partition flash). Then
   re-run `nuxel-bluetooth-diag.sh on/status`. No userspace change can make
   `hci0` appear without this blob.
2. **GNSS (BLOCKED_FIRMWARE):** install the BCM4773 GNSS firmware and wire a
   bounded NMEA reader/gpsd provider; until then no coordinate may be claimed.
3. **Audio unmute (BLOCKED_KERNEL/driver):** the MADERA `HPOUT1 Digital` unmute
   D-state hang needs a kernel driver/UCM investigation (capture a real
   EnableSequence via `nuxel-audio-diag.sh capture`, or fix the 4.14 MADERA
   control path). Do not attempt unmute from the UI in the meantime.
4. **USB-C HDMI (BLOCKED_KERNEL):** `CONFIG_DRM` is not set; enabling
   `DRM_EXYNOS` + the displayport bridge/connector plus a Type-C DP Alt Mode
   stack is a separate, scoped kernel/defconfig task. Until then Mirror/Desktop
   are honestly unavailable.

## 11. Definition-of-done status

- Settings and Quick Settings now read the same authoritative provider state for
  Bluetooth and Location, and the new Audio/Displays pages report real hardware.
- Supported controls operate real services (Bluetooth power, ALSA volume);
  unsupported controls (unmute, Mirror/Desktop) report real blockers.
- Tests pass; the known-good phone (Wi-Fi, browser, shell, lockscreen, charging,
  serial Live Console) remains reachable and recoverable.
- No physical-hardware success was claimed without an on-device observation.
---

## 12. v0.7.0 correction — the Bluetooth blocker is the kernel transport, not only the HCD

The v0.7.0 release re-tested Bluetooth with the owner-supplied, checksum-verified
vendor HCD (`bcm4375B1_semco.hcd`, SHA-256
`35fd013f4fd3e3c28145aa37e40c04c9c250a222c324b146e9fb861b8f53993e`) installed
into the userspace firmware search path. The radio still cannot register `hci0`
because the running 4.14.253 kernel was built with `CONFIG_BT_HCIUART` **not
set**:

- `CONFIG_BT_BCM43XX=y` binds `bcm43xx_bluetooth`, which is only the power and
  rfkill driver (it has no HCI transport or firmware download path).
- `/sys/class/bluetooth/` stays empty, `bluetoothctl list` reports
  `No default controller available`, and there is no `ttyHS*` HCI UART node.
- `firmware_class.path=/vendor/firmware`; the HCD can be present, but a blob
  alone cannot create a transport.

The provider now returns `blocker: "BLOCKED_KERNEL"` and names
`CONFIG_BT_HCIUART` in `detail`/`kernel_hci_transport`. Scanning therefore
cannot return devices until a scoped kernel rebuild enables the HCI UART
transport. The earlier `BLOCKED_FIRMWARE` conclusion is superseded by this
more precise, measured root cause.

