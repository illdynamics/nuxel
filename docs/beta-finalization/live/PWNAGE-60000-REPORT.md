# PWNAGE-60000 — S10+ Mali production rollout, WebKit DMA-BUF boundary, video/HDMI/casting readiness

**Date:** 2026-11-03 (Europe/Amsterdam)  
**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Mali-G76 MP12)  
**OS:** Fedora 43 aarch64 / Nuxel  
**Live kernel:** `4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT`  
**Transport:** Wi-Fi SSH `root@10.20.30.16`, key `~/.ssh/wicked_wqn_id_rsa`  
**Final cold-boot ID:** `954ea1bf-732c-4274-825f-ff2788b14467`

---

## 1. Executive summary

The already-proven Mali path is now the **normal production Home/Settings/WebKit
profile**, with a bounded, fail-closed startup probe and an automatic
`software-safe` fallback.  It survived three cold boots, two deploy cycles, a
deliberate GPU-startup-failure test and a full rollback/redeploy cycle.

On the final cold boot:

- `phoc` maps `libEGL_mesa.so.0.0.0`, `libgallium_dri.so` and
  `libwlroots-0.19.so`, holds 3 × `/dev/mali0`, and has **no llvmpipe threads**;
- `WebKitWebProcess` maps `libgallium_dri.so`, holds 3 × `/dev/mali0`, and runs
  with `NUXEL_GRAPHICS_PROFILE_ACTIVE=gpu-rendered-shm-presented`,
  `WEBKIT_FORCE_COMPOSITING_MODE=1`, `WEBKIT_DISABLE_COMPOSITING_MODE=0`;
- the profile is `gpu-rendered-shm-presented`; no fallback marker exists;
- `nuxel-wl-fb` is the **single** `/dev/fb0` writer and reports `FRAMES_OK`,
  `decon_pan_failed=0`, panel 1440×3040;
- the Settings API returns `ACCELERATED_SHM` /
  `GPU-RENDERED / SHM-PRESENTED` and keeps `zero_copy_scanout=false`.

Measured matched A/B (3 × 60 s each, same boot, screen kept awake, profile
verified inside the measured WebKit process):

| Case | `software-safe` median | `gpu-rendered-shm-presented` median | Delta |
|---|---:|---:|---:|
| idle Home | 11.05% of one core | 5.10% | **−53.8%** |
| Settings scroll | 22.80% | 23.83% | +4.5% |

The idle win is large and repeatable.  The scroll workload is a small **4.5%
regression**, inside the mission's 5% bound: Phoc drops from 8.35% to 3.29%,
but WebKitWebProcess rises from ~4.0% to ~13.8% because it now keeps an
accelerated compositor busy.  This report does not turn that into an FPS or
battery claim.

**WebKit DMA-BUF is still BLOCKED**, now with source-level and live proof rather
than a guess.  `webkitgtk-2.54.1` (`628d6ce1850e17225185a5807a9d0aa375bae2be`)
requires `drmMainDevice()` for `RendererBufferTransportMode::Hardware`; the live
`drmGetDevices2()` probe returns `ENOENT`, `/dev/dri` is absent and
`CONFIG_DRM_VGEM` is unset.  No fake DRM node, no `/dev/mali0` symlink and no
`WEBKIT_WEB_RENDER_DEVICE_FILE` stub was used.  WebKit remains truthfully
**GPU-rendered, SHM-presented**, and the final panel remains the CPU
framebuffer bridge.

Hardware video decode remains **BLOCKED_GUARDED**: the S10+ exposes
`s5p-mfc-dec0` (`/dev/video6`), but `mfc_fw.bin` is absent from every firmware
path and `CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y` can wait in
`request_firmware()`.  No `/dev/video*` node was opened.  USB-C/DP Alt Mode/HDMI
is `NEEDS OWNER TEST`; Miracast and LAN share are `CANDIDATE` only, with no UI
control exposed.

---

## 2. Starting point and revalidation

