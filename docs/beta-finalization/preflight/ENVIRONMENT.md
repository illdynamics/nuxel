# Environment preflight — measured, not assumed (briq-00a)

> **2026-10-16 re-verification (bg-00, second session of this run): the handset IS reachable in
> this session — the USB CDC-ACM live console answers and every device-side fact in §13 below
> was read off the physical SM-G975F. §6, §10 and §12 record the *first* session, where the
> console enumerated but did not answer; §13 supersedes them for the current session.**


**Access tier:** repository-only in the first session (§1–§12); **repository + read-only live
console** in the re-verification session (§13).
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

---

## 13. Re-verification in the current session — Linux host, live USB console **ONLINE**

**Access tier this session:** repository + **read-only live inspection of the handset** over the
USB CDC-ACM console.  Nothing was written to the phone, no service was restarted, no partition or
block device was touched, no reboot was issued and no key was injected.  The only device-side
write is the framing temp file `/var/tmp/nx-<id>` that the project's own console tool creates for
every command (see §13.4) — it is transient, holds only a command's stdout/stderr, and is removed
by the tool itself at the start of the next command.

**Measured (real clock, `TZ=Europe/Amsterdam` → +02:00):** 2026-10-16T17:26Z → 17:32Z
(19:26 → 19:32 +02:00).  Every value below quotes the command output it came from; the raw
captures live in `docs/beta-finalization/preflight/live/`.

### 13.1 What changed since the first session (§1–§12)

