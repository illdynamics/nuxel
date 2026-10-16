# A32 baseline protected-asset register (briq-00d)

**Purpose.** The A32 build (`0102b6009d5ac561fe15c85b25a58942404d081d`, 2026-10-16T15:11:15+02:00) is the
**floor** of the Nuxel beta finalization. Everything that A32 proved on the handset must still
work after eleven parallel build groups have finished writing into this tree. This file turns
that sentence into first-class, hash-pinned, machine-checkable invariants, and
`tools/beta/regression-guard.sh` is the gate that enforces them.

* Machine-readable register: **`docs/beta-finalization/baseline-protection.json`**
* Gate: **`tools/beta/regression-guard.sh`** (exit 0 ⇔ no invariant regressed)
**Re-verified and extended 2026-10-16 (session 2, HEAD `6ee6a39c`)** — see §9 for the re-run,
the hygiene fix, the hash table and the new INV-10; §10 states the regression rule every later
group follows.  The §1–§8 text below is preserved unchanged except where §9.2 corrects it.

* Baseline floor record: `docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/13-RELEASE-NOTES-A32.md`
  (also `00-BASELINE.md`)

**The gate was executed before this register was frozen:**

```
$ bash tools/s10plus/a32/tests/run-tests.sh ; echo EXIT=$?
== 0 failing suite(s) ==
EXIT=0
```

---

## 1. Verbatim invariants that apply to every briQ (do not weaken)

> NO FLASHING of any kind — no writes to raw partition block devices or to
> BOOT/USERDATA/SYSTEM/RECOVERY/DTB/DTBO/VBMETA/radio/modem/EFS/SEC_EFS/calibration/IMEI/PIT
> or partition metadata; no Heimdall/Odin/wrappers, no Download Mode, no TWRP, no new kernel
> installed to the physical phone. Recovery/Download-Mode power-menu entries may be
> implemented and offline-tested but MUST NOT be triggered.
> NEVER create/edit/build anything under `/Users/wicked/x/nuxel/.qq` or RUN_ROOT — QonQrete
> metadata is read-only; NEVER write receipt JSON or pipeline metadata into the project
> workspace.
> Do not regress the A32 baseline. Do not start over: no new launcher, no replacing Fedora,
> no recreating existing functionality. Never claim untested hardware works; a passing unit
> test never yields VERIFIED_ON_S10PLUS. Reboots are allowed but must return to Nuxel with a
> known-working userspace rollback path; no blind repeat reboots. After three same-mode
> failures, change diagnostic strategy.

The register itself is guarded: `INV-8` fails if this document stops stating those
constraints.

---

## 2. Hash-pin modes (why not every file is a byte pin)

| Mode | Meaning | On drift |
|------|---------|----------|
| **hard** | the file is owned by this baseline / by no other build group; its bytes are the invariant | guard **FAILS**; the only sanctioned way to change it is an explicit re-pin (§5) |
| **soft** | the file is *shared* — another build group is contractually allowed to evolve it right now (e.g. `bg-02-boot-animation-launcher` owns `pwa/nuxel-home/sw.js`, `js/apps.js`, `js/safe-zones.js`, `js/status-bar.js`, `manifest.json`, `configs/nuxel/**`, `tools/s10plus/a32/tests/safe-zones-test.js`; `bg-04` owns `shell/config/systemd-user/`) | the byte pin is only *last-known-good*: drift is a **WARN**, and the behavioural assertions for that invariant are still enforced as hard PASS/FAIL |
| **self** | the register documenting itself | informational |
| **soft assertion** (`"mode": "soft"` on an individual assertion) | the assertion exercises a file that **another build group owns and is editing right now** (e.g. `tools/s10plus/a32/tests/safe-zones-test.js` belongs to `bg-02` this run) | assertion failure is a **WARN naming the owner**, not a FAIL — and never a silent pass. Everything defaults to hard. |

This is deliberate. A byte pin that fails every time a parallel group legitimately bumps the
service-worker cache namespace would be noise, and noise gets ignored. Behaviour is pinned
hard; bytes are pinned where ownership is exclusive.

---

## 3. Protected assets, pinned hashes and the invariant each one holds

Measured 2026-10-16T16:0x+02:00, Europe/Amsterdam (`shasum -a 256`). The table is generated
from `baseline-protection.json`, so the manifest and the document cannot disagree.

