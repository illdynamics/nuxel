# Boot diagnostics: three durable Settings controls, their boot-time consumer, and
# the honest Bixby-hold override (area 3 – display/boot, briq-02b)
#
# `bg-02-boot-animation-launcher` verification pass (revision 3): the surface now
# carries the FULL set the briQ asks for - the standard-animation control
# (`animation_mode`), the persistent verbose-boot control (`verbose_boot`) and the
# verbosity level (`verbosity_level`) - in ONE durable document, with ONE
# precedence rule, exposed on all four paths (Settings app, Quick Settings tile,
# `nuxelctl`, and the early-boot consumer).

Scope: Samsung Galaxy S10+ **SM-G975F / beyond2lte**, Fedora 43 ARM64 userspace,
Linux 4.14.253, systemd PID 1.

Access tier: **repository-only implementation** with a persisted setting and a
boot-time consumer, plus a **one-time Bixby hold override** that the installed
early boot stage cannot support today.

**Terminal states for this area**

| Item | State |
|---|---|
| Durable setting document + migration + upgrade-safety | `OFFLINE_TESTED` |
| Settings UI path (Quick Settings tile + Settings app) | `OFFLINE_TESTED` |
| Console path (`nuxelctl verbose-boot status\|on\|off\|animation\|verbosity`) | `OFFLINE_TESTED` |
| Boot-time consumer (early userspace stage, systemd unit) | `OFFLINE_TESTED` |
| Standard-animation control (`animation_mode`) + verbosity level | `OFFLINE_TESTED` |
| An actual verbose boot / skipped animation seen on the glass | `NEEDS_OWNER_TEST` |
| One-time **Bixby hold** override | `BLOCKED_KERNEL` / **`BOOT_UPDATE_REQUIRED`** (see §5) |

No claim in this document is `VERIFIED_ON_S10PLUS`.

---

## 1. What "verbose boot" means here

There are two different things a user could call "verbose boot", and only one of
them is reachable without flashing:

1. **Kernel command line** (`nuxel.verbose_boot=1`, `console=ttyGS0`, loglevel).
   This lives in the **BOOT partition**. Changing it needs a boot-image write,
   which this mission forbids. It is therefore **not** implemented and the tooling
   says so (see §5).
2. **Nuxel's own boot surface** — the thing the user actually sees: a boot log on
   the panel + a shortened boot animation so the log is visible as early as
   possible, instead of a full 8 s animation. **This is what the setting
   controls**, and it is entirely userspace: no BOOT/USERDATA/DTB write.

The setting is deliberately honest about that boundary: enabling it never claims
to have changed the kernel command line.

## 2. Storage contract: durable, migratable, never clobbered

| Item | Value |
|---|---|
| Durable document | `/etc/nuxel/boot/verbose-boot.json` (shipped default: `configs/nuxel/boot/verbose-boot.json`) |
| Schema | `schema_version: 1`, `verbose_boot: bool`, `animation_mode: "standard"\|"short"\|"off"`, `verbosity_level: 0..3`, `set_by`, `updated_at`, `migrated_from` |
| Schema note | the two added keys deliberately do **not** bump `schema_version`: the contract is additive and merge-on-write, so an older launcher keeps reading the document it knows and a newer one falls back to a default for a missing key |
| Written by | Nuxel Settings / Quick Settings (via `NuxelHost.configSet('verbose-boot')`) and `nuxelctl verbose-boot on\|off\|animation\|verbosity` — **the same file, atomically** (same-directory `rename`) |
| Legacy locations migrated once | `/etc/nuxel/verbose-boot`, `/var/lib/nuxel/verbose-boot.legacy`, `/var/lib/nuxel/verbose-boot`; plus the old launcher localStorage flags `nuxel.verboseBoot`, `nuxel.verbose_boot`, `nuxel.settings.verboseBoot` |
| Upgrade rule | the image installs the shipped default with the **`keep`** rule (existing file wins), and every write **merges** into the loaded document, so keys a newer/older revision does not know about are preserved. An unreadable document is reported and **never overwritten** |
| Runtime state it publishes | `/run/nuxel/verbose-boot` (K=V: `EFFECTIVE`, `SOURCE`, `CONFIG_SOURCE`, `ANIMATION_MODE`, `ANIMATION_MODE_SOURCE`, `EFFECTIVE_ANIMATION`, `ANIMATION_REASON`, `VERBOSITY`, `VERBOSITY_SOURCE`, `ANIM_HANDOFF`, `OVERRIDE_*`, `ONCE*`, `CMDLINE_VERBOSE`, `TS`), `/run/nuxel/anim-skip.request`, `/var/lib/nuxel/verbose-boot` (durable record), `/var/log/nuxel/boot-stage.log`, kernel markers `NUXEL_VERBOSE_BOOT=…` and `NUXEL_BOOT_ANIMATION=…` |

