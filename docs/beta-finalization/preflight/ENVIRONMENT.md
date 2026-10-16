# Environment preflight — measured, not assumed (briq-00a)

**Access tier:** repository-only (no phone, no VM required for this briQ).
**Measured at:** 2026-10-16T15:59:31+02:00 (2026-10-16T13:59:31Z, epoch 1792159173).
**Clock:** real host clock, `TZ=Europe/Amsterdam` → **CEST (+02:00)**. Nothing in this document
is a fabricated timestamp; every value came from a command whose output is quoted below.

> **Drift caveat (important).** This run is a *parallel* build: eleven other build groups are
> writing into this same working tree at the same time. `git ls-files --others` grew from
> **776 (15:54)** → **971 (15:57)** → **1024 (15:59:31)** while this preflight ran, entirely
> from other groups' new files (`pwa/nuxel-apps/*/icons/`, `configs/networkmanager/…`).
> Counts below are a timestamped *snapshot*, not a constant. Anything that must be stable
> (the A32 protected assets) is hash-pinned in `docs/beta-finalization/BASELINE-PROTECTION.md`.

---

## 1. Repository revision and working-tree state

```
$ git rev-parse HEAD
de45917d6d9b2ebaf3f8b81467484637807f2ad0
$ git rev-parse --abbrev-ref HEAD
main
$ git rev-parse HEAD^{tree}
32ab6ad06298a59205bd99797db5d78954611f61
$ git log -1 --format='%H%n%an%n%ad%n%s' --date=iso-strict
de45917d6d9b2ebaf3f8b81467484637807f2ad0
Ricky van Poppel
2026-10-16T15:49:20+02:00
qq: update .gitignore
$ git status --porcelain | head
?? .qonqrete-chat-task-20261016-154919-282d6fbe.md
?? .venv/
?? docs.zip
?? scripts.zip
?? tools.zip
$ git worktree list
/Users/wicked/x/nuxel de45917 [main]
$ git branch -a
* main
  remotes/origin/HEAD -> origin/main
  remotes/origin/main
$ git stash list
(empty)
```

| Property | Value |
|----------|-------|
| HEAD | `de45917d6d9b2ebaf3f8b81467484637807f2ad0` (`qq: update .gitignore`, 2026-10-16T15:49:20+02:00) |
| Branch | `main` (up to date with `origin/main`) |
| HEAD tree | `32ab6ad06298a59205bd99797db5d78954611f61` |
| Tracked files | **1505** |
| Modified-tracked files | **0** — no tracked file had uncommitted edits at 15:59:31 |
| Staged files | **0** |
| Untracked files | **1024** (772 of them inside `.venv/`; 252 are parallel-group work in progress) |
| Untracked bytes | 142 300 168 B ≈ 135.7 MiB (772 `.venv` files dominate; the three supplied zips add 129 738 949 B) |
| Extra worktrees / submodules | none (single worktree, no `.gitmodules`) |
| Stashes | none |
| Last 5 commits | `de45917 qq: update .gitignore` · `314b92a fixes` · `04a5b35 A32: report the status-bar safe-zone verdict only when it changes (…)` · `0102b60 A32 BETA HARDWARE FINALIZER: touchscreen alive (normal-boot fix), launcher parity + cache invalidation, DECON colour conversion, ten-zone cutout safe areas, phone buttons, full boot animation` · `7aa54da A31 docs: …` |

The A32 commit `0102b60` is the beta floor this whole mission must not regress; its protected
assets are registered in `docs/beta-finalization/BASELINE-PROTECTION.md`.

---

## 2. Host platform

```
$ uname -a
Darwin infranux 24.6.0 Darwin Kernel Version 24.6.0: Tue Jul 21 20:51:05 PDT 2026;
root:xnu-11417.140.69.711.44~1/RELEASE_ARM64_T6000 arm64
$ sw_vers
ProductName:		macOS
ProductVersion:	15.7.9
BuildVersion:	24G830
$ date
Fri Oct 16 15:54:04 CEST 2026
```