The PWNAGE-53000 state was reproduced on the physical phone before edits:

- Phoc: `libEGL_mesa.so.0.0.0` + `libgallium_dri.so` + `libwlroots-0.19.so`,
  3 × `/dev/mali0`, 1 × `/dev/udmabuf`, no llvmpipe threads.
- `nuxel-wl-fb`: sole `/dev/fb0` writer, `FRAMES_OK`, `decon_pan_failed=0`,
  `virtual_size=1440,6080`, mode `U:1440x3040p-0`.
- `graphics-profile.json`: `default_profile=software-safe`.
- WebKit at baseline: `WEBKIT_DISABLE_COMPOSITING_MODE=1`,
  `LIBGL_ALWAYS_SOFTWARE=1`, no `libgallium_dri.so`, no `/dev/mali0`.
- KLVND link `/usr/lib64/libEGL_mesa.so.0` still pointed at the stock
  `.nuxel-bak`; the kbase library was only selected by the systemd vendor JSON.
  The new release manifest/verifier now checks this exact failure.
- Baseline bridge state (old A67 binary):
  `blit_avg_ms=27`, `damage_avg_ms=27` on the live Home.

Baseline evidence: `evidence/pwnage-60000/baseline/01-*.txt` … `08-*.txt`.

---

## 3. What changed

### 3.1 Production profile and fallback

`configs/nuxel/graphics/graphics-profile.json` now defaults to
`gpu-rendered-shm-presented`, with WebKit and GTK3 sections pointing at it and
`software-safe` as the per-process fallback.  `gpu-rendered-dmabuf-presented`
and `fully-accelerated` remain unavailable with explicit reasons;
`presentation.zero_copy_scanout=false`.

`tools/s10plus/a45/nuxel-graphics-profile` was rewritten with:

- strict schema/profile/application/fallback validation (`validate`);
- closed, shell-quoted `env` output (no `eval` of untrusted values; newline and
  control-character flattening);
- bounded kbase EGL probe (4 s default, process-group kill on timeout);
- per-boot, library/policy-hash-keyed cache in
  `/run/nuxel/graphics-gpu-probe.json`;
- automatic software fallback if `/dev/mali0`, the pinned Mesa/wlroots set, the
  EGL vendor JSON, the probe or the renderer check fails;
- compositor fallback-marker awareness;
- separate `profile_requested` / `profile_active` / `fallback_active` and a
  reason;
- explicit GTK4 `gl` only after the live GSK probe passes, `cairo` fallback.

A missing probe is **fail-closed** (release images require it); the explicit
developer escape is `NUXEL_GPU_PROBE_DISABLE=1`.

`tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh` now runs the bounded probe
**before** phoc gets the session.  A failed probe arms the existing
`/run/nuxel-gpu-fallback` marker, selects pixman and leaves the panel usable.
`nuxel-session.sh` pre-warms the same probe and resolves the WebKit/GTK
environment from the helper.

### 3.2 Cold-boot revert defect (found and fixed)

The first cold boot after deployment came up with WebKit software despite Phoc
being on Mali.  Root cause: the PWN36000 boot bootstrap
(`stage36000/apply-pwnage36000.sh`) unconditionally installed its October 2026
`session/nuxel-session.sh` over the newer deployed session on every boot.

Fix:
- `services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh` now applies the session
  only if the staged copy is genuinely newer;
- the image builder stages the guarded bootstrap and the current session;
- the image verifier fails if the guard is missing or staged/deployed session
  hashes differ;
- deploy installs both live and staged copies.

The final cold boot shows identical hashes:
`07668a4e3d8fcce31ef895239977a14696834eae30222c491d0ba8d87df4403f` for both
`/usr/lib/nuxel/nuxel-session.sh` and
`/usr/lib/nuxel/stage36000/session/nuxel-session.sh`, and WebKit starts on Mali.

### 3.3 Release pinning and fail-closed image verification

