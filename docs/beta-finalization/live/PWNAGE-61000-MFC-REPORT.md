# PWNAGE-61000 — Exynos 9820 MFC bring-up report

**Status: `IMPLEMENTED_NOT_PHYSICALLY_VERIFIED`**

Mission: safe, genuine Exynos MFC hardware video decoding on the Samsung Galaxy
S10+ SM-G975F (`beyond2lte`, Exynos 9820), without removing the software
fallback or the historical GStreamer/WirePlumber safety guard.

Repository: `/x/nuxel`, branch `main`, HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`.
Pinned kernel: `Linux4/android_kernel_samsung_exynos9820` @
`f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253 downstream).

> This report distinguishes source-level implementation, build verification and
> physical proof. No physical MFC decode was performed. The live handset still
> runs its pre-patch kernel and has no `mfc_fw.bin`. The status is therefore
> **not** `FULLY_DONE`.

---

## 1. What changed

### Kernel

- `kernel/s10plus/patches/0008-mfc-firmware-fail-closed.patch` (+ `.required`)
  - `mfc_load_firmware()` now uses `request_firmware_direct()` instead of
    `request_firmware()`. With `CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y`, the
    old call could wait for the 60 s firmware timeout while `mfc_open()` held
    `dev->mfc_mutex`. The direct loader returns `-ENOENT` immediately.
  - failed requests propagate the real error and log the exact name;
  - `NULL`/empty/short/oversized blobs are rejected and released correctly;
  - `mfc_probe()` rejects a DT `ip_ver` other than the Exynos 9820 `0x1300`
    with `-ENODEV` before firmware allocation or register access;
  - `MFC_SUPPORTED_IP_VER` added to `mfc_common.h`.
- `kernel/s10plus/configs/nuxel-drm-kbase.fragment` — explicit MFC/media/IOMMU
  symbols.
- `kernel/s10plus/configs/live-required.config` — the same symbols are now
  required by `tools/s10plus/verify-kernel-config.py`.
- The patch is marked `.required`, so a patch failure aborts the build.

### Firmware

- `firmware/s10plus/manifest.yml` — the existing `video/mfc_fw.bin` entry now
  records the exact source repository/commit/path, size, driver request name,
  expected IP revision, format, license/provenance and redistribution policy.
  It remains `required: false` so software-only images stay buildable.
- `firmware/s10plus/gen-manifest.py` — regenerates those provenance fields.
- `firmware/s10plus/install-firmware.sh` — new `--verify-mfc` mode checks
  presence, size `685832`, SHA-256
  `f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f`, and the
  ARM32 header word `ea000077`. It fails closed and never fabricates/pads a
  file. `--rootfs-staging` additionally verifies the staged copy.
- `firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin` — the exact blob staged
  locally for image builds (gitignored, not committed).

### Userspace

- `tools/s10plus/a61/nuxel-mfc-diag` — inventory-first diagnostic.
  - default mode is `--inventory`; it reads sysfs only and never opens
    `/dev/video*`;
  - exact decoder identity: `s5p-mfc-dec0`, `s5p-mfc`, `samsung,exynos-mfc`,
    `0x1300`, platform `188d0000.mfc`;
  - `--query-only` requires `--device`, `--allow-hardware-open` and a matching
    owner-approved safety receipt; `--repeat N` supports 5/20/100 open/close;
  - `--decode-test` delegates to the vendor-ABI helper;
  - `--status --json` emits schema `nuxel.mfc.status/1` and never opens a node;
  - logs to `/var/log/nuxel/mfc/`, never logs media contents;
  - `--self-test` runs offline (17 checks).
- `tools/s10plus/a61/nuxel-mfc-decode.c` — experimental vendor-ABI decode
  helper (source + cross-compiled aarch64 binary). It uses OUTPUT USERPTR,
  CAPTURE DMA-BUF via `/dev/udmabuf`, no `VIDIOC_DECODER_CMD`, no
  `V4L2_EVENT_SOURCE_CHANGE`, no MMAP. It is **not executed** on hardware.
