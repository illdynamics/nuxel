# A51 — Preflight summary

Captured before modifying services (2026-10-22 CEST), over the framed live
console. Full detail in PREFLIGHT-AND-ROOT-CAUSE.md.

- **Repo**: branch `nuxel/A50-operation-smooth-penguin`, HEAD `432c6c2`
  (A50 perf work preserved; A50 changes not overwritten).
- **Device**: SM-G975F beyond2lte, Fedora 43 aarch64, kernel 4.14.253,
  7.2 GiB RAM, rootfs 56% used. Boot mode normal.
- **Console**: `/dev/cu.usbmodem201` (VID 0x18d1 PID 0x4ee7,
  `NUXEL-S10PLUS-0001`, 115200 8N1), root shell, `REACHABLE`.
- **Wi-Fi**: `wlan0`/`wlan1` both type-2 and disconnected; scans work; two
  saved profiles exist with `autoconnect=false`.
- **Backup**: off-device hashes recorded; on-device `.a51-rollback` copies
  captured before first write.
- **Recovery**: USB console remains independent of Wi-Fi; no flashing.