- `tools/s10plus/a67/gpu-build-pins.env` pins:
  - Mesa `a5010bb447ae34e697cb917c2d387272063e9fd8`
    (`26.3.0-devel (git-a5010bb447)`);
  - wlroots tag `0.19.3` peeled commit
    `88a869855742281c98c22cab9641b317b8d065ef`;
  - Fedora 43 / aarch64-glibc-2.42 / libglvnd 1.7.0-8.fc43.
- `build-mesa-kbase-wayland.sh` and `build-wlroots-kbase-linear.sh` fetch,
  detach to the full commit, clean the tree and `git apply --check` the patches.
- `release/s10plus/gpu/gpu-manifest.json` records path, SHA-256, mode, SONAME,
  ELF build ID, source commits, patch hashes, probe hash, profile and symlinks.
- `release/s10plus/gpu/SHA256SUMS` is regenerated by
  `tools/s10plus/a67/gen-gpu-manifest.py`.
- `tools/s10plus/a67/nuxel-gpu-image-verify.sh` verifies every hash/mode,
  GLVND symlink (rejecting `.nuxel-bak`), profile default, software fallback,
  unavailable modes, probe presence, runtime manifest, and the stage36000
  session guard.
- `images/s10plus/build-phone-rootfs-inside-fedora.sh` sets `GPU_REQUIRED=1`
  when `NUXEL_RELEASE=1` or `NUXEL_REQUIRE_KBASE=1`, verifies the release hashes
  before installing, never falls back to a developer tree, installs the runtime
  manifest, and runs the image verifier as the final gate.

A full rootfs image was not built in this run (no aarch64 container/image build
was authorized here); the verifier was exercised against a synthetic stage and
the live root.  That limitation is reflected in the matrix.

### 3.4 Layered diagnostics

`tools/s10plus/a67/nuxel-gpu-status` is the single read-only status source:

- kernel GPU/kbase, EGL vendor/library/renderer, Phoc mappings/FDs/threads,
  GTK3, GTK4/GSK, WebKit renderer and transport, linux-dmabuf protocol/format
  info, final panel writer/geometry/timings, MFC, Type-C, casting;
- `--json` and human output; `--deep` runs bounded GTK probes; normal refresh is
  `--no-probe`;
- FD scanning normalizes systemd's `/newroot/...` namespace prefix and reports
  `fd_scan=denied` instead of a false “zero FDs”;
- no `/dev/video*` open, no `/dev/fb0` open, no DRM node creation.

The bridge `graphics.status` RPC now maps this document to
`nuxel.graphics-status/2`, caches it for 5 s, and reports
`ACCELERATED_SHM` / `GPU-RENDERED / SHM-PRESENTED` separately from
`zero_copy_scanout=false`.

### 3.5 Framebuffer bridge (`nuxel-wl-fb`)

Only measured, contract-preserving changes:

- persistent wlr-screencopy SHM buffer instead of reopening/recreating the
  shm file, mmap and `wl_buffer` every frame;
- dirty **runs** (up to 64) instead of one min..max row span, so a clock at the
  top and a battery glyph at the bottom do not re-expand the unchanged middle;
- copy-back only changed rows, not the whole 4.4 MiB source frame;
- atomic state/proof writes (`tmp` + `rename`) so status readers never see a
  truncated file;
- orientation proof throttled to 1 Hz;
- separate capture/compare/blit/pan timings in `FRAMES_OK`;
- new `--damage-selftest` for coalescing, full-span detection and pathological
  fragmentation fallback;
- single-owner lock, `/dev/fb0` open count, rotation/touch code and one-writer
  contract unchanged.

Live bridge state after the change: `blit_avg_ms=1–2`, `damage_avg_ms=0–2`,
`pan_avg_ms=8–10`, `capture_avg_ms=4–9`, `compare_avg_ms=0–3`, `decon_pan_failed=0`.
The old baseline reported 27 ms blit average.  This is a live-state comparison,
not a controlled synthetic blit benchmark; the workloads differ.

