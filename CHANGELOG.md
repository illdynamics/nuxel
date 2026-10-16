# Changelog

All notable changes to the Nuxel Phone OS repository are documented here.

The canonical version lives in [`VERSION`](VERSION) and is bumped in lockstep
across the shell apps, the PWA manifest, the device `APKBUILD`s, the VM tooling
and the OTA builder (see *Versioning* below).

---

## [v0.5.0-beta-rc1] — 2026-10-16 — *live deployment cycle (task2)*

**Version unchanged on purpose:** this cycle does not add a new feature surface, it moves what was
already written onto the physical handset. The identifier stays `v0.5.0-beta-rc1` (no silent
renumber); the release engineering that justifies `-rc1` is unchanged, and the Beta verdict is still
`BETA_CANDIDATE_PENDING_HARDWARE_PROOF`.

**Landed on the phone (S10+ `beyond2lte`, from host `dextronux`):**

* **Root fix.** The deploy plan now resolves onto `/usr/share/nuxel` — the root the handset actually
  serves — instead of `/home/nuxel/nuxel`, which does not exist on the device. 440/624 targets were
  pointed at a tree nothing reads; that was why earlier passes produced "no difference on my phone".
  Manifest gains a `target_root_map`; `nuxel_live.build_deploy_plan` applies it before guarding.
* **Applied** the 16-group / 624-step plan (5 runs): launcher + safe zones (22/22), PWA app suite +
  shared runtime + registry (400/400), configs / a33 tools / services / native-shell sources /
  touch+buttons / audio+network (185/185), a33 runtime + session units + boot animation + packages
  (64/64, 4/4 health checks), animation handoff (2/2). Files hash-verified on-device; the served
  launcher hash equals the repository and 25 apps answer `HTTP 200`.
* **Boot mode.** Two normal OS reboots cleared the LPM/charger-mode boot and armed the touchscreen
  (`sec_touchscreen`, `INPUT_PROP_DIRECT`, `sec_ts` IRQ 431, all units active, 0 failed). A recurrence
  was traced to an 11.6 s hardware POWER-key hold; the offline bootmode guard stays `BLOCKED_KERNEL`.
* **Persistence.** The deployed userspace survived a reboot (served launcher hash unchanged).

**Live-tooling fixes (each blocked the deploy):** CRLF frame normalisation; sysfs hex `idVendor`
parsing (Linux console discovery found zero nodes); `MAX_WRAPPER_LEN` raised 480→3800 after measuring
the real tty limit; `chunk_size_for` now returns the largest fitting chunk; `install_script` no longer
reverts every successful install via a stray trailing rollback; group health checks run once per group
rather than inside every file's install; the flash-tool guard no longer matches `pit` inside base64;
`push_bytes` writes idempotent per-chunk part files and verifies the staged hash on-device; the deploy
plan validates `--only` against the full manifest; the apply loop auto-reconnects the console and skips
already-current files (resumable).

**Honest gaps recorded, not hidden:** human touch/audio/button/radio acceptance is `NEEDS_OWNER_TEST`;
`nuxel-portal`/`nuxel-bridge` are deployed but not enabled; the device clock is wrong
(`2026-09-15` vs the real `2026-10-16`); `flatpak` is still absent so NuXtore has no backend.

**New artefacts:** `docs/beta-finalization/live/BASELINE-CAPTURE.md`,
`docs/beta-finalization/live/DEPLOYMENTS.md`, evidence bundles under
`docs/beta-finalization/live/evidence/{baseline,deploy,reboot-verify}-*`.

---

## [v0.5.0-beta-rc1] — 2026-10-16

**Theme:** the alpha hardware bring-up becomes a *maintainable* beta candidate.
The device truth is now recorded per subsystem instead of asserted, the whole
programme runs through a resumable on-disk work queue, and the release gate has a
real test hierarchy, a bounded soak, a reboot policy and a rollback discipline
behind it.

> **This is a beta CANDIDATE (`-rc1`), not a beta release.** The identifier is
> justified because the *release engineering* (queue, gate, soak, rollback,
> capability manifest) now exists and is offline-tested — and because the
> hardware story is honest rather than finished: the phone boots Fedora 43 with
> systemd, the launcher runs on the panel through the Wayland→framebuffer
> bridge, the live console is proven, and the separate subsystems say plainly
> which of them are still unproven. Per-subsystem status is **not** in this file:
> it lives in [`docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md`](docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md)
> (machine-readable twin `.json`, cross-checked against the work queue by
> `tools/beta/validate-capability-manifest.py`). Words like "working" in this
> changelog mean "exists in the repository and passed its offline suite" unless a
> live capture is cited.

### Added — release engineering (this cycle's deliverable, `bg-09`)

- **`tools/beta/run-all-tests.sh` — the release gate.** One command runs every
  offline suite plus the A32 baseline regression guard, prints a per-suite table
  (`ID / TIER / STATUS / OWNER / CHECKS / SECS`) and exits non-zero on any hard
  failure. `CHECKS` is the number of PASS-shaped assertion lines the suite
  printed (a floor, never a coverage claim). `--list`, `--only REGEX`, `--strict`,
  `--external`, `--json -` (pure JSON on stdout, transcript on stderr), `--quiet`.
  The machine summary carries `gate` **and** `raw_gate`, `counts`, every
  `failures[]` entry attributed to its owning group, and `allowances_applied[]`.
- **`docs/beta-finalization/testing/TEST-STRATEGY.md`** — the L1–L6 hierarchy
  (static → unit → integration → UTM VM → live phone → owner physical),
  what each tier may claim, the hardware truth table that constrains those
  claims, and the rule that a metric the phone could not produce is reported
  unproven rather than assumed healthy.
- **`docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md`** + the extended
  harness. The soak is bounded (default ≤ 30 min for an autonomous run, 8 h on
  the device tier) and now measures, in addition to stability: **disk headroom,
  swap pressure, WebKit subprocess count and memory, Phoc CPU/RSS, the
  framebuffer bridge's CPU and commit volume, leftover animation processes,
  runnable-process count and the input-node inventory** — alongside the existing
  reboot / failed-unit / launcher-availability / single-framebuffer-owner /
  stack-CPU / RSS-growth / service-restart / thermal findings. Unreachable
  console ⇒ `BLOCKED_EXTERNAL_RESOURCE`, never a fabricated sample.
