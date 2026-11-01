# PWNAGE-53000 — LPM kernel flash, CONFIG_NFC, microphone, Flatpak, clean rootfs

**Date:** 2026-11-01
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820
**Transports:** TWRP ADB `R58M75KDB2X` for BOOT writes; Wi-Fi SSH `root@192.168.178.167` for live validation.
**Kernel after work:** `4.14.253-gf7194c1d15ed-dirty #5` (built 2026-11-01 13:38:15 CET)
**Live BOOT partition hash:** `2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc`

## What was asked

1. Flash the last required fix from `flash.md` (charger/LPM touch bind).
2. Enable `CONFIG_NFC`.
3. Continue fixing remaining blockers after the reboot.
4. Run the clean rootfs build now that host space exists.
5. Fix the microphone.

All five were worked. Items 1, 2, 4 and 5 are completed; Flatpak moved from
BLOCKED to WORKING. Fingerprint and WebKit hardware acceleration remain blocked
for reasons documented below.

## 1. BOOT flash (LPM touch bind)

The prepared exact-source patch `kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch`
was applied to the pinned tree and built into the running kernel. No other
partition was written.

| Item | Value |
|---|---|
| TWRP device | `R58M75KDB2X`, `product:omni_beyond2lte`, `model:Galaxy_S10_` |
| Target | `/dev/block/by-name/boot` -> `/dev/block/sda14`, 57,671,680 bytes |
| Pre-flash hash | `2ca57776d6e7f5cac478fe9fa2bfff71485f792594f6c50262556b86ac3af063` (intermediate) |
| Final image | `build/out/s10plus/nuxel-beyond2lte-boot-a52d-padded.img` |
| Final image SHA-256 | `2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc` |
| Readback SHA-256 | identical |
| Rollback image | `docs/beta-finalization/live/evidence/pwnage-51000/kernel/boot14.userns.padded.img` |
| Rollback SHA-256 | `574c239c910152fcf8321a132df9c567c8ce63da787fb2f7f0a8300a10b2fa59` |

The final kernel booted on the first attempt and SSH returned in ~32 s. The
`sec_ts` initcall now logs `LPM power-up (lpcharge=1): binding touchscreen`
instead of returning `-ENODEV`. The physical charger-attached cold-boot test is
still an owner action (the phone cannot press its own power button); the code
path and BOOT image are deployed.

## 2. CONFIG_NFC

`CONFIG_NFC=y` alone was not sufficient. The first build with NFC enabled
panicked in `sysfs_warn_dup()` because the Samsung `sec_nfc` driver and the
generic NFC core both created `/sys/class/nfc`. Patch
`0007-sec-nfc-class-name.patch` renames the vendor support class to
`sec_nfc`. The final kernel has:

```
CONFIG_NFC=y
CONFIG_NFC_DIGITAL=y
CONFIG_NFC_NCI=y
CONFIG_SAMSUNG_NFC=y
CONFIG_SEC_NFC=y
CONFIG_SEC_NFC_LOGGER=y
```

Live result:

- `/dev/sec-nfc` exists (`crw------- root root 10:107`).
- `/sys/class/nfc` exists and no longer collides.
- `/sys/class/sec_nfc/nfc_support` exists.
- Controller at `/sys/bus/i2c/devices/7-0027` is bound.
- `dmesg`: `nfc: nfc_init: NFC Core ver 0.1`, `[sec_nfc] probe() success`.
- Firmware `sec_s3nrn82_firmware.bin` was copied from the vendor partition to
  `/lib/firmware/nfc/` and `/vendor/firmware/nfc/`
  (SHA-256 `d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb`,
  matching `firmware/s10plus/manifest.yml`).

Bridge verdict moved from `BLOCKED_KERNEL` to **`BLOCKED_EXTERNAL_RESOURCE`**:
the kernel/controller/firmware are present, but Nuxel has no userspace NCI
reader that speaks the Samsung `/dev/sec-nfc` transport. A physical tag read is
not claimed. Payment/secure-element is explicitly not implemented.

## 3. Microphone — fixed and measured