### 3.6 WebKit 2.54.1 DMA-BUF gate

Source evidence saved under `evidence/pwnage-60000/webkit/`:

- tag `webkitgtk-2.54.1`, peeled commit
  `628d6ce1850e17225185a5807a9d0aa375bae2be`;
- `AcceleratedBackingStore::rendererBufferTransportMode()` adds
  `RendererBufferTransportMode::Hardware` only after a non-null
  `drmMainDevice()`;
- `DRMMainDevice.cpp` enumerates `drmGetDevices2(0, ...)` and requires a real
  render node.

Live probe `nuxel-drm-main-device-probe` (read-only, same libdrm enumeration):

```
drm_devices=error errno=2
render_nodes=0 webkit_drmMainDevice_is_null=true
WEBKIT_WEB_RENDER_DEVICE_FILE=unset
```

Options evaluated and rejected: bypassing only the check (still no GBM
allocator); `WEBKIT_WEB_RENDER_DEVICE_FILE=/dev/mali0` (fake DRM identity, no
GBM ioctls); `/dev/dri` symlink (forbidden and nonfunctional); VGEM alone
(enumeration only, no kbase-exportable/scanout buffer); real Exynos DRM/KMS
integration (independent, conflicts with the working DPU20 fbdev owner and
requires a separately approved kernel project).

### 3.7 Video, USB-C/HDMI and casting

- MFC: `samsung,exynos-mfc` at `188d0000.mfc`, driver `s5p-mfc`,
  `MFC_DRIVER_INFO 180315`, firmware name `mfc_fw.bin`.  The file is absent
  from `/lib/firmware`, `/usr/lib/firmware` and `/vendor/firmware`.
  `CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y` makes a blind open unsafe.  No
  `/dev/video*` was opened; the GStreamer guard remains installed.
- USB-C: `/sys/class/typec/port0` exists (dual role); **no DP altmode
  directory and no DRM connector**.  No mux/PMIC/PHY/regulator writes.
- Casting: `iw` reports a P2P device and a `p2p0` interface; `openh264enc`
  exists; `grim`/PipeWire exist.  There is no implemented
  capture→encode→RTSP/RTP→receiver pipeline and no `gnome-network-displays`
  drop-in.  No Cast UI control was added.

---

## 4. Live evidence

### 4.1 Final cold boot (PASS)

`evidence/pwnage-60000/live/29-final-boot.txt`

- boot ID changed to `954ea1bf-732c-4274-825f-ff2788b14467`;
- all five services active (`nuxel-wayland`, `nuxel-wl-fb`, `nuxel-bridge`,
  `nuxel-http-bridge`, `nuxel-web`);
- profile active: `gpu-rendered-shm-presented`, no fallback marker;
- Phoc: 3 × `/dev/mali0`, `libEGL_mesa`/`libgallium`/`libwlroots`, no
  llvmpipe threads;
- WebKit: profile active, `WEBKIT_DISABLE_COMPOSITING_MODE=0`,
  `WEBKIT_FORCE_COMPOSITING_MODE=1`, `libgallium_dri.so`, 3 × `/dev/mali0`,
  no udmabuf/dmabuf presentation FDs (SHM transport);
- bridge: `FRAMES_OK`, `decon_pan_failed=0`, one writer, 1440×3040 panel,
  `virtual_size=1440,6080`.
- live pixels on this final boot: two grim captures 65 s apart differ in
  2.03% of pixels (bbox 98,67–636,346, the Home clock area); `final-g.png` /
  `final-h.png` and `33-final-live-pixels.txt` are in
  `evidence/pwnage-60000/live/`.

### 4.2 Automatic GPU startup failure and recovery (PASS)

`evidence/pwnage-60000/live/14-fallback-test.txt`

Test method: temporarily rename the installed `nuxel-kbase-egl-probe`, remove
the marker/cache and restart the session.  The probe is missing, so the wrapper
fails closed before phoc.

Observed:

