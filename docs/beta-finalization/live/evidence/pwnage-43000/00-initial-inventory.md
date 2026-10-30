# PWNAGE-43000 — Initial System Inventory (2026-10-30)

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte
**Transport:** Wi-Fi SSH `root@192.168.178.167:22` (`~/.ssh/wicked_wqn_id_rsa`)
**Git:** main @ 211417e (origin/main). Uncommitted work present (PWNAGE-40000 power-menu files, plus untracked 43000 prompt/docs).

## Live system
- Kernel: `Linux ... 4.14.253-gf7194c1d15ed-dirty #8 SMP PREEMPT aarch64` (Samsung vendor kernel, no CONFIG_DRM).
- OS: Fedora Linux 43 (Forty Three), aarch64.
- Hostname: `2001-1c00-4d09-8a00-162b-e49d-dc7c-4128`.
- Default target: `multi-user.target`.
- Memory: 7419 MiB total, ~5005 free, no swap. Load average ~12.9 (elevated; WebKitWebProcess + phoc + nuxel-wl-fb are the top CPU consumers).

## Boot timing (systemd-analyze)
- `3.437s (kernel) + 30.914s (userspace) = 34.351s`.
- `multi-user.target` reached after `16.029s` in userspace.
- Top blame:
  - `nuxel-abox-firmware-reload.service` 25.823s
  - `nuxel-fallback.service` 12.030s
  - `nuxel-wl-fb.service` 5.254s
  - `NetworkManager-wait-online.service` 3.023s
  - `nuxel-boot-sound.service` 2.511s
  - `nuxel-audio-route.service` 2.418s
  - `NetworkManager.service` 2.269s
- Critical chain to `multi-user.target`: NetworkManager path, not the display path. The UI (wl-fb/launcher) stabilises later than multi-user.target.

## Display / UI stack
- Wayland: `phoc` headless + pixman (`WLR_BACKENDS=headless,libinput`), no VT/drm.
- Display bridge: `nuxel-wl-fb` (Wayland screencopy -> `/dev/fb0` AMOLED).
- Launcher: `nuxel-pwa-host` (WebKitGTK) serving `pwa/nuxel-home`.
- Fallback UI: `nuxel-fallback.service` (skipped when launcher owns panel).

## Boot-stage state machine
- `nuxel-animation.service`, `nuxel-preload-cinema` (early pre-lockscreen MP4 overlay),
  MP4 `nuxel-preloading-screen.mp4` (7.6 MB) + `nuxel-boot-animation.mp4` (5.5 MB).
- Boot markers show `ANIMATION_STOPPED` at ~18.6s monotonic on this cold boot.

## Audio stack (ABOX)
- PipeWire/WirePlumber/Pulse are started **inside** `nuxel-session.sh`, i.e. as children of
  `phoc` under `nuxel-wayland.service`. This couples audio to the UI session.
- `nuxel-abox-firmware-reload.service` (WantedBy=nuxel-wayland.service) stops
  `nuxel-wayland.service` to drop the PipeWire ABOX runtime-PM reference, cycles the
  DSP, then restarts the session. This causes the UI to restart multiple times.
- `nuxel-audio-route.service` / `-retry` + `nuxel-audio-route.timer` re-apply the
  RDMA1->UAIF1/SIFS1 route after boot.
- ABOX firmware: Calliope core reached `MUB0` after 2 PM attempts on this boot.

## Power / charging
- Power supplies: `ac`(Mains, offline), `battery`(Discharging), `max77705-charger`,
  `max77705-fuelgauge`, `mfc-charger`, `otg`, `ps`, `usb`, `wireless`.
- `nuxel-charger-mode-recovery.service` (enabled) + `nuxel-power-mode.service` (disabled).

## USB
- UDC present: `10c00000.dwc3`, currently `not attached`.
- ConfigFS gadget `nuxel` bound to `10c00000.dwc3` with function `acm.usb0`
  (serial console only — no MTP/mass-storage function present).

## Storage
- Root on `/dev/sda31` (ext4, 110.9 GiB, rw). No active /home, /var or userdata
  writable block device exported to USB (only `/dev/sda31` is mounted as `/`).
- sda1..sda30 are Android/Samsung partitions (NOT mounted at inventory time).

## Applications
- Flatpak/packages not yet audited (next inventory step).

## Initial TODO state
`docs/beta-finalization/live/PWNAGE-43000-TODO.md` created. Evidence under
`docs/beta-finalization/live/evidence/pwnage-43000/`.