- `tools/s10plus/a61/nuxel-mfc-play` — truthful policy:
  - default / `--software`: `mpv --hwdec=no`;
  - `--hardware`: refuses unless `AVAILABLE_HARDWARE_DECODE` from a recorded
    decode proof; otherwise explicit error and software fallback;
  - `--auto`: uses MFC only when that proof exists;
  - `--show-policy` reports the real state.
- `tools/s10plus/a61/nuxel-mfc-safety-receipt.py` — refuses to write a receipt
  without `--owner-approve`, the exact firmware hash and
  `--kernel-patch-applied`.
- `tools/s10plus/a61/mfc-status.schema.json` — versioned status schema.
- `tools/s10plus/a61/nuxel-mfc-image-verify.sh` — software/mfc profile image
  invariants.
- `tools/s10plus/a61/rollback-pwnage61000.sh` — narrow rollback.
- `images/s10plus/build-phone-rootfs-inside-fedora.sh` — installs the
  diagnostic, policy, schema and optional helper; **also installs the guard
  itself**, which a clean image previously did not do.
- `docs/beta-finalization/live/PWNAGE-61000-MFC-OPERATOR.md` — owner-approved
  physical test procedure.

### Safety controls deliberately unchanged

- `tools/s10plus/a29/nuxel-gstreamer-guard.sh` still disables
  `libgstvideo4linux2.so`, `libgstv4l2codecs.so`, `libgstkms.so`,
  `libgstopengl.so` and clears stale registries.
- Both `nuxel-session.sh` paths still invoke the guard.
- WirePlumber still has `hardware.video-capture = disabled`,
  `hardware.audio = required`, `hardware.bluetooth = required`.
- Boot/preload still uses `mpv --hwdec=no`.
- No camera capture, KMS GStreamer plugin or OpenGL GStreamer plugin was
  restored.

---

## 2. Driver / firmware compatibility

| Item | Evidence | Result |
|---|---|---|
| SoC / board | SM-G975F, `beyond2lte`, Exynos 9820 | PASS |
| MFC hardware IP | DT `ip_ver = <0x1300>`; live DT read as `0x1300` | PASS (declared) |
| Driver | `drivers/media/platform/exynos/mfc/`, vendor Samsung driver, `MFC_DRIVER_INFO 180315` | PASS |
| Match string | `samsung,exynos-mfc` | PASS |
| Kernel config | `CONFIG_VIDEO_EXYNOS_MFC=y`, `CONFIG_VIDEOBUF2_DMA_SG=y`, `CONFIG_EXYNOS_IOMMU=y` in live and built config | PASS |
| DT resources | `0x188d0000`, IRQ SPI 0x152, `aclk_mfc`, two SysMMUs, `pd-mfc`, hwfc/mmcache, QoS table | PASS |
| Decoder node | `/dev/video6` = `s5p-mfc-dec0`, platform `188d0000.mfc` | PASS |
| Firmware request | `MFC_FW_NAME = "mfc_fw.bin"` (`mfc_common.h:68`) | PASS |
| Firmware provenance | `Linux4/proprietary_vendor_samsung@05c9ef8f…`, `exynos9820-common/proprietary/vendor/firmware/mfc_fw.bin` | PASS |
| Firmware size/hash | 685832 bytes / `f3802d34…b55f`; matches manifest | PASS |
| Firmware ABI/version | driver checks `mfc_get_mfc_version()` against DT `ip_ver` after `RISC_ON`/`SYS_INIT` | **NOT_TESTED_ON_DEVICE** |
| Runtime DMA/IOMMU | source uses two SysMMUs and DMA-BUF capture; no hardware run | **NOT_TESTED_ON_DEVICE** |
| V4L2 API mode | vendor-specific nonstandard M2M-style | PASS (classified) |
| Missing-firmware promptness | `request_firmware_direct()` patch compiled | PASS (source/build) / **NOT_TESTED_ON_DEVICE** |

### API classification (important)

The driver is **not** a standard stateful or stateless V4L2 decoder:

- it has OUTPUT and CAPTURE multi-planar queues on one node;
- it does **not** use the `v4l2_m2m` framework;
- it has no `VIDIOC_DECODER_CMD`, no `V4L2_EVENT_SOURCE_CHANGE`, no Request API;
- it rejects `V4L2_MEMORY_MMAP`;
- capture buffers are imported as DMA-BUF fds (`dma_buf_get` in `mfc_get_iovmm`);
- QUERYCAP reports separate mplane caps, not `V4L2_CAP_VIDEO_M2M_MPLANE`.

Therefore generic GStreamer `v4l2codecs` (stateless), generic stateful
GStreamer `v4l2*h264dec` and FFmpeg `v4l2_m2m` are not interchangeable with this
device. The first userspace milestone is the purpose-built vendor-ABI helper.

---

## 3. MFC proof

**No MFC frame was decoded. `MFC_DECODE` = `NOT_TESTED_ON_DEVICE`.**

What was proven:

- the decoder node is uniquely identified by sysfs, not by a `/dev/videoN`
  guess (`evidence/pwnage-61000/live-mfc-inventory.json`);
- the live diagnostic reports:
  ```text
  state = BLOCKED_FIRMWARE_MISSING
  reason = mfc_fw.bin is absent; hardware decode stays blocked
  decoder_node = /dev/video6
  decoder_sysfs_name = s5p-mfc-dec0
  platform_device = 188d0000.mfc
  driver = s5p-mfc
  compatible = samsung,exynos-mfc
  ip_ver = 0x1300
  safe_open_allowed = false
  ```
- the guard and WirePlumber safety state are intact on the live handset;
- the exact firmware blob was acquired and verified against the pinned source
  of record.

What was **not** done:

- `/dev/video6` was never opened;
- no `QUERYCAP`, `ENUM_FMT`, `REQBUFS`, `STREAMON` or `DQBUF` on the handset;
- no frame checksum or visual validation;
- no player playback;
- no benchmark or thermal run;
- no 4K test.

Reason: the live kernel is the pre-patch `-dirty #5` image. Opening the
historically wedged node without the `request_firmware_direct()` safety patch
and without explicit approval for the first live open would violate the
mission's safety gate.

Evidence paths:

```text
docs/beta-finalization/live/evidence/pwnage-61000/live-inventory.txt
docs/beta-finalization/live/evidence/pwnage-61000/live-mfc-inventory.json
docs/beta-finalization/live/evidence/pwnage-61000/live-config.txt
docs/beta-finalization/live/evidence/pwnage-61000/mfc-firmware-verify.txt
docs/beta-finalization/live/evidence/pwnage-61000/pytest-pwnage61000.log
docs/beta-finalization/live/evidence/pwnage-61000/live-post-reboot-final.txt
docs/beta-finalization/live/evidence/pwnage-61000/live-mfc-status-post-reboot.json
docs/beta-finalization/live/evidence/pwnage-61000/live-software-fallback.txt
```

---

## 4. Codec / resolution matrix

Nothing has been physically verified. The DT advertises 10-bit, 4:2:2, P010
and HDR10+ metadata, and the driver enumerates H.264/HEVC/VP8/VP9/MPEG4/VC1
stream formats in source. **These are silicon/driver declarations, not Nuxel
capabilities.**

| Mode | Status | Evidence |
|---|---|---|
| H.264 720p30 | NOT_TESTED_ON_DEVICE | no decode run |
| H.264 1080p30 | NOT_TESTED_ON_DEVICE | no decode run |
| H.264 1080p60 | NOT_TESTED_ON_DEVICE | no decode run |
| HEVC Main 1080p30 | NOT_TESTED_ON_DEVICE | no decode run |
| 4K30 / 4K60 | NOT_TESTED_ON_DEVICE | no caps/thermal proof |
| 10-bit / HDR | NOT_TESTED_ON_DEVICE | decode bit depth ≠ HDR display |

No claim of "4K supported", "hardware accelerated", "zero-copy", "smooth 4K"
or "HDR enabled" is made.

---

## 5. Performance / thermal

**NOT_RUN.** No matched software-vs-MFC benchmark was performed because no
MFC decode was proven. Do not infer energy savings from CPU percentage.