- fallback marker created;
- `nuxel-wayland` and `nuxel-wl-fb` active;
- WebKit `NUXEL_GRAPHICS_PROFILE_ACTIVE=software-safe`,
  `WEBKIT_DISABLE_COMPOSITING_MODE=1`, no `libgallium_dri.so`;
- `FRAMES_OK`, `decon_pan_failed=0`;
- screenshot `/tmp/fallback.png` is 511,941 bytes (not a blank 0-byte panel);
- after restoring the probe and removing the marker, WebKit returned to the
  GPU profile with 3 × `/dev/mali0`.

### 4.3 Rollback and redeploy (PASS)

`evidence/pwnage-60000/deploy/rollback-test-*.log`,
`rollback-verify.txt`

- `rollback-pwnage60000.sh` restored the pre-PWNAGE-60000 backup
  (`/var/backups/nuxel/p60000-20261102T225116Z`) with all hashes verified;
- the old session/helper/profile came back, WebKit was software, services and
  `FRAMES_OK` stayed healthy (`ROLLBACK_OK`);
- the final deploy then reinstalled the GPU set, validated the profile, passed
  the image verifier on the live root, and restarted the minimum services.

### 4.4 Matched A/B

Raw data: `evidence/pwnage-60000/bench/final/final-bench/`  
Summary: `evidence/pwnage-60000/bench/final/SUMMARY.json`

| Process (median, % one core) | SW idle | GPU idle | SW scroll | GPU scroll |
|---|---:|---:|---:|---:|
| Phoc | 3.41 | 1.16 | 8.35 | 3.29 |
| `nuxel-wl-fb` | 1.83 | 0.84 | 2.51 | 2.10 |
| WebKitWebProcess | 3.01 | 1.65 | 4.03 | 13.77 |
| `nuxel-pwa-host` | 3.09 | 1.46 | 7.90 | 4.53 |
| **Active UI total** | **11.05** | **5.10** | **22.80** | **23.83** |

- GPU idle: **−53.8%** (all three runs below every SW run).
- GPU Settings scroll: **+4.5%** (within the 5% regression bound).
- No FPS or p95 frame-time claim is made.  The bridge's per-phase timings and
  frame counts are raw state snapshots, not a frame-time distribution.
- The scroll workload is a bounded wheel stream from
  `nuxel-scroll-workload` over a second Settings PWA host under the verified
  profile; it is not a touch gesture.  Physical touch/rotation was not
  exercised in this run and is listed as an owner check.

---

## 5. Capability matrix

| Capability | Result | Evidence |
|---|---|---|
| Phoc Mali rendering | **PASS** | live maps, 3 × `/dev/mali0`, no llvmpipe |
| GTK3 accelerated widgets | **PASS** | deep `GtkGLArea` probe: `Mali-G76 MC12 (Panfrost)` |
| GTK4/GSK acceleration | **PASS (gl) / cairo fallback** | live GSK probe prints PASS with `GSK_RENDERER=gl`; production session sets `gl` only on GPU profile |
| Home/Settings WebKit GPU rendering | **PASS** | cold-boot WebKit maps + 3 × `/dev/mali0`; Settings host asserted under the same profile during A/B |
| WebKit SHM presentation | **PASS** | zero udmabuf/dmabuf presentation FDs, transport=`shm` |
| WebKit DMA-BUF presentation | **BLOCKED** | source gate + live `drmGetDevices2` ENOENT; no fake device |
| Final panel zero-copy scanout | **NOT AVAILABLE** | `nuxel-wl-fb` still CPU copy/scale to `/dev/fb0`; status says false |
| Framebuffer bridge optimization | **PARTIAL** | timings improved, selftests PASS, live frames healthy; physical touch/rotation not exercised |
| Production profile default + fallback | **PASS** | cold boot + deliberate probe failure + restore |
| Exynos MFC hardware decode | **BLOCKED_GUARDED** | `mfc_fw.bin` absent; no video node opened; guard active |
| USB-C DP Alt Mode / HDMI | **NEEDS OWNER TEST** | Type-C present, no DP altmode, no DRM connector; no mux writes |
| Wireless Miracast | **CANDIDATE** | P2P capability only; no RTSP/capture/encoder/receiver proof |
| LAN/WebRTC screen share | **CANDIDATE / NOT IMPLEMENTED** | no authenticated capture pipeline |

