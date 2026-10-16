# 12 — REMAINING HARDWARE BLOCKERS (honest list)

Each entry states the symptom, the exact evidence, and what would be needed — no
optimistic language.

## 1. Audio output is not verified (userspace path incomplete)

* **Measured**: kernel cards exist (`0 beyond-madera`, `1 abox_vdma`, `2 abox_dump`) and
  alsa-lib is installed, but the image has **no** `alsa-utils`, **no** `pipewire`/
  `wireplumber`, and **no** player; the only writable playback control alsa-lib reports is
  `Left AMP PCM Gain` (0..20) on card0.
* **Consequence**: volume *control* is real and verified; **sound is not**.  The Samsung
  madera/abox routing normally performed by Android userspace (UCM profiles, DSP
  routing, speaker amp enable) is absent.
* **What is needed**: an ALSA UCM/`amixer` style initialisation for `beyond-madera`
  (the repo already carries `configs/s10plus/alsa-ucm`, unproven on hardware), plus a
  minimal player for a quiet test.  Until then: **audio = unsupported**.

## 2. Camera, modem, Wi-Fi/Bluetooth: unchanged by this cycle

No camera capture path, no modem stack and no verified WLAN were exercised.  The launcher
reports these abilities truthfully as unavailable; nothing was faked.

## 3. No DRM/KMS, so Wayland runs headless + a bridge

`CONFIG_DRM is not set` on this vendor kernel.  The phone therefore composites in phoc’s
*headless* backend and presents through `nuxel-wl-fb` (screencopy → `/dev/fb0`).  This
works (24 fps, 40 ms/frame at 1440x3040) but it is a two-stage path; enabling DRM is a
driver-porting project, not a config flag, and was deliberately not attempted here.

## 4. Boot mode decides whether input exists at all

A bootloader LPM/charger-mode boot (`androidboot.mode=charger`) disables `sec_ts`
(and the fingerprint/Wacom drivers) before userspace runs.  There is **no** userspace
workaround: `CONFIG_KEXEC` is off and nothing is a loadable module.  The runtime check is
`tr ' ' '\n' < /proc/cmdline | grep androidboot.mode`; if it prints a line, input is
disabled for that boot and the fix is a normal reboot, not a patch.

## 5. `sec_ts` IRQ arming (not needed in a normal boot, kept as fallback)

`nuxel-touch-arm.service` (stop→start through `/sys/class/sec/tsp/`) is active and
harmless now; in LPM boots it fails with exit 2 because the driver never bound.  If a
future boot shows `sec_touchscreen` registered but no IRQ, the driver's documented
"internal POWER_ON → no IRQ enable" path is the thing to look at — not regulators.

## 6. Power-button long press has no menu

Long press is mapped to `power-menu`, which is **logged and refused** because no power
menu exists in the launcher yet.  Refusing loudly was chosen over guessing a shutdown.

## 7. Service-worker/offline caching is deliberately reduced on the phone

The handset host now removes the launcher's service-worker registrations and HTTP caches
at startup (stale-frontend prevention).  Offline operation of the launcher is therefore
not a feature of the phone build (the VM/desktop keeps it) — the launcher's server is
local, so nothing is lost, but this is a deliberate trade-off and is recorded as such.

## 8. Kernel-side note for a future cycle

`sec_ts`'s LPM gate and the `sec_bat_is_lpm_check` `__setup` handler already behave
correctly; the only durable way to make a charger-mode boot usable for input would be a
source-level change to the kernel (honouring a Nuxel parameter), which would require a
new BOOT image and a flash — explicitly out of scope for live userspace work.