## 3. Boot-time consumer

`nuxel-verbose-boot.service` (installed from
`tools/s10plus/a33/nuxel-verbose-boot.service`) runs
`/usr/libexec/nuxel/nuxel-verbose-boot`
(`tools/s10plus/a33/nuxel-verbose-boot.py`) in the **early userspace** stage:

* `DefaultDependencies=no`, `After=local-fs.target systemd-journald.socket`,
  `Before=nuxel-wl-fb.service nuxel-pwa-host.service nuxel-wayland.service`,
  `WantedBy=sysinit.target`;
* `SuccessExitStatus=0 1` — a failure here must never stop a boot;
* it touches **no framebuffer memory**: it decides, records and publishes, which
  keeps the single-owner rule from `ANIMATION-HANDOFF.md` intact. The display
  bridge and the launcher read the state it publishes.

Read by:

| Consumer | Uses |
|---|---|
| `/usr/lib/nuxel/nuxel-wl-fb` (bridge) | `/run/nuxel/verbose-boot`, `/run/nuxel/anim-skip.request` before the handoff ⇒ **deliberately waives the minimum-cycle floor** so the boot log is on the glass as early as possible. The verdict comes from decision 5 of the shared handoff table; the bridge emits `ANIM_MIN_CYCLE_SKIPPED`, writes `ANIM_MIN_CYCLE_SKIPPED` to `/var/lib/nuxel/anim-min-cycle.completed`, and the receipt records `reason=verbose_boot_requested` with **`terminal=0`** — a user choice is never reported as a completed animation cycle |
| `nuxel-pwa-host` + `pwa/nuxel-home/js/bootlog.js` | the boot-log overlay in the launcher (same boot) |
| `nuxelctl verbose-boot status` | printed effective state, source and override capability |

Effective-state resolution order (first match wins, and the source is recorded):
`bixby_hold_once` → `cmdline` → `config` → `default`.

### 3.1 The other two controls: the standard-animation control and the verbosity level

`verbose_boot` answers *"is the boot log shown?"*. The two controls the briQ also
requires answer different questions, so they are separate keys (and separate
console verbs) rather than overloading one boolean:

| Control | Key in the durable document | Values | What it does |
|---|---|---|---|
| Standard animation | `animation_mode` | `standard` (default) · `short` · `off` | `standard` = the full 192-frame / 24 fps animation and its minimum-cycle handoff; `short` = trade the animation for the earliest handoff; `off` = no animation at all |
| Verbose boot | `verbose_boot` | `true` · `false` (default) | show the boot log on the glass and hand over early |
| Verbosity level | `verbosity_level` | `0` quiet · `1` normal (default) · `2` verbose · `3` debug | **how much** the boot log says. It never turns the log on — that is `verbose_boot`'s job alone |

**One precedence rule**, implemented once in the consumer and asserted in two
suites, so the three controls can never contradict each other. The canonical,
machine-greppable form (it appears verbatim in
`configs/nuxel/boot/verbose-boot.json`, in the consumer and in the Settings panel):

```
off > short > verbose_boot > standard
```