| Invariant | Path | sha256 | Mode | Role |
|---|---|---|---|---|
| `INV-1-launcher-cache-invalidation` | `pwa/nuxel-home/sw.js` | `d7fd084352f8fafa377d6f0ac28a4dd576fb842d03fd7292924609f6538ded30` | soft | service worker: versioned cache namespace + activate purge |
| `` | `pwa/nuxel-home/js/app.js` | `2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a` | soft | SW registration + updatefound handling |
| `` | `pwa/nuxel-home/js/apps.js` | `029c9331f45a1b52344baaf53c8d23eae985a549a3b39bdab6784c7e8abac401` | soft | app registry bridge used by the launcher |
| `` | `tools/s10plus/a32/nuxel-pwa-host.c` | `adeddd50474b57f9b927a13831e411845fad0d3453d95086b4c02b24eed616a6` | hard | host-side cache purge + URL version stamp |
| `INV-2-colour-conversion` | `tools/s10plus/a32/nuxel-wl-fb.c` | `6501c6d5d74128f9004088663ca78e46356b7131756d325165822a76b56c51d7` | hard | the bridge: conversion + animation gate + screen on/off |
| `INV-3-ten-zone-safe-areas` | `pwa/nuxel-home/js/safe-zones.js` | `ca99df1a9da4d94c75d83b91b5962b3d6aafd3b3ec76af5b5cf2b2c9b97cdb93` | soft | zone engine (10 zones) + presets + editor |
| `` | `configs/nuxel/statusbar-safezones.json` | `5dec2d293480f30ea4c6c1cf2b690d7efebd10247a4575a52c9c264c0cd9d9c6` | soft | persisted safe-zone document (device default) |
| `` | `tools/s10plus/a32/tests/safe-zones-test.js` | `aae114a6ee7481fd59382ce7a4ce02889d9a45811abb801c82d6fe05ccfe898d` | soft | 15-assertion offline test for the engine |
| `INV-4-button-manager` | `tools/s10plus/a32/nuxel-button-manager.c` | `07ce5c56d7f14efa4850a8ff8e851f574a034fe6582eb98fbec6188413b8632c` | hard | the manager: key map, ALSA volume, display toggle, OSD |
| `` | `tools/s10plus/a32/nuxel-button-manager.service` | `d911babfdbc9fbfe59da9f13317833601ecec4816494d1c672cc5526d3b1f90c` | hard | systemd unit (only owner of gpio_keys) |
| `` | `configs/nuxel/buttons.json` | `6e9994c054d8e983bdf0fe66a476106ad9036e21286aafb5871d778193e5ff25` | soft | user-remappable action map |
| `INV-5-live-usb-console` | `tools/s10plus/a24-nuxel-console.c` | `d5d4c65c0605f88e8769a1e04d00795e27048899d493dee212f97e7134ad6dd1` | hard | HUP-proof live root shell + /dev/kmsg mirror |
| `` | `scripts/s10plus-debug-pack/nuxel-console-host.sh` | `9428a1b2ce7cf46a2927d0738ceed4a9084b2579c254f3ae8b14be1e8b74202b` | hard | host-side driver (list/watch/run/accept) |
| `` | `boot/initramfs/init.sh` | `897e3e7de552855f76853aee5976b49f25c416f9653609958495211f64049395` | hard | initramfs launch point for /opt/nuxel/nuxel-console |
| `INV-6-userspace-rollback` | `tools/nuxel-rollback-home.sh` | `b6288c34e1117edfccaa76bd7d764fbb903108a9dc29ea88e9582c27993c1f24` | hard | rollback: native -> kiosk home |
| `` | `shell/config/systemd-user/nuxel-home-kiosk.service` | `18c24f92a417251eae14de154dd17cb2a07c4f58f1393e9565f55d304c13b8f8` | soft | known-working PWA kiosk unit |
| `` | `shell/config/systemd-user/nuxel-home-native.service` | `08ef67de38fdeda878556e0652ba915653e6d9c95745473bba060d3b7a91ade0` | soft | native home unit (the one rolled back from) |
| `` | `shell/config/systemd-user/nuxel-phosh-agent.service` | `e4ac569e0a6f0bf4fff2981a7669e38a254069363c7b6df8fc10d30e12829c72` | soft | Wayland/phoc session for the kiosk |
| `INV-7-a32-release-record` | `docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/13-RELEASE-NOTES-A32.md` | `a4bfe968f1c409c3e0233877d6284c369eef263216111a2cad2aaf4b4c24db67` | hard | A32 release record (floor of the mission) |
| `` | `docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/00-BASELINE.md` | `0f7474fcca4dcf4b09325807ed333636a5a142da936517c2fe2e4e2e4adfa197` | hard | A32 baseline statement |
| `INV-8-no-flash-invariant-recorded` | `docs/beta-finalization/BASELINE-PROTECTION.md` | `(absent)` | self | this register |
| `INV-9-a32-suite` | `tools/s10plus/a32/tests/run-tests.sh` | `cc9c79701e2848f9eafe737927fdafc799d8c9e644f3ff8403ba0e1aac77ef58` | soft | the A32 offline suite entry point, re-run by the gate |

### Invariant statements