Apple Silicon (`arm64`, T6000), macOS 15.7.9 (24G830). The host is the **build/orchestration
host only** — it is not the target. Notably, the A32 aarch64 ELF binaries built for the phone
execute *directly on this host* (see §9), which is how the colour-conversion selftest runs
without touching the UTM guest.

---

## 3. Disk and the 22 GiB hard budget

```
$ df -k /Users/wicked/x/nuxel | tail -1
/dev/disk3s1   971350180 928318496  22498592    98% 5563663 225899320    2%   /System/Volumes/Data
$ df -h /Users/wicked/x/nuxel | tail -1
/dev/disk3s1   926Gi   885Gi    22Gi    98%   /System/Volumes/Data
```

| Property | Value |
|----------|-------|
| Volume | `/dev/disk3s1` → `/System/Volumes/Data` (also holds `/tmp`) |
| Total | 971 350 180 KiB ≈ 926 GiB |
| Used | 928 318 496 KiB ≈ 885 GiB |
| **Available** | **22 498 592 KiB ≈ 21.5 GiB** (22 GiB shown by `df -h`) |
| Capacity | 98 % — treat as a **HARD BUDGET** |

Consuming trees inside the workspace (measured 15:56, `find … | wc -l` + `du -sh`):

| Tree | Files | Size | Class |
|------|------:|-----:|-------|
| `kernel/` | 103 478 | 3.3 G | **generated** (shallow clones + compiled trees, gitignored `kernel/*/.build/`) |
| `build/` | 1 074 | 7.9 G | **generated** (`build/out/…` cycle bundles, gitignored) |
| `artifacts/` | 18 | 2.6 G | **generated** (VM disk images, gitignored) |
| `backups/` | 61 | 1.7 G | **generated/local** (gitignored) |
| `scripts/` | 679 | 349 M | source + captured evidence (tracked) |
| `boot/` | 157 | 205 M | source + generated `boot/boot.img/…` (partly gitignored) |
| `finish2/` | 35 | 17 M | scratch (gitignored trees) |
| `tools/` | 174 | 8.9 M | **source** |
| `docs/` | 139 | 5.5 M | **source** |
| `assets/` | 2 | 6.4 M | **source** (canonical media) |
| `pwa/` | 335 | 41 M | **source** |
| `firmware/` | 97 | 41 M | source manifests + pulled blobs (blobs gitignored) |
| `vm/`, `shell/`, `services/`, `configs/`, `images/`, `device/`, `phones/`, `prompts/`, `design/`, `ci/`, `external/`, `finish/` | 3–68 each | 84 K–2.8 M | **source** |

Whole-repo on-disk size: **20 G** (`.git` itself is only 40 M).

**Budget rules that follow** (also written into `ARCHIVE-INVENTORY.md` §4):
do **not** unpack `scripts.zip` (125 MB packed / 365 MB unpacked) or `nuxel-main.zip` (66 MB)
into the repository; read archives in place with `unzip -p` or extract to `/tmp` with an
8 GiB headroom pre-check. Never delete `build/out/s10plus/a32/` — it is the colour-selftest
input for the regression guard.

**Phone filesystem free space:** **NOT MEASURED** — the phone console was not reachable
(§6). Recorded as a gap rather than guessed.

---

## 4. Tool inventory actually present