Root cause: the image had no PipeWire capture source, and the vendor capture
route had never been applied. The source is now a real WDMA1 capture PCM, not a
monitor loopback.

Added:

- `configs/s10plus/pipewire/51-nuxel-s10-mic.conf` — static
  `api.alsa.pcm.source` on `hw:0,13` (WDMA1), 48 kHz S16LE stereo.
- `services/nuxel-s10/bin/nuxel-mic-route.sh` — vendor-derived route from
  `mixer_paths.xml`:
  `UAIF0 -> NSRC0 -> SIFM0/WDMA1`, plus `dev-main-mic`
  (`LHPF1<-IN3L`, `ASRC1IN1L<-LHPF1`, `ISRC1INT1<-ASRC1IN1L`,
  `AIF1TX1/2<-ISRC1INT1`, `DMIC1=on`). Idempotent and read-back verified.
- `services/nuxel-s10/systemd/nuxel-mic-route.service` — enabled at boot,
  after the audio session.

Live evidence:

```
$ pactl list short sources
31  alsa_output.hw_0_1.monitor  PipeWire  s16le 2ch 48000Hz  SUSPENDED
32  alsa_input.hw_0_13           PipeWire  s16le 2ch 48000Hz  SUSPENDED

$ parecord --device=alsa_input.hw_0_13 ... /tmp/nuxel-mic-test.wav
channels 2 rate 48000 frames 475136
peak 779 rms 116.89 nonzero 942838 of 950272
```

Bridge privacy provider:

```
state=LIVE, supported=true, source_count=1,
monitor_sources_excluded=1, hardware_capture_present=true
```

Mute round-trip: `microphone-set {muted:true}` -> `MUTED`;
`{muted:false}` -> `LIVE`; `pactl get-source-mute` reads `no` after unmute.
The microphone privacy tile is now a real, enforceable control.

## 4. Flatpak / user namespaces — fixed

Three independent blockers were removed:

1. **User namespace gate.** `0008-nuxel-userns-flatpak.patch` removes the
   Samsung `current_chrooted()` and `LOD_SEC` uid gates that returned EPERM on
   the Nuxel switch_root layout. Standard kuid/kgid mapping checks remain.
2. **statx mount id.** `0009-nuxel-statx-mnt-id.patch` backports
   `STATX_MNT_ID` / `STATX_MNT_ID_UNIQUE` to the 4.14 `statx` result. Flatpak
   1.16 previously aborted with `statx didn't return all required fields: No
   data available`.
3. **bubblewrap fd binds.** bwrap 0.12's `--ro-bind-fd` path resolution fails
   on this 4.14 kernel. `tools/s10plus/nuxel-bwrap-compat.py` is installed as
   `/usr/bin/bwrap`, keeps the real binary at `/usr/libexec/bwrap.real`, and
   rewrites `--ro-bind-fd` / `--bind-fd` to the fd's resolved path. The shim is
   staged by the rootfs builder.

Live evidence:

```
root_unshare_Ur=0
nuxel_unshare_Ur=0
nuxel_bwrap=0
root_bwrap=0
flatpak run --command=/bin/sh org.mozilla.firefox -c 'echo ...'
  nuxel-bwrap-compat: rewrote 29 fd-bind options
  FLATPAK_SANDBOX_OK
  NAME="Freedesktop SDK" VERSION="25.08 (Flatpak runtime)"
flatpak run org.mozilla.firefox --version
  Mozilla Firefox 159.0
```

Firefox's own nested content sandbox still logs a harmless
`CanCreateUserNamespace() clone() failure: EPERM`; the Flatpak sandbox itself
works. VLC refuses to run as root by design; Signal needs a session bus.

## 5. Clean rootfs build

The host was cleaned of caches and the kernel build tree, then the Fedora 43
aarch64 image was built from RPMs with podman on Apple Silicon:

- Builder: `images/s10plus/build-phone-rootfs-fedora.sh`
- Output: `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-a52-final2.img`
- SHA-256: `e8d2604a19553832aa975895ae4e1f0cab088d728260d9ba8239147d5c984f2a`
- Logical size: 4096 MiB (1.8 GiB physical/sparse)
- Verification: `verify-fedora-phone-rootfs.py` PASS (RPM-installed ARM64
  binaries, systemd, Nuxel overlays, source parity)