---

## 6. Tests and exact results

Run on 2026-11-03 from `/x/nuxel`:

```sh
python3 -m pytest -q tests/pwnage52000 tests/pwnage50000 tests/pwnage53000 tests/pwnage60000
# 91 passed in 2.24s
```

Coverage added in `tests/pwnage60000/`:

- shipped default is GPU-SHM with `software-safe` fallback;
- missing GPU node/library/vendor JSON → software-safe with reason;
- compositor fallback marker → software-safe;
- Panfrost probe accepted and cached once per boot;
- llvmpipe renderer rejected;
- probe timeout bounded and falls back;
- missing probe fails closed;
- cache invalidated when the policy file changes;
- GTK3/GTK4 targets do not leak WebKit variables;
- malicious/newline values are shell-quoted and flattened;
- invalid profile/app/fallback and fake `fully-accelerated` rejected;
- status reports requested/active/gpu separately;
- manifest hashes match release files and pinned commits;
- synthetic image stage passes; tampered hash, stock EGL symlink, software
  default, unguarded boot bootstrap and staged-session mismatch all fail;
- diagnostics are read-only and never open `/dev/video*`;
- framebuffer source has persistent buffer, dirty runs, phase timings,
  one-writer lock and damage selftest.

On-device:

```sh
/usr/lib/nuxel/nuxel-wl-fb --damage-selftest
# PASS dirty-run coalescing, full-span detection, fragmentation fallback
/usr/lib/nuxel/nuxel-wl-fb --colour-selftest
# PASS all primaries + alpha
/usr/lib/nuxel/nuxel-kbase-egl-probe
# GL_RENDERER=Mali-G76 MC12 (Panfrost), GLES 3.2, rc=0
tools/s10plus/a67/nuxel-gpu-image-verify.sh <stage> --manifest release/.../gpu-manifest.json
# GPU IMAGE VERIFY: PASS (10 files, 3 symlinks)
```

All raw outputs are under `evidence/pwnage-60000/`.

---

## 7. Deployment and rollback

Deploy (atomic, hash-verified, auto-rollback on health failure):

```sh
tools/s10plus/a67/deploy-pwnage60000.sh root@10.20.30.16
```

Rollback:

```sh
tools/s10plus/a67/rollback-pwnage60000.sh root@10.20.30.16 [backup-dir]
# default backup: /run/nuxel-p60000-backup-dir
```

The deploy:
- backs up every replaced file with modes and SHA-256;
- builds the two probes and bridge on the target;
- runs the damage/colour selftests and the kbase EGL probe;
- installs only userspace files (no BOOT, firmware, partition or `/dev/fb0`
  writes);
- verifies the live tree against the release manifest;
- restarts `nuxel-wayland`, `nuxel-wl-fb`, then `nuxel-bridge`;
- requires `FRAMES_OK`, one `/dev/fb0` writer and a WebKit process with
  `libgallium` + `WEBKIT_DISABLE_COMPOSITING_MODE=0`;
- rolls back automatically if the health check fails.

Latest verified deployment:
`/var/backups/nuxel/p60000-20261103T001339Z`  
Rollback proof: `/var/backups/nuxel/p60000-20261102T225116Z`.

---

## 8. Artifact hashes (live)