```
$ command -v <tool>                                  # per-tool probe
python3                      /usr/local/bin/python3   Python 3.11.9
adb                          /opt/homebrew/bin/adb    Android Debug Bridge 1.0.41 (37.0.1-15733141)
podman                       /opt/homebrew/bin/podman 6.1.4 (machine: podman-machine-default, applehv, 6 cpu / 8 GiB / 100 GiB, last up 2 days ago)
podman-remote                /opt/homebrew/bin/podman-remote
docker                       /opt/homebrew/bin/docker 29.9.0
qemu-aarch64-static          ABSENT
aarch64-linux-gnu-gcc        /opt/homebrew/bin/aarch64-linux-gnu-gcc  GCC 15.2.0
clang                        /usr/bin/clang           Apple clang 17.0.0 (clang-1700.6.3.2)
gcc                          /usr/bin/gcc             (Apple clang)
make                         /usr/bin/make            GNU Make 3.81
git                          /opt/homebrew/bin/git    2.56.0
jq                           /usr/bin/jq              1.7.1-apple
unzip                        /usr/bin/unzip          UnZip 6.00 (Apple)
zip                          /usr/bin/zip
shasum                       /usr/bin/shasum          6.02   (sha256 verified below)
sha256sum                    /sbin/sha256sum
node                         ~/.nvm/versions/node/v20.20.2/bin/node  v20.20.2
utmctl                       /Applications/UTM.app/Contents/MacOS/utmctl   present (UTM is running)
```

| Capability | Present? | Consequence for this mission |
|-----------|----------|------------------------------|
| Python 3 | ✅ 3.11.9 | all `tools/beta/*.py` and `tools/s10plus/**/*.py` run natively |
| Node.js | ✅ v20.20.2 | the A32 status-bar / launcher-registry JS tests actually execute (not skipped) |
| `adb` | ✅ binary, but **no device attached** | `adb devices -l` → empty list; adb-reachable phone = **BLOCKED_EXTERNAL_RESOURCE** |
| Podman | ✅ 6.1.4, applehv machine up | usable for aarch64 containers, but A32 deliberately builds on the UTM guest instead ("the podman/gvproxy cross-build path is deliberately NOT used — measured unstable on this host", `tools/s10plus/a32/build-a32.sh`) |
| `qemu-aarch64-static` (binfmt) | ❌ **ABSENT** | host-side `/proc/sys/fs/binfmt_misc` does not exist (macOS); no binfmt-based aarch64 emulation. Not needed: aarch64 ELFs execute natively here (§9) |
| Cross toolchain | ✅ `aarch64-linux-gnu-gcc` 15.2.0 | offline static compilation is possible without the VM |
| UTM + VM | ✅ running | the `VERIFIED_IN_VM_ONLY` evidence channel is available (§7) |
| Android build tools | n/a | never required — this mission does not build Android |

---

## 5. Reachability probe: UTM VM (evidence channel)

```
$ pgrep -fl UTM | head -3
19264 /Applications/UTM.app/Contents/MacOS/UTM
     78576 … QEMULauncher … -machine virt -accel hvf … -name nuxelaarch64phosh
$ arp -an | grep 192.168.64
? (192.168.64.3) at 52:54:0:a1:6a:6b on bridge100 ifscope [bridge]
$ nc -z -G 4 192.168.64.3 22 ; echo $?
0
$ ssh -o BatchMode=yes -o ConnectTimeout=8 nuxel@192.168.64.3 'uname -sm; cat /etc/fedora-release; df -h / | tail -1'
Linux aarch64
Fedora release 43 (Forty Three)
/dev/vda3        38G   14G   25G  36% /
```

The UTM guest `nuxel-aarch64-phosh.utm` is **up and reachable** at `nuxel@192.168.64.3`,
running **Fedora 43 aarch64** with 25 G free on `/`. This is the reference launcher truth
(WebKitGTK + Phoc + Wayland→framebuffer bridge) and the `VERIFIED_IN_VM_ONLY` channel.
This briQ does not use it beyond the probe; VM parity runs belong to the VM-parity group.

---

## 6. Reachability probe: the physical Galaxy S10+ (live USB console)

