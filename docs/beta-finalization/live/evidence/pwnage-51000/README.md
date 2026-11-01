# PWNAGE-51000 evidence

All files were captured from the physical SM-G975F (`beyond2lte`) or the pinned
build tree on 2026-11-01. Hashes for large/removed artifacts are recorded here.

## Decisive artifacts

- `baseline/` — TWRP/live state, final kernel config and services.
- `kernel/Image-userns` — final kernel Image (SHA 513eedaa…).
- `kernel/boot14.userns.img` / `.padded.img` — packed boot image (9c339535… / 574c239c…).
- `kernel/initramfs.userns.cpio` — embedded initramfs (d10bdb4a…).
- `kernel/running.config`, `kernel/userns.config`, `kernel/userns.image.config` —
  live/known-good/candidate configs.
- `kernel/vendor-src/` — the exact 4.14 userns/nsproxy source gates.
- `twrp/sda14.current.img` — verified pre-flash known-good rollback (97f78f5d…).
- `dmabuf/coredumps/` — Phoc and Wayland-EGL probe SIGSEGV cores.
- `dmabuf/journal/system.journal` — crash-window journal (excerpt also below).
- `flatpak/live-runtime-tests.txt` — userns/bwrap EPERM proof.
- `mtp-macos/` — `mtp-detect`, `mtp-files`, transfer logs and copied file.
- `drivers/capability-diagnostics.txt` — fresh modem/camera/NFC/sensor diagnostics.
- `boot-performance/final-boot.txt`, `shutdown/previous-boot-stop-trace.txt`.
- `deployment/deployed-hashes.txt`.

## Large duplicates removed after hashing

- `twrp/boot14.orig.img` — SHA `7f3f4454dd296f56dc7902e3b21ad35e0c0559cc0f455d30b520056a89bac1f4`;
  same kernel payload as `twrp/sda14.current.img`, only partition-tail bytes differ.
- `kernel/boot14.new.img` — SHA `63e46d43939831e59f74fc56365dccaabcc81f4ee900118bafe130097bfe8192`;
  the rejected p50000 image (`CONFIG_INITRAMFS_SOURCE=""`, release `4.14.253`).
- `dmabuf/journal/system-old.journal` — superseded by `system.journal` and the
  crash excerpts in `PWNAGE-51000-DMABUF-CRASH.md`.

No private keys, credentials, TOTP seeds or auth tokens are included.