- **`tools/beta/rollback.sh`** — record previous hash → stage → verify sha256 →
  atomic install → restart only the smallest affected service → health-check →
  **automatic rollback** on failure. Per-task baselines under
  `/var/lib/nuxel/rollback/<briq-id>/` via the new `--briq` switch.
- **`tools/beta/reboot-policy.sh`** — the pre/post reboot checklist (live console,
  progress saved, logs flushed, systemd ready, no package transaction, known-good
  rollback, bounded reconnect) plus mechanical refusals: no reason, blind repeat,
  repeated reason, previous reboot never returned, no known-good rollback,
  3-reboot budget, and the mode-scoped **three-same-mode-failures** guard. It
  never reboots on its own initiative.
- **`docs/beta-finalization/release/REBOOT-ROLLBACK.md`** and **`ROLLBACK.md`** —
  the discipline, the component map, the backup paths and the rollback routes,
  including the time-bounded auto-rollback rule for security/network changes that
  could cut the only reachable console.
- **`docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.{md,json,schema.json}`**
  and **`tools/beta/validate-capability-manifest.py`** — 41 subsystem entries,
  each naming the work-queue record that authorises it; the validator rejects any
  verdict stronger than the record's (schema validation **and** cross-check).
- **`tools/beta/tests/test-rollback-reboot.sh`** — 22 mocked-failure scenarios
  that prove the rollback really triggers and the reboot path is inert.

### Changed

- **`VERSION`** → `v0.5.0-beta-rc1`, in lockstep with this entry.
- **`tools/beta/soak.sh` / `soak_lib.py`** — the probe emits a second short line
  (`SOAK2`) for the resource/performance metrics, and two sample families are now
  explicitly separated: *gated* (decides the verdict) and *recorded* (warns).
- **`tools/beta/run-all-tests.sh`** — the JSON emitter no longer writes invalid
  JSON for a suite that never ran (`"rc": -` → `null`), the external tier is
  reported as `EXTERNAL`/`BLOCKED_EXTERNAL_RESOURCE` instead of the meaningless
  `EXTERNAL_EXTERNAL`, and cross-group allowances are now **evidence-derived**:
  an entry is honoured only while its owning group still has an unfinished record
  in the work queue, so it stops working by itself when that group lands.
- Legacy alpha-cycle gates (`tools/s10plus/a27/*`) are precondition-gated with a
  `probe:` prerequisite: a missing alpha build artefact or host tool is a loud
  `SKIP` that names the missing piece, never a silent pass and never a fake
  failure.

### Fixed

- **Invalid machine-readable summary** (`"rc": -` for a suite that never ran)
  made `summary.json` unparseable whenever any suite was skipped. Fixed and
  covered by the release-tooling self-test.
- **`tools/beta/tests/test-release-tools.sh`** had a stray `from release_lib
  import` line that made the `release_lib.py` unit block die with a SyntaxError;
  the block now runs.
- **The release-tool self-test asserted the wrong stream**: with `--json -` the
  gate now keeps stdout pure JSON and moves the human transcript to stderr, and
  the test captures the two streams separately.

### Preserved from A32 (do not start over)

The A32 hardware-proven baseline is unchanged and still guarded, as hash pins and
behavioural invariants in `docs/beta-finalization/baseline-protection.json` plus
`tools/beta/regression-guard.sh` (passing in the release gate): Fedora 43 ARM64 +
Samsung Linux 4.14.253 with systemd PID1 and the USB CDC-ACM console, the DECON
framebuffer at 1440×3040, the XRGB8888→Samsung ABGR8888 screencopy translation,
Phoc headless + the Wayland→framebuffer bridge, the original MP4 boot animation
with a single framebuffer owner and receipt-driven handoff, the WebKitGTK Nuxel
Home PWA as the authoritative launcher, the A32 button manager, and the ten-zone
status-bar safe areas.

### Still open / not claimed (see the capability manifest for the full matrix)

- **No subsystem in this release is `VERIFIED_ON_S10PLUS` by this cycle.** The
  live preflight was read-only; the manifest caps every entry at its recorded
  offline/vendor ceiling, and no entry in it claims live verification from this run.
- The touch controller is present but **deliberately not initialised** while
  `androidboot.mode=charger` sets `lpcharge=1` (`sec_ts_init: Do not load driver
  due to : lpm 1`); touch is `BLOCKED_KERNEL` on the boot mode until a normal
  boot is performed, and the finger test is `NEEDS_OWNER_TEST`.
- Wi-Fi enumerates (`brcmfmac`, `wlan0`/`wlan1`, unblocked, **down**) but
  association/DHCP/DNS/reconnect are unproven; Bluetooth is soft-blocked;
  ModemManager reports `No modems were found` despite the Shannon `rmnet*`
  interfaces; `pipewire`, `wireplumber`, `alsa-utils` and `flatpak` are **not
  installed** on the phone.
- There is **no exposed battery-backed RTC** (`timedatectl`: *RTC time: n/a*); the
  device clock reads ~31 days behind the host and that already breaks RPM
  signature verification (`signature is not alive`). Time is therefore reported
  with its uncertainty rather than as a precise value.
- The 8 h device soak, the UTM tiers and every physical acceptance item are
  registered but **not executed** here: the soak and the VM tiers are
  `BLOCKED_EXTERNAL_RESOURCE`, and the physical items are `NEEDS_OWNER_TEST` in
  `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`.
- The release gate is **RED** at the time of this entry for two suites owned by
  another build group (`U-baseline-a32-suite` and `U-boot-s10plus-gates`, both
  needing alpha-cycle build artefacts that the beta build host cannot produce:
  the aarch64 bridge binary and the A5 boot fixture). They are attributed in
  `build/reports/beta-tests/summary.json` as `failures[]`; nothing here hides
  them, and `--strict` reports the raw verdict.