Required benchmark inputs when the owner approves the physical test:

- identical H.264 file, same output path and duration;
- 3 software runs and 3 hardware runs;
- CPU, dropped/repeated frames, latency, memory, MFC clock/power (if exposed);
- SoC temperature and throttle state before/during/after;
- 20–30 minutes sustained at the highest claimed everyday mode.

---

## 6. Memory / DMA-BUF status

The claims are kept separate:

| State | Result |
|---|---|
| `MFC_DECODE` | NOT_TESTED_ON_DEVICE |
| `MFC_DMABUF_EXPORT` | NOT_TESTED_ON_DEVICE |
| `MALI_EGL_IMPORT` | NOT_TESTED_ON_DEVICE |
| `PHOC_COMPOSE` | NOT_TESTED_ON_DEVICE |
| `FB_BRIDGE_PRESENT` | NOT_TESTED_ON_DEVICE |
| `ZERO_COPY_END_TO_END` | NOT_TESTED_ON_DEVICE |

The helper's first milestone is a copied path: MFC capture DMA-BUF →
CPU-mapped NV12M planes → checksum/raw output. It does not claim Mali/EGL
import or zero-copy.

---

## 7. Userspace integration status

- Installed mpv/FFmpeg-free has **no `v4l2m2m` hwdec** (`mpv --hwdec=help` lists
  nvdec/vaapi/vulkan/vdpau only). It cannot drive this vendor ABI directly.
- GStreamer `v4l2codecs` is stateless and does not match this stateful-looking
  but vendor-specific driver. The GStreamer guard remains active.
- The implemented path is:
  1. `nuxel-mfc-diag` inventory/status;
  2. `nuxel-mfc-decode` vendor-ABI helper (not run);
  3. `nuxel-mfc-play --hardware` (helper decode → raw NV12 → mpv rawvideo,
     not run).
- Default playback is `nuxel-mfc-play --software` / `mpv --hwdec=no`.
- The boot/preload controller remains `--hwdec=no` and never depends on MFC.

**Player integration = IMPLEMENTED, NOT_TESTED_ON_DEVICE.**

---

## 8. Build and test results

### New PWNAGE-61000 suite

```text
pytest -q tests/pwnage61000  ->  36 passed
```

It covers manifest/provenance, inventory-never-opens, exact node allow-list,
firmware hash/status, receipt/gate refusal, status schema, guard/WirePlumber,
boot/preload safety, kernel patch application (forward or already-applied),
helper ABI/source checks, helper native build + refusal, rollback, image verifier.

### Kernel build

```text
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --jobs 16
BUILD_EXIT=0
[kernel] Done.
[kernel] capability parity:
kernel config: PASS — matches the live S10+ capability set
```

Artifacts:

```text
Image.gz   16M   sha256 cfc80df9b80374ed6e390507a5cec304b131e57aa9a8e6b369aea6ac79d90ed7
.config          sha256 74d61637cf43a94eb0e37ca808042a4ebc88dc635830f6338fa06d9e3a5add2d
exynos9820.dtb   sha256 a6b67b460d25846ac5f5b6222c8458c9cb8f83d1db99d04f4cb115b1834d4e95
```

The final `.config` contains `CONFIG_VIDEO_EXYNOS_MFC=y`,
`CONFIG_VIDEOBUF2_DMA_SG=y`, `CONFIG_EXYNOS_IOMMU=y` and
`CONFIG_V4L2_MEM2MEM_DEV=y`; capability parity is 53/53.

Patch application log (`kernel/s10plus/.build/out/patch-application.log`):

```text
[kernel-patches] APPLY: 0008-mfc-firmware-fail-closed.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0008-mfc-firmware-fail-closed.patch
```

Binary proof that the compiled driver uses the direct loader:

```text
$ aarch64-linux-gnu-objdump -d --disassemble=mfc_load_firmware vmlinux | grep request_firmware
ffffff8008b3c0ec:  97f05a07  bl  ffffff8008752908 <request_firmware_direct>
```

