# Archive inventory — supplied comparison archives (briq-00b)

**Access tier:** repository-only (no phone, no VM).  **Re-scanned in session 2 — see §7.**
**Measured:** 2026-10-16 15:23–16:00 (Europe/Amsterdam). Real clock, real filesystem.
**Method:** actual filesystem inspection only — `find`, `stat`, `shasum -a 256`, `unzip -l`,
`unzip -p <member> | shasum -a 256`. No archive was extracted into the repository.
**Hard budget:** 22 GiB free on `/System/Volumes/Data` (the volume holding `$WORKSPACE_ROOT`),
measured at 15:54 — see `docs/beta-finalization/preflight/ENVIRONMENT.md`.

Rule applied throughout: an archive is only referenced after it has been *seen on disk*.
Paths named in the mission but not present on disk are recorded as **ABSENT** and dependent
work is marked as degraded — never silently assumed.

---

## 1. Confirmed-present archives

| # | Path | Size (bytes) | mtime (Europe/Amsterdam) | sha256 | Entries | Uncompressed |
|---|------|-------------:|--------------------------|--------|--------:|-------------:|
| 1 | `docs.zip` (repo root) | 1 121 618 | 2026-10-16T15:23:49+02:00 | `427c7bd954cb1e4ab47ff508f53685d959099f6bb44cff2098e3f870d64721b0` | 182 | 5 492 560 B |
| 2 | `scripts.zip` (repo root) | 125 885 057 | 2026-10-16T15:24:02+02:00 | `35a51844b711f986c743b609a83153db9cad2075e3eec8ab11198978cb86cb0e` | 877 | 364 669 631 B |
| 3 | `tools.zip` (repo root) | 2 732 274 | 2026-10-16T15:23:56+02:00 | `98b1adc9b94e66e1c7ae159078dc278de13d8a83aa4417d128c5992d58a5c4eb` | 228 | 8 936 269 B |
| 4 | `/Users/wicked/Downloads/nuxel-main.zip` | 66 280 653 | 2026-10-16T15:22:56+02:00 | `17c15a013983c87febc488a7c6d0014d25e69cf4b9173d507fefb98a11378ffd` | 1826 | 159 773 138 B |
| 5 | `/Users/wicked/Downloads/snekbyte-main.zip` | 22 448 | 2026-10-16T15:11:06+02:00 | `97f27d12942c708a7840ea403ebb4d2b9879ba0c6f02040dfaddc799c001f387` | 32 | 60 298 B |
| 6 | `/Users/wicked/Downloads/snekbyte-main (1).zip` | 22 448 | 2026-10-16T15:21:47+02:00 | `97f27d12942c708a7840ea403ebb4d2b9879ba0c6f02040dfaddc799c001f387` | 32 | 60 298 B |
| 7 | `/Users/wicked/Nuxel/nuxel-main (2).zip` | 14 092 498 | 2026-05-10T12:14:34+02:00 | `38956349aabc3e043e5b5a1896db8e3762ed2cec5e7a67b0c9769758b58db4c9` | 286 | 14 913 476 B |

Total uncompressed for all seven: **553 905 672 B ≈ 528 MiB**.

Raw inspection commands (representative):

```
$ stat -f 'size=%z mtime=%Sm' -t '%Y-%m-%dT%H:%M:%S%z' docs.zip scripts.zip tools.zip
$ shasum -a 256 docs.zip scripts.zip tools.zip
$ unzip -l docs.zip | tail -3          # 182 files, 5492560 bytes uncompressed
$ unzip -l scripts.zip | tail -3       # 877 files, 364669631 bytes uncompressed
$ unzip -l tools.zip | tail -3         # 228 files, 8936269 bytes uncompressed
```

### Top-level listings