1. **INV-1 launcher / PWA cache invalidation** (`bg-02`). A32's headline launcher finding was
   not "the launcher is different in the VM" — it was a *stale service-worker cache*: the old
   `./js/*.js` stayed alive after deployment, and two registry entries pointed at frontends
   that did not exist. The invariant has three legs, all enforced: the SW namespace is
   explicitly versioned (`const CACHE_VERSION = '…'`) and `activate` deletes the previous
   namespaces; the launcher reacts to `updatefound` and can be refreshed; the native host
   purges `CacheStorage` + `WebKitCache` at startup and version-stamps the launcher URL from
   the served `index.html` (`?v=<mtime+size>`), so the first navigation can never be a cached
   document. `NUXEL_KEEP_CACHE=1` remains the documented opt-out used when measuring cache
   behaviour itself.
2. **INV-2 colour conversion** (`bg-02`). The compositor hands the bridge XRGB8888
   (`R@16 G@8 B@0`); the panel's DECON maps `R@0 G@8 B@16` (ABGR_8888). Copying words
   unchanged swapped red and blue on the glass. The R↔B swap must stay in the scanout path,
   and the binary must still reproduce the A32 selftest vectors (`red 0x00ff0000 → 0xff0000ff`,
   green unchanged, blue `0x000000ff → 0xffff0000`, alpha forced opaque). Two independent
   checks run: a source assertion, and the real aarch64 binary's `--colour-selftest`, whose
   built hash is additionally compared against the hash A32 recorded as deployed and verified
   on the phone (`e4b4293e…`, see §4).
3. **INV-3 ten-zone safe areas** (`bg-02`). Ten zones, per-device and per-orientation presets,
   live preview, persistence and a console fallback; the S10+ preset blocks zones **9,10** in
   portrait and nothing in `landscape_left`, and device detection keys on the real hardware
   identity (`S10+|G975|beyond2`). A32 moved the battery cluster 112 px clear of zones 9–10;
   that placement must not silently revert to a no-cutout profile.
4. **INV-4 button manager** (`bg-03`). One process, not two, owns `gpio_keys`
   (114/115/116/703): POWER short → display off/on through `nuxel-wl-fb` (so there is still
   exactly one framebuffer owner), volume → the real ALSA element, assistant key → a
   configurable action (default Nuxel Terminal). The unit restarts the manager, and the key
   device is resolved by name/capability — never by a hard-coded `/dev/input/eventN`.
5. **INV-5 live USB console** (`bg-00`, protected baseline). The CDC-ACM console is the only
   channel that can inspect a running Nuxel without flashing and without adb. The ACM tty
   raises SIGHUP to the foreground process group when a host attaches, so the supervisor must
   respawn the shell (measured A24: `shell #N exited; respawning`), and the initramfs must
   start `/opt/nuxel/nuxel-console` before `switch_root`. The host driver
   `scripts/s10plus-debug-pack/nuxel-console-host.sh` must stay executable and must never
   touch the framebuffer (a stray `open("/dev/fb0")` disables DECON; A21 measured this).
6. **INV-6 userspace rollback** (`bg-04`/`bg-09`). `tools/nuxel-rollback-home.sh` flips from
   the native home unit back to the known-working PWA kiosk unit, which is why a normal reboot
   can never leave the phone without a launcher. The script and all three systemd-user units
   must exist and stay wired together.
7. **INV-7 A32 release record** (`bg-00`). `13-RELEASE-NOTES-A32.md` and `00-BASELINE.md` are
   the measured floor — they carry the deployed artefact hashes *and* the explicit
   "Still not claimed" list (audio output, camera, modem, WLAN, the owner-acceptance tests).
   Rewriting this record would make every later "no regression" claim worthless, so it is
   byte-pinned and the guard fails if it changes.
8. **INV-8 no-flash invariant recorded** (`bg-00`). The register must keep stating the
   NO FLASHING constraint, the `.qq`/RUN_ROOT read-only rule and the evidence discipline
   (`VERIFIED_ON_S10PLUS` requires on-device evidence).9. **INV-9 the A32 suite still runs** (`bg-00`, soft while other groups are mid-flight).
   A32's own evidence is `bash tools/s10plus/a32/tests/run-tests.sh` exiting 0 with
   `0 failing suite(s)`. The gate re-runs it on every invocation so a real regression in
   the colour selftest, the keycode bitmap decode, the ten-zone engine, the launcher
   registry or the wallpaper asset is visible immediately. It is deliberately a **soft**
   assertion: two of the suites it drives (the safe-zone engine test and the engine
   itself) are owned by `bg-02`, which is legitimately extending them during this parallel
   build. A failure there is therefore reported as a WARN that names the owner — and,
   critically, the same A32 behaviour is *also* gated hard and independently by INV-3's
   `json_eq`/`regex` assertions and INV-2's real aarch64 colour selftest, so the soft
   signal cannot be used to hide a genuine baseline regression.

---

## 4. Deployed-artefact hash parity (A32 → now)

