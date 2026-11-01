## PWNAGE-53000 — current live status (2026-11-01)

Kernel flashed to BOOT from TWRP: `4.14.253-gf7194c1d15ed-dirty #5`,
image SHA-256 `2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc`.
Device rebooted cleanly; SSH returned in ~32 s; 10/10 Nuxel services active.

Completed this run:

1. **LPM touch bind** — `0006-sec-ts-lpm-bind.patch` is in the flashed kernel.
2. **CONFIG_NFC** — `CONFIG_NFC`, `NFC_NCI`, `NFC_DIGITAL`, `SAMSUNG_NFC`,
   `SEC_NFC` enabled. A duplicate `/sys/class/nfc` panic was fixed by
   `0007-sec-nfc-class-name.patch`. Controller `/dev/sec-nfc` and I2C 0x27 are
   bound; firmware copied to `/lib/firmware/nfc/` and `/vendor/firmware/nfc/`.
3. **Microphone** — real PipeWire source `alsa_input.hw_0_13` (WDMA1, 48 kHz)
   plus the vendor UAIF0→NSRC0→SIFM0/WDMA1 route. Recorded 475,136 frames,
   peak 779, RMS 116.89; privacy provider `LIVE` / `MUTED` round-trip works.
4. **Flatpak** — user namespaces enabled (`0008`), statx `MNT_ID` backported
   (`0009`), bwrap fd-bind shim installed. `flatpak run` reaches a real
   Freedesktop SDK 25.08 sandbox; Firefox 159.0 reports its version.
5. **Clean rootfs build** — Fedora 43 aarch64 image built with podman and
   offline-verified: `nuxel-beyond2lte-rootfs-fedora-phone-a52-final2.img`,
   SHA-256 `e8d2604a19553832aa975895ae4e1f0cab088d728260d9ba8239147d5c984f2a`.
   Not flashed.

Verification:

- `pytest -q tests/pwnage49000 tests/pwnage52000`: **55 passed**
- `verify-a25-boot.py`: **PASS**
- Touch registered; audio route `dsp1=2/2 route=verified`; mic route applied.

## Honest remaining blockers

1. **Charger-attached cold boot** — code and BOOT image deployed; physical
   power-off/charger/power-on test still needs the owner.
2. **NFC tag read** — kernel/controller/firmware are up, but no userspace NCI
   reader for `/dev/sec-nfc` exists. Verdict `BLOCKED_EXTERNAL_RESOURCE`.
3. **Fingerprint unlock** — qbt2000 nodes exist; no verified TEE/trustlet
   provider in this rootfs.
4. **WebKitGTK acceleration** — Phoc is kbase-accelerated; WebKit remains
   software (`PARTIAL`).
5. **Clean rootfs image** — built and offline-verified, not flashed.

Rollback BOOT image (TWRP):

```sh
adb push docs/beta-finalization/live/evidence/pwnage-51000/kernel/boot14.userns.padded.img /tmp/rollback.img
adb shell 'dd if=/tmp/rollback.img of=/dev/block/by-name/boot bs=1M; sync'
adb shell 'sha256sum /dev/block/sda14'   # 574c239c...
adb reboot
```

Full report: `docs/beta-finalization/live/PWNAGE-53000-REPORT.md`