---

---

## [v0.4.0-alpha] — 2026-10-15

**Theme:** the Galaxy S10+ **boots Nuxel** — and the release CI now builds the
exact image that runs on the handset. The earlier "bootloops on the Samsung logo"
status is **superseded**.

### Proven on hardware (SM-G975F), each step with a device marker

| Step | Evidence |
|---|---|
| S-Boot loads and executes the Nuxel ARM64 kernel | S-Boot record + `linux_banner` in the ram console |
| Embedded Nuxel initramfs executes | `NUXEL_MARKER INITRAMFS_EXECUTED` |
| Nuxel `/init` runs, USERDATA discovered | `USERDATA_FALLBACK /dev/sda31`, `USERDATA_DISCOVERED` |
| Fedora ext4 rootfs mounts | `ROOTFS_MOUNTED /dev/sda31 ext4` |
| `switch_root` → Fedora systemd 258 PID 1 | `systemd[1]: systemd 258.11-1.fc43 … arm64` |
| systemd builds its unit graph / services execute / cgroup2 / journald | `Reached target basic.target` (A15); A18 spawn-failure fix |
| Stable boot without spontaneous reset | A15 ran 1892 s (operator reset only) |
| Nuxel renders on the AMOLED panel; spinning penguin | A16 first light on the DECON fbdev path |
| Original MP4 boot animation, 24.00 fps, 0 skipped frames | A21/A22 measurements |
| Panel colour order | ABGR_8888 proven from the driver commit path (A23) |
| Interactive live root console over USB | A21 acceptance suite; A24/A25 disconnect survival (HUP-proof, respawning supervisor) |
| Fedora userspace UI process + real framebuffer commit | A24 `UI_STARTED`, `FIRST_FRAME_COMMITTED fbio_pan rc=0` |
| Animation → UI handoff | A24 `ANIMATION_STOP_SIGNALLED`, `PHONE_UI_READY` |
| A25 (single-instance UI + console-owned postboot supervisor) | flashed to BOOT with full 51,718,144-byte SHA-256 readback PASS; boot is the next observation |

### Added

- **`tools/s10plus/build-a25-initramfs.sh`** — builds the A25 initramfs **from
  repo sources** (no local candidate base): freestanding aarch64 binaries
  (`nuxel-ui`, `nuxel-anim-player`, `nuxel-fb-phone`, `nuxel-syscall-probe`),
  static-glibc binaries (`nuxel-console`, `nuxel-hwprobe`, `nuxel-verify`), toybox
  + applets, `/init`, the systemd units, the post-boot supervisor and the pinned
  `libsystemd-shared`. Every member is re-extracted and hash-compared before the
  script reports success.
- **`tools/s10plus/mkinitramfs-cpio.py`** — deterministic newc packer used by the
  builder (works on macOS and Linux; no host `cpio`).
- **`images/s10plus/build-a25-boot.sh`** — the A25 BOOT image pipeline: build the
  initramfs → merge the board DTB (`fdtoverlay`) → **rebuild the kernel with
  `CONFIG_INITRAMFS_SOURCE`** → pack a legacy v1 `boot.img` with the **raw arm64
  `Image`** → gate the result.
- **`tools/s10plus/verify-a25-boot.py`** — fail-closed verifier: container
  structure (delegated to `verify-boot-image.py`, including the partition budget),
  raw (non-gzip) arm64 Image, the initramfs really embedded, the embedded archive
  identical member-by-member to the built one, the pinned systemd payload, and the
  ramdisk copy carrying the same archive.
- **`boot/s10plus/payload/libsystemd-shared-258.11-1.fc43.so`** (+ provenance
  README) — the kernel-4.14 `pidfd_spawn`/`pidref` patched library `/init` installs
  into the Fedora rootfs, SHA-256 pinned (`848149cf…`) by both the payload README
  and `boot/initramfs/init.sh`.

### Changed

- **`.github/workflows/release.yml`**: the S10+ job now builds the A25 image
  (`images/s10plus/build-a25-boot.sh`) instead of the legacy
  `--boot-images-only` `Image.gz` + external-ramdisk boot image; the shared
  initramfs step is now g7power-only; the Fedora 43 ARM64 phone rootfs step is
  unchanged.
- **`tools/verify-artifacts.sh`**: the s10plus branch no longer requires
  `Image.gz`; it requires the A25 contract (`Image-A25` + `initramfs-A25.cpio` +
  `nuxel-beyond2lte-boot.img`) through `tools/s10plus/verify-a25-boot.py`.
- **Docs/README status + scoreboard** updated to the proven state: build system
  58% → 85%, S10+ bring-up 55% → 85%, flashable images 80% → 90%, overall
  ~45–50% → ~60%.
- **Version bump to v0.4.0-alpha** across `VERSION`, README/design/docs, the flash
  guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling and the
  OTA builder.

### Still open (unchanged in kind)

- Touch input: every boot so far was `androidboot.mode=charger` (no touch device).
- Human-visible confirmation of the UI and of the animation colours.
- The Fedora boot graph stalls before `multi-user.target`; `bootreport.txt` now
  instruments which job stalls.
- Phosh/Phoc need DRM/KMS — this 4.14 vendor tree has `# CONFIG_DRM is not set`.
- Moto G7 Power still hangs at a black/flashy screen.

---

## [v0.3.3-alpha] — 2026-10-14

**Theme:** flashing is **proven** on the Galaxy S10+ — the full Nuxel image set
now writes to the handset and verifies on the device. The phone reaches the
Samsung logo and **bootloops**; boot-chain bring-up is the remaining work.

The S10+ **full image set** — the merged-DTB boot image
(`nuxel-beyond2lte-boot.img`) and the Fedora 43 aarch64 phone rootfs
(`nuxel-beyond2lte-rootfs-fedora-phone.img`, real Python / systemd / Phosh /
Phoc RPM binaries) — was written to **BOOT + USERDATA over ADB** and **read back
byte-for-byte** from the device. So flashing/transfer, partition sizing and the
storage handoff are no longer open questions: the device now **bootloops on the
Samsung logo**, which points at S-Boot handoff, kernel bring-up or the root
mount (systemd/init) rather than the flash.

