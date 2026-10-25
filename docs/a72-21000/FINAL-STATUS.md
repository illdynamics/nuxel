# NUXEL A72 / 21000 — FINAL STATUS (honest, live-verified)

**Date:** 2026-10-25 (session ~16:00–17:45 CEST)
**Agent:** one writer, macOS host `infranux` (Darwin 24.6.0 arm64)
**Transport:** USB CDC-ACM Live Console `/dev/cu.usbmodem101` (18d1:4ee7, NUXEL-S10PLUS-0001)
**Target:** Samsung Galaxy S10+ SM-G975F (beyond2lte), Linux `4.14.253 #15 aarch64`, Fedora 43
**Repo HEAD:** `fe3ccd0` (working-tree A70/A71 WIP preserved, not reset)

## What was actually completed this run
1. **Lockscreen icon equal-size fix** (owner-reported "charging bigger than the
   other two") — root-caused, fixed, deployed, and physically verified. See
   `13-ICON-SIZE-FIX.md`.
2. **dnf5 package manager recovered** — the previous 13-package plan was audited
   and corrected to a 10-package additive bootstrap (3 wrong packages dropped:
   `coreutils-single` conflicts with installed `coreutils`,
   `systemd-standalone-sysusers` redundant with installed `systemd-sysusers`,
   `glibc-minimal-langpack` redundant with installed `glibc-langpack-en`).
   All 10 GPG-verified, installed, `dnf5 --version` = 5.2.18.0, `repolist`/`list`
   resolve against Fedora 43 aarch64. T37/T38 PASS.
3. **Signed dependency packages installed** (gpgcheck=1, small reviewable
   transactions): alsa-utils+alsa-ucm (3), bluez (1), pipewire+wireplumber+alsa+
   pulseaudio (15), mpv (105), vlc+Qt6 (30). 463→627 RPMs, disk 848M free.
   Provenance in `package-install-manifest.csv`.
4. **Speaker audio root cause PROVEN with real tools** (not inherited):
   `aplay -D hw:0,0` fails `Unable to install hw params` on a valid WAV; dmesg
   shows `calliope_sram.bin ... error -2` on every ABox resume. See 06-AUDIO.
5. **mpv runtime verified**: decodes 44100 Hz S16 WAV (`--ao=null`, clean EOF).
   VLC installed but refuses to run as root (documented limitation).

## 13 objectives — current truth
| id | objective | status |
|---|---|---|
| A69-01 | lockscreen battery | PASS_DEVICE_RUNTIME (cold-boot visual pending owner reboot) |
| A69-02 | single nav bar | PASS_DEVICE_RUNTIME |
| A69-03 | speaker audio | BLOCKED_FIRMWARE (calliope_sram + cs47l93/cs35l40 DSP; aplay hw-params fail proven) |
| A69-04 | 7-mode rotation | BLOCKED_FIRMWARE (SSP down, raw 0,0,0) |
| A69-05 | GPS + Maps | GNSS BLOCKED_FIRMWARE; Maps PASS_DEVICE_RUNTIME |
| A69-06 | NFC | BLOCKED_FIRMWARE/DRIVER (sec-nfc registered, no bound device) |
| A69-07 | BT + A2DP | BLOCKED_FIRMWARE/DRIVER (BlueZ now installed; no hci0, bcm43xx probe w/o HCI) |
| A69-08 | USB-C DAC/headset | BLOCKED_EQUIPMENT (no accessory; recovery USB occupied) |
| A69-09 | VLC + music | mpv PASS_DEVICE_RUNTIME (decode); VLC installed (root limitation); audible BLOCKED_FIRMWARE |
| A69-10 | volume latency | PASS_DEVICE_RUNTIME (visual OSD); audible BLOCKED_FIRMWARE |
| A69-11 | performance | PASS_OFFLINE_ONLY (baseline captured) |
| A69-12 | animations | PASS_OFFLINE_ONLY |
| A69-13 | app foregrounding | PASS_DEVICE_RUNTIME |

## Lockscreen icon equal-size fix (this run, verified)
- Before: `active=charging:70,184,68x68|usb:146,184,68x68|live:222,184,68x68`
- After:  `active=charging:52,191,68x68|usb:128,187,91x76|live:227,184,82x82`
- The three painted penguins now share the same ~59px height. PNG pixel art,
  row `top:184px`, glow and independent animations untouched.
- Evidence: `evidence/icon-size-fix/{before-unequal,after-equal}-size-360x760.png`.
- Files: `pwa/nuxel-home/css/lockscreen.css`, `index.html` (?v=a72), `sw.js`
  (v42-a72-icon-size), `manifest.json` (cache_version v42), extended layout test.

## Package provenance (signed, verified)
- dnf5 bootstrap: 10 RPMs from dl.fedoraproject.org, sha256 + `rpmkeys -K` OK.
- alsa/bluez/pipewire/mpv/vlc: `dnf5 install`, gpgcheck=1, no `--nodeps/--force/
  --nosignature/--replacefiles`, no broad distro upgrade. Full list + counts in
  `package-install-manifest.csv`; `dnf5 history` receipts recorded on device.

## Regression after all package installs (measured)
- nuxel-wayland / nuxel-wl-fb / nuxel-bridge / nuxel-button-manager: active.
- Wi-Fi: wlan0 state 100 (connected); HTTPS fedoraproject.org → 302 (TLS OK).
- Live Console: `nuxel-console` PIDs unchanged, reachable throughout.
- Single-nav: `NAVOWNER native-dock=present`; launcher session restarted once
  (launcher only — CDC-ACM console lives in `init.scope`, never touched).

## Remaining blockers (exact, not collapsed)
- **Audio speaker/headphone:** missing Samsung ABox `calliope_sram.bin` + Cirrus
  `cs47l93/cs35l40` DSP (proprietary, not in linux-firmware). Owner-supplied,
  license/provenance-verified firmware is the unblock.
- **Bluetooth:** BlueZ present; BCM43xx controller never registers hci0
  (firmware/transport), so pairing/A2DP cannot proceed until an owner-supplied,
  license-verified HCD + a bound transport is available.
- **Rotation/GNSS/NFC:** SSP sensor-hub firmware (BCM47752) + userspace; NFC
  controller bind; no kernel swap authorized/needed in 21000.
- **VLC:** runs only under a non-root wrapper (Nuxel session is root); a small
  setuid wrapper is the honest next step if the owner wants the VLC GUI.

## Rollback
- PWA: `.prev` copies on device + `ROLLBACK.sh` + `a72-backup-latest`.
- Packages: `dnf5 history undo <id>` for each transaction, or
  `rpm -e` reverse-order receipts in `package-install-manifest.csv`.
- No kernel/firmware/boot/partition change; no agent-initiated reboot.

## Next actions (priority)
1. Owner physical interaction: cold-boot battery, Back/Home/Tabs, drawer launch,
   10 wake cycles, 3 cold boots, touch animation (T02–T06, T21, T25–T29, T31–T34).
2. Owner-supplied firmware (Cirrus DSP / BCM43xx HCD / SSP) to unblock audio/BT/
   rotation/GNSS, each with licence/provenance + isolated reversible test.
3. Optional: non-root VLC wrapper to launch the installed Qt GUI.
4. USB-C DAC test only with a second recovery route present (owner accessory).
