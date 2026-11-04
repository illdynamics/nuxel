# FULL-PWNAGE-71000 — Land PWNAGE-61000 on the live S10+: patched MFC kernel, firmware, userspace, and first real decode

**Mission type:** finish-off / physical deployment / proof for `full-pwnage-61000.md`.
**Relationship to 61000:** the 61000 foundation, source, kernel build, firmware verification and tests are complete. The patched kernel is **not** on the phone, the firmware is **not** installed, the MFC userspace tools are **not** deployed, and no MFC hardware open or decode has been performed. This mission lands and proves them.
**Repository:** `/x/nuxel` (Git root), branch `main`, baseline HEAD `0bed35d881ba674a21f67d31501e84f1031992b5` (re-verify; do not assume).
**Prompt suite:** `/home/wicked/Desktop/nuxel-pwnage/`.
**Owner request:** the owner explicitly asked for the remaining PWNAGE-61000 work to be finished on the phone and explicitly asked whether TWRP is required. This mission therefore authorises the **minimum** privileged action needed: writing the existing BOOT partition with the patched 61000 boot image, installing the hash-verified `mfc_fw.bin`, deploying the MFC userspace tools, and performing the gated first open/decode after the safety receipt is generated. It does **not** authorise EFS/modem/recovery/other-partition writes, repartitioning, bootloader changes, or a factory reset.

---

## 0. Current verified state (2026-11-03 ~19:45 CET) — re-verify, do not assume

### 0.1 Source / build state (foundation complete)