* `docs.zip` → `docs/` (+ macOS `__MACOSX/docs/…` resource-fork overlay).
  Subtrees: `docs/incidents`, `docs/s10plus-autonomous-boot-repair` (incl. `BETA-FINALIZER`,
  `BETA-HARDWARE-FINALIZER`, `UTM-LAUNCHER-PORT`, `evidence-a26`, `evidence-a27`,
  `evidence-a27-reset`), `docs/s10plus-bootloop-repair`.
* `scripts.zip` → `scripts/` (+ `__MACOSX`). Subtrees: `scripts/nuxel-adb-flash-pack`,
  `scripts/s10plus-debug-pack` (incl. `captures/…` live-run evidence trees).
* `tools.zip` → `tools/` (+ `__MACOSX`, `tools/__pycache__`).
  Subtree `tools/s10plus/` holding the per-cycle directories `a17 a18 a19 a20 a21 a23 a24
  a25 a26 a27 a28 a29 a30 a31 a32` plus `a24-nuxel-console.c`, `build-a25-initramfs.sh`,
  `check-device-pit.py`, `check-phone-runtime-staging.py`, … **Note: `tools/s10plus/a33` is
  NOT present** (a33 is the current cycle's tree).
* `nuxel-main.zip` → `nuxel-main/` with the full repository skeleton
  (`.github assets boot ci configs design device docs external finish finish2 firmware images
  kernel phones prompts pwa scripts services shell tools vm`) — i.e. the whole repo, not a delta.
* `snekbyte-main.zip` (and the identical `(1)` copy) → `snekbyte-main/`:
  `main.py`, `snekbyte.py`, `requirements.txt`, `src/{config,event_handler,food,game_logic,
  game_loop,game_state,main,poop,snake,ui}.py`, `src/utils/{constants,logger}.py`,
  `tests/test_{core,event_handler,game_logic,game_state,input_handling,rendering,
  rendering_adapter,snake}.py`.
* `/Users/wicked/Nuxel/nuxel-main (2).zip` → `nuxel/` (older, smaller repo skeleton; no
  `ci/`, no `phones/`, no `prompts/`, no `finish/`, different member date — 2026-05-10).

### Cross-check against the live tree (provenance proof)

Three members were streamed out of their archives and hashed **without extracting**:

```
docs.zip        docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/13-RELEASE-NOTES-A32.md
                -> a4bfe968f1c409c3e0233877d6284c369eef263216111a2cad2aaf4b4c24db67
repo copy       -> a4bfe968f1c409c3e0233877d6284c369eef263216111a2cad2aaf4b4c24db67   IDENTICAL

scripts.zip     scripts/s10plus-debug-pack/nuxel-console-host.sh
                -> 9428a1b2ce7cf46a2927d0738ceed4a9084b2579c254f3ae8b14be1e8b74202b
repo copy       -> 9428a1b2ce7cf46a2927d0738ceed4a9084b2579c254f3ae8b14be1e8b74202b   IDENTICAL

nuxel-main.zip  nuxel-main/pwa/nuxel-home/sw.js
                -> d7fd084352f8fafa377d6f0ac28a4dd576fb842d03fd7292924609f6538ded30
repo copy       -> d7fd084352f8fafa377d6f0ac28a4dd576fb842d03fd7292924609f6538ded30   IDENTICAL
```

Conclusion: `docs.zip`, `scripts.zip`, `tools.zip` and `nuxel-main.zip` are **snapshots of this
same repository taken minutes before this run (15:22–15:24)**. They are supplementary
cross-check inputs, not an independent source. Nothing in them may be copied wholesale over
the live tree; the live tree is the source of truth.

---

## 2. Archives named in the mission but absent from disk — **ABSENT**

Searched with `find /Users/wicked -maxdepth 4 -name '<pattern>'` and a full-tree scan of
`$WORKSPACE_ROOT` (excluding `.git/`, `.qq/`, `.codeseeq/` and the `.yarn` package cache).
Nothing matched.

| Mission name | Search patterns tried | Result |
|--------------|-----------------------|--------|
| `docs(8).zip` / `docs (8).zip` | `docs(8).zip`, `docs (8).zip` | **ABSENT** |
| `scripts(7).zip` / `scripts (7).zip` | `scripts(7).zip`, `scripts (7).zip` | **ABSENT** |
| `tools(4).zip` / `tools (4).zip` | `tools(4).zip`, `tools (4).zip` | **ABSENT** |
| "A30/A31/A32 artifact archives" as standalone zips | `*a30*.zip`, `*a31*.zip`, `*a32*.zip` in `/Users/wicked` (depth 4) and the repo | **ABSENT as supplied inputs** — see below |
| `nuxel-main(2).zip` in the Downloads path | mission named it loosely; the file actually lives at `/Users/wicked/Nuxel/nuxel-main (2).zip` | **PRESENT at a different path** (row 7 above) |

**A30/A31/A32 clarification (matters, because it changes a dependency):** the A30/A31/A32
material exists in two *generated* forms inside the workspace, not as supplied archives:

* `tools.zip` carries the per-cycle source trees `tools/s10plus/a30`, `a31`, `a32`;
* the workspace carries the previous cycles' generated bundles
  `build/out/s10plus/a30.zip`, `a31.zip`, `a32.zip`, `a29.zip`, `a28.zip`,
  `build/out/s10plus/debug-candidates/A26.zip` (all gitignored, regenerable).

The authoritative A32 *record* is in-tree at
`docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/13-RELEASE-NOTES-A32.md`
(sha256 `a4bfe968…`, quoted above) and is hash-pinned by briq-00d.

Also present and relevant (not a "supplied archive", recorded so nobody re-discovers it):

| Path | Size | Note |
|------|-----:|------|
| `/Users/wicked/Nuxel/Fedora-Everything-netinst-aarch64-44-1.7.iso` | 1 247 682 560 B | Fedora **44** netinst ISO. Target platform is Fedora **43**; this ISO must **not** be silently used to justify F43 package claims. Not needed for this briQ. |

---

## 3. Per-archive disposition

| Archive | Disposition | Why |
|---------|-------------|-----|
| `docs.zip` | **used — cross-check only** | Byte-identical subset of the live `docs/` tree; used to confirm no documentation was lost between cycles. No extraction. |
| `scripts.zip` | **used — streamed only, NEVER extracted wholesale** | 125 MB / 365 MB uncompressed; contains the live `scripts/s10plus-debug-pack/captures/…` evidence trees that already exist in the workspace. Extraction is forbidden by the 22 GiB budget rule. |
| `tools.zip` | **used — cross-check only** | Supplies `tools/s10plus/a17…a32` provenance; a33 absent. |
| `/Users/wicked/Downloads/nuxel-main.zip` | **used — cross-check only** | Whole-repo snapshot from minutes earlier; the live tree supersedes it. |
| `/Users/wicked/Downloads/snekbyte-main.zip` | **used — handed to the SnekByte port work (bg-07 specialty apps)** | 32 files, tiny; the readable source for "SnekByte — port the original game". Read in place (`unzip -p`), extraction optional. |
| `/Users/wicked/Downloads/snekbyte-main (1).zip` | **not-needed** | Byte-identical duplicate of the previous row (same sha256, single unique hash across both files). |
| `/Users/wicked/Nuxel/nuxel-main (2).zip` | **used — historical cross-check only** | 2026-05-10 skeleton (286 files); useful as an early-history diff basis, never as a source of truth. |
| `docs(8).zip`, `scripts(7).zip`, `tools(4).zip` | **absent** | Not on disk. Any work that hoped to pull newer comparison material from them degrades to "compare against the live tree + `docs.zip`/`scripts.zip`/`tools.zip` snapshots". |
| "A30/A31/A32 archives" | **absent as supplied inputs; present as generated outputs + `tools.zip` subtrees** | Recorded above; no fabricated path referenced. |
| Fedora 44 netinst ISO | **not-needed** | Wrong release for a Fedora 43 target. |

---

## 4. Extraction plan (respects the 22 GiB hard budget)

Facts that drive the plan:

* free space on the volume holding the workspace: **22 GiB** (22 589 932 KiB at 15:54);
* the workspace itself is already **20 GB** (`kernel/` 3.3 G + `build/` 7.9 G +
  `artifacts/` 2.6 G + `backups/` 1.7 G are gitignored, regenerable trees);
* all seven archives together are only ~528 MiB uncompressed, so extraction is not what
  threatens the budget — *careless or repeated* extraction plus large `build/` rebuilds are.

Plan:

1. **Never extract into `$WORKSPACE_ROOT`.** Archives are read *in place*.
2. Prefer streaming single members: `unzip -p <archive> <member> | shasum -a 256`
   (used above) or `unzip -p … > /tmp/<name>`.
3. If a whole tree must be unpacked for a comparison, unpack to
   `/tmp/nuxel-archive-<archive>-<epoch>/` — **never** `scripts.zip` (365 MB uncompressed and
   already resident in the workspace), and always inside a `trap` that removes the directory.
4. Guard every extraction with a pre-flight check, e.g.
   `test "$(df -k /tmp | awk 'NR==2{print $4}')" -gt 8388608` (8 GiB headroom) and abort
   otherwise; re-check free space afterwards.
5. `docs.zip` / `scripts.zip` / `tools.zip` / `nuxel-main.zip` are now **gitignored** (see
   §5) so they can never be committed; they stay on disk as read-only provenance inputs.
6. To reclaim budget if a later briQ needs it (documented, opt-in, destructive — owner's call):
   `build/`, `artifacts/`, `backups/` and `kernel/*/.build/` are all gitignored and
   regenerable by `images/build.sh`, `kernel/build-kernel.sh` and the a-cycle build scripts.
   **Do not** delete them during this run without recording it — the a32 binaries under
   `build/out/s10plus/a32/` are the colour-selftest gate input for briq-00d.

---

## 5. Repository hygiene change made by this briQ

`git status` showed `docs.zip`, `scripts.zip`, `tools.zip` as **untracked and not ignored**
(`git check-ignore` matched none of them) — a 125 MB `scripts.zip` was therefore one
`git add -A` away from entering the history. `.gitignore` gained a narrowly-scoped block
(anchored `/docs.zip`, `/scripts.zip`, `/tools.zip`, `/*.zip`, `.venv/`); see
`docs/beta-finalization/preflight/ENVIRONMENT.md` §9 and
`docs/beta-finalization/BASELINE-PROTECTION.md` §6 for the exact block and its rollback.

---

## 6. Verdicts

| Item | Verdict |
|------|---------|
| Archive discovery + hashing + per-archive disposition | **OFFLINE_TESTED** |
| Cross-check of archive members against the live tree | **OFFLINE_TESTED** |
| `docs(8).zip` / `scripts(7).zip` / `tools(4).zip` / A30·A31·A32 supplied archives | **BLOCKED_EXTERNAL_RESOURCE** (absent on disk; degraded to documented gap) |
| Using the archives as a *content* source for the beta deliverables | **IMPLEMENTED_NOT_DEPLOYED** (inputs identified, extraction deliberately not performed) |

---

## 7. Session-2 re-scan (2026-10-16T17:30Z / 19:30+02:00) — this host carries **no** supplied archive

The bg-00 re-verification ran on a different host from §1–§6 (Fedora Linux 43 x86_64, workspace
`/x/nuxel`).  The supplied comparison archives are **not present on this host at all**, so they are
re-recorded as ABSENT rather than assumed.  Nothing was extracted; nothing was re-hashed from a
stale table.

Exact search performed (raw output: `docs/beta-finalization/preflight/archive-rescan.txt`):

```
$ for p in /x/nuxel /x/nuxel/docs /tmp /x /home/wicked /home/wicked/Downloads /home/wicked/Nuxel /mnt /media /run/media; do
    find "$p" -maxdepth 3 -type f \( -name docs.zip -o -name scripts.zip -o -name tools.zip \
      -o -name 'nuxel-main*.zip' -o -name 'snekbyte-main*.zip' -o -name 'docs(8).zip' \
      -o -name 'scripts(7).zip' -o -name 'tools(4).zip' -o -name '*A30*.zip' -o -name '*A31*.zip' -o -name '*A32*.zip' \) ; done
(no output for any root)
$ find /x/nuxel /home/wicked/Downloads -maxdepth 6 -name '*.zip'
/x/nuxel/build/out/g7power/stock/firmware/RETEU_10.zip
/x/nuxel/build/out/g7power/stock/blankflash/blankflash_from_PDOS29.114-134-2.zip
/x/nuxel/build/out/g7power/stock/blankflash/blankflash_from_QCO30.85-18.zip
```

The three zips that do exist are **Motorola G7 Power stock-firmware/blankflash bundles from an
unrelated earlier bring-up**, not Nuxel inputs; they are gitignored build outputs and were not
opened.

### 7.1 Disposition table (this session)

| # | Archive named by the mission | Where it was in session 1 | On this host | Disposition |
|---|------------------------------|---------------------------|--------------|-------------|
| 1 | `docs.zip` (1 121 618 B) | repo root | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` — tried `/x/nuxel`, `/x/nuxel/docs`, `/tmp`, `/x`, `~/Downloads`, `~/Nuxel`, `/mnt`, `/media`, `/run/media` (depth 3) and a depth-6 `*.zip` sweep |
| 2 | `scripts.zip` (125 885 057 B) | repo root | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` (same search) |
| 3 | `tools.zip` (2 732 274 B) | repo root | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` (same search) |
| 4 | `nuxel-main.zip` (66 280 653 B) | `~/Downloads` | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` |
| 5 | `snekbyte-main.zip` (22 448 B) | `~/Downloads` | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` — **but the genuine snekbyte source is present as a git checkout, §7.2** |
| 6 | `snekbyte-main (1).zip` | `~/Downloads` | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` |
| 7 | `nuxel-main (2).zip` (14 092 498 B) | `~/Nuxel` | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` |
| 8 | `docs(8).zip` / `scripts(7).zip` / `tools(4).zip` | never present | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` (unchanged from session 1) |
| 9 | standalone A30 / A31 / A32 artifact archives | never present | **ABSENT** | `BLOCKED_EXTERNAL_RESOURCE` (unchanged); the A30–A32 *source trees and journals* are in the repository itself (`tools/s10plus/a30…a32/`, `docs/s10plus-autonomous-boot-repair/`), which is what the queue actually reads |

**Impact on the mission:** none of the delivery depends on the archives.  They were supplied as
*comparison snapshots* of this same repository; the repository itself — at HEAD `6ee6a39c`, with
54 work-queue records, the A32 release record and the per-cycle `tools/s10plus/aNN/` trees — is the
authoritative input and it is present in full.  No briQ is blocked by the absence; the comparison
exercise (session 1's three streamed members) is simply not repeatable here and is recorded as such.

### 7.2 Genuine snekbyte source located (new, this session)

`/x/snekbyte` is a **real git checkout of the upstream project**, not an unpacked zip:

```
$ git -C /x/snekbyte rev-parse HEAD
84430528bf0b6c9d0810975e117a3fc9e298ce08
$ git -C /x/snekbyte log -3 --format='%H %ad %s' --date=iso-strict
84430528bf0b6c9d0810975e117a3fc9e298ce08 2025-12-15T03:14:19+01:00 refactor: remove redundant directories and update project name
60ba2d0cdd105b33ec6a04ac4ac181c7a85e8490 2025-12-15T03:02:38+01:00 docs: update README with WoNQ mode and new structure
14691ccce087fb8248b1850b1f05f3f56907d812 2025-12-15T02:57:33+01:00 Merge pull request #1 from illdynamics/feat/improvements
$ git -C /x/snekbyte remote -v
origin  https://github.com/illdynamics/snekbyte.git (fetch/push)
$ git -C /x/snekbyte status --porcelain      # clean
```

Working tree: `main.py`, `snekbyte.py`, `requirements.txt`, `README.md`, `.gitignore`,
`src/{__init__,config,event_handler,food,game_logic,game_loop,game_state,main,poop,snake,ui}.py`,
`src/utils/{__init__,constants,logger}.py`, `tests/test_{core,event_handler,game_logic,game_state,
input_handling,rendering,rendering_adapter,snake}.py`.

| Path | sha256 | Path | sha256 |
|------|--------|------|--------|
| `README.md` | `ccd558434e8e9078…` | `src/snake.py` | `bb5011ce42fd697a…` |
| `main.py` | `536efa4ff990c97e…` | `src/poop.py` | `85d60475da41a8f5…` |
| `snekbyte.py` | `2396dc85d6a0da3a…` | `src/ui.py` | `fd066d55f3eaaf4a…` |
| `src/game_logic.py` | `95492eee4473dc77…` | `src/game_loop.py` | `c24d185c926c7a4d…` |
| `src/game_state.py` | `4064780bd4cdf6f3…` | `src/config.py` | `5bb47077061490df…` |
| `src/event_handler.py` | `1e88c41a4eb70095…` | `src/utils/constants.py` | `7de4fb7cf9875b2e…` |

Full hashes are in the raw capture; the two invariants worth stating here are the ones the snekbyte
briQ (`07d-snekbyte`) needs:

* the **`poop.py` + `game_logic.py` pair is present**, i.e. the Poop-obstacle mechanic and the
  Poop-o-meter of the upstream game, plus `README.md`'s WoNQ-mode documentation — this is the
  genuine source, **not** a generic Snake clone, and the mission explicitly forbids substituting one;
* the tree is a **clean checkout** (`git status` empty), so a port can cite an exact revision,
  `84430528bf0b6c9d0810975e117a3fc9e298ce08`, as its provenance.

The tree is *outside* the repository (`/x/snekbyte`), so `07d-snekbyte` must **vendor or copy** the
sources under `TARGET_PATH` before packaging — referring to a path outside the repo would not be a
reproducible deliverable.  That is recorded here so the snekbyte briQ does not have to rediscover it.

### 7.3 Baseline facts the queue relies on, from the A30–A32 journals in-tree

Read from `docs/s10plus-autonomous-boot-repair/` (`STATUS.md`, `NEXT-ACTION.md`,
`BETA-HARDWARE-FINALIZER/{00-BASELINE.md,01-TOUCHSCREEN-ROOT-CAUSE.md,02-INPUT-PIPELINE-TRACE.md,
03-UTM-LAUNCHER-PARITY.md,04-WALLPAPER-AND-COLOR-PIPELINE.md,05-STATUSBAR-SAFE-ZONES.md,
06-POWER-BUTTON.md,07-VOLUME-AND-AUDIO.md,08-BIXBY-MAPPING.md,09-ANIMATION-REGRESSION.md,
10-LIVE-DEPLOYMENTS.md,11-BETA-ACCEPTANCE.md,12-REMAINING-HARDWARE-BLOCKERS.md,
13-RELEASE-NOTES-A32.md)`, `A26-*.md`, `DEVICE-OBSERVATIONS.md`, `FRAMEBUFFER-OWNERSHIP.md`:

1. **Fedora userspace works on the handset.** A26 repaired the systemd boot graph *on the running
   phone*; `systemctl is-system-running` returned `running` for the first time. The three root
   causes were all `ENOSYS` on Samsung Linux 4.14.253 (no `pidfd_open`, Linux 5.3): systemd-userdbd
   cannot start; `dbus-broker-launch` dies in `launcher_fork` (⇒ the system bus uses
   **`dbus-daemon`**); `systemd-udevd` cannot create worker objects and was **masked** after a
   17 723-process event storm — devtmpfs supplies the nodes Nuxel needs. These are persisted in
   `tools/s10plus/a26/nuxel-rootfs-fixes.sh` and wired into
   `images/s10plus/build-phone-rootfs-inside-fedora.sh`, i.e. **not** phone-only hotfixes.
2. **The 4.14 kernel is the hard ceiling**, and it shows up everywhere the later bands look:
   no DRM/KMS (no `/dev/dri`, hence Phoc-headless + Wayland→framebuffer bridge, *not* native
   accelerated Phosh), no sd-event `pidfd` child watcher, no cgroup-BPF device control (confirmed
   again live in this session's journal, §13.17 of the preflight), and no upstream ModemManager
   support for the Shannon LTE modem.
3. **Touch was proven present in a NORMAL (not charger) boot** (A26: device present with multitouch
   capabilities read). The A32 notes then fixed the normal-boot charger/lpcharge interaction that
   had kept `sec_ts` from arming. The observed P0 condition in this session (`androidboot.mode=
   charger` ⇒ `sec_ts_init: Do not load driver due to : lpm 1`) is the same mechanism, one boot
   mode later — it is **not** a regression of A32's fix, and no userspace hack can undo it.
4. **Display/animation chain is proven and receipt-driven**: original MP4 animation, ABGR_8888,
   zero skips (A21–A23); the animation stops and the UI takes panel ownership (A26/A32); the
   handoff is now recorded as explicit receipts (`BOOT_WAIT_LAUNCHER → LAUNCHER_READY →
   ANIMATION_STOP_REQUESTED → ANIMATION_STOP_CONFIRMED → LAUNCHER_DISPLAY_OWNER`) — read back from
   the device in this session and quoted in the preflight (§13.16).
5. **Wallpaper/colour**: the A32 XRGB8888→DECON-ABGR8888 repair is authoritative and guarded
   (INV-2); the canonical wallpaper lives once in `assets/nuxel-background.png`
   (`sha256 6e337ef2d506a167…`) and per-app copies are build-time artefacts of
   `tools/dedupe-assets.sh` — the exact step this group re-ran in this session (§13.19).
6. **Buttons/Bixby/volume** were mapped in A32 (power short = screen toggle, Bixby = Terminal,
   ALSA volume) with the single-owner rule for `gpio_keys` (INV-4); the live device shows the
   button manager running and a real `source=bixby(short) action=open-terminal` receipt.
7. **The rules that must not drift** (all still stated in `NEXT-ACTION.md` and kept by this group):
   never write BOOT/USERDATA/EFS/SEC_EFS/PIT/DTBO/bootloader from the live session; never open
   `/dev/fb0` from a diagnostic (closing it powers the AMOLED down); never run a second framebuffer
   client; drive the UI through its own command FIFO; **every live fix must land in the rootfs
   builder the same cycle it is made** — no phone-only fixes. This group added no device-side
   change at all, so nothing needed to be landed.

### 7.4 Verdicts for this session

| Item | Verdict |
|------|---------|
| Archive re-scan performed against the current host with exact search roots | **OFFLINE_TESTED** |
| All seven supplied archives + the three `(N).zip` variants | **BLOCKED_EXTERNAL_RESOURCE** (absent; search paths recorded) |
| Genuine snekbyte source identified, revision + clean-tree status + hashes recorded | **OFFLINE_TESTED** |
| A30–A32 journal baseline facts re-read from the in-tree records | **OFFLINE_TESTED** (documentation review; nothing re-run) |
| Using the archives as a content source | **DEFERRED** — no archive on this host; the repository itself is the source of truth |