| `animation_mode` | effective `verbose_boot` | Result | `ANIMATION_REASON` |
|---|---|---|---|
| `off` | any | animation off | `animation_mode_off` |
| `short` | any | hand over early | `animation_mode_short` |
| `standard` | `true` (config, cmdline, or the one-time hold) | hand over early — the operator asked to *see* the log | `verbose_boot_requested` |
| `standard` | `false` | full animation + minimum-cycle handoff | `standard` |
| a typo (e.g. `turbo`) | any | falls back to `standard` **and says so** (`ANIMATION_MODE_SOURCE=invalid`) | per the rows above |

An invalid `verbosity_level` is reported too: a non-integer falls back to `1`
(`VERBOSITY_SOURCE=invalid`), an out-of-range integer is **clamped and reported**
(`VERBOSITY_SOURCE=clamped`) by the boot consumer, while the *console* refuses an
out-of-range value outright (`refused, not clamped silently`) so an operator typo
is never stored behind their back.

The consumer publishes the whole decision in `/run/nuxel/verbose-boot`
(`ANIMATION_MODE`, `ANIMATION_MODE_SOURCE`, `EFFECTIVE_ANIMATION`,
`ANIMATION_REASON`, `VERBOSITY`, `VERBOSITY_SOURCE`, `ANIM_HANDOFF`) and emits
`NUXEL_BOOT_ANIMATION=<effective> reason=<reason> verbosity=<n>` to the kernel log.
`/run/nuxel/anim-skip.request` now names the reason
(`ANIM_SKIP_REQUESTED reason=animation_mode_off|animation_mode_short|verbose_boot_requested
animation_mode=<requested>`), so the bridge and the receipt carry the *why* and not
just the *that*.

## 4. The UI and console paths cannot diverge

| Surface | File | Notes |
|---|---|---|
| Quick Settings tile | `pwa/nuxel-home/js/qs.js` | One **boot-diagnostics** tile, created dynamically, synced from the store. **Tap** = verbose boot on/off; **long press (600 ms, with a click-swallow guard so it cannot double-fire)** = cycle the animation policy `standard → short → off`. Its `title`/dataset always name the *effective* policy and its reason, so the precedence is visible in the panel instead of surprising the operator after a reboot |
| Settings app | `pwa/nuxel-apps/settings/` (Developer → **Boot diagnostics** card) | Three real controls: `#animation-mode` (standard/short/off), `#verbose-boot-toggle`, `#verbosity-level` (0..3), plus `#save-boot` for one whole-panel write. It writes the same document through the host (`configSet('verbose-boot')`), **merges** into the loaded JSON (so unknown keys survive), sets `set_by=user`/`updated_at`, shows the durable state + the effective policy/reason + the `this boot:` line from `/run/nuxel/verbose-boot`, and states the override capability verbatim. If the write fails the panel reloads from the document and says so — the UI never claims a setting it did not store |
| Settings store | `pwa/nuxel-home/js/settings-store.js` | DOM-free, unit-tested store: one document per setting name, merge-on-write, migration, host→localStorage degradation, plus `animationMode()/setAnimationMode()`, `verbosityLevel()/setVerbosityLevel()`, `bootDiagnostics()/setBootDiagnostics()` and `effectiveAnimation()` (the precedence rule in one place) |
| Console | `tools/s10plus/a33/nuxelctl` | `verbose-boot status`, `on`, `off`, `animation standard\|short\|off`, `verbosity 0..3`, `override` — every write goes through one merge-on-write helper |
| Offline gate | `tools/s10plus/a33/tests/run-boot-tests.sh` | runs this harness (plus the handoff, colour, launcher and safe-zone legs) as one command, headless and rootless |
| Owner procedure | `docs/beta-finalization/manual-proof/03-display-boot.md` | area 3 step 5: enable verbose boot, reboot once, watch the boot log appear; step 5b: compare verbosity 0 vs 3; step 5c: set the animation policy to `off` and back to `standard` |
| Launcher manifest | `pwa/nuxel-home/manifest.json` | `nuxel.settings_documents` lists `/etc/nuxel/boot/verbose-boot.json` |