A32 recorded these hashes as installed and verified **on the handset**:

| Target on the phone | sha256 | Built from |
|---|---|---|
| `/usr/lib/nuxel/nuxel-wl-fb` | `e4b4293e8d3d7d5e1c168e58c80ef23e4cb64db30313f0658498362ccaca7b9e` | `tools/s10plus/a32/nuxel-wl-fb.c` |
| `/usr/lib/nuxel/nuxel-pwa-host` | `18631d5b71eb938d821ba319ddf78ee73b403811933824d93b36dc9439f7f6b0` | `tools/s10plus/a32/nuxel-pwa-host.c` |
| `/usr/lib/nuxel/nuxel-button-manager` | `5f052ef4523a3fee8f13c65a24fddfede553753d18725bd533e7e877f7cc3dc5` | `tools/s10plus/a32/nuxel-button-manager.c` |
| `/usr/bin/nuxelctl` | `e4281cab…` (abbreviated in the A32 record) | `tools/s10plus/a32/nuxelctl` |
| `/etc/systemd/system/nuxel-button-manager.service` | `d911babfdbc9fbfe59da9f13317833601ecec4816494d1c672cc5526d3b1f90c` | `tools/s10plus/a32/nuxel-button-manager.service` |

The guard recomputes the hashes of the **built artefacts** in `build/out/s10plus/a32/` and
compares them with the table above. Honest limitation, stated up front: this run has **no live
phone console** (`docs/beta-finalization/preflight/ENVIRONMENT.md` §6 —
`/dev/cu.usbmodem201` enumerated but never answered), so the guard proves *build parity with
the bytes A32 shipped*, not a fresh read of the phone. A fresh on-device re-read requires the
owner or a reachable console and is recorded as **NEEDS_OWNER_TEST** in the work queue.
`build/` is gitignored; if the artefacts are absent the guard reports those two assertions as
**WARN (gate unavailable)** with the exact rebuild command, rather than pretending they passed.

---

## 5. Using the guard

```
$ bash tools/beta/regression-guard.sh                  # full gate; exit 0 ⇔ nothing regressed
$ bash tools/beta/regression-guard.sh --quiet          # one summary line per invariant
$ bash tools/beta/regression-guard.sh --no-tests       # hash + assertion checks only (fast)
$ bash tools/beta/regression-guard.sh --json           # machine-readable result on stdout
$ bash tools/beta/regression-guard.sh --repin <path> --reason "why this byte changed"
```

* Exit codes: `0` = all enforced checks pass; `1` = at least one **FAIL**; `2` = usage or
  manifest problem.
* Every run appends a log to `build/out/beta/regression-guard-<UTC>.log` (gitignored, so
  evidence accumulates without polluting the source tree).
* `--repin` is the **only** sanctioned way to move a hard pin. It rewrites the pinned hash in
  `docs/beta-finalization/baseline-protection.json`, **moves every `type:"sha256"` assertion that
  carries the old expected hash for that same path**, appends a `repin` entry to the manifest
  history with your reason, the old/new hashes and the number of assertions moved, and never
  edits the protected file itself. A re-pin is a claim that the behaviour behind the file is
  still intact — the behavioural assertions for that invariant still have to pass.
* Section 0 of the gate includes a **manifest self-consistency** check: if any `type:"sha256"`
  assertion disagrees with the `files[]` pin for the same path, the register is self-contradictory
  and the gate **FAILS** (rather than silently failing the file the operator just re-pinned).
* WARNs never fail the gate but they are printed loudly, because a soft-pin drift means a
  parallel group changed a protected behaviour and the behavioural assertions are the only
  thing holding the line.

### 5.1 Defect found by the self-test and repaired in this briQ

The first version of the guard updated only `files[].sha256` on `--repin`, leaving the
`type:"sha256"` assertion for the same path holding the **old** expected hash. The gate then
failed on the very file it had just re-pinned, and the register was self-contradictory:

```
$ bash tools/beta/tests/test-regression-guard.sh
PASS re-pin stores the new hash and appends a history entry
FAIL run after re-pin -> exit 1 (expected 0)
...
FAIL  self-test byte pin  [want 729681b0bc355e5765836070eb4d974e93e396cef22e7e92656adb7b9901ac84 got d58af9ebca634673ddd2b93e63cb098d3763a85423017d924e7e506380da5231]
```

Repair (all three parts are in `tools/beta/regression-guard.sh`):

1. `--repin` now rewrites `files[].sha256` **and** every matching `type:"sha256"` assertion
   `expect` in the same `jq` transaction, recording `sha256_assertions_updated` in the history.
2. Section 0 gained the manifest self-consistency FAIL described above, so the contradiction can
   never come back silently.
3. The `record()` helper accepted four arguments only; the new three-argument consistency check
   tripped `set -u`. `record()` now takes an optional `DETAIL`.