The built `exynos9820.dtb` and the `exynos9820-beyond2lte_eur_open_*.dtbo`
overlays are retained under `kernel/s10plus/.build/out/arch/arm64/boot/dts/`.
No DTB was written to the handset.

### Regression matrix

Per-directory results are in
`evidence/pwnage-61000/regression-summary.txt` and `regression/`.
Notable results:

- PASS: `pwnage30000` 21, `pwnage31000` 49, `pwnage34000` 4, `pwnage38000` 7,
  `pwnage46000` 13, `pwnage50000` 8, `pwnage52000` 39, `pwnage53000` 13,
  `pwnage58000` 10, `pwnage60000` 31, `pwnage61000` 35.
- Pre-existing failures unrelated to MFC: `pwnage33000` (launcher registry),
  `pwnage37000` (two assertions including a29/a45 session identity),
  `pwnage40000` (audio route/session), `pwnage42000` (top-bar contrast),
  `pwnage49000` (radio icons / back-root).
- Script-style test modules `pwnage44000`, `pwnage45000`, `pwnage54000` call
  `sys.exit()` at import time and abort pytest collection; this is
  pre-existing and not caused by PWNAGE-61000.

A full `pytest -q` is therefore not a meaningful green gate in this tree at
present; the new suite and the relevant subsystem suites are reported
individually.

### Other checks

```text
python3 tools/s10plus/verify-kernel-config.py --config <live /proc/config.gz>  -> PASS
firmware/s10plus/install-firmware.sh --verify-mfc                            -> PASS
nuxel-mfc-diag --self-test                                                  -> PASS (17 checks)
aarch64-linux-gnu-gcc ... nuxel-mfc-decode.c                                -> PASS
bash -n <modified shell scripts>                                            -> PASS
```

---

## 9. Deployment

- No flash, no protected partition access, no camera capture and no MFC node
  open occurred during implementation.
- The patched kernel and DTB are build artifacts under
  `kernel/s10plus/.build/out/`; they were **not** written to the handset.
- `firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin` is staged locally but
  was **not** installed into the live handset's `/lib/firmware` (installing it
  on the pre-patch kernel would turn a prompt firmware-missing failure into a
  possible hardware-init hang).
- The owner-requested reboot was performed at 2026-11-03T01:37:26+01:00.
  The handset returned with a new boot ID `95b82b79-3d51-4a48-955e-b446551ccffd`
  and the **same pre-patch** kernel `4.14.253-gf7194c1d15ed-dirty`. The reboot
  did not deploy the patched kernel.
- Post-reboot state: SSH reachable, `phoc` and `wireplumber` running,
  `/dev/video6` present, guard active, WirePlumber video capture disabled,
  diagnostic state `BLOCKED_FIRMWARE_MISSING`, `safe_open_allowed=false`.
  `systemctl is-system-running` reported `degraded` with three failed units
  (`avahi-daemon`, `NetworkManager-wait-online`, `nuxel-boot-sound`); none is
  MFC-related and none is a new PWNAGE-61000 dependency.
- Software fallback verified on the handset after reboot:
  `mpv --no-config --hwdec=no --vo=null --ao=null --frames=5
  /usr/share/nuxel/preload/nuxel-preloading-screen.mp4` returned 0 and the
  asset hash still matched
  `b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1`.

---

## 10. Rollback

```sh
# narrow rollback on the handset / image rootfs
/usr/lib/nuxel/rollback-pwnage61000.sh --rootfs / \
    --receipt --firmware --userspace --restore-guard

# or from the repository against a staging rootfs
tools/s10plus/a61/rollback-pwnage61000.sh --rootfs build/out/rootfs \
    --receipt --firmware --userspace --restore-guard
```

What it does:

- removes only `/etc/nuxel/mfc/safety-receipt.json`;
- removes only `/lib/firmware/mfc_fw.bin` (not ABOX/audio or any other blob);
- removes the new userspace tools and status file;
- re-disables the four GStreamer plugins and clears stale registries;
- never flashes BOOT/recovery/modem/EFS and never touches other firmware.