### Added

- **S10+ bootloop debug pack** (`scripts/s10plus-debug-pack/`): a standalone,
  **read-only** observability toolkit (no `adb push`, `dd of=`, `flash`,
  `reboot`, `remount`, `mount`, `wipe` or `setprop`). It captures pstore /
  `/proc/last_kmsg`, TWRP recovery logs, partition/mount maps and an offline
  Android-boot-image + Fedora-rootfs inspection, produces an evidence-based
  `TRIAGE.md`, and ships an opt-in, best-effort redacted share bundle. See
  `docs/BOOTLOOP-DECISION-TREE.md`.
- **`images/s10plus/build.sh --boot-images-only`**: packs the S10+ boot image(s)
  and per-artifact checksums without invoking the (intentionally disabled)
  legacy shared rootfs bake, so the real Fedora rootfs can be built separately.

### Changed

- **The S10+ release job now builds the real image set.**
  `.github/workflows/release.yml` builds the merged board-DTB boot image (with an
  explicit board revision, `NUXEL_S10PLUS_BOARD_REV`) and the Fedora 43 ARM64
  phone rootfs via `images/s10plus/build-phone-rootfs-fedora.sh` in an arm64
  container, instead of the retired `images/s10plus/build.sh --device s10plus`
  path (which now fails closed rather than emit a skeleton/"incorrect-runtime"
  rootfs). Only the `s10plus` job changed; `g7power` is untouched.
- **`tools/verify-artifacts.sh` verifies the S10+ image set for what it is**:
  the merged board DTB, the `ANDROID!` boot image, and the Fedora ARM64 phone
  rootfs (via `tools/s10plus/verify-fedora-phone-rootfs.py --ext4`) — not the
  Plymouth-boot-splash payload that the legacy shared rootfs carried.

### Docs / version

- README status: **S10+ 38% → 55%**, **Flashable images 65% → 80%**, overall
  **~40–45% → ~45–50%**; S10+ row now states flashing is proven and the device
  bootloops on the Samsung logo. `S10PLUS-PROGRESS.md` updated to match.
- **Version bump to v0.3.3-alpha** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests + meson, the
  services, the VM tooling and the OTA builder.

---

## [v0.3.2-alpha] — 2026-10-13

**Theme:** make the release CI build the **same complete rootfs** a local build
does — the boot splash is no longer silently dropped.

Reported symptom: the S10+ rootfs published by CI still held only ~20 MB of
content while a local build's staging tree was ~60 MB. Root cause:
`images/mkrootfs.sh` builds the Plymouth boot theme through
`tools/build-nuxel-boot-theme.sh`, which needs **`ffmpeg`** to extract the
animation frames. `.github/workflows/release.yml` never installed `ffmpeg`, and
that step is deliberately non-fatal, so it logged a warning and continued — the
rootfs shipped without the ~50 MB frame sequence (96 PNGs) and the
`nuxel.plymouth` / `nuxel.script` descriptors. `tools/verify-artifacts.sh`
passed because it never checked for the theme.

Verified against the artifacts: a local rootfs image carries 96 `frame-*.png`
files (99 PNG signatures incl. wallpapers) and a `plymouth/` payload; the
v0.3.1-alpha CI image carried 2 PNGs (wallpapers only) and no `plymouth` payload
at all — i.e. 19.9 MB of non-zero inode data vs ~88 MB locally.

### Fixed

- **CI installs `ffmpeg`.** The Release workflow build dependencies now include
  `ffmpeg`, so `images/mkrootfs.sh` -> `tools/build-nuxel-boot-theme.sh`
  produces the Plymouth theme (96 PNG frames + `nuxel.plymouth` / `nuxel.script`)
  in CI exactly as it does on a dev box. This closes the local-vs-CI rootfs gap.
- **`tools/verify-artifacts.sh` is fail-closed on the boot splash.** For both
  `g7power` and `s10plus` it now requires, inside the ext4 rootfs:
  - `/usr/share/nuxel/boot/nuxel-boot-animation.mp4` (size-checked via `debugfs`,
    must be >= 1 MB), and
  - the generated Plymouth theme
    (`/usr/share/plymouth/themes/nuxel/nuxel.plymouth` + `frame-0001.png`).

  A rootfs that silently lost its theme — the exact v0.3.1-alpha CI failure — is
  now a hard failure instead of a green build.
- **Version bump to `v0.3.2-alpha`** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling
  and the OTA builder. The device `APKBUILD`s and shell/PWA `meson.build`s, which
  the previous bump left at `0.3.0-alpha`, are now in lockstep.

### Notes

- No hardware/boot status changed: still **0 of 3 phones verified booting**.
- The G7 Power rootfs gains the boot splash in CI too (same shared builder), so
  both bring-up phones now ship the full userspace + theme.

---

## [v0.3.1-alpha] — 2026-10-13

**Theme:** make the bring-up rootfs **actually contain a userspace**, and make
the artifact gate stop a near-empty image from ever being published as
"complete".

Reported symptom: the S10+ release archive was only ~21 MB (a 22 MB boot image
plus a 26 MB rootfs holding a **44 KB / 10-file** overlay), while a local build's
rootfs was ~60 MB+. Root cause: `images/mkrootfs.sh` declared every userspace
step but **never called them** — the script was a no-op that exited 0, so every
"rootfs" was only the per-device config overlay.

### Fixed

- **`images/mkrootfs.sh` now actually builds the userspace.** Added the missing
  driver (`main`): clean -> Flatpak/fallback base -> core services -> native apps
  -> security configs -> assets -> Plymouth theme -> directory/permission setup
  -> optional dm-verity image -> summary. Previously none of these ran, so
  `/usr/bin/nuxel-bridge`, `/etc/nuxel/paths.conf`, the AppArmor/nftables/sysctl
  configs and the boot theme were absent from every rootfs image.