Result after the repair (real runs):

```
$ bash tools/beta/tests/test-regression-guard.sh
== 0 failing self-test(s), 10 passing ==

$ bash tools/beta/regression-guard.sh
== summary ==
   PASS=43  FAIL=0  WARN=2  INFO=2
   REGRESSION GUARD: PASS — the A32 baseline is intact (no failing checks).
```

---

## 6. Repository hygiene carried by this baseline

`docs.zip`, `scripts.zip`, `tools.zip` (129.7 MB) and `.venv/` (772 files) were untracked **and
unignored**, i.e. one `git add -A` away from entering the repository history. `.gitignore`
gained this anchored block (see `docs/beta-finalization/preflight/ENVIRONMENT.md` §9):

```
# --- Supplied comparison archives + local virtualenv (preflight briq-00a) ----
/docs.zip
/scripts.zip
/tools.zip
/*.zip
.venv/
```

Rollback: remove those lines — tracked-file impact is zero. `regression-guard.sh` asserts the
archive paths stay ignored, so a future edit that un-ignores a 125 MB zip fails the gate.

---

## 7. What the guard deliberately does **not** claim

* It does **not** claim any hardware works. A green gate means "the A32 code paths, presets and
  unit definitions are still intact and the aarch64 colour selftest still passes on this host".
  Touch, audio, Wi-Fi, camera, modem and the owner acceptance tests remain unproven and are
  listed as such.
* It does **not** touch the phone, the framebuffer, the console or any block device. It reads
  files, runs the offline test suites and (for the colour leg) executes a user-space binary
  with `--colour-selftest`.
* It does **not** replace the A32 suite — it re-runs it
  (`tools/s10plus/a32/tests/run-tests.sh`, INV-9) as one more assertion and reports its exit code.