Kernel/DTB rollback: keep the previous known-good boot image. The patched
kernel is additive (one required patch + config symbols); reverting means
booting the previous image, not editing the live DTB. No automatic flash is
provided.

---

## 11. Safety assessment

Resolved at source/build level:

- the 60 s userspace-fallback wait on missing `mfc_fw.bin` is removed by
  `request_firmware_direct()`;
- an empty/invalid/oversized blob returns a controlled error;
- an unknown DT `ip_ver` returns `-ENODEV` in probe;
- IRQ waits remain bounded (4000 ms, one 2× retry; 800 ms close; 5000 ms
  hwlock).

Still open:

- the live handset runs the old kernel, so the D-state risk is **not yet
  removed in production**;
- firmware ABI acceptance and runtime IOMMU/DMA behavior are unproven;
- the vendor ABI has no standard decoder-command/source-change contract, so
  drain/EOF/seek behavior must be validated with the helper and a real stream;
- no generic player can use the node directly; the rawvideo helper path is
  two-stage and not zero-copy.

---

## 12. Next blocker (single concrete action)

Deploy the PWNAGE-61000 kernel (patched `request_firmware_direct()` path) and
`mfc_fw.bin` to the handset with explicit owner approval, boot it, run
`nuxel-mfc-diag --inventory`, generate the owner-approved receipt, and perform
the single `--query-only` first open from a second SSH session. Do not open
`/dev/video6` before that.


---

## PWNAGE-71000 deployment preparation (2026-11-03)

**Status: DEPLOYMENT_PREPARED / IMPLEMENTED_NOT_PHYSICALLY_VERIFIED / OWNER_ACTION_REQUIRED**

- Built `evidence/pwnage-61000/71000/pwnage71000-boot.img` (48,596,992 bytes, SHA-256 `0a888ae709582e5072f9ae979e9d9f6468c72adf7d8850fbb0aad43991f6535a`).
- `verify-boot-image.py` PASS: header v1, raw ARM64 Image, exact live LZMA initramfs (84 cpio records, `/init` 0755), 9,074,688 bytes partition slack.
- Live BOOT backup captured read-only and verified on host and phone: 57,671,680 bytes, SHA-256 `2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc`.
- Kernel config and `request_firmware_direct()` confirmed in source, built vmlinux and Image (`#9`, build date 2026-11-03 01:36:01 CET).
- DTB `exynos9820.dtb` contains `samsung,exynos-mfc` with `ip_ver = <0x1300>`; the proven live boot image has no appended DTB.
- `tests/pwnage61000` 36 passed; `nuxel-mfc-diag --self-test` 17 checks pass; AArch64 decoder hash matches `96925752...`.
- New boot image, manifest and original backup staged at `/root/pwnage71000/`; hashes match.
- **Not performed:** BOOT write, TWRP/Download Mode, firmware install, live userspace install, `/dev/video6` open, reboot.
- Phone still runs old kernel `#5`; boot ID unchanged `e3b5e426-5c2b-4ac8-ad14-70e2cfb27ab4`; `/lib/firmware/mfc_fw.bin` absent; 0 `/dev/video6` open FDs.
- Exact flash/verify/decode/rollback procedure: `PWNAGE-71000-OWNER-ACTIONS.md`.

---

## PWNAGE 60000–65000 completion addendum (2026-11-04)

- Read-only diagnostic and truthful player policy were installed on the live
  S10+ (`/usr/local/sbin/nuxel-mfc-diag`, `/usr/local/bin/nuxel-mfc-play`,
  `/usr/share/nuxel/mfc/mfc-status.schema.json`).
- `nuxel-mfc-diag --self-test`: PASS (17 checks).
- Live status: **`BLOCKED_FIRMWARE_MISSING`**, `/dev/video6` identified as
  `s5p-mfc-dec0` but **never opened**, `mfc_fw.bin` absent,
  `safe_open_allowed=false`, GStreamer guard active.
- `tests/pwnage61000`: 36 passed.
- No firmware, kernel image, BOOT/DTB or partition was written. The prepared
  patched boot image remains staged for explicit owner approval.