## 5. The one-time Bixby-hold override — implemented, NOT deployed

Requirement: holding **Bixby during the early boot stage** turns verbose boot on
for **that boot only** (a recovery aid).

* The early boot stage half is written (`tools/s10plus/a33/nuxel-boot-stage-verbose.sh`):
  it discovers the `gpio_keys` input node **by name** (never a hard-coded
  `eventN`, the same rule the touch pipeline uses), checks that the Bixby key
  (keycode 703) is held for `NUXEL_BIXBY_HOLD_MS` (default 1200 ms), then drops
  `/run/nuxel/boot-verbose-once` and publishes
  `bixby-hold-override=1` in `/run/nuxel/boot-stage-capabilities`.
* **It is not installed.** That fragment belongs in the initramfs inside the
  **BOOT partition** (insertion point documented: `boot/initramfs/init.sh`, just
  before the `nuxel_start_animation` call). Installing it requires a BOOT
  partition write, which this mission forbids.
* The userspace consumer therefore honours the override **only** when the stage
  proves it can produce it (`bixby-hold-override=1` present). On the installed
  A23 initramfs it reports:

```
OVERRIDE_CAPABILITY=BOOT_UPDATE_REQUIRED
OVERRIDE_REASON=the installed early boot stage does not publish bixby-hold-override=1
                (it cannot read the Bixby key state); enabling the one-time override
                requires a BOOT partition update, which this mission forbids (no flashing)
NUXEL_VERBOSE_BOOT_OVERRIDE_REFUSED reason=BOOT_UPDATE_REQUIRED
```

There is **no cosmetic switch** for this: a request that cannot be honoured is
refused with a kernel marker, and the shipped config records the status as
`BOOT_UPDATE_REQUIRED` in `bixby_hold_override.status`. When a future BOOT update
installs the fragment, the same code path starts honouring it with no change.

Starting from the repository:
`bash tools/s10plus/a33/nuxel-boot-stage-verbose.sh` is the fragment; a future
BOOT update must add `nuxel-key-hold` (a small helper that returns 0 when the key
is held for the requested duration) to the initramfs.

## 6. Tests (offline)

```sh
python3 tools/s10plus/a33/nuxel-verbose-boot.py --selftest   # the acceptance harness
python3 tools/s10plus/a33/nuxel-verbose-boot.py --status     # decision + policy + verbosity
node      tools/s10plus/a33/tests/settings-store-test.js     # the store contract
NUXEL_ROOT=/tmp/fake nuxelctl verbose-boot on|off|status     # the console path
NUXEL_ROOT=/tmp/fake nuxelctl verbose-boot animation off     # the standard-animation control
NUXEL_ROOT=/tmp/fake nuxelctl verbose-boot verbosity 3       # the verbosity level
python3 tools/s10plus/a33/tests/test-boot-surface-contract.py # cross-file wiring
```

### 6.1 The acceptance harness: does the setting survive an upgrade?

`nuxel-verbose-boot.py --selftest` runs the **real** consumer and the **real**
decision code against fake roots (`/etc`, `/run`, `/var`, `/proc` under a tmpdir) —
no phone, no systemd, no `/etc` write on this host:

| Scenario | Assertion | Result |
|---|---|---|
| shipped default | `verbose_boot=false`; override recorded as `BOOT_UPDATE_REQUIRED` (not faked) | PASS |
| fresh install | `EFFECTIVE=0`, no `anim-skip.request`, durable record written, capability reported | PASS |
| user turns it ON | `EFFECTIVE=1 SOURCE=config`, `ANIM_HANDOFF=skip-animation`, boot log seeded | PASS |
| **rootfs/package upgrade** | the installer's **`keep`** rule leaves the user's `verbose_boot=true` (and `set_by=user`) intact; the next boot is still verbose | PASS |
| negative control | a *plain overwrite* of the shipped default **would** lose the setting (proves the test is load-bearing) | PASS |
| legacy location | one migration into the durable document, value preserved, `migrated_from` recorded | PASS |
| unreadable document | boot still succeeds (exit 0), file left byte-identical, reported `CONFIG_SOURCE=unreadable` | PASS |
| Bixby hold, stage cannot | `ONCE_REQUESTED=1`, `ONCE=0`, boot stays non-verbose (refused, not faked) | PASS |
| Bixby hold, stage can | `EFFECTIVE=1 SOURCE=bixby_hold_once`, **nothing persisted**, request consumed so a second start in the same boot is normal again | PASS |
| shipped default (policy) | `animation_mode=standard`, `verbosity_level=1`, and the precedence rule is present in the document | PASS |
| default boot (policy) | `EFFECTIVE_ANIMATION=standard ANIMATION_REASON=standard VERBOSITY=1`, **no** `anim-skip.request` | PASS |
| verbose only | `EFFECTIVE_ANIMATION=short reason=verbose_boot_requested`, skip request names the reason, `VERBOSITY` untouched (controls are independent), the document itself is unchanged | PASS |
| `animation_mode=short` / `off` (verbose OFF) | skip request with `reason=animation_mode_short` / `animation_mode_off`; `off` also wins over `verbose_boot=true` | PASS |
| precedence: `off` + verbose ON | `EFFECTIVE_ANIMATION=off reason=animation_mode_off` while `EFFECTIVE=1` (the log is still shown) | PASS |
| unknown `animation_mode` | falls back to `standard`, reported as `ANIMATION_MODE_SOURCE=invalid`, and is **not** faked into a skip request | PASS |
| `verbosity_level` 3 / 9 / `"lots"` | honoured, clamped to 3 (`clamped`), rejected to 1 (`invalid`); **no** skip request and **no** boot log are created by verbosity alone | PASS |
| boot-log snapshot by level | level 0 is the bounded quiet form and never emits subsystem lines; level 3 says strictly more than level 0 | PASS |

Result: **`verbose-boot offline harness passed (upgrade-safe, offline)`** — 55 checks, 0 failures (recorded this revision).

### 6.2 The store contract (`settings-store-test.js`)

**59 checks, 0 failures** (recorded this revision). Part 1–4: default OFF, one host name (`verbose-boot`),
persistence and round-trip, merge-on-write preserving an unknown key, legacy-flag
migration marked `set_by=migrated` and **not** overriding a user decision, host
transport (`configGet`/`configSet('verbose-boot')`), and cross-checks that the boot
consumer, the launcher manifest, the Quick Settings tile **and the Settings app's
Boot diagnostics card** all use the same document (including that the app merges
rather than replaces, and reverts its controls when a write fails).

Part 5 (bg-02 verification pass) covers the other two controls: the exported
`ANIMATION_MODES` list is exactly the one the console accepts; the defaults are
`standard` / `1`; `setAnimationMode('turbo')` and `setVerbosityLevel(9)` are
**refused rather than stored**; all three keys land in ONE document and a write to
one does not drop its siblings; `bootDiagnostics()` / `setBootDiagnostics()` give
the panel a whole-document read/write that still preserves an unknown key
(`future_key`); and the precedence table is asserted case by case
(`off`+off, `short`+off, `standard`+verbose, `off`+verbose, `short`+verbose,
`standard`+quiet, and a typo with verbose on).

### 6.3 The cross-file wiring contract (`test-boot-surface-contract.py`)

Asserts that the document, the consumer, `nuxelctl`, the store, the Settings app
and the Quick Settings tile all speak the same three-value vocabulary and the same
precedence rule, that there is exactly one document writer per surface, that the
consumer publishes `EFFECTIVE_ANIMATION`/`VERBOSITY`/`NUXEL_BOOT_ANIMATION`, that
the skip request names its reason, and that the boot surface contains **no guessed
reboot/magic string**. See §6.4 for the recorded failure count.

### 6.4 Recorded run (this revision, build host, no phone/VMs)