```
$ adb devices -l
List of devices attached
                                          <- empty: no adb device, no adb access
$ ls -la /dev/tty.usb* /dev/cu.usb*
crw-rw-rw-  1 root  wheel  0x9000007 Oct 16 15:21 /dev/cu.usbmodem201
crw-rw-rw-  1 root  wheel  0x9000006 Oct 16 15:21 /dev/tty.usbmodem201
$ lsof /dev/tty.usbmodem201
(no process held the device)
$ stty -f /dev/tty.usbmodem201 115200 cs8 -cstopb -parenb   # rc=0
$ timeout 6 cat /dev/tty.usbmodem201 | head -c 2000
                                          <- 0 bytes in 6 s
$ bash scripts/s10plus-debug-pack/nuxel-console-host.sh --run 'uname -a; df -h /; free -m'
# console /dev/cu.usbmodem201
                                          <- no reply within 30 s (bounded run, then killed)
```

Interpretation, stated conservatively: the CDC-ACM console **device node exists** (something
is enumerated on the USB port), but the Nuxel console **did not answer** a bounded read at
115200 and did not answer the console-host probe at 9600. Therefore:

* live phone access = **BLOCKED_EXTERNAL_RESOURCE** for this run;
* the phone's filesystem free space = **NOT MEASURED**;
* no on-device command was run, nothing was written to the device, and no reboot was attempted.
  (Mission rule honoured: no blind reboots, no flashing, no raw-partition writes of any kind.)

Owner-facing follow-up for the manual proof checklist (not a blocker for repository work):
power the handset into Nuxel normally, confirm "Nuxel S10+ Live Console" enumerates, then run
`bash scripts/s10plus-debug-pack/nuxel-console-host.sh --run 'df -h /; free -m; systemctl --failed'`.

---

## 7. Top-level tree classification (source vs generated vs metadata)

| Path | Class | Tracked? | Notes |
|------|-------|----------|-------|
| `assets/`, `configs/`, `device/`, `docs/`, `firmware/` (manifests), `images/`, `phones/`, `prompts/`, `pwa/`, `scripts/` (scripts + captured live-run evidence), `services/`, `shell/`, `tools/`, `vm/`, `design/`, `ci/`, `external/`, `finish/` | **source** | yes | the repository proper; `tools/s10plus/aNN/` are per-cycle source trees |
| `build/`, `artifacts/`, `backups/`, `finish2/tree*/`, `kernel/*/.build/`, `boot/boot.img/*.img`, `*.qcow2` | **generated / local** | no (gitignored) | regenerable; carve-out for the 22 GiB budget — see §3 |
| `docs.zip`, `scripts.zip`, `tools.zip`, `.venv/`, `.qonqrete-chat-task-*.md`, `yolo*.md`, `*.ms` | **local / non-source inputs** | no (now gitignored, §10) | supplied comparison archives + throwaway session outputs |
| `.git/` | metadata | — | repo metadata, 40 M |
| `.qq/`, `.codeseeq/` | **QonQrete/pipeline metadata — READ ONLY** | no | Never written to by this agent; receipts go only to `RECEIPT_PATH` |
| `.scratch/` | local scratch | no | unpacked kernels/images for boot experiments |
| `S10PLUS-*`, `*-flash-guide*.md`, `heim.md`, `35b.ms`, `fb.md` | source-ish notes | partly | legacy top-level notes; untouched by this briQ |

---

## 8. Frozen baseline evidence: the A32 gate runs green right now

