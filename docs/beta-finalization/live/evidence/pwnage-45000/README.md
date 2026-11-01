# PWNAGE-45000 evidence index

- `baseline/live-baseline.txt` — read-only inventory (kernel config, UDC/configfs,
  desktop entries, packages, registry, NFC/LED/fingerprint, session).
- `baseline/mtp-probe.txt` — first MTP/FunctionFS/configfs probe.
- `live/providers.txt` — final live provider status and inventory.
- `live/native-launch-evidence.txt` — Firefox/Software visible; VLC/Signal truth.
- `live/software-evidence.txt` — PackageKit/pkcon + Flatpak gate.
- `live/security-evidence.txt` — PIN/lock/unlock cycle.
- `live/led-framebuffer-evidence.txt` — direct `/dev/fb0` color samples.
- `live/mtp-composition-evidence.txt` — acm+mtp composition and safe restore.
- `live/deployed-sha256.txt` — hashes of deployed artifacts.
- `live/journal-tail.txt` — service journal tail after deployment.
- `live/post-reboot*.txt`, `live/final-state.txt` — final reboot/session checks.
- `live/pwa-url-check.txt` — all registered PWA URLs HTTP 200.
- `tests/pwnage45000-run-all.txt` — 291 PASS / 0 FAIL.
- `screenshots/home-after-p45000.png` — compositor capture after deployment.

No credentials, private keys, biometric data or notification secrets are stored
here. The PIN used in the live security test does not appear in any evidence file.

## PWNAGE-45001 follow-up

- `screenshots/lockscreen-no-topbar-p45001.png` — live lock overlay, no top bar.
- `screenshots/post-reboot-lockscreen-no-topbar.png` — same check after reboot.
- `live/topbar-lockscreen-followup.txt` — build hash, deploy hashes, SHOWN/HIDDEN transitions.
- `live/post-reboot-topbar-followup.txt` — post-reboot units, hashes and served cache version.
- `live/podman-build-p45001.log` — full ARM64 Fedora 43 rootfs build log.
- `tests/pwnage45001-run-all.txt` — 300 PASS / 0 FAIL.