```
python3 tools/s10plus/a33/nuxel-verbose-boot.py --selftest   -> passed, 55 checks, 0 failures
node tools/s10plus/a33/tests/settings-store-test.js          -> passed, 59 checks, 0 failures
python3 tools/s10plus/a33/tests/test-boot-surface-contract.py -> PASS, 295 checks, 0 failures
node tools/s10plus/a33/tests/launcher-registry-test.js       -> passed, 107 checks, 0 failures (1 WARN: the Live Console app tree belongs to another build group)
node tools/s10plus/a32/tests/safe-zones-test.js              -> passed, 44 checks, 0 failures
bash tools/s10plus/a33/tests/run-boot-tests.sh               -> BOOT-TESTS: ALL PASS (8 legs, 1 SKIP)
```

The compiled-artefact legs (`--build`, the binary layer of the colour golden-bytes
test) need an aarch64 host: the UTM Fedora 43 guest was **not reachable** during
this revision, so those legs reported `SKIP` — a skip is never a pass, and the
aarch64 build/VM parity run stays owned by `bg-11-vm-parity`.

## 7. Owner test (deferred; recorded in the manual proof checklist, area 3)

```sh
nuxelctl verbose-boot on ; cat /etc/nuxel/boot/verbose-boot.json
# reboot normally (the phone must return to Nuxel), then:
cat /run/nuxel/verbose-boot
dmesg | grep NUXEL_VERBOSE_BOOT
dmesg | grep NUXEL_BOOT_ANIMATION
```
Expected: next boot shows Nuxel's boot log early and a shortened animation; the
document still says `"verbose_boot": true` after the reboot; `/run/nuxel/verbose-boot`
reports `EFFECTIVE_ANIMATION=short ANIMATION_REASON=verbose_boot_requested`.
Then `nuxelctl verbose-boot off` and reboot again: the full animation returns
(`EFFECTIVE_ANIMATION=standard ANIMATION_REASON=standard`, and **no**
`/run/nuxel/anim-skip.request`). Finish with `nuxelctl verbose-boot animation off`
+ reboot (no animation) and back to `standard` — area 3 steps 5b/5c.

Failure symptoms: the document reverts to `false` after a reboot/upgrade (the
`keep` rule or a merge was broken); `/run/nuxel/verbose-boot` absent (the unit did
not run — `systemctl status nuxel-verbose-boot`); `animation_mode=standard` with
`ANIMATION_REASON=verbose_boot_requested` (expected, not a defect — turn verbose
boot off for the full animation); a value the console refused (check
`nuxelctl verbose-boot status` for the stored value, not what you meant to type).

## 8. Rollback

Repository-only. `git revert` the commit(s) touching
`tools/s10plus/a33/nuxel-verbose-boot.py`,
`tools/s10plus/a33/nuxel-verbose-boot.service`,
`tools/s10plus/a33/nuxel-boot-stage-verbose.sh`,
`configs/nuxel/boot/verbose-boot.json`, `pwa/nuxel-home/js/qs.js`,
`pwa/nuxel-home/js/settings-store.js`, `pwa/nuxel-apps/settings/{index.html,settings.js}`,
`tools/s10plus/a33/nuxelctl`,
`tools/s10plus/a33/tests/{settings-store-test.js,test-boot-surface-contract.py}` and the
boot/settings documents listed in §6.4. On the device: `systemctl disable
nuxel-verbose-boot.service` restores the previous behaviour immediately (the
setting document is inert without its consumer), and the `/etc/nuxel/boot/`
document may be left in place — nothing else reads it.

**Downgrade path (verified, not assumed).** The two added keys are additive, so
`schema_version` stays `1` and an older launcher/consumer that does not know them
**preserves** them instead of clobbering them; an older consumer ignores
`animation_mode` and behaves exactly as it did before (standard animation, verbose
boot shortens it). Roll the setting back with
`nuxelctl verbose-boot animation standard` + `verbosity 1` before downgrading if you
want the visible behaviour to match too. No boot/USERDATA/DTB write is involved at
any point — **no flashing of any kind**.