```
$ bash tools/s10plus/a32/tests/run-tests.sh ; echo "EXIT=$?"
== A32 offline tests ==
-- colour conversion (the real bridge binary, aarch64: run on the UTM guest)
PASS red   src=0x00ff0000 got=0xff0000ff want=0xff0000ff
PASS green src=0x0000ff00 got=0xff00ff00 want=0xff00ff00
PASS blue  src=0x000000ff got=0xffff0000 want=0xffff0000
PASS white src=0x00ffffff got=0xffffffff want=0xffffffff
PASS black src=0x00000000 got=0xff000000 want=0xff000000
PASS alpha forced opaque on every channel pattern
-- input keycode bitmap decode
decoded keys: [114, 115, 116, 703]
PASS gpio_keys key set matches the measured EVIOCGBIT output
PASS key 114 = VOLUMEDOWN present
PASS key 115 = VOLUMEUP present
PASS key 116 = POWER present
PASS key 703 = assistant/Bixby present
-- status-bar safe zones      (15 assertions, all PASS)
-- launcher registry         (14 assertions, all PASS)
-- wallpaper asset
PASS assets/nuxel-background.png sha256=6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
PASS pwa/nuxel-home/assets/nuxel-background.png sha256=6e337ef2… (identical)
PASS style.css background-image = ../assets/nuxel-background.png
-- button manager / host sources parse
PASS present nuxel-button-manager.c
PASS present nuxel-pwa-host.c
== 0 failing suite(s) ==
EXIT=0
```

Runtime ≈ 0.5 s, exit code **0**, **0 failing suites**, 2026-10-16 15:5x. This is the frozen
gate that `tools/beta/regression-guard.sh` re-runs. Note `file build/out/s10plus/a32/nuxel-wl-fb`
→ `ELF 64-bit LSB executable, ARM aarch64 … dynamically linked` **executes natively on this
host**, so the colour-selftest leg does not depend on the VM being up.

---

## 9. Repository hygiene change made by this preflight (and its rollback)

`git check-ignore -v docs.zip scripts.zip tools.zip .venv` matched **nothing** — the three
supplied archives (129.7 MB together) and a 772-file virtualenv were untracked *and
unignored*, i.e. one `git add -A` away from being committed. `.gitignore` therefore gained this
narrowly-scoped, anchored block (appended, nothing else reordered):

```
# --- Supplied comparison archives + local virtualenv (preflight briq-00a) ----
# docs.zip / scripts.zip / tools.zip are read-only provenance inputs supplied for
# the beta finalization run (scripts.zip alone is 125 MB).  They are inspected in
# place / streamed with `unzip -p` and must never enter the repository history.
/docs.zip
/scripts.zip
/tools.zip
/*.zip
.venv/
```

Rollback: delete those six lines (`git checkout -- .gitignore` would revert to `de314b92…`'s
version). Tracked-file impact: **none** — no tracked file changed.

---

## 10. What was deliberately NOT measured

| Not measured | Why | Marked as |
|--------------|-----|-----------|
| Phone filesystem free space / `systemctl --failed` / kernel ring | USB console enumerated but did not answer; adb has no device | BLOCKED_EXTERNAL_RESOURCE |
| Any on-device touch / audio / Wi-Fi behaviour | out of this briQ's access tier, owner-only in any case | NEEDS_OWNER_TEST (downstream) |
| Fedora 43 package availability claims | belongs to the userspace-completion group (verified against real repo metadata there) | not claimed here |
| `docs(8).zip`, `scripts(7).zip`, `tools(4).zip`, standalone A30/A31/A32 zips | absent on disk — see `ARCHIVE-INVENTORY.md` §2 | BLOCKED_EXTERNAL_RESOURCE |
| Per-file hashes of all 1826 members of `nuxel-main.zip` | 22 GiB budget + no need; three members were streamed and hashed instead | OFFLINE_TESTED (sampled) |

---

## 11. Verdicts

| Item | Verdict |
|------|---------|
| Git revision, branch, tree, dirty/untracked state captured | **OFFLINE_TESTED** |
| Host tool inventory captured (Python, adb, podman, cross-gcc, node, UTM) | **OFFLINE_TESTED** |
| Disk budget measured and recorded as a hard constraint (22 GiB) | **OFFLINE_TESTED** |
| Top-level tree classified source / generated / metadata | **OFFLINE_TESTED** |
| A32 baseline gate executed (exit 0) | **OFFLINE_TESTED** |
| `.gitignore` hardening for the supplied archives | **IMPLEMENTED_NOT_DEPLOYED** (file edit is on disk; nothing is deployed to the phone) |
| Phone console + phone free-space measurement | **BLOCKED_EXTERNAL_RESOURCE** |
| UTM VM reachability | **VERIFIED_IN_VM_ONLY** (probe only; no parity claim made here) |
| Anything requiring the handset in a human's hands | **NEEDS_OWNER_TEST** |