- Offline `debugfs` check: `51-nuxel-s10-mic.conf`,
  `nuxel-mic-route.service`, `nuxel-mic-route.sh`, `/usr/bin/bwrap` shim and
  `/usr/libexec/bwrap.real` are present.
- The builder now includes the microphone source/route/unit and the bwrap shim.
  This final2 image also includes the microphone service wait/retry fix
  (`--wait 180`, `Restart=on-failure`) so it applies after the asynchronous
  ABOX/audio-route boot sequence.
- NFC firmware is a proprietary vendor blob and is not embedded in the clean
  image; install it from the vendor partition with
  `firmware/s10plus/install-firmware.sh` (live copy already installed).

**The clean image has not been flashed.** Flashing it would replace the live
19.3 GiB userdata tree and is a separate owner decision. The live system was
validated in place.

## Tests

- `pytest -q tests/pwnage52000`: **39 passed**.
- `pytest -q tests/pwnage49000 tests/pwnage52000`: **55 passed**.
- `pytest -q tests/pwnage49000 tests/pwnage52000 tests/pwnage53000`:
  **60 passed** (new suite covers mic source/route, builder staging, bwrap shim,
  and the four required kernel patches).
- Kernel BOOT verifier: `verify-a25-boot.py` **PASS** (raw arm64 Image,
  header v1, merged DTB, embedded initramfs member-by-member, partition fit).
- Live: 10/10 Nuxel services active; `sec_touchscreen` registered; audio route
  `dsp1=2/2 route=verified`; mic route applied; `NAV_DOCK` actions observed.

## Remaining blockers (honest)

1. **Charger-attached cold boot** — code + BOOT image deployed, physical
   power-off/charger/power-on acceptance still requires the owner.
2. **NFC tag read** — kernel/controller/firmware are up; no userspace NCI
   reader for `/dev/sec-nfc` is installed. Verdict `BLOCKED_EXTERNAL_RESOURCE`.
3. **Fingerprint unlock** — qbt2000 device nodes exist, but there is no
   verified TEE/trustlet provider in this rootfs. Not claimed.
4. **WebKitGTK acceleration** — Phoc is kbase-accelerated; WebKitGTK remains
   software (`PARTIAL`). No linux-dmabuf path.
5. **Clean rootfs image not flashed** — built and offline-verified only.

## Artifacts

| Artifact | SHA-256 |
|---|---|
| `build/out/s10plus/nuxel-beyond2lte-boot-pwnage53000.img` (identical to `...-a52d-padded.img`) | `2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc` |
| `build/out/s10plus/a52-kernel/artifacts/Image-a52f` | `7e066fc6809ecab3fc74d57adbbce2b5bebeb66a1d394d8e4e51fd05f34efb7a` |
| `build/out/s10plus/a52-kernel/initramfs.cpio` | `c1d2f06455b3b94ffb2dabde0931d8b54f98c636e78c17554e0d6df0e078713b` |
| `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-a52-final2.img` | `e8d2604a19553832aa975895ae4e1f0cab088d728260d9ba8239147d5c984f2a` |
| rollback `boot14.userns.padded.img` | `574c239c910152fcf8321a132df9c567c8ce63da787fb2f7f0a8300a10b2fa59` |

Kernel patches added this run:

- `0007-sec-nfc-class-name.patch` (+ `.required`)
- `0008-nuxel-userns-flatpak.patch` (+ `.required`)
- `0009-nuxel-statx-mnt-id.patch` (+ `.required`)

## Rollback

From TWRP:

```sh
adb push docs/beta-finalization/live/evidence/pwnage-51000/kernel/boot14.userns.padded.img /tmp/rollback.img
adb shell 'dd if=/tmp/rollback.img of=/dev/block/by-name/boot bs=1M; sync'
adb shell 'sha256sum /dev/block/sda14'   # 574c239c...
adb reboot
```