- **`tools/verify-artifacts.sh` is now genuinely fail-closed.** It no longer
  accepts an image on a magic number alone:
  - boot images must carry a real kernel + ramdisk + device tree (Android v1
    header sizes must be non-zero) — an empty/placeholder header fails;
  - rootfs images must contain the expected payload (per-device config plus the
    Nuxel userspace core `/usr/bin/nuxel-bridge`), verified by reading the ext4
    contents with `debugfs` — the 44 KB S10+ image that shipped in
    v0.3.0-alpha is now a hard failure;
  - `NUXEL_S10PLUS_UBOOT=1` makes `u-boot-beyond2lte.img` a required artifact.
- **Rootfs images are sized from real content.** The 512 MB minimum floor in
  both device builders, combined with a `resize2fs -M` that cannot always shrink
  a many-small-file filesystem, produced a **512 MB** G7 Power rootfs in CI. The
  floor is now 64 MB and the image is sized from the staging tree (content + 25%
  + slack).
- **The S10+ build no longer reports a phantom `INCOMPLETE`.** U-Boot is a
  mainline-stretch artifact; the supported Phase-1 downstream/heimdall set is
  `boot.img` + `rootfs.img`, exactly as the flash guide documents. U-Boot is
  built when present and only fails the build when explicitly required
  (`NUXEL_S10PLUS_UBOOT=1`).
- **Version bump to `v0.3.1-alpha`** across `VERSION`, README/design/docs, the
  flash guides, PWA/shell manifests, VM tooling and the OTA builder.

### Notes

- **There is no `userdata.img`** by design in Phase 1: the rootfs image *is* the
  userdata payload (G7 Power: shared `userdata`; S10+: `SYSTEM`/`userdata`), so
  the archive ships `nuxel-*-rootfs.img`, not a separate `userdata.img`.
- **`lk2nd` is G7 Power-only** (`msm8953`). The S10+ is Exynos and never uses
  `lk2nd`; its chain is stock `S-Boot` -> (optional `u-boot-beyond2lte.img`) ->
  `nuxel-beyond2lte-boot.img`.
- Device-proprietary vendor blobs (`firmware/*/blobs/vendor-*`) remain
  **unshippable** (gitignored): CI builds the rootfs from repo sources only, so a
  CI image is smaller than a local one that has pulled those blobs. The gate
  verifies the repo-provided payload, not the non-redistributable firmware.

---

## [v0.3.0-alpha] — 2026-10-13

**Theme:** make the release pipeline **fail-closed and genuinely green** for the
two bring-up phones (**G7 Power** `g7power`/ocean and **Galaxy S10+**
`s10plus`/beyond2lte). Every build/release step for both phones now actually
produces its artifact, and the workflow can no longer report success when a
kernel / initramfs / boot image / rootfs is missing or invalid.

### Changed

- **`mustang` (Google Pixel 10 Pro XL) removed from the release workflow** for
  now. The build matrix is `g7power` + `s10plus` only; the `prepare` job filters
  any other device key out (with a warning) and fails if nothing supported is
  requested. `images/build.sh` still refuses non-mustang devices except in the
  new initramfs-only mode.
- **Per-device `sha256sums.txt` in every release archive.**
  `images/g7power/build.sh` and `images/s10plus/build.sh` now emit
  `sha256sums.txt` alongside the images, so the flash guides can verify each
  flashed artifact (`nuxel-ocean-boot.img`, `nuxel-ocean-rootfs.img`, `lk2nd.img`
  / `nuxel-beyond2lte-boot.img`, `nuxel-beyond2lte-rootfs.img`) before writing
  it to the device.
- **Version bump to `v0.3.0-alpha`** across `VERSION`, README/design/docs,
  APKBUILDs, PWA/shell manifests, services and the OTA builder.

### Fixed

- **Release workflow no longer goes green on a failed build.** All
  `continue-on-error: true` flags were removed from the build matrix, the
  "Package device artifact" step is no longer `if: always()` + best-effort, the
  upload step uses `if-no-files-found: error`, and the `publish release` job now
  runs only when the whole build matrix succeeded (`if: needs.build.result ==
  'success'`). A device whose kernel/images fail leaves the run **red** and no
  GitHub Release is created.
- **New strict artifact gate `tools/verify-artifacts.sh`.** After the image
  build, CI verifies (per device) that the kernel `Image.gz` is a real
  gzip-compressed **ARM64 Linux Image** (`0x644d5241`), that the board DTB is a
  valid FDT (`0xd00dfeed`), that the boot image carries the `ANDROID!` header,
  that the rootfs is `ext4` (`0x53EF` superblock magic), and — on G7 Power —
  that `lk2nd.img` is present. Any miss fails the job with `::error::`.
- **S10+ boot image now builds in CI.** The downstream Exynos 9820 tree ships
  only the SoC base DTB (`dts/exynos/exynos9820.dtb`) plus per-revision overlays
  (`dts/samsung/exynos9820-beyond2lte_eur_open_<rev>.dtbo`); the previous build
  looked for a board `.dtb` that is never produced, so `images/s10plus/build.sh`
  aborted with "No beyond2lte DTB found". It now merges base + highest-revision
  overlay into `exynos9820-beyond2lte.dtb` with `fdtoverlay`
  (`device-tree-compiler`) before packing, matching the previously-built local
  artifact byte-for-byte (376101 bytes, rev 26).
- **Shared initramfs is now a first-class step.** `images/build.sh` gained
  `--initramfs-only`, which assembles the device-agnostic initramfs, mirrors it
  to `build/boot-artifact/` and exits 0 — instead of the old "mustang dispatcher"
  invocation that exited 3 whenever the (now-removed) mustang kernel was absent.
- **G7 Power `lk2nd.img` is now built in CI.** New
  `boot/g7power/lk2nd/build-lk2nd.sh` clones `msm8916-mainline/lk2nd` and builds
  `lk2nd-msm8953` with the `arm-none-eabi` toolchain, producing the
  `lk2nd.img` that `images/g7power/build.sh` copies into the release. Without it
  the G7 Power artifact set was silently incomplete.