| Artifact | SHA-256 |
|---|---|
| `libEGL_mesa.so.0.0.0` | `eba18f340e519bbd04765c0744bb7f554df99ca328f3dd7921698600d3477b0f` |
| `libgallium_dri.so` | `818bc380242006c158455241099b3b5185dfc70630f6f4c9cda5602a9196b800` |
| `libwlroots-0.19.so` | `95e039a783bf4e9263542a01f9609e03ffb4b2f8d47ca9ec23c60a6803d2d4cc` |
| `nuxel-wl-fb` | `137eed48d33b8545f8c5dbabe82a183a6d0b089c26a62974902b947090757785` |
| `nuxel-kbase-egl-probe` | `613ee5ed4926883e9a12ba87158c85ee4a288b38f6985c746bf8c3e0d7c2eabd` |
| `nuxel-graphics-profile` | `cf161394aa3f418ad1125e08adae46fcaa3278e1cf0b8ad301de061f1aaa0dbc` |
| `nuxel-gpu-status` | `9a8e4d2ff3b4a95b40bb186ab6b949bb6a293d62f64cd946bab4764a2478dcd5` |
| `nuxel-wayland-gpu-wrapper.sh` | `31d6bc3aab4fefa028b7912171ce1f42496624de53a05340e94e469d96d790e7` |
| `nuxel-session.sh` | `07668a4e3d8fcce31ef895239977a14696834eae30222c491d0ba8d87df4403f` |
| bridge `api.py` | `a337121202eff07c36cfc2f8e45a3043e9110dac8f37f2223174acbca46eb5fd` |
| PWN36000 apply (live) | `a357b0fa013e4f81c056db5fc76cb812c10aa8f48f37e958e5fe4ce3bc91a638` |

The release manifest additionally records ELF build IDs:
`libEGL_mesa` `d1a3a0a58aa0b86246526a32d4f54184979e16ab`,
`libgallium_dri` `0924f8d37dab71b26cdc0b295794b8d24e1ac086`,
`libwlroots` `e7ce7b747b395e4fc73e3deccf903252344c2b26`.

---

## 9. Owner handoff — physical cable / receiver tests

Do these only with an alternate recovery path (Wi-Fi SSH is currently working):

1. **USB-C → HDMI**: record the adapter chipset and power arrangement; run
   `nuxel-typec-diag.sh status --json` before and after connecting; capture
   `dmesg -w` and the full `nuxel-gpu-status --json`.  Stop when DP Alt Mode or
   a DRM connector is not observed.  Do not write mux/PMIC/PHY/regulator state.
2. **HDMI output**: only if a real DRM connector/EDID appears, test 1080p60,
   then 1440p if the link/monitor allow.  Visible Nuxel pixels are required
   before claiming support.  Keep the internal panel/touch/rotation working.
3. **Miracast**: requires a real P2P group, RTSP, capture, H.264 encode, RTP and
   a receiver showing moving Nuxel pixels.  Capability enumeration alone is not
   proof.  No Cast control exists yet.
4. **LAN/WebRTC screen share**: require explicit start/stop, single-use pairing,
   authentication, lockscreen redaction and network scoping before any UI.
5. **Touch/rotation regression**: perform a physical touch, rotation, suspend/
   resume and screen-off/on check.  The bridge code path for rotation/touch was
   not modified, but this run did not exercise those physically.

Do not flash boot/recovery/EFS/modem/partitions, do not enable
`CONFIG_DRM_EXYNOS` as an experiment, do not create `/dev/dri` or symlink
`/dev/mali0`, and do not remove the GStreamer guard without the MFC firmware
and open-path proof described in `evidence/pwnage-60000/mfc/README.md`.

---

## 10. Honest remaining gaps

- WebKit DMA-BUF/zero-copy presentation is blocked by the missing DRM/GBM
  device; a real kernel/display project is required.
- The final panel still has a CPU copy/scale; `fully-accelerated` remains
  unavailable.
- GPU-SHM is 4.5% higher than software-safe under the Settings-scroll workload;
  idle Home is 53.8% lower.  No frame-time distribution was collected.
- The full release image was not built here; the fail-closed verifier was tested
  against a synthetic stage and the live root.
