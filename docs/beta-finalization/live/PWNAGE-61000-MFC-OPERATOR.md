# PWNAGE-61000 — operator procedure for the first physical MFC test

This procedure is for the owner of the S10+ and must be run from a second
machine over Wi-Fi SSH. It is **not** run at boot, login, package install, a
GStreamer plugin scan or a Settings render.

## Hard preconditions (all must be true)

1. The handset is running the **PWNAGE-61000 patched kernel**, not the old
   `-dirty #5` image. Confirm:
   ```sh
   uname -r
   grep -E 'mfc|MFC' /proc/version || true
   dmesg | grep -i mfc | tail
   ```
   The safety patch replaces `request_firmware()` with
   `request_firmware_direct()`; a missing blob must return `-ENOENT` promptly.
2. `/lib/firmware/mfc_fw.bin` exists and matches:
   ```sh
   sha256sum /lib/firmware/mfc_fw.bin
   # f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f
   stat -c %s /lib/firmware/mfc_fw.bin
   # 685832
   ```
3. The decoder is still the exact allow-listed node:
   ```sh
   /usr/lib/nuxel/nuxel-mfc-diag --inventory
   ```
   Expected: `/dev/video6`, `s5p-mfc-dec0`, driver `s5p-mfc`,
   compatible `samsung,exynos-mfc`, `ip_ver 0x1300`.
4. The GStreamer guard and WirePlumber state are intact:
   ```sh
   /usr/lib/nuxel/nuxel-mfc-diag --status
   # guard.v4l2_plugins_disabled = true
   # wireplumber.video_capture_disabled = true, audio/bluetooth = required
   ```
5. A second SSH session and a recovery-capable console are open. Do not start
   the test if SSH is your only path.

## Step 1 — generate the owner-approved safety receipt

Only after the owner has explicitly approved the first hardware open **in the
active task**, on the handset:

```sh
install -d -m 0755 /etc/nuxel/mfc
/usr/lib/nuxel/nuxel-mfc-safety-receipt.py \
  --out /etc/nuxel/mfc/safety-receipt.json \
  --decoder-node /dev/video6 \
  --firmware /lib/firmware/mfc_fw.bin \
  --owner-approve --approved-by "<owner>" \
  --kernel-patch-applied --firmware-installed \
  --missing-firmware-test PASS
```

The tool refuses without `--owner-approve`, without the exact firmware hash,
and without `--kernel-patch-applied`. It never fabricates a blob.

## Step 2 — inventory and status only (no open)

```sh
/usr/lib/nuxel/nuxel-mfc-diag --inventory --json > /run/nuxel/mfc/inventory.json
/usr/lib/nuxel/nuxel-mfc-diag --status --json > /run/nuxel/mfc/status.json
```

Expected state before the first open: `AVAILABLE_PROBE_ONLY` (or
`BLOCKED_FIRMWARE_MISSING` if the blob is absent). `safe_open_allowed` must be
`false` while any precondition is missing.

## Step 3 — exactly one query/open/close

Run **one** process. Capture dmesg before and after:

```sh
dmesg -T > /tmp/mfc-before.log
/usr/lib/nuxel/nuxel-mfc-diag --device /dev/video6 \
  --allow-hardware-open --receipt /etc/nuxel/mfc/safety-receipt.json \
  --query-only --json 2>&1 | tee /tmp/mfc-query-1.json
rc=$?
dmesg -T > /tmp/mfc-after.log
```

If the command does not return promptly, stop. Do **not** launch a second
opener, do not hammer the node, and do not assume `kill -9` or a shell
`timeout` can release an uninterruptible `D` task. Record the blocker and
keep the guard active.

## Step 4 — bounded repetition

Only if Step 3 returned promptly:

```sh
# 5, then 20, then 100 open/query/close cycles
/usr/lib/nuxel/nuxel-mfc-diag --device /dev/video6 \
  --allow-hardware-open --receipt /etc/nuxel/mfc/safety-receipt.json \
  --query-only --repeat 5 --json
# repeat with --repeat 20 and --repeat 100
```

One active test process at a time.

## Step 5 — first real decode

Use a short, known H.264 Annex-B stream (720p30 first). The helper follows the
vendor ABI: OUTPUT USERPTR, CAPTURE DMA-BUF, no `VIDIOC_DECODER_CMD`, no MMAP.

```sh
/usr/lib/nuxel/nuxel-mfc-decode \
  --device /dev/video6 \
  --input /path/to/720p30.h264 \
  --width 1280 --height 720 \
  --allow-hardware-open --receipt /etc/nuxel/mfc/safety-receipt.json \
  --output /run/nuxel/mfc/720p30.nv12 --max-frames 30
```

Expected: `RESULT decoded_frames=... checksum=...`. If `decoded_frames=0`,
collect `dmesg`, the exact stream hash and the helper log; do not claim MFC
decode.

Validate the raw output against a trusted software decode (frame count,
dimensions, visible content and checksum). Only then update the receipt with
`--decode-verified --decode-evidence <log>`.

## Step 6 — one player path

```sh
/usr/lib/nuxel/nuxel-mfc-play --hardware /path/to/720p30.h264 \
  --width 1280 --height 720 --fps 30
```

This is a two-stage path: the helper decodes to raw NV12, then mpv plays it
with `--demuxer=rawvideo --hwdec=no`. It is **not** zero-copy and not a live
MFC→Wayland pipeline. The wrapper refuses unless the receipt says
`decode_verified: true`.

Software fallback remains:

```sh
/usr/lib/nuxel/nuxel-mfc-play --software /path/to/file
# equivalent to: mpv --hwdec=no --no-config /path/to/file
```

## Step 7 — benchmark and thermal run

Use identical files, identical display path and the same idle settling time.
Run software and hardware three times each. Record CPU, dropped frames,
latency, memory, MFC power/clock if exposed, and SoC temperature. Do not claim
a speedup from one run, and do not claim 4K/HDR from a single short sample.

## Step 8 — rollback

```sh
# narrow rollback: receipt, firmware, userspace, guard
/usr/lib/nuxel/rollback-pwnage61000.sh --rootfs / --receipt --firmware --userspace --restore-guard

# keep the previous known-good kernel/DTB; never flash automatically
```

The guard is restored, not removed. Audio/ABOX firmware and all unrelated
blobs are untouched.