### Notes

- `g7power` kernel build time varies with runner speed (~25–47 min for the full
  mainline `msm8953` tree: `Image.gz` + `dtbs` + `modules`); both bounds are
  normal. The `s10plus` downstream 4.14 kernel builds in ~15 min.

## [v0.2.2-alpha] — 2026-10-13

**Theme:** pre-release fix on top of v0.2.1-alpha — make the **S10+** and the
**Pixel 10 Pro XL (`mustang`)** kernel builds actually produce an `Image.gz` in
CI. No other behaviour changes; the readiness picture is unchanged.

### Fixed

- **S10+ kernel build (CI).** v0.2.1-alpha forced `CROSS_COMPILE` and dropped
  compiler-unsupported KCFLAGS, but the build still failed on the runner's GCC 13
  because the downstream 4.14 Exynos 9820 tree hard-codes `-Werror` in two places
  a `KCFLAGS` relaxation cannot reach:
  - **per-category promotions** in the top `Makefile`
    (`KBUILD_CFLAGS += $(call cc-option,-Werror=strict-prototypes)` and friends,
    `Makefile:935-947`). GCC's "the more specific option wins, independently of
    order" rule means the generic `-Wno-error` appended via KCFLAGS does **not**
    downgrade them, so the build died on
    `block/blk-crypt.c:213: error: function declaration isn't a prototype
    [-Werror=strict-prototypes]`;
  - **per-directory flags appended after `KBUILD_CFLAGS`** on the cc command
    line — the bcmdhd Wi-Fi driver's
    `DHDCFLAGS += -Wall -Werror -Wstrict-prototypes` → `EXTRA_CFLAGS` →
    `ccflags-y`. That re-enables a general `-Werror`, so the build died on
    `drivers/net/wireless/broadcom/bcmdhd_101_16/wl_android.c:12016: error: the
    comparison will always evaluate as ‘true’ … [-Werror=address]`
    (`cc1: all warnings being treated as errors`).

  `kernel/s10plus/build-kernel.sh` now runs the new
  `tools/kernel-relax-werror.sh`, which strips the `-Werror` /
  `-Werror=<diag>` / `-Werror-<diag>` tokens (and whole
  `$(call cc-option,-Werror=...)` expressions) from the scratch tree's **source**
  Makefiles — leaving `-Wno-error…` untouched and avoiding the kbuild-internal
  `scripts/Makefile.*` feature-probe helpers. `DEFAULT_KCFLAGS` also gains
  `-Wno-error=strict-prototypes`, `-Wno-error=date-time` and
  `-Wno-error=designated-init` (each still probed against the selected compiler
  and dropped if unsupported). Idempotent; the tree is a throwaway clone.
- **Pixel 10 Pro XL (`mustang`) kernel build — patch.** The committed
  `kernel/google-pixel-10-pro-xl/patches/0001-nuxel-phone-features.patch`
  declared `@@ -0,0 +1,108 @@` for a hunk that adds only 107 lines
  (`drivers/nuxel/nuxel-core.c`), so `git apply --check` failed
  (`error: corrupt patch`) and `kernel/build-kernel.sh` aborted with
  `error: patch not applied and does not apply` before it ever configured or
  built. The hunk header is corrected to `@@ -0,0 +1,107 @@`; the patch now applies
  cleanly to the `android16-6.12` GKI common tree.
- **Pixel 10 Pro XL (`mustang`) compiler-diagnostics relaxation.**
  `kernel/build-kernel.sh` now neutralises the GKI tree's global
  `CONFIG_WERROR=y` (which lands in `KBUILD_CPPFLAGS` via
  `scripts/Makefile.extrawarn`) with a probe-checked
  `DEFAULT_KCFLAGS="-Wno-error=parentheses -Wno-error"` — KCFLAGS is appended to
  `KBUILD_CFLAGS`, i.e. *after* the `-Werror`, so it wins — fixing e.g.
  `fs/fuse/dev.c:458: … [-Werror=parentheses]`. It also runs
  `tools/kernel-relax-werror.sh` to strip the per-directory `-Werror`
  (`arch/arm64/kernel/vdso32`, aic7xxx, lpfc). The generated asm/uapi headers are
  now produced before `archprepare` (`make asm-generic archprepare`) so the
  host-tool gate builds on a pristine tree.

### Added

- `tools/kernel-relax-werror.sh` — idempotent helper that strips hard-coded
  `-Werror` from a kernel source tree's Makefiles (used by the `mustang` and
  S10+ kernel dispatchers).

### Changed

- **Repository-wide version bump v0.2.1-alpha → v0.2.2-alpha** in: `VERSION`,
  `README.md`, `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with a
  new 0.2.2-alpha release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`) and the OTA builder (`images/build-ota.sh`).
- `README.md` gains a short *What's new in v0.2.2-alpha* section.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.2-alpha`.
- Historical run logs (under `vm/logs/`) and the point-in-time VM recon report
  (`vm/utm-state-report.md`) are left untouched as record.

---

## [v0.2.1-alpha] — 2026-10-13

**Theme:** pre-release fix on top of v0.2.0 — make the **S10+ kernel build**
succeed in CI. No other behaviour changes; the readiness picture is unchanged.

### Fixed

- **S10+ kernel build (CI / any non-Samsung host).**
  `kernel/s10plus/build-kernel.sh` never overrode the downstream Samsung tree's
  hardcoded toolchain. The Exynos 9820 `Makefile` line 316 sets

  ```
  CROSS_COMPILE ?= $(srctree)/toolchain/gcc-cfp/gcc-cfp-jopp-only/aarch64-linux-android-4.9/bin/aarch64-linux-android-
  ```

  a tree-internal Android GCC that is **not** shipped with the source. A bare
  `make` therefore failed before compiling anything:

  ```
  make[1]: .../aarch64-linux-android-gcc: No such file or directory
  Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not supported by compiler
  make[1]: *** [Makefile:1267: prepare-compiler-check] Error 1
  ```

  which cascaded into `[nuxel-s10plus-build][error] Kernel image not found:
  .../arch/arm64/boot/Image.gz` and an empty `build/out/s10plus/` (the GitHub
  Actions job logged the kernel step as exit 2 and packaged nothing). The
  wrapper now sets `CROSS_COMPILE` (default `aarch64-linux-gnu-`, matching the
  `gcc-aarch64-linux-gnu` package CI installs) and passes it on **every** `make`
  invocation, so the command-line assignment overrides the tree's `?=` default.
  `--cross <prefix>` is now honoured (previously accepted and silently ignored),
  and `--cross ''`/`CROSS_COMPILE=` yields a native aarch64 host build.