| Property | First session (§1–§12) | This session (§13) |
|----------|------------------------|--------------------|
| Host | macOS 15.7.9 on Apple Silicon (`Darwin infranux`) | **Fedora Linux 43 x86_64** (`dextronux`, kernel 6.17.1-300.fc43) |
| Workspace path | `/Users/wicked/x/nuxel` | **`/x/nuxel`** (same repository, same `origin/main`) |
| Supplied archives | `docs.zip`, `scripts.zip`, `tools.zip`, `nuxel-main.zip`, … present in `~/Downloads` | **absent** — re-scan found none (§13.19, `ARCHIVE-INVENTORY.md` §5) |
| `.venv/` | present, 772 files | **absent** (a fresh clone of the same tree) |
| Phone console | node enumerated, **did not answer** → `BLOCKED_EXTERNAL_RESOURCE` | **answers** (framed, SHA-256-verified round trips) |
| aarch64 execution channel | native on the arm64 Mac + UTM guest | **none**: no cross-gcc, no `qemu-aarch64-static`, no binfmt, no UTM (see §13.2) |
| HEAD at start | `de45917d` | **`6ee6a39c727f8936ae530092ba23bfe3b7d1e4a1`** (`main`, working tree clean except other groups' in-flight files) |

### 13.2 Host platform and tool inventory (this session)

```
$ uname -a
Linux dextronux 6.17.1-300.fc43.x86_64 #1 SMP PREEMPT_DYNAMIC Mon Oct  6 15:37:21 UTC 2025 x86_64 GNU/Linux
$ cat /etc/os-release | head -2
NAME="Fedora Linux"
VERSION="43 (Workstation Edition)"
$ uptime ; free -m | head -2
 19:30:15 up 14 days, 18:25,  5 users,  load average: 0.14, 0.18, 0.11
               total        used        free      shared  buff/cache   available
Mem:           31829        7600        6878        1370       19185       24229
```

| Tool | This session | Consequence |
|------|--------------|-------------|
| `python3` | `/x/qonqrete/.venv/bin/python3` — **3.11.8** | every `tools/beta/*.py` and `tools/s10plus/**/*.py` runs; the QonQrete venv is first on `PATH` |
| `git` | 2.55.0 | repository work normal |
| `jq` | 1.8.1 | the regression guard's manifest reader works |
| `node` | v20.20.0 (nvm) | the JS suites (safe zones, launcher registry) actually execute |
| `adb` | present, `adb devices` → **empty** | adb channel unavailable; the serial console is the only device channel |
| `podman` / `docker` | present (29.9.0) | `docker run --platform linux/arm64 fedora:43 uname -m` → **`exec /usr/sbin/uname: exec format error`**: `/proc/sys/fs/binfmt_misc` holds only `register`/`status`, **no `qemu-aarch64` handler**, so **no aarch64 container execution channel** |
| `qemu-system-aarch64`, `socat`, `aarch64-linux-gnu-gcc` | **ABSENT** | nothing on this host can execute an aarch64 Linux ELF; a cross build is not possible here |
| `lsusb` | present | used for the gadget identity probe |

**Consequence for the whole run:** the aarch64 colour selftest behind INV-2 cannot execute on this
host (it executed natively on the arm64 Mac in the first session).  The handset itself is the only
aarch64 execution channel available in this environment, and this group may only read from it.
That is why `tools/beta/regression-guard.sh` reports the two INV-2 binary legs as **WARN**
(`binary absent or not executable: build/out/s10plus/a32/nuxel-wl-fb`) while the source-level and
A33 golden-bytes legs pass.

### 13.3 Disk

```
$ df -k / /tmp
Filesystem        1K-blocks      Used Available Use% Mounted on
/dev/mapper/vg-lv 486191160 417842156  68349004  86% /
tmpfs              16296908   1311596  14985312   9% /tmp
```
Host: **66 747 KiB … 68 349 004 KiB (≈65 GiB) free** on the volume holding `/x/nuxel`; `/tmp` is a
16 GiB tmpfs with ≈14.3 GiB free.  The 22 GiB hard budget of the first session does not bind here,
but the rule stands: still no bulk unpacking (nothing needs it — no archive is present).

**Phone filesystem free space — MEASURED (first session: NOT MEASURED):**

```
$ df -h ; df -k / | tail -1
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda31      3.9G  1.7G  2.0G  47% /
tmpfs           3.5G   13M  3.4G   1% /dev/shm
tmpfs           1.4G  268K  1.4G   1% /run
tmpfs           3.5G     0  3.5G   0% /tmp
/dev/sda31       4046560 1781008   2055840  47% /
```
The Nuxel rootfs (`/dev/sda31`, ext4) is **3.9 GiB, 47 % used, 2 055 840 KiB ≈ 1.96 GiB free**.
`free -m` on the phone: **7420 MiB total, 6416 MiB free, 0 swap**.

### 13.4 How the live console was reached, and the three tool defects fixed

``` 
$ ls -la /dev/ttyACM0 /dev/serial/by-id/
crw-rw----. 1 root dialout 166, 0 Oct 16 19:30 /dev/ttyACM0
usb-Nuxel_Nuxel_S10+_Live_Console_NUXEL-S10PLUS-0001-if00 -> ../../ttyACM0
$ lsusb | grep 18d1
Bus 002 Device 015: ID 18d1:4ee7 Google Inc. Nexus/Pixel Device (charging + debug)
$ sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh --dev /dev/ttyACM0 --run 'uname -a'
Linux fedora 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64 GNU/Linux
```

The console node exists, carries the gadget string **`Nuxel_Nuxel S10+_Live Console`** /
`NUXEL-S10PLUS-0001`, and answers in framed round trips (`@@NXB/@@NXR/@@NXH/@@NXE`, target-side
SHA-256 re-verified on the host — `sha_ok=yes` on every command captured today; a mangled frame is
re-requested, never accepted).  Three defects in the host tool had to be fixed before it could be
used **on Linux** (all three are repository changes by this group, listed with their rollback in
§13.18):

1. **Missing heredoc terminator.** `scripts/s10plus-debug-pack/nuxel-live.sh` opened
   `exec "$PY" - … <<'PYEOF'` at line 64 and never closed it — bash warned
   *"here-document at line 64 delimited by end-of-file (wanted `PYEOF')"* on every invocation and
   fed the interpreter from EOF.  Fixed by appending the `PYEOF` terminator; `bash -n` clean.
2. **macOS-only device discovery.** The default was `ls /dev/cu.usbmodem*`; on Linux the gadget is
   `/dev/ttyACM*`.  The tool now probes both and, when the node exists but is not readable, prints
   the real remedy (`root:dialout 0660`; add yourself to `dialout` *or* re-run with `sudo` — never
   `chmod` the node).
3. **Port lock crashed instead of falling back.** `open("/tmp/nuxel-live.<dev>.lock","w")` under
   `sudo` fails with `EACCES` on a Fedora host because `fs.protected_regular=2` forbids root from
   `O_CREAT`-opening another user's file in the shared sticky `/tmp`.  The tool printed a raw
   `PermissionError` traceback — exactly the failure class the A33 cable-pull fix removed for the
   serial port.  Now a genuinely **held** lock is still reported as such (exit 3), and a lock that
   merely cannot be *opened* falls back to a private per-uid lock, announcing the substitution.

Access note for later groups: **the node is `root:dialout 0660`, and `wicked` is not in `dialout`
in this environment** (`id` → `wicked wheel vboxusers docker`).  Every capture below therefore ran
through `sudo -n` (passwordless sudo verified, `sudo -n id` → `uid=0(root)`).  Do not `chmod` the
device node: use `sudo`, or `usermod -aG dialout` plus a fresh login.

### 13.5 Device identity and boot mode

```
$ cat /proc/version
Linux version 4.14.253 (root@) (gcc version 15.3.1 20260722 (Red Hat 15.3.1-1) (GCC)) #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026
$ tr -d '\000' < /proc/device-tree/model ; echo
Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820
```
| Item | Measured |
|------|----------|
| Model / codename | **SM-G975F / beyond2lte** (`androidboot.em.model=SM-G975F`, board `BEYOND2LTE EUR OPEN 26`), SoC **Exynos 9820** |
| Kernel | **4.14.253** (`#15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026`), built with **GCC 15.3.1 (Red Hat)** — i.e. the Fedora toolchain |
| Distribution | **Fedora release 43 (Forty Three)**, aarch64, hostname `fedora`, systemd PID 1 |
| Bootloader | `androidboot.bootloader=G975FXXSEFUL1`, `androidboot.verifiedbootstate=orange` (unlocked, as required by the project) |
| Serial / AP serial | present in `/proc/cmdline` — **deliberately not reproduced in this document** (identity is established by model, board, SoC and bootloader string). The raw capture `preflight/live/batch-1-identity.out` keeps the command line **verbatim**, unredacted, because it is the primary evidence for the charger-mode finding and doctoring evidence would be worse than quoting it. No IMEI, IMSI, PIN, APN credential or SIM identifier was read at any point — the modem was only probed with `mmcli -L` (which returned "No modems were found") and with `ls` on the device nodes. |
| **Boot mode** | **`androidboot.mode=charger`** and `charging_mode=0x3030` in `/proc/cmdline` (`consoleblank=0`), i.e. the handset is in **charger/LPM mode** |
| Consequence | `[sec_input] sec_ts_init: Do not load driver due to : lpm 1` — the touchscreen driver **deliberately does not initialise** in this boot (§13.8). This is the P0 condition bg-01 owns; **this group took no action on it** (no reboot, no service change) because bg-00 is repository plus read-only inspection only. |
| Other cmdline facts used later in this run | `root=/dev/sda25` (initramfs) → switch_root into `/dev/sda31`; `sec_tsp_log=0x40000@0x91244000` (the `sec_ts` log region exists even though the driver does not arm); `printk.devkmsg=on` |

### 13.6 systemd health

```
$ systemctl is-system-running
degraded
$ systemctl --failed --no-pager
  UNIT                    LOAD   ACTIVE SUB    DESCRIPTION
● nuxel-touch-arm.service loaded failed failed Nuxel S10+ touchscreen arming (sec_ts stop->start, then hold open)
```

**One failed unit**, and it is the expected one: the touchscreen arming hook cannot arm a driver
the kernel skipped in charger mode.

```
$ systemctl status nuxel-touch-arm.service --no-pager -l | head
× nuxel-touch-arm.service - Nuxel S10+ touchscreen arming (sec_ts stop->start, then hold open)
     Active: failed (Result: exit-code) since Tue 2026-09-15 00:01:46 UTC; 14min ago
   Process: 5783 ExecStart=/usr/lib/nuxel/nuxel-touch-arm (code=exited, status=2)
   Sep 15 00:01:46 fedora systemd[1]: nuxel-touch-arm.service: Scheduled restart job, restart counter is at 10.
   Sep 15 00:01:46 fedora systemd[1]: nuxel-touch-arm.service: Start request repeated too quickly.
```

Running units (16, measured):

```
init.scope · dbus-daemon.service · ModemManager.service · NetworkManager.service
nuxel-button-manager.service · nuxel-wayland.service · nuxel-wl-fb.service
polkit.service · seatd.service · systemd-journald.service · systemd-logind.service
dbus.socket · systemd-journald{,-audit,-dev-log}.socket · systemd-logind-varlink.socket
```

Unit files live in **`/etc/systemd/system/`** (not `/usr/lib/systemd/system/`): `nuxel-button-manager.service`
(+ `…service.prev-a32`), `nuxel-fallback.service`, `nuxel-firstlight.service` (**disabled**),
`nuxel-touch-arm.service`, `nuxel-ui-fallback.service` (**disabled**), `nuxel-ui.service`,
`nuxel-wayland.service`, `nuxel-wl-fb.service`, plus `nuxel-ui.service.d/10-launcher-primary.conf`.

### 13.7 Display, framebuffer and the graphical stack

```
$ ls -la /dev/fb0 /dev/dri ; cat /sys/class/graphics/fb0/name /sys/class/graphics/fb0/virtual_size /sys/class/graphics/fb0/bits_per_pixel
ls: cannot access '/dev/dri': No such file or directory
crw------- 1 root root 29, 0 Jan  1  1970 /dev/fb0
1440,6080
32
$ cat /sys/class/graphics/fb0/modes
U:1440x3040p-0
$ ls -l /sys/class/graphics/
fb0 -> ../../devices/platform/19030000.decon_f/graphics/fb0
fb1 -> ../../devices/platform/19050000.decon_t/graphics/fb1
```
| Item | Measured |
|------|----------|
| Framebuffer | `/dev/fb0` = `19030000.decon_f`, **1440×6080 virtual (double-height), 32 bpp**, mode `U:1440x3040p-0` — matches the A32 DECON/XRGB8888→ABGR8888 baseline |
| DRM | **no `/dev/dri`** — the session is Phoc-headless + Wayland→framebuffer bridge, exactly as documented; native DRM/KMS is still future kernel work (no equivalence claimed) |
| Compositor | `phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh` (PID 5315, 392.7 MB, 72 tasks); log: `Linux dmabuf support unavailable`, `Output 'HEADLESS-1' added` |
| Launcher host | `/usr/lib/nuxel/nuxel-pwa-host` (PID 5349) + `python3 -m http.server 8000 --bind 127.0.0.1` (PID 5359) + 2× `WebKitWebProcess` (5402, 5641) + `WebKitNetworkProcess` (5400) |
| Bridge | `nuxel-wl-fb` (PID 5387) |
| Buttons | `nuxel-button-manager` (PID 5388) |

**CPU cost measured on the handset** (`ps -eo … --sort=start_time`): `nuxel-wl-fb` **63.6 % CPU**,
`phoc` **32.5 %**, `WebKitWebProcess` 7.1 % / 1.0 %, `nuxel-pwa-host` 1.0 % — i.e. the bridge and the
software-rendered compositor are the dominant CPU consumers at idle.  Load average on the phone at
capture time: **12.11 11.71 7.85** with 8 CPUs and 347 tasks.  This is a real, measured
performance finding for the resource/performance workstream (it is *not* a verdict that the
launcher is broken — the launcher process tree is healthy and holding the display).

### 13.8 Input devices — and the missing touchscreen

```
$ cat /proc/bus/input/devices        # 7 devices, condensed
meta_event   event0   /devices/virtual/input/input0            (EV=5 REL=c0)
gpio_keys    event1   /devices/platform/gpio_keys/input/input1 (EV=3 KEY=…1c000000000000)
grip_sensor  event2   /devices/virtual/input/input2
ssp_context  event3   /devices/virtual/input/input3
Headset      event4   madera-extcon (EV=23 KEY=40 … 402000000 c000000000000 SW=94)
hall         event5   /devices/platform/hall/input/input5
certify_hall event6   /devices/platform/certify_hall/input/input6
$ ls -la /sys/class/sec/tsp
ls: cannot access '/sys/class/sec/tsp': No such file or directory
$ ls /sys/module | grep -iE 'sec_ts|tsp|touch'      # (empty)
$ dmesg | grep -iE 'sec_ts|tsp_|lpcharge' | tail -4
[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1
[    2.214721] tsp_io: disabling
[    2.214833] tsp_avdd: disabling
```

| Finding | Evidence | Meaning |
|---------|----------|---------|
| **No touchscreen evdev node exists** | 7 input devices, none is `sec_ts`/`sec_touchscreen`; `/sys/class/sec/tsp` absent | nothing for libinput/Phoc to use — touch cannot work in this boot |
| Root cause | `sec_ts_init: Do not load driver due to : lpm 1` + `androidboot.mode=charger` | the kernel *chose* not to arm the controller because the boot is a charger/LPM boot |
| No loadable modules at all | `lsmod` → header only (`1` line) | the 4.14.253 kernel is monolithic for these drivers; a "modprobe sec_ts" recovery is impossible by construction |
| `nuxel-touch-arm.service` | failed (exit 2), restart counter 10 | the userspace "stop→start then hold open" hook cannot succeed while the driver is skipped; mission rule honoured — no hacks were added by this group to resurrect it |
| Also useful later | `/sys/class/input/eventN` → `inputN` symlinks are device-scoped and stable **by capability**, not by number; `/dev/input/eventN` nodes are `root:root 0600` | the "no hardcoded eventN" rule (bg-01's `libnuxel-libinput-path.so`) is the right design; any later group that opens `/dev/input/eventN` as a non-root user will get `EACCES` (measured: `crw-------`) |

### 13.9 Audio

```
$ cat /proc/asound/cards
 0 [beyondmadera   ]: beyond-madera - beyond-madera
 1 [aboxvdma       ]: abox_vdma - abox_vdma
 2 [aboxdump       ]: abox_dump - abox_dump
$ aplay -l
sh: aplay: command not found
```
* ALSA card **0 = `beyond-madera`** is present, as the A32 baseline predicted, plus the ABox DMA/dump
  helpers.  `/proc/asound/devices` exposes 12 playback PCMs (`pcmC0D0p`…`pcmC0D11p`) and 10 capture
  PCMs (`pcmC0D12c`…`pcmC0D22p`), so both directions have real device nodes.
* **`alsa-utils` is not installed** (`aplay` missing) and **neither is `pipewire` nor
  `wireplumber`** (§13.15).  So there is no mixer to read, no userspace sound server, and no way to
  play a test tone on the device today.  Audio must therefore be reported as **prepared but
  unproven**; nothing about speaker output is claimed here, and no mixer value was written.
* `/sys/class/sound` lists the same cards and PCM nodes — the hardware side is real.

### 13.10 Radios: Wi-Fi, Bluetooth, modem

```
$ rfkill list
0: bcm43xx Bluetooth: Bluetooth     Soft blocked: yes   Hard blocked: no
1: phy0: Wireless LAN               Soft blocked: no    Hard blocked: no
2: brcmfmac-wifi: Wireless LAN      Soft blocked: no    Hard blocked: no
$ ip -br link | grep -E 'wlan|p2p|rmnet|umts'
p2p0  DOWN 00:90:4c:33:22:11 ; wlan0 DOWN 00:90:4c:4c:b1:54 ; wlan1 DOWN 02:90:4c:4c:b1:54
umts_dm0 DOWN <POINTOPOINT…> ; rmnet0…rmnet7 DOWN <POINTOPOINT…>
$ ls -la /dev/cdc-wdm* /dev/wwan* /dev/mhi*
ls: cannot access '/dev/cdc-wdm*': No such file or directory        (all three absent)
$ mmcli -L
No modems were found
```
| Radio | Measured state | Consequence |
|-------|----------------|-------------|
| Wi-Fi | **`brcmfmac` / `phy0` driver present**, `wlan0` + `wlan1` + `p2p0` interfaces exist, all `DOWN`; `rfkill` shows the Wi-Fi PHY **unblocked**; `/etc/NetworkManager/system-connections/` is empty; `nmcli -t … dev` lists every non-`lo` interface as `unmanaged`; `cat /etc/resolv.conf` → **No such file** | the chipset is Broadcom `brcmfmac` on this exact unit (measured, not assumed from any Pixel document). Interfaces enumerate ⇒ the driver bound; **no scan, no association, no DHCP, no DNS** has happened on this boot. Everything beyond "interface enumerates" is unproven. |
| Bluetooth | `bcm43xx Bluetooth`, **soft blocked** | controller seen by rfkill, currently blocked; BlueZ pairing is unproven |
| Modem | `ModemManager` running, `mmcli -L` → **No modems were found**; `rmnet0..7`/`umts_dm0` exist but are `DOWN`; no `cdc-wdm*`/`wwan*`/`mhi*` device nodes | consistent with the A32 baseline: the Shannon LTE modem has no upstream ModemManager-compatible host interface on this kernel. **BLOCKED_KERNEL/BLOCKED_FIRMWARE** territory — no EFS/IMEI/calibration/radio-firmware contact of any kind was made |
| Gadget | `/dev/ttyGS0` present (the live console's serial function) | the USB gadget is what carries this very session |

### 13.11 Power, thermal and CPU

```
$ nproc ; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor \
        /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors
8
schedutil
performance schedutil
$ cat /sys/class/thermal/thermal_zone0/type /sys/class/thermal/thermal_zone0/temp
BIG
39000
$ ls /sys/class/power_supply
ac  battery  max77705-charger  max77705-fuelgauge  mfc-charger  otg  ps  usb  wireless
$ for f in capacity status health temp voltage_now current_now charge_type; do echo "battery/$f=$(cat /sys/class/power_supply/battery/$f)"; done
battery/capacity=100    battery/status=Full   battery/health=Good   battery/temp=271
battery/voltage_now=4317000   battery/current_now=0   battery/charge_type=Fast
```
| Item | Measured | Consequence for the power-management workstream |
|------|----------|--------------------------------------------------|
| CPUs | **8** (`nproc`), `scaling_governor=schedutil` | the only governors this kernel implements are **`performance` and `schedutil`** — an "ondemand/powersave/conservative" UI would be a lie on this kernel; the governor list must be read from sysfs, never hardcoded |
| Thermal | `thermal_zone0` = **`BIG` 39.0 °C** at idle | thermal zones are readable; thermal throttling must never be disabled |
| Charger/FG | `max77705-charger`, `max77705-fuelgauge`, `mfc-charger`, `otg`, `wireless`, `ac`, `battery`, `ps` | all Samsung PMIC interfaces the power app needs are visible |
| Battery | **100 %, `Full`, `Good`, 4.317 V, 0 mA, 27.1 °C, `charge_type=Fast`** (PDIC cable, `cable_type=19` from the kernel ring) | the handset is plugged in and full; idle-drain measurements are only meaningful unplugged, so they are **not** claimed |

### 13.12 Sensors (real enumeration)

```
$ for d in /sys/bus/iio/devices/iio:device*; do echo "$d name=$(cat $d/name)"; done
iio:device0  15c40000.adc            iio:device14 rotation_vector_sensor
iio:device1  accelerometer_sensor    iio:device15 game_rotation_vector
iio:device2  geomagnetic_sensor      iio:device16 sig_motion_sensor
iio:device10 light_flicker_sensor    iio:device17 step_det_sensor
iio:device11 proximity_sensor        iio:device18 step_cnt_sensor
iio:device12 proximity_alert_sensor  iio:device19 tilt_detector
iio:device13 proximity_raw           iio:device20 pickup_gesture
iio:device21 scontext_iio            iio:device23 thermistor_sensor
iio:device22 light_cct_sensor        iio:device24 proximity_pocket
iio:device25 uncal_accel_sensor      iio:device26 meta_event
```
23 IIO devices are enumerated on this exact unit: accelerometer, geomagnetic, ambient-light (two
variants), proximity (4 variants), rotation vector, game rotation vector, significant motion, step
detector/counter, tilt, pickup gesture, thermistor, light flicker, plus the sensor-context bridge.
The sensors workstream can therefore build a diagnostics page against **real** device names instead
of guessing — and the absent ones (barometer, hall is `event5`/`event6` *input*, not IIO; no
fingerprint IIO node) must be reported as absent.

### 13.13 LEDs, flashlight and haptics

```
$ ls /sys/class/leds
leds-sec1    torch-sec1
$ ls /sys/class/vibrator /sys/class/timed_output
ls: cannot access '/sys/class/vibrator': No such file or directory
/sys/class/timed_output:
vibrator
```
* **No multicolor RGB notification LED exists** on this unit: the only LED-class devices are
  `leds-sec1` (a single Samsung LED-class entry) and `torch-sec1` (the camera flash).  Per the
  mission's rule, the camera flash must **never** be presented as a notification LED ⇒ the
  notification-LED feature is `NOT_SUPPORTED_ON_DEVICE`; software "edge lighting" must be labelled
  as software.
* The vibrator **does** exist, but through the Samsung `timed_output` interface
  (`/sys/class/timed_output/vibrator`), not the input-force-feedback path.  Haptics is therefore
  implementable as a bounded, duration-based write — with the "no continuous test loops" rule.

### 13.14 Time and RTC

```
$ timedatectl
               Local time: Tue 2026-09-15 00:16:09 UTC
           Universal time: Tue 2026-09-15 00:16:09 UTC
                 RTC time: n/a
                Time zone: UTC (UTC, +0000)
System clock synchronized: no
              NTP service: inactive
$ ls -la /etc/localtime /etc/timezone
ls: cannot access '/etc/localtime': No such file or directory
cat: /etc/timezone: No such file or directory
```
| Item | Measured | Note |
|------|----------|------|
| Phone clock | **2026-09-15T00:16:09Z** while the host clock was **2026-10-16T17:31Z** | the handset is **≈31 days behind**; this is a plausible "last known time" from a previous session, not a fabricated value — but it is definitely not current time |
| Kernel RTC | **`RTC time: n/a`** | **no battery-backed RTC is exposed to userspace on this kernel/board** — so "restore the clock at boot from the RTC" is not available as a userspace fix; report the uncertainty instead of pretending |
| NTP | `NTP service: inactive`, `System clock synchronized: no` | time sync awaits a working network (§13.10) |
| Timezone | `UTC`, and **`/etc/localtime` and `/etc/timezone` do not exist** | tzdata is not installed/configured: the Settings timezone feature has real work to do |
| Downstream symptom | `rpm -q …` reports *"Signature c9fa created at Tue Sep 15 17:23:38 2026 invalid: signature is not alive … Not live until 2026-09-15T17:18:38Z"* and `rpmdbNextIterator: skipping h# 379` | the stale clock makes RPM **signature verification fail** and hides one header, so package queries are unreliable until the clock is set |

### 13.15 Packages, Flatpak and the application inventory

```
$ rpm -qa | wc -l
410
$ rpm -q fedora-release systemd NetworkManager ModemManager pipewire wireplumber alsa-utils flatpak webkitgtk6.0 phoc phosh python3 mesa-dri-drivers
fedora-release-43-27.noarch
… (rpm signature "not alive" errors, see 13.14) …
package systemd is not installed            <- query artefact: the rpmdb header skip, not a missing systemd
NetworkManager-1.54.3-3.fc43.aarch64
ModemManager-1.24.2-1.fc43.aarch64
package pipewire is not installed
package wireplumber is not installed
package alsa-utils is not installed
package flatpak is not installed
webkitgtk6.0-2.52.5-1.fc43.aarch64
phoc-0.54.0-1.fc43.aarch64
phosh-0.54.0-1.fc43.aarch64
python3-3.14.7-1.fc43.aarch64
mesa-dri-drivers-25.3.6-3.fc43.aarch64
$ flatpak --version
sh: flatpak: command not found
```
| Package | On the device | Consequence |
|---------|---------------|-------------|
| `fedora-release` | 43-27 | the Fedora 43 ARM64 base is the one the project claims |
| `systemd` | **is** PID 1 (16 units running) but the query hides its header | the **rpmdb is damaged/partially hidden while the clock is wrong**; treat rpm output as advisory until the time fix lands |
| `NetworkManager` 1.54.3, `ModemManager` 1.24.2 | installed and running | Wi-Fi/network plumbing exists |
| `webkitgtk6.0` 2.52.5 | installed | note: the *running* launcher uses `webkit2gtk-4.1` helpers (`/usr/libexec/webkit2gtk-4.1/WebKitWebProcess`), so the 6.0 packages are present but are **not** what the live session uses — a parity question for the launcher workstream |
| `phoc` 0.54.0, `phosh` 0.54.0, `mesa-dri-drivers` 25.3.6, `python3` 3.14.7 | installed | compositor + shell + Python tooling present |
| `pipewire`, `wireplumber`, `alsa-utils`, `flatpak` | **NOT installed** | audio userspace, sound settings and the whole Flatpak/NuXtore package path are **not deployable on the device today**; they are repository work + a live-deploy task, not something to claim as working |

`/etc/nuxel/` exists with `device/`, `display/`, `input/`, `nuxel-beyond2lte.conf`,
`phoc-phone.ini`, `phone-runtime-status`.  `/usr/local/bin` is empty.  A frozen package list from an
earlier session is still on the device at `/var/lib/nuxel/pkglist.txt`.

### 13.16 On-device state receipts (boot / animation / display ownership)

```
$ cat /var/lib/nuxel/boot-stage /var/lib/nuxel/boot-context /var/lib/nuxel/display \
      /var/lib/nuxel/fb-owner /var/lib/nuxel/animation /var/lib/nuxel/buttons \
      /var/lib/nuxel/ui-build /var/lib/nuxel/ui-fb-ready \
      /var/lib/nuxel/anim-min-cycle.completed /var/lib/nuxel/fb-hold-stop
STAGE=PHONE_UI_INSTALLED
REV=A25-fbdev-phone-ui-1
root=/dev/sda31 device=s10plus slot=a
DISPLAY_ON
brightness=12800
saved_brightness=12800
max_brightness=48600
owner=nuxel-wl-fb
BOOT_WAIT_LAUNCHER
LAUNCHER_READY
ANIMATION_STOP_REQUESTED
ANIMATION_STOP_CONFIRMED
LAUNCHER_DISPLAY_OWNER
ANIM_STAGE=ANIMATION_STOPPED
ANIM_OWNER=nuxel-wl-fb
2026-09-15T00:01:02Z ACTION source=bixby(short) action=open-terminal
UI_REV=A25-fbdev-phone-ui-1
INSTALLED_AT_BOOT=1
PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888
ANIM_MIN_CYCLE_COMPLETED
ANIMATION_STOP_REQUESTED
```
These are the **readiness/ownership receipts** the boot-handoff invariant asks for, and on this boot
they form a complete chain: `BOOT_WAIT_LAUNCHER → LAUNCHER_READY → ANIMATION_STOP_REQUESTED →
ANIMATION_STOP_CONFIRMED → LAUNCHER_DISPLAY_OWNER`, with `owner=nuxel-wl-fb`, a committed
`fbio_pan_display 1440x3040x32 abgr8888` frame, and `ANIM_STAGE=ANIMATION_STOPPED`.  They are
**consumed here as evidence of what the device recorded**, not as a new verdict: this group did not
re-run the handoff.  The unrelated `buttons` receipt shows a real Bixby short-press handled as
`open-terminal` at 2026-09-15T00:01:02Z (the A32 button manager working, ~1 minute after boot).

The file inventory itself is a health signal for later groups: `bootreport.txt` (157 KB),
`ui-a27-home.ppm`, `ui-a27-settings.ppm`, `ui-home.ppm` (13.1 MB PPM screencopies), `touch-raw.bin`
(2 928 B — from an earlier touch experiment), `deploy.tmp`, `push-33470.b64`, `nxrecv.py`,
`pkglist.txt` and the empty `nxpayload.b64` are still on the rootfs.  Their presence is a cleanup
opportunity for the cleanup/deploy workstreams; **this group deleted nothing.**

### 13.17 Journal snapshot (errors in this boot)

```
$ journalctl -b -p err --no-pager | tail
… watchdog: watchdog0: watchdog did not stop!            (repeats every 10 s, kernel)
… dwc3 10c00000.dwc3: failed to send remote wakeup       (repeats)
… systemd[1]: Attaching device control BPF program to cgroup /system.slice/systemd-timedated.service failed: Argument list too long
… systemd[1]: systemd-timedated.service: bpf-firewall: Attaching egress BPF program to cgroup … failed: Argument list too long
… kernel: EXT4-fs (sda31): errors=remount-ro for active namespaces on umount 2
… kernel: audit: kauditd hold queue overflow
… kernel: <keyctl> add_key succeeded(0). type: user, desc: invocation_id
```
Reading these without alarm: the `watchdog0: did not stop!` and `dwc3 … remote wakeup` lines are
the A32-era baseline noise; **`s3c2410-wdt … RTC 2026-09-15 00:13:58 UTC`** in the kmsg stream is
the same stale clock as §13.14.  Two lines matter for later work: (a) **systemd cannot attach cgroup
BPF device-control programs on this kernel** (*"Argument list too long"* — the 4.14 kernel's BPF
program-load path rejects them), which caps what the permission/sandbox workstream can enforce and
must be stated honestly instead of promising eBPF-based app confinement; (b) the ext4
`errors=remount-ro … on umount` line is the boot-time mount-namespace teardown, recorded here
because it appeared in the same window and nothing like it was seen again.

### 13.18 Backup list — every file this group replaces

`docs/beta-finalization/preflight/BACKUP-LIST-20261016.tsv` records, for each file touched by
bg-00 in this session, the **git blob id at HEAD** (the rollback source) and the sha256 of the
version that was in the tree when the group started:

```
$ git checkout 6ee6a39c727f8936ae530092ba23bfe3b7d1e4a1 -- <path>     # per-file rollback
```

| File | git blob at HEAD | sha256 at HEAD |
|------|------------------|----------------|
| `scripts/s10plus-debug-pack/nuxel-live.sh` | `dc9aa86a33d6…` | `3b68af7f22dd48cf414e32a2d28cbcc3cfdfa5744be6b18d3dc1c321817b67b4` |
| `.gitignore` | `a2e3f4c161be…` | `b2c34efb04bd92e141cbb593c3bde87389fd4f27b84cb33b94a8bc910eb5ab9b` |
| `tools/beta/workqueue.py` | `68fcb4c1bddd…` | `f7036027041c9b7819e187ca5db417b1d9cfaf4f4529cb0d517e8c6c8d880f95` |
| `tools/beta/tests/test_workqueue.py` | `baebaf6e6846…` | `804b8878ec7ff3f046a92fd342d69f76bd1edcce11a780c367031564eb921549` |
| `docs/beta-finalization/WORK-QUEUE.md` | `89414a4cf7f6…` | `69ff064889b39af86982804f97c374d65458d47f263e31991a6dea69d8b9d408` |
| `docs/beta-finalization/baseline-protection.json` | `82fe81f5dd99…` | `733105d7ed123e766ef8af152d3682672dc044b836cc94f341ac7bcf3a07319f` |
| `docs/beta-finalization/BASELINE-PROTECTION.md` | `6b7d15545df7…` | `a840e4eb27519d113d789b4bed3246c1310553b7d323ab633c28e7e8d478fc3e` |
| `docs/beta-finalization/preflight/ENVIRONMENT.md` | `80968e2d3aad…` | `1cc5d6a1739ec3a98cc3c86af9a59833ee8a439d8ec852881c9a9692672d692e` |
| `docs/beta-finalization/ARCHIVE-INVENTORY.md` | `ff0078f1df4a…` | `c3dcf66703af9dec4afe9258eb6ca3f2eeb2f17b01584c663a6c59e38d7b7d15` |
| `docs/beta-finalization/workqueue/briq-00{a,b,c,d}-*.json` | see the TSV | append-only revisions; the earlier revisions are never rewritten |

The only files whose **bytes** this group changes are the six host/repository tooling and document
files above plus the four append-only task records; nothing under `configs/`, `pwa/`, `services/`,
`shell/`, `firmware/` or `tools/s10plus/a3*` is modified by bg-00 (see §13.19 for the one shared
build-time asset step).

### 13.19 Raw evidence index (all under `docs/beta-finalization/preflight/`)

| Capture | Content |
|---------|---------|
| `live/batch-1-identity.txt` / `.out` | identity, kernel, Fedora, uptime, `/proc/cmdline`, board, disk, memory, partitions — device commands + framed results |
| `live/batch-2-graphics-input.txt` / `.out` | systemd state + failed units, running units, process tree with CPU, framebuffer/DECON, `/proc/bus/input/devices`, `/dev/input`, `/sys/class/input`, missing `/sys/class/sec/tsp`, nuxel unit files, `/var/lib/nuxel` |
| `live/batch-3-audio-radio-power.txt` / `.out` | ALSA cards/PCMs, rfkill, interfaces, modem devices + `mmcli`, power_supply, IIO sensors, LEDs/haptics, CPUfreq/thermal, `timedatectl` |
| `live/batch-4-pkgs-services-receipts.txt` / `.out` | on-device receipts, unit files, `nuxel-touch-arm` failure, `nuxel-wayland` status, `journalctl -b -p err`, rpm inventory, flatpak, modules + `sec_ts` dmesg, resolv.conf, NM devices |
| `host-tool-inventory.txt` | host tools, versions, disk, load, virt probe, serial nodes, `lsusb` |
| `archive-rescan.txt` | the archive re-scan (all search roots, all names) |
| `protected-asset-hashes-20261016.tsv` | every protected asset: pinned vs current sha256 and MATCH/DRIFT |
| `BACKUP-LIST-20261016.tsv` | pre-change git blob + sha256 for every file this group touches |
| `gate-a32-suite.txt` | `tools/s10plus/a32/tests/run-tests.sh` with exit code |
| `gate-workqueue.txt` | `test_workqueue.py`, `verify-schema --json`, `render --check` with exit codes |
| `gate-regression-guard.txt` | `tools/beta/regression-guard.sh` (human + `--json`) with exit code |
| `gate-asset-invariant.txt` | `tools/dedupe-assets.sh --verify` with exit code |

**One shared build-time asset step:** two suites in the A32 gate (`wallpaper asset`,
`launcher registry → every precached asset exists in the tree`) require
`pwa/*/assets/nuxel-background.png`, which is **gitignored by design** (single source of truth in
`assets/`, copied per app at build time).  In this fresh clone the copies were absent, so the gate
failed for a *missing build artefact*, not a regression.  `tools/dedupe-assets.sh` (the project's own
sanctioned step) was run: it copies the canonical wallpaper into the six PWA `assets/` dirs and
re-copies the animation, and `tools/dedupe-assets.sh --verify` now reports
**`[VERIFY-OK] All 6 PWA asset dirs are byte-identical to the canonical assets/ tree`**.  The A32
suite went from **3 failing suites to 1**; the remaining failure is the aarch64 colour selftest,
which cannot execute on this host (§13.2) and belongs to `bg-02` (INV-2).

### 13.20 What was deliberately NOT measured, and why

| Not measured / not done | Why | Marked as |
|-------------------------|-----|-----------|
| Touch behaviour, swipe, multi-contact, on-screen keyboard | no touchscreen device node exists in this boot (§13.8); a charger-mode boot cannot produce one, and bg-00 may not change device state | `BLOCKED_KERNEL`-class condition for the moment of capture; owner/bg-01 action |
| Any audio playback ("mixer writes ≠ audible sound") | `alsa-utils`, PipeWire and WirePlumber are not installed; no tone was ever played and **no mixer value was written** | `NEEDS_OWNER_TEST` (after the userspace workstream deploys) |
| Wi-Fi scan/association/DHCP/DNS | needs credentials the mission forbids guessing, and this group may not write to the device | `NEEDS_OWNER_TEST` |
| Idle drain / battery life | the handset is on the charger at 100 % (`status=Full`) | not claimed (measurement invalid while charging) |
| GPS fix, camera frame, NFC tag, Bluetooth pairing, microSD, SIM, calls/SMS | requires a finger, a SIM tag, a card, a tag or an owner decision — and most need userspace that is not installed yet | `NEEDS_OWNER_TEST` / `NOT_SUPPORTED_ON_DEVICE` where hardware is absent |
| Reboot into Nuxel to escape charger mode | explicitly out of bg-00's scope (repository + read-only inspection); the reboot decision belongs to bg-01/bg-10 with the safety rules in the mission | not done |
| UTM/VM parity | no UTM and no hypervisor VM on this host; no aarch64 execution channel at all (§13.2) | `BLOCKED_EXTERNAL_RESOURCE` for the VM channel in this environment |
| The 7 supplied archives | not present anywhere on this host (re-scanned, §13.19 + `ARCHIVE-INVENTORY.md` §5) | per-archive `BLOCKED_EXTERNAL_RESOURCE` |

### 13.21 Verdicts for this session

| Item | Verdict |
|------|---------|
| Repository revision/tree state captured at HEAD `6ee6a39c` | **OFFLINE_TESTED** |
| Host tool inventory, disk, toolchain limits (no aarch64 execution channel) measured | **OFFLINE_TESTED** |
| Live USB console reachable, framed, SHA-256-verified round trips | **VERIFIED_ON_S10PLUS** |
| Device identity (SM-G975F / beyond2lte / Exynos 9820), kernel 4.14.253 #15, Fedora 43 | **VERIFIED_ON_S10PLUS** |
| Boot mode is `androidboot.mode=charger`; `sec_ts` deliberately skipped (`lpm 1`) | **VERIFIED_ON_S10PLUS** (observation of the device's own kernel log) |
| `systemctl is-system-running = degraded`, exactly one failed unit (`nuxel-touch-arm.service`) | **VERIFIED_ON_S10PLUS** |
| Touchscreen interaction | **NEEDS_OWNER_TEST** — impossible to test in this boot; no touch node exists |
| Framebuffer/DECON 1440×3040×32 state, Phoc-headless + bridge + PWA host process tree | **VERIFIED_ON_S10PLUS** |
| Phone rootfs free space (3.9 GiB, 47 % used, 1.96 GiB free) | **VERIFIED_ON_S10PLUS** (closes the first session's gap) |
| ALSA `beyond-madera` card + PCM device nodes present | **VERIFIED_ON_S10PLUS**; audible output still **NEEDS_OWNER_TEST** |
| Wi-Fi interfaces enumerate (brcmfmac, `wlan0`/`wlan1`/`p2p0`, all DOWN) | **VERIFIED_ON_S10PLUS**; connectivity itself **NEEDS_OWNER_TEST** |
| `mmcli -L` → "No modems were found" on this boot | **VERIFIED_ON_S10PLUS** (negative result recorded as such) |
| Battery/thermal/CPUfreq/governor inventory (`performance`, `schedutil` only) | **VERIFIED_ON_S10PLUS** |
| 23 IIO sensors enumerated; no RGB notification LED; `timed_output/vibrator` present | **VERIFIED_ON_S10PLUS** |
| No battery-backed RTC (`RTC time: n/a`), clock ≈31 days stale, tzdata unconfigured | **VERIFIED_ON_S10PLUS** (uncertainty stated, no precise time fabricated) |
| Repository tooling fixes (`nuxel-live.sh` ×3, `.gitignore`) | **OFFLINE_TESTED** (bash -n, real runs, guard re-run) |
| Work-queue ledger + `render` regeneration + 38 assertions | **OFFLINE_TESTED** |
| A32 protected-asset pins re-verified (hard 10/10 held; soft drift on files owned by `bg-02`) | **OFFLINE_TESTED** |
| Regression guard | **OFFLINE_TESTED** — `PASS=41 FAIL=0 WARN=8 INFO=2` after the `.venv` hygiene fix |
| aarch64 colour selftest (INV-2 binary legs) | **BLOCKED_EXTERNAL_RESOURCE** in this environment (no aarch64 execution channel); owner `bg-02` |
| Anything requiring a human finger/SIM/card/ear/eyes | **NEEDS_OWNER_TEST** |

> **Corrections appended 2026-10-16 (repair pass; `briq-00a-repo-preflight` revision 5).**  The rows
> above are preserved unchanged — this section is append-only.  Two claims of this session needed
> correcting, both recorded here next to the evidence channel that contradicts them:
>
> 1. **Regression-guard result.**  The last row above quotes `PASS=41 FAIL=0 WARN=8 INFO=2`.  That was
>    the **intermediate, pre-INV-10** measurement, not the session's final gate result.  The final
>    result is **`PASS=53 FAIL=0 WARN=8 INFO=2`** (INV-10 present: 41 + the 12 new INV-10 assertions =
>    53), captured in `docs/beta-finalization/preflight/gate-regression-guard.txt` (2026-10-16T17:36:56Z,
>    `REGRESSION GUARD: PASS`, `exit=0`) and re-confirmed by re-running
>    `bash tools/beta/regression-guard.sh` in this repair pass.  `BASELINE-PROTECTION.md` §9.1 quotes
>    the same 53; only the cited row here was stale.  The correction is also recorded as an appended
>    entry in `docs/beta-finalization/baseline-protection.json` → `reverification_log`.
> 2. **Batch-1 frame count.**  The identity capture's on-device evidence entry (queue record
>    `briq-00a-repo-preflight` revision 4) said *"12/12 framed round trips"*.  The capture itself,
>    `live/batch-1-identity.txt` / `.out`, carries **10** commands and **10** `sha_ok=yes` frames
>    (`grep -c '^===== ' live/batch-1-identity.out` = 10, `grep -c 'sha_ok=yes'` = 10).  The **12/12**
>    figure belongs to `live/batch-4-pkgs-services-receipts.out` (12 commands, 12 `sha_ok=yes`).
>    Corrected in `docs/beta-finalization/workqueue/briq-00a-repo-preflight.json` **revision 5**
>    (revision 4 is left untouched): **10/10 framed round trips, `sha_ok=yes` on every frame, rc=0**.

> **Second correction appended 2026-10-16 (repair pass 2; `briq-00a-repo-preflight` revision 6).**
> Correction 1, immediately above, was itself one step stale about *which* measurement is final —
> the same defect class, one step further along. **The final gate measurement of this pass is
> `PASS=68 FAIL=0 WARN=8 INFO=2` with INV-11 present** (raw capture:
> `docs/beta-finalization/preflight/gate-regression-guard-inv11.txt`, `run 20261016T175559Z` =
> 2026-10-16T19:55:59+02:00, summary line `REGRESSION GUARD: PASS`, `exit=0`). **`PASS=53` was the
> pre-INV-11 measurement and `PASS=41` the pre-INV-10 one, both within the same session** (53 + the
> 15 new INV-11 assertions = 68).  The row above (41) and correction 1 (53) are both preserved
> unchanged — this section is append-only.  INV-11 itself is named in neither of them: it is
> recorded in `docs/beta-finalization/BASELINE-PROTECTION.md` §11 and, with this final number, in
> the appended `reverification_log` entry of `docs/beta-finalization/baseline-protection.json`.
> Re-confirmed on this repair pass's HEAD `3c0264e9112f7ac4e60510e2be6b5783ac3e286a` by re-running
> `bash tools/beta/regression-guard.sh` -> `PASS=68 FAIL=0 WARN=8 INFO=2`, exit 0.

### 13.22 Observed tool caveat — `tools/beta/health-check.sh` mis-detects this workstation

Captured (raw: `docs/beta-finalization/preflight/observed-health-check-host.txt`) while validating
that nothing else in the tree regressed:

```
$ bash tools/beta/health-check.sh
=== Nuxel health check ===  root=/  tier=ON_DEVICE
  [FAIL] unit-nuxel-pwa / unit-nuxel-wl-fb / unit-nuxel-button-manager / unit-nuxel-wayland /
         unit-nuxel-pwa-host / unit-nuxel-touch-arm   inactive (inactive)
  [FAIL] no-failed-units        2 failed unit(s)   <- the workstation's own caddy.service and xrdp.service
  [FAIL] fb-owner-present       no fb-owner record (/var/lib/nuxel/fb-owner)
  [FAIL] launcher-http          http://127.0.0.1:8000/ -> 000
  [FAIL] touch-node             by-path touch nodes: none
verdict: UNHEALTHY
```

This was run on the **Fedora workstation** (`root=/`), and every line is therefore a statement about
the workstation, not the handset: it has no `nuxel-*` units, no `/dev/fb0`, no
`/var/lib/nuxel/fb-owner` and nothing listening on 127.0.0.1:8000.  The tool's tier auto-detection
reported `tier=ON_DEVICE` anyway, which is the caveat worth recording: **a later cycle that runs this
tool in the wrong place will get a confident-looking `UNHEALTHY` that means nothing about the phone.**
The tool's own footer agrees — *"offline health checks verify recorded/fixture state and are advisory;
they are never proof that the phone is healthy"*.  Recorded here as an observation for
`bg-09-integration-release` (the owner of that tool); this group did not modify it.

For contrast, the **actual** device state measured in §13.6 over the live console is: 16 units
running, one failed unit (`nuxel-touch-arm.service`), the launcher process tree up and holding the
display.