- Pinned kernel: Linux4 `android_kernel_samsung_exynos9820` @ `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253 downstream).
- Fail-closed patch `kernel/s10plus/patches/0008-mfc-firmware-fail-closed.patch` is already applied idempotently to the pinned build tree; `request_firmware()` is replaced by `request_firmware_direct()`.
- `python3 -m pytest -q tests/pwnage61000` → **36 passed**.
- Kernel build artifacts present:
  - `kernel/s10plus/.build/out/arch/arm64/boot/Image` — **46,168,072 bytes** (raw ARM64 Image).
  - `kernel/s10plus/.build/out/arch/arm64/boot/Image.gz` — 16,377,730 bytes (do **not** flash gzip; S-Boot does not decompress).
- Firmware staged at `firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin`:
  - size **685,832**;
  - SHA-256 `f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f`;
  - first word `ea000077`; `install-firmware.sh --verify-mfc` PASS.
- MFC userspace tools built under `tools/s10plus/a61/`: `nuxel-mfc-diag`, `nuxel-mfc-decode`, `nuxel-mfc-play`, `nuxel-mfc-safety-receipt.py`, `nuxel-mfc-image-verify.sh`, `mfc-status.schema.json`.
- Rollback script: `tools/s10plus/a61/rollback-pwnage61000.sh` (narrow: receipt, firmware, userspace, guard; never flashes).

### 0.2 Live phone state (strict Wi-Fi SSH, read-only)

- Target: `root@10.20.30.16`, key `~/.ssh/wicked_wqn_id_rsa`, SM-G975F `beyond2lte`.
- Kernel: **old** `4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT` — the pre-patch image.
- Boot ID: `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4`.
- `/lib/firmware/mfc_fw.bin` — **ABSENT**.
- `/dev/video6` exists, mode `0600 root:root`, **never opened** by this mission yet.
- No MFC module loaded; MFC is built into the kernel path (verify the final config).
- MFC userspace tools are **not installed** under `/usr/lib/nuxel/`.
- `/usr/lib/nuxel/nuxel-gstreamer-guard.sh` is installed; guard is active.
- BOOT partition: `/dev/sda14` (in Fedora; `/dev/block/by-name/boot` in TWRP), **57,671,680 bytes**, `/sys/class/block/sda14/ro = 0` (writable from the live root shell).
- Current live boot header:
  - magic `ANDROID!`, page 2048, header v1, `os_version 0x18000171` (12.0.0);
  - `kernel_size = 48,723,976`, `kernel_addr = 0x10008000`, raw kernel payload;
  - `ramdisk_size = 2,424,832`, `ramdisk_addr = 0x11000000`, `tags_addr = 0x10000100`;
  - cmdline `buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw`.

### 0.3 TWRP answer (must be stated correctly in the report)

**TWRP does not need to be reflashed.** TWRP/Download Mode is a *boot mode*, not a package to install. The unit already has TWRP and a known Download Mode path. The only privileged step is the BOOT partition write. Three valid paths exist, in order of preference:

1. **TWRP (recommended):** boot the existing TWRP (Vol Up + Bixby + Power), `adb push` the verified boot image, `dd` to `/dev/block/by-name/boot`, `sync`, read the partition back and compare SHA-256, then reboot.
2. **Download Mode + heimdall:** flash only BOOT, then read back and verify.
3. **Live Wi-Fi SSH root shell (`dd if=... of=/dev/sda14`)**: technically possible because `ro=0` and the partition is unmounted. Use only if the owner explicitly accepts the risk and a recovery mode (TWRP/Download Mode) is available. Use `conv=fsync`, verify the readback, and never interrupt the write.

Everything else — firmware installation, userspace MFC tools, diagnostics, first open, decode, benchmarks, reports — is done over **Wi-Fi SSH**.

---

## 1. What is missing (the 71000 checklist)

- [ ] A flashable BOOT image containing the **raw** 61000 `Image`, the proven live initramfs, the correct merged DTB, and the same cmdline.
- [ ] The current BOOT partition backed up and hash-verified on the device and on the host.
- [ ] The patched kernel written to BOOT and booted; `uname -r`/`dmesg` prove the new image.
- [ ] The missing-firmware path proven to return promptly (`request_firmware_direct`), with no 60 s fallback wait.
- [ ] `/lib/firmware/mfc_fw.bin` installed with exact hash/size/header verification.
- [ ] MFC userspace tools installed under `/usr/lib/nuxel/` and `/usr/share/nuxel/`.
- [ ] `nuxel-mfc-diag --inventory` proving `/dev/video6` = `s5p-mfc-dec0`, driver `s5p-mfc`, compatible `samsung,exynos-mfc`, `ip_ver 0x1300`.
- [ ] Owner-approved safety receipt.
- [ ] Exactly one bounded query/open/close, then 5/20/100 repetitions.
- [ ] A real 720p30 H.264 decode with objective frame-count/dimension/checksum proof against a software decode.
- [ ] One player path selecting verified hardware decode; software fallback intact.
- [ ] Matched software-vs-MFC benchmark and a 20–30 minute sustained playback run at the highest claimed everyday mode.
- [ ] Guard transition only if proven; otherwise keep the guard active.
- [ ] Updated `PWNAGE-61000-MFC-REPORT.md`, `PWNAGE-61000-MFC-TODO.md`, `PWNAGE-61000-MFC-OPERATOR.md`, evidence and rollback.

---

## 2. Non-negotiable safety and recovery rules

- **Recovery first.** Before any write: confirm the phone's TWRP or Download Mode recovery path, keep a second SSH session open, charge the phone above 50%, and have the USB data cable available.
- **Back up the exact BOOT bytes** from `/dev/sda14` to the host and to `/root/pwnage71000/`. Record size and SHA-256. Verify the host copy by reading it back and comparing.
- **Write only BOOT.** Never write EFS, modem, recovery, param, persistent, keystorage, carrier, cp_debug, misc, dtbo, or any other partition. Never repartition, relock the bootloader, or touch Knox.
- **Do not install `mfc_fw.bin` before the patched kernel is running.** The old kernel has the unbounded `request_firmware()` path. The intended sequence is: patched kernel first → prove prompt missing-firmware failure → install firmware → then the gated open.
- **Do not open any `/dev/video*` node until** the safety receipt exists and the exact allow-list identity is confirmed. Never scan/probe every video node.
- **Never auto-retry a hung open.** A shell `timeout` or `kill -9` cannot release an uninterruptible `D` task. If the first open does not return promptly, stop, record `dmesg`, keep the guard active, and do not launch a second opener.
- **No false claims.** A successful kernel compile, a probe, or a firmware hash is not decoded pixels. Only real decoded frames and objective comparison count.
- Preserve the owner's dirty tree. Do not revert, reset, clean, stash, commit or push.

---

## 3. Execution order

### Phase A — reconcile and build the flashable BOOT image

1. Read `PWNAGE-61000-MFC-REPORT.md`, `PWNAGE-61000-MFC-TODO.md`, `PWNAGE-61000-MFC-OPERATOR.md`, `full-pwnage-61000.md`, the patch, config fragments, `build-kernel.sh`, `boot/s10plus/pack-boot-v1.sh`, and the MFC tools.
2. Re-run:

```sh
python3 -m pytest -q tests/pwnage61000
```

   Record the exact pass/fail/skip counts and exit code. Do not edit tests to make them pass.

3. Verify the kernel config and patch:

```sh
grep -E 'CONFIG_VIDEO_EXYNOS_MFC|CONFIG_VIDEOBUF2_DMA_SG|CONFIG_EXYNOS_IOMMU|CONFIG_V4L2_MEM2MEM_DEV' \
  kernel/s10plus/.build/out/.config
