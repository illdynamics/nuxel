# NUXEL — ORIGINAL MP4 BOOT ANIMATION (WoNQ priority 1)

## 1. The asset (found, fingerprinted, preserved)

| Field | Value |
|---|---|
| Source path | `assets/nuxel-boot-animation.mp4` (canonical, git-tracked) |
| SHA-256 | `280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c` |
| Size | 5,474,699 bytes |
| Container | QuickTime / MOV (`isom`), encoder `Google` |
| Video codec | H.264 High (`avc1.640028`), level 4.0, yuv420p, 8-bit |
| Resolution | 1080 × 1920 (portrait) |
| Frame rate | 24 fps, 192 frames |
| Duration | 8.000 s |
| Audio tracks | **none** |
| Copies in tree | `pwa/nuxel-apps/*/assets/`, `build/out/rootfs*/usr/share/nuxel/boot/` — all byte-identical (verified by size + the two tools that gate on it) |

The asset was **not** regenerated, re-rendered, substituted or restyled. It is the
original file, unchanged.

## 2. How the original was meant to be played — and why that cannot work here

`tools/build-nuxel-boot-theme.sh` is the original single source of truth: it turns
the MP4 into a **Plymouth "script" theme** (720×1280 RGBA PNG frame sequence,
`NUXEL_BOOT_FPS=12`, navy padding, `nuxel.plymouth` + `nuxel.script` looping until
Plymouth quits), installed into `/usr/share/nuxel/boot/`.

Plymouth needs a DRM/KMS renderer. This Samsung downstream kernel reports
`# CONFIG_DRM is not set` and exposes only `/dev/fb0` (Exynos DECON/DSIM fbdev).
**Plymouth cannot run at all on this kernel**, which is why the bring-up used a
diagnostic penguin instead.

## 3. The chosen architecture — Approach B, preprocessed, framebuffer-native

Same idea as the Plymouth theme (preprocessed frames), but decoded by a Nuxel
freestanding player straight onto the DECON fbdev:

```
assets/nuxel-boot-animation.mp4                (the original, unchanged)
        |  tools/s10plus/nuxel-anim-pack.py     (build time, on the Mac)
        v
build/out/s10plus/nuxel-animation.nux          18,481,546 B  sha256 7d296871…
        |  tools/s10plus/nuxel-anim-player.c    (freestanding aarch64, 66 KB)
        v
/dev/fb0  1440×3040×32bpp, stride 5760, yres_virtual 6080 (2 buffers)
```

### 3.1 Why this encoding

Measured on the source (see `nuxel-animation.pack.json`):

* the animation is **dark**: 96 % of frame 0 is near-black, mean luma ≈ 10–34;
* consecutive frames differ by only **mean |Δ| = 1.15/255**, i.e. it is a
  near-static scene revealed slowly, plus H.264 grain;
* that grain defeats a naive frame delta: raw index-plane deflate was 48.6 MB,
  `sticky` + deflate still 21.3 MB, and a *whole-plane* delta needed 2 MB of
  inflate per frame — far too much CPU for 24 fps.

Final pipeline:
1. `ffmpeg` — `hqdn3d=3:3:6:6` denoise, lanczos scale to **1080×1920** (native);
2. a **shared 256-colour median-cut palette**, no dither — reconstruction error
   1.75/255;
3. **temporal stickiness**: a pixel keeps its previous palette index while the new
   colour is within 6/255 of it. This is what removes the grain churn
   (12.5 % → 5.6 % of pixels change per frame);
4. frame 0 = raw index plane; frames 1.. = **span list of changed pixels only**
   (varint gap, u16 length, new indices), each **raw-DEFLATE**d;
5. container `NUXANM01` with a palette, a frame table and per-frame blobs.

Result: **18,481,546 B (18.5 MB), 21.5× smaller than the raw index planes, 38.2 dB
PSNR** against the denoised source. Inflate workload during playback is only
~220 KB/frame (~5 MB/s at 24 fps) instead of 2 MB/frame.

### 3.2 Player properties

* freestanding aarch64, no libc, no dynamic linking, 66 KB — rides in the
  **initramfs** (BOOT partition); the 18.5 MB container lives in the **Fedora
  rootfs**, so the kernel image is not enlarged by animation data;
* reads the **real** `/dev/fb0` geometry at runtime; never assumes 1440×3040;
  fits the source raster into the panel with integer nearest-neighbour maths and
  centres it (letterbox bars painted black, matching the artwork);