* It does **not** claim that a file owned by another build group is frozen. Where such a file
  is exercised (INV-3's a32 suite, the `pwa/nuxel-home/js/*` and `configs/nuxel/*` soft pins),
  the register says so: an assertion marked `"mode":"soft"` reports failure as a WARN naming
  the owning group, and the *hard* assertions for that invariant are what hold the line.

## 8. Verdicts

| Item | Verdict |
|------|---------|
| Protected-asset register (hashes + invariants) created from the real tree | **OFFLINE_TESTED** |
| `tools/beta/regression-guard.sh` implemented and executed green on the untouched tree | **OFFLINE_TESTED** (PASS=43 FAIL=0 WARN=2 INFO=2) |
| `tools/beta/tests/test-regression-guard.sh` self-test (tamper detection, re-pin protocol, `--json`) | **OFFLINE_TESTED** (10/10 after repairing the `--repin` defect in §5.1) |
| A32 test suite re-run as a gate (INV-9, `tools/s10plus/a32/tests/run-tests.sh`) | **OFFLINE_TESTED** (exit 0, 0 failing suites) |
| Files owned by other build groups (`bg-02`: safe-zone engine + its suite) | **soft-pinned**, drift reported as WARN with the owning group named — `bg-02` is editing them right now; a genuine regression still FAILs through INV-3's hard `json_eq`/`regex` assertions |
| A32 deployed-artefact hash parity re-read from the phone | **BLOCKED_EXTERNAL_RESOURCE** → **NEEDS_OWNER_TEST** |
| Any of these invariants re-verified on the physical S10+ in this run | **NOT_SUPPORTED_ON_DEVICE** in this environment (no console, no adb) — requires a reachable phone |

---

## 9. Session-2 re-verification (2026-10-16, HEAD `6ee6a39c727f8936ae530092ba23bfe3b7d1e4a1`)

The register was re-run against the current tree on a **different host** from §1–§8 (Fedora Linux 43
x86_64, workspace `/x/nuxel`) and against the **live handset** (read-only).  Nothing in this section
deletes or rewrites an existing pin: it records what was re-measured, what had to be fixed to make
the gate green again, and one new invariant.

### 9.1 The gate, re-executed

```
$ bash tools/beta/regression-guard.sh --json
{"tool":"regression-guard","verdict":"PASS","pass":53,"fail":0,"warn":8,"info":2,
 "failed_invariants":"","warned_invariants":"INV-1… INV-3… INV-9-a32-suite INV-2-colour-conversion …"}
$ bash tools/beta/tests/test-regression-guard.sh
== 0 failing self-test(s), 11 passing ==
$ bash tools/s10plus/a32/tests/run-tests.sh ; echo EXIT=$?
== 1 failing suite(s) ==   EXIT=1
$ bash tools/dedupe-assets.sh --verify ; echo EXIT=$?
[VERIFY-OK] All 6 PWA asset dirs are byte-identical to the canonical assets/ tree.   EXIT=0
```

Raw captures: `docs/beta-finalization/preflight/gate-regression-guard.txt`,
`gate-a32-suite.txt`, `gate-asset-invariant.txt`, `gate-workqueue.txt`.

### 9.2 The one hard FAIL, and its fix

The first re-run failed exactly once, in repository hygiene:

```
    FAIL  repository hygiene: '.venv' must stay gitignored …  [git check-ignore .venv]
```

Root cause, measured: `.gitignore` carried the **directory-only** pattern `.venv/`.  On this fresh
clone (no `.venv` present) git cannot know that the path is a directory, so the pattern does not
match and `git check-ignore .venv` exits 1 — i.e. the guard's own assertion was checking a rule that
only held *after* the risky directory already existed.  Fixed in `.gitignore` by dropping the
trailing slash (`.venv` matches the path whether or not it exists).  **Authorised by
`briq-00a-repo-preflight` revision 4 / `briq-00d-baseline-protection` revision 4** (this section is
that record).  Re-measured after the fix:

```
$ for p in docs.zip scripts.zip tools.zip .venv; do git check-ignore -q "$p" && echo "$p ignored OK"; done
docs.zip ignored OK · scripts.zip ignored OK · tools.zip ignored OK · .venv ignored OK
```

> **Correction to §6 of this document.** The `.gitignore` block quoted in §6 shows `.venv/` as the
> last line.  The current, correct rule is `.venv` (no slash), for the reason above.  The block is
> otherwise unchanged; nothing else in the repository-hygiene rule was relaxed.

### 9.3 Build-time artefacts had to be restored before the A32 gate could pass

Two A32 suites fail on a fresh clone for a reason that is **not** a regression: the per-app wallpaper
copies are gitignored **by design** (single source of truth `assets/nuxel-background.png`, copied per
app at build time by `tools/dedupe-assets.sh`).  Measured before/after running that project step:

| Suite | Before | After |
|-------|--------|-------|
| `wallpaper asset` | `FAIL missing pwa/nuxel-home/assets/nuxel-background.png` | PASS |
| `launcher registry` | `FAIL every precached asset exists in the tree ["assets/nuxel-background.png"]` | PASS |
| `colour conversion` | `FAIL` (no `build/out/s10plus/a32/nuxel-wl-fb`) | **still FAIL — unchanged, not fixable here** |

The colour leg needs an aarch64 ELF to execute, and **this session's host has no aarch64 execution
channel at all**: no cross-gcc, no `qemu-aarch64-static`, no binfmt handler (`/proc/sys/fs/binfmt_misc`
holds only `register`/`status`), and `docker run --platform linux/arm64 fedora:43 uname -m` →
`exec /usr/sbin/uname: exec format error`; there is no UTM/VM either.  It is reported as a **WARN**
naming its owner (`bg-02-boot-animation-launcher`, INV-2), never as a pass and never as a baseline
regression.

### 9.4 Hash table — every protected asset, pinned vs current

Full machine-readable table: `docs/beta-finalization/preflight/protected-asset-hashes-20261016.tsv`.

```
INV-1  soft  pwa/nuxel-home/sw.js                        DRIFT  (owner bg-02)
INV-1  soft  pwa/nuxel-home/js/app.js                    MATCH
INV-1  soft  pwa/nuxel-home/js/apps.js                   DRIFT  (owner bg-02)
INV-1  hard  tools/s10plus/a32/nuxel-pwa-host.c          MATCH
INV-2  hard  tools/s10plus/a32/nuxel-wl-fb.c             MATCH
INV-3  soft  pwa/nuxel-home/js/safe-zones.js             DRIFT  (owner bg-02)
INV-3  soft  configs/nuxel/statusbar-safezones.json      MATCH
INV-3  soft  tools/s10plus/a32/tests/safe-zones-test.js  DRIFT  (owner bg-02)
INV-4  hard  tools/s10plus/a32/nuxel-button-manager.c    MATCH
INV-4  hard  tools/s10plus/a32/nuxel-button-manager.service  MATCH
INV-4  soft  configs/nuxel/buttons.json                  MATCH
INV-5  hard  tools/s10plus/a24-nuxel-console.c           MATCH
INV-5  hard  scripts/s10plus-debug-pack/nuxel-console-host.sh  MATCH
INV-5  hard  boot/initramfs/init.sh                      MATCH
INV-6  hard  tools/nuxel-rollback-home.sh                MATCH
INV-6  soft  shell/config/systemd-user/nuxel-home-kiosk.service    MATCH
INV-6  soft  shell/config/systemd-user/nuxel-home-native.service   MATCH
INV-6  soft  shell/config/systemd-user/nuxel-phosh-agent.service   MATCH
INV-7  hard  docs/…/BETA-HARDWARE-FINALIZER/13-RELEASE-NOTES-A32.md  MATCH
INV-7  hard  docs/…/BETA-HARDWARE-FINALIZER/00-BASELINE.md           MATCH
INV-8  self  docs/beta-finalization/BASELINE-PROTECTION.md           (self)
INV-9  soft  tools/s10plus/a32/tests/run-tests.sh        DRIFT  (owner bg-02)
INV-10 soft  scripts/s10plus-debug-pack/nuxel-live.sh    NEW PIN (8c413a471051be8d…)
```

**`hard pins: 10/10 held`.  No protected asset needed a re-pin in this session, so none was
performed** — the only hash change is the new INV-10 pin on a tool this group itself repaired, and
its old→new pair is recorded below.

| Path | Old sha256 | New sha256 | Reason | Authorising briQ |
|------|------------|------------|--------|------------------|
| `scripts/s10plus-debug-pack/nuxel-live.sh` | `3b68af7f22dd48cf414e32a2d28cbcc3cfdfa5744be6b18d3dc1c321817b67b4` | `8c413a471051be8d6d226dd818c3d6f780b02236c23dd165353793656a54eb20` | three real defects made the console unusable on a Linux host: missing `PYEOF` heredoc terminator (bash warning on every run), macOS-only `/dev/cu.usbmodem*` discovery, and a raw `PermissionError` traceback when the shared `/tmp` lock cannot be opened under `sudo` (`fs.protected_regular=2`) — details in `docs/beta-finalization/preflight/ENVIRONMENT.md` §13.4 | `briq-00a-repo-preflight` (rev 4) + `briq-00d-baseline-protection` (rev 4) |

### 9.5 New invariant added by this session

**INV-10 `console-and-ledger-tooling`** (hash mode `soft`, owner `bg-00-preflight`) pins twelve
assertions: the console tool stays executable; its Python heredoc is opened *and terminated*; the
Linux `/dev/ttyACM*` node is discovered; the port lock can be redirected (`NUXEL_LIVE_LOCK`); the
`fs.protected_regular` case is documented in the tool; the session-2 preflight, the device captures
and the backup list exist; and — the one that keeps the *plan* honest — `tools/beta/workqueue.py
render --check` exits 0, i.e. **`WORK-QUEUE.md` still matches the JSON store**.  Verified green:

```
-- INV-10-console-and-ledger-tooling
    PASS  the console tool stays executable
    PASS  the heredoc that carries the Python body is opened AND terminated
    PASS  the interpreter call and its terminator both use PYEOF
    PASS  the Linux CDC-ACM node (/dev/ttyACM*) is discovered, not only the macOS one
    PASS  the port lock can be redirected when the shared /tmp one is unusable
    PASS  the fs.protected_regular root-vs-shared-/tmp case is documented in the tool
    PASS  the session-2 environment preflight exists
    PASS  the session-2 device captures are preserved as evidence
    PASS  the session-2 backup list (pre-change blobs) exists
    PASS  workqueue.py is runnable as a program (so the render check below can execute it)
    PASS  the work queue has a renderer for its human view
    PASS  WORK-QUEUE.md still matches the JSON store (render --check)
```

### 9.6 What this session's re-verification does **not** claim

* The phone's A32 artefact hashes were **not** re-read from the device in this session: `nuxel-wl-fb`,
  `nuxel-pwa-host`, `nuxel-button-manager` and `nuxelctl` were not hashed on the handset, because
  bg-00 may only read *and* the read would still not be a verdict for a running feature.  The
  deployed-hash parity row of §4 therefore remains **NEEDS_OWNER_TEST** for this session as well.
* The green gate does **not** mean touch, audio, Wi-Fi, camera, modem or any owner acceptance test
  works.  It means the A32 code paths, presets, unit definitions and tool contracts are intact, and
  that the queue's human view still matches its machine view.
* The `WARN`s are not passes.  Four soft pins belong to `bg-02` and are mid-flight; the aarch64
  colour selftest is unavailable on this host; the A32 suite now fails only because of that
  unavailable selftest.

---

## 10. The regression rule every later group must follow

> **A protected hash may change only via an explicit work-queue revision that names the authorising
> briQ.**

Operationally (this is the contract; the guard enforces the mechanical half of it):

1. **Never edit a protected file and leave the register stale.**  If your briQ legitimately changes a
   protected file, that briQ must (a) append a revision to its own record in
   `docs/beta-finalization/workqueue/`, (b) record the transition here — old hash, new hash, reason,
   authorising briQ — as §9.4 does, and (c) move the pin with
   `tools/beta/regression-guard.sh --repin <path> --reason '<why>'`, which updates both the file pin
   and any `sha256` assertion that carried the old value (a stale copy is exactly the defect the
   register's self-consistency check exists to catch).
2. **A re-pin is a claim, not a proof.**  The behavioural assertions for that invariant must still
   pass; a byte pin that matches while the behaviour broke is caught by the `regex`/`json_eq`/
   `program`/`suite` assertions, not by the hash.
3. **Hard vs soft is about ownership, not importance.**  A file that another build group owns *right
   now* is `soft`: its pin is last-known-good and drift is a WARN that names the owner.  Drift is
   **never** a silent pass and never a FAIL-for-someone-else's-work-in-progress.
4. **Deleting a pin is not allowed by this rule.**  A pin can only be superseded by an appended entry
   that records the change (this register is append-only in exactly the same spirit as the queue).
5. **Evidence discipline is part of the baseline.**  A green gate is `OFFLINE_TESTED`, never
   `VERIFIED_ON_S10PLUS`; the only thing that yields an on-device verdict is an on-device capture
   (the queue tool refuses anything else).

---

## 11. Repair-pass addition (2026-10-16, `briq-00d-baseline-protection` revision 5): INV-11

Everything in §1–§10 is preserved unchanged.  This section records an **appended** invariant: the
inspeQtor found that four assets this briQ's own deliverable explicitly enumerates were left with
**no pin and no assertion anywhere in the tree** — a silent omission, which this briQ forbids.
`INV-11-a32-enumerated-asset-pins` close that gap.  Nothing was deleted, moved or rewritten.

| # | Item named by the briQ | State before INV-11 | Now |
|---|------------------------|---------------------|-----|
| a | `tools/s10plus/a32/nuxelctl` (and `tools/s10plus/a33/nuxelctl`) | only metadata + the abbreviated deployed hash `e4281cab…` in the A32 record; the guard had no assertion on it | **hard** pin + `file_executable` + `sha256` assertion on the a32 copy (`e4281cab8c96a70cc24a79aa10230ae6ab716141893d0c95abdbb1481b2d2c3b` = the full hash behind the abbreviation); the a33 copy is **soft**-pinned (current-cycle tree) |
| b | `tools/s10plus/a31/nuxel-libinput-path.c` + `tools/s10plus/a33/nuxel-libinput-path.c` (source of `libnuxel-libinput-path.so`) | zero occurrences in the register or the guard — even though `bg-01b` owns/edits the a33 copy in this same run, which is exactly the drift this register exists to catch | **soft** pins (`f94240412b731233…`, byte-identical at pin time) + two soft behavioural assertions (`INPUT_PROP_DIRECT` capability decision, `by-path/nuxel-touchscreen` devlink), each naming `bg-01-touch-pipeline` as owner, so drift is a **named WARN** instead of invisible |
| c | `assets/nuxel-boot-animation.mp4` + `assets/nuxel-background.png` | no expected-hash constant for the MP4 anywhere in the tree; the wallpaper only covered *indirectly* by the soft A32-suite `wp.py` step | **hard** `sha256` pins (`280e094fb3efe54e…`, `6e337ef2d506a167…`) with matching `sha256` assertions |
| d | `pwa/nuxel-apps/settings/**`, `pwa/nuxel-apps/terminal/**` | the launcher-registry test only checks that `index.html` + js **exist**, never their bytes | **per-file soft pins** for 18 files (9 per app) + hard `file_exists` assertions on the surfaces (`index.html`, `settings.js`, `terminal.js`, `terminal/sw.js`); owners named per file |

**Deliberately left unpinned, and said so (no silent gap):** the two 0-byte `.keep` placeholders in
those app directories — pinning an empty file proves nothing and would be noise.

**The gate, re-executed with INV-11 present** (raw capture:
`docs/beta-finalization/preflight/gate-regression-guard-inv11.txt`):

```
$ bash tools/beta/regression-guard.sh ; echo EXIT=$?
   hard pins: 13/13 held
== summary ==
   PASS=68  FAIL=0  WARN=8  INFO=2
   REGRESSION GUARD: PASS — the A32 baseline is intact (no failing checks).
EXIT=0
$ bash tools/beta/regression-guard.sh --json
{"tool":"regression-guard","verdict":"PASS","pass":68,"fail":0,"warn":8,"info":2, ... }
```

53 (session 2's final count, §9.1) + 15 new INV-11 assertions = **68**; hard pins went 10 → 13
(a32 `nuxelctl`, the wallpaper, the animation).  The 8 WARNs are the same soft drifts as §9.1
(owned by `bg-02`), plus the unavailable aarch64 colour selftest — unchanged.

**Authorising record for the appended pins** (regression rule §10): `briq-00d-baseline-protection`
revision 5, whose appended revision names every old→new pair; the manifest entry is appended in
`docs/beta-finalization/baseline-protection.json` → `history` (`invariant-added`,
`INV-11-a32-enumerated-asset-pins`, with the `old_to_new` table).  No protected file's bytes were
changed by this addition, so no re-pin was required.

**Verdict:** `OFFLINE_TESTED` — the gate ran on this host against the real tree (exit 0).  It is
still not a claim about any hardware: INV-11 exists so that drift in these A32 assets is *visible*,
never so that a green gate proves a feature works.