---

## 12. Addendum — re-measure after the four repository-foundation briQs landed

Re-measured at the end of bg-00 (real clock, `TZ=Europe/Amsterdam`): **2026-10-16T14:11:40Z →
14:11:52Z (16:11:40 → 16:11:52 +02:00)**.  The parallel build groups kept writing during this
window, which is exactly why the values below are quoted with a timestamp.

```
$ date -u '+%Y-%m-%dT%H:%M:%SZ'            -> 2026-10-16T14:11:40Z
$ git rev-parse HEAD                       -> de45917d6d9b2ebaf3f8b81467484637807f2ad0   (unchanged)
$ df -k /Users/wicked/x/nuxel | tail -1
/dev/disk3s1 971350180 929596660 21220428 98% 5632022 212204280 3% /System/Volumes/Data
$ bash tools/s10plus/a32/tests/run-tests.sh ; echo EXIT=$?
== 0 failing suite(s) ==                    EXIT=0
$ bash tools/beta/regression-guard.sh --json
{"tool":"regression-guard","verdict":"PASS","pass":44,"fail":0,"warn":4,"info":2,
 "warned_invariants":"INV-1-launcher-cache-invalidation INV-1-launcher-cache-invalidation
                      INV-3-ten-zone-safe-areas INV-3-ten-zone-safe-areas"}
$ bash tools/beta/tests/test-regression-guard.sh
== 0 failing self-test(s), 11 passing ==
$ python3 tools/beta/tests/test_workqueue.py
== 0 failing case(s), 27 passing ==
$ python3 tools/beta/workqueue.py verify-schema --json
{"tasks": 54, "ok": true, "errors": [], "verified_on_s10plus": []}
$ date -u '+%Y-%m-%dT%H:%M:%SZ'            -> 2026-10-16T14:11:52Z
```

| Property | 15:54 preflight | 16:11 end of bg-00 | Note |
|----------|-----------------|--------------------|------|
| `HEAD` | `de45917` | `de45917` | unchanged: bg-00 is repository-only and commits nothing |
| Free space | 22 498 592 KiB (21.5 GiB) | 21 220 428 KiB (20.2 GiB) | 1.2 GiB consumed by the eleven parallel groups' in-flight work; still inside the hard budget |
| Untracked/ignored inputs | archives untracked **and unignored** | archives + `.venv` now ignored (`git check-ignore -q` passes for all four) | see §9 |
| A32 gate | exit 0 | exit 0 | still green |
| Baseline regression guard | did not exist yet | `PASS=44 FAIL=0 WARN=4 INFO=2` | see `docs/beta-finalization/BASELINE-PROTECTION.md`; the 4 WARNs are soft pins/drift on files owned by `bg-02` (safe-zone engine + its suite), which is mid-flight |
| Work queue | did not exist yet | 54 tasks, schema valid, nothing claiming `VERIFIED_ON_S10PLUS` | `docs/beta-finalization/WORK-QUEUE.md` |

Two honest corrections recorded because this preflight's own discipline demands them:

1. **Free space is a moving number.** Any briQ that needs to unpack something must re-run
   `df -k` itself rather than quoting §3 above.
2. **The phone is still unreachable.** The re-measure did not touch the handset; the CDC-ACM
   node (`/dev/cu.usbmodem201`) was not re-probed and no on-device value is claimed here. The
   phone free-space measurement remains **BLOCKED_EXTERNAL_RESOURCE** (§6, §10).