- **S10+ kernel build, second toolchain bug: version-specific `KCFLAGS`.**
  With the toolchain path fixed, the build still died at the same
  `prepare-compiler-check` — but no longer because of a missing compiler.
  `DEFAULT_KCFLAGS` contained `-Wno-error=return-mismatch`, and `-Wno-error=<x>`
  is a **hard error** when the compiler has no `-W<x>` (GCC 13 does not know
  `-Wreturn-mismatch`; it is GCC >= 14). The downstream tree appends `$(KCFLAGS)`
  to `KBUILD_CFLAGS` (`Makefile:963`), so the unknown flag made **every**
  `cc-option` probe fail — producing the misleading
  `Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not
  supported by compiler`. The wrapper now probes each relaxation flag against the
  selected compiler (`echo | $(CC) <flag> -c -x c - -o /dev/null`) and keeps only
  the supported ones: GCC 13 drops `-Wno-error=return-mismatch`; GCC 15 keeps it.
  Verified against GCC 13.4 (probe fails before, passes after) and GCC 15.2.

- **S10+ kernel build, third issue: the tree's global `-Werror`.** With the
  probe flag fixed the kernel finally compiled (`CC arch/arm64/...`), then died
  on a real warning promoted to an error:
  `arch/arm64/mm/fault.c: ... error: format '%lx' expects argument of type
  'long unsigned int', but argument 5 has type 'phys_addr_t' ... [-Werror=format=]`.
  The downstream Makefile compiles with a global `-Werror` (`Makefile:428`), so
  any `-Wall` warning is fatal. `DEFAULT_KCFLAGS` now ends with a bare
  `-Wno-error`; because `$(KCFLAGS)` is appended **last** to `KBUILD_CFLAGS`
  (`Makefile:963`), it downgrades the tree's `-Werror` (and its earlier
  `-Werror=<...>` set) back to warnings - while the specific
  `-Wno-error=<diag>` relaxations still cover GCC 14+ default-errors.

### Changed

- **Repository-wide version bump v0.2.0 → v0.2.1-alpha** in: `VERSION`,
  `README.md`, `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with a
  new 0.2.1-alpha release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`), and the OTA builder (`images/build-ota.sh`).
- `README.md` gains a short *What's new in v0.2.1-alpha* section.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.1-alpha`.
- Historical run logs (under `vm/logs/`) and the point-in-time VM recon report
  (`vm/utm-state-report.md`) are left untouched as record.

---

## [v0.2.0] — 2026-10-13

**Theme:** from a single mustang-only scaffold to a **three-target bring-up
repository**, with per-device orchestration, safety gates, consolidated device
docs, and a repository-wide version bump.

> ⛔ **Readiness headline (unchanged in spirit from v0.1.0):** Nuxel is still a
> **design scaffold + code prototype**. It is **not** a flashable phone OS. No
> target has booted Nuxel from a Nuxel-built image, and there is **no verified
> flashable artifact set** for any device.

### Added

- **Multi-device support with explicit selection.** `tools/nuxel-device-select.sh`
  resolves a device key (`--device` > `NUXEL_DEVICE` env > explicit error;
  aliases `s10plus|beyond2lte`, `g7power|ocean`) and every per-device script
  sources it and prints the resolved key before doing any work.
- **Per-device subtrees** for `firmware/`, `kernel/`, `device/`, `boot/`,
  `configs/` and `images/` for all three targets (`google-pixel-10-pro-xl`
  / mustang, `s10plus`, `g7power`).
- **Phase 0 device-inventory templates + build gates:**
  - `docs/g7power-device-inventory.md`
  - `docs/s10plus-device-inventory.md`
  - `docs/pixel10proxl-device-inventory.md`

  Every build/flash/firmware script refuses to run while load addresses or
  firmware filenames are still `PLACEHOLDER`/`UNKNOWN`.
- **G7 Power (Motorola Moto G7 Power, SDM632/msm8953, `ocean`) bring-up:**
  - On-device **stock-evidence** capture bundle —
    `phones/g7power/stock-evidence/` (partitions, props, dmesg, input devices,
    i2c, USB, firmware sysfs, vendor modules, etc.).
  - lk2nd chainloader docs and artifact — `boot/g7power/lk2nd/`.
  - QCDT boot-image packer `tools/build-qcdt-boot.py` (lk2nd-format DT table).
  - Boot-image cmdline patcher `tools/patch-boot-cmdline.py`.
  - Two-phase fastboot flash flow (`boot/g7power/flash.sh`), recovery
    (`boot/g7power/recovery.sh`), boot packer (`boot/g7power/pack-boot-v1.sh`),
    boot config (`boot/g7power/boot-config.txt`).
  - EDL (Qualcomm 9008) unbrick path documented.
  - Bring-up guide: `docs/g7power-bringup.md`; "do it now" checklist:
    `phones/g7power/g7power-go-guide.md`.
- **S10+ (Samsung Galaxy S10+, Exynos 9820, `beyond2lte`) bring-up:**
  - Exynos boot chain docs (S-Boot → U-Boot → Linux), the **no-fastboot**
    reality (TWRP + Download Mode / heimdall), Knox-tripped constraints,
    protected-partition list and anti-cross-flash rules.
  - Flash tooling: `boot/s10plus/flash.sh`, `flash-heimdall.sh`,
    `uboot-chainload.sh`, `pack-boot-v1.sh`, `recovery.sh`,
    `boot/s10plus/boot-config.txt`.
  - Firmware staging: `firmware/s10plus/` (`fetch-vendor-blobs.sh`,
    `gen-manifest.py`, `install-firmware.sh`, `verify-firmware.sh`, vendor
    firmware blob trees).
  - Bring-up guide: `docs/s10plus-bringup.md`; "do it now" checklist:
    `phones/s10plus/s10plus-go-guide.md`.