* paints **every** virtual buffer (yres_virtual/PH), because the DECON may scan
  either half of the 6080-line surface;
* only changed pixels are written: ~410 K pixel writes/frame across both buffers;
* bounded memory: index plane (2.07 MB) + one inflate buffer (2.07 MB) + the
  mmap'd container. The animation is **never** held uncompressed;
* pacing: sleeps to a monotonic deadline; if it falls behind it resynchronises
  the deadline instead of accumulating unbounded lag (late frames are dropped,
  never queued);
* **takes the framebuffer over itself**: it walks `/proc` with `getdents64`,
  SIGTERMs any `nuxel-fb-phone` painter, and publishes the displaced pid to
  `fb-hold.pid`. Two painters can never fight for the surface;
* **stops only on an explicit request** — SIGUSR1/SIGTERM or the `anim-stop`
  file. Never on a timer;
* survives `switch_root`: the state directory is held open as a **directory fd**
  before the pivot, so `openat`-relative writes keep working after init moves the
  rootfs from `${ROOT_MNT}` to `/`.

## 4. Offline validation (all green, no handset needed)

`tools/s10plus/test-anim-player.sh`:

```
PASS source MP4 is the original asset          (sha256 280e094f…)
PASS device player is small enough for the initramfs (66,120 B)
PASS device player is an aarch64 ELF
PASS magic NUXANM01
PASS all 192 frames decode bit-identically in C and Python
```

The last line is the important one: the **C decoder that ships on the device** and
an **independent Python decoder** produce identical CRC32 for every one of the 192
decoded index planes. The device binary's inflate and span applier are therefore
proven correct off-device.

## 5. Handoff state machine (implemented)

```
EARLY_FIRST_LIGHT            init.sh nuxel_first_light()      (proven A16/A19)
   -> FEDORA_MOUNTED         init.sh nuxel_start_animation()  marker FEDORA_MOUNTED
   -> ORIGINAL_MP4_ANIMATION player starts, ANIM_STAGE=ORIGINAL_MP4_ANIMATION
   -> PHONE_UI_STARTING      (not yet implemented)
   -> PHONE_UI_FRAME_COMMITTED / PHONE_UI_READY  (not yet implemented)
   -> ANIMATION_STOPPED      on SIGUSR1/SIGTERM/anim-stop only
```

`nuxel-anim-player` takes the framebuffer over from the penguin and holds it. If
the player or the container is missing, `init.sh` keeps the first-light penguin —
the fallback is preserved exactly as before.

## 6. Deployment

| Piece | Where | Delivered by |
|---|---|---|
| `nuxel-anim-player` (66 KB) | initramfs `/opt/nuxel/` | BOOT partition (A20) |
| `nuxel-anim-player` (copy) | rootfs `/usr/bin/` | live write, sha256 re-verified |
| `nuxel-animation.nux` (18.5 MB) | rootfs `/usr/share/nuxel/boot/` | live write, sha256 re-verified |

USERDATA was **not** reflashed: one directory and two files were added to the
mounted ext4 rootfs and the filesystem was unmounted cleanly.

## 7. Status

```
MILESTONE_ORIGINAL_MP4_ANIMATION_IMPLEMENTED            = yes
MILESTONE_ORIGINAL_MP4_ANIMATION_OFFLINE_VALIDATED      = yes
MILESTONE_ORIGINAL_MP4_ANIMATION_DELIVERED_TO_HARDWARE  = yes (A20, kernel-embedded initramfs)
MILESTONE_ORIGINAL_MP4_ANIMATION_VISIBLE_ON_AMOLED      = PENDING USER OBSERVATION
```

## 8. Delivery note — the three wasted A20 flashes

The first three A20 attempts shipped only a new BOOT partition and changed nothing
at all on the device, because this board's bootloader never populates the initrd
memory it advertises and the kernel therefore runs its **built-in** initramfs. See
`INITRAMFS-DELIVERY-ROOT-CAUSE.md`. The working delivery is:

```
init.sh -> initramfs.cpio -> (kbuild) Image-A20 with CONFIG_INITRAMFS_SOURCE -> boot.img -> BOOT
```

A20 as finally shipped embeds the A20 initramfs in the kernel and adds a
`NUXEL_INIT_REV=A20-original-mp4-animation` line so a capture can never again be
ambiguous about which `/init` ran.

Hardware confirmation is required from the operator: see `NEXT-ACTION.md`.