objdump -d kernel/s10plus/.build/out/drivers/media/platform/exynos/mfc/mfc_buf.o \
  | grep -A3 -B3 request_firmware_direct || true
```

4. Capture the current live BOOT partition read-only:

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16 \
  'dd if=/dev/sda14 bs=1M status=none' > evidence/pwnage-61000/71000/live-boot-before.img
sha256sum evidence/pwnage-61000/71000/live-boot-before.img
```

   Also save a device-side copy under `/root/pwnage71000/` and verify both hashes.

5. Build the new boot image. Requirements:

- kernel: `kernel/s10plus/.build/out/arch/arm64/boot/Image` (**raw**, never `Image.gz`);
- ramdisk: the current proven live initramfs (extract from the captured boot image) or the repository initramfs that exactly matches the live one; verify `/init`, touch and display behavior are preserved;
- DTB: the current hardware-proven merged DTB for this exact board revision (extract from the captured boot image or use the repository's known-good merged DTB); verify the final DTB contains the correct `samsung,exynos-mfc` node, `ip_ver = <0x1300>`, and the real board compatible strings; do not substitute an unrelated DTB;
- cmdline: identical to the current live boot image;
- load addresses: exactly `kernel_addr=0x10008000`, `ramdisk_addr=0x11000000`, `tags_addr=0x10000100`, page 2048, header v1.

Pack with the repository tool (read its `--help`; use `--v1-spec` and the addresses above or `--addresses-from-device`):

```sh
python3 boot/s10plus/pack-boot-v1.sh \
  --kernel kernel/s10plus/.build/out/arch/arm64/boot/Image \
  --ramdisk <proven-initramfs.cpio.gz> \
  --dtb <merged.dtb> \
  --cmdline 'buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw' \
  --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 --tags-addr 0x10000100 \
  --v1-spec --strict --output build/out/s10plus/pwnage71000-boot.img
```

6. Verify the image before it goes near the phone:

- `read-boot-header-v1.py --json` reports the expected magic, sizes, addresses, page size, header v1 and cmdline;
- kernel payload at offset 2048 is byte-identical to the 61000 `Image` (SHA-256 match);
- ramdisk payload matches the chosen initramfs;
- DTB is present and valid (`0xd00dfeed`);
- total file size ≤ **57,671,680** bytes;
- `sha256sum` recorded in a manifest.

If any check fails, stop and fix the packer/inputs. Do not flash an unverified image.

### Phase B — write BOOT and boot the patched kernel

Choose one path, in order of preference.

**B1 — TWRP (recommended; no TWRP reflash needed):**

```sh
# Boot the existing TWRP (Vol Up + Bixby + Power); use the serial shown by `adb devices`.
adb -s R58M75KDB2X push build/out/s10plus/pwnage71000-boot.img /tmp/
adb -s R58M75KDB2X shell 'sha256sum /tmp/pwnage71000-boot.img'
adb -s R58M75KDB2X shell 'dd if=/tmp/pwnage71000-boot.img of=/dev/block/by-name/boot bs=1M conv=fsync; sync'
adb -s R58M75KDB2X shell 'sha256sum /dev/block/by-name/boot'
adb -s R58M75KDB2X reboot
```

The readback SHA-256 must match the image. If it does not, restore the backed-up BOOT image immediately.

**B2 — Download Mode + heimdall:** flash only BOOT; read back and verify; reboot.

**B3 — Live Wi-Fi SSH `dd` (only with explicit owner acceptance of the risk):**

```sh
scp -i ~/.ssh/wicked_wqn_id_rsa build/out/s10plus/pwnage71000-boot.img \
  root@10.20.30.16:/root/pwnage71000/
ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16 \
  'set -e; sha256sum /root/pwnage71000/pwnage71000-boot.img; \
   dd if=/root/pwnage71000/pwnage71000-boot.img of=/dev/sda14 bs=1M conv=fsync; sync; \
   sha256sum /dev/sda14'
```

Then reboot through the bounded policy. Do not issue the write while the battery is low or over a flaky link.

### Phase C — prove the patched kernel and the fail-closed missing-firmware path

After boot, over Wi-Fi SSH:

```sh
uname -a
cat /proc/sys/kernel/random/boot_id
dmesg -T | grep -i -E 'mfc|firmware' | tail -40
test ! -e /lib/firmware/mfc_fw.bin && echo FIRMWARE_ABSENT_EXPECTED
/usr/lib/nuxel/nuxel-mfc-diag --inventory 2>&1 || true
```

- Confirm the kernel is the new 61000 build (not `-dirty #5`).
- Confirm SSH, phoc, `nuxel-wl-fb`, statusbar/navdock and the bridge returned.
- With the firmware still absent, confirm the MFC driver path reports a prompt `-ENOENT`/missing-firmware state and does **not** wait ~60 s for a userspace helper. This is the safety proof that the patch is live.
- Do not open `/dev/video6` yet.

If the phone does not return to SSH and the desktop after a bounded wait, restore the backed-up BOOT image via TWRP/Download Mode. Do not blind-reboot repeatedly.

### Phase D — deploy MFC userspace and install firmware

1. Back up the prior state of `/usr/lib/nuxel`, `/usr/share/nuxel/mfc-status.schema.json`, `/etc/nuxel/mfc`, `/run/nuxel/mfc` and `/lib/firmware/mfc_fw.bin` (absent marker).
2. Install atomically over Wi-Fi SSH:

```sh
install -Dm0755 tools/s10plus/a61/nuxel-mfc-diag            /usr/lib/nuxel/nuxel-mfc-diag
install -Dm0755 tools/s10plus/a61/nuxel-mfc-decode          /usr/lib/nuxel/nuxel-mfc-decode
install -Dm0755 tools/s10plus/a61/nuxel-mfc-play            /usr/lib/nuxel/nuxel-mfc-play
install -Dm0755 tools/s10plus/a61/nuxel-mfc-safety-receipt.py /usr/lib/nuxel/nuxel-mfc-safety-receipt.py
install -Dm0755 tools/s10plus/a61/nuxel-mfc-image-verify.sh /usr/lib/nuxel/nuxel-mfc-image-verify.sh
install -Dm0644 tools/s10plus/a61/mfc-status.schema.json    /usr/share/nuxel/mfc-status.schema.json
install -d -m0755 /etc/nuxel/mfc /run/nuxel/mfc
```

   If a repository deploy script exists for 61000, use it instead and audit it first; otherwise make the minimal install script with backup/rollback.

3. Verify the tools load and the inventory is read-only:

```sh
/usr/lib/nuxel/nuxel-mfc-diag --version
/usr/lib/nuxel/nuxel-mfc-diag --inventory --json > /run/nuxel/mfc/inventory.json
/usr/lib/nuxel/nuxel-mfc-diag --status --json > /run/nuxel/mfc/status.json
```

   Expect `BLOCKED_FIRMWARE_MISSING` while the blob is absent, `safe_open_allowed=false`, and the exact allow-list identity for `/dev/video6`.

4. Install the firmware only now, with exact verification:

```sh
install -Dm0644 firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin /lib/firmware/mfc_fw.bin
sha256sum /lib/firmware/mfc_fw.bin   # f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f
stat -c %s /lib/firmware/mfc_fw.bin  # 685832
od -An -tx4 -N4 /lib/firmware/mfc_fw.bin  # ea000077
```

   Re-run `--inventory` and `--status`; the state should move to probe-only/available according to the tool's gate, but `safe_open_allowed` must still require the receipt.

### Phase E — first open, repetitions, decode proof

1. Generate the safety receipt only with explicit owner approval in the active task:

```sh
/usr/lib/nuxel/nuxel-mfc-safety-receipt.py \
  --out /etc/nuxel/mfc/safety-receipt.json \
  --decoder-node /dev/video6 \
  --firmware /lib/firmware/mfc_fw.bin \
  --owner-approve --approved-by "<owner>" \
  --kernel-patch-applied --firmware-installed \
  --missing-firmware-test PASS
```

2. Capture `dmesg -T > /tmp/mfc-before.log`, then exactly one open/query/close:

```sh
/usr/lib/nuxel/nuxel-mfc-diag --device /dev/video6 \
  --allow-hardware-open --receipt /etc/nuxel/mfc/safety-receipt.json \
  --query-only --json 2>&1 | tee /tmp/mfc-query-1.json
dmesg -T > /tmp/mfc-after.log
```

   If it does not return promptly, **stop**. Do not launch a second opener, do not hammer the node, do not assume `timeout`/`kill -9` releases a `D` task.

3. Only after a prompt first open, repeat 5, then 20, then 100 open/query/close cycles with one process at a time. Record `dmesg` deltas.

4. Decode a short known H.264 Annex-B 720p30 stream with the vendor ABI:

```sh
/usr/lib/nuxel/nuxel-mfc-decode \
  --device /dev/video6 --input <720p30.h264> --width 1280 --height 720 \
  --allow-hardware-open --receipt /etc/nuxel/mfc/safety-receipt.json \
  --output /run/nuxel/mfc/720p30.nv12 --max-frames 30
```

   Validate frame count, dimensions, visible content and checksum against a trusted software decode. Only then update the receipt with `--decode-verified --decode-evidence <log>`.

5. Test one player path:

```sh
/usr/lib/nuxel/nuxel-mfc-play --hardware <720p30.h264> --width 1280 --height 720 --fps 30
/usr/lib/nuxel/nuxel-mfc-play --software <720p30.h264>
```

   The hardware wrapper must refuse unless the receipt says `decode_verified: true`. The software path must remain intact.

### Phase F — benchmark, thermal, guard transition

- Run identical-file software vs MFC three times each; record CPU, dropped frames, latency, memory, MFC power/clock if exposed, and SoC temperature.
- Run 20–30 minutes of sustained playback at the highest mode actually claimed.
- Keep the GStreamer guard and WirePlumber `video-capture=disabled` unless the full proof supports a narrow, reversible relaxation. A single decode is not enough to change the default player policy.
- No zero-copy/DMA-BUF claim unless separately proven; MFC decode and GPU presentation are independent.

---

## 4. Acceptance matrix

| Criterion | Required state |
|---|---|
| Patched kernel built from pinned source | PASS (source/build) |
| Idempotent patch application | PASS |
| `request_firmware_direct()` in the built kernel | PASS (objdump/compile evidence) |
| Boot image verified and ≤ partition size | PASS |
| BOOT partition backup + readback hash | PASS |
| Patched kernel running on the phone | PASS (`uname`/`dmesg`) |
| Prompt missing-firmware failure (no 60 s wait) | PASS |
| Firmware hash/size/header | PASS |
| MFC userspace tools installed | PASS |
| Inventory identity `/dev/video6` | PASS |
| Safety receipt with owner approval | PASS |
| First query/open/close prompt | PASS or BLOCKED |
| 5/20/100 repetitions | PASS or NOT_TESTED |
| Real 720p30 decode + software comparison | PASS or BLOCKED |
| Hardware player path + software fallback | PASS or NOT_TESTED |
| Matched benchmark | PASS or NOT_TESTED |
| 20–30 min sustained playback | PASS or NOT_TESTED |
| Guard transition | only if proven; else unchanged |
| Rollback tested where possible | PASS |
| Report/TODO/operator updated | PASS |

`FULLY_DONE` requires real decoded frames, an objective software comparison, the player path and sustained playback. Otherwise use `IMPLEMENTED_NOT_PHYSICALLY_VERIFIED`, `BLOCKED_<reason>`, or `FAILED`. Do not invent success.

---

## 5. Rollback and recovery

1. **Kernel/DTB:** restore the saved `/root/pwnage71000/live-boot-before.img` or the host copy to BOOT via TWRP/Download Mode; verify SHA-256 readback; reboot. Never touch another partition.
2. **Firmware:** `rm -f /lib/firmware/mfc_fw.bin` (only that blob; never remove ABOX/audio or other firmware).
3. **Userspace:** use `tools/s10plus/a61/rollback-pwnage61000.sh --rootfs / --receipt --firmware --userspace --restore-guard` or the equivalent backed-up restore.
4. **Player policy:** restore software-only playback; keep the GStreamer guard active.
5. **Service/status:** report `BLOCKED`; do not auto-retry the hardware.
6. Keep the previous known-good boot image and all hashes in both the repo evidence tree and `/root/pwnage71000/`.

---

## 6. Deliverables

1. Flashable `pwnage71000-boot.img` + header/size/SHA manifest.
2. Current-BOOT backup and readback verification evidence.
3. Patched-kernel boot evidence (`uname`, `dmesg`, boot ID, service health).
4. Missing-firmware safety proof.
5. Installed MFC userspace inventory + firmware verification.
6. Safety receipt and first-open/dmesg evidence.
7. Real decode logs, output checksum, software comparison.
8. Benchmark CSV/table and thermal/sustained-playback evidence.
9. Updated `PWNAGE-61000-MFC-REPORT.md`, `PWNAGE-61000-MFC-TODO.md`, `PWNAGE-61000-MFC-OPERATOR.md`.
10. Exact rollback commands and tested status.
11. Final response with: files changed, commands/exit codes, pass/fail/skip counts, physical evidence timestamps, remaining blockers, owner actions and honest per-criterion status.

## 7. Final response format

- **A. What was deployed** (boot image hash, firmware hash, userspace files, backup path).
- **B. Kernel proof** (`uname`, `dmesg`, missing-firmware prompt behavior).
- **C. MFC proof** (inventory, one open, repetitions, decoded frame count/checksum, software comparison).
- **D. Player/benchmark** (hardware vs software, sustained/thermal).
- **E. Guard/policy state** (unchanged or narrowly changed, with evidence).
- **F. Rollback** (exact commands and tested status).
- **G. Remaining blockers** (firmware ABI, codecs not proven, DMA-BUF, etc.).
- **H. Honest overall status** (`FULLY_DONE` / `IMPLEMENTED_NOT_PHYSICALLY_VERIFIED` / `BLOCKED_<reason>` / `FAILED`).

Do not treat a successful compile, a sysfs read, or a firmware hash as physical decode proof.