- **Pixel 10 Pro XL (mustang) prep:** Phase 0 inventory template + gate
  (`docs/pixel10proxl-device-inventory.md`) and reconciliation against the
  multi-device layout.
- **[`CHANGELOG.md`](CHANGELOG.md)** (this file).

### Changed

- **Repository-wide version bump v0.1.0 → v0.2.0** in: `VERSION`, `README.md`,
  `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with
  a new 0.2.0 release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver=0.2.0`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`, `vm/utm-state-report.md`), and the OTA builder
  (`images/build-ota.sh`).
- **README** rewritten around the multi-device reality: a new
  *What's new in v0.2.0* section, a restructured *Project Structure* table
  (`phones/`, `prompts/`), an updated *Honest Status* table (per-target rows,
  per-area scores), corrected documentation links, and per-device "go-guide"
  links.
- Documentation cross-references updated to the new `phones/` layout.

### Fixed

- **G7 Power touchscreen.** Root-caused the "no touch driver" dead end: the
  controller (ILI2117) is handled by mainline **`ili210x`**
  (`CONFIG_TOUCHSCREEN_ILI210X`, OF match `ilitek,ili2117`); the config had
  requested the **nonexistent** `CONFIG_TOUCHSCREEN_ILI2117`, so no driver was
  ever built. Config fixed and kernel rebuilt
  (`kernel/g7power/defconfig`, `configs/g7power/libinput/`).
- **G7 Power lk2nd black-screen packaging bug.** The payload boot image's DT
  region must be an lk2nd-format QCDT v3 table (12-byte header, 40-byte
  entries) — a raw FDT or a 20-byte Qualcomm header fails validation. Fixed via
  `tools/build-qcdt-boot.py` (DTB bytes unchanged; only packaging corrected).

### Moved / reorganised

- Device **documentation bundles** consolidated under [`phones/`](phones/):
  - `g7power/` → `phones/g7power/`
  - `s10plus/` → `phones/s10plus/`
  - `pixel10proxl/` → `phones/pixel10proxl/`
- Loose planning / analysis prompts consolidated under `prompts/`.
- All in-repo references (docs, scripts, APKBUILDs, config READMEs) updated to
  the new paths.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.0`.
- The historical provenance lines that describe an analysis *of the v0.1.0
  tree* (e.g. "Based on: Deep analysis of Nuxel v0.1.0 repo") are intentionally
  left at v0.1.0; run logs under `vm/logs/` are left untouched as historical
  record.

### Readiness assessment — v0.2.0

| Area | Score | Notes |
|---|---|---|
| Design/docs | 78% | Architecture, security model, PWA spec, three device doc bundles |
| Repo structure | 85% | Clean layout; device doc bundles consolidated under `phones/` |
| PWA apps | 45% | Manifests, SWs, JS exist — need integration testing |
| Native GTK apps | 25–35% | C source exists, not proven buildable on aarch64 |
| D-Bus bridge/portal | 30% | Python parses, dev-grade auth, not integration-tested |
| Sandbox/security | 20% | Configs exist, enforcement not wired end-to-end |
| Build system | 20% | Per-device dispatchers + inventory gates; still unproven on hardware |
| Flashable images | 0% | No verified boot artifact set produced |
| Pixel 10 Pro XL (mustang) | 5% | Public mustang Linux is UART/initramfs-level only |
| Galaxy S10+ (beyond2lte) | 10% | Bring-up: device package, gates, docs — no boot yet |
| Moto G7 Power (ocean) | 15% | Bring-up: touchscreen-driver fix, stock evidence, lk2nd/QCDT tooling |
| UTM VM | 25% | Scripts/docs exist, no VM image artifact produced |

**Overall: ~30–35% MVP scaffold. 0% verified flashable OS. ~40–45% patchable VM demo.**

### Still not done (honest gaps)

- **No target has booted a Nuxel-built image.** 0% verified flashable.
- **Phase 0 inventories are empty templates** — load addresses, firmware
  filenames and checksums remain `PLACEHOLDER`/`UNKNOWN` until filled from the
  physical devices. Every build/flash gate therefore stays closed.
- **Sandbox enforcement is not wired end-to-end** (namespaces + seccomp +
  Landlock + AppArmor + nftables configs exist; enforcement is not proven).
- **Native GTK4 apps are unproven on aarch64.**
- **No VM image artifact** is produced by the bootstrap (scripts/docs only).
- **Modem, camera and sensors are deferred** on both bring-up targets.

### Next (v0.3.0 candidates)

1. Fill the G7 Power and S10+ Phase 0 inventories from the real devices.
2. Produce real kernel + lk2nd + boot/rootfs images and attempt first boot.
3. Build a bootable UTM VM image artifact and run Phosh + bridge/portal.
4. Prove the sandbox enforces (namespaces/seccomp/Landlock/AppArmor/nftables)
   in an integration test.

---

## [v0.1.0] — 2026-05-10

**Baseline release: mustang-only design scaffold + code prototype.**

- Architecture blueprint, security model and PWA runtime specification.
- PWA shells (home, mail, calendar, notes, files, camera) with manifests and
  service workers.
- Python D-Bus services (bridge, portal, notifications) and native GTK4 C app
  source.
- Security configuration files (AppArmor, nftables, hardened_malloc).
- Build / flash / sign / recovery scripts as architectural planning material.
- UTM VM testing scripts for early validation.

Status at v0.1.0: ~25–30% MVP scaffold, **0% verified flashable**, ~35–45%
patchable VM demo. See [`docs/repo-audit.md`](docs/repo-audit.md) for the
measured code footprint and [`docs/milestones.md`](docs/milestones.md) for the
programme view.