- MFC hardware decode remains blocked on matching `mfc_fw.bin` and a safe
  open/close/ABI proof.
- HDMI and casting remain owner/hardware projects; no UI claims were added.
- Physical touch/rotation/suspend regression was not exercised in this run.

**Bottom line:** the proven Mali path is now the normal Home/Settings path after
cold boot, the software fallback is automatic and tested, the release gate is
fail-closed, the WebKit DMA-BUF boundary is documented with real source and
device evidence, and no unsupported “fully accelerated”, zero-copy, hardware
video, HDMI or Miracast claim is made.


---

## PWNAGE-70000 live completion (2026-11-03)

**Status: PARTIAL / OWNER_ACTION_REQUIRED**

- Atomic userspace deploy `tools/s10plus/a67/deploy-pwnage60000.sh root@10.20.30.16` **PASSED** (exit 0).
- Backup: `/var/backups/nuxel/p60000-20261103T192549Z`.
- `GPU IMAGE VERIFY: PASS (10 files, 3 symlinks)` against the live rootfs `/`.
- EGL symlink now `libEGL_mesa.so.0 -> libEGL_mesa.so.0.0.0`; installed `nuxel-session.sh` and runtime manifest both `fe61581a46f95b725e90c0f76cd2e2ab4484db0f81cb017c9151bbe2a85ed2e2`.
- kbase probe: `Mali-G76 MC12 (Panfrost)`, GL ES 3.2, rc 0.
- phoc: 8 Mesa maps, 0 llvmpipe, `/dev/mali0` + udmabuf FDs. WebKit: 3 `/dev/mali0` FDs, `gpu-rendered-shm-presented`, transport `shm`.
- Exactly one `/dev/fb0` writer; `FRAMES_OK` during deploy/fallback; presenter remains the CPU framebuffer bridge; zero-copy false.
- Fallback proven for the marker and genuine probe-missing paths, both `FRAMES_OK`, then restored to the GPU profile with a fresh WebKit process.
- Host tests: pwnage60000 31 passed, pwnage53000 13 passed, pwnage50000 8 passed; release SHA256SUMS 10/10.
- **Not tested:** matched A/B benchmark (harness exited early); cold boot (no reboot authorized).
- **Blocked/unchanged:** WebKit DMA-BUF, zero-copy scanout, USB-C DP/HDMI, casting and MFC remain as previously labelled.
- Rollback: `tools/s10plus/a67/rollback-pwnage60000.sh root@10.20.30.16 /var/backups/nuxel/p60000-20261103T192549Z`.

---

## PWNAGE 60000–65000 completion addendum (2026-11-04)

**GPU status: `GPU_ACCELERATION_VERIFIED` (GPU-SHM path).**

Live revalidation on the same handset (kernel `#5`, boot `e3b5e426…`):

- kbase probe: `Mali-G76 MC12 (Panfrost)`, GLES 3.2, rc 0;
- Phoc: 3 × `/dev/mali0`, 0 llvmpipe threads; Home WebKit:
  `gpu-rendered-shm-presented`, 3 × `/dev/mali0`;
- `nuxel-wl-fb`: `FRAMES_OK`, `decon_pan_ok=4936`, `decon_pan_failed=0`,
  one writer, panel 1440×3040;
- new `tools/s10plus/a67/nuxel-gles-bench.c`: 512×512, 128-iteration shader,
  **Mali median 176.3 fps vs llvmpipe 20.2 fps (8.73×)**, identical pixels;
- during burn: `gpu_busy` **78–86 %**, clock **200–377 MHz**, `mali_trace`
  `JM_SUBMIT`/`JM_JOB_DONE`;
- no fallback marker; profile on disk defaults to GPU-SHM.

Zero-copy remains blocked exactly as documented (`/dev/dri` absent,
`CONFIG_DRM_VGEM/EXYNOS` unset). No reboot was performed in this run; cold-boot
persistence remains an owner check. Full evidence:
`artifacts/pwnage-completion-60000-65000/`.
